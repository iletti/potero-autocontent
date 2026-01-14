# Potero Autocontent - AI Agent Builder Guide (Production-Ready)

This guide is for implementing Potero Standard + Finnish technical realism in the existing LangGraph loop (Planner -> Artist -> Critic -> Editor -> Fallback). It is written to be directly actionable in this repo.

---

## 0) Definition of done (slide acceptance gates)

A slide becomes completed only if both gates pass:

Gate A - OPSEC (hard fail)
- Fail immediately if any:
  - identifiable face (clear facial features)
  - readable text/logos/watermarks/patch lettering
  - disallowed symbols/insignia
  - cosplay drift elements that expose identity (name tape, unit patch readable)

Gate B - Potero Standard (hard fail below threshold)
- potero_score >= 7.5
- Minimum sub-scores:
  - lighting >= 2/3 (on-axis harsh flash signature present)
  - authenticity >= 2/3 (Finnish identity cues are present)

If OPSEC passes but PoteroScore is 6.0-7.4: return warn (optionally allow pass), but force style-tightening injection on the next attempt/next slide.

---

## 1) Make Potero Standard a locked, versioned artifact

Create immutable assets that are never rewritten by LLMs. Treat these as "brand shaders".

Files
- `assets/potero/potero_shader_v1_1.txt`
- `assets/potero/potero_negative_v1_1.txt`
- `assets/potero/finnish_kit_ontology_v1.txt`
- `assets/potero/continuum_slide_intents_v1.json`

Config
- `POTERO_SHADER_VERSION=v1_1`
- Persist version in `output/<run_id>/state.json` and `briefs.json`

Injection rule

Planner always injects, in order:
1. potero_shader (locked)
2. slide-specific content (theme + intent + shot type)
3. kit constraints (from ontology; slide-appropriate)
4. potero_negative (locked)
5. composition guidance

Never allow LLM editor to modify the shader/negative blocks. Only add deltas outside them.

---

## 2) Brief schema upgrade (internal blueprint, deterministic compilation)

Current SlideBrief:
- shot_type
- positive_prompt
- negative_prompt
- reference_assets
- composition_guidance

Add these fields (internal; they compile into text prompts + ref packs):
- intent (enum): domestic_front | mobilization | transition | field_wait | artifact_detail
- continuum_cue (string): subtle story anchor (coffee ritual, kotivara water, shelter waiting)
- kit_anchors (list): must-show silhouettes/features (RK95 muzzle, Savotta PALS grid, belt dump pouch)
- env_preset (enum): taiga_summer | taiga_winter_kaamos | cqb_osb | industrial_hall | shelter_brutalist
- lighting_signature (enum): lofi_flash_on_axis (always), plus mood (kaamos, fluorescent shelter)
- risk_profile (enum): low | medium | high (high = weapons + hands + faces risk)
- reference_roles_required (list): see Section 3

These make prompts compiler output, not free text vibes.

---

## 3) Reference system: role-based packs (stop attach everything)

### 3.1 Reference roles (manifest + registry)

Extend `assets/references/manifest.json` to tag each asset with a role and optional tags.

Roles (recommended baseline)
- IDENTITY_ANCHOR (slide 1 final image becomes this for slides 2-5)
- TEXTURE_M05_WOODLAND, TEXTURE_M05_SNOW
- WEAPON_RK95_LEFT, WEAPON_RK95_RIGHT, WEAPON_RK95_MUZZLE_CLOSE
- GEAR_PLATE_CARRIER_LAYOUT, GEAR_POUCHES_DETAIL, GEAR_BELT_DUMP_POUCH
- GEAR_HELMET_HIGH_CUT, GEAR_HEADSET_COMTAC
- GEAR_BACKPACK_JAAKARI_34, GEAR_PALS_CLOSE, GEAR_STRAPS_CONNECT
- ENV_TAIGA_WINTER_KAAMOS, ENV_TAIGA_SUMMER_NIGHT, ENV_CQB_OSB, ENV_INDUSTRIAL_HALL, ENV_SHELTER
- PROP_KUKSA, PROP_NOKIPANNU, PROP_WATER_CAN, PROP_GEAR_MAINTENANCE

