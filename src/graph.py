import logging
from pathlib import Path
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from src.budget import can_consume, consume
from src.state import CarouselState, SlideBrief
from src.agents.planner import Planner
from src.agents.artist import Artist
from src.agents.critic import Critic
from src.agents.editor import Editor
from src.run_storage import RunStorage

class GraphState(TypedDict):
    carousel_state: CarouselState
    briefs: List[SlideBrief]
    retry_count: int
    critic_passed: bool
    critic_feedback: Optional[str]
    skip_validation: bool

def build_fallback_brief(index: int, environment: str) -> SlideBrief:
    return SlideBrief(
        index=index,
        shot_type="fallback_texture",
        positive_prompt=(
            "Low risk texture shot of discarded gear on forest floor, "
            f"{environment}, foggy, static, harsh flash, high ISO, crushed blacks."
        ),
        negative_prompt=(
            "unapproved text, text, letters, words, typography, slogans, "
            "numbers, watermark, face, eyes, unapproved logo, flag, "
            "patch, name tape, bright colors, studio lighting"
        ),
        reference_assets=[],
        composition_guidance="Leave top-left quadrant empty for typography."
    )

def create_graph(
    planner: Optional[Planner] = None,
    artist: Optional[Artist] = None,
    critic: Optional[Critic] = None,
    editor: Optional[Editor] = None,
    storage: Optional[RunStorage] = None,
):
    logger = logging.getLogger(__name__)
    planner = planner or Planner()
    artist = artist or Artist()
    critic = critic or Critic()
    editor = editor or Editor()

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
        persist_state(state["carousel_state"], briefs)
        return {"briefs": briefs}

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

        brief = state["briefs"][current_idx]
        try:
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
        allow_llm = editor.uses_llm() and can_consume(carousel.budget, "editor")
        if editor.uses_llm() and not allow_llm:
            logger.warning(
                "budget_exceeded_editor",
                extra={"slide_index": current_idx + 1},
            )
        if allow_llm:
            consume(carousel.budget, "editor")
        briefs[current_idx] = editor.refine_brief(
            briefs[current_idx],
            state.get("critic_feedback") or "",
            reference_assets=briefs[current_idx].reference_assets,
            allow_llm=allow_llm,
        )
        persist_state(carousel, briefs)
        return {"briefs": briefs}

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
            briefs[current_idx].index, carousel.global_constraints.environment
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

        return "retry"

    workflow = StateGraph(GraphState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("artist", artist_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("editor", editor_node)
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
            "fallback": "fallback",
            "end": END,
        },
    )

    workflow.add_edge("advance", "artist")
    workflow.add_edge("editor", "artist")
    workflow.add_edge("fallback", "artist")

    return workflow
