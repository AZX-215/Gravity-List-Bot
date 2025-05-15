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
                return json.load(f)
        return {"items": [], "view_message_id": None}

    def save(self, channel_id, channel_name, data):
        path = self._get_filepath(channel_id, channel_name)
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)

    def add_name(self, channel_id, channel_name, name):
        data = self.load(channel_id, channel_name)
        data["items"].append({"name": name, "category": None, "struck": False})
        self.save(channel_id, channel_name, data)

    def edit_name(self, channel_id, channel_name, old_name, new_name):
        data = self.load(channel_id, channel_name)
        for item in data["items"]:
            if item["name"] == old_name:
                item["name"] = new_name
                break
        self.save(channel_id, channel_name, data)

    def strike_name(self, channel_id, channel_name, name):
        data = self.load(channel_id, channel_name)
        for item in data["items"]:
            if item["name"] == name:
                item["struck"] = not item["struck"]
                break
        self.save(channel_id, channel_name, data)

    def categorize_name(self, channel_id, channel_name, name, category):
        data = self.load(channel_id, channel_name)
        for item in data["items"]:
            if item["name"] == name:
                item["category"] = category
                break
        self.save(channel_id, channel_name, data)

    def remove_name(self, channel_id, channel_name, name):
        data = self.load(channel_id, channel_name)
        data["items"] = [item for item in data["items"] if item["name"] != name]
        self.save(channel_id, channel_name, data)

    def get_items(self, channel_id, channel_name):
        data = self.load(channel_id, channel_name)
        return data.get("items", [])

    def get_view_message(self, channel_id, channel_name):
        data = self.load(channel_id, channel_name)
        return data.get("view_message_id")

    def set_view_message(self, channel_id, channel_name, message_id):
        data = self.load(channel_id, channel_name)
        data["view_message_id"] = message_id
        self.save(channel_id, channel_name, data)

    def delete_list(self, channel_id, channel_name):
        path = self._get_filepath(channel_id, channel_name)
        if os.path.exists(path):
            os.remove(path)
