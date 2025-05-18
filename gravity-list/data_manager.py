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

    def delete_list(self, guild_id, list_name):
        guild = self.db.get(guild_id, {})
        lists = guild.get('lists', {})
        if list_name in lists:
            del lists[list_name]
            self._save()
            return True
        return False

    def add_entry(self, guild_id, list_name, entry, category):
        list_obj = self.db[guild_id]['lists'][list_name]
        list_obj['entries'].append({'entry': entry, 'category': category})
        self._save()

    def edit_entry(self, guild_id, list_name, old_entry, new_entry, new_category):
        list_obj = self.db[guild_id]['lists'][list_name]
        for e in list_obj['entries']:
            if e['entry'] == old_entry:
                e['entry'] = new_entry
                e['category'] = new_category
                self._save()
                return True
        return False

    def get_list(self, guild_id, list_name):
        return self.db[guild_id]['lists'].get(list_name)

    def set_message_metadata(self, guild_id, list_name, channel_id, message_id):
        list_obj = self.db[guild_id]['lists'][list_name]
        list_obj['channel_id'] = channel_id
        list_obj['message_id'] = message_id
        self._save()
