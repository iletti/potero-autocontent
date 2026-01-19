from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class RunBudget(BaseModel):
    max_total_calls: int = 50
    max_planner_calls: int = 2
    max_artist_calls: int = 15
    max_critic_calls: int = 15
    max_editor_calls: int = 5
    max_retries_per_slide: int = 3
    total_calls: int = 0
    planner_calls: int = 0
    artist_calls: int = 0
    critic_calls: int = 0
    editor_calls: int = 0
    exceeded: bool = False

class GlobalConstraints(BaseModel):
    design_id_locked: str
    environment: str
    aspect_ratio: str = "4:5"
    potero_shader_version: str = "v1_2"
    image_aspect: str = "4:5"
    image_size: str = "2K"
    allow_warn_pass: bool = False
    potero_pass_threshold: float = 7.5
    potero_warn_threshold: float = 6.0
    enable_edit_mode: bool = True
    max_refs_per_call: int = 10
    max_refs_hard: int = 14
    anchor_candidates: int = 3

class SlideState(BaseModel):
    index: int
    status: str = "pending" # pending, in_progress, completed, failed, fallback_pending
    image_path: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    qa_score: Optional[int] = None
    qa_status: Optional[str] = None # pass, warn, fail
    retry_count: int = 0
    last_critic_feedback: Optional[str] = None
    opsec_pass: Optional[bool] = None
    potero_score: Optional[float] = None
    potero_breakdown: Optional[Dict[str, int]] = None
    repair_mode: Optional[str] = None
    repair_targets: List[str] = Field(default_factory=list)
    repair_instructions: Optional[str] = None

class CarouselState(BaseModel):
    carousel_id: str
    global_constraints: GlobalConstraints
    slides: List[SlideState] = Field(default_factory=list)
    current_slide_index: int = 0
    budget: RunBudget = Field(default_factory=RunBudget)
    style_tighten_next: bool = False

class SlideBrief(BaseModel):
    index: int
    shot_type: str
    positive_prompt: str
    negative_prompt: str
    reference_assets: List[str]
    composition_guidance: Optional[str] = None
    potero_shader_version: str = "v1_2"
    intent: Optional[str] = None
    continuum_cue: Optional[str] = None
    kit_anchors: List[str] = Field(default_factory=list)
    env_preset: Optional[str] = None
    lighting_signature: Optional[str] = None
    risk_profile: Optional[str] = None
    reference_roles_required: List[str] = Field(default_factory=list)
    reference_roles_selected: List[str] = Field(default_factory=list)
    asset_role_map: Dict[str, str] = Field(default_factory=dict)
    image_aspect: Optional[str] = None
    image_size: Optional[str] = None
