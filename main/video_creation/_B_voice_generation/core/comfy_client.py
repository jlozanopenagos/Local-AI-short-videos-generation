import contextlib
from collections import deque
import json
import random
import sys
import time
import re
import requests
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

try:
    from video_creation._B_voice_generation.voice.common.bank_manifest import VoiceBankManifest, sanitize_ref_transcript
    from video_creation._B_voice_generation.voice.languages import get_language_voice_profile
except (ImportError, ModuleNotFoundError):
    try:
        from ..voice.common.bank_manifest import VoiceBankManifest, sanitize_ref_transcript  # type: ignore[no-redef]
        from ..voice.languages import get_language_voice_profile  # type: ignore[no-redef]
    except (ImportError, ValueError):
        from voice.common.bank_manifest import VoiceBankManifest, sanitize_ref_transcript  # type: ignore[no-redef]
        from voice.languages import get_language_voice_profile  # type: ignore[no-redef]


def _safe_print(text: str, file=None, flush: bool = True) -> None:
    target = file or sys.stdout
    try:
        print(text, file=target, flush=flush)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"), file=target, flush=flush)


LOCALIZED_INSTRUCT_TEMPLATES = {
    "spanish": {
        "narrator": (
            "Un narrador nativo de español ({gender_es}) carismático y cálido presentando un video corto de YouTube Shorts con energía {energy_es}. "
            "Acento español neutro estándar 100% nativo, pronunciación hispana pura, cálida y natural, sin ningún rastro de acento estadounidense o inglés. "
            "Tono: {emotion}. Estilo: {style}. "
            "{pace_es}, entonación muy expresiva y auténtica de hablante nativo."
        ),
        "dialogue": (
            "Un hablante nativo de español ({gender_es}) actuando en un diálogo conversacional expresivo con energía {energy_es}. "
            "Acento español neutro estándar 100% nativo, pronunciación hispana auténtica y natural, sin ningún rastro de acento estadounidense o inglés. "
            "Manteniendo estrictamente el mismo registro vocal, tono y timbre de personaje en cada frase sin saltos bruscos de tono. "
            "Tono actoral de la réplica: {emotion}. Estilo: {style}. "
            "Voz estable, {pace_es}, inflexión emocional auténtica y dicción muy nítida."
        ),
    },
    "french": {
        "narrator": (
            "Un narrateur natif français ({gender_fr}) plein d'esprit parisien, charismatique, complice et chaleureux, présentant un court métrage YouTube Shorts avec une énergie {energy_fr}. "
            "Accent français parisien standard pur (France métropolitaine, Paris), prononciation parisienne raffinée et vivante, sans aucun accent américain, anglais ou québécois. "
            "Musicalité française authentique avec groupes rythmiques fluides, liaisons naturelles soignées, intonation montante chantante sur les questions et sourire dans la voix. "
            "Ton : {emotion}. Style : {style}. "
            "{pace_fr}, intonation chaleureuse et très expressive."
        ),
        "dialogue": (
            "Un locuteur natif français ({gender_fr}) plein de naturel et de charme parisien jouant un dialogue conversationnel expressif avec une énergie {energy_fr}. "
            "Accent français parisien standard pur (France métropolitaine, Paris), prononciation parisienne fluide et authentique, sans aucun accent américain, anglais ou québécois. "
            "En conservant strictement le même registre vocal, timbre de voix et hauteur fondamentale tout au long du dialogue sans variation artificielle. "
            "Musicalité française legato naturelle, groupes rythmiques chantants et sourire expressif dans la voix. "
            "Ton théâtral de la réplique : {emotion}. Style : {style}. "
            "Timbre vocal stable, {pace_fr}, inflexion émotionnelle authentique et articulation nette."
        ),
    },
    "italian": {
        "narrator": (
            "Un narratore madrelingua italiano ({gender_it}) carismatico, solare e coinvolgente che presenta un video YouTube Shorts con energia {energy_it}. "
            "Accento italiano standard autentico e brillante, con la naturale musicalità, calore ed espressività tipica di un vero madrelingua italiano (mai piatto o artificiale, nessun accento straniero). "
            "Tono: {emotion}. Stile: {style}. "
            "{pace_it}, dizione italiana limpida e intonazione espressiva."
        ),
        "dialogue": (
            "Un parlante madrelingua italiano ({gender_it}) che recita in un dialogo conversazionale espressivo con energia {energy_it}. "
            "Accento italiano standard autentico e brillante, con la tipica musicalità, calore ed espressività spontanea italiana (nessun accento inglese o straniero). "
            "Mantenendo rigorosamente lo stesso registro vocale, timbro e altezza fondamentale in ogni battuta senza salti di tonalità. "
            "Tono recitativo della battuta: {emotion}. Stile: {style}. "
            "Timbro vocale stabile, {pace_it}, inflessione emotiva autentica e dizione limpida."
        ),
    },
}


