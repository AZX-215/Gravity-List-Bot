import os
import json

DATA_DIR = "lists"

def _ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def _get_list_path(list_name):
    _ensure_data_dir()
    return os.path.join(DATA_DIR, f"{list_name}.json")

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
    for entry in data:
        if entry["name"].lower() == old_name.lower():
            entry["name"] = new_name
            entry["category"] = new_category
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
