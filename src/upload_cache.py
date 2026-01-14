from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class UploadCache:
    client: Any
    cache: Dict[str, Any] = field(default_factory=dict)

    def get(self, path: Path, role: Optional[str] = None) -> Optional[Any]:
        return self.cache.get(self._cache_key(path, role))

    def add(self, path: Path, handle: Any, role: Optional[str] = None) -> Any:
        self.cache[self._cache_key(path, role)] = handle
        return handle

    def upload(self, path: Path, role: Optional[str] = None) -> Any:
        cached = self.get(path, role)
        if cached is not None:
            return cached
        handle = self.client.files.upload(file=str(path))
        return self.add(path, handle, role)

    def _cache_key(self, path: Path, role: Optional[str]) -> str:
        resolved = path.resolve()
        digest = _hash_file(resolved)
        role_tag = role or "unassigned"
        return f"{resolved}:{digest}:{role_tag}"


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()
