# Project Context & Architecture Guide for AI Agents

## 🎯 Purpose
Automate Stash-to-Plex migration: rename files, generate XBMC-compatible `.nfo` metadata, crop performer faces to 500x500, and provide safe, session-scoped rollback capabilities.

## 🏗️ Architecture Overview
| Component | Role | Tech |
|-----------|------|------|
| `plex_exporter.yml` | Stash plugin task definitions & UI settings | YAML (Stash Spec) |
| `stash_rename.py` | Query Stash GraphQL → sanitize → rename files | Python, `requests`, `logging` |
| `stash_nfo_generator.py` | Query scenes/performers → write XBMC XML | Python, `xml.etree.ElementTree` |
| `stash_face_cropper.py` | OpenCV face detection → square crop → resize | Python, `opencv-python-headless` |
| `stash_plex_actor_processor.py` | Batch performers → distribute images | Python, `shutil`, GraphQL pagination |
| `stash_plex_rollback.py` | Parse structured log → reverse actions | Python, `re`, `logging` |

## 🔑 Core Contracts

### Stash Plugin I/O

- **Stash I/O:** JSON via `stdin`, output `{"output":"...","error":null}` to `stdout`
- **Logging:** `stderr` + `stash_plex_migration.log`
- **Auth:** `SessionCookie` value as cookie domain host
- **Pagination:** Loop until `len(results) < per_page`
- **NFO Schema:** XBMC `<movie>` with `<studio>`, `<collection>`, `<actor>` + `<thumb>`
- **Safety:** Dry-run default, session isolation, collision handling, Docker path validation

### GraphQL Pagination

- Use `page`/`per_page` loop until `len(results) < per_page`
- Never assume `findScenes` returns all data at once

### NFO Schema (Plex XBMC)

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<movie>
  <title>...</title>
  <year>YYYY</year>
  <releasedate>YYYY-MM-DD</releasedate>
  <studio>Primary Studio</studio>
  <collection>Studio 1</collection>
  <collection>Studio 2</collection>
  <actor>
    <name>Performer</name>
    <role>Actor</role>
    <thumb>file:///path/to/Performer_plex.jpg</thumb>
    <url>https://...</url>
  </actor>
</movie>
```

## ⚠️ Safety Constraints

Dry-Run Default: All destructive operations must default to preview mode
Session Isolation: Rollback only targets the latest [SESSION] start block
Collision Handling: Auto-append _1, _2 if target exists
Docker Paths: Central actor dir must be volume-mounted & match Stash Libraries
Stdout Purity: Only print valid JSON to stdout. All logs to stderr

## 🛠️ Development Guidelines

- Use standard `logging` module; configure once per module
- Handle missing data gracefully (`"Unknown"`, skip, or warn)
- Never hardcode paths; use `os.path` and `stdin` args
- Keep OpenCV optional; fallback to center-crop
- Validate all external paths before file operations
- Test with `dry_run=true` on ≤5 scenes before batch execution

## 🔄 Extension Points

- HTTP Actor Image Server (`http://` paths)
- Auto-Scan Mutation post-rename
- Images/Galleries support
- Performer bios/tags mapping
- Progress UI for long tasks

## 📦 Dependencies

requests>=2.28.0
opencv-python-headless>=4.8.0

## 🧪 Testing Protocol

Run with dry_run=true on small studio (≤5 scenes)
Verify stash_plex_migration.log structure
Check NFO XML validity & Plex ingestion
Test rollback dry-run → apply → verify original state
Confirm Docker path validation fails safely