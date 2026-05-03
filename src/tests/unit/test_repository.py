"""
Tests for the GitHub GraphQL client and domain models.

We never hit the real GitHub API in tests.
We mock httpx.post to return controlled GraphQL responses.

Run with:
    pytest tests/unit/test_repository.py -v
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from domains.engineering.domain.models import (
    AuthorRole,
    MergeableState,
    PRState,
    PullRequest,
    ReviewDecision,
    ReviewState,
)
from domains.engineering.infra.repository import GitHubRepository


# ------------------------------------------------------------------ #
# Helpers — fake GraphQL responses                                     #
# ------------------------------------------------------------------ #

def _make_pr_node(
    number: int = 42,
    title: str = "Add rate limiter",
    state: str = "OPEN",
    is_draft: bool = False,
    mergeable: str = "MERGEABLE",
    review_decision: str = "REVIEW_REQUIRED",
    author_login: str = "rahuldev",
    additions: int = 120,
    deletions: int = 30,
    reviews: list = None,
    review_requests: list = None,
) -> dict:
    """Builds a fake PR node matching GitHub's GraphQL response shape."""
    return {
        "id": f"PR_node_{number}",
        "number": number,
        "title": title,
        "url": f"https://github.com/rahuldev/gitdar/pull/{number}",
        "isDraft": is_draft,
        "state": state,
        "mergeable": mergeable,
        "reviewDecision": review_decision,
        "createdAt": "2024-01-01T10:00:00Z",
        "updatedAt": "2024-01-02T10:00:00Z",
        "mergedAt": None,
        "additions": additions,
        "deletions": deletions,
        "authorAssociation": "OWNER",
        "author": {"login": author_login},
        "repository": {
            "name": "gitdar",
            "owner": {"login": "rahuldev"},
            "isPrivate": False,
        },
        "reviews": {
            "nodes": reviews or []
        },
        "reviewRequests": {
            "nodes": review_requests or []
        },
    }


def _graphql_response(nodes: list, has_next_page: bool = False) -> MagicMock:
    """Wraps PR nodes in a fake httpx response object."""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {
        "data": {
            "viewer": {
                "login": "rahuldev",
                "pullRequests": {
                    "pageInfo": {
                        "hasNextPage": has_next_page,
                        "endCursor": "cursor_abc" if has_next_page else None,
                    },
                    "nodes": nodes,
                },
            }
        }
    }
    return mock


def _make_repo(token: str = "ghp_test", tmp_path=None) -> GitHubRepository:
    """Creates a GitHubRepository pointed at a temp DB for testing."""
    repo = GitHubRepository(token=token)
    if tmp_path:
        repo._db_path = tmp_path / "test_cache.db"
        repo._ensure_cache_table()
    return repo


# ------------------------------------------------------------------ #
# Domain model tests                                                   #
# ------------------------------------------------------------------ #

class TestPullRequestModel:

    def test_size_is_additions_plus_deletions(self):
        pr = _make_pr_node(additions=100, deletions=40)
        from domains.engineering.infra.repository import GitHubRepository
        repo = _make_repo()
        parsed = repo._parse_pr(pr)
        assert parsed.size == 140

    def test_has_conflicts_when_mergeable_is_conflicting(self):
        pr = _make_pr_node(mergeable="CONFLICTING")
        repo = _make_repo()
        parsed = repo._parse_pr(pr)
        assert parsed.has_conflicts is True

    def test_no_conflicts_when_mergeable(self):
        pr = _make_pr_node(mergeable="MERGEABLE")
        repo = _make_repo()
        parsed = repo._parse_pr(pr)
        assert parsed.has_conflicts is False

    def test_is_approved_when_review_decision_approved(self):
        pr = _make_pr_node(review_decision="APPROVED")
        repo = _make_repo()
        parsed = repo._parse_pr(pr)
        assert parsed.is_approved is True

    def test_needs_review_when_review_required(self):
        pr = _make_pr_node(review_decision="REVIEW_REQUIRED")
        repo = _make_repo()
        parsed = repo._parse_pr(pr)
        assert parsed.needs_review is True

    def test_repr_is_readable(self):
        pr = _make_pr_node(number=42, title="Add rate limiter")
        repo = _make_repo()
        parsed = repo._parse_pr(pr)
        assert "42" in repr(parsed)
        assert "Add rate limiter" in repr(parsed)


# ------------------------------------------------------------------ #
# GraphQL parsing tests                                                #
# ------------------------------------------------------------------ #

