### USER
a script for addressing the 'genre' tags. videos in stash have tags too but none really fit into the genre category so there should be a setting option for choosing which tags should be considered genres. OR they can pick just one tags and the plugin will query all of it's children tags and use those. Tags are identified by number but I think it would be much easier if people could input the name of the tags instead or either... 

### ASSISTANT
Here is the modular implementation for mapping Stash **Tags → Plex Genres**, integrated into your existing architecture while preserving dry-run safety, logging, and XBMC NFO compliance.

### 1. Updated `plex_exporter.yml` Settings
Add these to your `settings:` block. Supports both explicit lists and parent-child tree traversal.

```yaml
  genre_mapping_mode:
    displayName: Genre Mapping Mode
    description: "EXPLICIT (manual list) or PARENT_CHILD (auto-fetch children)"
    type: STRING
    default: "EXPLICIT"
  genre_tags:
    displayName: Explicit Genre Tags
    description: "Comma-separated tag names for EXPLICIT mode"
    type: STRING
    default: ""
  genre_parent_tag:
    displayName: Parent Tag for Genres
    description: "Tag name whose descendants become genres (PARENT_CHILD mode)"
    type: STRING
    default: ""
```

### 2. GraphQL Tag Resolution Queries
Add these to `stash_nfo_generator.py` alongside your existing scene pagination queries:

```python
FIND_TAG_BY_NAME = """
query FindTagsByName($filter: FindFilterType!) {
  findTags(filter: $filter) {
    count
    tags {
      id
      name
      children { id name }
    }
  }
}
"""

FIND_TAGS_BY_PARENT = """
query FindTagsByParent($parent_ids: [ID!]) {
  findTags(filter: { parent_ids: $parent_ids, per_page: 9999 }) {
    count
    tags { id name child_ids }
  }
}
"""
```

### 3. Genre Resolution & NFO Injection Logic
Append this to `stash_nfo_generator.py`. It handles tag resolution once per run, caches results, and safely injects `<genre>` into the NFO.

```python
import re
import xml.etree.ElementTree as ET
from typing import Set, Dict, List

def resolve_genres(session, url: str, mode: str, explicit_str: str, parent_name: str) -> Set[str]:
    """Resolves a set of genre tag names based on user settings."""
    genres = set()
    if mode == "EXPLICIT":
        genres = {t.strip().lower() for t in explicit_str.split(",") if t.strip()}
        # Normalize to actual stash names via single query if needed, 
        # but direct match is fine for explicit mode.
        return {t for t in genres} # Return as-is, matching will be case-insensitive later

    if mode == "PARENT_CHILD" and parent_name.strip():
        parent_name = parent_name.strip()
        # 1. Find parent tag ID
        resp = session.post(url, json={"query": FIND_TAG_BY_NAME, "variables": {
            "filter": {"q": parent_name, "per_page": 1}
        }})
        parent_tags = resp.json()["data"]["findTags"]["tags"]
        parent_id = None
        for t in parent_tags:
            if t["name"].lower() == parent_name.lower():
                parent_id = t["id"]
                break
        if not parent_id:
            print(f"| [WARN] Parent tag '{parent_name}' not found. Genres disabled.", file=sys.stderr)
            return set()

        # 2. Recursively collect all descendants
        queue = [parent_id]
        visited = {parent_id}
        while queue:
            pid = queue.pop(0)
            resp = session.post(url, json={"query": FIND_TAGS_BY_PARENT, "variables": {"parent_ids": [pid]}})
            children = resp.json()["data"]["findTags"]["tags"]
            for c in children:
                if c["id"] not in visited:
                    visited.add(c["id"])
                    genres.add(c["name"])
                    queue.append(c["id"])
    return genres

def generate_scene_nfo(scene: Dict, genre_set: Set[str], dry_run: bool, log_fh) -> str:
    """Generates XBMC movie.nfo content with genre injection."""
    root = ET.Element("movie")
    
    # Title & Year
    ET.SubElement(root, "title").text = scene.get("title") or "Untitled"
    ET.SubElement(root, "year").text = (scene.get("date") or "Unknown")[:4]
    ET.SubElement(root, "releasedate").text = scene.get("date", "Unknown")
    if scene.get("details"):
        ET.SubElement(root, "plot").text = scene["details"]
        
    # Studios & Collections
    studios = []
    s = scene.get("studio")
    while s:
        studios.append(s["name"])
        s = s.get("parent_studio")
    studios = list(dict.fromkeys(studios)) # Dedupe preserving order
    if studios:
        ET.SubElement(root, "studio").text = studios[0]
        for st in studios:
            ET.SubElement(root, "collection").text = st
            
    # Genres
    scene_tags = {t["name"].lower(): t["name"] for t in scene.get("tags", [])}
    matched_genres = []
    for g_name in genre_set:
        if g_name in scene_tags:
            matched_genres.append(scene_tags[g_name])
    matched_genres.sort()
    
    if matched_genres:
        for genre in matched_genres:
            ET.SubElement(root, "genre").text = genre
        if not dry_run:
            log_fh.write(f"| LOG_TYPE:GENRE_MAPPED | ID:{scene['id']} | GENRES:{', '.join(matched_genres)}\n")

    # Actors (existing logic placeholder)
    for p in scene.get("performers", []):
        actor = ET.SubElement(root, "actor")
        ET.SubElement(actor, "name").text = p["name"]
        ET.SubElement(actor, "role").text = "Actor"
        # Add thumb/url logic here as per your existing contract

    # Write NFO
    nfo_path = f"{scene['path'].rsplit('.', 1)[0]}.nfo" # Assumes Title.ext → Title.nfo
    if dry_run:
        return f"[DRY RUN] Would create {nfo_path}"
    
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(nfo_path, encoding="UTF-8", xml_declaration=True)
    return nfo_path
```

