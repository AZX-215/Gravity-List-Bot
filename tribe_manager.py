import json
import os
import re

class TribeManager:
    def __init__(self, directory='lists'):
        self.directory = directory
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)

    def _sanitize(self, name):
        # Replace non-alphanumeric, underscore, or hyphen with underscore
        return re.sub(r'[^\w\-]', '_', name)

    def _get_filepath(self, channel_id, channel_name):
        safe_name = self._sanitize(channel_name.lower().replace(' ', '_'))
        filename = f"{safe_name}-{channel_id}.json"
        return os.path.join(self.directory, filename)

    def create_list(self, channel_id, channel_name):
        path = self._get_filepath(channel_id, channel_name)
        if not os.path.exists(path):
            data = {"list": [], "view_message_id": None}
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)

    def list_exists(self, channel_id, channel_name):
        return os.path.exists(self._get_filepath(channel_id, channel_name))

    def load_data(self, channel_id, channel_name):
        path = self._get_filepath(channel_id, channel_name)
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return {"list": [], "view_message_id": None}

    def save_data(self, channel_id, channel_name, data):
        path = self._get_filepath(channel_id, channel_name)
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)

    def add_name(self, channel_id, channel_name, name):
        data = self.load_data(channel_id, channel_name)
        data["list"].append(name)
        self.save_data(channel_id, channel_name, data)

    def edit_name(self, channel_id, channel_name, old_name, new_name):
        data = self.load_data(channel_id, channel_name)
        try:
            idx = data["list"].index(old_name)
            data["list"][idx] = new_name
            self.save_data(channel_id, channel_name, data)
        except ValueError:
            pass

    def remove_name(self, channel_id, channel_name, name):
        data = self.load_data(channel_id, channel_name)
        try:
            data["list"].remove(name)
            self.save_data(channel_id, channel_name, data)
        except ValueError:
            pass

    def get_list(self, channel_id, channel_name):
        data = self.load_data(channel_id, channel_name)
        return data["list"]

    def get_view_message(self, channel_id, channel_name):
        data = self.load_data(channel_id, channel_name)
        return data.get("view_message_id")

    def set_view_message(self, channel_id, channel_name, message_id):
        data = self.load_data(channel_id, channel_name)
        data["view_message_id"] = message_id
        self.save_data(channel_id, channel_name, data)

    def delete_list(self, channel_id, channel_name):
        path = self._get_filepath(channel_id, channel_name)
        if os.path.exists(path):
            os.remove(path)
