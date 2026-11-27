# Shorts Automation WebUI Frontend

Modern, high-performance Web Single Page Application (SPA) for managing, monitoring, and batch-producing generative vertical short-form videos across all pipeline stages.

---

## Tech Stack & Architecture

- **Core Framework**: React 19 + TypeScript (Strict Type Safety)
- **Build Tool**: Vite 8 (fast HMR and optimized asset bundling)
- **Styling**: Tailwind CSS + Lucide React icon set
- **Streaming & Real-Time Comms**: WebSockets (`/ws/jobs/{job_id}`, `/ws/system`) paired with adaptive REST status polling
- **Backend Delivery**: Pre-compiled production bundle output to `shorts_automation/main/webui/static/`, served as static files by FastAPI (`main/webui/server.py`, default port `8190`).

---

## Voice controls

Voice generation supports **Hybrid routing** (`Auto`: ElevenLabs `eleven_v3` for `ROLEPLAY`, `EXPRESSION`, and `FUN_FACTS`, Local Qwen3-TTS for `GAME`), **ElevenLabs only**, or **Local Qwen3-TTS only**. Configure `ELEVENLABS_API_KEY` directly in Mass Creation (persisted to gitignored `main/.env`), pick the ElevenLabs model (`eleven_v3`, `eleven_multilingual_v2`, `eleven_flash_v2_5`), preview estimated credits before launch, and enable **Force** / **Recast (`Choose new voices`)** when rerendering. The active local bank (`52` baseline voices) and ElevenLabs curated catalog (`227` voices) live on the backend.

## The 6 Primary Navigation Views

The WebUI is structured around 6 tabs in the top navigation bar (`Navbar.tsx`):

### 1. Home (`HomeView.tsx`)
- Pipeline overview, global asset completion metrics across all languages (**English**, **French**, **Spanish**, **Italian**) and video formats (`EXPRESSION`, `GAME`, `ROLEPLAY`, `FUN_FACTS`), and quick-navigation launch cards.

### 2. Script Catalog & Detail Inspection (`ScriptList.tsx` & `ScriptDetailModal.tsx`)
- **System Health Telemetry (`SystemCard.tsx`)**: Live connectivity status for the LLM Server, ComfyUI, and hardware/VRAM telemetry with start/stop controls.
- **Filterable Catalog**: Search and filter available scripts (`1,224` in `main/state/`) by language, video format, and stage status.
- **Script Detail Modal (`ScriptDetailModal.tsx`)**: Inspects script sections, audio waveform, scene storyboard illustrations, live-editable thumbnail title & preview (`POST /api/scripts/{script_id}/render-thumbnail`), and YouTube SEO metadata:
  - **Gemini Prompt Auditor**: Calls `POST /api/scripts/{script_id}/gemini-audit-prompt` to reroll Cultural Worlds and audit prompts.
  - **Single-Scene & Full-Set Image Redo**: Redo individual scene frames, or trigger **Queue Redo (All Images)** to preserve your saved/edited `general_prompt` (`preserve_general_prompt=True`) while running the two-phase Llama -> ComfyUI rebuild of all scene prompts and PNGs.
  - **Direct Google Drive Upload**: Scoped upload (`all`, `video`, or `thumbnail`) via `POST /api/drive/scripts/{script_id}/upload`, cleaning existing duplicates before uploading.

### 3. Queue (`JobQueueView.tsx`)
- **Active Task Monitoring**: Real-time visualization of queued, running, completed, and cancelled background worker jobs.
- **Live Terminal Log Streaming**: Streaming ANSI console output over WebSockets (`/ws/jobs/{job_id}`) with cancel controls and per-script progress telemetry.

