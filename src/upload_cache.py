from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional
import json


@dataclass
class UploadCache:
    client: Any
    cache: Dict[str, Any] = field(default_factory=dict)
    name_cache: Dict[str, str] = field(default_factory=dict)
    cache_path: Optional[Path] = None

    def __post_init__(self) -> None:
        self._load_cache()

    def get(self, path: Path, role: Optional[str] = None) -> Optional[Any]:
        return self.cache.get(self._cache_key(path, role))

    def add(self, path: Path, handle: Any, role: Optional[str] = None) -> Any:
        cache_key = self._cache_key(path, role)
        self.cache[cache_key] = handle
        handle_name = getattr(handle, "name", None)
        if isinstance(handle_name, str) and handle_name:
            self.name_cache[cache_key] = handle_name
            self._persist_cache()
        return handle

    def upload(self, path: Path, role: Optional[str] = None) -> Any:
        cache_key = self._cache_key(path, role)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        cached_name = self.name_cache.get(cache_key)
        if cached_name:
            try:
                handle = self.client.files.get(name=cached_name)
                self.cache[cache_key] = handle
                return handle
            except Exception:
                self.name_cache.pop(cache_key, None)
                self._persist_cache()
        handle = self.client.files.upload(file=str(path))
        self.cache[cache_key] = handle
        handle_name = getattr(handle, "name", None)
        if isinstance(handle_name, str) and handle_name:
            self.name_cache[cache_key] = handle_name
            self._persist_cache()
        return handle

    def _cache_key(self, path: Path, role: Optional[str]) -> str:
        resolved = path.resolve()
        digest = _hash_file(resolved)
        role_tag = role or "unassigned"
        return f"{resolved}:{digest}:{role_tag}"

    def _load_cache(self) -> None:
        if not self.cache_path:
            return
        try:
            payload = json.loads(self.cache_path.read_text())
        except FileNotFoundError:
            return
        except json.JSONDecodeError:
            return
        if isinstance(payload, dict):
            entries = payload.get("files", payload)
            if isinstance(entries, dict):
                self.name_cache = {
                    str(key): value
                    for key, value in entries.items()
                    if isinstance(value, str)
                }

    def _persist_cache(self) -> None:
        if not self.cache_path:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"files": self.name_cache}
        self.cache_path.write_text(json.dumps(payload, indent=2))


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()
