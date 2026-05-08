# README.md

# Stash to Plex Exporter

A modular Stash plugin suite that prepares your media library for Plex by renaming files to Plex-compliant conventions, generating XBMC-compatible `.nfo` metadata, and intelligently cropping performer portraits into Plex-optimized headshots.

> ⚠️ **Status:** v1.0 Stable | Safe Dry-Run Default | Session-Scoped Rollback

---

## 🎯 Overview

Migrate Stash-managed scenes to Plex Media Server with zero manual metadata entry. This project handles:
1. **File Renaming** → `Title (Year).ext`
2. **NFO Generation** → `<movie>` XML with studios, collections, performers, and thumbnails
3. **Actor Face Cropping** → OpenCV face detection → 500x500 square crops
4. **Safe Rollback** → Session-isolated undo from persistent logs

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Plex Naming** | `Title (Year).ext` with safe character sanitization & collision handling |
| **XBMC NFO Spec** | Strict `<title>`, `<year>`, `<releasedate>`, `<studio>`, `<collection>`, `<actor>` structure |
| **Studio Hierarchy** | Auto-flattens `Studio → Parent → Network` into Plex collections |
| **Performer Integration** | Extracts names, URLs, and auto-crops face images for Plex actor view |
| **Actor Distribution** | `PER_SCENE` (`.actor/` folders) or `CENTRAL` (shared directory) modes |
| **Dry-Run Default** | Preview all changes before touching disk |
| **Session Rollback** | Reverse the last run using structured log parsing |
| **Stash Plugin Native** | Follows `stdin`/`stdout` JSON contract; integrates with Stash Tasks UI |

---

## 📦 Project Structure

stash-plex-exporter/
├── README.md # Project documentation
├── AGENTS.md # AI/LLM context & architecture guide
├── plex_exporter.yml # Stash plugin configuration
├── requirements.txt # Python dependencies
├── .gitignore # Standard exclusions
├── stash_rename.py # Scene file renaming logic
├── stash_nfo_generator.py # XBMC NFO generation with performer data
├── stash_face_cropper.py # OpenCV face detection & 500x500 cropping
├── stash_plex_actor_processor.py # Batch actor processing & distribution
└── stash_plex_rollback.py # Session-scoped undo tool

---

## 🛠️ Prerequisites

- **Stash** v0.20+ (local or network-accessible)
- **Python 3.9+**
- **Plex Media Server**
- Required Packages:

```bash
  pip install requests opencv-python-headless
```

## 📥 Installation

Clone or download this repository:
Place the contents into your Stash plugins directory:

Linux/macOS: ~/.stash/plugins/
Windows: %APPDATA%\.stash\plugins\
Docker: Map to your container's /root/.stash/plugins/

In Stash UI: Settings → Plugins → Reload Plugins
Verify tasks appear on the Tasks page.

## 🚀 Usage Workflow

### 1️⃣ Configure UI Settings

| Setting | Type | Default Notes |
|---------|------|--------|
| Studio Filter | STRING | (empty) | Exact match. Leave blank for all scenes. |
| Dry Run | BOOLEAN | true | Always true first. Preview only. |
| Actor Save Mode | STRING | PER_SCENE PER_SCENE or CENTRAL |
| Central Actor Folder | STRING | (empty) | Required if mode=CENTRAL. Must be Docker-mounted & in Stash Libraries. |
| Execute Rollback | BOOLEAN | false | WARNING: Check to permanently reverse last session. |

### 2️⃣ Execute Safely (Dry Run)

Leave Dry Run: true
Click Rename Scenes → Verify stash_plex_migration.log
Click Generate NFOs → Verify log
Click Process Actor Images → Verify cropping/distribution log

### 3️⃣ Apply Changes

Uncheck Dry Run
Run Rename Scenes
⚠️ CRITICAL: In Stash UI → Tasks → Scan Library (keep "Generate Fingerprints" enabled)
Run Generate NFOs
Run Process Actor Images (if not done in dry-run)
Point Plex to your media folder → Scan → Enjoy local metadata.

### 4️⃣ Rollback (If Needed)

Leave Execute Rollback: false → Click Rollback Last Run (Dry preview)
Check Execute Rollback: true → Click Rollback Last Run (Reverts files & NFOs)

## 📺 Plex Library Setup Checklist

1. Add Library → Type: Movies
2. Scanner → Plex Movie Scanner
3. Agent → Plex Movie (ensure "Use local assets" / "Prefer local metadata" is enabled)
4. Advanced → Check Prefer local metadata
5. Point folder to your renamed library
6. Scan → Plex auto-ingests movie.nfo & actor images

## 📚 References

Stash Plugin Documentation
Stash GraphQL API
Plex Movie Naming Guidelines
Plex Local NFO Metadata