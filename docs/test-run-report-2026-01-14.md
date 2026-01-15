# Test Run Report 2026-01-14

## Executive Summary
A test run was initiated on 2026-01-14 to generate a carousel with the theme `ENV_TAIGA_SUMMER_NIGHT` and design `rk_hoodie`. The run successfully initialized and uploaded reference assets but encountered a fatal orchestrator crash during the first slide's validation phase.

---

## 1. Run Metadata
- **Run ID:** `36263ce6438043cabca269e4660e6eb8`
- **Output Directory:** `output/36263ce6438043cabca269e4660e6eb8`
- **Theme:** `ENV_TAIGA_SUMMER_NIGHT`
- **Design:** `rk_hoodie`
- **Timestamp:** 2026-01-14 09:52 UTC+2

---

## 2. Incident Description
The system successfully performed the following steps:
1.  **Asset Loading:** Validated 38 assets from `manifest.json`.
2.  **Asset Registry Upload:** Reference images for the first slide were successfully uploaded to the Gemini API.
3.  **Prompt Compilation:** Briefs were generated (stored in `briefs.json`).

The failure occurred immediately after the **Artist** step, when the **Critic Agent** was invoked.

### 2.1 Error Details
- **Error Type:** `NOT_FOUND (404)`
- **Agent:** `src.agents.critic`
- **Raw Log:**
  ```json
  {"ts": "2026-01-14T07:52:48.427632+00:00", "level": "ERROR", "logger": "src.agents.critic", "message": "critic_validation_failed", "error": "404 NOT_FOUND. {'error': {'code': 404, 'message': 'models/gemini-1.5-flash is not found for API version v1beta...'}}"}
  ```

### 2.2 Root Cause Analysis
The configuration in `src/config.py` uses default model IDs that are either deprecated, incorrectly formatted for the `v1beta` endpoint, or refer to internal/non-public preview names (e.g., `gemini-3-pro-preview`). Specifically, `models/gemini-1.5-flash` failed to resolve.

---

## 3. Design & Prompting Observations (User Notice)

> [!WARNING]
> **Potero Standard Hallucination Detected**
>
> With current configuration and prompt guidelines, the AI is consistently getting confused about the **"POTERO STANDARD"** embroidery text.
> 1.  **Incorrect Placement:** It is frequently generating the "POTERO STANDARD" text on the **back side** of the hoodie.
> 2.  **Incorrect Scale/Frequency:** It is creating it as a primary design element rather than a detail.
>
> **Correct Specification:**
> - The "POTERO STANDARD" embroidery is a **small detail** only.
> - Location: **Front of the hoodie, specifically over the left chest**.
> - It should **not** appear on the back or anywhere else.

Proposed solution: Only use reference images with naming "back" to backshots and "front" to frontshots and only mention POTERO STANDARD embroidery when handling frontshots of hoodies. Yes this is the way to get consistent results: Edit flow that its in the hierarchy and to ensure that front and back details are not mixed up. Also make sure system promts are not allowing to mix up front and back details. 

---

## 4. Required Actions
1.  **Resolve Model Naming:** Update our logic to use latest google models.
2.  **Hard-code Design Rules:** Update `src/agents/planner.py` to explicitly forbid the "POTERO STANDARD" text on the back of hoodies and pin it to the left chest area.
3.  **Negative Prompting:** Add "no text on back", "no large logos" to the global artist constraints.


Other notes:
For safety lets leace all composition_guidance promts out of mentios of "text" or "logo" and only mention empty space or other visual composition.
"composition_guidance": "Leave top-left empty for typography.",
