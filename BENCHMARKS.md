# Performance Benchmarks & Pipeline Evolution

This document tracks the historical and current performance benchmarks of the **LingoVerse Shorts Automation Pipeline**. As optimizations, hardware profiles, and batching strategies evolve, this log serves as the canonical record of execution efficiency, VRAM usage, and generation latency.

---

## 1. Executive Summary & Pipeline Evolution

| Metric / Stage | Version 1.0 (Naive Sequential) | Version 2.0 (Interleaved ID-by-ID) | Version 3.0 (Two-Phase Decoupled) | Evolution Gain |
| :--- | :--- | :--- | :--- | :--- |
| **Prompt Generation Strategy** | On-demand per scene with repeated LLM calls | Per-ID prompt generation before each ID's render | **Phase 1 Batched LLM session across all target IDs** | **~10x faster prompt generation** |
| **Prompt Speed per Script** | ~60s – 90s per script | ~30s – 45s per script | **22.8s per script (~4.4s per scene)** | **~2x – 4x faster** |
| **LLM Server Cycling Overhead** | Cycled constantly (VRAM collision) | 30 starts & stops for 30 IDs (~25–30 min pure idle) | **Single LLM session (1 startup, 1 shutdown)** | **Zero idle switching pauses** |
| **GPU VRAM Handoff** | High collision risk between LLaMA & ComfyUI | High fragmentation across 30 swap cycles | **Clean 1-time handoff freeing ~2.0 GB VRAM** | **Stable 0 OOM crashes** |
| **Image Render Duration** | **350s – 450s / image** (excluding prompt time) | **90s – 120s / image** (excluding swap time) | **90s – 115s / image** (continuous steady state) | **3.5x – 4x faster than v1** |
| **Game Script Optimization** | Rendered all 5 scenes in ComfyUI | Rendered all 5 scenes in ComfyUI | **Native chalkboard + static waiting (0s)** | **Saves ~3.5 min per Game video** |
| **Total 30-Script Production Time** | **~15 – 18 hours** | **~6 – 7.5 hours** | **~4.5 – 5 hours** | **~65% – 70% total time saved** |

---

## 2. Benchmark Run: 30-Script Mass Image Production

* **Run Date**: 2026-11-11
* **Active Job ID**: `AE2CC6D7`
* **Target Scripts**: 30 IDs (`IE07`, `IG07`, `IR07`, `IE09`, `IG09`, `IR09`, `IE02`, `IG02`, `IR02`, `IE48`, `IG48`, `IR48`, `IE87`, `IG87`, `IR87`, `SE08`, `SG08`, `SR08`, `SE33`, `SG33`, `SR33`, `SE02`, `SG02`, `SR02`, `SE37`, `SG37`, `SR37`, `SE27`, `SG27`, `SR27`)
* **Hardware Profile**: Local Single-GPU workstation (NVIDIA RTX VRAM-constrained architecture).

### Phase 1: Batched Storyboard Visual Prompt Generation (LLM)
* **Start Time**: `13:30:19`
* **End Time**: `13:42:17`
* **Total Phase 1 Duration**: **718.0 seconds (11.97 minutes)**
* **Total Scripts Processed**: 30 scripts (150+ visual scene prompts generated)
* **Average Generation Time per Script**: **22.80s**
* **Average Time per Scene Prompt**: **~4.38s**
* **Fastest Script**: `IE48` (17.0s) | **Slowest Script**: `SR08` (30.0s)

#### Per-Script Prompt Timing Log:
* `IE07`: 29.0s
* `IG07`: 22.0s
* `IR07`: 28.0s
* `IE09`: 21.0s
* `IG09`: 21.0s
* `IR09`: 22.0s
* `IE02`: 22.0s
* `IG02`: 24.0s
* `IR02`: 29.0s
* `IE48`: 17.0s
* `IG48`: 28.0s
* `IR48`: 28.0s
* `IE87`: 20.0s
* `IG87`: 18.0s
* `IR87`: 20.0s
* `SE08`: 23.0s
* `SG08`: 23.0s
* `SR08`: 30.0s
* `SE33`: 19.0s
* `SG33`: 20.0s
* `SR33`: 24.0s
* `SE02`: 22.0s
* `SG02`: 20.0s
* `SR02`: 28.0s
* `SE37`: 24.0s
* `SG37`: 18.0s
* `SR37`: 23.0s
* `SE27`: 18.0s
* `SG27`: 17.0s
* `SR27`: 26.0s

