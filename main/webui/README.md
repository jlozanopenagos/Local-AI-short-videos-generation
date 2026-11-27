# Shorts Automation WebUI Backend & Server

High-performance FastAPI application serving the modern browser-based management studio and background task execution engine for the `shorts_automation` pipeline.

## Start and stop

Launch with `py main/tools/webui.py` from the repository root. Studio listens on port 8190 by default. Use `--dev --reload` for development. On Ctrl+C, Uvicorn gives in-flight connections up to five seconds to drain before application cleanup. The job manager then gives its worker up to 30 seconds to unwind. ComfyUI and llama.cpp have separate service controls.

The worker serializes production jobs. The voice adapter can queue a required next take ahead within a single job, and cancellation targets the prompts that job submitted. The image batch queue is separate.

## Architecture Overview

The WebUI backend implements an asynchronous, thread-safe Model-View-Controller (MVC) architecture designed for long-running generative media tasks:

```text
main/webui/
├── server.py                       # FastAPI application factory, middleware, static mounting & exception handlers
├── settings.py                     # WebUI configuration, default ports (8190), CORS policies
├── routers/                        # API route controllers
│   ├── system.py                   # Service connectivity checks (LLM, ComfyUI, GPU VRAM, Gemini status) & controls
│   ├── jobs.py                     # Job queue submission, status, cancellation, WebSocket streaming (/ws/jobs, /ws/system)
│   ├── scripts.py                  # Script state querying, Gemini prompt audit, chalkboard/redo & validate-ids
│   ├── media.py                    # Static media asset streaming (audio, images, video) with HTTP Range support
│   ├── sheets.py                   # Google Sheets script (Col D) & thumbnail title (Col J) sync endpoints
│   └── drive.py                    # Google Drive status check & scoped single-script upload endpoints
├── jobs/                           # Background job orchestration & stage adapters
│   ├── manager.py                  # Thread-safe in-memory task runner & WebSocket event dispatcher
│   ├── models.py                   # Job schemas, statuses, and execution requests
│   └── adapters/                   # Stage-specific execution adapters
│       ├── base.py                 # Abstract BaseStageAdapter interface
│       ├── scripts.py              # Adapts Stage _A (Modular Script Generation: Game, Roleplay, Expression, Fun Facts)
│       ├── voice.py                # Adapts Stage _B via hybrid ElevenLabs (`eleven_v3`) + local Qwen3-TTS (`orchestrator.py`) + VRAM handoff
│       ├── images.py               # Adapts Stage _C (Scene illustrations + forced general/scene prompt rebuild)
│       ├── chalkboard.py           # Adapts CPU FreeType chalkboard rendering for Game quiz scenes
│       ├── thumbnails.py           # Adapts Stage _F (CPU category thumbnails + Spanish LatAm/Spain variants)
│       ├── assembly.py             # Adapts Stage _G (Typed video assembly, non-overlapping subtitles, strict subtitle reuse, staged replacement)
│       └── drive.py                # Adapts batch Google Drive scoped (`all` | `video` | `thumbnail`) replacement uploads
├── static/                         # Production pre-compiled React SPA assets (HTML, JS, CSS)
├── frontend/                       # React 19 + TypeScript + Vite source code
└── README.md                       # WebUI backend manual (this document)
```

---

## API Endpoints Reference

### 1. System Health & Process Metrics (`/api/system`)
- `GET /api/system/status`: Returns live infrastructure health (LLM server connectivity/model, ComfyUI `/system_stats`, RAM/GPU VRAM metrics).
- `POST /api/system/service/{service}/{action}`: Controls headless services (`comfyui`/`comfy`, `llama`/`llm`) with actions (`start`, `stop`, `restart`).
- `POST /api/system/comfy/{start|stop|restart}` & `POST /api/system/llm/{start|stop|restart}`: Direct service control aliases.
- `GET /api/system/logs/{service}`: Streams recent service log lines.
- `GET /api/system/gemini-status` & `POST /api/system/gemini-key`: Reports and configures the Gemini Prompt Auditor API key.
- `GET /api/system/elevenlabs-status` & `POST /api/system/elevenlabs-key`: Reports ElevenLabs key configuration, subscription tier/remaining credits, and saves `ELEVENLABS_API_KEY` to `main/.env`.

