"""PostToolUse hook: auto-format and lint-fix any Python file Claude edits.

Fails soft: if ruff isn't installed the edit still goes through.
"""

import json
import subprocess
import sys

data = json.load(sys.stdin)
path = (data.get("tool_input") or {}).get("file_path", "")
if not path.endswith(".py"):
    sys.exit(0)

for args in (["format", path], ["check", "--fix", "--quiet", path]):
    try:
        res = subprocess.run(
            [sys.executable, "-m", "ruff", *args], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        sys.exit(0)
    if "No module named ruff" in res.stderr:
        sys.exit(0)
    if args[0] == "check" and res.returncode != 0:
        # Exit 2 feeds the remaining lint errors back to Claude so it fixes them.
        print(f"ruff found issues in {path}:\n{res.stdout}{res.stderr}", file=sys.stderr)
        sys.exit(2)
