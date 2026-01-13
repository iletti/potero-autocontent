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

class SlideState(BaseModel):
    index: int
    status: str = "pending" # pending, in_progress, completed, failed, fallback_pending
    image_path: Optional[str] = None
    qa_score: Optional[int] = None
    qa_status: Optional[str] = None # pass, warn, fail
    retry_count: int = 0
    last_critic_feedback: Optional[str] = None

class CarouselState(BaseModel):
    carousel_id: str
    global_constraints: GlobalConstraints
    slides: List[SlideState] = Field(default_factory=list)
    current_slide_index: int = 0
    budget: RunBudget = Field(default_factory=RunBudget)

class SlideBrief(BaseModel):
    index: int
    shot_type: str
    positive_prompt: str
    negative_prompt: str
    reference_assets: List[str]
    composition_guidance: Optional[str] = None
