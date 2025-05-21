import os
import json

# Read storage path from environment, default to './lists/data.json'
DATABASE_PATH = os.getenv("DATABASE_PATH", "./lists/data.json")

def _ensure_data_dir():
    # Ensure the containing directory exists
    dir_path = os.path.dirname(DATABASE_PATH)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

def _get_list_path(list_name):
    _ensure_data_dir()
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
