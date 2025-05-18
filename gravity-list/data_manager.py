import json
import os

class DataManager:
    def __init__(self, path='lists/data.json'):
        self.path = path
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w') as f:
            json.dump(self.db, f, indent=2)

    def initialize_guild(self, guild_id):
        if guild_id in self.db:
            return False
        self.db[guild_id] = {'lists': {}}
        self._save()
        return True

    def create_list(self, guild_id, list_name):
        guild = self.db.setdefault(guild_id, {'lists': {}})
        lists = guild['lists']
        if list_name in lists:
            return False
        lists[list_name] = {
            'entries': [],
            'message_id': None,
            'channel_id': None
        }
        self._save()
        return True

    def add_entry(self, guild_id, list_name, entry, category):
        list_obj = self.db[guild_id]['lists'][list_name]
        list_obj['entries'].append({'entry': entry, 'category': category})
        self._save()

    def get_list(self, guild_id, list_name):
        return self.db[guild_id]['lists'].get(list_name)

    def set_message_metadata(self, guild_id, list_name, channel_id, message_id):
        list_obj = self.db[guild_id]['lists'][list_name]
        list_obj['channel_id'] = channel_id
        list_obj['message_id'] = message_id
        self._save()
