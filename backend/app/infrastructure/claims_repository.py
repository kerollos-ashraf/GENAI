"""JSON-file implementation of the `ClaimsRepository` port (Repository pattern)."""

import json
import os
import secrets
import tempfile
import threading
from pathlib import Path

from app.domain.claims import Claim, ClaimLookup, ClaimNotFoundError, ClaimStatus, ClaimSubmission


class JsonClaimsRepository:
    """Stores claims in a JSON array. A lock plus write-to-temp-then-`os.replace` keeps
    concurrent writes safe and the file never half-written."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("[]", encoding="utf-8")

    def get(self, claim_id: str) -> Claim:
        claim_id = ClaimLookup(claim_id=claim_id).claim_id
        with self._lock:
            record = next((r for r in self._read() if r.get("claim_id") == claim_id), None)
        if record is None:
            raise ClaimNotFoundError(claim_id)
        return Claim(**record)

    def submit(self, submission: ClaimSubmission) -> Claim:
        with self._lock:
            records = self._read()
            claim = Claim(
                claim_id=self._new_claim_id({r.get("claim_id") for r in records}),
                status=ClaimStatus.SUBMITTED,
                **submission.model_dump(),
            )
            records.append(claim.model_dump())
            self._write(records)
        return claim

    def _read(self) -> list[dict]:
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write(self, records: list[dict]) -> None:
        fd, tmp = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(records, fh, indent=2)
            fh.write("\n")
        os.replace(tmp, self._path)

    @staticmethod
    def _new_claim_id(existing: set[str]) -> str:
        while True:
            claim_id = f"CLM-{secrets.randbelow(900_000) + 100_000}"
            if claim_id not in existing:
                return claim_id