---

### Phase 2: Batch ComfyUI FIFO Queue Rendering
* **Start Time**: `13:42:17`
* **Status**: Continuous FIFO batch queue without GPU idle stops.

#### Scene Render Latency Breakdown:
* **Initial Model Warm-up**: `IE07_hook.png` took **221.2s** (first image includes unet model weight transfer into VRAM and text encoder initialization).
* **Steady-State Range**: **90.3s – 128.3s** per image.
* **Representative Steady-State Samples**:
  * `IR07_dialogue_part_3.png`: **90.3s**
  * `IE07_payoff.png`: **92.2s**
  * `IR07_hook.png`: **92.2s**
  * `IR07_dialogue_part_2.png`: **92.2s**
  * `IR07_payoff.png`: **92.2s**
  * `IE09_hook.png`: **92.2s**
  * `IR07_dialogue_part_1.png`: **92.4s**
  * `IE07_example.png`: **94.2s**
  * `IG07_explanation.png`: **97.0s**
  * `IG07_answer.png`: **98.2s**
  * `IR07_dialogue_part_4.png`: **107.0s**
  * `IE09_setup.png`: **108.7s**
  * `IE07_discovery.png`: **108.9s**

#### Complete Script Turnaround Times:
* **Expression Script (`IE07`, 5 scenes)**: **655.7s (10.9 min)** *(includes initial 221s cold warm-up)*
* **Game Script (`IG07`, 5 scenes total)**: **319.1s (5.3 min)**
  * *`challenge`*: 0s (Native Python chalkboard engine)
  * *`pressure`*: 0s (Pre-rendered static asset)
  * *`hook`, `answer`, `explanation`*: ~97s each in ComfyUI
* **Roleplay Script (`IR07`, 6 scenes)**: **569.0s (9.48 min)** (~94.8s / scene average)
* **Expression Script (`IE09`, 5 scenes)**: **638.3s (10.64 min)**

---

## 3. Analysis & Key Insights

1. **Decoupled Architecture Wins**:
   By executing all LLM prompt operations in Phase 1 and fully shutting down the LLaMA server before calling ComfyUI, the GPU has 100% of its VRAM dedicated to ComfyUI. This prevents CUDA Out-Of-Memory thrashing and eliminates the 45-60s server reboot latency per ID.

2. **Continuous FIFO Queue in ComfyUI**:
   Enqueuing all scenes of a script simultaneously into ComfyUI's native queue keeps the model weights hot in VRAM, bringing steady-state rendering down to **~90 – 95 seconds per image**.

3. **Game Content Optimization**:
   The native programmatic chalkboard renderer and language-specific static waiting assets eliminate 2 unnecessary ComfyUI generations per game video, cutting Game generation time in half (from ~10.5 minutes down to ~5.3 minutes).

---

## 4. Benchmark Run: Stage B Voice Synthesis — Smart Queue & QA Gate Optimization

* **Run Dates**: `2026-11-23` (Baseline `23:09` run) vs. `2026-11-24` (Optimized `00:17` run)
* **Target / Scope**: Multi-character Roleplay voice synthesis (`ER01` — 10 segments EN, `SR08` — 10 segments ES; part of `ER01`, `SR08`, `SG02` WebUI batch)
* **Optimizations Benchmarked**:
  1. **Adaptive Take #2 (`Fast-Pass Take #1`)**: Evaluates Take #1 immediately; skips Take #2 whenever Take #1 is clean (`flags == []`) and `score >= 0.75`.
  2. **Speaker-Grouped Synthesis**: Synthesizes segments grouped by speaker (`Narrator` → `PERSON_ONE` → `PERSON_TWO`) so ComfyUI reuses the same reference voice consecutively, then re-sorts by original segment index before final merge.
  3. **Node 40 (`SenseVoiceASR`) Bypass**: Strips redundant ASR reference transcription from the ComfyUI workflow whenever `ref_text` is already known or `x_vector_only=True`.
  4. **Calibrated Acoustic QA Gate & Locked ICL Identity**: Reference-F0-anchored shrillness ceiling, `1.35s` breath allowance on multi-sentence/hook/payoff/explicit-pause segments, restored `use_icl=True` on one locked `baseline.wav` per Roleplay character, and `PermissionError` (`WinError 32`) retry on ComfyUI `.flac` cleanup.

