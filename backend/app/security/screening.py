"""Indirect prompt-injection screening for documents.

One rule, shared by every way a document enters the knowledge base - API uploads
(`DocumentService`) and files dropped into the policies folder (`KnowledgeBase.sync`) - so
poisoned text never reaches the index, and from there the model, as "policy".
"""

from collections.abc import Iterable

from app.domain.models import Section
from app.domain.ports import InputGuard


def injection_reason(sections: Iterable[Section], guard: InputGuard) -> str | None:
    """Why the document must be rejected, or None if every section is clean."""
    for section in sections:
        verdict = guard.check(f"{section.label}\n{section.text}")
        if not verdict.allowed:
            return (
                f"Rejected: section '{section.label}' looks like a prompt-injection attempt "
                f"({verdict.reason})"
            )
    return None
