import json
import random
import sys
import time
import requests
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

def _safe_print(text: str, file=None, flush: bool = True) -> None:
    target = file or sys.stdout
    try:
        print(text, file=target, flush=flush)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"), file=target, flush=flush)

class ComfyClient:
    def __init__(self, api_url: str, workflow_json_path: Path, comfy_output_dir: Optional[Path] = None):
        self.api_url = api_url.rstrip("/")
        self.workflow_json_path = workflow_json_path
        self.comfy_output_dir = comfy_output_dir
        self.workflow_template = self._load_template()

    def _load_template(self) -> Dict[str, Any]:
        """Loads the ComfyUI API workflow template."""
        if not self.workflow_json_path.exists():
            raise FileNotFoundError(f"Workflow template not found at {self.workflow_json_path}")
        with self.workflow_json_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def check_connection(self) -> None:
        """Checks if the ComfyUI server is reachable and responsive."""
        from config import check_comfy_connection
        check_comfy_connection(self.api_url, raise_on_error=True)

    def free_memory(self, unload_models: bool = False) -> bool:
        """Forces ComfyUI to free memory cache but keeps models in RAM unless specified."""
        url = f"{self.api_url}/free"
        payload = {"unload_models": unload_models, "free_memory": True}
        try:
            resp = requests.post(url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            print(f"Warning: Could not free memory via API: {e}")
            return False

    def interrupt(self) -> bool:
        """Interrupts any currently executing workflow in ComfyUI immediately."""
        url = f"{self.api_url}/interrupt"
        try:
            resp = requests.post(url, timeout=15)
            return resp.status_code == 200
        except Exception as e:
            print(f"Warning: Could not interrupt ComfyUI execution: {e}")
            return False

    def clear_queue(self) -> bool:
        """Clears all pending items in ComfyUI's queue."""
        url = f"{self.api_url}/queue"
        try:
            resp = requests.post(url, json={"clear": True}, timeout=15)
            return resp.status_code == 200
        except Exception as e:
            print(f"Warning: Could not clear ComfyUI queue: {e}")
            return False

    def ensure_clean_slate(self) -> None:
        """Checks if ComfyUI has stuck running or pending tasks and cleans them up."""
        try:
            resp = requests.get(f"{self.api_url}/queue", timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                running = data.get("queue_running", [])
                pending = data.get("queue_pending", [])
                if running or pending:
                    _safe_print(f"[Watchdog] Detected {len(running)} running / {len(pending)} pending tasks in ComfyUI queue. Cleaning slate...")
                    self.interrupt()
                    self.clear_queue()
                    time.sleep(1.0)
        except Exception:
            pass

    def _prepare_workflow(
        self,
        ref_audio_name: str,
        target_text: str,
        language: str,
        gender: str,
        context: str,
        emotion: str,
        energy: str,
        style: str,
        output_prefix: str,
        seed: int = None
    ) -> Dict[str, Any]:
        """Clones the template and updates inputs for the specific segment."""
        # Deep copy the template
        wf = json.loads(json.dumps(self.workflow_template))
        
        # 1. Update LoadAudio (Node 6)
        # Verify Node 6 exists
        if "6" in wf and "inputs" in wf["6"]:
            wf["6"]["inputs"]["audio"] = ref_audio_name
            # Update the UI field just in case
            wf["6"]["inputs"]["audioUI"] = f"/api/view?filename={ref_audio_name}&type=input"

        # 2. Update SaveAudio (Node 8)
        if "8" in wf and "inputs" in wf["8"]:
            wf["8"]["inputs"]["filename_prefix"] = output_prefix

        # 3. Update Qwen3TTSVoiceClone (Node 39)
        if "39" in wf and "inputs" in wf["39"]:
            node_inputs = wf["39"]["inputs"]
            node_inputs["target_text"] = target_text
            node_inputs["target_language"] = language.capitalize()
            if seed is not None:
                node_inputs["seed"] = seed
            else:
                node_inputs["seed"] = random.randint(1, 10**15)
            
            # Generation parameters tuned for lively pace, zero robotic artifacts, and stable speaker timbre
            is_dialogue = "dialogue" in context.lower() or "roleplay" in context.lower()
            # Natural acoustic temperature (0.75-0.80) unlocks human vocal elasticity and pitch micro-contours
            node_inputs["temperature"] = 0.75 if not is_dialogue else 0.80
            node_inputs["top_p"] = 0.90 if not is_dialogue else 0.95
            node_inputs["top_k"] = 50
            node_inputs["subtalker_temperature"] = 0.75 if not is_dialogue else 0.80

            # Gentle repetition penalty (1.02) avoids audio token looping while preserving natural vowel duration and resonance
            node_inputs["repetition_penalty"] = 1.02

            # Dynamic max_new_tokens: 1 word ~ 4 tokens at 12Hz.
            # Allow 12 tokens/word, min 96 tokens (~8s), max 240 tokens (~20s).
            # This tightly bounds generation so runaway trailing silence is impossible.
            words_count = max(1, len(target_text.split()))
            node_inputs["max_new_tokens"] = max(96, min(240, words_count * 12))
            
            # Format the system-level instruction prompt with vivid theatrical acting directives
            personality_clause = f" Persona: {context}." if context else ""
            if is_dialogue:
                node_inputs["instruct"] = (
                    f"A {gender.lower()} voice actor performing authentic, natural conversational dialogue in {language}.{personality_clause} "
                    f"Emotional acting tone: {emotion}. "
                    f"Energy level: {energy.upper()}. "
                    f"Delivery: {style}. Natural spoken cadence, fluid phoneme blending, authentic breath, and human intonation. Avoid any robotic or monotone cadence."
                )
            else:
                node_inputs["instruct"] = (
                    f"A {gender.lower()} narrator delivering a lively YouTube Shorts presentation in {language}.{personality_clause} "
                    f"Tone: {emotion}. "
                    f"Energy level: {energy.upper()}. "
                    f"Delivery: {style}. Highly articulate, fluent, charismatic, and engaging with seamless vocal transitions."
                )

        return wf

    def queue_prompt(self, workflow: Dict[str, Any]) -> str:
        """Sends the workflow to the ComfyUI API to queue execution.
        Returns the prompt ID.
        """
        url = f"{self.api_url}/prompt"
        payload = {"prompt": workflow}

        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()

        data = response.json()
        if "prompt_id" not in data:
            raise KeyError(f"Failed to queue prompt, server returned: {data}")

        return data["prompt_id"]

    def get_history(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves history for the specific prompt execution."""
        url = f"{self.api_url}/history/{prompt_id}"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            if prompt_id in data:
                return data[prompt_id]
        except Exception:
            # Temporary socket delay or server busy during heavy tensor calculation
            return None
        return None

    def poll_for_completion(
        self,
        prompt_id: str,
        timeout_seconds: int = 300,
        poll_interval: float = 1.0,
        heartbeat_interval: float = 5.0,
    ) -> Dict[str, Any]:
        """Polls ComfyUI API until the execution is completed, returning outputs."""
        start_time = time.time()
        last_heartbeat = start_time
        while time.time() - start_time < timeout_seconds:
            history = self.get_history(prompt_id)
            if history:
                return history

            now = time.time()
            if now - last_heartbeat >= heartbeat_interval:
                elapsed = int(now - start_time)
                _safe_print(f"  [ComfyUI Voice] Generating... ({elapsed}s elapsed)")
                last_heartbeat = now

            time.sleep(poll_interval)

        raise TimeoutError(f"Prompt {prompt_id} execution timed out after {timeout_seconds} seconds.")

    def download_file(self, filename: str, subfolder: str, file_type: str, dest_path: Path) -> None:
        """Downloads a file from ComfyUI view API."""
        url = f"{self.api_url}/view"
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": file_type
        }

        # Ensure destination directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        response = requests.get(url, params=params, stream=True, timeout=60)
        response.raise_for_status()

        with dest_path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    def generate_voice_segment(
        self,
        ref_audio_name: str,
        target_text: str,
        language: str,
        gender: str,
        context: str,
        emotion: str,
        energy: str,
        style: str,
        output_prefix: str,
        dest_path: Path,
        seed: int = None,
        max_retries: int = 3,
        stall_timeout: int = 300,
    ) -> Path:
        """Executes the voice cloning pipeline for a single segment with auto-retry and watchdog.
        Returns the path to the downloaded audio file.
        """
        # Ensure ComfyUI queue is clean before queuing
        self.ensure_clean_slate()

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                # Prepare workflow payload
                wf = self._prepare_workflow(
                    ref_audio_name=ref_audio_name,
                    target_text=target_text,
                    language=language,
                    gender=gender,
                    context=context,
                    emotion=emotion,
                    energy=energy,
                    style=style,
                    output_prefix=output_prefix,
                    seed=seed
                )

                # Queue task
                print(f"Queuing voice generation (attempt {attempt}/{max_retries}): '{target_text[:35]}...'")
                prompt_id = self.queue_prompt(wf)

                # Poll for completion
                print(f"Executing workflow (ID: {prompt_id}). Polling for results...")
                history = self.poll_for_completion(prompt_id, timeout_seconds=stall_timeout)

                # Parse outputs to find the SaveAudio file details
                outputs = history.get("outputs", {})

                # Look for SaveAudio node (usually node 8 in our template)
                save_node_id = "8"
                if save_node_id not in outputs:
                    # Fallback search for a node that has "audio" output containing file details
                    for nid, nout in outputs.items():
                        if "audio" in nout and isinstance(nout["audio"], list) and len(nout["audio"]) > 0:
                            save_node_id = nid
                            break

                if save_node_id not in outputs:
                    raise KeyError(f"SaveAudio output node could not be found in history outputs: {outputs}")

                audio_list = outputs[save_node_id]["audio"]
                if not audio_list:
                    raise ValueError(f"No audio file output was generated by node {save_node_id}")

                audio_info = audio_list[0]
                filename = audio_info["filename"]
                subfolder = audio_info.get("subfolder", "audio")
                file_type = audio_info.get("type", "output")

                # Download output
                print(f"Downloading generated audio: {filename}")
                self.download_file(filename, subfolder, file_type, dest_path)

                # Cleanup original from ComfyUI output directory to prevent duplicates
                if self.comfy_output_dir:
                    source_file = self.comfy_output_dir / subfolder / filename
                    try:
                        if source_file.exists():
                            source_file.unlink()
                    except Exception as e:
                        print(f"Warning: Could not delete original file {source_file}: {e}")

                # Brief breather between generations so memory and CUDA stream settle
                time.sleep(0.3)
                return dest_path

            except TimeoutError as te:
                last_error = te
                _safe_print(
                    f"[Watchdog] ComfyUI voice generation stalled (> {stall_timeout}s). Auto-interrupting...",
                )
                self.interrupt()
                time.sleep(1.5)
                if attempt < max_retries:
                    _safe_print(
                        f"[Watchdog] Retrying voice generation (attempt {attempt + 1}/{max_retries})... "
                        f"\"Go ahead, don't stop!\"",
                    )
            except Exception as exc:
                last_error = exc
                if attempt < max_retries:
                    _safe_print(
                        f"[Watchdog] ComfyUI voice generation error ({exc}). Retrying (attempt {attempt + 1}/{max_retries})...",
                    )
                    self.interrupt()
                    time.sleep(1.5)

        raise last_error or RuntimeError("Failed to generate voice segment after retries.")
