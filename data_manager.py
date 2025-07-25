
import os
import json
import hashlib

# Read storage path from environment, default to './lists/data.json'
DATABASE_PATH = os.getenv("DATABASE_PATH", "./lists/data.json")
# Dashboards file in same directory
DASHBOARDS_PATH = os.getenv("DASHBOARDS_PATH", None)
if DASHBOARDS_PATH is None:
    DASHBOARDS_PATH = os.path.join(os.path.dirname(DATABASE_PATH), "dashboards.json")

# Timers file in same directory
TIMERS_PATH = os.getenv("TIMERS_PATH", None)
if TIMERS_PATH is None:
    TIMERS_PATH = os.path.join(os.path.dirname(DATABASE_PATH), "timers.json")

def _ensure_dir(path):
    base_dir = os.path.dirname(path)
    if base_dir and not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)

# --- List management ---

def _get_list_path(list_name):
    _ensure_dir(DATABASE_PATH)
    base_dir = os.path.dirname(DATABASE_PATH)
    return os.path.join(base_dir, f"{list_name}.json")

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

def add_to_list(list_name, entry, category):
    data = load_list(list_name)
    data.append({"name": entry, "category": category})
    save_list(list_name, data)

def edit_entry(list_name, old_name, new_name, new_category):
    data = load_list(list_name)
    for item in data:
        if item["name"].lower() == old_name.lower():
            item["name"] = new_name
            item["category"] = new_category
            break
    save_list(list_name, data)

def remove_entry(list_name, entry):
    data = load_list(list_name)
    new_data = [item for item in data if item["name"].lower() != entry.lower()]
    save_list(list_name, new_data)

def delete_list(list_name):
    path = _get_list_path(list_name)
    if os.path.exists(path):
        os.remove(path)

def list_exists(list_name):
    return os.path.exists(_get_list_path(list_name))

# --- Dashboard management ---

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

def get_list_hash(list_name):
    data = json.dumps(load_list(list_name), sort_keys=True)
    return hashlib.md5(data.encode()).hexdigest()

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
