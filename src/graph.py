import logging
from pathlib import Path
from typing import TypedDict, List, Optional

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    StateGraph = None
    END = None
    LANGGRAPH_AVAILABLE = False
from src.budget import can_consume, consume
from src.state import CarouselState, SlideBrief
from src.model_utils import update_model
from src.agents.planner import Planner
from src.reference_selector import select_reference_assets
from src.kit_compiler import apply_kit_consistency
from src.preflight import apply_brand_drift_preflight, apply_style_tighten
from src.agents.artist import Artist
from src.agents.critic import Critic
from src.agents.editor import Editor
from src.agents.artist_edit import ArtistEdit
from src.run_storage import RunStorage

class GraphState(TypedDict):
    carousel_state: CarouselState
    briefs: List[SlideBrief]
    retry_count: int
    critic_passed: bool
    critic_feedback: Optional[str]
    skip_validation: bool

def build_fallback_brief(
    index: int,
    environment: str,
    potero_shader_version: str,
) -> SlideBrief:
    fallback_templates = [
        {
            "shot_type": "fallback_edge_human",
            "positive_prompt": (
                "Anonymous edge-of-human detail: gloved hands, coffee steam, "
                "technical fabric edge, pine needles or rough concrete, harsh flash, "
                "high ISO grain, crushed blacks. No faces, no weapons."
            ),
            "negative_prompt": (
                "readable text, labels, logos, faces, eyes, skin, weapon, "
                "patch, name tape, bright colors, studio lighting, woodland camouflage"
            ),
            "composition_guidance": "Leave the top-left quadrant empty.",
        },
        {
            "shot_type": "fallback_gear_layout",
            "positive_prompt": (
                "Top-down gear layout on wool blanket or rough wood, "
                "ranger green gear details, props like kuksa or nokipannu, harsh flash, "
                "grainy, no readable labels."
            ),
            "negative_prompt": (
                "readable text, labels, logos, faces, eyes, skin, weapon, "
                "patch, name tape, bright colors, studio lighting, woodland camouflage"
            ),
            "composition_guidance": "Leave the upper-right quadrant empty.",
        },
        {
            "shot_type": "fallback_environment_only",
            "positive_prompt": (
                "Environment-only Potero mood: Finnish taiga night or shelter "
                "corridor, flash hotspot, noise, crushed blacks, no people."
            ),
            "negative_prompt": (
                "readable text, labels, logos, faces, eyes, skin, weapon, "
                "patch, name tape, bright colors, studio lighting"
            ),
            "composition_guidance": "Leave the top band empty.",
        },
    ]
    template = fallback_templates[(index - 1) % len(fallback_templates)]
    return SlideBrief(
        index=index,
        shot_type=template["shot_type"],
        positive_prompt=f"{template['positive_prompt']} Environment: {environment}.",
        negative_prompt=template["negative_prompt"],
        reference_assets=[],
        composition_guidance=template["composition_guidance"],
        potero_shader_version=potero_shader_version,
    )

