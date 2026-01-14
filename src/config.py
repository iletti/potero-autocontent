from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os
import uuid


@dataclass(frozen=True)
class AppConfig:
    root_dir: Path
    output_dir: Path
    assets_dir: Path
    references_dir: Path
    asset_manifest_path: Path
    google_api_key: Optional[str]
    run_id: str
    theme_id: Optional[str]
    design_id: Optional[str]
    potero_shader_version: str
    potero_image_aspect: str
    potero_image_size: str
    potero_allow_warn_pass: bool
    potero_pass_threshold: float
    potero_warn_threshold: float
    potero_enable_edit_mode: bool
    potero_max_refs_per_call: int
    potero_max_refs_hard: int
    potero_anchor_candidates: int
    planner_mode: str
    critic_model: str
    critic_warn_threshold: int
    critic_fail_threshold: int
    max_total_calls: int
    max_planner_calls: int
    max_artist_calls: int
    max_critic_calls: int
    max_editor_calls: int
    max_retries_per_slide: int
    planner_model: str
    artist_model: str
    artist_fallbacks: str
    editor_model: str
    editor_mode: str
    log_level: str
    require_api_key: bool
    require_assets: bool

    def ensure_output_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)


def _parse_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> AppConfig:
    root_dir = Path(__file__).resolve().parents[1]
    output_dir = Path(
        os.getenv("POTERO_OUTPUT_DIR", str(root_dir / "output"))
    )
    assets_dir = Path(
        os.getenv("POTERO_ASSETS_DIR", str(root_dir / "assets"))
    )
    references_dir = Path(
        os.getenv("POTERO_REFERENCES_DIR", str(assets_dir / "references"))
    )
    asset_manifest_path = Path(
        os.getenv(
            "POTERO_ASSET_MANIFEST",
            str(references_dir / "manifest.json"),
        )
    )

    google_api_key = os.getenv("GOOGLE_API_KEY")
    run_id = os.getenv("POTERO_RUN_ID") or uuid.uuid4().hex
    theme_id = os.getenv("POTERO_THEME_ID")
    design_id = os.getenv("POTERO_DESIGN_ID")
    potero_shader_version = os.getenv("POTERO_SHADER_VERSION", "v1_1").strip()
    potero_image_aspect = os.getenv("POTERO_IMAGE_ASPECT", "4:5").strip()
    potero_image_size = os.getenv("POTERO_IMAGE_SIZE", "2K").strip()
    potero_allow_warn_pass = _parse_bool(
        os.getenv("POTERO_ALLOW_WARN_PASS"), False
    )
    potero_pass_threshold = float(
        os.getenv("POTERO_POTERO_PASS_THRESHOLD", "7.5")
    )
    potero_warn_threshold = float(
        os.getenv("POTERO_POTERO_WARN_THRESHOLD", "6.0")
    )
    potero_enable_edit_mode = _parse_bool(
        os.getenv("POTERO_ENABLE_EDIT_MODE"), True
    )
    potero_max_refs_per_call = int(
        os.getenv("POTERO_MAX_REFS_PER_CALL", "10")
    )
    potero_max_refs_hard = int(
        os.getenv("POTERO_MAX_REFS_HARD", "14")
    )
    potero_anchor_candidates = int(
        os.getenv("POTERO_ANCHOR_CANDIDATES", "3")
    )
    planner_mode = os.getenv("POTERO_PLANNER_MODE", "template").strip().lower()
    critic_model = os.getenv("POTERO_CRITIC_MODEL", "gemini-1.5-flash")
    critic_warn_threshold = int(os.getenv("POTERO_CRITIC_WARN_THRESHOLD", "85"))
    critic_fail_threshold = int(os.getenv("POTERO_CRITIC_FAIL_THRESHOLD", "70"))
    max_total_calls = int(os.getenv("POTERO_MAX_TOTAL_CALLS", "50"))
    max_planner_calls = int(os.getenv("POTERO_MAX_PLANNER_CALLS", "2"))
    max_artist_calls = int(os.getenv("POTERO_MAX_ARTIST_CALLS", "15"))
    max_critic_calls = int(os.getenv("POTERO_MAX_CRITIC_CALLS", "15"))
    max_editor_calls = int(os.getenv("POTERO_MAX_EDITOR_CALLS", "5"))
    max_retries_per_slide = int(os.getenv("POTERO_MAX_RETRIES_PER_SLIDE", "3"))
    planner_model = os.getenv("POTERO_PLANNER_MODEL", "gemini-3-pro-preview")
    artist_model = os.getenv("POTERO_ARTIST_MODEL", "gemini-3-pro-image-preview")
    artist_fallbacks = os.getenv(
        "POTERO_ARTIST_FALLBACKS",
        "imagen-3.0-generate-001,gemini-1.5-flash",
    )
    editor_model = os.getenv("POTERO_EDITOR_MODEL", "gemini-3-pro-preview")
    editor_mode = os.getenv("POTERO_EDITOR_MODE", "rules").strip().lower()
    log_level = os.getenv("POTERO_LOG_LEVEL", "INFO").upper()
    require_api_key = _parse_bool(
        os.getenv("POTERO_REQUIRE_API_KEY"), True
    )
    require_assets = _parse_bool(
        os.getenv("POTERO_REQUIRE_ASSETS"), True
    )

    return AppConfig(
        root_dir=root_dir,
        output_dir=output_dir,
        assets_dir=assets_dir,
        references_dir=references_dir,
        asset_manifest_path=asset_manifest_path,
        google_api_key=google_api_key,
        run_id=run_id,
        theme_id=theme_id,
        design_id=design_id,
        potero_shader_version=potero_shader_version,
        potero_image_aspect=potero_image_aspect,
        potero_image_size=potero_image_size,
        potero_allow_warn_pass=potero_allow_warn_pass,
        potero_pass_threshold=potero_pass_threshold,
        potero_warn_threshold=potero_warn_threshold,
        potero_enable_edit_mode=potero_enable_edit_mode,
        potero_max_refs_per_call=potero_max_refs_per_call,
        potero_max_refs_hard=potero_max_refs_hard,
        potero_anchor_candidates=potero_anchor_candidates,
        planner_mode=planner_mode,
        critic_model=critic_model,
        critic_warn_threshold=critic_warn_threshold,
        critic_fail_threshold=critic_fail_threshold,
        max_total_calls=max_total_calls,
        max_planner_calls=max_planner_calls,
        max_artist_calls=max_artist_calls,
        max_critic_calls=max_critic_calls,
        max_editor_calls=max_editor_calls,
        max_retries_per_slide=max_retries_per_slide,
        planner_model=planner_model,
        artist_model=artist_model,
        artist_fallbacks=artist_fallbacks,
        editor_model=editor_model,
        editor_mode=editor_mode,
        log_level=log_level,
        require_api_key=require_api_key,
        require_assets=require_assets,
    )
