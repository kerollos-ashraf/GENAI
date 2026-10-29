"""Claim entities and value objects. Validation lives here, so every entry point (tools, API,
tests) enforces the same rules."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.domain.errors import NotFoundError

ClaimType = Literal["Water Damage", "Personal Property"]

CLAIM_ID_PATTERN = r"^CLM-\d{4,6}$"
POLICY_NUMBER_PATTERN = r"^POL-\d{4,6}$"
MAX_CLAIM_AMOUNT = 1_000_000

_CLAIM_TYPE_ALIASES: dict[str, ClaimType] = {
    "water damage": "Water Damage",
    "water": "Water Damage",
    "pipe burst": "Water Damage",
    "personal property": "Personal Property",
    "property": "Personal Property",
}


class ClaimStatus(StrEnum):
    SUBMITTED = "Submitted"
    UNDER_REVIEW = "Under Review"
    APPROVED = "Approved"
    REJECTED = "Rejected"


def _upper_stripped(value: object) -> object:
    return value.strip().upper() if isinstance(value, str) else value


class ClaimLookup(BaseModel):
    """Input for looking a claim up."""

    claim_id: str = Field(description="Claim identifier, e.g. CLM-8821", pattern=CLAIM_ID_PATTERN)

    _normalise_id = field_validator("claim_id", mode="before")(_upper_stripped)


class ClaimSubmission(BaseModel):
    """Input for filing a claim. Every field is validated before anything is written."""

    policy_number: str = Field(
        description="Policy number, e.g. POL-1092", pattern=POLICY_NUMBER_PATTERN
    )
    claim_type: ClaimType = Field(
        description="Type of claim: 'Water Damage' or 'Personal Property'"
    )
    amount: float = Field(
        description="Claimed amount in USD", gt=0, le=MAX_CLAIM_AMOUNT, allow_inf_nan=False
    )
    description: str = Field(
        description="Short description of the incident", min_length=10, max_length=1000
    )

    _normalise_policy = field_validator("policy_number", mode="before")(_upper_stripped)

    @field_validator("claim_type", mode="before")
    @classmethod
    def _resolve_alias(cls, value: object) -> object:
        if isinstance(value, str):
            return _CLAIM_TYPE_ALIASES.get(value.strip().lower(), value)
        return value

    @field_validator("amount")
    @classmethod
    def _round_to_cents(cls, value: float) -> float:
        return round(value, 2)

    @field_validator("description")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class Claim(BaseModel):
    claim_id: str
    policy_number: str
    claim_type: str
    status: str
    amount: float
    description: str | None = None


class ClaimNotFoundError(NotFoundError):
    def __init__(self, claim_id: str) -> None:
        super().__init__(f"No claim found with ID {claim_id}")
        self.claim_id = claim_id
