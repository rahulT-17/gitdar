"""
Core domain models for the engineering domain.

Rules:
- Pure dataclasses only — no ORM, no I/O, no imports from other src layers
- These shapes flow through the entire application
- If a field can be unknown/missing, it is Optional with a None default
- Enums use str mixin so they serialise cleanly to/from JSON for caching
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ------------------------------------------------------------------ #
# Enums                                                                #
# ------------------------------------------------------------------ #

class PRState(str, Enum):
    OPEN   = "OPEN"
    CLOSED = "CLOSED"
    MERGED = "MERGED"


class MergeableState(str, Enum):
    MERGEABLE   = "MERGEABLE"
    CONFLICTING = "CONFLICTING"
    UNKNOWN     = "UNKNOWN"


class ReviewDecision(str, Enum):
    APPROVED          = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    REVIEW_REQUIRED   = "REVIEW_REQUIRED"


class AuthorRole(str, Enum):
    OWNER         = "OWNER"
    MEMBER        = "MEMBER"
    COLLABORATOR  = "COLLABORATOR"
    CONTRIBUTOR   = "CONTRIBUTOR"
    NONE          = "NONE"


class ReviewState(str, Enum):
    APPROVED          = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    COMMENTED         = "COMMENTED"
    DISMISSED         = "DISMISSED"
    PENDING           = "PENDING"


# ------------------------------------------------------------------ #
# Nested models                                                        #
# ------------------------------------------------------------------ #

@dataclass
class Author:
    """Who opened or reviewed the PR."""
    login: str
    role: AuthorRole = AuthorRole.NONE


@dataclass
class Repository:
    """Which repo the PR lives in."""
    name: str           # e.g. "gitdar"
    owner: str          # e.g. "rahuldev"
    is_private: bool = False

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


@dataclass
class Review:
    """
    A formal review left on a PR.
    This is an Approve / Request Changes / Comment — not just a comment.
    """
    author: Author
    state: ReviewState
    submitted_at: datetime
    body: str = ""


@dataclass
class ReviewRequest:
    """Someone who has been requested to review but hasn't yet."""
    login: str


# ------------------------------------------------------------------ #
# Core PR model                                                        #
# ------------------------------------------------------------------ #

@dataclass
class PullRequest:
    """
    Everything gitdar needs to know about a PR.

    reviews and review_requests are nested — fetched in the same
    GraphQL query as the PR itself and cached together as one object.
    """
    # Identity
    id: str                         # GitHub node ID (used for cache key)
    number: int                     # PR #42
    title: str
    url: str

    # Ownership
    author: Author
    repository: Repository

    # State
    state: PRState
    is_draft: bool
    mergeable: MergeableState
    review_decision: Optional[ReviewDecision]

    # Time
    created_at: datetime
    updated_at: datetime
    merged_at: Optional[datetime] = None

    # Size — useful for risk scoring (huge PRs = higher risk)
    additions: int = 0
    deletions: int = 0

    # Reviews — nested, fetched in the same query
    reviews: list[Review] = field(default_factory=list)
    review_requests: list[ReviewRequest] = field(default_factory=list)

    # ---------------------------------------------------------------- #
    # Computed properties — used by risk scoring in rules.py            #
    # ---------------------------------------------------------------- #

    @property
    def is_mine(self) -> bool:
        """Convenience — set externally after fetching based on viewer login."""
        return getattr(self, "_is_mine", False)

    @property
    def size(self) -> int:
        """Total lines changed — proxy for PR complexity."""
        return self.additions + self.deletions

    @property
    def has_conflicts(self) -> bool:
        return self.mergeable == MergeableState.CONFLICTING

    @property
    def is_approved(self) -> bool:
        return self.review_decision == ReviewDecision.APPROVED

    @property
    def needs_review(self) -> bool:
        return self.review_decision == ReviewDecision.REVIEW_REQUIRED

    @property
    def changes_requested(self) -> bool:
        return self.review_decision == ReviewDecision.CHANGES_REQUESTED

    @property
    def age_hours(self) -> float:
        """How many hours old this PR is — used for staleness rules."""
        from datetime import timezone
        now = datetime.now(timezone.utc)
        created = self.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return (now - created).total_seconds() / 3600

    def __repr__(self) -> str:
        return (
            f"PullRequest(#{self.number} '{self.title}' "
            f"by {self.author.login} — {self.state.value})"
        )