class TestParsing:

    def test_parses_basic_pr_fields(self):
        node = _make_pr_node(number=51, title="Rate limiter")
        repo = _make_repo()
        pr = repo._parse_pr(node)

        assert pr.number == 51
        assert pr.title == "Rate limiter"
        assert pr.author.login == "rahuldev"
        assert pr.repository.name == "gitdar"
        assert pr.state == PRState.OPEN
        assert pr.is_draft is False

    def test_parses_nested_reviews(self):
        node = _make_pr_node(
            reviews=[{
                "author": {"login": "priya"},
                "state": "APPROVED",
                "submittedAt": "2024-01-02T09:00:00Z",
                "body": "Looks good!",
            }]
        )
        repo = _make_repo()
        pr = repo._parse_pr(node)

        assert len(pr.reviews) == 1
        assert pr.reviews[0].author.login == "priya"
        assert pr.reviews[0].state == ReviewState.APPROVED

    def test_parses_review_requests(self):
        node = _make_pr_node(
            review_requests=[{
                "requestedReviewer": {"login": "priya"}
            }]
        )
        repo = _make_repo()
        pr = repo._parse_pr(node)

        assert len(pr.review_requests) == 1
        assert pr.review_requests[0].login == "priya"

    def test_returns_none_for_malformed_node(self):
        repo = _make_repo()
        pr = repo._parse_pr({})   # empty node — missing required fields
        assert pr is None

    def test_author_role_parsed_correctly(self):
        node = _make_pr_node()
        node["authorAssociation"] = "COLLABORATOR"
        repo = _make_repo()
        pr = repo._parse_pr(node)
        assert pr.author.role == AuthorRole.COLLABORATOR


# ------------------------------------------------------------------ #
# Cache tests                                                          #
# ------------------------------------------------------------------ #

class TestCache:

    def test_returns_cached_result_without_hitting_api(self, tmp_path):
        repo = _make_repo(tmp_path=tmp_path)
        pr_node = _make_pr_node()
        prs = [repo._parse_pr(pr_node)]

        # Write to cache manually
        repo._write_cache("test_key", repo._serialise_prs(prs))

        # Now fetch — should not call the API at all
        with patch("httpx.post") as mock_post:
            result = repo._fetch_with_cache(
                cache_key="test_key",
                fetcher=lambda: [],   # fetcher would return empty if called
            )
            mock_post.assert_not_called()

        assert len(result) == 1
        assert result[0].number == 42

    def test_hits_api_when_cache_is_stale(self, tmp_path):
        repo = _make_repo(tmp_path=tmp_path)
        pr_node = _make_pr_node(number=99)
        prs = [repo._parse_pr(pr_node)]

        # Write stale cache — timestamp in the past
        with repo._db_path.open("w"):
            pass  # ensure file exists
        import sqlite3
        repo._ensure_cache_table()
        with sqlite3.connect(repo._db_path) as conn:
            conn.execute(
                "INSERT INTO github_cache (key, data, timestamp) VALUES (?, ?, ?)",
                ("stale_key", repo._serialise_prs(prs), time.time() - 9999),
            )

        # Fresh data from the API
        fresh_pr = _make_pr_node(number=77)
        fetcher_called = []

        def fake_fetcher():
            fetcher_called.append(True)
            return [repo._parse_pr(fresh_pr)]

        result = repo._fetch_with_cache(
            cache_key="stale_key",
            fetcher=fake_fetcher,
        )

        assert fetcher_called   # API was called
        assert result[0].number == 77

    def test_falls_back_to_stale_cache_when_api_fails(self, tmp_path):
        repo = _make_repo(tmp_path=tmp_path)
        pr_node = _make_pr_node(number=42)
        prs = [repo._parse_pr(pr_node)]

        # Write stale cache
        import sqlite3
        repo._ensure_cache_table()
        with sqlite3.connect(repo._db_path) as conn:
            conn.execute(
                "INSERT INTO github_cache (key, data, timestamp) VALUES (?, ?, ?)",
                ("fail_key", repo._serialise_prs(prs), time.time() - 9999),
            )

        # Fetcher blows up — simulates GitHub being down
        def broken_fetcher():
            raise ConnectionError("GitHub is down")

        result = repo._fetch_with_cache(
            cache_key="fail_key",
            fetcher=broken_fetcher,
        )

        # Should return stale data, not crash
        assert len(result) == 1
        assert result[0].number == 42

    def test_returns_empty_list_when_no_cache_and_api_fails(self, tmp_path):
        repo = _make_repo(tmp_path=tmp_path)

        def broken_fetcher():
            raise ConnectionError("GitHub is down")

        result = repo._fetch_with_cache(
            cache_key="nonexistent_key",
            fetcher=broken_fetcher,
        )

        assert result == []


# ------------------------------------------------------------------ #
# Serialisation round-trip test                                        #
# ------------------------------------------------------------------ #

class TestSerialisation:

    def test_pr_survives_serialise_deserialise_round_trip(self):
        """
        PRs go through JSON when stored in SQLite cache.
        Make sure nothing is lost in the round trip.
        """
        node = _make_pr_node(
            number=42,
            title="Add rate limiter",
            reviews=[{
                "author": {"login": "priya"},
                "state": "APPROVED",
                "submittedAt": "2024-01-02T09:00:00Z",
                "body": "LGTM",
            }],
            review_requests=[{
                "requestedReviewer": {"login": "ali"}
            }],
        )
        repo = _make_repo()
        original = repo._parse_pr(node)

        serialised   = repo._serialise_prs([original])
        deserialised = repo._deserialise_prs(serialised)

        assert len(deserialised) == 1
        restored = deserialised[0]

        assert restored.number == original.number
        assert restored.title == original.title
        assert restored.author.login == original.author.login
        assert restored.reviews[0].author.login == "priya"
        assert restored.review_requests[0].login == "ali"
        assert restored.additions == original.additions