### 4. Integration into Main Execution Flow
In your `main()` or `run_task()` function, wire it up before the scene loop:

```python
def run_nfo_generation(server_conn: Dict, args: Dict):
    # ... setup session, url, dry_run, log_fh ...
    
    mode = args.get("genre_mapping_mode", "EXPLICIT")
    explicit_tags = args.get("genre_tags", "")
    parent_tag = args.get("genre_parent_tag", "")
    
    print(f"| [INIT] Resolving genres (mode={mode})...", file=sys.stderr)
    genre_set = resolve_genres(session, url, mode, explicit_tags, parent_tag)
    print(f"| [INIT] Found {len(genre_set)} genre tags.", file=sys.stderr)
    
    # Pagination loop for scenes
    page, per_page = 1, 100
    while True:
        # ... fetch scenes ...
        for scene in scenes:
            if len(scene.get("files", [])) > 1:
                log_fh.write(f"| [WARN] Skipping multi-file scene ID:{scene['id']}\n")
                continue
                
            result = generate_scene_nfo(scene, genre_set, dry_run, log_fh)
            if not dry_run:
                log_fh.write(f"| LOG_TYPE:NFO_CREATED | ID:{scene['id']} | PATH:{result}\n")
                
        if len(scenes) < per_page: break
        page += 1
        
    # ... cleanup & stdout output ...
    print(json.dumps({"output": f"Genre-mapped NFO generation complete. {len(genre_set)} genres resolved.", "error": None}))
```

### 🔑 Key Design Decisions
1. **Name-Based Input:** Users enter human-readable names (`PARENT_CHILD` or `EXPLICIT`). The resolver handles case-insensitive matching against Stash's DB.
2. **One-Time Resolution:** Tag trees are fetched **once** at script start, not per-scene. This keeps GraphQL overhead minimal even on large libraries.
3. **Safe Fallbacks:** If `parent_name` isn't found, it logs a warning and skips genre injection without failing the run.
4. **Dry-Run Compatible:** Genre mapping logic runs in preview mode. `LOG_TYPE:GENRE_MAPPED` is only written when `dry_run=false`.
5. **XBMC Compliance:** `<genre>` is a standard Plex/ XBMC tag. Multiple genres are sorted alphabetically for deterministic output.

### 🧪 Testing Protocol
1. Set `dry_run: true` in UI.
2. Test `EXPLICIT` mode with 2-3 comma-separated tag names.
3. Test `PARENT_CHILD` mode with a known parent tag (e.g., `"Categories"`).
4. Verify `stash_plex_migration.log` shows `LOG_TYPE:GENRE_MAPPED` entries.
5. Open a generated `.nfo` and confirm `<genre>` tags appear correctly.
6. Uncheck dry-run, execute, then trigger **Plex Scan Library**.

Let me know if you want this wrapped into a complete `stash_nfo_generator.py` file or if you need the `EXPLICIT` mode to auto-resolve names to IDs for exact DB matching.

### USER
the tag names should be checked that they correspond to tag IDs

### ASSISTANT
Here is the updated genre resolution module with **strict ID validation**. It maps user-provided tag names to Stash tag IDs, warns on mismatches, and only injects verified genres into the NFO.

### 🔧 Updated `resolve_genres` with ID Validation
Replace your previous `resolve_genres` function with this version. It performs explicit name→ID lookups, logs resolution results, and safely handles missing tags.

