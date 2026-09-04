"""Persistent HOOK scopes and robust .hkd storage."""
from __future__ import annotations
from pathlib import Path
import json
import tempfile
import os

class HKDError(Exception): pass

class HKD:
    VERSION = 2
    def __init__(self, path): self.path = Path(path).expanduser().resolve()
    def load(self, default=None):
        if not self.path.exists(): return default if default is not None else {}
        try:
            obj = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(obj, dict) or obj.get("version") not in (1, self.VERSION): raise HKDError("invalid .hkd file")
            return obj.get("data", {})
        except (OSError, json.JSONDecodeError) as e: raise HKDError(f"cannot read {self.path}: {e}") from e
    def save(self, data, scope="phone", owner=None):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": self.VERSION, "scope": scope, "owner": owner, "data": data}
        fd, tmp = tempfile.mkstemp(prefix=".hook-", suffix=".hkd", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2, default=str); f.write("\n"); f.flush(); os.fsync(f.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)

class PersistentScope:
    def __init__(self, root, name):
        self.root = Path(root).expanduser().resolve(); self.name = name
        self.file = self.root / ".hook" / f"{name}.hkd"; self.values = HKD(self.file).load({})
    def get(self, key, default=None): return self.values.get(key, default)
    def set(self, key, value): self.values[key] = value; HKD(self.file).save(self.values, self.name, self.name)
    def delete(self, key):
        if key in self.values: del self.values[key]; HKD(self.file).save(self.values, self.name, self.name)
    def all(self): return dict(self.values)

class PersistentScopes:
    """Stable storage for folder and phone-wide HOOK variables across CLI processes."""
    def __init__(self, phone_root=None):
        self.phone_root = Path(phone_root or Path.home()).expanduser().resolve()
    def phone(self): return PersistentScope(self.phone_root, "phone")
    def folder(self, folder): return PersistentScope(Path(folder), "folder")