class ComfyClient:
    def __init__(self, api_url: str, workflow_json_path: Path, comfy_output_dir: Optional[Path] = None):
        self.api_url = api_url.rstrip("/")
        self.workflow_json_path = workflow_json_path
        self.comfy_output_dir = comfy_output_dir
        self.workflow_template = self._load_template()
        self._ref_transcripts_cache: Optional[Dict[str, str]] = None
        self.check_cancelled: Optional[Callable[[], bool]] = None
        self.pool = None
        try:
            # pyrefly: ignore[missing-import]
            from core.comfy_pool import get_comfy_pool
            self.pool = get_comfy_pool(self.api_url)
        except Exception:
            pass

    def _load_template(self) -> Dict[str, Any]:
        """Loads the ComfyUI API workflow template."""
        if not self.workflow_json_path.exists():
            raise FileNotFoundError(f"Workflow template not found at {self.workflow_json_path}")
        with self.workflow_json_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _has_manifest_ref_text(self, ref_audio_name: str) -> bool:
        """Returns True if `ref_audio_name` exists in the curated `VoiceBankManifest` with a transcript."""
        if not ref_audio_name:
            return False
        if not hasattr(self, "_bank_manifest_cache"):
            self._bank_manifest_cache = VoiceBankManifest.load()
        if self._bank_manifest_cache is None:
            return False
        return bool(self._bank_manifest_cache.lookup_ref_text(ref_audio_name))

    def _get_ref_transcript(self, ref_audio_name: str, language: str = "") -> str:
        """Looks up a reference transcript from curated bank manifest or cleaned `ref_transcripts.json`."""
        if not ref_audio_name:
            return ""
        if not hasattr(self, "_bank_manifest_cache"):
            self._bank_manifest_cache = VoiceBankManifest.load()
        if self._bank_manifest_cache is not None:
            manifest_txt = self._bank_manifest_cache.lookup_ref_text(ref_audio_name)
            if manifest_txt:
                return manifest_txt

        if self._ref_transcripts_cache is None:
            self._ref_transcripts_cache = {}
            try:
                import config
                t_path = getattr(config, "REF_TRANSCRIPTS_PATH", None)
                if t_path and Path(t_path).exists():
                    raw = json.loads(Path(t_path).read_text(encoding="utf-8"))
                    if isinstance(raw, dict):
                        for k, v in raw.items():
                            self._ref_transcripts_cache[k] = str(v)
                            self._ref_transcripts_cache[Path(k).name] = str(v)
            except Exception:
                pass
        raw_txt = (
            self._ref_transcripts_cache.get(ref_audio_name)
            or self._ref_transcripts_cache.get(Path(ref_audio_name).name)
            or ""
        )
        return sanitize_ref_transcript(raw_txt, language=language, audio_name=ref_audio_name)

    def check_connection(self) -> None:
        """Checks if the ComfyUI server is reachable and responsive."""
        from config import check_comfy_connection
        check_comfy_connection(self.api_url, raise_on_error=True)

    def _http_get(self, url: str, **kwargs) -> requests.Response:
        if hasattr(requests.get, "mock_calls"):
            return requests.get(url, **kwargs)
        if self.pool:
            return self.pool.session.get(url, **kwargs)
        return requests.get(url, **kwargs)

    def _http_post(self, url: str, **kwargs) -> requests.Response:
        if hasattr(requests.post, "mock_calls"):
            return requests.post(url, **kwargs)
        if self.pool:
            return self.pool.session.post(url, **kwargs)
        return requests.post(url, **kwargs)

    def free_memory(self, unload_models: bool = False) -> bool:
        """Forces ComfyUI to free memory cache but keeps models in RAM unless specified."""
        url = f"{self.api_url}/free"
        payload = {"unload_models": unload_models, "free_memory": True}
        try:
            resp = self._http_post(url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            print(f"Warning: Could not free memory via API: {e}")
            return False

    def interrupt(self) -> bool:
        """Interrupts any currently executing workflow in ComfyUI immediately."""
        url = f"{self.api_url}/interrupt"
        try:
            resp = self._http_post(url, timeout=15)
            return resp.status_code == 200
        except Exception as e:
            print(f"Warning: Could not interrupt ComfyUI execution: {e}")
            return False

    def cancel_prompts(self, prompt_ids: list[str]) -> None:
        """Remove pending takes and interrupt running takes owned by this job."""
        if not prompt_ids:
            return
        try:
            self._http_post(f"{self.api_url}/queue", json={"delete": prompt_ids}, timeout=5).raise_for_status()
        except requests.RequestException as exc:
            _safe_print(f"Could not remove pending voice prompts: {exc}")
        for prompt_id in prompt_ids:
            try:
                self._http_post(
                    f"{self.api_url}/interrupt", json={"prompt_id": prompt_id}, timeout=5,
                ).raise_for_status()
            except requests.RequestException as exc:
                _safe_print(f"Could not interrupt voice prompt {prompt_id}: {exc}")

    def _check_job_cancelled(self) -> None:
        if self.check_cancelled is not None and self.check_cancelled():
            raise InterruptedError("Voice generation cancelled.")

    def clear_queue(self) -> bool:
        """Clears all pending items in ComfyUI's queue."""
        url = f"{self.api_url}/queue"
        try:
            resp = self._http_post(url, json={"clear": True}, timeout=15)
            return resp.status_code == 200
        except Exception as e:
            print(f"Warning: Could not clear ComfyUI queue: {e}")
            return False

    def ensure_clean_slate(self) -> None:
        """Checks if ComfyUI has stuck running or pending tasks and cleans them up."""
        try:
            resp = self._http_get(f"{self.api_url}/queue", timeout=15)
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

    @staticmethod
    def _localize_emotion_and_style(
        lang_norm: str,
        emotion: str,
        style: str,
        is_dialogue_speaker: bool,
    ) -> Tuple[str, str]:
        """Translates English emotion and persona/style descriptions into pure target-language text
        so zero English words bleed into Romance-language Qwen3-TTS instruct prompts.
        """
        emo_low = (emotion or "").strip().lower()
        style_low = (style or "").strip().lower()

        if lang_norm == "french":
            if "game-show" in emo_low or "trivia" in emo_low or "countdown" in emo_low or "celebratory" in emo_low:
                if "countdown" in emo_low or "suspense" in emo_low:
                    emo_loc = "suspense intense et anticipation de jeu télévisé"
                elif "triumphant" in emo_low or "reveal" in emo_low:
                    emo_loc = "révélation triomphante, enthousiaste et joyeuse"
                else:
                    emo_loc = "animateur de quiz dynamique, enthousiaste et captivant"
            elif "frustrated" in emo_low or "exasperated" in emo_low or "panicked" in emo_low or "anxious" in emo_low:
                emo_loc = "frustré, expressif et très réactif"
            elif "surprise" in emo_low or "baffled" in emo_low or "incredulous" in emo_low or "confusion" in emo_low:
                emo_loc = "surpris, incrédule et intrigué avec naturel"
            elif "delighted" in emo_low or "fascinated" in emo_low:
                emo_loc = "fasciné, ravi et agréablement surpris"
            elif "dramatic" in emo_low or "intriguing" in emo_low or "mysterious" in emo_low:
                emo_loc = "captivant, expressif et plein de suspense"
            elif "relieved" in emo_low or "reassured" in emo_low or "friendly" in emo_low or "warm" in emo_low or "calm" in emo_low:
                emo_loc = "chaleureux, naturel, souriant et rassurant"
            else:
                emo_loc = "expressif, chaleureux, dynamique et naturel"

            if is_dialogue_speaker:
                if "person_one" in style_low or "partner" in style_low:
                    style_loc = "interlocuteur parisien naturel, spontané et expressif dans une vraie conversation"
                else:
                    style_loc = "ami parisien natif, chaleureux, fluide et authentique"
            else:
                style_loc = "présentateur parisien charismatique, dynamique, chaleureux et captivant"
            return emo_loc, style_loc

        if lang_norm == "spanish":
            if "game-show" in emo_low or "trivia" in emo_low or "countdown" in emo_low or "celebratory" in emo_low:
                if "countdown" in emo_low or "suspense" in emo_low:
                    emo_loc = "suspenso emocionante y anticipación de concurso"
                elif "triumphant" in emo_low or "reveal" in emo_low:
                    emo_loc = "revelación triunfante, alegre y entusiasta"
                else:
                    emo_loc = "presentador de concurso vibrante, carismático y lleno de entusiasmo"
            elif "frustrated" in emo_low or "exasperated" in emo_low or "panicked" in emo_low or "anxious" in emo_low:
                emo_loc = "expresivo, sorprendido y muy reactivo"
            elif "surprise" in emo_low or "baffled" in emo_low or "incredulous" in emo_low or "confusion" in emo_low or "confundido" in emo_low:
                emo_loc = "sorprendido, curioso y expresivo con total naturalidad"
            elif "delighted" in emo_low or "fascinated" in emo_low:
                emo_loc = "fascinado, entusiasmado y gratamente sorprendido"
            elif "dramatic" in emo_low or "intriguing" in emo_low or "mysterious" in emo_low:
                emo_loc = "intrigante, cautivador y lleno de energía"
            elif "relieved" in emo_low or "reassured" in emo_low or "friendly" in emo_low or "warm" in emo_low or "calm" in emo_low or "amused" in emo_low:
                emo_loc = "cálido, cercano, simpático y natural"
            else:
                emo_loc = "expresivo, cálido, dinámico y totalmente natural"

            if is_dialogue_speaker:
                if "person_one" in style_low or "partner" in style_low:
                    style_loc = "interlocutor hispanohablante nativo, espontáneo, expresivo y cercano"
                else:
                    style_loc = "hablante nativo cercano, seguro, natural y fluido"
            else:
                style_loc = "narrador hispanohablante carismático, dinámico, cálido y cautivador"
            return emo_loc, style_loc

        if lang_norm == "italian":
            if "game-show" in emo_low or "trivia" in emo_low or "countdown" in emo_low or "celebratory" in emo_low:
                if "countdown" in emo_low or "suspense" in emo_low:
                    emo_loc = "suspense avvincente e ritmo incalzante da quiz televisivo"
                elif "triumphant" in emo_low or "reveal" in emo_low:
                    emo_loc = "rivelazione trionfante, solare ed entusiasta"
                else:
                    emo_loc = "conduttore brillante, solare, travolgente e pieno di entusiasmo"
            elif "frustrated" in emo_low or "exasperated" in emo_low or "panicked" in emo_low or "anxious" in emo_low or "ansioso" in emo_low:
                emo_loc = "espressivo, vivace, spontaneo e molto partecipativo"
            elif "surprise" in emo_low or "baffled" in emo_low or "incredulous" in emo_low or "confusion" in emo_low or "bewildered" in emo_low:
                emo_loc = "sorpreso, incuriosito e spontaneo con naturale espressività italiana"
            elif "delighted" in emo_low or "fascinated" in emo_low:
                emo_loc = "affascinato, entusiasta e meravigliato con brio"
            elif "dramatic" in emo_low or "intriguing" in emo_low or "mysterious" in emo_low:
                emo_loc = "coinvolgente, magnetico, brillante e ricco di energia"
            elif "relieved" in emo_low or "reassured" in emo_low or "friendly" in emo_low or "warm" in emo_low or "ottimista" in emo_low:
                emo_loc = "solare, caloroso, sorridente e incoraggiante"
            else:
                emo_loc = "brillante, solare, espressivo e ricco di vitalità naturale"

            if is_dialogue_speaker:
                if "person_one" in style_low or "partner" in style_low:
                    style_loc = "interlocutore madrelingua italiano spontaneo, vivace, espressivo e naturale"
                else:
                    style_loc = "amico madrelingua italiano caloroso, brillante, sicuro e autentico"
            else:
                style_loc = "narratore madrelingua italiano carismatico, solare, dinamico e coinvolgente"
            return emo_loc, style_loc

        return emotion, style

    @staticmethod
    def _build_localized_instruct(
        lang_norm: str,
        gender: str,
        context: str,
        emotion: str,
        energy: str,
        style: str,
        is_dialogue_speaker: bool,
    ) -> Optional[str]:
        """Builds a localized target-language instruct prompt for Romance languages when enabled."""
        if lang_norm not in LOCALIZED_INSTRUCT_TEMPLATES:
            return None
        g_low = gender.strip().lower()
        gender_es = "hombre" if g_low == "male" else "mujer"
        gender_fr = "homme" if g_low == "male" else "femme"
        gender_it = "uomo" if g_low == "male" else "donna"

        e_low = (energy or "high").strip().lower()
        energy_es = "muy alta" if "very" in e_low else ("media" if "med" in e_low else "alta")
        energy_fr = "très haute" if "very" in e_low else ("moyenne" if "med" in e_low else "haute")
        energy_it = "molto alta" if "very" in e_low else ("media" if "med" in e_low else "alta")

        emo_loc, style_loc = ComfyClient._localize_emotion_and_style(
            lang_norm=lang_norm,
            emotion=emotion,
            style=style,
            is_dialogue_speaker=is_dialogue_speaker,
        )

        ctx_low = (context or "").lower()
        emo_low = (emotion or "").lower()
        is_quiz_prompt = any(
            kw in ctx_low or kw in emo_low
            for kw in ("game", "quiz", "trivia", "countdown", "game-show")
        )
        if is_quiz_prompt:
            pace_es = "Ritmo ágil, claro y vibrante de presentador de concurso"
            pace_fr = "Débit vif, clair et rythmé d'animateur de jeu télévisé"
            pace_it = "Ritmo vivace, brillante e coinvolgente da conduttore di quiz"
        else:
            pace_es = "Ritmo pausado, claro y bien articulado, ligeramente más lento que el habla cotidiana para que los estudiantes comprendan cada palabra"
            pace_fr = "Débit posé, clair et bien articulé, légèrement ralenti par rapport au débit natif rapide pour que les apprenants saisissent chaque mot"
            pace_it = "Ritmo posato, chiaro e ben scandito, leggermente più lento del parlato quotidiano per chi studia la lingua"

        tpl_group = LOCALIZED_INSTRUCT_TEMPLATES[lang_norm]
        tpl = tpl_group["dialogue"] if is_dialogue_speaker else tpl_group["narrator"]
        return tpl.format(
            gender_es=gender_es,
            gender_fr=gender_fr,
            gender_it=gender_it,
            energy_es=energy_es,
            energy_fr=energy_fr,
            energy_it=energy_it,
            emotion=emo_loc,
            style=style_loc,
            pace_es=pace_es,
            pace_fr=pace_fr,
            pace_it=pace_it,
        )

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
        seed: int = None,
        use_icl: Optional[bool] = None,
        ref_text: Optional[str] = None,
        localize_instruct: Optional[bool] = None,
        sampling_overrides: Optional[Dict[str, Any]] = None,
        accent_hint: Optional[str] = None,
        delivery_direction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Clones the template and updates inputs for the specific segment."""
        # Deep copy the template
        wf = json.loads(json.dumps(self.workflow_template))

        lang_norm = str(language or "english").split("|")[0].strip().lower()
        if "french" in lang_norm or "français" in lang_norm or lang_norm == "fr":
            lang_norm = "french"
        elif "spanish" in lang_norm or "español" in lang_norm or lang_norm == "es":
            lang_norm = "spanish"
        elif "italian" in lang_norm or "italiano" in lang_norm or lang_norm == "it":
            lang_norm = "italian"
        else:
            lang_norm = "english"

        if use_icl is None or localize_instruct is None:
            try:
                import config
                if use_icl is None:
                    use_icl = bool(getattr(config, "QWEN3_USE_ICL", False)) and (
                        lang_norm != "english"
                        or "kokoro_golden" in str(ref_audio_name).lower()
                        or self._has_manifest_ref_text(ref_audio_name)
                    )
                if localize_instruct is None:
                    localize_instruct = bool(getattr(config, "QWEN3_LOCALIZE_INSTRUCT", False)) and lang_norm != "english"
            except Exception:
                use_icl = False if use_icl is None else use_icl
                localize_instruct = False if localize_instruct is None else localize_instruct

        # 1. Update LoadAudio (Node 6)
        if "6" in wf and "inputs" in wf["6"]:
            wf["6"]["inputs"]["audio"] = ref_audio_name
            wf["6"]["inputs"]["audioUI"] = f"/api/view?filename={ref_audio_name}&type=input"

        # 2. Update SaveAudio (Node 8)
        if "8" in wf and "inputs" in wf["8"]:
            wf["8"]["inputs"]["filename_prefix"] = output_prefix

        # 2b. Configure Qwen3TTSVoiceClonePrompt (Node 35) for ICL vs x-vector cloning.
        # Unlink and remove Node 40 (SenseVoiceASR) whenever x_vector_only=True or ref_text is already known
        # so ComfyUI never loads or runs SenseVoiceSmall unnecessarily.
        if "35" in wf and "inputs" in wf["35"]:
            if use_icl:
                wf["35"]["inputs"]["x_vector_only"] = False
                resolved_ref_text = ref_text if ref_text is not None else self._get_ref_transcript(ref_audio_name, language=lang_norm)
                if resolved_ref_text:
                    wf["35"]["inputs"]["ref_text"] = resolved_ref_text
                    wf.pop("40", None)
            else:
                wf["35"]["inputs"]["x_vector_only"] = True
                wf["35"]["inputs"]["ref_text"] = ""
                wf.pop("40", None)

        # 3. Update Qwen3TTSVoiceClone (Node 39)
        if "39" in wf and "inputs" in wf["39"]:
            node_inputs = wf["39"]["inputs"]
            node_inputs["target_text"] = target_text
            node_inputs["target_language"] = lang_norm.capitalize()
            if seed is not None:
                node_inputs["seed"] = seed
            else:
                node_inputs["seed"] = random.randint(1, 10**15)

            # Generation parameters tuned for lively pace, zero robotic artifacts, and stable speaker timbre
            is_dialogue_speaker = "dialogue" in context.lower() or ("character" in context.lower() and "narrator" not in context.lower())

            if is_dialogue_speaker:
                node_inputs["temperature"] = 0.76
                node_inputs["top_p"] = 0.90
                node_inputs["top_k"] = 50
                node_inputs["subtalker_temperature"] = 0.78
                node_inputs["repetition_penalty"] = 1.05
            else:
                node_inputs["temperature"] = 0.84
                node_inputs["top_p"] = 0.92
                node_inputs["top_k"] = 50
                node_inputs["subtalker_temperature"] = 0.88
                node_inputs["repetition_penalty"] = 1.03

            if sampling_overrides and isinstance(sampling_overrides, dict):
                for param in ("temperature", "top_p", "top_k", "subtalker_temperature", "repetition_penalty"):
                    if param in sampling_overrides and sampling_overrides[param] is not None:
                        node_inputs[param] = sampling_overrides[param]

            spoken_only = re.sub(r"\[pause:\d+(?:\.\d+)?\]", " ", target_text)
            words_count = max(1, len(spoken_only.split()))
            node_inputs["max_new_tokens"] = max(128, min(2048, words_count * 18))

            localized = (
                self._build_localized_instruct(
                    lang_norm=lang_norm,
                    gender=gender,
                    context=context,
                    emotion=emotion,
                    energy=energy,
                    style=style,
                    is_dialogue_speaker=is_dialogue_speaker,
                )
                if localize_instruct
                else None
            )

            accent_clause = ""
            if accent_hint:
                lang_prof = get_language_voice_profile(lang_norm)
                hint_str = lang_prof.accent_instruct_hints.get(accent_hint, "")
                if hint_str:
                    accent_clause = f" {hint_str}"

            if delivery_direction:
                node_inputs["instruct"] = f"{delivery_direction}{accent_clause}".strip()
            elif localized:
                node_inputs["instruct"] = f"{localized}{accent_clause}".strip()
            elif is_dialogue_speaker:
                role_clause = f"as {context}" if context else "as a character"
                node_inputs["instruct"] = (
                    f"A consistent {gender.lower()} native speaker character with a stable vocal timbre and clear, learner-friendly conversational pacing in {language}. "
                    f"Speak {role_clause} with vibrant vocal energy and authentic theatrical acting. "
                    f"Acting tone: {emotion}. Energy level: {energy.upper()}. "
                    f"Delivery: {style}. Unhurried, articulate tempo that language learners can easily follow, expressive human inflection, and engaging reactive dialogue.{accent_clause}"
                )
            else:
                personality_clause = f" Persona: {context}." if context else ""
                node_inputs["instruct"] = (
                    f"A charismatic {gender.lower()} storyteller delivering an exciting YouTube Shorts presentation in {language}.{personality_clause} "
                    f"Tone: {emotion}. "
                    f"Energy level: {energy.upper()}. "
                    f"Delivery: {style}. Clear, unhurried learner-friendly tempo with high vocal enthusiasm, expressive emotional inflection, captivating cadence, and warm human flow. "
                    f"Avoid any rushed, sleepy, monotone, or robotic announcer enunciation.{accent_clause}"
                )

        return wf

    def queue_prompt(self, workflow: Dict[str, Any]) -> str:
        """Sends the workflow to the ComfyUI API to queue execution.
        Returns the prompt ID.
        """
        url = f"{self.api_url}/prompt"
        payload = {"prompt": workflow}

        response = self._http_post(url, json=payload, timeout=180)
        response.raise_for_status()

        data = response.json()
        if "prompt_id" not in data:
            raise KeyError(f"Failed to queue prompt, server returned: {data}")

        return data["prompt_id"]

    def get_history(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves history for the specific prompt execution."""
        url = f"{self.api_url}/history/{prompt_id}"
        try:
            response = self._http_get(url, timeout=3 if self.check_cancelled is not None else 30)
            response.raise_for_status()
            data = response.json()
            if prompt_id in data:
                return data[prompt_id]
        except Exception:
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
            self._check_job_cancelled()
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

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        response = self._http_get(url, params=params, stream=True, timeout=60)
        response.raise_for_status()

        with dest_path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    def _save_completed_voice(self, history: Dict[str, Any], dest_path: Path) -> None:
        outputs = history.get("outputs", {})

        save_node_id = "8"
        if save_node_id not in outputs:
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

        print(f"Downloading generated audio: {filename}")
        self.download_file(filename, subfolder, file_type, dest_path)

        if self.comfy_output_dir:
            source_file = self.comfy_output_dir / subfolder / filename
            if source_file.exists():
                for _attempt in range(2):
                    try:
                        source_file.unlink()
                        break
                    except PermissionError:
                        time.sleep(0.08)
                    except Exception:
                        break


    def generate_voice_candidates(
        self, takes: list[tuple[Path, Dict[str, Any]]], **workflow_inputs: Any,
    ) -> None:
        """Queue one known candidate ahead on ComfyUI's single execution lane."""
        pending: deque[tuple[str, Path]] = deque()
        vram_guard = self.pool.vram_guard("VOICE_GENERATION") if self.pool else contextlib.nullcontext()
        with vram_guard:
            try:
                for index, (path, inputs) in enumerate(takes):
                    self._check_job_cancelled()
                    prompt_id = self.queue_prompt(self._prepare_workflow(**workflow_inputs, **inputs))
                    pending.append((prompt_id, path))
                    _safe_print(f"Queued voice take {index + 1}/{len(takes)} (ID: {prompt_id}).")
                    if len(pending) == 2:
                        self._collect_voice_candidate(pending)
                if pending:
                    self._collect_voice_candidate(pending)
            finally:
                self.cancel_prompts([prompt_id for prompt_id, _ in pending])

    def _collect_voice_candidate(self, pending: deque[tuple[str, Path]]) -> None:
        prompt_id, path = pending[0]
        history = self.poll_for_completion(prompt_id)
        pending.popleft()
        self._check_job_cancelled()
        self._save_completed_voice(history, path)

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
        use_icl: Optional[bool] = None,
        ref_text: Optional[str] = None,
        localize_instruct: Optional[bool] = None,
        sampling_overrides: Optional[Dict[str, Any]] = None,
        accent_hint: Optional[str] = None,
        delivery_direction: Optional[str] = None,
    ) -> Path:
        """Executes the voice cloning pipeline for a single segment with auto-retry and watchdog.
        Returns the path to the downloaded audio file.
        """
        self._check_job_cancelled()
        if self.check_cancelled is None:
            self.ensure_clean_slate()

        vram_guard = self.pool.vram_guard("VOICE_GENERATION") if self.pool else contextlib.nullcontext()
        with vram_guard:
            return self._execute_voice_generation_loop(
                ref_audio_name=ref_audio_name,
                target_text=target_text,
                language=language,
                gender=gender,
                context=context,
                emotion=emotion,
                energy=energy,
                style=style,
                output_prefix=output_prefix,
                dest_path=dest_path,
                seed=seed,
                max_retries=max_retries,
                stall_timeout=stall_timeout,
                use_icl=use_icl,
                ref_text=ref_text,
                localize_instruct=localize_instruct,
                sampling_overrides=sampling_overrides,
                accent_hint=accent_hint,
                delivery_direction=delivery_direction,
            )

    def _execute_voice_generation_loop(
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
        use_icl: Optional[bool] = None,
        ref_text: Optional[str] = None,
        localize_instruct: Optional[bool] = None,
        sampling_overrides: Optional[Dict[str, Any]] = None,
        accent_hint: Optional[str] = None,
        delivery_direction: Optional[str] = None,
    ) -> Path:
        last_error = None
        for attempt in range(1, max_retries + 1):
            self._check_job_cancelled()
            prompt_id = None
            try:
                prep_kwargs: Dict[str, Any] = dict(
                    ref_audio_name=ref_audio_name,
                    target_text=target_text,
                    language=language,
                    gender=gender,
                    context=context,
                    emotion=emotion,
                    energy=energy,
                    style=style,
                    output_prefix=output_prefix,
                    seed=seed,
                    use_icl=use_icl,
                    ref_text=ref_text,
                    localize_instruct=localize_instruct,
                )
                if sampling_overrides is not None:
                    prep_kwargs["sampling_overrides"] = sampling_overrides
                if accent_hint is not None:
                    prep_kwargs["accent_hint"] = accent_hint
                if delivery_direction is not None:
                    prep_kwargs["delivery_direction"] = delivery_direction
                wf = self._prepare_workflow(**prep_kwargs)

                print(f"Queuing voice generation (attempt {attempt}/{max_retries}): '{target_text[:35]}...'")
                prompt_id = self.queue_prompt(wf)

                print(f"Executing workflow (ID: {prompt_id}). Polling for results...")
                history = self.poll_for_completion(prompt_id, timeout_seconds=stall_timeout)

                prompt_id = None
                self._check_job_cancelled()
                self._save_completed_voice(history, dest_path)
                time.sleep(0.3)
                return dest_path

            except InterruptedError:
                if prompt_id is not None and self.check_cancelled is not None:
                    self.cancel_prompts([prompt_id])
                raise
            except TimeoutError as te:
                last_error = te
                _safe_print(
                    f"[Watchdog] ComfyUI voice generation stalled (> {stall_timeout}s). Auto-interrupting...",
                )
                if self.check_cancelled is None:
                    self.interrupt()
                elif prompt_id is not None:
                    self.cancel_prompts([prompt_id])
                if attempt < max_retries:
                    time.sleep(1.5)
                if attempt < max_retries:
                    _safe_print(
                        f"[Watchdog] Retrying voice generation (attempt {attempt + 1}/{max_retries})... "
                        f"\"Go ahead, don't stop!\"",
                    )
            except requests.exceptions.Timeout as req_te:
                last_error = req_te
                if prompt_id is not None and self.check_cancelled is not None:
                    self.cancel_prompts([prompt_id])
                if attempt < max_retries:
                    _safe_print(
                        f"[Watchdog] ComfyUI HTTP request timed out ({req_te}); waiting for server to respond before retrying (attempt {attempt + 1}/{max_retries})...",
                    )
                    time.sleep(5.0)
                    if self.check_cancelled is None:
                        self.ensure_clean_slate()
            except Exception as exc:
                last_error = exc
                if prompt_id is not None and self.check_cancelled is not None:
                    self.cancel_prompts([prompt_id])
                if attempt < max_retries:
                    _safe_print(
                        f"[Watchdog] ComfyUI voice generation error ({exc}). Retrying (attempt {attempt + 1}/{max_retries})...",
                    )
                    if self.check_cancelled is None:
                        self.interrupt()
                    time.sleep(2.5)

        raise last_error or RuntimeError("Failed to generate voice segment after retries.")
