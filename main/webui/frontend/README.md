# Shorts Automation WebUI Frontend

Modern, high-performance Web Single Page Application (SPA) for managing, monitoring, and batch-producing generative vertical short-form videos across all pipeline stages.

---

## Tech Stack & Architecture

- **Core Framework**: React 19 + TypeScript (Strict Type Safety)
- **Build Tool**: Vite 7 (Lightning-fast HMR and optimized asset bundling)
- **Styling**: Tailwind CSS + Lucide React icon set
- **Streaming & Real-Time Comms**: Server-Sent Events (SSE) via `EventSource` for real-time job execution logging
- **Backend Delivery**: Pre-compiled production bundle output to `shorts_automation/main/webui/static/`, served as static files by FastAPI (`main/webui/server.py`).

---

## The 4 Primary Production Views

The WebUI is structured around 4 purpose-built views accessible from the top navigation bar:

### 1. Dashboard View (`DashboardView.tsx`)
- **System Service Health**: Real-time status cards checking connectivity to:
  - **OpenAI-Compatible LLM Server** (e.g. Ollama, llama.cpp, vLLM, LM Studio)
  - **ComfyUI Server** (`/system_stats` status, active workflows, GPU allocation)
  - **Kokoro-82M Engine** (local deterministic pronunciation bank readiness)
- **Pipeline Statistics**: Global progress indicators across languages (English, French, Spanish, Italian) and video formats (`EXPRESSION`, `GAME`, `ROLEPLAY`, `FUN_FACTS`).
- **Stage Status Overview**: Breakdown of scripts currently pending, in-progress, or completed across all 6 generation stages.

### 2. Job Queue View (`JobQueueView.tsx`)
- **Active Task Monitoring**: Real-time visualization of background worker jobs queued or currently running.
- **Live Terminal Log Streaming**: Full-fidelity ANSI terminal emulation streaming process stdout/stderr directly from the backend via SSE (`GET /api/jobs/{id}/events`).
- **Job Controls**: Immediate cancellation / abort controls, re-run buttons, and historical log inspection.

### 3. Google Sheets Sync Studio (`GoogleSheetsSyncView.tsx`)
Interactive, 4-step browser interface implementing the full Google Sheets connectivity suite:
- **Step 1: Fetch External Revisions**: Pulls Column D (`SCRIPT_CHANGED`) from external Google Sheets spreadsheets into local `script_to_change` CSV queues. Supports full sheets, number ranges, or specific ID lists.
- **Step 2: Check & Audit Differences**: Executes a dry-run audit (`check_script_changes.py`), displaying before/after diffs, word count variances, and speaker normalization previews without modifying disk state.
- **Step 3: Apply Detected Changes**: Batch-updates local state JSONs with zero section duplication, automatically invalidating downstream generation stages (`voice_generation`, `image_generation`, `thumbnail_generation`, `video_assembly`) to `'pending'`.
- **Step 4: Scan Ready Scripts**: Scans Columns E–H (`script_ready == TRUE` and `video_ready == FALSE`), automatically grouping target expressions by broadcast date into `<date>_ready_scripts.csv`.

### 4. Mass Assets Creation Studio (`MassAssetsCreationView.tsx`)
High-throughput batch production interface designed for targeted asset recreation across arbitrary script IDs:
- **Flexible Script ID Parsing**: Accepts comma-separated, space-separated, newline-separated, or mixed ID inputs (e.g. `EE01, EE02, FG04, SR10`).
- **Instant ID Validation (`POST /api/scripts/validate-ids`)**: Real-time backend validation checking existence in `main/state/`, returning validated lists, target languages, formats, and flagging missing IDs.
- **Target Asset Selection**:
  - **Voice (TTS)** (`Stage _B`): Regenerates multi-speaker Qwen3-TTS audio with candidate sampling, Kokoro fallback, and automatic VRAM memory management.
  - **Scene Images** (`Stage _C`): Batch generates 4-scene or 6-scene storyboard illustrations with visual director anchors.
  - **Thumbnail Images** (`Stage _F`): Renders 576x1024 chalkboard thumbnails with FreeType titles and Flux character portraits.
- **Forced Re-Generation Modes**:
  - `All Assets`: Forces complete regeneration even if state JSON marks the asset as completed (`status = "done"`).
  - `Missing Only`: Generates assets only for scripts where the target asset status is `'pending'`.
- **Advanced Stage Controls**: Dynamic speaker gender overrides (`male, female`), seed locking, and candidate counts.

---

## Directory Layout

```text
main/webui/frontend/
├── src/
│   ├── components/                     # Reusable UI components
│   │   ├── Header.tsx                  # Top navigation bar, connection status, view tabs
│   │   ├── MetricCard.tsx              # KPI metric display cards
│   │   ├── LogViewer.tsx               # Real-time SSE streaming terminal log viewer
│   │   └── ServiceStatusBadge.tsx      # Live health indicators for ComfyUI / LLM
│   ├── views/                          # The 4 primary view components
│   │   ├── DashboardView.tsx           # Dashboard & health stats
│   │   ├── JobQueueView.tsx            # Active job monitor and SSE terminal
│   │   ├── GoogleSheetsSyncView.tsx    # 4-step Google Sheets sync workflow
│   │   └── MassAssetsCreationView.tsx  # Mass batch generation studio
│   ├── services/                       # API clients & SSE wrappers
│   │   └── api.ts                      # Typed fetch client connecting to FastAPI backend
│   ├── types/                          # Shared TypeScript interfaces & models
│   │   └── index.ts                    # Job, Script, Health, and Sheets types
│   ├── App.tsx                         # Root component & view router
│   ├── main.tsx                        # React application bootstrap
│   └── index.css                       # Tailwind CSS directives & global styling
├── public/                             # Static brand assets (favicons, logos)
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
