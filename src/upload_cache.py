from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class UploadCache:
    client: Any
    cache: Dict[str, Any] = field(default_factory=dict)

    def get(self, path: Path) -> Optional[Any]:
        return self.cache.get(str(path.resolve()))

    def add(self, path: Path, handle: Any) -> Any:
        self.cache[str(path.resolve())] = handle
        return handle

    def upload(self, path: Path) -> Any:
        cached = self.get(path)
        if cached is not None:
            return cached
        handle = self.client.files.upload(file=str(path))
        return self.add(path, handle)
