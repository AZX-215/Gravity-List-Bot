import json
import os

class DataManager:
    def __init__(self, path='data.json'):
        self.path = path
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {}

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.db, f, indent=2)

    def guild_exists(self, guild_id):
        return guild_id in self.db

    def initialize_guild(self, guild_id):
        if guild_id in self.db:
            return False
        self.db[guild_id] = {'categories': {}}
        self._save()
        return True

    def add_name(self, guild_id, category, name):
        guild_data = self.db.setdefault(guild_id, {'categories': {}})
        guild_data['categories'].setdefault(category, []).append(name)
        self._save()

    def get_names(self, guild_id, category):
        return self.db.get(guild_id, {}).get('categories', {}).get(category, [])
