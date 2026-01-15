# Potero Autocontent - Implementation Updates

This document summarizes the implementation changes completed in this repo to align with the production-ready Potero standard.

## New assets (locked and versioned)
- `assets/potero/potero_shader_v1_1.txt`
- `assets/potero/potero_negative_v1_1.txt`
- `assets/potero/finnish_kit_ontology_v1.txt`
- `assets/potero/continuum_slide_intents_v1.json`
- `assets/potero/golden_reference_packs_v1.json`

## New or updated docs
- `docs/potero-ai-agent-builder-guide.md`
- `docs/potero-user-guide.md`
- `docs/ai-agent-strategy.md`
- `docs/code-stack.md`

## Config/env vars (new)
- `POTERO_SHADER_VERSION`
- `POTERO_IMAGE_ASPECT`
- `POTERO_IMAGE_SIZE`
- `POTERO_ALLOW_WARN_PASS`
- `POTERO_POTERO_PASS_THRESHOLD`
- `POTERO_POTERO_WARN_THRESHOLD`
- `POTERO_ENABLE_EDIT_MODE`
- `POTERO_MAX_REFS_PER_CALL`
- `POTERO_MAX_REFS_HARD`
- `POTERO_ANCHOR_CANDIDATES`

## Prompt compilation
- Planner injects locked shader/negative blocks directly into briefs.

## Brief schema (internal)
`SlideBrief` now includes:
- `intent`, `continuum_cue`, `kit_anchors`, `env_preset`, `lighting_signature`, `risk_profile`, `reference_roles_required`
- `image_aspect`, `image_size`

## Manifest schema (role-based)
`assets/references/manifest.json` now supports role/tag entries:

```json
{
  "designs": {
    "rk_hoodie": [
      {"path": "hoodies/hoodie_rk_black_front.webp", "role": "DESIGN_FRONT"},
      {"path": "hoodies/hoodie_rk_black_back.webp", "role": "DESIGN_BACK"},
      {"path": "hoodies/hoodie_rk_black_side.webp", "role": "DESIGN_SIDE"}
    ]
  }
}
```

## Reference selection
- `src/reference_selector.py` selects deterministic roles with caps.
- Role selection can inject golden packs per `env_preset`.
- Quality scoring favors higher-resolution refs when PIL is available.
 - Reference caching uses file hash + role keys.

## Preflight + kit consistency
- `src/preflight.py`: brand drift scan (text-only) with constraint injection.
- `src/kit_compiler.py`: downgrades risky scenes if required role refs are missing.

## Critic schema and repair routing
- `src/agents/critic.py` now returns OPSEC + Potero scoring fields and repair hints.
- `src/agents/editor.py` adds `style_tighten` and `defect_fix` modes.
- `src/agents/artist_edit.py` adds edit-mode image calls.
- `src/graph.py` routes edit-mode failures to ArtistEdit, otherwise regen via Editor.
- Anchor candidate scoring consumes critic budget and is capped to prevent runaway cost.

## Fallback behavior
- `build_fallback_brief` now rotates Potero-safe fallback templates.

## Anchor candidate pool
- Slide 1 uses a candidate pool (default 3) and picks the best by critic score.

## Warn-pass tightening
- When OPSEC passes but PoteroScore is below the pass threshold, a style-tighten delta is injected on the next slide.

## Logging
- Reference selection now logs role counts and quality scores.
- Critic repair targets are logged for diagnostics.

## Tests added
- `tests/test_reference_selector.py`
- `tests/test_edit_mode_routing.py`
- `tests/test_fallback_templates.py`
