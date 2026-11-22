# Shorts Automation WebUI Frontend

Modern, high-performance Web Single Page Application (SPA) for managing, monitoring, and batch-producing generative vertical short-form videos across all pipeline stages.

---

## Tech Stack & Architecture

- **Core Framework**: React 19 + TypeScript (Strict Type Safety)
- **Build Tool**: Vite 7 (Lightning-fast HMR and optimized asset bundling)
- **Styling**: Tailwind CSS + Lucide React icon set
- **Streaming & Real-Time Comms**: WebSockets (`/ws/jobs/{job_id}`, `/ws/system`) paired with adaptive REST status polling
- **Backend Delivery**: Pre-compiled production bundle output to `shorts_automation/main/webui/static/`, served as static files by FastAPI (`main/webui/server.py`).

---

## Voice controls

Use Voice with Force to regenerate audio and enable Recast if you want Studio to pick different references. Review the resulting audio in the Script Detail modal. The active voice bank is configured on the backend.

## The 6 Primary Navigation Views

The WebUI is structured around 6 tabs in the top navigation bar (`Navbar.tsx`):

### 1. Home (`HomeView.tsx`)
- Pipeline overview, global asset completion metrics across all languages (**English**, **French**, **Spanish**, **Italian**) and video formats (`EXPRESSION`, `GAME`, `ROLEPLAY`, `FUN_FACTS`), and quick-navigation launch cards.

### 2. Script Catalog & Detail Inspection (`ScriptList.tsx` & `ScriptDetailModal.tsx`)
- **System Health Telemetry (`SystemCard.tsx`)**: Live connectivity status for the LLM Server, ComfyUI, and hardware/VRAM telemetry with start/stop controls.
- **Filterable Catalog**: Search and filter available scripts by language, video format, and stage status.
- **Script Detail Modal (`ScriptDetailModal.tsx`)**: Inspects script sections, audio waveform, scene storyboard illustrations, thumbnail preview, and YouTube SEO metadata:
  - **Gemini Prompt Auditor**: Calls `POST /api/scripts/{script_id}/gemini-audit-prompt` to enforce purely-positive Z-Image-Turbo rules and automatically reroll a fresh Cultural World excluding the previous draft's setting.
  - **Single-Scene & Full-Set Image Redo**: Redo individual scene frames, or trigger **Queue Redo (All Images)** to preserve your saved/edited `general_prompt` (`preserve_general_prompt=True`) while running the two-phase Llama -> ComfyUI rebuild of all scene prompts and PNGs.
  - **Direct Google Drive Upload**: Verifies video + thumbnail presence and uploads cleanly (`POST /api/drive/scripts/{script_id}/upload`), deleting existing duplicates before uploading.

### 3. Queue (`JobQueueView.tsx`)
- **Active Task Monitoring**: Real-time visualization of queued, running, completed, and cancelled background worker jobs.
- **Live Terminal Log Streaming**: Streaming ANSI console output over WebSockets (`/ws/jobs/{job_id}`) with cancel controls and per-script progress telemetry.

### 4. Mass Assets Creation (`MassAssetsCreationView.tsx`)
High-throughput batch production interface for arbitrary script ID lists across any language or video format:
- **Flexible ID Collection**: Accepts pasted IDs (`POST /api/scripts/validate-ids`), CSV drag-and-drop (`ID` / `SCRIPT_ID` column), or one-click catalog presets (*pending scene images*, *pending voice tracks*, *pending thumbnails*, *ready for video assembly*, *ready for drive upload (video + thumb)*, *game chalkboards*).
- **7 Supported Target Stages**:
  - **Script Dialogues** (`scripts`, Stage A): Regenerates modular scripts via LLM.
  - **Scene Images** (`images`, Stage C): When forced (`force: true` default), rebuilds both `general_prompt` and storyboard `image_prompts` via Llama before rendering via ComfyUI.
  - **Voice Files** (`voice`, Stage B): Multi-speaker Qwen3-TTS + Kokoro synthesis with automatic Llama VRAM handoff.
  - **Thumbnail Images** (`thumbnails`, Stage F): Vertical chalkboard thumbnails (`1080x1920`).
  - **Chalkboard Images** (`chalkboard`, Game only): Instant CPU FreeType chalk typography rendering (zero ComfyUI/LLM).
  - **Video Assembly** (`assembly`, Stage G): Always dispatches with `force: true`; validates Stage B + Stage C prerequisites, unlinks any existing final `.mp4` on disk, and re-renders modular typed video & ASS subtitles from scratch.
  - **Google Drive Upload** (`drive_upload`): Filters to scripts that have both final video and thumbnail, removes existing duplicates on Drive, and uploads fresh `<script_id>.mp4` & `<script_id>_thumbnail.png` bundles via `DriveAdapter`.

### 5. Google Sheets Sync (`GoogleSheetsSyncView.tsx`)
- Interactive 4-step browser sync powered by `/api/sheets/sync` & `/api/sheets/status` across all 16 sheets (including `FUN_FACTS`): cache purge, Column D (`SCRIPT_CHANGED` / `SCRIPT_CHANGE`) + Column B (`EXPRESSION`) fetch, format-aware diff audit, and state JSON synchronization with automatic topic-change and downstream invalidation.

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
# 1. Start the FastAPI backend
py main/tools/webui.py --port 8000

# 2. In another terminal, start the Vite development server
cd main/webui/frontend
npm install
npm run dev
```
Vite will launch on `http://localhost:5173` and automatically proxy API calls (`/api/*`) to `http://127.0.0.1:8000`.

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
