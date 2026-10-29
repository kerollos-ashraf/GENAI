"""PreToolUse hook: block edits to secrets and to the pristine seed data."""

import json
import sys
from pathlib import Path

data = json.load(sys.stdin)
path = Path((data.get("tool_input") or {}).get("file_path", ""))

if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
    print(
        "Blocked: never write to .env files (they hold API keys). Edit .env.example instead.",
        file=sys.stderr,
    )
    sys.exit(2)
if path.name == "mock_claims.seed.json":
    print(
        "Blocked: mock_claims.seed.json is the pristine test fixture. Edit mock_claims.json instead.",
        file=sys.stderr,
    )
    sys.exit(2)
