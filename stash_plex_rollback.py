#!/usr/bin/env python3
import os, sys, json, re, logging, argparse

def setup_logger():
    logger = logging.getLogger("stash_plex_rollback")
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stderr)
    ch.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S'))
    logger.addHandler(ch)
    fh = logging.FileHandler("stash_plex_migration.log", encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(fh)
    return logger
log = setup_logger()

RENAME_RE = re.compile(r'LOG_TYPE:RENAME_SUCCESS \| ID:(\d+) \| OLD:(.+?) \| NEW:(.+)$')
NFO_RE    = re.compile(r'LOG_TYPE:NFO_CREATED \| ID:(\d+) \| PATH:(.+)$')
SESSION_RE = re.compile(r'\[SESSION\] start')

def parse_latest_session(log_file="stash_plex_migration.log"):
    if not os.path.exists(log_file):
        log.error(f"Log file not found: {log_file}")
        return []
    actions = []
    session_found = False
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if SESSION_RE.search(line):
                session_found = True
                actions = []
                continue
            if not session_found: continue
            if m := RENAME_RE.search(line):
                actions.append(('RENAME', m.group(1), m.group(2), m.group(3)))
            elif m := NFO_RE.search(line):
                actions.append(('NFO', m.group(1), m.group(2)))
    return actions

def get_args():
    try:
        stdin_data = json.loads(sys.stdin.read())
        args = stdin_data.get("args", {})
        apply_bool = str(args.get("apply", "false")).lower() in ("true", "1", "yes")
        return apply_bool, args.get("log", "stash_plex_migration.log")
    except (json.JSONDecodeError, IOError):
        parser = argparse.ArgumentParser(description="Rollback Stash-to-Plex migration actions")
        parser.add_argument("--log", default="stash_plex_migration.log")
        parser.add_argument("--apply", action="store_true")
        parsed = parser.parse_args()
        return parsed.apply, parsed.log

def main():
    apply_changes, log_file = get_args()
    actions = parse_latest_session(log_file)
    
    if not actions:
        log.warning("No actionable items in latest session. Nothing to rollback.")
        print(json.dumps({"output": "Nothing to rollback.", "error": None}))
        return

    log.info(f"Found {len(actions)} actions. Processing in reverse chronological order...")
    reverted, skipped, errors = 0, 0, 0

    for action in reversed(actions):
        try:
            if action[0] == 'RENAME':
                _, sid, old_p, new_p = action
                if not os.path.exists(new_p):
                    log.warning(f"⏭️ Skip reverse rename (file missing): {new_p}")
                    skipped += 1; continue
                if not apply_changes:
                    log.info(f"🔍 [DRY RUN] Reverse: {new_p} → {old_p}")
                else:
                    os.rename(new_p, old_p)
                    log.info(f"✅ Reversed: {new_p} → {old_p}")
                reverted += 1

            elif action[0] == 'NFO':
                _, sid, nfo_p = action
                if not os.path.exists(nfo_p):
                    log.warning(f"⏭️ Skip NFO delete (file missing): {nfo_p}")
                    skipped += 1; continue
                if not apply_changes:
                    log.info(f"🔍 [DRY RUN] Delete NFO: {nfo_p}")
                else:
                    os.remove(nfo_p)
                    log.info(f"🗑️ Deleted NFO: {nfo_p}")
                reverted += 1
        except Exception as e:
            log.error(f"❌ Failed: {action} | {e}")
            errors += 1

    log.info(f"🏁 Rollback complete. Reverted: {reverted} | Skipped: {skipped} | Errors: {errors}")
    if not apply_changes:
        log.info("ℹ️ Dry run finished. Toggle 'Execute Rollback' in plugin settings to apply changes.")
    print(json.dumps({"output": f"Done. Reverted: {reverted}, Skipped: {skipped}, Errors: {errors}", "error": None}))

if __name__ == "__main__":
    main()