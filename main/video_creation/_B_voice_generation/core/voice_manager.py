import csv
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import config

# Known problematic / accented Open-Swara reference clips excluded for native target-language cloning
EXCLUDED_NON_ENGLISH_PATTERNS = (
    "_english_",
    "french_male_open_swara_001.wav",
    "french_male_open_swara_019.wav",
)


class VoiceManager:
    def __init__(self, open_swara_dir: Path, comfy_input_dir: Path):
        self.open_swara_dir = open_swara_dir
        self.comfy_input_dir = comfy_input_dir
        self.data_dir = Path(__file__).parent.parent / "data"
        self.voice_pools = {}
        self.current_assignments = {}
        self.speaker_seeds = {}
        self.fallback_used_paths = set()
        
        # Ensure ComfyUI input folder exists
        self.comfy_input_dir.mkdir(parents=True, exist_ok=True)
        self._load_csv_pools()

    @staticmethod
    def _is_acceptable_ref(path: Path, lang: str) -> bool:
        """Filters out cross-accented or corrupted reference clips for non-English scripts."""
        if lang == "english":
            return True
        name_low = path.name.lower()
        return not any(pat in name_low for pat in EXCLUDED_NON_ENGLISH_PATTERNS)

    @classmethod
    def resolve_engine_for_speaker(
        cls,
        language: str,
        gender: str = "female",
        speaker: str = "narrator",
        is_dialogue: bool = False,
        cli_engine_override: Optional[str] = None,
        kokoro_available: bool = True,
        is_multi_speaker_script: bool = False,
    ) -> Tuple[str, Optional[str]]:
        """Determines whether a speaker segment should be synthesized with 'kokoro' or 'qwen3',
        and returns `(engine_name, kokoro_voice_id_or_None)`.

        Engine modes (`VOICE_ENGINE_BY_LANGUAGE` or `--engine`):
          - 'qwen3'  : Always use Qwen3-TTS via ComfyUI.
          - 'kokoro' : Always use Kokoro-82M (using `ff_siwis_male` pitch-shifted if French male,
                       and `*_narrator` timbre variant for the 3rd speaker in Roleplays).
          - 'hybrid' : Use Kokoro-82M when a native gender voice exists (`ef_dora`, `em_alex`,
                       `ff_siwis`, `if_sara`, `im_nicola`); for French male dialogue (since Kokoro
                       v1.0 has no native male French voice), fall back to Qwen3-TTS ICL cloning.
        """
        lang = cls.normalize_language(language)
        gend = "male" if str(gender).strip().lower() == "male" else "female"

        mode = (cli_engine_override or "").strip().lower()
        if not mode or mode == "auto":
            engine_map = getattr(config, "VOICE_ENGINE_BY_LANGUAGE", {})
            mode = engine_map.get(lang, "qwen3").strip().lower()

        if mode == "qwen3" or not kokoro_available:
            return "qwen3", None

        kokoro_voices = getattr(config, "KOKORO_VOICES", {})
        voice_list = kokoro_voices.get((lang, gend), [])
        chosen_voice = voice_list[0] if voice_list else None

        if mode == "hybrid":
            # In French, Kokoro v1.0 only has a native female voice (ff_siwis).
            # Narrator uses ff_siwis_narrator, while a male dialogue speaker falls back to Qwen3-TTS ICL.
            if lang == "french" and gend == "male":
                if is_dialogue:
                    return "qwen3", None
                # Single-narrator French script: prefer native female voice ff_siwis_narrator
                return "kokoro", "ff_siwis_narrator"

        if not chosen_voice:
            from video_creation._B_voice_generation.core.kokoro_engine import KokoroEngine
            chosen_voice = KokoroEngine.resolve_voice(lang, gender=gend)

        # Always give the Narrator a dedicated `_narrator` energetic host persona
        # (brighter style blend + lively storytelling pitch/cadence) so the Narrator
        # never sounds sleepy or identical to a dialogue character (`PERSON_ONE` / `PERSON_TWO`).
        if not is_dialogue and "narrator" in speaker.lower() and chosen_voice:
            if not chosen_voice.endswith("_narrator"):
                chosen_voice = f"{chosen_voice}_narrator"

        return "kokoro", chosen_voice

    @staticmethod
    def normalize_language(language: str) -> str:
        """Normalizes any language string, compound metadata label, or shortcode to canonical lowercase:
        'english', 'french', 'spanish', or 'italian'.
        """
        if not language:
            return "english"
        raw = str(language).strip().lower()

        # Check first token before pipe, and full string
        first_token = raw.split("|")[0].strip()
        for token in [first_token, raw]:
            if any(k in token for k in ["french", "français", "francais"]) or token == "fr":
                return "french"
            if any(k in token for k in ["spanish", "español", "espanol"]) or token in ["es", "sp"]:
                return "spanish"
            if any(k in token for k in ["italian", "italiano"]) or token == "it":
                return "italian"
            if "english" in token or token == "en":
                return "english"
        return "english"

    def _load_csv_pools(self):
        if not self.data_dir.exists():
            return
        for csv_file in self.data_dir.glob("*.csv"):
            name = csv_file.stem
            parts = name.split("_")
            if len(parts) == 2 and parts[0] in ("english", "french", "spanish", "italian"):
                lang, gend = parts
                self.voice_pools[(lang, gend)] = []
                try:
                    with open(csv_file, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if "FILE_PATH" in row:
                                self.voice_pools[(lang, gend)].append(row["FILE_PATH"])
                except Exception as e:
                    print(f"Error reading {csv_file}: {e}")

        # Also discover and index any newly generated filesystem reference audio in open_swara
        if self.open_swara_dir and self.open_swara_dir.exists():
            for lang in ("english", "french", "spanish", "italian"):
                for gend in ("male", "female"):
                    key = (lang, gend)
                    if key not in self.voice_pools:
                        self.voice_pools[key] = []
                    target_dir = self.open_swara_dir / lang / gend
                    if target_dir.exists():
                        existing_set = set(self.voice_pools[key])
                        for p in sorted(target_dir.glob("*.wav")):
                            rel = f"{lang}/{gend}/{p.name}"
                            if rel not in existing_set and p.name not in existing_set:
                                self.voice_pools[key].append(rel)
                                existing_set.add(rel)

    def get_available_voices(self, language: str, gender: str) -> List[Path]:
        """Returns all existing reference voice WAV paths available for the given language and gender."""
        lang = self.normalize_language(language)
        gend = gender.strip().lower()
        voices = []
        seen = set()

        # 1. From NARRATOR_VOICES in config
        for rel in getattr(config, "NARRATOR_VOICES", {}).get((lang, gend), []):
            p = self.open_swara_dir / rel
            if p.exists() and p.name not in seen and self._is_acceptable_ref(p, lang):
                voices.append(p)
                seen.add(p.name)

        # 2. From voice pools CSVs
        for rel in self.voice_pools.get((lang, gend), []):
            p = self.open_swara_dir / rel
            if p.exists() and p.name not in seen and self._is_acceptable_ref(p, lang):
                voices.append(p)
                seen.add(p.name)

        # 3. From open-swara filesystem directly
        target_dir = self.open_swara_dir / lang / gend
        if target_dir.exists():
            for p in sorted(target_dir.glob("*.wav")):
                if p.name not in seen and self._is_acceptable_ref(p, lang):
                    voices.append(p)
                    seen.add(p.name)

        return sorted(voices, key=lambda x: x.name)

    @staticmethod
    def _rank_voice_by_tier(path_str: str, gender: str, role: str, video_type: Optional[str] = None) -> int:
        """Assigns priority ranking (lower is better) based on video type and acoustic pitch tier."""
        name = Path(path_str).stem.lower()
        vtype = (video_type or "expression").lower()
        is_narrator = "narrator" in role.lower()
        gend = "male" if gender == "male" else "female"

        # Tier preferences (priority from highest=0 to lowest=10)
        if vtype == "roleplay":
            if is_narrator:
                if gend == "male":
                    tiers = ["baritone", "narrator", "bass", "tenor", "char1", "char2"]
                else:
                    tiers = ["mezzo", "narrator", "alto", "char2", "char1", "soprano"]
            else:
                if gend == "male":
                    tiers = ["bass", "char2", "baritone", "char1", "tenor", "narrator"]
                else:
                    tiers = ["alto", "char1", "mezzo", "char2", "narrator", "soprano"]
        elif vtype in ("expression", "explanation"):
            if gend == "male":
                tiers = ["baritone", "narrator", "char1", "bass", "tenor", "char2"]
            else:
                tiers = ["alto", "mezzo", "narrator", "char1", "char2", "soprano"]
        elif vtype == "fun_facts":
            if gend == "male":
                tiers = ["tenor", "baritone", "narrator", "char1", "bass", "char2"]
            else:
                tiers = ["mezzo", "soprano", "narrator", "char2", "alto", "char1"]
        elif vtype == "game":
            if gend == "male":
                tiers = ["baritone", "narrator", "char1", "tenor", "bass", "char2"]
            else:
                tiers = ["mezzo", "narrator", "char2", "alto", "char1", "soprano"]
        else:
            tiers = ["narrator", "baritone", "mezzo", "alto", "char1", "char2"]

        for idx, t in enumerate(tiers):
            if f"_{t}" in name:
                return idx
        return len(tiers) + 1

    def assign_voices_for_script(
        self,
        unique_speakers: list,
        language: str,
        manual_genders: dict = None,
        manual_voice_paths: dict = None,
        video_type: Optional[str] = None
    ):
        self.current_assignments.clear()
        self.speaker_seeds.clear()
        self.fallback_used_paths.clear()
        lang = self.normalize_language(language)
        if manual_genders is None:
            manual_genders = {}
        if manual_voice_paths is None:
            manual_voice_paths = {}

        if len(unique_speakers) == 1:
            speaker = list(unique_speakers)[0]
            # Random gender for single narrator (for French in hybrid/kokoro mode, prefer female where native ff_siwis exists)
            engine_mode = getattr(config, "VOICE_ENGINE_BY_LANGUAGE", {}).get(lang, "qwen3")
            if speaker in manual_genders:
                gender = manual_genders[speaker]
            elif lang == "french" and engine_mode in ("kokoro", "hybrid"):
                gender = "female"
            else:
                gender = random.choice(["male", "female"])
            abs_path = manual_voice_paths.get(speaker)
            
            if not abs_path or not Path(abs_path).exists():
                preferred_pool = getattr(config, "NARRATOR_VOICES", {}).get((lang, gender), [])
                valid_preferred = [
                    self.open_swara_dir / p for p in preferred_pool
                    if (self.open_swara_dir / p).exists() and self._is_acceptable_ref(self.open_swara_dir / p, lang)
                ]
                if valid_preferred:
                    golden = [p for p in valid_preferred if "kokoro_golden" in p.name]
                    if golden:
                        golden.sort(key=lambda p: self._rank_voice_by_tier(str(p), gender, "narrator", video_type))
                        abs_path = golden[0]
                    else:
                        abs_path = random.choice(valid_preferred)
                else:
                    pool = self.voice_pools.get((lang, gender), [])
                    valid_pool = [
                        self.open_swara_dir / p for p in pool
                        if (self.open_swara_dir / p).exists() and self._is_acceptable_ref(self.open_swara_dir / p, lang)
                    ]
                    if valid_pool:
                        abs_path = random.choice(valid_pool)
                    else:
                        abs_path = self.find_reference_voice(lang, gender)
            else:
                abs_path = Path(abs_path)
                    
            if abs_path:
                self.fallback_used_paths.add(abs_path)
            self.current_assignments[speaker] = (gender, abs_path)
            self.speaker_seeds[speaker] = random.randint(1, 10**14)
        else:
            # Separate narrator from characters
            narrator_key = None
            characters = []
            for speaker in unique_speakers:
                if "narrator" in speaker.strip().lower():
                    narrator_key = speaker
                else:
                    characters.append(speaker)
                    
            # Assign genders to characters
            char_genders = {}
            for speaker in characters:
                if speaker in manual_genders:
                    gender = manual_genders[speaker]
                else:
                    gender = self.resolve_speaker_gender(speaker)
                    
                    # Force opposite gender if this gender is already taken by another character
                    if gender != "unknown" and gender in char_genders.values():
                        gender = "female" if gender == "male" else "male"
                        
                    if gender == "unknown":
                        m_count = list(char_genders.values()).count("male")
                        f_count = list(char_genders.values()).count("female")
                        if m_count > f_count:
                            gender = "female"
                        elif f_count > m_count:
                            gender = "male"
                        else:
                            gender = random.choice(["male", "female"])
                        
                char_genders[speaker] = gender
                
            # Assign gender to narrator
            narrator_gender = None
            if narrator_key:
                if narrator_key in manual_genders:
                    narrator_gender = manual_genders[narrator_key]
                else:
                    genders_present = list(char_genders.values())
                    if len(genders_present) >= 2 and all(g == genders_present[0] for g in genders_present):
                        narrator_gender = "female" if genders_present[0] == "male" else "male"
                    elif characters and char_genders.get(characters[0]) in ("male", "female"):
                        narrator_gender = "male" if char_genders[characters[0]] == "female" else "female"
                    elif lang == "french":
                        narrator_gender = "female"
                    else:
                        narrator_gender = random.choice(["male", "female"])
                    
            # Now, assign unique voice paths
            used_paths = set()
            
            # Assign characters first
            for speaker in characters:
                gender = char_genders[speaker]
                abs_path = manual_voice_paths.get(speaker)

                if not abs_path or not Path(abs_path).exists():
                    pool = self.voice_pools.get((lang, gender), [])
                    
                    narrator_voices = getattr(config, "NARRATOR_VOICES", {}).get((lang, gender), [])
                    available_pool = [
                        p for p in pool
                        if p not in used_paths
                        and p not in narrator_voices
                        and (self.open_swara_dir / p).exists()
                        and self._is_acceptable_ref(self.open_swara_dir / p, lang)
                    ]
                    golden_char_pool = [p for p in available_pool if "kokoro_golden" in p]
                    
                    if golden_char_pool:
                        golden_char_pool.sort(key=lambda p: self._rank_voice_by_tier(p, gender, speaker, video_type))
                        rel_path = golden_char_pool[0]
                        abs_path = self.open_swara_dir / rel_path
                        used_paths.add(rel_path)
                    elif available_pool:
                        rel_path = random.choice(available_pool)
                        abs_path = self.open_swara_dir / rel_path
                        used_paths.add(rel_path)
                    else:
                        abs_path = self.find_reference_voice(lang, gender)
                else:
                    abs_path = Path(abs_path)

                if abs_path:
                    self.fallback_used_paths.add(abs_path)
                self.current_assignments[speaker] = (gender, abs_path)
                self.speaker_seeds[speaker] = random.randint(1, 10**14)
                
            # Assign narrator
            if narrator_key:
                abs_path = manual_voice_paths.get(narrator_key)

                if not abs_path or not Path(abs_path).exists():
                    pool = self.voice_pools.get((lang, narrator_gender), [])
                    
                    preferred_pool = getattr(config, "NARRATOR_VOICES", {}).get((lang, narrator_gender), [])
                    available_preferred = [
                        p for p in preferred_pool
                        if p not in used_paths
                        and (self.open_swara_dir / p).exists()
                        and self._is_acceptable_ref(self.open_swara_dir / p, lang)
                    ]
                    golden_narrator_pool = [p for p in available_preferred if "kokoro_golden" in p]
                    
                    if golden_narrator_pool:
                        golden_narrator_pool.sort(key=lambda p: self._rank_voice_by_tier(p, narrator_gender, "narrator", video_type))
                        rel_path = golden_narrator_pool[0]
                        abs_path = self.open_swara_dir / rel_path
                        used_paths.add(rel_path)
                    elif available_preferred:
                        rel_path = random.choice(available_preferred)
                        abs_path = self.open_swara_dir / rel_path
                        used_paths.add(rel_path)
                    else:
                        available_pool = [
                            p for p in pool
                            if p not in used_paths
                            and (self.open_swara_dir / p).exists()
                            and self._is_acceptable_ref(self.open_swara_dir / p, lang)
                        ]
                        if available_pool:
                            rel_path = random.choice(available_pool)
                            abs_path = self.open_swara_dir / rel_path
                            used_paths.add(rel_path)
                        else:
                            abs_path = self.find_reference_voice(lang, narrator_gender)
                else:
                    abs_path = Path(abs_path)

                if abs_path:
                    self.fallback_used_paths.add(abs_path)
                self.current_assignments[narrator_key] = (narrator_gender, abs_path)
                self.speaker_seeds[narrator_key] = random.randint(1, 10**14)

    def get_speaker_voice(self, speaker: str, language: str) -> Tuple[str, Path, int]:
        """Returns the assigned (gender, absolute_voice_path, seed) for the speaker.
        Falls back to default find_reference_voice if something is missing, and persists it.
        """
        lang = self.normalize_language(language)

        if speaker in self.current_assignments:
            gender, abs_path = self.current_assignments[speaker]
            if speaker not in self.speaker_seeds:
                self.speaker_seeds[speaker] = random.randint(1, 10**14)
            seed = self.speaker_seeds[speaker]
            
            if abs_path and abs_path.exists():
                return gender, abs_path, seed
                
            fallback_voice = self.find_reference_voice(lang, gender)
            self.current_assignments[speaker] = (gender, fallback_voice)
            return gender, fallback_voice, seed
        
        gender = self.resolve_speaker_gender(speaker)
        if gender == "unknown":
            gender = random.choice(["male", "female"])
        fallback_voice = self.find_reference_voice(lang, gender)
        seed = random.randint(1, 10**14)
        self.current_assignments[speaker] = (gender, fallback_voice)
        self.speaker_seeds[speaker] = seed
        return gender, fallback_voice, seed

    def resolve_speaker_gender(self, speaker_name: str) -> str:
        """Determines the gender (male/female) of a speaker name using heuristics."""
        name_clean = speaker_name.strip().lower()
        
        if name_clean in config.SPEAKER_GENDER_MAP:
            return config.SPEAKER_GENDER_MAP[name_clean]
            
        for key, gender in config.SPEAKER_GENDER_MAP.items():
            if key in name_clean or name_clean in key:
                return gender

        if name_clean.endswith("a") or name_clean.endswith("á"):
            return "female"
        if name_clean.endswith("o") or name_clean.endswith("ó") or name_clean.endswith("or") or name_clean.endswith("er"):
            return "male"
            
        if "person" in name_clean or "speaker" in name_clean:
            return "unknown"
            
        return "female"

    def find_reference_voice(self, language: str, gender: str) -> Path:
        """Finds a reference voice file from Open-Swara voices folder.
        Never falls back to English unless the target language is English or absolutely no target voices exist.
        """
        lang = self.normalize_language(language)
        gend = gender.strip().lower()
        
        # 1. Try preferred voice from config (pick a random narrator voice)
        preferred_pool = getattr(config, "NARRATOR_VOICES", {}).get((lang, gend), [])
        if preferred_pool:
            available_pref = [
                self.open_swara_dir / p
                for p in preferred_pool
                if (self.open_swara_dir / p).exists()
                and (self.open_swara_dir / p) not in self.fallback_used_paths
                and self._is_acceptable_ref(self.open_swara_dir / p, lang)
            ]
            if available_pref:
                chosen = random.choice(available_pref)
                self.fallback_used_paths.add(chosen)
                return chosen

        # 2. Try voice pools from data/*.csv
        csv_pool = self.voice_pools.get((lang, gend), [])
        if csv_pool:
            available_csv = [
                self.open_swara_dir / p
                for p in csv_pool
                if (self.open_swara_dir / p).exists()
                and (self.open_swara_dir / p) not in self.fallback_used_paths
                and self._is_acceptable_ref(self.open_swara_dir / p, lang)
            ]
            if available_csv:
                chosen = random.choice(available_csv)
                self.fallback_used_paths.add(chosen)
                return chosen

        # 3. Try scanning the target directory for any acceptable .wav files
        target_dir = self.open_swara_dir / lang / gend
        if target_dir.exists():
            wav_files = [f for f in target_dir.glob("*.wav") if self._is_acceptable_ref(f, lang)]
            if not wav_files:
                wav_files = list(target_dir.glob("*.wav"))
            if wav_files:
                available = [f for f in wav_files if f not in self.fallback_used_paths]
                if not available:
                    available = wav_files
                chosen = random.choice(available)
                self.fallback_used_paths.add(chosen)
                return chosen
                
        # 4. Fallback: Check general target language directory
        lang_dir = self.open_swara_dir / lang
        if lang_dir.exists():
            wav_files = [f for f in lang_dir.rglob("*.wav") if self._is_acceptable_ref(f, lang)]
            if not wav_files:
                wav_files = list(lang_dir.rglob("*.wav"))
            if wav_files:
                available = [f for f in wav_files if f not in self.fallback_used_paths]
                if not available:
                    available = wav_files
                matching = [f for f in available if f"_{gend}_" in f.name.lower() or gend in f.parent.name.lower()]
                chosen = random.choice(matching if matching else available)
                self.fallback_used_paths.add(chosen)
                return chosen

        # 5. Last Resort: Warn and fallback to English only if target language has no voices
        if lang != "english":
            print(f"[Warning] No reference voice found for language '{lang}' ({gend}) in '{self.open_swara_dir}'. Falling back to English voice.")

        english_fallback_dir = self.open_swara_dir / "english" / gend
        if english_fallback_dir.exists():
            wav_files = list(english_fallback_dir.glob("*.wav"))
            if wav_files:
                available = [f for f in wav_files if f not in self.fallback_used_paths]
                if not available:
                    available = wav_files
                chosen = random.choice(available)
                self.fallback_used_paths.add(chosen)
                return chosen
                
        # 6. Entire Open-Swara voices folder
        if self.open_swara_dir.exists():
            all_wavs = list(self.open_swara_dir.rglob("*.wav"))
            if all_wavs:
                return all_wavs[0]

        # 7. Check ComfyUI input folder
        comfy_input_wavs = list(self.comfy_input_dir.glob("*.wav"))
        if comfy_input_wavs:
            return comfy_input_wavs[0]

        raise FileNotFoundError(
            f"No voice reference WAV files found in Open-Swara dir '{self.open_swara_dir}' "
            f"or ComfyUI input dir '{self.comfy_input_dir}'."
        )

    def prepare_voice_in_comfy(self, voice_file_path: Path) -> str:
        """Copies the reference voice file to ComfyUI input folder if needed.
        Returns the filename (basename) to be used in ComfyUI's LoadAudio node.
        """
        import shutil
        dest_file_path = self.comfy_input_dir / voice_file_path.name
        
        if not dest_file_path.exists() or dest_file_path.stat().st_size != voice_file_path.stat().st_size:
            print(f"Copying reference voice '{voice_file_path.name}' to ComfyUI input folder...")
            shutil.copy2(voice_file_path, dest_file_path)
            
        return voice_file_path.name

    def cleanup_comfy_input(self) -> None:
        """Cleans up the reference voice files copied into the ComfyUI input directory during this run."""
        if not self.comfy_input_dir.exists():
            return
            
        paths_to_delete = set()
        for speaker, assignments in self.current_assignments.items():
            _, abs_path = assignments
            if abs_path:
                paths_to_delete.add(abs_path.name)
                
        for abs_path in self.fallback_used_paths:
            if abs_path:
                paths_to_delete.add(abs_path.name)
                
        for filename in paths_to_delete:
            dest_file_path = self.comfy_input_dir / filename
            try:
                if dest_file_path.exists():
                    print(f"Cleaning up reference voice '{filename}' from ComfyUI input folder...")
                    dest_file_path.unlink()
            except Exception as e:
                print(f"Warning: Could not delete input reference file {dest_file_path}: {e}")