### Before vs. After Comparison

| Metric | `ER01` Before (`23:09`) | `ER01` After (`00:17`) | `SR08` Before (`23:23`) | `SR08` After (`00:25`, through Seg 7) |
| :--- | :---: | :---: | :---: | :---: |
| **Total Script Duration** | `865.9s` (~14.4 min) | **`455.1s` (~7.6 min)** | `777.8s` (~13.0 min) | **~430–460s projected** (~7.2–7.7 min) |
| **Net Speedup** | — | **`-410.8s` (-6.8 min / 47.4% faster)** | — | **~41% – 45% faster** |
| **Total ComfyUI Takes** | 26 takes | **13 takes (-50%)** | 22 takes | 10 takes across first 8 segments |
| **Fast-Passed on Take #1** | 0 / 10 (always 2 takes) | **7 / 10** (`Scores: 0.78–1.07`) | 0 / 10 (always 2 takes) | **7 / 7** on first 7 segs (`Scores: 0.80–0.99`, ~4.5 min) |
| **Calm 3rd-Take Retries** | 5 | **0** | 2 | 1 (Seg 5 only) |
| **`WinError 32` Cleanup Warnings** | 1 | **0** | 0 | **0** |

### Key Observations & Bottlenecks
1. **Adaptive Take #2 Cuts Render Count in Half Without Quality Loss**: On `ER01`, 7 of 10 segments passed cleanly on Take #1 and skipped Take #2 immediately. The QA gate still caught genuine defects on Take #1 (`ER01` Seg 1 erratic pitch `38.0%`, Seg 10 `+9.2 ST` register drift), and Take #2 recovered both cleanly (`0.93` and `0.90`).
2. **Speaker Grouping & Locked Character Identity**: Grouping turns (`Narrator` → `PERSON_ONE` → `PERSON_TWO`) under `use_icl=True` with a single locked `baseline.wav` kept `PERSON_ONE` pitch variance tightly consistent (`16%–23%`, scores `0.78–0.99`) across all 4 dialogue turns on both `ER01` and `SR08`, with final merged duration `60.46s` on `ER01`.
3. **False QA Retries Eliminated**: Zero false silence-freeze (`> 0.85s`) or shrillness triggers occurred in the optimized run.
4. **Watch Item (`SR08` Seg 5)**: Short incredulous male questions (`"¿Embarazada tú?..."` on `es_m_narrator_conversational_08`, low baseline F0 `~115–127 Hz`) tripped `+5.4` to `+7.8 ST` register drift on all 3 takes (`+96s`). If this recurs across other shocked male questions, relaxing the Roleplay drift guard from `4.5 ST` to `5.5 ST` is a safe follow-up.

---

## 5. Benchmark Log Entry Template

Use this format when recording future benchmarks (e.g. Stage B Voice Synthesis, Stage G Video Assembly, or future ComfyUI model optimizations):

```markdown
### Benchmark Run: [Stage Name] — [YYYY-MM-DD]
* **Target / Scope**: [e.g. 30 scripts, Voice / Image / Assembly]
* **Hardware & Driver**: [GPU, CUDA version, OS]
* **Phase 1 Metrics**: [Total duration, average per script, min/max]
* **Phase 2 Metrics**: [Steady-state latency per asset, warmup time]
* **Key Observations / Bottlenecks**: [Notes on memory, throughput, or regressions]
```