### 2. Job Queue & WebSocket Streaming (`/api/jobs`, `/ws`)
- `POST /api/jobs`: Enqueues a new background pipeline task.
  - Request payload:
    ```json
    {
      "stage": "scripts" | "voice" | "images" | "assembly" | "thumbnails" | "chalkboard" | "drive_upload",
      "script_ids": ["EE01", "EE02"],
      "options": {
        "force": true,
        "regenerate_prompts": true,
        "candidates": 3,
        "voice_provider": "auto",
        "elevenlabs_model": "eleven_v3",
        "accent": "es_latam_neutral",
        "voice_engine": "typed",
        "recast": false,
        "keep_subtitles": false,
        "drive_scope": "all",
        "seed": 42
      }
    }
    ```
- `GET /api/jobs`: Lists all active, pending, and completed jobs.
- `GET /api/jobs/{job_id}`: Returns status, progress percentage, logs, and stage for a specific job.
- `POST /api/jobs/{job_id}/cancel`: Aborts an active or queued job cleanly.
- `WS /ws/jobs/{job_id}`: Streams live logs and progress snapshots for a specific job in real time.
- `WS /ws/system`: Streams global queue and system health events.

### 3. Script Inspection, Prompt Auditing & Validation (`/api/scripts`)
- `GET /api/scripts`: Lists indexed scripts with pagination, facet filtering, and search.
- `GET /api/scripts/facets` & `POST /api/scripts/refresh`: Returns filter facets and refreshes script index cache.
- `GET /api/scripts/{script_id}` & `PUT /api/scripts/{script_id}`: Fetches or updates the full runtime JSON state for a script ID.
- `POST /api/scripts/{script_id}/toggle-stage`: Toggles a stage status (`pending` / `done`) for manual re-queuing.
- `POST /api/scripts/{script_id}/generate`: Enqueues single-script generation.
- `POST /api/scripts/{script_id}/gemini-audit-prompt`: Audits general & scene prompts via Gemini using purely-positive Z-Image-Turbo rules (`19-year-old`, `1:7.5`, expressive sclera eyes) and automatically rerolls a fresh Cultural World excluding the previous draft's setting (unless fixed by the script).
- `POST /api/scripts/{script_id}/render-chalkboard`: Synchronously renders CPU FreeType chalkboard artwork for Game scripts.
- `POST /api/scripts/{script_id}/render-thumbnail`: Updates `content_metadata.thumbnail_title` (if provided) and synchronously renders category thumbnail(s) (`thumbnail.png` or Spanish `latam`/`spain` variants).
- `POST /api/scripts/validate-ids`: Batch validates arbitrary script IDs against `main/state/`, returning existence, metadata, language/type, and asset status (`has_video`, `has_thumbnail`, `can_upload_drive`).
- `POST /api/scripts/estimate-voice-credits`: Estimates ElevenLabs character credits vs 0-credit Local Qwen3-TTS routing for a batch of IDs and provider/model selection.
- `POST /api/scripts/{script_id}/scenes/{scene_type}/redo-image`: Enqueues an isolated single-scene ComfyUI regeneration job.
- `POST /api/scripts/{script_id}/redo-all-images`: Saves optional edited general prompt, clears stale scene prompts/PNGs, and queues a full two-phase Llama -> ComfyUI rebuild with `preserve_general_prompt=True` so the saved `general_prompt` is preserved while scene prompts and images regenerate.

### 4. Media Asset Streaming (`/api/media`)
- `GET /api/media` & `GET /api/media/{path:path}`: Securely streams audio, image, and video assets from `OUTPUT_DIR` with HTTP Range seeking and strict directory traversal protection.

