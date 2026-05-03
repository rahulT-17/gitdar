"""
GitHub GraphQL client with mandatory local cache.

Two rules that never break:
  1. Cache first — always check SQLite before hitting the API
  2. Graceful fallback — if API fails, return stale cache instead of crashing

Why GraphQL over REST?
  One query gets PRs + reviews + review requests in a single request.
  REST would need 3+ calls per repo, burning through rate limits fast.
"""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

from src.config.defaults import (
    DB_FILE,
    GITHUB_API_BASE,
    GITHUB_CACHE_TTL_SECONDS,
)
from src.domains.engineering.domain.models import (
    Author,
    AuthorRole,
    MergeableState,
    PRState,
    PullRequest,
    Repository,
    Review,
    ReviewDecision,
    ReviewRequest,
    ReviewState,
)


# ------------------------------------------------------------------ #
# GraphQL query                                                        #
# ------------------------------------------------------------------ #

# One query — gets everything gitdar needs about your open PRs
# viewer = the authenticated user (whoever's token we're using)
PULL_REQUESTS_QUERY = """
query($after: String) {
  viewer {
    login
    pullRequests(
      first: 50
      states: [OPEN]
      orderBy: { field: UPDATED_AT, direction: DESC }
      after: $after
    ) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        id
        number
        title
        url
        isDraft
        state
        mergeable
        reviewDecision
        createdAt
        updatedAt
        mergedAt
        additions
        deletions
        author {
          login
          ... on User {
            login
          }
        }
        authorAssociation
        repository {
          name
          owner { login }
          isPrivate
        }
        reviews(first: 20) {
          nodes {
            author { login }
            state
            submittedAt
            body
          }
        }
        reviewRequests(first: 20) {
          nodes {
            requestedReviewer {
              ... on User { login }
            }
          }
        }
      }
    }
  }
}
"""

# Query to get PRs that were recently merged or closed — for standup
RECENT_ACTIVITY_QUERY = """
query($login: String!, $since: DateTime!) {
  user(login: $login) {
    pullRequests(
      first: 30
      states: [MERGED, CLOSED]
      orderBy: { field: UPDATED_AT, direction: DESC }
    ) {
      nodes {
        id
        number
        title
        url
        isDraft
        state
        mergeable
        reviewDecision
        createdAt
        updatedAt
        mergedAt
        additions
        deletions
        authorAssociation
        repository {
          name
          owner { login }
          isPrivate
        }
        reviews(first: 20) {
          nodes {
            author { login }
            state
            submittedAt
            body
          }
        }
        reviewRequests(first: 20) {
          nodes {
            requestedReviewer {
              ... on User { login }
            }
          }
        }
      }
    }
  }
}
"""


# ------------------------------------------------------------------ #
# Repository                                                           #
# ------------------------------------------------------------------ #

