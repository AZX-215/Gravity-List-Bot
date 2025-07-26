
import os
import json
import hashlib
import time

# Paths for standard lists, dashboards, timers, and generator lists
DATABASE_PATH = os.getenv("DATABASE_PATH", "./lists/data.json")
DASHBOARDS_PATH = os.getenv("DASHBOARDS_PATH") or os.path.join(os.path.dirname(DATABASE_PATH), "dashboards.json")
TIMERS_PATH = os.getenv("TIMERS_PATH") or os.path.join(os.path.dirname(DATABASE_PATH), "timers.json")
GEN_LISTS_DIR = os.path.join(os.path.dirname(DATABASE_PATH), "generator_lists")
GEN_DASHBOARDS_PATH = os.getenv("GEN_DASHBOARDS_PATH") or os.path.join(os.path.dirname(DATABASE_PATH), "generator_dashboards.json")

def _ensure_dir(path):
    base = os.path.dirname(path)
    if base and not os.path.exists(base):
        os.makedirs(base, exist_ok=True)

# --- Standard list management ---

def _get_list_path(list_name):
    _ensure_dir(DATABASE_PATH)
    base = os.path.dirname(DATABASE_PATH)
    return os.path.join(base, f"{list_name}.json")

def save_list(list_name, data):
    path = _get_list_path(list_name)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_list(list_name):
    path = _get_list_path(list_name)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []

def delete_list(list_name):
    path = _get_list_path(list_name)
    if os.path.exists(path):
        os.remove(path)

def list_exists(list_name):
    return os.path.exists(_get_list_path(list_name))

def get_all_list_names():
    _ensure_dir(DATABASE_PATH)
    base = os.path.dirname(DATABASE_PATH)
    names = [f[:-5] for f in os.listdir(base) if f.endswith(".json")]
    return sorted(names)

# --- Standard dashboards ---

def _load_dashboards():
    _ensure_dir(DASHBOARDS_PATH)
    if os.path.exists(DASHBOARDS_PATH):
        with open(DASHBOARDS_PATH, "r") as f:
            return json.load(f)
    return {}

def _save_dashboards(data):
    _ensure_dir(DASHBOARDS_PATH)
    with open(DASHBOARDS_PATH, "w") as f:
        json.dump(data, f, indent=2)

def save_dashboard_id(list_name, channel_id, message_id):
    data = _load_dashboards()
    data[list_name] = {"channel_id": channel_id, "message_id": message_id}
    _save_dashboards(data)

def get_dashboard_id(list_name):
    data = _load_dashboards()
    dash = data.get(list_name)
    if dash:
        return dash["channel_id"], dash["message_id"]
    return None

def get_all_dashboards():
    return _load_dashboards()

# --- Timer management ---

def load_timers():
    _ensure_dir(TIMERS_PATH)
    if os.path.exists(TIMERS_PATH):
        with open(TIMERS_PATH, "r") as f:
            return json.load(f)
    return {}

def save_timers(data):
    _ensure_dir(TIMERS_PATH)
    with open(TIMERS_PATH, "w") as f:
        json.dump(data, f, indent=2)

def add_timer(timer_id, timer_data):
    timers = load_timers()
    timers[timer_id] = timer_data
    save_timers(timers)

def remove_timer(timer_id):
    timers = load_timers()
    if timer_id in timers:
        timers.pop(timer_id)
        save_timers(timers)

# --- Generator list management ---

def _get_gen_list_path(list_name):
    _ensure_dir(GEN_LISTS_DIR + "/.placeholder")
    return os.path.join(GEN_LISTS_DIR, f"{list_name}.json")

def save_gen_list(list_name, data):
    path = _get_gen_list_path(list_name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_gen_list(list_name):
    path = _get_gen_list_path(list_name)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []

def delete_gen_list(list_name):
    path = _get_gen_list_path(list_name)
    if os.path.exists(path):
        os.remove(path)

def gen_list_exists(list_name):
    return os.path.exists(_get_gen_list_path(list_name))

def get_all_gen_list_names():
    _ensure_dir(GEN_LISTS_DIR + "/.placeholder")
    if not os.path.exists(GEN_LISTS_DIR):
        return []
    names = [f[:-5] for f in os.listdir(GEN_LISTS_DIR) if f.endswith(".json")]
    return sorted(names)

def add_to_gen_list(list_name, entry_name, gen_type, element, shards, gas, imbued):
    data = load_gen_list(list_name)
    data.append({
        "name": entry_name,
        "type": gen_type,
        "element": element,
        "shards": shards,
        "gas": gas,
        "imbued": imbued,
        "timestamp": time.time()
    })
    save_gen_list(list_name, data)

# --- Generator dashboards ---

def _load_gen_dashboards():
    _ensure_dir(GEN_DASHBOARDS_PATH)
    if os.path.exists(GEN_DASHBOARDS_PATH):
        with open(GEN_DASHBOARDS_PATH, "r") as f:
            return json.load(f)
    return {}

def _save_gen_dashboards(data):
    _ensure_dir(GEN_DASHBOARDS_PATH)
    with open(GEN_DASHBOARDS_PATH, "w") as f:
        json.dump(data, f, indent=2)

def save_gen_dashboard_id(list_name, channel_id, message_id):
    data = _load_gen_dashboards()
    data[list_name] = {"channel_id": channel_id, "message_id": message_id}
    _save_gen_dashboards(data)

def get_gen_dashboard_id(list_name):
    data = _load_gen_dashboards()
    dash = data.get(list_name)
    if dash:
        return dash["channel_id"], dash["message_id"]
    return None

def get_all_gen_dashboards():
    return _load_gen_dashboards()

# --- Hashing ---

def get_list_hash(list_name):
    return hashlib.md5(json.dumps(load_list(list_name), sort_keys=True).encode()).hexdigest()

def get_gen_list_hash(list_name):
    return hashlib.md5(json.dumps(load_gen_list(list_name), sort_keys=True).encode()).hexdigest()