### 3.2 Reference selection algorithm (deterministic)

Goal: strong adherence without dilution.

Rules
- Target 6-10 total refs per call.
- Hard cap 14 (model limit).
- Always include:
  - 1x environment vibe (ENV_*)
  - 1x M05 texture (matching season)
  - If weapon in scene: 1x RK95 silhouette + 1x muzzle close
  - If Savotta shown: 1x backpack 3/4 + 1x PALS close
  - If plate carrier: 1x layout + 1x pouch detail
  - Slides 2-5: include slide 1 output as IDENTITY_ANCHOR

If model fidelity drops (drift):
- Reduce to fewer, higher-signal refs (do not add more)

### 3.3 Upload caching (already present)

Keep UploadCache. Extend cache key to include file hash + role (so you can track which role caused drift).

---

## 4) Model invocation: align Artist with Nano Banana Pro usage

Current usage:
- `generate_images` (Imagen)
- `generate_content` (text and multimodal)

For Nano Banana Pro (Gemini 3 Pro Image preview), use `generate_content` and pass:
- text prompt
- reference images as parts
- image config:
  - aspect ratio 4:5
  - image size 2K default, 4K for PALS-heavy / texture-critical slides

Keep Imagen as fallback only.

Recommended env vars
- `POTERO_IMAGE_ASPECT=4:5`
- `POTERO_IMAGE_SIZE=2K|4K`
- `POTERO_ARTIST_MODEL=gemini-3-pro-image-preview`
- `POTERO_ARTIST_FALLBACKS=imagen-3.0-generate-001,...`

---

## 5) Prompt compiler: enforce a consistent prompt structure

Do not let Planner output raw prose. Build a deterministic template:

Positive prompt structure (always same order)
1. Potero Shader (locked)
2. Scene: intent + env_preset + time_of_day + season
3. Subject: "Finnish reservist realism" + pose/action ("waiting/maintenance/fatigue", not hero)
4. Kit anchors: must-show items + silhouettes + key features
5. Composition: framing + what must be visible
6. "No readable text/logos; anonymity preserved" (reinforcement)

Negative prompt structure
1. Potero Negative (locked)
2. Additional slide-specific bans:
   - if winter: "no warm golden light"
   - if M05: "no pixelated/digital squares"
   - if weapon: "no AR-15/M4 silhouette"
   - if high-risk hands: "hands not centered; avoid fingers close to camera"

This keeps behavior stable and testable.

---

## 6) Critic v2: dual scoring + local defect targeting

### 6.1 Critic output JSON (strict)

Extend Critic output to include:

```json
{
  "pass": true,
  "fatal": false,
  "qa_score": 8.7,
  "qa_status": "pass",
  "opsec_pass": true,
  "opsec_violations": [],
  "potero_score": 8.1,
  "potero_breakdown": {
    "lighting": 3,
    "texture": 2,
    "authenticity": 2,
    "narrative": 1,
    "anti_warcore": 0,
    "composition_imperfect": 1
  },
  "potero_fail_reasons": [],
  "violations": [],
  "feedback": "short actionable text",
  "repair_mode": "edit",
  "repair_targets": ["weapon_muzzle", "pals_grid"],
  "repair_instructions": "single paragraph instruction for edit",
  "confidence": 0.82
}
```

### 6.2 Add crop critic stage (high impact)

Before scoring the full image, run checks on crops:
- weapon muzzle region
- stock/receiver region
- PALS/webbing region
- shoulder strap connection region
- M05 fabric region

Implementation option:
- First call: Gemini Flash returns bounding boxes for these targets (or approximate coordinates).
- Second call(s): Critic evaluates each crop and returns local failures.

If crop checks fail -> set `repair_mode="edit"` and specify `repair_targets`.

---

## 7) Editor v2: two modes - style-tighten vs defect-fix

Current Editor focuses on constraint reassertion. Add two deterministic behaviors:

Mode A - style_tighten (Potero drift)
- Triggered when opsec_pass=true but potero_score < threshold.
- Editor outputs a delta:
  - increase on-axis flash emphasis
  - add high ISO sensor noise + color noise
  - enforce Nordic palette (no warm)
  - enforce candid imperfections
  - ban influencer warcore cues

Mode B - defect_fix (local technical failure)
- Triggered when Critic returns `repair_mode="edit"`.
- Editor outputs:
  - edit instruction text (for image editing call)
  - optional crop/mask plan if supported

Keep this deterministic; do not rewrite whole prompts.

---

## 8) Add an Edit path to the graph (do not regen everything)

Right now you regenerate after failures. Add a new node:
- ArtistEdit node: takes last image + repair_instructions + references (especially the relevant role refs) and performs an edit call.

Routing changes
- Critic fail + repair_mode="edit" -> ArtistEdit -> Critic
- Critic fail + repair_mode="regen" -> Editor -> Artist -> Critic
- Retries exhausted -> Potero-safe fallback (see Section 9)

This reduces the "fix one thing, break three" problem.

---

## 9) Replace generic fallback with Potero-safe fallback

Current fallback drops references and produces generic textures. Replace with 3 Potero-safe fallback templates (still reference-driven, low OPSEC risk):

1) Anonymous edge-of-human
- gloves + coffee steam + M05 fabric edge + pine needles / concrete
- no faces, no weapon, no readable packaging

2) Gear layout / inspection
- top-down layout on wool blanket / rough wood / concrete
- include product + props, no readable labels

3) Environment-only Potero
- taiga night / shelter corridor / OSB wall texture with flash hotspot and noise

Fallback still uses:
- ENV reference + texture ref + prop refs
- always includes shader/negative blocks

---

## 10) Unit tests you should add (fast, prevents regressions)

Prompt compiler tests
- shader and negative blocks always present
- role-based refs selected correctly for:
  - winter weapon slide (must include M05 snow + RK95 muzzle + ENV kaamos)
  - Savotta slide (must include PALS close + straps connect)
  - cap enforcement (<=14)

Critic grading tests
- OPSEC violations hard-fail regardless of potero score
- PoteroScore threshold routing
- Warn triggers style-tighten flag

Graph routing tests
- edit-mode route triggers on local failures
- fallback uses Potero-safe templates, not generic textures

---

## 11) Operational knobs (env vars worth adding)

- `POTERO_SHADER_VERSION`
- `POTERO_IMAGE_ASPECT=4:5`
- `POTERO_IMAGE_SIZE=2K|4K`
- `POTERO_ALLOW_WARN_PASS=true|false`
- `POTERO_POTERO_PASS_THRESHOLD=7.5`
- `POTERO_POTERO_WARN_THRESHOLD=6.0`
- `POTERO_ENABLE_EDIT_MODE=true|false`
- `POTERO_MAX_REFS_PER_CALL=10` (soft target)
- `POTERO_MAX_REFS_HARD=14`
- `POTERO_ANCHOR_CANDIDATES=3`

Persist these into state for deterministic resume.

---

## 12) Implementation checklist (sequence to production-ready)

1. Add Potero assets (shader/negative/ontology/intents) + versioning
2. Extend manifest with roles + tags
3. Implement role-based reference selector
4. Implement prompt compiler template (locked ordering)
5. Upgrade Critic JSON output + PoteroScore rubric
6. Add crop-critic stage (bbox -> crop eval)
7. Add ArtistEdit node and routing
8. Replace fallback with Potero-safe fallback templates
9. Add tests + smoke check scenario for each env preset
10. Ship User Guide (how to provide refs) so inputs are consistent

---

## Robustness extras (strongly recommended)

### 1) Add a Brand Drift Firewall layer before generation

Preflight (text-only)
- Input: theme + slide intent + planned prompt
- Output: ok | rewrite_required with reasons:
  - detects banned vibes: "cinematic", "golden hour", "operator", "hero shot", "tactical influencer"
  - detects US kit tokens: "AR-15", "M4", "Multicam", "SEAL", etc.
  - detects risky text props: "logo", "patch text", "brand name visible"
  - detects lighting mismatch: winter + "warm sunset"