def create_graph(
    planner: Optional[Planner] = None,
    artist: Optional[Artist] = None,
    critic: Optional[Critic] = None,
    editor: Optional[Editor] = None,
    artist_edit: Optional[ArtistEdit] = None,
    storage: Optional[RunStorage] = None,
):
    if not LANGGRAPH_AVAILABLE:
        raise RuntimeError("langgraph is required to build the workflow.")
    logger = logging.getLogger(__name__)
    planner = planner or Planner()
    artist = artist or Artist()
    critic = critic or Critic()
    editor = editor or Editor()
    artist_edit = artist_edit or ArtistEdit()

    def persist_state(carousel: CarouselState, briefs: List[SlideBrief]) -> None:
        if not storage:
            return
        storage.save_state(carousel)
        storage.save_briefs(briefs)

    def planner_node(state: GraphState):
        logger.info("planner_node_start")
        if state["briefs"]:
            return {}
        briefs = planner.generate_briefs(state["carousel_state"])
        
        # Apply consistency checks once during planning
        registry = planner.registry if planner else None
        env = state["carousel_state"].global_constraints.environment
        
        refined_briefs = []
        for b in briefs:
            b = apply_kit_consistency(b, registry)
            b, _ = apply_brand_drift_preflight(b, env)
            refined_briefs.append(b)
            
        persist_state(state["carousel_state"], refined_briefs)
        return {"briefs": refined_briefs}

    def artist_node(state: GraphState):
        carousel = state["carousel_state"]
        current_idx = carousel.current_slide_index
        logger.info(
            "artist_node_start",
            extra={"slide_index": current_idx + 1},
        )

        anchor_path = None
        if current_idx > 0:
            anchor_path = carousel.slides[0].image_path
            logger.info(
                "anchor_context_injected",
                extra={"anchor_path": anchor_path},
            )

        current_slide = carousel.slides[current_idx]
        if current_slide.status == "completed" and current_slide.image_path:
            image_path = Path(current_slide.image_path)
            if image_path.exists():
                logger.info(
                    "artist_skip_completed",
                    extra={"slide_index": current_idx + 1},
                )
                return {"skip_validation": True}
            logger.warning(
                "completed_slide_missing_file",
                extra={"slide_index": current_idx + 1},
            )
            current_slide.status = "failed"

        if not consume(carousel.budget, "artist"):
            carousel.slides[current_idx].status = "failed"
            carousel.slides[current_idx].last_critic_feedback = (
                "Budget exceeded for artist generation."
            )
            persist_state(carousel, state["briefs"])
            logger.error(
                "budget_exceeded_artist",
                extra={"slide_index": current_idx + 1},
            )
            return {"carousel_state": carousel, "skip_validation": True}

        brief = state["briefs"][current_idx]
        if carousel.style_tighten_next:
            brief = apply_style_tighten(brief)
            carousel.style_tighten_next = False
            state["briefs"][current_idx] = brief

        state["briefs"][current_idx] = brief
        persist_state(carousel, state["briefs"])
        if planner and planner.registry and brief.reference_roles_required:
            reference_assets, role_map, score_map = select_reference_assets(
                brief=brief,
                registry=planner.registry,
                max_refs=carousel.global_constraints.max_refs_per_call,
                hard_cap=carousel.global_constraints.max_refs_hard,
                anchor_path=anchor_path,
                assets_dir=planner.potero_assets_dir,
            )
            
            # Flatten role_map (Role -> [Paths]) to asset_role_map (Path -> Role)
            # This allows the Artist to label each image contextually
            asset_map = {}
            for role, paths in role_map.items():
                for path in paths:
                    asset_map[path] = role
            
            brief = update_model(
                brief,
                {
                    "reference_assets": reference_assets,
                    "asset_role_map": asset_map,
                },
            )
            state["briefs"][current_idx] = brief
            persist_state(carousel, state["briefs"])
            logger.info(
                "reference_selection",
                extra={
                    "slide_index": current_idx + 1,
                    "roles": list(role_map.keys()),
                    "role_counts": {
                        role: len(paths) for role, paths in role_map.items()
                    },
                    "selected_count": len(reference_assets),
                    "scores": score_map,
                },
            )
        try:
            if current_idx == 0 and carousel.global_constraints.anchor_candidates > 1:
                remaining_critic_for_candidates = (
                    carousel.budget.max_critic_calls
                    - carousel.budget.critic_calls
                    - 1
                )
                desired_candidates = (
                    carousel.global_constraints.anchor_candidates
                    if remaining_critic_for_candidates > 0
                    else 1
                )
                candidate_count = 1
                for _ in range(desired_candidates - 1):
                    if consume(carousel.budget, "artist"):
                        candidate_count += 1
                    else:
                        break
                candidates = artist.generate_candidates(
                    brief=brief,
                    anchor_image_path=anchor_path,
                    count=candidate_count,
                )
                best_path = None
                best_score = -1
                available_critic = remaining_critic_for_candidates
                for candidate_path in candidates:
                    if available_critic <= 0:
                        break
                    if not consume(carousel.budget, "critic"):
                        break
                    available_critic -= 1
                    candidate_result = critic.validate_image(
                        candidate_path,
                        reference_assets=brief.reference_assets,
                    )
                    score = candidate_result.get("qa_score") or 0
                    if candidate_result.get("opsec_pass") is False:
                        score = -1
                    if score > best_score:
                        best_score = score
                        best_path = candidate_path
                image_path = best_path or candidates[0]
            else:
                image_path = artist.generate_image(brief, anchor_path)
        except Exception as exc:
            retry_count = state["retry_count"] + 1
            carousel.slides[current_idx].status = "failed"
            carousel.slides[current_idx].retry_count = retry_count
            carousel.slides[current_idx].last_critic_feedback = str(exc)
            persist_state(carousel, state["briefs"])
            logger.error(
                "artist_generation_failed",
                extra={
                    "slide_index": current_idx + 1,
                    "error": str(exc),
                },
            )
            return {
                "carousel_state": carousel,
                "critic_passed": False,
                "critic_feedback": str(exc),
                "retry_count": retry_count,
                "skip_validation": True,
            }
        current_slide.image_path = image_path
        current_slide.status = "in_progress"

        persist_state(carousel, state["briefs"])
        return {"carousel_state": carousel, "skip_validation": False}

    def critic_node(state: GraphState):
        carousel = state["carousel_state"]
        current_idx = carousel.current_slide_index
        logger.info(
            "critic_node_start",
            extra={"slide_index": current_idx + 1},
        )

        if carousel.budget.exceeded:
            carousel.slides[current_idx].status = "failed"
            carousel.slides[current_idx].last_critic_feedback = (
                "Budget exceeded."
            )
            persist_state(carousel, state["briefs"])
            return {
                "carousel_state": carousel,
                "critic_passed": False,
                "critic_feedback": "Budget exceeded.",
                "retry_count": state["retry_count"],
                "skip_validation": False,
            }

        if state.get("skip_validation"):
            if carousel.slides[current_idx].status == "completed":
                persist_state(carousel, state["briefs"])
                return {
                    "carousel_state": carousel,
                    "critic_passed": True,
                    "critic_feedback": "Skipped validation (already completed).",
                    "retry_count": 0,
                    "skip_validation": False,
                }
            persist_state(carousel, state["briefs"])
            return {
                "carousel_state": carousel,
                "critic_passed": False,
                "critic_feedback": "Skipped validation due to earlier failure.",
                "retry_count": state["retry_count"],
                "skip_validation": False,
            }

        image_path = carousel.slides[current_idx].image_path
        if not image_path:
            feedback = "No image path available for validation."
            retry_count = state["retry_count"] + 1
            carousel.slides[current_idx].status = "failed"
            carousel.slides[current_idx].retry_count = retry_count
            carousel.slides[current_idx].last_critic_feedback = feedback
            persist_state(carousel, state["briefs"])
            return {
                "carousel_state": carousel,
                "critic_passed": False,
                "critic_feedback": feedback,
                "retry_count": retry_count,
                "skip_validation": False,
            }

        if not consume(carousel.budget, "critic"):
            carousel.slides[current_idx].status = "failed"
            carousel.slides[current_idx].last_critic_feedback = (
                "Budget exceeded for critic."
            )
            persist_state(carousel, state["briefs"])
            return {
                "carousel_state": carousel,
                "critic_passed": False,
                "critic_feedback": "Budget exceeded for critic.",
                "retry_count": state["retry_count"],
                "skip_validation": False,
            }

        brief = state["briefs"][current_idx]
        result = critic.validate_image(
            image_path,
            reference_assets=brief.reference_assets,
        )
        if result.get("fatal"):
            carousel.budget.exceeded = True
            carousel.slides[current_idx].status = "failed"
            carousel.slides[current_idx].last_critic_feedback = result.get(
                "feedback", "Critic fatal error."
            )
            persist_state(carousel, state["briefs"])
            logger.error(
                "critic_fatal_error",
                extra={"slide_index": current_idx + 1},
            )
            return {
                "carousel_state": carousel,
                "critic_passed": False,
                "critic_feedback": result.get("feedback", ""),
                "retry_count": state["retry_count"],
                "skip_validation": False,
            }
        passed = bool(result.get("pass"))
        feedback = result.get("feedback", "")
        qa_status = result.get("qa_status")
        carousel.slides[current_idx].qa_score = result.get("qa_score")
        carousel.slides[current_idx].qa_status = qa_status
        carousel.slides[current_idx].last_critic_feedback = feedback
        carousel.slides[current_idx].opsec_pass = result.get("opsec_pass")
        carousel.slides[current_idx].potero_score = result.get("potero_score")
        breakdown = result.get("potero_breakdown")
        if isinstance(breakdown, dict):
            carousel.slides[current_idx].potero_breakdown = breakdown
        carousel.slides[current_idx].repair_mode = result.get("repair_mode")
        carousel.slides[current_idx].repair_targets = result.get("repair_targets") or []
        carousel.slides[current_idx].repair_instructions = result.get(
            "repair_instructions"
        )
        if carousel.slides[current_idx].repair_targets:
            logger.info(
                "critic_repair_targets",
                extra={
                    "slide_index": current_idx + 1,
                    "repair_mode": carousel.slides[current_idx].repair_mode,
                    "repair_targets": carousel.slides[current_idx].repair_targets,
                },
            )

        if passed:
            carousel.slides[current_idx].status = "completed"
            if qa_status == "warn":
                logger.warning(
                    "critic_warning",
                    extra={
                        "slide_index": current_idx + 1,
                        "feedback": feedback,
                        "qa_score": result.get("qa_score"),
                    },
                )
                carousel.style_tighten_next = True
            persist_state(carousel, state["briefs"])
            return {
                "carousel_state": carousel,
                "critic_passed": True,
                "critic_feedback": feedback,
                "retry_count": 0,
                "skip_validation": False,
            }

        retry_count = state["retry_count"] + 1
        carousel.slides[current_idx].status = "failed"
        carousel.slides[current_idx].retry_count = retry_count
        persist_state(carousel, state["briefs"])
        return {
            "carousel_state": carousel,
            "critic_passed": False,
            "critic_feedback": feedback,
            "retry_count": retry_count,
            "skip_validation": False,
        }

    def editor_node(state: GraphState):
        carousel = state["carousel_state"]
        current_idx = carousel.current_slide_index
        logger.info(
            "editor_node_start",
            extra={"slide_index": current_idx + 1},
        )

        briefs = list(state["briefs"])
        briefs[current_idx] = editor.refine_with_mode(
            briefs[current_idx],
            {
                "opsec_pass": carousel.slides[current_idx].opsec_pass,
                "potero_score": carousel.slides[current_idx].potero_score,
                "repair_mode": carousel.slides[current_idx].repair_mode,
                "repair_instructions": carousel.slides[current_idx].repair_instructions,
            },
        )
        allow_llm = editor.uses_llm() and can_consume(carousel.budget, "editor")
        if editor.uses_llm() and not allow_llm:
            logger.warning(
                "budget_exceeded_editor",
                extra={"slide_index": current_idx + 1},
            )
        if allow_llm:
            consume(carousel.budget, "editor")
        brief = editor.refine_brief(
            briefs[current_idx],
            state.get("critic_feedback") or "",
            reference_assets=briefs[current_idx].reference_assets,
            allow_llm=allow_llm,
        )
        
        # Re-apply consistency to the newly refined brief
        brief = apply_kit_consistency(brief, planner.registry if planner else None)
        brief, preflight = apply_brand_drift_preflight(
            brief, 
            carousel.global_constraints.environment
        )
        if preflight.reasons:
             logger.info("editor_preflight_warning", extra={"reasons": preflight.reasons})
             
        briefs[current_idx] = brief
        persist_state(carousel, briefs)
        return {"briefs": briefs}

    def artist_edit_node(state: GraphState):
        carousel = state["carousel_state"]
        current_idx = carousel.current_slide_index
        logger.info(
            "artist_edit_node_start",
            extra={"slide_index": current_idx + 1},
        )
        brief = state["briefs"][current_idx]
        instructions = carousel.slides[current_idx].repair_instructions or ""
        image_path = carousel.slides[current_idx].image_path
        if not image_path:
            return {"critic_passed": False, "skip_validation": True}
        try:
            edited_path = artist_edit.edit_image(
                brief=brief,
                image_path=image_path,
                instructions=instructions,
            )
        except Exception as exc:
            logger.error(
                "artist_edit_failed",
                extra={
                    "slide_index": current_idx + 1,
                    "error": str(exc),
                },
            )
            retry_count = state["retry_count"] + 1
            carousel.slides[current_idx].retry_count = retry_count
            persist_state(carousel, state["briefs"])
            return {
                "carousel_state": carousel,
                "critic_passed": False,
                "critic_feedback": f"Edit failed: {str(exc)}",
                "retry_count": retry_count,
                "skip_validation": True,
            }
        carousel.slides[current_idx].image_path = edited_path
        carousel.slides[current_idx].status = "in_progress"
        persist_state(carousel, state["briefs"])
        return {"carousel_state": carousel, "skip_validation": False}

    def advance_node(state: GraphState):
        carousel = state["carousel_state"]
        carousel.current_slide_index += 1
        persist_state(carousel, state["briefs"])
        return {
            "carousel_state": carousel,
            "retry_count": 0,
            "critic_passed": False,
            "critic_feedback": None,
            "skip_validation": False,
        }

    def fallback_node(state: GraphState):
        carousel = state["carousel_state"]
        current_idx = carousel.current_slide_index
        logger.warning(
            "fallback_triggered",
            extra={"slide_index": current_idx + 1},
        )

        briefs = list(state["briefs"])
        briefs[current_idx] = build_fallback_brief(
            briefs[current_idx].index,
            carousel.global_constraints.environment,
            carousel.global_constraints.potero_shader_version,
        )
        carousel.slides[current_idx].status = "fallback_pending"
        persist_state(carousel, briefs)
        return {
            "briefs": briefs,
            "carousel_state": carousel,
            "retry_count": 0,
            "critic_passed": False,
            "critic_feedback": None,
            "skip_validation": False,
        }

    def route_after_critic(state: GraphState):
        carousel = state["carousel_state"]
        current_idx = carousel.current_slide_index

        if carousel.budget.exceeded:
            return "end"

        if state["critic_passed"]:
            if current_idx >= len(carousel.slides) - 1:
                return "end"
            return "advance"

        if state["retry_count"] >= carousel.budget.max_retries_per_slide:
            return "fallback"

        repair_mode = carousel.slides[current_idx].repair_mode
        if repair_mode == "edit" and carousel.global_constraints.enable_edit_mode:
            return "edit"

        return "retry"

    workflow = StateGraph(GraphState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("artist", artist_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("editor", editor_node)
    workflow.add_node("artist_edit", artist_edit_node)
    workflow.add_node("advance", advance_node)
    workflow.add_node("fallback", fallback_node)

    workflow.set_entry_point("planner")

    workflow.add_edge("planner", "artist")
    workflow.add_edge("artist", "critic")

    workflow.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "advance": "advance",
            "retry": "editor",
            "edit": "artist_edit",
            "fallback": "fallback",
            "end": END,
        },
    )

    workflow.add_edge("advance", "artist")
    workflow.add_edge("editor", "artist")
    workflow.add_edge("artist_edit", "critic")
    workflow.add_edge("fallback", "artist")

    return workflow
