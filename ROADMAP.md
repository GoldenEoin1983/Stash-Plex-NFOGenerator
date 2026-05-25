# Project Roadmap

> **For humans:** Check off items as you complete them. Update "In progress" when you start something new.  
> **For AI agents:** Read this file at the start of every session. Do not start work on "Next up" items unless the user asks or "In progress" is empty and the task is unblocked.

Last updated: 2026-05-20

---

## Purpose (one sentence)

Automate Stash → Plex migration: rename files, generate local metadata (NFO + images), crop performer portraits, and support safe rollback — always dry-run first.

---

## Current phase

**v1.1 — Gallery & poster assets** (branch: `Incorporating-Galleries`)

Core rename/NFO/actor/rollback tools exist on `master`. Active work adds Plex-local assets (`poster`, `background`, `logo`, `square`) via `stash_nfo_assets.py`.

---

## Done

- [x] Stash plugin shell (`plex_exporter.yml`) with dry-run defaults
- [x] Scene file renaming (`stash_rename.py`)
- [x] XBMC NFO generation (`stash_nfo_generator.py`)
- [x] Performer face crop + distribution (`stash_face_cropper.py`, `stash_plex_actor_processor.py`)
- [x] Session-scoped rollback (`stash_plex_rollback.py`)
- [x] Agent architecture guide (`AGENTS.md`)
- [x] Human README + project rules doc
- [x] Git repo on GitHub with `master` + feature branches
- [x] Draft poster/gallery asset script (`stash_nfo_assets.py`)
- [x] Wire **Generate Plex Assets** task in `plex_exporter.yml` (v1.1)

---

## In progress

- [ ] **Gallery/poster support** — dry-run test on ≤5 scenes using [`DRY_RUN_CHECKLIST.md`](DRY_RUN_CHECKLIST.md), then merge branch to `master`

---

## Next up (recommended order)

### Codebase

1. [ ] Dry-run test the full pipeline on one small studio (≤5 scenes) — follow [`DRY_RUN_CHECKLIST.md`](DRY_RUN_CHECKLIST.md)
3. [ ] Verify Plex ingests `movie.nfo` + poster/background files from a single test folder
4. [ ] Merge `Incorporating-Galleries` → `master` via pull request when tests pass
5. [ ] Remove or repurpose placeholder `main.py` (uv scaffold only; not used by Stash plugin)

### Repository & AI workflow

6. [ ] Open GitHub **Issues** for each backlog item you care about (templates below)
7. [ ] Tag releases on `master` after each stable milestone (`v1.0`, `v1.1`, …)
8. [ ] Add a minimal test script or `scripts/dry_run_check.sh` that validates NFO XML shape (optional but high value)

---

## Backlog (v2+)

From `AGENTS.md` and design notes — not started unless moved to "Next up":

- [ ] HTTP actor image server (`http://` thumb paths instead of `file://`)
- [ ] Auto-scan mutation after rename (partially explored in `stash_nfo_assets.py`)
- [ ] Performer bios / tags in NFO
- [ ] Progress UI for long Stash tasks
- [ ] CI: lint Python + validate `plex_exporter.yml` on push

---

## How to work with AI (Cursor)

| When you want… | Say something like… |
|----------------|---------------------|
| Continue current feature | "Continue gallery asset work on `Incorporating-Galleries`; check ROADMAP in progress." |
| Safe change only | "Dry-run only; don't rename files. Follow AGENTS.md safety rules." |
| Understand code | "Explain how `stash_nfo_generator.py` builds `<collection>` tags." |
| Plan before coding | "Update ROADMAP next-up; don't edit code yet." |
| Finish a milestone | "Mark ROADMAP items done and draft a PR summary." |

**Files agents should read first:** `ROADMAP.md` → `AGENTS.md` → `README.md` → relevant `stash_*.py`

**Files agents should update when finishing work:** checkboxes in this file, `AGENTS.md` "Current status" if architecture changes, `README.md` if user-facing steps change.

---

## Git workflow (beginner cheat sheet)

```text
master          ← stable, tested code
  └── feature-branch   ← one feature per branch (you are here: Incorporating-Galleries)
```

| Step | Command / action |
|------|------------------|
| See what changed | `git status` / `git diff` |
| Save work | `git add <files>` then `git commit -m "short description"` |
| Push to GitHub | `git push` |
| Merge safely | Open a **Pull Request** on GitHub; review diff; merge when happy |
| Start new feature | `git checkout master` → `git pull` → `git checkout -b my-new-feature` |

**Rule of thumb:** Never run destructive Stash tasks with dry-run off until you've previewed the same studio in dry-run and checked `stash_plex_migration.log`.

---

## GitHub Issues (copy as templates)

**Bug**
```
**What happened:**
**What I expected:**
**Dry-run:** yes/no
**Log excerpt:** (from stash_plex_migration.log)
```

**Feature**
```
**Goal:**
**Acceptance criteria:**
- [ ] Dry-run works
- [ ] ROADMAP updated
- [ ] README updated if user steps change
```

---

## Session log (optional — you fill this in)

Brief notes after each coding session help future-you and AI:

| Date | What I did | Next time |
|------|------------|-----------|
| 2026-05-08 | Added `stash_nfo_assets.py`, `images.md` on branch | Wire plugin task + dry-run test |
| 2026-05-20 | Wired **Generate Plex Assets** in `plex_exporter.yml` v1.1 | Run `DRY_RUN_CHECKLIST.md` in Stash |
