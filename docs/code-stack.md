# Potero Autocontent Code Stack

This document describes the full code stack in this repository: runtime, dependencies, tooling, and operational entrypoints. It is derived from the actual code and configuration in `src/`, `scripts/`, and `requirements.txt`.

## Runtime and language
- **Language**: Python
- **Execution model**: CLI entrypoint (`python -m src.main`) with environment configuration
- **Runtime environment**: virtualenv-friendly (no `pyproject.toml`; dependencies pinned in `requirements.txt`)

## Core architecture layers
- **Orchestration**: LangGraph state machine (`src/graph.py`)
- **Agents**: Planner, Artist, Critic, Editor (`src/agents/*.py`)
- **Prompt invariants**: Locked shader/negative injection is handled in the planner (`src/agents/planner.py`)
- **Preflight + kit consistency**: Drift checks and role enforcement (`src/preflight.py`, `src/kit_compiler.py`)
- **Reference selection**: Role-based selection + golden packs (`src/reference_selector.py`, `src/golden_packs.py`)
- **Local edit path**: Local defect targeting (`src/agents/artist_edit.py`)
- **State and budget**: Pydantic models and budget accounting (`src/state.py`, `src/budget.py`)
- **Assets**: Manifest-based registry (`src/asset_registry.py`) with reference files in `assets/references/`
- **Persistence**: JSON run state and briefs stored in `output/<run_id>/` (`src/run_storage.py`)
- **Logging**: JSON logs with structured fields (`src/logging_utils.py`)

## AI/LLM stack
- **Provider SDK**: Google GenAI (`google-genai`, `google-generativeai`)
- **API usage**:
  - `client.models.generate_content` for text and multimodal prompts
  - `client.models.generate_images` for Imagen image generation
  - `client.files.upload` for reference/anchor uploads with caching
- **Orchestration library**: `langgraph` (with `langgraph-prebuilt`, `langgraph-sdk`, `langgraph-checkpoint` installed)

## Optional dependencies
- **Pillow** (PIL): improves reference quality scoring when installed.

## Entrypoints and scripts
- **Main runner**: `src/main.py`
- **Smoke check**: `scripts/smoke_check.py`
- **Model listing**: `scripts/list_models.py`
- **CI hook**: `scripts/ci.sh`

## Tests
- **Test framework**: `unittest`
- **Discovery command**: `python -m unittest discover -s tests`
- **Coverage**: budget logic, config loading, critic grading, planner templates, resume logic, and asset registry validation

## Configuration and environment variables
Configuration is loaded in `src/config.py`. Names only (no values are printed here):

- `GOOGLE_API_KEY`
- `POTERO_OUTPUT_DIR`
- `POTERO_ASSETS_DIR`
- `POTERO_REFERENCES_DIR`
- `POTERO_ASSET_MANIFEST`
- `POTERO_RUN_ID`
- `POTERO_THEME_ID`
- `POTERO_DESIGN_ID`
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
- `POTERO_PLANNER_MODE`
- `POTERO_PLANNER_MODEL`
- `POTERO_ARTIST_MODEL`
- `POTERO_ARTIST_FALLBACKS`
- `POTERO_CRITIC_MODEL`
- `POTERO_CRITIC_WARN_THRESHOLD`
- `POTERO_CRITIC_FAIL_THRESHOLD`
- `POTERO_EDITOR_MODEL`
- `POTERO_EDITOR_MODE`
- `POTERO_MAX_TOTAL_CALLS`
- `POTERO_MAX_PLANNER_CALLS`
- `POTERO_MAX_ARTIST_CALLS`
- `POTERO_MAX_CRITIC_CALLS`
- `POTERO_MAX_EDITOR_CALLS`
- `POTERO_MAX_RETRIES_PER_SLIDE`
- `POTERO_LOG_LEVEL`
- `POTERO_REQUIRE_API_KEY`
- `POTERO_REQUIRE_ASSETS`

## Asset stack
- **Reference store**: `assets/references/`
- **Manifest**: `assets/references/manifest.json`
- **Validation**: `AssetRegistry` validates existence and expected entries for design assets.

## Output artifacts
- `output/<run_id>/state.json`
- `output/<run_id>/briefs.json`
- `output/<run_id>/slide_<index>.png`

## Pinned dependencies
Declared in `requirements.txt`:

- `annotated-types==0.7.0`
- `anyio==4.12.1`
- `certifi==2026.1.4`
- `charset-normalizer==3.4.4`
- `google-ai-generativelanguage==0.6.15`
- `google-api-core==2.29.0`
- `google-api-python-client==2.187.0`
- `google-auth==2.47.0`
- `google-auth-httplib2==0.3.0`
- `google-genai==1.33.0`
- `google-generativeai==0.8.6`
- `googleapis-common-protos==1.72.0`
- `grpcio==1.76.0`
- `grpcio-status==1.71.2`
- `h11==0.16.0`
- `httpcore==1.0.9`
- `httplib2==0.31.0`
- `httpx==0.28.1`
- `idna==3.11`
- `jsonpatch==1.33`
- `jsonpointer==3.0.0`
- `langchain-core==1.2.7`
- `langgraph==1.0.5`
- `langgraph-checkpoint==3.0.1`
- `langgraph-prebuilt==1.0.5`
- `langgraph-sdk==0.3.2`
- `langsmith==0.6.2`
- `orjson==3.11.5`
- `ormsgpack==1.12.1`
- `packaging==25.0`
- `proto-plus==1.27.0`
- `protobuf==5.29.5`
- `pyasn1==0.6.1`
- `pyasn1_modules==0.4.2`
- `pydantic==2.12.5`
- `pydantic_core==2.41.5`
- `pyparsing==3.3.1`
- `python-dotenv==1.2.1`
- `PyYAML==6.0.3`
- `requests==2.32.5`
- `requests-toolbelt==1.0.0`
- `rsa==4.9.1`
- `tenacity==9.1.2`
- `tqdm==4.67.1`
- `typing-inspection==0.4.2`
- `typing_extensions==4.15.0`
- `uritemplate==4.2.0`
- `urllib3==2.6.3`
- `uuid_utils==0.13.0`
- `xxhash==3.6.0`
- `zstandard==0.25.0`
