# Shorts Automation WebUI Backend & Server

High-performance FastAPI application serving the modern browser-based management studio and background task execution engine for the `shorts_automation` pipeline.

---

## Architecture Overview

The WebUI backend implements an asynchronous, thread-safe Model-View-Controller (MVC) architecture designed for long-running generative media tasks:

```text
main/webui/
├── server.py                       # FastAPI application factory, middleware, static mounting & exception handlers
├── settings.py                     # WebUI configuration, default ports (8190), CORS policies
├── routers/                        # API route controllers
│   ├── system.py                   # Service connectivity checks (LLM, ComfyUI, GPU VRAM) & process controls
│   ├── jobs.py                     # Job queue submission, status, cancellation, SSE & WebSocket log streaming
│   ├── scripts.py                  # Script state querying, metadata inspection, and validate-ids endpoint
│   ├── media.py                    # Static media asset streaming (audio, images, video)
│   └── sheets.py                   # Google Sheets 4-step sync endpoints (fetch, check, apply, ready)
├── jobs/                           # Background job orchestration & stage adapters
│   ├── manager.py                  # Thread-safe in-memory task runner & event dispatcher
│   ├── models.py                   # Job schemas, statuses, and execution requests
│   └── adapters/                   # Stage-specific execution adapters
│       ├── scripts.py              # Adapts Stage _A (Modular Script Generation: Game, Roleplay, Expression, Fun Facts)
│       ├── voice.py                # Adapts Stage _B (TTS), manages Llama/VRAM lifecycle
│       ├── images.py               # Adapts Stage _C (Scene illustrations)
│       ├── thumbnails.py           # Adapts Stage _F (Chalkboard thumbnails)
│       └── assembly.py             # Adapts Stage _G (Final video assembly & subtitles)
├── static/                         # Production pre-compiled React SPA assets (HTML, JS, CSS)
├── frontend/                       # React 19 + TypeScript + Vite source code
└── README.md                       # WebUI backend manual (this document)
```

---

## API Endpoints Reference

### 1. System Health & Process Metrics (`/api/system`)
- `GET /api/system/status`: Returns live infrastructure health:
  - LLM server connectivity and active model name.
  - ComfyUI server status, queue metrics, and device stats.
  - Available system RAM and NVIDIA GPU VRAM metrics.
- `POST /api/system/service`: Controls headless services (`comfyui`, `llama`) with actions (`start`, `stop`, `restart`).

### 2. Job Queue, SSE & WebSocket Streaming (`/api/jobs`)
- `POST /api/jobs`: Enqueues a new background pipeline task.
  - Request payload:
    ```json
    {
      "stage": "scripts" | "voice" | "images" | "thumbnails" | "assembly",
      "script_ids": ["EE01", "EE02"],
      "force": true,
      "options": {
        "candidates": 3,
        "genders": "male, female",
        "seed": 42
      }
    }
    ```
- `GET /api/jobs`: Lists all active, pending, and completed jobs.
- `GET /api/jobs/{id}`: Returns status, progress percentage, and stage for a specific job.
- `GET /api/jobs/{id}/events`: **Server-Sent Events (SSE)** endpoint. Streams live stdout/stderr log lines in real time to the browser terminal emulator.
- `GET /api/jobs/ws`: **WebSocket** endpoint for bidirectional real-time job updates and logs.
- `POST /api/jobs/{id}/cancel`: Aborts an active or queued job cleanly.

### 3. Script Inspection & Validation (`/api/scripts`)
- `GET /api/scripts`: Lists all indexed scripts with pagination, facet filtering, and search.
- `GET /api/scripts/{id}`: Returns the full runtime JSON state machine for a specific script ID.
- `PUT /api/scripts/{id}`: Updates script state or resets downstream stages.
- `POST /api/scripts/validate-ids`: Batch validates an arbitrary list of script IDs against local state JSON files (`main/state/`).
  - Returns:
    ```json
    {
      "valid_ids": ["EE01", "FG03"],
      "invalid_ids": ["ZZ99"],
      "details": [
        {"id": "EE01", "language": "english", "type": "expression", "status": {"voice": "done", "image": "pending"}}
      ]
    }
    ```

### 4. Media Asset Streaming (`/api/media`)
- `GET /api/media/{filename}`: Securely streams audio, image, and video files from `OUTPUT_DIR` with strict protection against directory traversal attacks.

### 5. Google Sheets Sync (`/api/sheets`)
- `POST /api/sheets/fetch-corrections`: Executes `fetch_corrected_scripts.py` to pull Column D (`SCRIPT_CHANGED`) into `input/csv/script_to_change/`.
- `POST /api/sheets/check-changes`: Executes `check_script_changes.py --check-only` dry run, returning structured diffs, word count comparisons, and pending modifications.
- `POST /api/sheets/apply-changes`: Executes `check_script_changes.py --apply`, cleanly synchronizing state JSONs and resetting downstream stages to `'pending'`.
- `POST /api/sheets/scan-ready`: Executes `scan_ready_scripts.py`, filtering Columns E-H and exporting daily `<date>_ready_scripts.csv` files.

---

## VRAM & Hardware Coordination

When executing heavy generative tasks via WebUI job adapters:
- **TTS Synthesis (`jobs/adapters/voice.py`)**:
  - Automatically queries `LlamaManager` to release LLM VRAM allocations before synthesis begins (`llama_manager.ensure_llama_stopped()`).
  - Ensures Qwen3-TTS and Kokoro-82M have full access to GPU memory.
  - Automatically restarts the LLM background server once audio processing completes (`llama_manager.ensure_llama_running()`).
- **Diffusion Concurrency (`jobs/adapters/images.py` & `thumbnails.py`)**:
  - Leverages `core/comfy_pool.py` mutex guards to avoid simultaneous VRAM collisions.
- **Assembly Processing (`jobs/adapters/assembly.py`)**:
  - Offloads subtitle transcription to CPU Whisper and runs localized FFmpeg assembly.

---

## Launcher Tool (`main/tools/webui.py`)

Launch the unified server and frontend with a single command:

```powershell
# Default launch (runs on port 8190 and opens browser automatically)
py main/tools/webui.py

# Custom port or host
py main/tools/webui.py --port 8195 --host 0.0.0.0
```
```
