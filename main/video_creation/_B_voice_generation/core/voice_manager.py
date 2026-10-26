import csv
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import config

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
            if len(parts) == 2:
                lang, gend = parts
                self.voice_pools[(lang, gend)] = []
                try:
                    with open(csv_file, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            self.voice_pools[(lang, gend)].append(row["FILE_PATH"])
                except Exception as e:
                    print(f"Error reading {csv_file}: {e}")

    def get_available_voices(self, language: str, gender: str) -> List[Path]:
        """Returns all existing reference voice WAV paths available for the given language and gender."""
        lang = self.normalize_language(language)
        gend = gender.strip().lower()
        voices = []
        seen = set()

        # 1. From NARRATOR_VOICES in config
        for rel in getattr(config, "NARRATOR_VOICES", {}).get((lang, gend), []):
            p = self.open_swara_dir / rel
            if p.exists() and p.name not in seen:
                voices.append(p)
                seen.add(p.name)

        # 2. From voice pools CSVs
        for rel in self.voice_pools.get((lang, gend), []):
            p = self.open_swara_dir / rel
            if p.exists() and p.name not in seen:
                voices.append(p)
                seen.add(p.name)

        # 3. From open-swara filesystem directly
        target_dir = self.open_swara_dir / lang / gend
        if target_dir.exists():
            for p in sorted(target_dir.glob("*.wav")):
                if p.name not in seen:
                    voices.append(p)
                    seen.add(p.name)

        return sorted(voices, key=lambda x: x.name)

    def assign_voices_for_script(
        self,
        unique_speakers: list,
        language: str,
        manual_genders: dict = None,
        manual_voice_paths: dict = None
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
            # Random gender for single narrator
            gender = manual_genders.get(speaker) or random.choice(["male", "female"])
            abs_path = manual_voice_paths.get(speaker)
            
            if not abs_path or not Path(abs_path).exists():
                # Use random narrator voice from the NARRATOR_VOICES list if available
                preferred_pool = getattr(config, "NARRATOR_VOICES", {}).get((lang, gender), [])
                valid_preferred = [
                    self.open_swara_dir / p for p in preferred_pool
                    if (self.open_swara_dir / p).exists()
                ]
                if valid_preferred:
                    abs_path = random.choice(valid_preferred)
                else:
                    pool = self.voice_pools.get((lang, gender), [])
                    valid_pool = [
                        self.open_swara_dir / p for p in pool
                        if (self.open_swara_dir / p).exists()
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
                    # This guarantees Person 1 and Person 2 will have different voices (Male/Female)
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
                    
                    # Exclude ALL narrator voices and previously used paths from the character's pool
                    narrator_voices = getattr(config, "NARRATOR_VOICES", {}).get((lang, gender), [])
                    available_pool = [
                        p for p in pool
                        if p not in used_paths and p not in narrator_voices and (self.open_swara_dir / p).exists()
                    ]
                    
                    if available_pool:
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
                    
                    # Prioritize NARRATOR_VOICES explicitly reserved in config
                    preferred_pool = getattr(config, "NARRATOR_VOICES", {}).get((lang, narrator_gender), [])
                    available_preferred = [
                        p for p in preferred_pool
                        if p not in used_paths and (self.open_swara_dir / p).exists()
                    ]
                    
                    if available_preferred:
                        rel_path = random.choice(available_preferred)
                        abs_path = self.open_swara_dir / rel_path
                        used_paths.add(rel_path)
                    else:
                        # Fallback if no NARRATOR_VOICES available
                        available_pool = [
                            p for p in pool
                            if p not in used_paths and (self.open_swara_dir / p).exists()
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
                
            # If absolute path was missing or invalid, resolve via fallback and persist it
            fallback_voice = self.find_reference_voice(lang, gender)
            self.current_assignments[speaker] = (gender, fallback_voice)
            return gender, fallback_voice, seed
        
        # Complete fallback for unknown speaker: resolve and permanently store
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
        
        # Check explicit mapping in config
        if name_clean in config.SPEAKER_GENDER_MAP:
            return config.SPEAKER_GENDER_MAP[name_clean]
            
        # Try checking parts of the name (e.g. "agent (stressé)" -> "agent")
        for key, gender in config.SPEAKER_GENDER_MAP.items():
            if key in name_clean or name_clean in key:
                return gender

        # Heuristic rules for romance languages (Spanish/French)
        # Ends with a -> female
        if name_clean.endswith("a") or name_clean.endswith("á"):
            return "female"
        # Ends with o or er or or -> male
        if name_clean.endswith("o") or name_clean.endswith("ó") or name_clean.endswith("or") or name_clean.endswith("er"):
            return "male"
            
        # If it's a generic tag like person_one, return unknown to trigger randomization
        if "person" in name_clean or "speaker" in name_clean:
            return "unknown"
            
        # Default fallback
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
                if (self.open_swara_dir / p).exists() and (self.open_swara_dir / p) not in self.fallback_used_paths
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
                if (self.open_swara_dir / p).exists() and (self.open_swara_dir / p) not in self.fallback_used_paths
            ]
            if available_csv:
                chosen = random.choice(available_csv)
                self.fallback_used_paths.add(chosen)
                return chosen

        # 3. Try scanning the target directory for any .wav files
        target_dir = self.open_swara_dir / lang / gend
        if target_dir.exists():
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
            wav_files = list(lang_dir.rglob("*.wav"))
            if wav_files:
                available = [f for f in wav_files if f not in self.fallback_used_paths]
                if not available:
                    available = wav_files
                # Find file matching gender if possible
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
        
        # Copy file if it doesn't exist, or has different size
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
