"""A directory of JSON files, so a validation run against a frozen Server site can be repeated quickly."""
import json
import os


class JsonCache:
    def __init__(self, directory):
        self.directory = directory
        os.makedirs(directory, exist_ok=True)

    def path(self, key):
        safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in key)
        return os.path.join(self.directory, safe + ".json")

    def get(self, key):
        try:
            with open(self.path(key), encoding="utf-8") as handle:
                return json.load(handle)
        except (FileNotFoundError, ValueError):
            return None

    def set(self, key, value):
        tmp = self.path(key) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(value, handle)
        os.replace(tmp, self.path(key))
