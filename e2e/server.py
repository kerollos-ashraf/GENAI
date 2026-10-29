"""Runs the real backend with the rule-based LLM, hashing embeddings and a fake transcriber,
on a private copy of the data. Used by the e2e suite and handy for UI work without an API key:

    python e2e/server.py --port 8000 --data-dir /tmp/omnicare-e2e
"""

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "backend"), str(Path(__file__).resolve().parent)]

import uvicorn  # noqa: E402
from fake_llm import RuleBasedLLM  # noqa: E402

from app.config import DATA_DIR, Settings  # noqa: E402
from app.domain.models import Transcript  # noqa: E402
from app.main import create_app  # noqa: E402

SPOKEN_QUESTION = "Are floods covered?"


class FakeTranscriber:
    """Whatever is recorded, 'hears' the same question, so voice tests are deterministic."""

    def transcribe(self, audio: bytes, filename: str) -> Transcript:
        return Transcript(text=SPOKEN_QUESTION, language="en", duration_seconds=1.0)


def build_app(data_dir: Path):
    data_dir.mkdir(parents=True, exist_ok=True)
    policies = data_dir / "policies"
    if not policies.exists():
        policies.mkdir()
        shutil.copy(DATA_DIR / "policies" / "sample_policy.md", policies)
    claims = data_dir / "mock_claims.json"
    if not claims.exists():
        shutil.copy(DATA_DIR / "mock_claims.seed.json", claims)
    settings = Settings(
        _env_file=None,
        embeddings_provider="hashing",
        policies_dir=policies,
        chroma_dir=None,
        claims_path=claims,
        kb_watch_interval=0,
        kb_collection_name="e2e",
    )
    return create_app(settings, llm=RuleBasedLLM(), transcriber=FakeTranscriber())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    uvicorn.run(build_app(args.data_dir), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
