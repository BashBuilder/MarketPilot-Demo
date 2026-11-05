"""Repository modules, one per aggregate root."""

from app.database.repositories import approvals, campaigns, runs, versions

__all__ = ["approvals", "campaigns", "runs", "versions"]
