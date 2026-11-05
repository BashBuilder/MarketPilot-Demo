"""Compliance findings produced by the Compliance agent."""

from typing import Annotated

from pydantic import Field

from app.agents.outputs.base import OutputModel


class ComplianceItem(OutputModel):
    """One policy or claim check with an explicit verdict."""

    check: Annotated[str, Field(min_length=3)]
    passed: bool
    reason: Annotated[str, Field(min_length=5)]


class ComplianceReport(OutputModel):
    """A flag-only report; it never rewrites copy."""

    items: Annotated[list[ComplianceItem], Field(min_length=1)]
