import os
import json
import time
from typing import Any, Dict, List, Optional, Tuple

# ───────────────────────────── Storage paths ─────────────────────────────
BASE_DATA = os.getenv("DATABASE_PATH", "./data.json")
BASE_DIR  = os.path.dirname(BASE_DATA) or "."

LISTS_DIR            = os.path.join(BASE_DIR, "lists")
DASHBOARDS_PATH      = os.getenv("DASHBOARDS_PATH")      or os.path.join(BASE_DIR, "dashboards.json")

GEN_LISTS_DIR        = os.path.join(BASE_DIR, "generator_lists")
GEN_DASHBOARDS_PATH  = os.getenv("GEN_DASHBOARDS_PATH")  or os.path.join(BASE_DIR, "generator_dashboards.json")

TIMERS_PATH          = os.path.join(BASE_DIR, "timers.json")

# --- One-time migration from old nested layout (safe & idempotent) ---
def _migrate_old_layout() -> None:
    try:
        old_base = os.path.join(BASE_DIR, "lists")  # when BASE_DATA defaulted to ./lists/data.json
        # Move nested regular lists: lists/lists/*.json -> ./lists/*.json
        old_nested = os.path.join(old_base, "lists")
        if os.path.isdir(old_nested):
            os.makedirs(LISTS_DIR, exist_ok=True)
            for fn in os.listdir(old_nested):
                if fn.endswith(".json"):
                    src = os.path.join(old_nested, fn)
                    dst = os.path.join(LISTS_DIR, fn)
                    if not os.path.exists(dst):
                        os.replace(src, dst)

        # Move generator lists: lists/generator_lists/*.json -> ./generator_lists/*.json
        old_gen = os.path.join(old_base, "generator_lists")
        if os.path.isdir(old_gen):
            os.makedirs(GEN_LISTS_DIR, exist_ok=True)
            for fn in os.listdir(old_gen):
                if fn.endswith(".json"):
                    src = os.path.join(old_gen, fn)
                    dst = os.path.join(GEN_LISTS_DIR, fn)
                    if not os.path.exists(dst):
                        os.replace(src, dst)

        # Move dashboards/timers written under the old base
        for src, dst in [
            (os.path.join(old_base, "dashboards.json"), DASHBOARDS_PATH),
            (os.path.join(old_base, "generator_dashboards.json"), GEN_DASHBOARDS_PATH),
            (os.path.join(old_base, "timers.json"), TIMERS_PATH),
        ]:
            if os.path.isfile(src) and not os.path.exists(dst):
                _ensure_dir(dst)
                os.replace(src, dst)
    except Exception:
        # Never block the bot if migration fails; it's safe to ignore.
        pass

_migrate_old_layout()


# ───────────────────────────── I/O helpers ──────────────────────────────
def _ensure_dir(path: str) -> None:
    # If given a file path (has an extension), ensure its parent exists;
    # otherwise treat it as a directory and create it directly.
    is_file = os.path.splitext(path)[1] != ""
    directory = (os.path.dirname(path) or ".") if is_file else path
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

def _safe_read_json(path: str, default: Any) -> Any:
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _safe_write_json(path: str, data: Any) -> None:
    _ensure_dir(path)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)

# ───────────────────────── Regular lists (non-gen) ──────────────────────
def list_path(name: str) -> str:
    return os.path.join(LISTS_DIR, f"{name}.json")

def list_exists(name: str) -> bool:
    return os.path.exists(list_path(name))

def load_list(name: str) -> List[Dict[str, Any]]:
    return _safe_read_json(list_path(name), default=[])

def save_list(name: str, data: List[Dict[str, Any]]) -> None:
    _safe_write_json(list_path(name), data)

def delete_list(name: str) -> None:
    p = list_path(name)
    if os.path.exists(p):
        os.remove(p)

def get_all_list_names() -> List[str]:
    _ensure_dir(LISTS_DIR)
    names: List[str] = []
    for fname in os.listdir(LISTS_DIR):
        if fname.endswith(".json"):
            names.append(fname[:-5])
    return sorted(names)

# Regular list dashboards
def get_dashboard_id(list_name: str) -> Optional[Tuple[int, int]]:
    data = _safe_read_json(DASHBOARDS_PATH, default={})
    v = data.get(list_name)
    if isinstance(v, list) and len(v) == 2:
        try:
            return int(v[0]), int(v[1])
        except Exception:
            return None
    return None