### 4. Mass Assets Creation (`MassAssetsCreationView.tsx`)
High-throughput batch production interface for arbitrary script ID lists across any language or video format:
- **Flexible ID Collection**: Accepts pasted IDs (`POST /api/scripts/validate-ids`), CSV drag-and-drop (`ID` / `SCRIPT_ID` column), or one-click catalog presets (*pending scene images*, *pending voice tracks*, *pending thumbnails* filtering `stages.thumbnails !== 'done'`, *ready for video assembly*, *ready for drive upload*, *game chalkboards*).
- **7 Supported Target Stages**:
  - **Script Dialogues** (`scripts`, Stage A): Regenerates modular scripts via LLM.
  - **Scene Images** (`images`, Stage C): When forced (`force: true` default), rebuilds both `general_prompt` and storyboard `image_prompts` via Llama before rendering via ComfyUI.
  - **Voice Files** (`voice`, Stage B): Hybrid ElevenLabs (`eleven_v3`) + Local Qwen3-TTS (`ComfyUI`) synthesis with automatic Llama VRAM handoff, credit estimation, accent/model overrides, and recasting.
  - **Thumbnail Images** (`thumbnails`, Stage F): Vertical category thumbnails (`576x1024`, zero VRAM) across 20 templates including Spanish LatAm/Spain variants.
  - **Chalkboard Images** (`chalkboard`, Game only): Instant CPU FreeType chalk typography rendering (zero ComfyUI/LLM).
  - **Video Assembly** (`assembly`, Stage G): Always dispatches with `force: true`; validates Stage B + Stage C prerequisites, strictly respects the **"Reuse existing subtitles"** checkbox (`keep_subtitles`), and renders non-overlapping `.ass` captions and MP4s via staged replacement.
  - **Google Drive Upload** (`drive_upload`): Supports `drive_scope` selector (**Both: Final Video + Thumbnail(s)**, **Final Video Only**, **Thumbnail(s) Only**), validates scope readiness, removes existing duplicates on Drive, and uploads via `DriveAdapter`.

### 5. Google Sheets Sync (`GoogleSheetsSyncView.tsx`)
- **Script Revisions (Column D)**: Interactive 4-step sync powered by `/api/sheets/sync` across all 16 sheets (`SCRIPT_CHANGED`/`SCRIPT_CHANGE` + Column B `EXPRESSION`) with `Counter`-based diffing and `GAME` option merging.
- **Thumbnail Titles Sync (Column J)**: Syncs Column J (`THUMBNAIL_TITLE`) across all 16 sheets via `/api/sheets/sync-thumbnails`, updating `content_metadata.thumbnail_title` and resetting only `thumbnail_generation` to `pending`.

### 6. Bingo Matrix (`BingoMatrixView.tsx`)
- Visual asset readiness grid tracking completion across all 16 language/format matrices (`EE`, `EG`, `ER`, `EF`, etc.).

---

## Directory Layout

```text
main/webui/frontend/
├── src/
│   ├── assets/                         # Brand SVGs & hero assets
│   ├── components/                     # Views & reusable UI components
│   │   ├── BingoMatrixView.tsx         # 16-matrix asset readiness grid
│   │   ├── ErrorBoundary.tsx           # React render error boundary
│   │   ├── GoogleSheetsSyncView.tsx    # 4-step Google Sheets sync workflow
│   │   ├── HomeView.tsx                # Pipeline overview & quick launch view
│   │   ├── JobQueueView.tsx            # Active job monitor and WebSocket log viewer
│   │   ├── MassAssetsCreationView.tsx  # 7-stage mass batch creation & Drive upload studio
│   │   ├── Navbar.tsx                  # Top navigation bar, theme toggle & system card
│   │   ├── ScriptDetailModal.tsx       # Script inspector, Gemini auditor, redo & Drive upload
│   │   ├── ScriptList.tsx              # Searchable, filterable script catalog
│   │   └── SystemCard.tsx              # Live telemetry & start/stop controls for ComfyUI / LLM
│   ├── api.ts                          # Typed fetch client & WebSocket helpers for FastAPI backend
│   ├── types.ts                        # Shared TypeScript interfaces & job/script types
│   ├── App.tsx                         # Root component, adaptive polling & tab router
│   ├── App.css                         # Component layout stylesheets
│   ├── main.tsx                        # React application bootstrap
│   └── index.css                       # Global design tokens & Tailwind CSS styling
├── public/                             # Static public assets
├── package.json                        # Frontend dependencies and npm scripts
├── tsconfig.json                       # TypeScript compiler configuration
├── vite.config.ts                      # Vite build & development proxy configuration
└── README.md                           # Frontend architecture and developer guide (this file)
```

---

## Developer Workflow

### Prerequisites
- Node.js 18+ and `npm`

### Local Development (with Hot Reloading)
```bash
# 1. Start the FastAPI backend (default port 8190)
py main/tools/webui.py

# 2. In another terminal, start the Vite development server
cd main/webui/frontend
npm install
npm run dev
```
Vite launches on `http://127.0.0.1:5173` and proxies API/WebSocket calls (`/api/*`, `/ws/*`) to the FastAPI backend (`8190`).

### Production Build
Whenever frontend source files in `src/` are modified, rebuild the production bundle:
```bash
cd main/webui/frontend
npm run build
```
Vite outputs the compiled HTML, JavaScript, and CSS bundles into `main/webui/static/`. Once built, the application is served directly by running:
```bash
py main/tools/webui.py
```
Zero Node.js runtime is required in production!
