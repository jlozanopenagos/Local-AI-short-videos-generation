# Contributor & Agent Guidance: Shorts Automation

> [!NOTE]
> **Repository Scope & Isolation:** `shorts_automation/` is a standalone Git repository. Restrict all edits strictly inside `shorts_automation/` — never modify companion workspaces such as `GoogleSheet_UI_auditor/` or `ComfyUI_windows_portable/`.

This repository houses **Shorts Studio** (`main/`), the production pipeline and React + FastAPI WebUI for generating vertical language-learning Shorts across **English**, **French**, **Spanish**, and **Italian** (`EXPRESSION`, `GAME`, `ROLEPLAY`, `FUN_FACTS`).

For the full system contract, stage rules, invariants, and file index, see [main/AGENTS.md](main/AGENTS.md) and [main/README.md](main/README.md).

---

## Quick Launch & Key Entry Points

```powershell
# Launch WebUI Management Studio (http://127.0.0.1:8190)
py main/tools/webui.py

# Headless service supervisors (ComfyUI + llama.cpp)
py main/tools/comfy.py {start|stop|status|logs}
py main/tools/llama.py {start|stop|status|logs}

# Build WebUI frontend after editing main/webui/frontend/src/**
npm --prefix main/webui/frontend run build
```

- **Production State:** `1,224` script state JSON files under `main/state/<language>/<video_type>/` (`EN: 372`, `IT: 303`, `ES: 279`, `FR: 270`).
- **Voice Architecture (Hybrid):**
  - **ElevenLabs (`eleven_v3`)** powers `ROLEPLAY`, `EXPRESSION`, and `FUN_FACTS` using a `227`-voice curated catalog (`main/video_creation/_B_voice_generation/elevenlabs/voice_catalog.json`) with full-cycle LRU (`max_history=60`).
  - **Local Qwen3-TTS (`ComfyUI`)** powers `GAME` (and any local override) using `52` baseline voices in `VOICE_BANK_DIR/voice_bank_manifest.json` (`60% es_latam_neutral / 40% es_spain_castilian` exact rotation for Spanish).

---

## Test & Verification Safety

Offline tests automatically isolate `VOICE_PROVIDER="local"` and clear `ELEVENLABS_API_KEY` via `test/conftest.py` (unless `SHORTS_LIVE_ELEVENLABS=1` is set), so `py -m pytest` never spends live ElevenLabs credits:

```powershell
py -m pytest test -m "not live and not browser" --basetemp="$env:TEMP\shorts_pytest_tmp" -o cache_dir="$env:TEMP\shorts_pytest_cache"
```

For full test instructions, see [test/README.md](test/README.md).
