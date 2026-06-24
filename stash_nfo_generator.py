#!/usr/bin/env python3
import os, sys, json, logging, requests, xml.etree.ElementTree as ET
from datetime import datetime

def setup_logger(log_file="stash_plex_migration.log"):
    logger = logging.getLogger("stash_plex_exporter")
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

def resolve_studio_id(session, url, name):
    if not name: return []
    q = """query FindStudio($n:String!){findStudios(studio_filter:{name:{value:$n,modifier:EQUALS}},filter:{per_page:1}){studios{id}}}"""
    r = session.post(url, json={"query":q,"variables":{"n":name}}); r.raise_for_status()
    s = r.json()["data"]["findStudios"]["studios"]
    if not s: return []
    return [s[0]["id"]]

def get_studio_hierarchy(studio_obj):
    studios = []
    current = studio_obj
    while current and current.get("name"):
        name = current["name"].strip()
        if name and name not in studios:
            studios.append(name)
        current = current.get("parent_studio")
    return studios

def get_performer_image(performer):
    try:
        from stash_face_cropper import crop_and_save_performer_image
    except ImportError:
        log.warning("Cropper not loaded. Returning original image.")
        return performer.get("image_path")
    
    img_path = performer.get("image_path")
    if not img_path or not os.path.exists(img_path):
        return None
        
    dir_name = os.path.dirname(img_path)
    base = os.path.splitext(os.path.basename(img_path))[0]
    plex_img = os.path.join(dir_name, f"{base}_plex.jpg")
    
    if os.path.exists(plex_img):
        return plex_img
        
    return crop_and_save_performer_image(img_path, plex_img)

def write_nfo(scene, dir_path, dry_run):
    root = ET.Element("movie")
    ET.SubElement(root, "title").text = scene["title"] or "Untitled"
    
    # Date fields: premiered (Plex preferred) + year + releasedate (compat)
    if scene["date"]:
        ET.SubElement(root, "year").text = scene["date"][:4]
        ET.SubElement(root, "premiered").text = scene["date"]  # Plex preferred format YYYY-MM-DD
        ET.SubElement(root, "releasedate").text = scene["date"]  # Keep for XBMC compat
    
    # Unique ID: Critical for Plex watch-state persistence across rescans
    ET.SubElement(root, "uniqueid", type="stash", default="true").text = str(scene["id"])
    if scene.get("details"):
        ET.SubElement(root, "plot").text = scene["details"]
    
    all_studios = get_studio_hierarchy(scene.get("studio"))
    if all_studios:
        ET.SubElement(root, "studio").text = all_studios[0]
        for s_name in all_studios:
            ET.SubElement(root, "collection").text = s_name

    for p in scene.get("performers", []):
        actor = ET.SubElement(root, "actor")
        ET.SubElement(actor, "name").text = p["name"]
        ET.SubElement(actor, "role").text = "Actor"
        
        if p.get("urls"):
            for u in p["urls"]:
                if u.get("url"):
                    ET.SubElement(actor, "url").text = u["url"]
        
        img_path = get_performer_image(p)
        if img_path:
            ET.SubElement(actor, "thumb").text = f"file://{img_path}"

    xml_str = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    xml_str += ET.tostring(root, encoding="unicode")
    
    nfo_path = os.path.join(dir_path, "movie.nfo")
    if dry_run:
        log.info(f"LOG_TYPE:NFO_DRY_RUN | ID:{scene['id']} | PATH:{nfo_path}")
    else:
        try:
            with open(nfo_path, "w", encoding="utf-8") as f: f.write(xml_str)
            log.info(f"LOG_TYPE:NFO_CREATED | ID:{scene['id']} | PATH:{nfo_path}")
        except Exception as e:
            log.error(f"LOG_TYPE:NFO_ERROR | ID:{scene['id']} | PATH:{nfo_path} | ERROR:{e}")

def main():
    conn, args = get_connection()
    dry_run = str(args.get("dry_run", "true")).lower() in ("true", "1", "yes")
    studio_name = args.get("studio", "").strip()
    
    session, url = build_session(conn)
    studio_ids = resolve_studio_id(session, url, studio_name)
    scene_filter = {"studios": {"value": studio_ids, "modifier": "INCLUDES"}} if studio_ids else {}

    query = """
    query FindScenes($page: Int!, $perPage: Int!, $sceneFilter: SceneFilterInput) {
      findScenes(filter: { page: $page, per_page: $perPage }, scene_filter: $sceneFilter) {
        scenes {
          id title date details
          studio { name parent_studio { name parent_studio { name } } }
          performers { name image_path urls { url } }
          files { path }
        }
      }
    }"""
    
    log.info(f"[SESSION] start | dry_run={dry_run} | studio={studio_name or 'ALL'} | timestamp={datetime.now().isoformat()}")
    page, per_page, total = 1, 100, 0
    
    while True:
        vars = {"page": page, "perPage": per_page, "sceneFilter": scene_filter}
        r = session.post(url, json={"query": query, "variables": vars}); r.raise_for_status()
        scenes = r.json()["data"]["findScenes"]["scenes"]
        if not scenes: break
        
        for scene in scenes:
            if not scene["files"]: continue
            dir_path = os.path.dirname(scene["files"][0]["path"])
            if os.path.isdir(dir_path):
                write_nfo(scene, dir_path, dry_run)
                total += 1
        if len(scenes) < per_page: break
        page += 1
        
    log.info(f"[SESSION] end | processed={total}")
    print(json.dumps({"output": f"Done. {total} NFOs processed.", "error": None}))

if __name__ == "__main__":
    main()