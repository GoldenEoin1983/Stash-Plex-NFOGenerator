# Project Context & Architecture Guide for AI Agents

## 📍 Current status

| Item | State |
|------|--------|
| **Stable core (v1.0)** | `master` — rename, NFO, actors, rollback |
| **Active work** | Branch `Incorporating-Galleries` — `stash_nfo_assets.py` (posters/gallery assets) |
| **Tracker** | See [`ROADMAP.md`](ROADMAP.md) for done / in-progress / next-up (update when completing tasks) |
| **Rules** | See `Stashapp Library Migration to Plex - Project Context Document.md` for MUST/SHOULD constraints |

**Start here:** Read `ROADMAP.md` before making changes. Do not skip dry-run testing on ≤5 scenes.

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
| `stash_nfo_assets.py` | Download Plex local assets (poster, fanart, logo, square) + optional scan trigger | Python, `requests`, GraphQL |

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
  <premiered>YYYY-MM-DD</premiered>  <!-- Plex preferred date field -->
  <releasedate>YYYY-MM-DD</releasedate>  <!-- XBMC compat -->
  <uniqueid type="stash" default="true">scene_id</uniqueid>  <!-- Stable GUID for watch-state -->
  <studio>Primary Studio</studio>
  <collection>Studio 1</collection>
  <collection>Studio 2</collection>
  <actor>
    <name>Performer</name>
    <role>Actor</role>
    <thumb>http://localhost:PORT/actors/Performer_plex.jpg</thumb>
    <url>https://...</url>
  </actor>
</movie>
```

> ⚠️ `<thumb>` target is `http://` paths. v1 code currently emits `file://` — this is a known gap. Do not "fix" `file://` → `http://` without also implementing the actor HTTP server.

### Plugin stdin JSON Shape

Each script reads this from `sys.stdin` on invocation by Stash:

```json
{
  "server_connection": {
    "Scheme": "http",
    "Host": "localhost",
    "Port": 9999,
    "SessionCookie": { "Name": "session", "Value": "<token>" }
  },
  "args": {
    "studio": "StudioName",
    "dry_run": true,
    "actor_save_mode": "PER_SCENE",
    "actor_central_dir": "",
    "apply": false
  }
}
```

### Data Flow

```
plex_exporter.yml (Stash UI)
        │
        ├── Rename Scenes → stash_rename.py
        │       └── GraphQL: findScenes → sanitize title → rename file → log LOG_TYPE:RENAME_*
        │
        ├── Generate NFOs → stash_nfo_generator.py
        │       ├── GraphQL: findScenes (with studio/performer/file data)
        │       ├── get_studio_hierarchy() → <studio> + <collection> elements
        │       ├── get_performer_image() → stash_face_cropper.py (optional, inline crop)
        │       └── write_nfo() → movie.nfo → log LOG_TYPE:NFO_*
        │
        ├── Process Actor Images → stash_plex_actor_processor.py
        │       ├── GraphQL: findPerformers (paginated)
        │       ├── stash_face_cropper.py → 500×500 face crop → *_plex.jpg
        │       └── distribute: PER_SCENE (.actors/ folder) or CENTRAL (shared dir)
        │
        └── Rollback Last Run → stash_plex_rollback.py
                └── Parse stash_plex_migration.log → latest [SESSION] block → reverse actions
```

## 📊 Current State

| Module | Status | Notes |
|--------|--------|-------|
| `stash_nfo_generator.py` | ✅ Working | `<premiered>` + `<uniqueid type="stash">` added; `file://` thumbs → `http://` planned |
| `stash_rename.py` | ✅ Working | Plex-safe naming, collision handling |
| `stash_face_cropper.py` | ✅ Working | OpenCV face detect + center-crop fallback |
| `stash_plex_actor_processor.py` | ✅ Working | PER_SCENE and CENTRAL modes |
| `stash_plex_rollback.py` | ✅ Working | Session-scoped log parsing |
| `main.py` | ⚠️ Stub | Placeholder only — not wired to plugin tasks |
| HTTP actor image server | 🔲 Planned v2 | Required before `http://` thumbs can be used |
| Auto-scan mutation post-rename | 🔲 Planned v2 | |
| Tag/genre mapping | 🔲 Planned v2 | Prefer tag names over IDs |
| Progress UI for long tasks | 🔲 Planned v2 | |

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