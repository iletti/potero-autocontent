import argparse
import logging
from dotenv import load_dotenv
from src.agents.planner import Planner
from src.agents.artist import Artist
from src.agents.critic import Critic
from src.agents.editor import Editor
from src.agents.artist_edit import ArtistEdit
from src.asset_registry import AssetRegistry, AssetRegistryError
from src.config import load_config
from src.graph import create_graph, GraphState
from src.logging_utils import configure_logging
from src.run_storage import RunStorage
from src.state import RunBudget
from src.upload_cache import UploadCache

load_dotenv()


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Potero Carousel Factory runner"
    )
    parser.add_argument(
        "--theme",
        dest="theme_id",
        help="Theme ID for the carousel run",
    )
    parser.add_argument(
        "--design",
        dest="design_id",
        help="Design ID for the carousel run",
    )
    return parser.parse_args()


def _first_incomplete_index(state):
    for idx, slide in enumerate(state.slides):
        if slide.status != "completed":
            return idx
        if not slide.image_path:
            return idx
    return None


def _parse_fallbacks(value: str):
    return [item.strip() for item in value.split(",") if item.strip()]

def _normalize_model_name(name: str) -> str:
    if not name:
        return name
    if name.startswith("models/"):
        return name
    return f"models/{name}"


def main():
    from google import genai
    app_config = load_config()
    configure_logging(app_config)
    logger = logging.getLogger(__name__)

    logger.info("potero_carousel_factory_start")

    if app_config.require_api_key and not app_config.google_api_key:
        logger.error("missing_google_api_key")
        return

    client = None
    if app_config.google_api_key:
        client = genai.Client(api_key=app_config.google_api_key)

    app_config.ensure_output_dir()

    args = _parse_args()
    theme = args.theme_id or app_config.theme_id
    design = args.design_id or app_config.design_id

    missing_inputs = []
    if not theme:
        missing_inputs.append("theme")
    if not design:
        missing_inputs.append("design")
    if missing_inputs:
        logger.error(
            "missing_runtime_inputs",
            extra={"missing": missing_inputs},
        )
        return

    registry = None
    try:
        registry = AssetRegistry.load(
            references_dir=app_config.references_dir,
            manifest_path=app_config.asset_manifest_path,
        )
        missing_assets = registry.validate()
        required_missing = []
        if app_config.require_assets:
            required_missing = registry.validate_required(design)
        if missing_assets or required_missing:
            logger.error(
                "missing_reference_assets",
                extra={
                    "missing_assets": missing_assets,
                    "missing_required_assets": required_missing,
                },
            )
            if app_config.require_assets:
                return
        logger.info(
            "reference_assets_validated",
            extra={"asset_count": registry.asset_count()},
        )
    except AssetRegistryError as exc:
        logger.error("asset_registry_error", extra={"error": str(exc)})
        if app_config.require_assets:
            return

    storage = RunStorage.create(
        base_output_dir=app_config.output_dir,
        run_id=app_config.run_id,
    )

    run_budget = RunBudget(
        max_total_calls=app_config.max_total_calls,
        max_planner_calls=app_config.max_planner_calls,
        max_artist_calls=app_config.max_artist_calls,
        max_critic_calls=app_config.max_critic_calls,
        max_editor_calls=app_config.max_editor_calls,
        max_retries_per_slide=app_config.max_retries_per_slide,
    )

    if not client:
        logger.error("missing_genai_client")
        return
    upload_cache = UploadCache(client=client)

    # Initialize components
    planner = Planner(
        model_name=_normalize_model_name(app_config.planner_model),
        registry=registry,
        planner_mode=app_config.planner_mode,
        potero_shader_version=app_config.potero_shader_version,
        potero_image_aspect=app_config.potero_image_aspect,
        potero_image_size=app_config.potero_image_size,
        potero_allow_warn_pass=app_config.potero_allow_warn_pass,
        potero_pass_threshold=app_config.potero_pass_threshold,
        potero_warn_threshold=app_config.potero_warn_threshold,
        potero_enable_edit_mode=app_config.potero_enable_edit_mode,
        potero_max_refs_per_call=app_config.potero_max_refs_per_call,
        potero_max_refs_hard=app_config.potero_max_refs_hard,
        potero_anchor_candidates=app_config.potero_anchor_candidates,
        potero_assets_dir=app_config.assets_dir,
        client=client,
    )
    fallbacks = [
        _normalize_model_name(model)
        for model in _parse_fallbacks(app_config.artist_fallbacks)
    ]
    artist = Artist(
        model_name=_normalize_model_name(app_config.artist_model),
        output_dir=storage.run_dir,
        upload_cache=upload_cache,
        client=client,
        fallbacks=fallbacks,
    )
    critic = Critic(
        model_name=_normalize_model_name(app_config.critic_model),
        warn_threshold=app_config.critic_warn_threshold,
        fail_threshold=app_config.critic_fail_threshold,
        potero_pass_threshold=app_config.potero_pass_threshold,
        potero_warn_threshold=app_config.potero_warn_threshold,
        allow_warn_pass=app_config.potero_allow_warn_pass,
        upload_cache=upload_cache,
        client=client,
    )
    editor = Editor(
        model_name=_normalize_model_name(app_config.editor_model),
        mode=app_config.editor_mode,
        client=client,
        upload_cache=upload_cache,
    )
    artist_edit = ArtistEdit(
        model_name=_normalize_model_name(app_config.artist_model),
        output_dir=storage.run_dir,
        upload_cache=upload_cache,
        client=client,
    )
    
    # 1. Plan the carousel
    state = storage.load_state()
    briefs = storage.load_briefs()

    if state:
        if state.budget:
            if state.budget.max_total_calls != run_budget.max_total_calls:
                logger.error("budget_mismatch_max_total")
                return
            if state.budget.max_planner_calls != run_budget.max_planner_calls:
                logger.error("budget_mismatch_max_planner")
                return
            if state.budget.max_artist_calls != run_budget.max_artist_calls:
                logger.error("budget_mismatch_max_artist")
                return
            if state.budget.max_critic_calls != run_budget.max_critic_calls:
                logger.error("budget_mismatch_max_critic")
                return
            if state.budget.max_editor_calls != run_budget.max_editor_calls:
                logger.error("budget_mismatch_max_editor")
                return
            if (
                state.budget.max_retries_per_slide
                != run_budget.max_retries_per_slide
            ):
                logger.error("budget_mismatch_max_retries")
                return
        if state.global_constraints.environment != theme:
            logger.error(
                "theme_mismatch_for_run",
                extra={
                    "run_id": app_config.run_id,
                    "expected": state.global_constraints.environment,
                    "received": theme,
                },
            )
            return
        if state.global_constraints.design_id_locked != design:
            logger.error(
                "design_mismatch_for_run",
                extra={
                    "run_id": app_config.run_id,
                    "expected": state.global_constraints.design_id_locked,
                    "received": design,
                },
            )
            return
        if (
            state.global_constraints.potero_shader_version
            != app_config.potero_shader_version
        ):
            logger.error(
                "shader_version_mismatch_for_run",
                extra={
                    "run_id": app_config.run_id,
                    "expected": state.global_constraints.potero_shader_version,
                    "received": app_config.potero_shader_version,
                },
            )
            return
        if (
            state.global_constraints.image_aspect
            != app_config.potero_image_aspect
        ):
            logger.error(
                "image_aspect_mismatch_for_run",
                extra={
                    "run_id": app_config.run_id,
                    "expected": state.global_constraints.image_aspect,
                    "received": app_config.potero_image_aspect,
                },
            )
            return
        if (
            state.global_constraints.image_size
            != app_config.potero_image_size
        ):
            logger.error(
                "image_size_mismatch_for_run",
                extra={
                    "run_id": app_config.run_id,
                    "expected": state.global_constraints.image_size,
                    "received": app_config.potero_image_size,
                },
            )
            return
        if (
            state.global_constraints.allow_warn_pass
            != app_config.potero_allow_warn_pass
        ):
            logger.error(
                "allow_warn_pass_mismatch_for_run",
                extra={
                    "run_id": app_config.run_id,
                    "expected": state.global_constraints.allow_warn_pass,
                    "received": app_config.potero_allow_warn_pass,
                },
            )
            return
        if (
            state.global_constraints.potero_pass_threshold
            != app_config.potero_pass_threshold
        ):
            logger.error(
                "potero_pass_threshold_mismatch_for_run",
                extra={
                    "run_id": app_config.run_id,
                    "expected": state.global_constraints.potero_pass_threshold,
                    "received": app_config.potero_pass_threshold,
                },
            )
            return
        if (
            state.global_constraints.potero_warn_threshold
            != app_config.potero_warn_threshold
        ):
            logger.error(
                "potero_warn_threshold_mismatch_for_run",
                extra={
                    "run_id": app_config.run_id,
                    "expected": state.global_constraints.potero_warn_threshold,
                    "received": app_config.potero_warn_threshold,
                },
            )
            return
        if (
            state.global_constraints.enable_edit_mode
            != app_config.potero_enable_edit_mode
        ):
            logger.error(
                "edit_mode_mismatch_for_run",
                extra={
                    "run_id": app_config.run_id,
                    "expected": state.global_constraints.enable_edit_mode,
                    "received": app_config.potero_enable_edit_mode,
                },
            )
            return
        if (
            state.global_constraints.max_refs_per_call
            != app_config.potero_max_refs_per_call
        ):
            logger.error(
                "max_refs_per_call_mismatch_for_run",
                extra={
                    "run_id": app_config.run_id,
                    "expected": state.global_constraints.max_refs_per_call,
                    "received": app_config.potero_max_refs_per_call,
                },
            )
            return
        if (
            state.global_constraints.max_refs_hard
            != app_config.potero_max_refs_hard
        ):
            logger.error(
                "max_refs_hard_mismatch_for_run",
                extra={
                    "run_id": app_config.run_id,
                    "expected": state.global_constraints.max_refs_hard,
                    "received": app_config.potero_max_refs_hard,
                },
            )
            return
        if (
            state.global_constraints.anchor_candidates
            != app_config.potero_anchor_candidates
        ):
            logger.error(
                "anchor_candidates_mismatch_for_run",
                extra={
                    "run_id": app_config.run_id,
                    "expected": state.global_constraints.anchor_candidates,
                    "received": app_config.potero_anchor_candidates,
                },
            )
            return
        state.current_slide_index = _first_incomplete_index(state)
        if state.current_slide_index is None:
            logger.info("run_already_complete", extra={"run_id": app_config.run_id})
            return
        logger.info(
            "resuming_run",
            extra={
                "run_id": app_config.run_id,
                "current_slide_index": state.current_slide_index + 1,
            },
        )
    else:
        state = planner.plan_carousel(theme, design, budget=run_budget)
        storage.save_state(state)
        logger.info("plan_created", extra={"carousel_id": state.carousel_id})

    if not briefs:
        briefs = planner.generate_briefs(state)
        storage.save_briefs(briefs)
        storage.save_state(state)
    
    # 2. Setup the Graph
    workflow = create_graph(
        planner=planner,
        artist=artist,
        critic=critic,
        editor=editor,
        artist_edit=artist_edit,
        storage=storage,
    )
    app = workflow.compile()
    
    # 3. Run the orchestration
    initial_state = GraphState(
        carousel_state=state,
        briefs=briefs,
        retry_count=0,
        critic_passed=False,
        critic_feedback=None,
        skip_validation=False,
    )
    
    # For simulation, we'll just run a few slides
    logger.info("swarm_orchestration_start")
    run_config = {"recursion_limit": 50}
    app.invoke(initial_state, run_config)

    logger.info("swarm_orchestration_complete")
    logger.info(
        "outputs_available",
        extra={"output_dir": str(storage.run_dir)},
    )

if __name__ == "__main__":
    main()
