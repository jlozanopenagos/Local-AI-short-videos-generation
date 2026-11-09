# Shorts Automation WebUI Backend & Server

High-performance FastAPI application serving the modern browser-based management studio and background task execution engine for the `shorts_automation` pipeline.

---

## Architecture Overview

The WebUI backend implements an asynchronous, thread-safe Model-View-Controller (MVC) architecture designed for long-running generative media tasks:

```text
main/webui/
├── server.py                       # FastAPI application factory, middleware, static mounting & exception handlers
├── settings.py                     # WebUI configuration, default ports, CORS policies
├── routers/                        # API route controllers
│   ├── health.py                   # Service connectivity checks (LLM, ComfyUI, GPU VRAM)
│   ├── jobs.py                     # Job queue submission, status, cancellation & SSE log streaming
│   ├── scripts.py                  # Script state querying, metadata inspection, and validate-ids endpoint
│   └── sheets.py                   # Google Sheets 4-step sync endpoints (fetch, check, apply, ready)
├── jobs/                           # Background job orchestration & stage adapters
│   ├── runner.py                   # Thread-safe in-memory task runner & event dispatcher
│   ├── adapters/                   # Stage-specific execution adapters
│   │   ├── voice.py                # Adapts Stage _B (TTS), manages Llama/VRAM lifecycle
│   │   ├── image.py                # Adapts Stage _C (Scene illustrations)
│   │   └── thumbnail.py            # Adapts Stage _F (Chalkboard thumbnails)
├── static/                         # Production pre-compiled React SPA assets (HTML, JS, CSS)
├── frontend/                       # React 19 + TypeScript + Vite source code
└── README.md                       # WebUI backend manual (this document)
```

---

## API Endpoints Reference

### 1. Health & System Metrics (`/api/health`)
- `GET /api/health`: Returns live infrastructure health:
  - LLM server connectivity and active model name.
  - ComfyUI server status, queue metrics, and device stats.
  - Available system RAM and NVIDIA GPU VRAM metrics.

### 2. Job Queue & SSE Streaming (`/api/jobs`)
- `POST /api/jobs`: Enqueues a new background pipeline task.
  - Request payload:
    ```json
    {
      "stage": "voice" | "image" | "thumbnail" | "assembly",
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
- `POST /api/jobs/{id}/cancel`: Aborts an active or queued job cleanly.

### 3. Script Inspection & Validation (`/api/scripts`)
- `GET /api/scripts/{id}`: Returns the full runtime JSON state machine for a specific script ID.
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

### 4. Google Sheets Sync (`/api/sheets`)
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
- **Diffusion Concurrency (`jobs/adapters/image.py` & `thumbnail.py`)**:
  - Leverages `core/comfy_pool.py` mutex guards to avoid simultaneous VRAM collisions.

---

## Launcher Tool (`main/tools/webui.py`)

Launch the unified server and frontend with a single command:

```powershell
# Default launch (runs on port 8000 and opens browser automatically)
py main/tools/webui.py

# Custom port or host
py main/tools/webui.py --port 8080 --host 0.0.0.0

# Headless / server mode without opening browser
py main/tools/webui.py --no-browser
```
