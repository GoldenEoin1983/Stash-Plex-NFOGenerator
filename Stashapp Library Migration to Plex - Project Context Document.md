# 📜 PROJECT RULES: Stash → Plex Exporter

## 1️⃣ CORE PRINCIPLES

MUST default to safety: All destructive operations run in dry-run mode until explicitly overridden.
MUST preserve reversibility: Every state-changing action must be loggable and rollback-capable.
MUST prioritize portability: Avoid host-specific paths; validate Docker/volume mappings explicitly.
SHOULD favor modularity: Keep rename, NFO, cropping, actor distribution, and rollback as separate, independently testable components.
MAY defer complex features to v2 if they break v1 contracts or require external services.

## 2️⃣ PLUGIN I/O & EXECUTION CONTRACT

MUST accept configuration via stdin JSON matching Stash's plugin spec (server_connection + args).
MUST output exactly one valid JSON object to stdout: {"output": "status message", "error": null}. No debug prints, no logs, no extra text.
MUST route all human-readable logs to stderr (for Stash UI) AND stash_plex_migration.log (for persistence).
MUST resolve paths using {pluginDir} or os.path.dirname(__file__); never hardcode absolute paths.
SHOULD support both Stash UI execution and standalone CLI fallback via argparse or stdin detection.

## 3️⃣ SAFETY & DATA INTEGRITY

MUST implement session-scoped rollback: Only reverse actions from the most recent [SESSION] start block.
MUST handle filename collisions gracefully: Append _1, _2, etc., and log the resolution.
MUST validate all target paths before file operations. Fail loudly with clear error messages if paths don't exist or lack permissions.
MUST never break Stash's internal tracking without documenting the required recovery step (Tasks → Scan Library).
SHOULD skip scenes with multiple files; log a warning and process files[0] only.
SHOULD fall back to center-crop if OpenCV face detection fails or haarcascade_frontalface_default.xml is missing.

## 4️⃣ API & INTEGRATION RULES

MUST authenticate via SessionCookie from server_connection (or ApiKey header if configured). Follow Stash API Docs.
MUST paginate all GraphQL queries: Loop until len(results) < per_page. Never assume a single response contains all data.
MUST generate strict XBMC-compatible NFO files. XML must be well-formed, encoded as UTF-8, and named exactly movie.nfo.
MUST follow Plex naming conventions: Title (Year).ext. Sanitize <>:"/\|?* → _. Fall back to Untitled/Unknown if metadata is missing.
SHOULD flatten studio hierarchies recursively: First studio → <studio>, all studios → <collection>.
SHOULD use file:// URLs for actor thumbnails in v1. Plan http:// server for v2.

## 5️⃣ CODE & ARCHITECTURE STANDARDS

MUST use Python 3.9+ and follow PEP 8. Type hints are encouraged but not mandatory.
MUST use Python's built-in logging module. Configure once per module with FileHandler + StreamHandler.
MUST keep dependencies minimal: requests and opencv-python-headless only. Document any additions in requirements.txt.
SHOULD wrap external calls (GraphQL, file I/O, OpenCV) in try/except with explicit error logging. Continue processing on non-fatal failures.
MUST never mutate global state. Pass configuration explicitly via function arguments or stdin args.
SHOULD cache reusable data (e.g., performer images, studio IDs) to reduce API calls and disk I/O.

## 6️⃣ TESTING & VALIDATION PROTOCOL

MUST run all new logic with dry_run=true on ≤5 scenes from a single studio before batch execution.
MUST verify stash_plex_migration.log contains parseable LOG_TYPE:* entries matching rollback regex patterns.
MUST validate generated NFO XML against Plex's local metadata scanner before declaring success.
MUST test rollback dry-run → apply → verify original state restoration.
SHOULD confirm Docker path resolution matches Stash's Settings → Libraries configuration before writing files.

## 7️⃣ DOCUMENTATION & VERSIONING

MUST maintain AGENTS.md / project context document with architecture, contracts, and known limitations.
MUST update README.md workflow steps whenever plugin settings or execution order changes.
MUST bump version in plex_exporter.yml on breaking changes or new task additions.
SHOULD log architectural decisions (e.g., file:// vs http:// actor paths, session-scoped rollback) in context docs.
MUST keep the v2 backlog explicit: HTTP actor server, auto-scan mutation, progress UI, image/gallery support.

## 🛑 HARD CONSTRAINTS (NON-NEGOTIABLE)

stdout contains ONLY the final JSON output. Nothing else.
Rollback NEVER touches actions outside the latest [SESSION] block.
No file is renamed, moved, or deleted without a corresponding dry-run log entry.
NFO files are never overwritten without explicit --apply or UI confirmation.
OpenCV is optional. The project MUST function (with degraded actor images) if it's unavailable.

## 💡 How to Use These Rules

Paste this into RULES.md at the root of the repo.
Reference it in PR reviews, AI prompts, and commit messages.
Enforce via CI linters (PEP 8, JSON validation) and manual dry-run checks.
Treat MUST as breaking if violated; SHOULD/MAY as guidelines for optimization.