def save_dashboard_id(list_name: str, channel_id: int, message_id: int) -> None:
    data = _safe_read_json(DASHBOARDS_PATH, default={})
    data[list_name] = [int(channel_id), int(message_id)]
    _safe_write_json(DASHBOARDS_PATH, data)

# ───────────────────────────── Generator lists ──────────────────────────
def gen_path(name: str) -> str:
    return os.path.join(GEN_LISTS_DIR, f"{name}.json")

def gen_list_exists(name: str) -> bool:
    return os.path.exists(gen_path(name))

def _default_gen_doc() -> Dict[str, Any]:
    return {"role_id": None, "items": []}

def _wrap_legacy(raw: Any) -> Dict[str, Any]:
    """Accept older file shapes and wrap into the current schema."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        # Old top-level list of items -> wrap
        return {"role_id": None, "items": raw}
    # Anything else, fall back to empty doc
    return _default_gen_doc()

def _load_gen_doc(name: str) -> Dict[str, Any]:
    raw = _safe_read_json(gen_path(name), default=_default_gen_doc())
    doc = _wrap_legacy(raw)
    # Normalize / migrate items so older files pick up new fields
    changed = _normalize_gen_items(doc)
    if changed:
        _safe_write_json(gen_path(name), doc)
    return doc

def _save_gen_doc(name: str, doc: Dict[str, Any]) -> None:
    _safe_write_json(gen_path(name), doc)

def _normalize_gen_items(doc: Dict[str, Any]) -> bool:
    """Ensure all items have the latest schema keys. Returns True if doc was changed."""
    items = doc.get("items", [])
    changed = False
    # Only keep items that are dict-like; ignore garbage gracefully
    normalized_items: List[Dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            # best-effort upgrade if it looks like [name, type, a, b]
            try:
                name, gtype, a, b = it[0], it[1], it[2], it[3]
                it = {"name": str(name), "type": str(gtype)}
                if str(gtype).lower().startswith("tek"):
                    it.update({"element": int(a), "shards": int(b), "gas": 0, "imbued": 0})
                else:
                    it.update({"element": 0, "shards": 0, "gas": int(a), "imbued": int(b)})
                changed = True
            except Exception:
                # skip unknown list shapes
                continue

        # required keys with defaults
        if "type" not in it:            it["type"] = "Tek"; changed = True
        if "name" not in it:            it["name"] = "Unknown"; changed = True

        # Tek fields
        if "element" not in it:         it["element"] = 0; changed = True
        if "shards" not in it:          it["shards"] = 0; changed = True

        # Electrical fields
        if "gas" not in it:             it["gas"] = 0; changed = True
        if "imbued" not in it:          it["imbued"] = 0; changed = True

        # timing / alerts
        if "timestamp" not in it:       it["timestamp"] = time.time(); changed = True
        if "alerted_low" not in it:     it["alerted_low"] = False; changed = True
        if "alerted_empty" not in it:   it["alerted_empty"] = False; changed = True

        # optional metadata
        if "notes" not in it:           it["notes"] = ""; changed = True
        if "alerts_muted" not in it:    it["alerts_muted"] = False; changed = True

        normalized_items.append(it)

    # replace with normalized list
    if normalized_items != items:
        doc["items"] = normalized_items
        changed = True

    # role_id shape
    if not isinstance(doc.get("role_id", None), (int, type(None))):
        doc["role_id"] = None
        changed = True

    return changed

def load_gen_list(name: str) -> List[Dict[str, Any]]:
    doc = _load_gen_doc(name)
    return doc.get("items", [])

def save_gen_list(name: str, items: List[Dict[str, Any]]) -> None:
    doc = _load_gen_doc(name)
    doc["items"] = items
    _save_gen_doc(name, doc)

def delete_gen_list(name: str) -> None:
    p = gen_path(name)
    if os.path.exists(p):
        os.remove(p)
    data = _safe_read_json(GEN_DASHBOARDS_PATH, default={})
    if name in data:
        del data[name]
        _safe_write_json(GEN_DASHBOARDS_PATH, data)

def get_all_gen_list_names() -> List[str]:
    _ensure_dir(GEN_LISTS_DIR)
    names: List[str] = []
    for fname in os.listdir(GEN_LISTS_DIR):
        if fname.endswith(".json"):
            names.append(fname[:-5])
    return sorted(names)

def add_to_gen_list(list_name: str, gen_name: str, gtype: str,
                    element: int, shards: int, gas: int, imbued: int) -> None:
    """Add a generator entry; initialize timestamp and alert flags."""
    doc = _load_gen_doc(list_name)
    items = doc.get("items", [])
    now = time.time()

    if gtype == "Tek":
        item = {
            "name": gen_name,
            "type": "Tek",
            "element": int(element),
            "shards": int(shards),
            "gas": 0,
            "imbued": 0,
            "timestamp": now,
            "alerted_low": False,
            "alerted_empty": False,
            "alerts_muted": False,
            "notes": "",
        }
    else:
        item = {
            "name": gen_name,
            "type": "Electrical",
            "element": 0,
            "shards": 0,
            "gas": int(gas),
            "imbued": int(imbued),
            "timestamp": now,
            "alerted_low": False,
            "alerted_empty": False,
            "alerts_muted": False,
            "notes": "",
        }

    items.append(item)
    doc["items"] = items
    _save_gen_doc(list_name, doc)

def set_gen_list_role(list_name: str, role_id: int) -> None:
    doc = _load_gen_doc(list_name)
    doc["role_id"] = int(role_id)
    _save_gen_doc(list_name, doc)

def get_gen_list_role(list_name: str) -> Optional[int]:
    doc = _load_gen_doc(list_name)
    rid = doc.get("role_id")
    try:
        return int(rid) if rid is not None else None
    except Exception:
        return None

# Generator dashboards (message/channel mapping for gen dashboards)
def get_gen_dashboard_id(list_name: str) -> Optional[Tuple[int, int]]:
    data = _safe_read_json(GEN_DASHBOARDS_PATH, default={})
    v = data.get(list_name)
    if isinstance(v, list) and len(v) == 2:
        try:
            return int(v[0]), int(v[1])
        except Exception:
            return None
    return None

def save_gen_dashboard_id(list_name: str, channel_id: int, message_id: int) -> None:
    data = _safe_read_json(GEN_DASHBOARDS_PATH, default={})
    data[list_name] = [int(channel_id), int(message_id)]
    _safe_write_json(GEN_DASHBOARDS_PATH, data)

# ─────────────────────────── Per-item helpers ────────────────────────────
def _find_gen_item(doc: Dict[str, Any], gen_name: str) -> Tuple[Optional[int], Optional[Dict[str, Any]]]:
    items = doc.get("items", [])
    for idx, it in enumerate(items):
        if it.get("name", "").lower() == gen_name.lower():
            return idx, it
    return None, None

def get_gen_item_notes(list_name: str, gen_name: str) -> Optional[str]:
    doc = _load_gen_doc(list_name)
    _, it = _find_gen_item(doc, gen_name)
    return None if it is None else it.get("notes", "")

def set_gen_item_notes(list_name: str, gen_name: str, notes: str) -> bool:
    doc = _load_gen_doc(list_name)
    idx, it = _find_gen_item(doc, gen_name)
    if it is None:
        return False
    it["notes"] = str(notes)
    doc["items"][idx] = it
    _save_gen_doc(list_name, doc)
    return True

def get_gen_item_alerts_muted(list_name: str, gen_name: str) -> Optional[bool]:
    doc = _load_gen_doc(list_name)
    _, it = _find_gen_item(doc, gen_name)
    return None if it is None else bool(it.get("alerts_muted", False))

def set_gen_item_alerts_muted(list_name: str, gen_name: str, muted: bool) -> bool:
    doc = _load_gen_doc(list_name)
    idx, it = _find_gen_item(doc, gen_name)
    if it is None:
        return False
    it["alerts_muted"] = bool(muted)
    doc["items"][idx] = it
    _save_gen_doc(list_name, doc)
    return True

# ─────────────────────────────── Timers API ─────────────────────────────
def load_timers() -> Dict[str, Any]:
    return _safe_read_json(TIMERS_PATH, default={})

def save_timers(data: Dict[str, Any]) -> None:
    _safe_write_json(TIMERS_PATH, data)

def add_timer(timer_id: str, timer_data: Dict[str, Any]) -> None:
    timers = load_timers()
    timers[timer_id] = timer_data
    save_timers(timers)

def remove_timer(timer_id: str) -> None:
    timers = load_timers()
    if timer_id in timers:
        del timers[timer_id]
        save_timers(timers)
