# CODEBASE_MAP

## Top-level structure
- agents.md: system-level overview of the Potero Carousel Factory.
- assets/: reference packs and support data (golden packs, ontologies).
- docs/: operator and architecture documentation.
- output/: run artifacts (state, briefs, generated images).
- scripts/: CI hooks and utility scripts.
- src/: application code (agents, graph orchestration, config, utils).
- tests/: unittest coverage.
- requirements.txt: pinned Python dependencies.
- debug_safety.py: local safety/debug helper.
- venv/: local virtualenv (if present).

## Key modules
- src/main.py: CLI entrypoint, loads config, validates assets, builds graph, runs orchestration.
- src/config.py: environment and path configuration (AppConfig).
- src/graph.py: LangGraph workflow, node wiring, retries, fallback brief logic.
- src/agents/planner.py: brief generation, prompt invariants, and theme templates.
- src/agents/artist.py: image generation calls and output handling.
- src/agents/critic.py: VQA checks and scoring.
- src/agents/editor.py: prompt refinement after critic feedback.
- src/agents/artist_edit.py: localized image edit path.
- src/state.py: core state models (CarouselState, SlideBrief, budgets).
- src/budget.py: budget tracking and enforcement.
- src/asset_registry.py: manifest parsing and asset validation.
- src/reference_selector.py: role-based reference selection.
- src/golden_packs.py: golden pack lookups (assets/potero/golden_reference_packs_v1.json).
- src/preflight.py: brand drift checks and style tightening.
- src/kit_compiler.py: kit consistency enforcement.
- src/reference_quality.py: reference quality scoring.
- src/run_storage.py: load/save state and briefs per run.
- src/upload_cache.py: upload deduping for assets.
- src/interaction_logger.py: per-run interaction logs.
- src/model_utils.py: model normalization and brief update helpers.
- src/logging_utils.py: structured logging config.

## Where configs live
- src/config.py: env vars + defaults (POTERO_* and GOOGLE_API_KEY).
- .env (optional): loaded by python-dotenv in src/main.py.
- assets/references/manifest.json: reference registry and roles.
- assets/potero/: golden packs, intents, and kit ontology.
- requirements.txt: dependency pins.
- scripts/ci.sh: CI command list.
- output/<run_id>/: runtime artifacts and logs.
