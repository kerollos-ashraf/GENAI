"""The agent's toolkit. Each tool validates its arguments with a domain Pydantic model and
depends only on ports (`Retriever`, `ClaimsRepository`), never on concrete storage."""

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from app.domain.claims import ClaimLookup, ClaimNotFoundError, ClaimSubmission
from app.domain.ports import ClaimsRepository, Retriever

TOOL_SEARCH = "search_policy"
TOOL_CLAIM_STATUS = "get_claim_status"
TOOL_SUBMIT_CLAIM = "submit_claim"


class PolicyQuery(BaseModel):
    query: str = Field(
        description="A focused search query (keywords from the user's question)",
        min_length=2,
        max_length=300,
    )


class AssistantToolkit:
    def __init__(self, retriever: Retriever, claims: ClaimsRepository, top_k: int = 3) -> None:
        self._retriever = retriever
        self._claims = claims
        self._top_k = top_k

    def search_policy(self, query: str) -> tuple[str, list[str]]:
        """Returns (passages for the model, citations as the tool artifact)."""
        chunks = self._retriever.search(query, k=self._top_k)
        if not chunks:
            return "The knowledge base is empty.", []
        content = "\n\n".join(f"[{c.citation}]\n{c.content}" for c in chunks)
        return content, [c.citation for c in chunks]

    def get_claim_status(self, claim_id: str) -> str:
        try:
            return self._claims.get(claim_id).model_dump_json(exclude_none=True)
        except ClaimNotFoundError as exc:
            return f"{exc}."

    def submit_claim(
        self, policy_number: str, claim_type: str, amount: float, description: str
    ) -> str:
        claim = self._claims.submit(
            ClaimSubmission(
                policy_number=policy_number,
                claim_type=claim_type,
                amount=amount,
                description=description,
            )
        )
        return (
            f"Claim submitted successfully. Confirmation ID: {claim.claim_id}. "
            f"Status: {claim.status}. {claim.model_dump_json()}"
        )

    def tools(self) -> list[BaseTool]:
        return [
            StructuredTool.from_function(
                func=self.search_policy,
                name=TOOL_SEARCH,
                description=(
                    "Search OmniCare's insurance policy documents (policies and addenda). Use "
                    "it for every coverage question. Returns passages tagged with [citation]."
                ),
                args_schema=PolicyQuery,
                response_format="content_and_artifact",
            ),
            StructuredTool.from_function(
                func=self.get_claim_status,
                name=TOOL_CLAIM_STATUS,
                description="Look up the current status of an existing insurance claim by its claim ID.",
                args_schema=ClaimLookup,
            ),
            StructuredTool.from_function(
                func=self.submit_claim,
                name=TOOL_SUBMIT_CLAIM,
                description=(
                    "File a NEW insurance claim. Only call once the user has supplied policy "
                    "number, claim type, amount and description and has asked to submit."
                ),
                args_schema=ClaimSubmission,
            ),
        ]
