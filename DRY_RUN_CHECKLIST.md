# Dry-Run Checklist (v1.1)

Use this the first time you run the plugin on a real library. **Do not turn off Dry Run until every step passes.**

Pick one studio with **≤5 scenes** and note its exact name for the Studio Filter.

---

## Before you start

- [ ] Plugin files are in your Stash plugins folder (or Docker volume mount)
- [ ] Stash → **Settings → Plugins → Reload Plugins**
- [ ] **Generate Plex Assets** appears on the **Tasks** page
- [ ] Python deps installed: `requests` (and `opencv-python-headless` if using actor crop)
- [ ] You know where `stash_plex_migration.log` is written (plugin working directory / Stash config path)

### Plugin settings (leave these for dry-run)

| Setting | Value |
|---------|--------|
| Studio Filter | Your test studio name (exact match) |
| Dry Run | **ON** (checked / true) |
| Execute Rollback | **OFF** |

---

## Step 1 — Rename Scenes (dry-run)

- [ ] Run task: **Rename Scenes**
- [ ] Task finishes with JSON success in Stash (no error in UI)
- [ ] Open `stash_plex_migration.log`
- [ ] See `[SESSION] start` with `dry_run=True`
- [ ] See `LOG_TYPE:RENAME_DRY_RUN` (or equivalent rename preview lines) — **no** `RENAME_APPLIED` yet
- [ ] Scene count looks right (≤5 for your test studio)

**If this fails:** fix studio name spelling or check Stash GraphQL connectivity before continuing.

---

## Step 2 — Scan Library (manual — even in dry-run)

Renames are preview-only in dry-run, but when you later apply renames, Stash needs a scan. For a **full apply** test you will need this; skip only if you have not renamed anything yet and are only testing NFO/assets on existing paths.

- [ ] Stash → **Tasks → Scan Library**
- [ ] Leave **Generate Fingerprints** enabled
- [ ] Wait until scan completes

---

## Step 3 — Generate NFOs (dry-run)

- [ ] Run task: **Generate NFOs**
- [ ] Log shows `LOG_TYPE:NFO_DRY_RUN` per scene (not `NFO_CREATED` yet)
- [ ] `[SESSION] end` reports a sensible `processed=` count

---

## Step 4 — Generate Plex Assets (dry-run)

- [ ] Run task: **Generate Plex Assets**
- [ ] Log shows `LOG_TYPE:IMAGE_DRY_RUN` for images that would be downloaded
- [ ] Log shows `LOG_TYPE:NFO_ASSETS_DRY_RUN` where `movie.nfo` already exists (or `NFO_MISSING` warnings where it does not — fix by running NFO step on those paths first)
- [ ] Log shows `LOG_TYPE:SCAN_DRY_RUN` with a list of directories (scan is **not** fired in dry-run)
- [ ] No new `poster.jpg` / `fanart.jpg` / `logo.png` / `square.jpg` on disk yet

**Expected dry-run log snippets:**

```text
| [SESSION] start | dry_run=True | studio=YourStudio | auto_scan=enabled
LOG_TYPE:IMAGE_DRY_RUN | URL:... | DEST:.../fanart.jpg
LOG_TYPE:NFO_ASSETS_DRY_RUN | PATH:.../movie.nfo | ASSETS:{...}
LOG_TYPE:SCAN_DRY_RUN | PATHS:['...']
| [SESSION] end | processed=N | skipped=0 | scan_paths=N
```

---

## Step 5 — Process Actor Images (dry-run)

Actor task does not use the global Dry Run setting today — it writes crops when run. For a **first** library test, you may **skip** this step until rename/NFO/assets apply cleanly.

- [ ] (Optional) Run **Process Actor Images** on the same studio if you accept image writes
- [ ] Or skip until after Step 6 apply pass

---

## Step 6 — Apply for real (one studio only)

Only after Steps 1–4 look correct:

- [ ] Set **Dry Run** to **OFF**
- [ ] Run **Rename Scenes** → confirm `LOG_TYPE:RENAME_APPLIED` (or equivalent)
- [ ] **Scan Library** in Stash (required after rename)
- [ ] Run **Generate NFOs** → confirm `LOG_TYPE:NFO_CREATED`
- [ ] Run **Generate Plex Assets** → confirm `LOG_TYPE:IMAGE_DOWNLOADED` and `LOG_TYPE:NFO_ASSETS_UPDATED`
- [ ] Confirm `LOG_TYPE:SCAN_TRIGGERED` (optional auto partial scan)
- [ ] Spot-check one scene folder on disk:

```text
Title (Year).ext
movie.nfo
poster.jpg      (if gallery linked)
fanart.jpg      (if scene cover exists)
logo.png        (if studio image exists)
square.jpg      (if scene cover exists)
```

---

## Step 7 — Plex verification

- [ ] Plex library uses **Plex Movie** agent with **prefer local metadata**
- [ ] Point library at the same folder Stash uses
- [ ] **Scan library files** on one test folder
- [ ] Poster/metadata appear without manual entry

---

## Step 8 — Rollback rehearsal (optional)

- [ ] **Execute Rollback** = OFF → run **Rollback Last Run** (preview)
- [ ] Log shows what would be reversed
- [ ] Only set **Execute Rollback** ON if you intend to undo the **last session**

---

## Done — update tracking

- [ ] Check off items in [`ROADMAP.md`](ROADMAP.md) under **Done**
- [ ] Add a row to the **Session log** table in ROADMAP
- [ ] Open a PR: `Incorporating-Galleries` → `master` when satisfied

---

## Quick troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| `NFO_MISSING` for every scene | Run **Generate NFOs** before assets (or paths don't match renamed files) |
| `SKIP_MULTI_FILE` | Scene has multiple files; only first file path is used by design |
| No images in dry-run | Expected — look for `IMAGE_DRY_RUN`, not files on disk |
| Task missing in Stash | Reload plugins; confirm `plex_exporter.yml` is in plugin folder |
| Wrong scene count | Studio Filter must **exactly** match Stash studio name (case-insensitive in assets script) |