### 5. Google Sheets Sync (`/api/sheets`)
- `GET /api/sheets/status`: Returns current status, progress, step number, and logs for the background sync worker.
- `POST /api/sheets/sync`: Launches the 4-step workflow across all 16 sheets including `FUN_FACTS` (`clean_cache`, Column D `SCRIPT_CHANGED`/`SCRIPT_CHANGE` + Column B `EXPRESSION` fetch, `Counter`-based format-aware diff audit, apply to state JSONs with `GAME` blank-line option merging, topic-change invalidation, and downstream resets).
- `POST /api/sheets/sync-thumbnails`: Fetches Column J (`THUMBNAIL_TITLE`) across all 16 sheets and updates `content_metadata.thumbnail_title` in local state JSONs (resetting only `thumbnail_generation` to `pending`).
- `POST /api/sheets/reset`: Resets the sync state back to `idle`.

### 6. Google Drive Export (`/api/drive`)
- `GET /api/drive/status`: Reports credentials detection (`token.json`, `service_account.json`, or `client_secret.json`) and target `DEFAULT_ROOT_FOLDER_ID`.
- `POST /api/drive/scripts/{script_id}/upload`: Accepts optional `drive_scope` (`all` | `video` | `thumbnail`), validates the required local assets, cleans duplicate `<script_id>` folders and old canonical files, and uploads replacements (including both Spanish regional thumbnails). Batch Drive uploads run asynchronously via `POST /api/jobs` with `stage="drive_upload"` (`DriveAdapter`).

---

## VRAM & Hardware Coordination

When executing heavy generative tasks via WebUI job adapters:
- **TTS Synthesis (`jobs/adapters/voice.py`)**:
  - Supports **hybrid ElevenLabs (`eleven_v3`) + local Qwen3-TTS (`ComfyUI`)** routing: skips local `LlamaManager` / `ComfyUI` VRAM cycles cleanly when rendering pure ElevenLabs batches, and queries `LlamaManager` (`ensure_llama_stopped()` / `ensure_llama_running()`) whenever local ComfyUI Qwen3-TTS runs.
  - Forwards `candidates`, `voice_provider`, `elevenlabs_model`, `accent`, `voice_engine` (`typed` / `legacy`), and `recast` options.
- **Diffusion Concurrency (`jobs/adapters/images.py` & `thumbnails.py`)**:
  - `ImagesAdapter` executes a two-phase VRAM handoff: boots Llama once in Phase 1 to batch-generate prompts (rebuilding both `general_prompt` and storyboard `image_prompts` from scratch when `force=True` or `regenerate_prompts=True` unless `preserve_general_prompt=True` is set by `redo-all-images`), stops Llama to free VRAM, then uses `core/comfy_pool.py` mutex guards during ComfyUI rendering.
- **Assembly Processing (`jobs/adapters/assembly.py`)**:
  - Targeted IDs are always forced: verifies Stage B voice and Stage C image prerequisites first, deletes any pre-existing final `.mp4` and resets `video_assembly` to `pending`, strictly respects `keep_subtitles` / `force_subtitles` (only reusing existing `.ass` captions when **"Reuse existing subtitles"** is checked), and runs CPU faster-whisper + modular Stage G typed FFmpeg assembly into a staging path before publishing.
- **Google Drive Sync (`jobs/adapters/drive.py`)**:
  - Authenticates once per batch via `GoogleDriveClient` (with automatic OAuth browser re-auth if `token.json` is expired/revoked and `client_secret.json` exists), forwards `drive_scope` (`all` | `video` | `thumbnail`) to `upload_script_to_drive()`, and logs `deleted_existing_count` for replaced items.

---

## Launcher Tool (`main/tools/webui.py`)

Launch the unified server and frontend with a single command:

```powershell
# Default launch (runs on port 8190 and opens browser automatically)
py main/tools/webui.py

# Custom port or host
py main/tools/webui.py --port 8195 --host 0.0.0.0
```


The studio owns its job worker, script catalog cache, and Sheets sync state per application instance. Production stages are queued from Script Catalog or Mass Creation. Mass Creation accepts pasted IDs, ID CSVs, and catalog selections. Seed, voice, and subtitle options are available with the applicable stages. See the [studio test guide](../../test/README.md) for isolated API and browser checks.
