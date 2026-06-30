# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

A Stash plugin suite that prepares a media library for Plex: renames files, generates XBMC-compatible `.nfo` metadata, crops performer portraits, and provides session-scoped rollback.

## Commands

```bash
# Install dependencies
uv sync

# Run a script manually (simulating Stash invocation)
echo '{"server_connection":{"Scheme":"http","Host":"localhost","Port":9999,"SessionCookie":{"Name":"session","Value":"<token>"}},"args":{"studio":"","dry_run":true}}' | uv run python stash_rename.py

# Lint / format — use uvx, NOT `uv run`, on Alpine/musl (see Environment note)
uvx ruff@0.9.0 check .
uvx ruff@0.9.0 format .
```

There is no automated test suite. Testing is done manually via Stash UI with `dry_run=true` on ≤5 scenes, then verifying `stash_plex_migration.log`.

### Environment gotcha (Alpine/musl)

`uv sync`/`uv run` fail here — `opencv-python-headless` has no musl wheel. Run Python tooling via `uvx` (isolated env) or in the glibc `Ubuntu` WSL distro. ruff is configured in `pyproject.toml` (`[tool.ruff]`: `E,F,I,UP,B`, line-length 100); a `PostToolUse` hook (`.claude/hooks/ruff-fix.sh`) auto-fixes/formats edited `*.py` via `uvx`. Existing code is not yet ruff-clean (~103 findings) — the hook only touches files you edit.

## Architecture

### Plugin I/O contract (critical)

Every script is invoked by Stash which pipes a JSON object to `stdin`. The script must print exactly one JSON object to `stdout` on completion:

```json
{"output": "Done. N processed.", "error": null}
```

All logging goes to `stderr` and `stash_plex_migration.log`. **stdout purity is mandatory** — any non-JSON stdout will break the Stash plugin interface.

### Module roles

| File | Role |
|------|------|
| `plex_exporter.yml` | Stash plugin task definitions and UI settings; drives all other scripts |
| `stash_rename.py` | GraphQL → sanitize title → rename files to `Title (Year).ext` |
| `stash_nfo_generator.py` | GraphQL → write XBMC `<movie>` XML with studio hierarchy, performers, and thumbs |
| `stash_nfo_assets.py` | Download poster/fanart/logo/square images alongside each scene |
| `stash_face_cropper.py` | Library only (no `main()`); OpenCV face detection → 500×500 crop, with center-crop fallback |
| `stash_plex_actor_processor.py` | Batches all performers, calls `stash_face_cropper`, distributes to `PER_SCENE` (`.actor/` subfolders) or `CENTRAL` directory |
| `stash_plex_rollback.py` | Parses `stash_plex_migration.log` for the latest `[SESSION]` block, reverses `RENAME_SUCCESS` and `NFO_CREATED` entries |
| `main.py` | uv scaffold stub — not used by Stash |

### Key design decisions

**Studio hierarchy → Plex collections.** `get_studio_hierarchy()` in `stash_nfo_generator.py` walks `parent_studio` chain (up to 3 levels deep in the GraphQL query). The leaf studio becomes `<studio>`; every studio in the chain becomes a `<collection>`.

**Log-driven rollback.** The rollback script has no database — it parses structured `LOG_TYPE:` lines from `stash_plex_migration.log`. Each write/rename emits a parseable line. Rollback targets only the most recent `[SESSION] start` block.

**`file://` thumbs in NFO.** `stash_nfo_generator.py` writes `file://` paths for performer thumbs, not `http://`. This is a known gap. Do not change `file://` to `http://` without also implementing the planned HTTP actor image server.

**OpenCV is optional.** `stash_nfo_generator.py` wraps the `stash_face_cropper` import in a try/except; missing OpenCV falls back to the original image path. `stash_plex_actor_processor.py` hard-exits if the cropper is missing.

**GraphQL pagination.** All `findScenes`/`findPerformers` calls loop until `len(results) < per_page`. Never assume a single GraphQL response contains all data.

### Dry-run default

All destructive operations — including file renames, NFO writes, image downloads, and actor image copies — must check `dry_run` before touching disk. This applies to **every script**, including `stash_plex_actor_processor.py`. Dry-run logs `LOG_TYPE:*_DRY_RUN` lines. Never change any default from `dry_run=true`. Any new script or function that writes or moves files must accept and honour `dry_run`.

### Workflow ordering (important)

After running **Rename Scenes**, the user must trigger **Stash UI → Tasks → Scan Library** before running NFO or asset steps. Stash's file-path index must be updated to reflect the renamed files.

## Active work

- Current in-progress branch: `Incorporating-Galleries` (gallery/poster asset support via `stash_nfo_assets.py`)
- See `ROADMAP.md` for done/in-progress/next-up; update its checkboxes when completing tasks
- See `AGENTS.md` for deeper architecture notes and `DRY_RUN_CHECKLIST.md` for the manual testing protocol