```python
import sys
import json

FIND_TAG_BY_NAME = """
query FindTagsByName($filter: FindFilterType!) {
  findTags(filter: $filter) {
    count
    tags {
      id
      name
    }
  }
}
"""

FIND_TAGS_BY_PARENT = """
query FindTagsByParent($parent_ids: [ID!]) {
  findTags(filter: { parent_ids: $parent_ids, per_page: 9999 }) {
    count
    tags { id name }
  }
}
"""

def resolve_genres(session, url: str, mode: str, explicit_str: str, parent_name: str, log_fh) -> set:
    """
    Resolves tag names to valid Stash IDs. 
    Returns a set of verified genre names for NFO injection.
    """
    genres = set()

    def lookup_tag(name):
        """Searches Stash for exact tag match and returns (id, db_name)."""
        if not name: return None, None
        resp = session.post(url, json={
            "query": FIND_TAG_BY_NAME,
            "variables": {"filter": {"q": name.strip(), "per_page": 50}}
        })
        data = resp.json()
        if "errors" in 
            log_fh.write(f"| LOG_TYPE:GENRE_ERROR | MSG:{data['errors']}\n")
            print(f"| [ERROR] GraphQL: {data['errors']}", file=sys.stderr)
            return None, None
            
        # Stash `q` is fuzzy; enforce exact match
        target = name.strip().lower()
        for t in data["data"]["findTags"]["tags"]:
            if t["name"].lower() == target:
                return t["id"], t["name"]
        return None, None

    if mode == "EXPLICIT":
        tags_to_check = [t.strip() for t in explicit_str.split(",") if t.strip()]
        if not tags_to_check:
            print("| [INFO] No explicit tags provided.", file=sys.stderr)
            return genres

        for tag_input in tags_to_check:
            tid, tname = lookup_tag(tag_input)
            if tid:
                genres.add(tname)
                log_fh.write(f"| LOG_TYPE:GENRE_RESOLVED | INPUT:{tag_input} -> ID:{tid} | DB_NAME:{tname}\n")
            else:
                log_fh.write(f"| LOG_TYPE:GENRE_MISSING | INPUT:{tag_input}\n")
                print(f"| [WARN] Tag '{tag_input}' not found in Stash. Skipping.", file=sys.stderr)

    elif mode == "PARENT_CHILD":
        if not parent_name.strip(): return genres
        
        pid, pname = lookup_tag(parent_name)
        if not pid:
            log_fh.write(f"| LOG_TYPE:GENRE_MISSING | PARENT:{parent_name}\n")
            print(f"| [WARN] Parent tag '{parent_name}' not found. Genres disabled.", file=sys.stderr)
            return genres

        log_fh.write(f"| LOG_TYPE:GENRE_PARENT_RESOLVED | INPUT:{parent_name} -> ID:{pid} | DB_NAME:{pname}\n")

        # BFS to collect all descendants
        queue = [pid]
        visited = {pid}
        while queue:
            current_pid = queue.pop(0)
            resp = session.post(url, json={
                "query": FIND_TAGS_BY_PARENT,
                "variables": {"parent_ids": [current_pid]}
            })
            children = resp.json()["data"]["findTags"]["tags"]
            for c in children:
                if c["id"] not in visited:
                    visited.add(c["id"])
                    genres.add(c["name"])
                    queue.append(c["id"])
                    
        log_fh.write(f"| LOG_TYPE:GENRE_CHILDREN_FOUND | PARENT:{pname} | COUNT:{len(genres)}\n")
        
    print(f"| [INIT] Resolved {len(genres)} valid genres.", file=sys.stderr)
    return genres
```

### 📝 Key Improvements
1. **Exact ID Mapping**: Queries Stash and enforces exact case-insensitive match against DB names. Fuzzy search results that don't match exactly are ignored.
2. **Validation Logging**: 
   - `LOG_TYPE:GENRE_RESOLVED` on success (shows input → ID → canonical name).
   - `LOG_TYPE:GENRE_MISSING` on failure (triggers stderr warning but doesn't abort).
   - `LOG_TYPE:GENRE_PARENT_RESOLVED` & `LOG_TYPE:GENRE_CHILDREN_FOUND` for tree mode.
3. **Safe Fallback**: Invalid names are silently skipped with a warning, preventing malformed NFOs.
4. **Canonical Names**: Uses `t["name"]` from the DB for NFO injection, ensuring consistent casing even if user types `tagname` vs `TagName`.

### 🔌 Integration Check
Ensure your NFO generator still uses this set correctly:
```python
# Inside generate_scene_nfo(...)
scene_tags = {t["name"].lower(): t["name"] for t in scene.get("tags", [])}
for genre in genres: # 'genres' is the set returned by resolve_genres
    if genre.lower() in scene_tags:
        ET.SubElement(root, "genre").text = scene_tags[genre.lower()]
```

### 🧪 Validation Protocol
1. Set `genre_mapping_mode: EXPLICIT`
2. Input: `valid_tag, TypoTag, AnotherValid`
3. Run with `dry_run: true`
4. Check `stash_plex_migration.log`:
   - `LOG_TYPE:GENRE_RESOLVED` for valid tags.
   - `LOG_TYPE:GENRE_MISSING` for typos.
5. Verify NFO only contains `<genre>` elements for the resolved tags.

This guarantees that only existing Stash tags (by ID) are mapped to Plex, preventing phantom genres from appearing in your library. Let me know if you need batch ID resolution optimization or tree-depth limiting.