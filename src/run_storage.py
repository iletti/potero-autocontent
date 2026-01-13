from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import json

from src.model_utils import model_dump
from src.state import CarouselState, SlideBrief


@dataclass(frozen=True)
class RunStorage:
    base_output_dir: Path
    run_id: str
    run_dir: Path
    state_path: Path
    briefs_path: Path

    @classmethod
    def create(cls, base_output_dir: Path, run_id: str) -> "RunStorage":
        run_dir = base_output_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            base_output_dir=base_output_dir,
            run_id=run_id,
            run_dir=run_dir,
            state_path=run_dir / "state.json",
            briefs_path=run_dir / "briefs.json",
        )

    def save_state(self, state: CarouselState) -> None:
        payload = model_dump(state)
        self.state_path.write_text(json.dumps(payload, indent=2))

    def load_state(self) -> Optional[CarouselState]:
        if not self.state_path.exists():
            return None
        payload = json.loads(self.state_path.read_text())
        return _parse_model(CarouselState, payload)

    def save_briefs(self, briefs: List[SlideBrief]) -> None:
        payload = [model_dump(brief) for brief in briefs]
        self.briefs_path.write_text(json.dumps(payload, indent=2))

    def load_briefs(self) -> Optional[List[SlideBrief]]:
        if not self.briefs_path.exists():
            return None
        payload = json.loads(self.briefs_path.read_text())
        if not isinstance(payload, list):
            return None
        return [_parse_model(SlideBrief, item) for item in payload]


def _parse_model(model_cls, payload):
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(payload)
    return model_cls.parse_obj(payload)