This can be a cheap Gemini Flash call. It prevents wasting retries.

### 2) Add a Kit Consistency Compiler (constraint solver-lite)

Examples of hard compile rules
- If weapon_present=true -> require RK95 refs (silhouette + muzzle) OR downgrade scene to "weapon not visible" (hands on sling only).
- If Savotta backpack present -> require PALS close ref OR constrain shot to "partial pack edge" (no full grid).
- If winter_kaamos -> enforce "cool color temp" + ban "warm light" tokens.
- If face risk high (close portrait) -> auto change shot type to crop/head out.

### 3) Add Reference Quality Scoring and refuse/repair bad inputs

Auto-score per reference:
- resolution (min px)
- sharpness
- compression artifacts
- watermark/text presence
- background cleanliness (packshot vs in-use)
- role fit (e.g., PALS close-up actually shows webbing)

If a required role score < threshold:
- fall back to a safer composition, or
- request better refs (interactive mode), or
- switch to Potero Safe slide archetype for that slide

### 4) Create Golden Reference Packs per environment preset

Each preset ships with:
- 1-2 environment vibe refs
- 1 M05 texture ref (or snow variant)
- 1-2 lighting exemplars (lo-fi flash look)
- 1-2 Finnish identity cues (shelter wall, OSB, taiga texture)

### 5) Add candidate pool + best-of selection for Slide 1 only

Strategy
- generate 3-4 candidates
- run critic + crop critic
- pick highest opsec_pass and potero_score and use it as anchor

### 6) Add local repair playbooks (deterministic fixes per defect)

Defect -> action examples
- Warm winter -> edit: "shift white balance cooler, kaamos blue, reduce warm highlights"
- Pixel camo -> edit localized on fabric: "replace with organic blotches matching M05 swatch"
- RK95 becomes AK -> edit rifle region + attach muzzle ref + silhouette ref
- PALS wobbly -> edit backpack area: "straight evenly spaced webbing rows"
- Floating straps -> edit shoulder region: "strap connects into carrier/buckle"

Keep the playbook in code; critic outputs defect codes that map to these actions.

### 7) Introduce two-tier identity modes to avoid face failures

Identity modes
- Default (Anonymous): head cropped / balaclava / shadow / back view
- De-identified gaze (rare): subject can face camera but face is non-identifiable (motion blur, overexposed, censor bars). Never allow clear facial features.

Planner sets the mode based on slide intent. Critic hard-fails violations.

### 8) Add compliance-safe prop handling

Rules
- No readable packaging text (ever)
- No recognizable brand logos
- If "red-and-gold coffee pack" is used: force generic, no text, no logo
- Shelter shots: remove signage, numbers, instructions

Make this part of OPSEC gate and negative prompts.

### 9) Build a PoteroStyle regression test suite

Minimal regression set (per release)
- For each env preset:
  - 1 field_wait slide
  - 1 artifact_detail slide
  - 1 domestic_front slide

Store
- the prompt + ref pack IDs
- the critic JSON
- a hash of the output image (or manual golden check)

### 10) Observability: log why we fail in a way you can act on

Log per attempt
- selected reference roles + counts
- ref quality scores
- potero breakdown scores
- defect codes
- repair action taken (edit/regen)
- time + model used

This supports analysis such as:
- Which role is missing in most failures?
- Does PALS failure correlate with low-res refs?
- Which themes cause warm-winter drift?

### 11) Safe-but-Potero fallback needs its own scoring gate

Even fallback must pass:
- OPSEC gate
- PoteroScore >= 7.0 (slightly lower is OK because it is fallback)

If not, fallback retries with a different safe archetype.

### 12) Remove duplicate SDK surface area

Standardize on one Google SDK path (`google-genai`) and one image generation path (Nano Banana Pro via `generate_content`).

---

If you want, share your `assets/references/manifest.json` format and one `briefs.json` slide example to tailor this guide to your exact structure.
