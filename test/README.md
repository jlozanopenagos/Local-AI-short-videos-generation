# Shorts Studio tests

Run the suite from the repository root (`shorts_automation/`). Install FFmpeg and FFprobe on `PATH`, or use the bundled Windows binaries in `main/video_creation/_G_video_assembly/`. The required media workflow fails if either executable is unavailable.

```powershell
py -m pip install -r main/requirements.txt -r test/requirements-test.txt
npm --prefix main/webui/frontend ci
npm --prefix main/webui/frontend run build
py -m playwright install chromium

# Offline pytest automatically isolates VOICE_PROVIDER="local" & ELEVENLABS_API_KEY=""
# via test/conftest.py (unless SHORTS_LIVE_ELEVENLABS=1 is set).
py -m pytest test -m "not live" --basetemp="$env:TEMP\shorts_pytest_tmp" -o cache_dir="$env:TEMP\shorts_pytest_cache"
```

Set `STUDIO_TEST_CHROMIUM` to an installed Chromium executable to use it instead of the Playwright-managed browser. On Windows, `--basetemp` and `-o cache_dir` avoid `test\.pytest_cache` / `%TEMP%` permission collisions.

## Test layout (`63` Python files)

| Path / Check | What runs | What it proves |
|---|---|---|
| `test/unit/` (`35` test files) | Core script engines, ElevenLabs catalog/LRU, local VoiceDesign bank/casting, Stage C visual prompts & Gemini auditor, chalkboard/thumbnail renderers, subtitles (non-overlap, collapse recovery), FFmpeg assembly, Drive scoped sync, and Sheets router (incl. Column J sync) | Unit invariants across Stages A–G and WebUI/connectivity services (strictly offline via `conftest.py` isolation). |
| `test/connectivity/` (`5` files) | Sheets fetcher, corrected-scripts CSV sync, reconciler, poster, ready-scripts scanner | Sheets HTTP client & CSV pipeline contracts. |
| `test/integration/` (`6` files) | SQLite Expression DB, service health checks, sample CSV/JSON schemas, gitignore/privacy security checks, status tracker, verbatim ingestion | Data contracts, security exclusions, and `check_script_changes.py`. |
| `test/webui/test_workspace_workflow.py` | Real Sheets import logic, API, job manager, stage adapters, state, chalkboard and thumbnail renderers, subtitle builder, and FFmpeg | An approved Game revision becomes a decodable short and thumbnail. The media API serves the MP4 with byte ranges. A failed forced render preserves the previous MP4 and a retry completes. |
| `test/browser/test_studio.py` | Built React app, Chromium, FastAPI, and the real thumbnail adapter | A user can select a script, queue a thumbnail, see a real failure, retry, and load the result in the media panel. |
| `py -m pytest test -m "not browser and not live"` | Deterministic backend suite (`unit`, `connectivity`, `integration`, `webui`) | Target language and format rules, service contracts, cancellation, state compatibility, and delivery safety. |

The workflow uses checked-in lesson data (`test/fixtures/image_prompts/states/`) and temporary state and output directories. It supplies Sheets rows, prompt responses, TTS clips, image HTTP responses, and transcription timestamps through test doubles.

## Live workstation check

Use a dedicated or idle ComfyUI instance with the production workflows, local models, and voice references already configured. The smoke check (`test/live/test_comfy_workstation.py`) writes generated project assets to a temporary workspace and submits real work to your configured GPU. Google writes are outside this smoke check.

```powershell
$env:SHORTS_LIVE_COMFY = "1"
py -m pytest test/live
Remove-Item Env:SHORTS_LIVE_COMFY
```

The GitHub workflow runs the frontend build, deterministic backend suite, required FFmpeg workflow, and browser test on Windows. Live GPU verification runs separately when explicitly enabled.

## Voice quality comparison tools (`test/tools/`)

- `test/tools/render_voice_preview.py`: Renders isolated ComfyUI voice previews (`baseline`, `continuity`, `direction`, `reference`, `roleplay`) from a baseline directory containing frozen script JSONs.
- `test/tools/compare_voice_preview.py`: Exports loudness-matched A/B clips and an answer key (`--pyin`, optional `--ecapa-model`).
- `test/tools/freeze_image_fixtures.py`: Snapshots/updates frozen Stage C golden image prompt contracts in `test/fixtures/image_prompts/`.
- `test/image_prompt_harness.py`: Offline harness for comparing Stage C visual prompt drafts and snapshots.