class GitHubRepository:
    """
    GitHub GraphQL client with SQLite cache.

    Usage:
        repo = GitHubRepository(token="ghp_xxx")
        prs  = repo.get_open_pull_requests()
    """

    GRAPHQL_URL = "https://api.github.com/graphql"

    def __init__(self, token: str) -> None:
        self.token = token
        self._db_path = Path(DB_FILE).expanduser()
        self._ensure_cache_table()

    # ---------------------------------------------------------------- #
    # Public API                                                         #
    # ---------------------------------------------------------------- #

    def get_open_pull_requests(self) -> list[PullRequest]:
        """
        Returns all open PRs for the authenticated user.
        Cache TTL: 5 minutes. Falls back to stale cache if API fails.
        """
        cache_key = f"open_prs:{self._get_viewer_login()}"
        return self._fetch_with_cache(
            cache_key=cache_key,
            fetcher=self._fetch_open_prs,
        )

    def get_recent_activity(self, since_hours: int = 24) -> list[PullRequest]:
        """
        Returns PRs merged or closed in the last N hours.
        Used by gitdar standup to build the YESTERDAY section.
        """
        login = self._get_viewer_login()
        cache_key = f"recent_activity:{login}:{since_hours}h"
        return self._fetch_with_cache(
            cache_key=cache_key,
            fetcher=lambda: self._fetch_recent_activity(login, since_hours),
            ttl=300,
        )

    def get_viewer_login(self) -> Optional[str]:
        """Returns the GitHub username of the authenticated user."""
        return self._get_viewer_login()

    # ---------------------------------------------------------------- #
    # Fetchers — hit the real GitHub GraphQL API                        #
    # ---------------------------------------------------------------- #

    def _fetch_open_prs(self) -> list[PullRequest]:
        """Paginate through all open PRs for the viewer."""
        prs = []
        cursor = None

        while True:
            variables = {"after": cursor}
            data = self._graphql(PULL_REQUESTS_QUERY, variables)

            if not data:
                break

            viewer = data.get("viewer", {})
            pr_connection = viewer.get("pullRequests", {})
            nodes = pr_connection.get("nodes", [])
            page_info = pr_connection.get("pageInfo", {})

            for node in nodes:
                pr = self._parse_pr(node)
                if pr:
                    prs.append(pr)

            if not page_info.get("hasNextPage"):
                break

            cursor = page_info.get("endCursor")

        return prs

    def _fetch_recent_activity(
        self,
        login: str,
        since_hours: int,
    ) -> list[PullRequest]:
        """Fetch recently merged/closed PRs for standup generation."""
        from datetime import timedelta
        since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        since_iso = since.isoformat()

        data = self._graphql(
            RECENT_ACTIVITY_QUERY,
            {"login": login, "since": since_iso},
        )

        if not data:
            return []

        nodes = (
            data.get("user", {})
            .get("pullRequests", {})
            .get("nodes", [])
        )

        prs = []
        for node in nodes:
            pr = self._parse_pr(node)
            if pr and pr.updated_at >= since:
                prs.append(pr)

        return prs

    # ---------------------------------------------------------------- #
    # Cache layer                                                        #
    # ---------------------------------------------------------------- #

    def _fetch_with_cache(
        self,
        cache_key: str,
        fetcher,
        ttl: int = GITHUB_CACHE_TTL_SECONDS,
    ) -> list[PullRequest]:
        """
        Cache-first fetch pattern.

        1. Check SQLite for a fresh cached result
        2. If fresh → return it immediately, no API call
        3. If stale or missing → fetch from GitHub API
        4. If API fails → return stale cache instead of crashing
        5. If no cache at all → return empty list with a warning
        """
        # Step 1: check cache
        cached = self._read_cache(cache_key)

        if cached:
            age = time.time() - cached["timestamp"]
            if age < ttl:
                # fresh — return immediately
                return self._deserialise_prs(cached["data"])

        # Step 2: try the API
        try:
            prs = fetcher()
            # success — update cache
            self._write_cache(cache_key, self._serialise_prs(prs))
            return prs
        except Exception:
            # Step 3: API failed — fall back to stale cache
            if cached:
                return self._deserialise_prs(cached["data"])
            # No cache at all
            return []

    def _ensure_cache_table(self) -> None:
        """Create the cache table if it doesn't exist yet."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS github_cache (
                    key       TEXT PRIMARY KEY,
                    data      TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)

    def _read_cache(self, key: str) -> Optional[dict]:
        try:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT data, timestamp FROM github_cache WHERE key = ?",
                    (key,),
                ).fetchone()
                if row:
                    return {"data": row[0], "timestamp": row[1]}
        except Exception:
            pass
        return None

    def _write_cache(self, key: str, data: str) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO github_cache (key, data, timestamp)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        data = excluded.data,
                        timestamp = excluded.timestamp
                    """,
                    (key, data, time.time()),
                )
        except Exception:
            pass  # cache write failure is never fatal

    # ---------------------------------------------------------------- #
    # GraphQL transport                                                  #
    # ---------------------------------------------------------------- #

    def _graphql(
        self,
        query: str,
        variables: Optional[dict] = None,
    ) -> Optional[dict]:
        """
        Send a GraphQL query to GitHub.
        Returns the 'data' field or None on failure.
        Never raises — callers handle None as a signal to use cache.
        """
        try:
            response = httpx.post(
                self.GRAPHQL_URL,
                json={"query": query, "variables": variables or {}},
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
            if response.status_code != 200:
                return None
            body = response.json()
            if "errors" in body:
                return None
            return body.get("data")
        except Exception:
            return None

    # ---------------------------------------------------------------- #
    # Viewer login (cached aggressively — changes almost never)         #
    # ---------------------------------------------------------------- #

    _viewer_login_cache: Optional[str] = None

    def _get_viewer_login(self) -> str:
        if self._viewer_login_cache:
            return self._viewer_login_cache

        data = self._graphql("{ viewer { login } }")
        login = (data or {}).get("viewer", {}).get("login", "unknown")
        self._viewer_login_cache = login
        return login

    # ---------------------------------------------------------------- #
    # Parsing — GraphQL response → domain models                        #
    # ---------------------------------------------------------------- #

    def _parse_pr(self, node: dict) -> Optional[PullRequest]:
        """Parse a single PR node from the GraphQL response."""
        try:
            author_node = node.get("author") or {}
            repo_node   = node.get("repository", {})
            owner_node  = repo_node.get("owner", {})

            author = Author(
                login=author_node.get("login", "unknown"),
                role=AuthorRole(
                    node.get("authorAssociation", "NONE")
                ),
            )

            repository = Repository(
                name=repo_node.get("name", ""),
                owner=owner_node.get("login", ""),
                is_private=repo_node.get("isPrivate", False),
            )

            reviews = [
                self._parse_review(r)
                for r in node.get("reviews", {}).get("nodes", [])
                if r
            ]

            review_requests = [
                ReviewRequest(
                    login=(
                        rr.get("requestedReviewer") or {}
                    ).get("login", "")
                )
                for rr in node.get("reviewRequests", {}).get("nodes", [])
                if rr.get("requestedReviewer")
            ]

            review_decision_raw = node.get("reviewDecision")
            review_decision = (
                ReviewDecision(review_decision_raw)
                if review_decision_raw else None
            )

            return PullRequest(
                id=node["id"],
                number=node["number"],
                title=node.get("title", ""),
                url=node.get("url", ""),
                author=author,
                repository=repository,
                state=PRState(node.get("state", "OPEN")),
                is_draft=node.get("isDraft", False),
                mergeable=MergeableState(
                    node.get("mergeable", "UNKNOWN")
                ),
                review_decision=review_decision,
                created_at=self._parse_dt(node.get("createdAt")),
                updated_at=self._parse_dt(node.get("updatedAt")),
                merged_at=self._parse_dt(node.get("mergedAt")),
                additions=node.get("additions", 0),
                deletions=node.get("deletions", 0),
                reviews=reviews,
                review_requests=review_requests,
            )
        except Exception:
            return None

    def _parse_review(self, node: dict) -> Review:
        author_node = node.get("author") or {}
        return Review(
            author=Author(login=author_node.get("login", "unknown")),
            state=ReviewState(node.get("state", "COMMENTED")),
            submitted_at=self._parse_dt(node.get("submittedAt")),
            body=node.get("body", ""),
        )

    @staticmethod
    def _parse_dt(value: Optional[str]) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return datetime.now(timezone.utc)

    # ---------------------------------------------------------------- #
    # Serialisation — domain models ↔ JSON for SQLite cache            #
    # ---------------------------------------------------------------- #

    def _serialise_prs(self, prs: list[PullRequest]) -> str:
        return json.dumps([self._pr_to_dict(pr) for pr in prs])

    def _deserialise_prs(self, data: str) -> list[PullRequest]:
        try:
            items = json.loads(data)
            return [self._dict_to_pr(d) for d in items]
        except Exception:
            return []

    def _pr_to_dict(self, pr: PullRequest) -> dict:
        return {
            "id": pr.id,
            "number": pr.number,
            "title": pr.title,
            "url": pr.url,
            "author": {"login": pr.author.login, "role": pr.author.role.value},
            "repository": {
                "name": pr.repository.name,
                "owner": pr.repository.owner,
                "is_private": pr.repository.is_private,
            },
            "state": pr.state.value,
            "is_draft": pr.is_draft,
            "mergeable": pr.mergeable.value,
            "review_decision": pr.review_decision.value if pr.review_decision else None,
            "created_at": pr.created_at.isoformat(),
            "updated_at": pr.updated_at.isoformat(),
            "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
            "additions": pr.additions,
            "deletions": pr.deletions,
            "reviews": [
                {
                    "author": {"login": r.author.login, "role": r.author.role.value},
                    "state": r.state.value,
                    "submitted_at": r.submitted_at.isoformat(),
                    "body": r.body,
                }
                for r in pr.reviews
            ],
            "review_requests": [
                {"login": rr.login} for rr in pr.review_requests
            ],
        }

    def _dict_to_pr(self, d: dict) -> PullRequest:
        author = Author(
            login=d["author"]["login"],
            role=AuthorRole(d["author"]["role"]),
        )
        repository = Repository(
            name=d["repository"]["name"],
            owner=d["repository"]["owner"],
            is_private=d["repository"]["is_private"],
        )
        reviews = [
            Review(
                author=Author(
                    login=r["author"]["login"],
                    role=AuthorRole(r["author"].get("role", "NONE")),
                ),
                state=ReviewState(r["state"]),
                submitted_at=datetime.fromisoformat(r["submitted_at"]),
                body=r.get("body", ""),
            )
            for r in d.get("reviews", [])
        ]
        review_requests = [
            ReviewRequest(login=rr["login"])
            for rr in d.get("review_requests", [])
        ]
        rd = d.get("review_decision")
        return PullRequest(
            id=d["id"],
            number=d["number"],
            title=d["title"],
            url=d["url"],
            author=author,
            repository=repository,
            state=PRState(d["state"]),
            is_draft=d["is_draft"],
            mergeable=MergeableState(d["mergeable"]),
            review_decision=ReviewDecision(rd) if rd else None,
            created_at=datetime.fromisoformat(d["created_at"]),
            updated_at=datetime.fromisoformat(d["updated_at"]),
            merged_at=datetime.fromisoformat(d["merged_at"]) if d.get("merged_at") else None,
            additions=d["additions"],
            deletions=d["deletions"],
            reviews=reviews,
            review_requests=review_requests,
        )