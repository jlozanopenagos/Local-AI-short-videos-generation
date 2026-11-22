# Shorts Studio tests

Run the suite from the repository root. Install FFmpeg and FFprobe on PATH, or use the bundled Windows binaries in the assembly directory. The required media workflow fails if either executable is unavailable.

```powershell
py -m pip install -r main/requirements.txt -r test/requirements-test.txt
npm --prefix main/webui/frontend ci
npm --prefix main/webui/frontend run build
py -m playwright install chromium
py -m pytest test -m "not live"
```

Set `STUDIO_TEST_CHROMIUM` to an installed Chromium executable to use it instead of the Playwright-managed browser.

| Check | What runs | What it proves |
|---|---|---|
| `py -m pytest test/webui/test_workspace_workflow.py` | Real Sheets import logic, API, job manager, stage adapters, state, chalkboard and thumbnail renderers, subtitle builder, and FFmpeg | An approved Game revision becomes a decodable short and thumbnail. The media API serves the MP4 with byte ranges. A failed forced render preserves the previous MP4 and a retry completes. |
| `py -m pytest test/browser` | Built React app, Chromium, FastAPI, and the real thumbnail adapter | A user can select a script, queue a thumbnail, see a real failure, retry, and load the result in the media panel. |
| `py -m pytest test -m "not browser and not live"` | Backend workflow plus narrower unit, API, integration, and connectivity checks | Targeted language and format rules, service contracts, cancellation, state compatibility, and delivery safety. |

The workflow uses checked-in lesson data and temporary state and output directories. It supplies Sheets rows, prompt responses, TTS clips, image HTTP responses, and transcription timestamps through test doubles. These checks can run without production API keys or model weights. The voice characterization suite checks all 16 golden IDs with offline takes, including production narrator prompts and preservation of the prior master after a failed forced merge.

## Live workstation check

Use a dedicated or idle ComfyUI instance with the production workflows, local models, and voice references already configured. The smoke check writes generated project assets to a temporary workspace and submits real work to your configured GPU. Google writes are outside this smoke check.

```powershell
$env:SHORTS_LIVE_COMFY = "1"
py -m pytest test/live
Remove-Item Env:SHORTS_LIVE_COMFY
```

The GitHub workflow runs the frontend build, deterministic backend suite, required FFmpeg workflow, and browser test on Windows. Live GPU verification runs separately when explicitly enabled.


## Voice quality comparisons

The preview runner requires a new workspace and a baseline directory containing per-ID folders with frozen script JSON. It uses the workstation's configured ComfyUI. Each preview keeps the winning master, timing map, alternate takes, and a JSON trace of the requested reference and quality checks.

```powershell
py test/tools/render_voice_preview.py --baseline scratch/voice-golden/baseline --workspace scratch/voice-golden/example --mode direction --ids EG01 --sections challenge
```

Use `roleplay` on selected dialogue sections to audition continuous turns and localized acting with their assigned cast. Use `baseline` for the existing directions and splitting, `continuity` to keep narrator paragraphs together, `direction` to try localized beat and turn instructions, or `reference` to add available same-speaker reference variants. Use `--recast` for a separate casting comparison. `--pitch-anchor-section hook` compares local pitch windows with a reviewed baseline hook. `--voice-anchor-section hook` also uses that narrator clip and its script transcript as the ICL reference.

`test/tools/compare_voice_preview.py` exports loudness-matched A/B clips and a separate answer key. Install `librosa` in the QA environment for `--pyin`. With SpeechBrain installed and local ECAPA model files, `--ecapa-model` adds cosine similarity as a diagnostic. The pitch and similarity measurements support listening review. Reference variants can differ perceptually even when they share a speaker ID. Review those pairs before setting an identity threshold or promoting a preset.
