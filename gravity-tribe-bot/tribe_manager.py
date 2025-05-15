import json
import os
import re

class TribeManager:
    def __init__(self, directory='lists'):
        self.directory = directory
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)

    def _sanitize(self, name):
        return re.sub(r'[^\w\-]', '_', name.lower())

    def _get_filepath(self, channel_id, channel_name):
        safe_name = self._sanitize(channel_name)
        return os.path.join(self.directory, f"{safe_name}-{channel_id}.json")

    def create_list(self, channel_id, channel_name):
        path = self._get_filepath(channel_id, channel_name)
        if not os.path.exists(path):
            data = {"items": [], "view_message_id": None}
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)

    def list_exists(self, channel_id, channel_name):
        return os.path.exists(self._get_filepath(channel_id, channel_name))

    def load(self, channel_id, channel_name):
        path = self._get_filepath(channel_id, channel_name)
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {"items": [], "view_message_id": None}
                else:
                    data.setdefault("items", [])
                    data.setdefault("view_message_id", None)
                return data
        return {"items": [], "view_message_id": None}

    def save(self, channel_id, channel_name, data):
        path = self._get_filepath(channel_id, channel_name)
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)

    def add_name(self, channel_id, channel_name, name, category=None):
        data = self.load(channel_id, channel_name)
        items = data.setdefault("items", [])
        items.append({"name": name, "category": category, "struck": False})
        self.save(channel_id, channel_name, data)

    def edit_name(self, channel_id, channel_name, old_name, new_name=None, category=None):
        data = self.load(channel_id, channel_name)
        for item in data.get("items", []):
            if item["name"] == old_name:
                if new_name is not None:
                    item["name"] = new_name
                if category is not None:
                    item["category"] = category
                break
        self.save(channel_id, channel_name, data)

    def strike_name(self, channel_id, channel_name, name):
        data = self.load(channel_id, channel_name)
        for item in data.get("items", []):
            if item["name"] == name:
                item["struck"] = not item["struck"]
                break
        self.save(channel_id, channel_name, data)

    def remove_name(self, channel_id, channel_name, name):
        data = self.load(channel_id, channel_name)
        data["items"] = [item for item in data.get("items", []) if item["name"] != name]
        self.save(channel_id, channel_name, data)

    def get_items(self, channel_id, channel_name):
        return self.load(channel_id, channel_name).get("items", [])

    def get_view_message(self, channel_id, channel_name):
        return self.load(channel_id, channel_name).get("view_message_id")

    def set_view_message(self, channel_id, channel_name, message_id):
        data = self.load(channel_id, channel_name)
        data["view_message_id"] = message_id
        self.save(channel_id, channel_name, data)

    def delete_list(self, channel_id, channel_name):
        path = self._get_filepath(channel_id, channel_name)
        if os.path.exists(path):
            os.remove(path)
