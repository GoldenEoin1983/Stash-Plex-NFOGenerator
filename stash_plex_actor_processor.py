#!/usr/bin/env python3
import os, sys, json, shutil, logging, requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from stash_face_cropper import crop_and_save_performer_image
except ImportError:
    print("❌ stash_face_cropper.py not found.")
    sys.exit(1)

def setup_logger(log_file="stash_plex_migration.log"):
    logger = logging.getLogger("stash_plex_actor_processor")
    if logger.handlers: return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    fh = logging.FileHandler(log_file, encoding='utf-8'); fh.setFormatter(fmt); logger.addHandler(fh)
    ch = logging.StreamHandler(sys.stderr); ch.setFormatter(fmt); logger.addHandler(ch)
    return logger
log = setup_logger()

def get_connection():
    try:
        data = json.loads(sys.stdin.read())
        return data.get("server_connection", {}), data.get("args", {})
    except json.JSONDecodeError:
        log.error("Failed to parse stdin JSON."); sys.exit(1)

def build_session(conn):
    scheme = conn.get("Scheme", "http")
    host = "localhost" if conn.get("Host") in ("0.0.0.0", "127.0.0.1") else conn.get("Host", "localhost")
    port = conn.get("Port", 9999)
    cookie = conn.get("SessionCookie", {})
    api_key = cookie.get("Value", "")
    s = requests.Session()
    if api_key: s.cookies.set(cookie.get("Name", "session"), api_key, domain=host)
    return s, f"{scheme}://{host}:{port}/graphql"

def fetch_performers(session, url):
    p_list = []
    page, per_page = 1, 100
    while True:
        q = """query FindPerformers($page:Int!,$perPage:Int!){findPerformers(filter:{page:$page,per_page:$perPage}){performers{id name image_path}}}"""
        r = session.post(url, json={"query":q,"variables":{"page":page,"perPage":per_page}}); r.raise_for_status()
        data = r.json()["data"]["findPerformers"]["performers"]
        p_list.extend([p for p in data if p.get("image_path")])
        if len(data) < per_page: break
        page += 1
    return p_list

def get_scene_dirs_for_performer(session, url, pid):
    dirs = set()
    page, per_page = 1, 100
    q = """query FindScenesByPerformer($page:Int!,$perPage:Int!,$pid:[ID!]){findScenes(scene_filter:{performers:{value:$pid,modifier:INCLUDES}},filter:{page:$page,per_page:$perPage}){scenes{files{path}}}}"""
    while True:
        r = session.post(url, json={"query":q,"variables":{"page":page,"perPage":per_page,"pid":[pid]}}); r.raise_for_status()
        scenes = r.json()["data"]["findScenes"]["scenes"]
        for s in scenes:
            if s.get("files"):
                dirs.add(os.path.dirname(s["files"][0]["path"]))
        if len(scenes) < per_page: break
        page += 1
    return dirs

def main():
    conn, args = get_connection()
    session, url = build_session(conn)
    
    mode = args.get("actor_save_mode", "PER_SCENE").strip().upper()
    central_dir = args.get("actor_central_dir", "").strip()
    
    log.info(f"[SESSION] actor_processing start | mode={mode} | timestamp={datetime.now().isoformat()}")
    
    if mode == "CENTRAL":
        if not central_dir:
            log.error("❌ CENTRAL mode selected but 'Central Actor Folder Path' is empty.")
            sys.exit(1)
        if not os.path.isdir(central_dir):
            log.error(f"❌ Central directory not found: {central_dir}")
            log.warning("⚠️ REMINDER: This path MUST be inside your Docker mounted volumes and match a path defined in Stash > Settings > Libraries.")
            sys.exit(1)

    performers = fetch_performers(session, url)
    log.info(f"Found {len(performers)} performers with images to process.")
    
    processed = 0
    skipped = 0
    errors = 0
    
    for i, p in enumerate(performers):
        name = p["name"]
        src = p["image_path"]
        if not os.path.exists(src):
            skipped += 1; continue
            
        try:
            cropped = crop_and_save_performer_image(src)
            
            if mode == "CENTRAL":
                dest = os.path.join(central_dir, f"{name}.jpg")
                shutil.copy2(cropped, dest)
                log.info(f"📁 [{i+1}/{len(performers)}] {name} -> {dest}")
            else:
                scene_dirs = get_scene_dirs_for_performer(session, url, p["id"])
                if not scene_dirs:
                    log.info(f"🎬 [{i+1}/{len(performers)}] {name} has no scenes. Skipped.")
                    skipped += 1; continue
                    
                for d in scene_dirs:
                    actor_dir = os.path.join(d, ".actor")
                    os.makedirs(actor_dir, exist_ok=True)
                    dest = os.path.join(actor_dir, f"{name}.jpg")
                    shutil.copy2(cropped, dest)
                log.info(f"🎬 [{i+1}/{len(performers)}] {name} copied to {len(scene_dirs)} scene(s).")
            processed += 1
        except Exception as e:
            log.error(f"❌ [{i+1}/{len(performers)}] {name}: {e}")
            errors += 1

    log.info(f"[SESSION] actor_processing end | processed={processed} | skipped={skipped} | errors={errors}")
    print(json.dumps({"output": f"Done. Processed: {processed}, Skipped: {skipped}, Errors: {errors}", "error": None}))

if __name__ == "__main__":
    main()