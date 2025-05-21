import os
import json

# Read storage path from environment, default to './lists/data.json'
DATABASE_PATH = os.getenv("DATABASE_PATH", "./lists/data.json")
# Dashboards file in same directory
DASHBOARDS_PATH = os.getenv("DASHBOARDS_PATH", None)
if DASHBOARDS_PATH is None:
    DASHBOARDS_PATH = os.path.join(os.path.dirname(DATABASE_PATH), "dashboards.json")

def _ensure_dir(path):
    base_dir = os.path.dirname(path)
    if base_dir and not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)

def _get_list_path(list_name):
    _ensure_dir(DATABASE_PATH)
    base_dir = os.path.dirname(DATABASE_PATH)
    filename = f"{list_name}.json"
    return os.path.join(base_dir, filename)

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

# Dashboard management

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
