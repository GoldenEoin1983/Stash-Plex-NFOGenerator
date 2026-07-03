#!/usr/bin/env bash
# PostToolUse hook: auto-lint + format the just-edited Python file.
#
# Reads the hook payload as JSON on stdin, pulls tool_input.file_path, and runs
# ruff (via uvx, pinned) only when the edited file is a *.py. No-ops otherwise so
# editing YAML/Markdown/etc. is untouched. ruff reads [tool.ruff] from pyproject.toml.
#
# Uses `uvx ruff` rather than `uv run ruff` on purpose: this project's deps
# (opencv-python-headless) have no musl/Alpine wheels, so `uv sync`/`uv run`
# can't build the project env here. uvx runs ruff in an isolated env.
set -euo pipefail

RUFF_VERSION="0.9.0"

# Extract the edited file path from the hook JSON on stdin.
file_path="$(python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print((data.get("tool_input") or {}).get("file_path", ""))
' || true)"

# Only act on Python files that still exist.
case "$file_path" in
  *.py) ;;
  *) exit 0 ;;
esac
[ -f "$file_path" ] || exit 0

# --fix applies safe lint fixes; format normalizes style. Non-fatal: never block edits.
uvx "ruff@${RUFF_VERSION}" check --fix "$file_path" >&2 2>&1 || true
uvx "ruff@${RUFF_VERSION}" format "$file_path" >&2 2>&1 || true

exit 0
