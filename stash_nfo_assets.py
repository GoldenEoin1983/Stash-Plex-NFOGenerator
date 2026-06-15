#!/usr/bin/env python3
import sys
import json
import os
import re
import logging
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG & LOGGING
# ─────────────────────────────────────────────────────────────────────────────
LOG_FILE = "stash_plex_migration.log"

def setup_logger():
    logger = logging.getLogger("stash_nfo_assets")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("| %(message)s")
    
    fh = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger

log = setup_logger()

# ─────────────────────────────────────────────────────────────────────────────
# GRAPHQL CONTRACTS
# ─────────────────────────────────────────────────────────────────────────────
SCENE_ASSET_QUERY = """
query FindScenes($page: Int!, $perPage: Int!) {
  findScenes(input: { page: $page, per_page: $perPage }) {
    scenes {
      id
      title
      date
      path
      cover_image
      files { path }
      galleries { id cover_image }
      studio { id name image parent_studio { id name image } }
    }
    count
  }
}
"""

SCAN_LIBRARY_MUTATION = """
mutation ScanLibrary($paths: [String!], $flags: ScanMetadataInput) {
  scanLibrary(paths: $paths, flags: $flags)
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# SESSION & API
# ─────────────────────────────────────────────────────────────────────────────
def get_stash_session(server_conn):
    session = requests.Session()
    cookie = server_conn.get("SessionCookie", {})
    if cookie.get("Value"):
        session.cookies.set(cookie.get("Name", "session"), cookie["Value"], domain=cookie.get("Domain", ""))
    return session

def run_graphql(session, base_url, query, variables):
    resp = session.post(f"{base_url}/graphql", json={"query": query, "variables": variables})
    resp.raise_for_status()
    return resp.json().get("data", {})

def build_stash_image_url(base_url, asset_type, asset_id):
    return f"{base_url}/image/{asset_type}/{asset_id}"

# ─────────────────────────────────────────────────────────────────────────────
# IMAGE HANDLING
# ─────────────────────────────────────────────────────────────────────────────
def download_image(session, url, dest_path, dry_run=True):
    if dry_run:
        log.info(f"LOG_TYPE:IMAGE_DRY_RUN | URL:{url} | DEST:{dest_path}")
        return False # Dry-run does not mutate disk
        
    try:
        resp = session.get(url, stream=True, timeout=10)
        resp.raise_for_status()
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        log.info(f"LOG_TYPE:IMAGE_DOWNLOADED | URL:{url} | DEST:{dest_path}")
        return True
    except Exception as e:
        log.warning(f"LOG_TYPE:IMAGE_FAIL | URL:{url} | ERR:{str(e)}")
        return False

def ensure_nfo_assets(nfo_path, assets, dry_run=True):
    if not os.path.exists(nfo_path):
        log.warning(f"LOG_TYPE:NFO_MISSING | PATH:{nfo_path} (Skipping asset tags)")
        return

    if dry_run:
        log.info(f"LOG_TYPE:NFO_ASSETS_DRY_RUN | PATH:{nfo_path} | ASSETS:{assets}")
        return

    try:
        tree = ET.parse(nfo_path)
        root = tree.getroot()
        
        tag_map = {
            "poster.jpg": ("thumb", None),
            "fanart.jpg": ("fanart", "thumb"),
            "logo.png": ("logo", None),
            "square.jpg": ("square", None)
        }
        
        for fname, (parent_tag, child_tag) in tag_map.items():
            if not assets.get(fname): continue
                
            if child_tag:
                for el in root.findall(f".//{parent_tag}"):
                    if child_tag in el.attrib or child_tag in el.tag:
                        root.remove(el)
            else:
                for el in root.findall(f".//{parent_tag}"):
                    root.remove(el)
                    
            parent_el = ET.SubElement(root, parent_tag)
            if child_tag:
                ET.SubElement(parent_el, child_tag).text = fname
            else:
                parent_el.text = fname
                
        tree.write(nfo_path, encoding="UTF-8", xml_declaration=True)
        log.info(f"LOG_TYPE:NFO_ASSETS_UPDATED | PATH:{nfo_path}")
    except Exception as e:
        log.error(f"LOG_TYPE:NFO_ASSETS_FAIL | PATH:{nfo_path} | ERR:{str(e)}")

# ─────────────────────────────────────────────────────────────────────────────
# AUTO-SCAN TRIGGER
# ─────────────────────────────────────────────────────────────────────────────
def trigger_stash_scan(session, base_url, target_paths, dry_run=True):
    """Trigger a partial Stash library scan for modified directories."""
    if not target_paths:
        log.info("LOG_TYPE:SCAN_SKIPPED | No modified directories found")
        return {"triggered": False}
        
    if dry_run:
        log.info(f"LOG_TYPE:SCAN_DRY_RUN | PATHS:{list(target_paths)}")
        return {"triggered": False}

    try:
        resp = session.post(
            f"{base_url}/graphql",
            json={"query": SCAN_LIBRARY_MUTATION, "variables": {"paths": target_paths, "flags": {}}},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        log.info(f"LOG_TYPE:SCAN_TRIGGERED | PATHS:{list(target_paths)}")
        return {"triggered": True, "status": data}
    except Exception as e:
        log.error(f"LOG_TYPE:SCAN_FAILED | PATHS:{list(target_paths)} | ERR:{str(e)}")
        return {"triggered": False, "error": str(e)}

# ─────────────────────────────────────────────────────────────────────────────
# MAIN PROCESSOR
# ─────────────────────────────────────────────────────────────────────────────
def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(json.dumps({"output": "Invalid stdin JSON", "error": str(e)}))
        sys.exit(1)

    server_conn = input_data.get("server_connection", {})
    args = input_data.get("args", {})
    dry_run = str(args.get("dry_run", "true")).lower() in ("true", "1", "yes")
    studio_filter = (args.get("studio") or args.get("studio_filter") or "").strip()

    session = get_stash_session(server_conn)
    scheme = server_conn.get("Scheme", "http")
    host = server_conn.get("Host", "localhost")
    port = server_conn.get("Port", 9999)
    base_url = f"{scheme}://{host}:{port}"

    log.info(f"| [SESSION] start | dry_run={dry_run} | studio={studio_filter or 'ALL'} | auto_scan=enabled")
    
    page, per_page = 1, 50
    processed, skipped = 0, 0
    modified_dirs = set()
    
    while True:
        data = run_graphql(session, base_url, SCENE_ASSET_QUERY, {"page": page, "perPage": per_page})
        scenes = data.get("findScenes", {}).get("scenes", [])
        
        for scene in scenes:
            try:
                studio_name = (scene.get("studio") or {}).get("name", "")
                if studio_filter and studio_name.lower() != studio_filter.lower():
                    continue

                scene_path = scene.get("path", "")
                if not scene_path: continue
                scene_dir = os.path.dirname(scene_path)
                scene_id = scene.get("id")
                
                # Skip multi-file scenes per contract
                if len(scene.get("files", [])) > 1:
                    log.warning(f"LOG_TYPE:SKIP_MULTI_FILE | ID:{scene_id} | PATH:{scene_path}")
                    skipped += 1
                    continue

                found_assets = {}
                local_map = {
                    "fanart.jpg": ("cover_image", "scene", scene_id),
                    "poster.jpg": ("galleries", "gallery", None),
                    "logo.png": ("studio", "studio", None),
                    "square.jpg": ("cover_image", "scene", scene_id)
                }
                
                for fname, (source, asset_type, aid) in local_map.items():
                    dest = os.path.join(scene_dir, fname)
                    if os.path.exists(dest):
                        found_assets[fname] = True
                        continue
                        
                    img_url = None
                    if fname == "fanart.jpg":
                        img_url = build_stash_image_url(base_url, "scene", scene_id)
                    elif fname == "poster.jpg":
                        galleries = scene.get("galleries", [])
                        if galleries and galleries[0].get("id"):
                            img_url = build_stash_image_url(base_url, "gallery", galleries[0]["id"])
                    elif fname == "logo.png":
                        studio_obj = scene.get("studio") or {}
                        studio = studio_obj if studio_obj.get("id") else (studio_obj.get("parent_studio") or {})
                        if studio.get("id"):
                            img_url = build_stash_image_url(base_url, "studio", studio["id"])
                    elif fname == "square.jpg":
                        img_url = build_stash_image_url(base_url, "scene", scene_id)
                            
                    if img_url:
                        if download_image(session, img_url, dest, dry_run):
                            found_assets[fname] = True
                            
                if found_assets:
                    ensure_nfo_assets(os.path.join(scene_dir, "movie.nfo"), found_assets, dry_run)
                    modified_dirs.add(scene_dir)
                    processed += 1
                    
            except Exception as e:
                log.error(f"LOG_TYPE:ASSET_FAIL | ID:{scene.get('id')} | ERR:{str(e)}")
                skipped += 1

        if len(scenes) < per_page:
            break
        page += 1

    # Trigger auto-scan for all touched directories
    trigger_stash_scan(session, base_url, list(modified_dirs), dry_run)

    log.info(f"| [SESSION] end | processed={processed} | skipped={skipped} | scan_paths={len(modified_dirs)}")
    print(json.dumps({"output": f"Processed {processed} scenes, skipped {skipped}. Dry-run: {dry_run}", "error": None}))

if __name__ == "__main__":
    main()