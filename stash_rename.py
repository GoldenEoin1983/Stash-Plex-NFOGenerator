#!/usr/bin/env python3
import os, sys, json, re, logging
from datetime import datetime

def setup_logger(log_file="stash_plex_migration.log"):
    logger = logging.getLogger("stash_plex_exporter")
    if logger.handlers: return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setFormatter(fmt); logger.addHandler(fh)
    ch = logging.StreamHandler(sys.stderr)
    ch.setFormatter(fmt); logger.addHandler(ch)
    return logger

log = setup_logger()

def get_connection():
    try:
        data = json.loads(sys.stdin.read())
        return data.get("server_connection", {}), data.get("args", {})
    except json.JSONDecodeError:
        log.error("Failed to parse stdin JSON."); sys.exit(1)

def build_session(conn):
    import requests
    scheme = conn.get("Scheme", "http")
    host = "localhost" if conn.get("Host") in ("0.0.0.0", "127.0.0.1") else conn.get("Host", "localhost")
    port = conn.get("Port", 9999)
    cookie = conn.get("SessionCookie", {})
    api_key = cookie.get("Value", "")
    s = requests.Session()
    if api_key: s.cookies.set(cookie.get("Name", "session"), api_key, domain=host)
    return s, f"{scheme}://{host}:{port}/graphql"

def resolve_studio_id(session, url, name):
    if not name: return []
    q = """query FindStudio($n:String!){findStudios(studio_filter:{name:{value:$n,modifier:EQUALS}},filter:{per_page:1}){studios{id}}}"""
    r = session.post(url, json={"query":q,"variables":{"n":name}}); r.raise_for_status()
    s = r.json()["data"]["findStudios"]["studios"]
    if not s: log.warning(f"Studio '{name}' not found. Processing ALL scenes."); return []
    return [s[0]["id"]]

def sanitize(title):
    safe = re.sub(r'[<>:"/\\|?*]', '_', title.strip() or "Untitled")
    return re.sub(r'_+', '_', safe).strip('_')

def main():
    import requests
    conn, args = get_connection()
    dry_run = str(args.get("dry_run", "true")).lower() in ("true", "1", "yes")
    studio_name = args.get("studio", "").strip()
    
    session, url = build_session(conn)
    studio_ids = resolve_studio_id(session, url, studio_name)
    scene_filter = {"studios": {"value": studio_ids, "modifier": "INCLUDES"}} if studio_ids else {}

    query = """
    query FindScenes($page: Int!, $perPage: Int!, $sceneFilter: SceneFilterInput) {
      findScenes(filter: { page: $page, per_page: $perPage }, scene_filter: $sceneFilter) {
        count scenes { id title date files { path } }
      }
    }"""
    
    log.info(f"[SESSION] start | dry_run={dry_run} | studio={studio_name or 'ALL'} | timestamp={datetime.now().isoformat()}")
    page, per_page, processed, skipped = 1, 100, 0, 0

    while True:
        vars = {"page": page, "perPage": per_page, "sceneFilter": scene_filter}
        resp = session.post(url, json={"query": query, "variables": vars}); resp.raise_for_status()
        data = resp.json()["data"]["findScenes"]
        if not data["scenes"]: break

        for scene in data["scenes"]:
            if not scene["files"]: continue
            old_path = scene["files"][0]["path"]
            dir_path, basename = os.path.split(old_path)
            name, ext = os.path.splitext(basename)
            
            year = scene["date"][:4] if scene["date"] and len(scene["date"]) >= 4 else "Unknown"
            safe_title = sanitize(scene["title"])
            new_name = f"{safe_title} ({year}){ext}"
            new_path = os.path.join(dir_path, new_name)
            
            if os.path.exists(new_path):
                counter = 1
                base, ext = os.path.splitext(new_name)
                while os.path.exists(new_path):
                    new_name = f"{base}_{counter}{ext}"
                    new_path = os.path.join(dir_path, new_name)
                    counter += 1

            if old_path == new_path:
                skipped += 1; continue

            if dry_run:
                log.info(f"LOG_TYPE:RENAME_DRY_RUN | ID:{scene['id']} | OLD:{old_path} | NEW:{new_path}")
            else:
                try:
                    os.rename(old_path, new_path)
                    log.info(f"LOG_TYPE:RENAME_SUCCESS | ID:{scene['id']} | OLD:{old_path} | NEW:{new_path}")
                    processed += 1
                except Exception as e:
                    log.error(f"LOG_TYPE:RENAME_ERROR | ID:{scene['id']} | PATH:{old_path} | ERROR:{e}")
            skipped += 1 if not dry_run else 0

        if len(data["scenes"]) < per_page: break
        page += 1

    log.info(f"[SESSION] end | processed={processed} | skipped={skipped}")
    print(json.dumps({"output": f"Done. {processed} renamed, {skipped} skipped.", "error": None}))

if __name__ == "__main__":
    main()