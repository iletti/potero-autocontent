# RUNBOOK

## Prereqs
- Install deps: `pip install -r requirements.txt`
- Ensure reference assets exist and are registered in `assets/references/manifest.json`.
- Provide `GOOGLE_API_KEY` or set `POTERO_REQUIRE_API_KEY=false` for no-API runs.

## Run the app
Option A (CLI args):
`python -m src.main --theme winter_ambush --design hoodie_013_ranger_green`

Option B (env-driven):
`POTERO_THEME_ID=winter_ambush POTERO_DESIGN_ID=hoodie_013_ranger_green python -m src.main`

Outputs land in `output/<run_id>/`:
- `state.json`, `briefs.json`, `interaction_log.md`, `slide_<index>.png`

## Tests and checks
- Unit tests: `python -m unittest discover -s tests`
- Smoke check (no API key/assets):
  `POTERO_REQUIRE_API_KEY=false POTERO_REQUIRE_ASSETS=false python scripts/smoke_check.py`
- CI hook: `sh scripts/ci.sh`

## Utilities
- List available models: `python scripts/list_models.py`
- Verify manifest entries: `python scripts/verify_manifest.py`

## Common pitfalls
- Missing `GOOGLE_API_KEY` with `POTERO_REQUIRE_API_KEY=true` (default) exits early.
- Missing or mismatched assets in `assets/references/manifest.json` with
  `POTERO_REQUIRE_ASSETS=true` (default) fails validation.
- Reusing `POTERO_RUN_ID` with different theme/design/config causes resume mismatch
  checks to abort the run in `src/main.py`.
- `scripts/verify_manifest.py` has a hardcoded path; update the `root` path before use.
- `langgraph` import errors will prevent workflow creation; ensure dependencies are
  installed from `requirements.txt`.
