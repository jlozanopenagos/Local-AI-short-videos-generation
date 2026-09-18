import csv
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

def extract_parenthetical(text: str) -> Tuple[str, Optional[str]]:
    """Extracts a parenthetical emotion/state from text.
    Example: 'Agent (Stressé)' -> ('Agent', 'Stressé')
    """
    match = re.search(r"\(([^)]+)\)", text)
    if match:
        emotion = match.group(1).strip()
        cleaned_text = re.sub(r"\([^)]+\)", "", text).strip()
        return cleaned_text, emotion
    return text, None

def normalize_spoken_dialogue(text: str) -> str:
    """Cleans up clunky text artifacts and awkward written interjections that degrade TTS fluency."""
    # Remove literal laugh spellings that TTS pronounces mechanically like "ha... ha"
    text = re.sub(r"\b(ha(ha)+|he(he)+|ho(ho)+)[!.,?]*\s*", "", text, flags=re.IGNORECASE)
    # Remove sound effect markers like *sigh*, *gasp*, *laughs*
    text = re.sub(r"\*[^*]+\*", "", text)
    # Smooth leading "Oh no, " or "Oh, no, " -> "No, "
    text = re.sub(r"^\s*oh\s*,?\s*no\s*,\s*", "No, ", text, flags=re.IGNORECASE)
    # Remove standalone awkward sighs like "Ugh, " or "Ugh! "
    text = re.sub(r"^\s*ugh[!.,?]*\s*", "", text, flags=re.IGNORECASE)
    # Normalize unicode smart quotes and dashes to standard ASCII
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", ", ")
    # Format multiple choice quiz options (e.g., 'hurt B) Good' -> 'hurt. B: Good', 'A) ' -> 'A: ') for clear articulate TTS pacing
    text = re.sub(r"(?<![.!?,:;\n])\s+([A-D]\))", r". \1", text)
    text = re.sub(r"\b([A-D])\)\s*", r"\1: ", text)
    # Replace mid-sentence multiple dots/ellipses that cause awkward 1-second gaps: "Break a... what?" -> "Break a, what?"
    text = re.sub(r"\.{2,}", ", ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

def clean_text_and_extract_emotions(text: str) -> Tuple[str, Optional[str]]:
    """Strips parentheticals, double asterisks, normalizes conversational speech, and collapses whitespace.
    Returns (cleaned_text, extracted_emotion).
    """
    emotions = []
    def replace_parenthetical(match):
        emotions.append(match.group(1).strip())
        return ""
    
    # Extract parentheticals
    cleaned = re.sub(r"\(([^)]+)\)", replace_parenthetical, text)
    
    # Strip double asterisks
    cleaned = cleaned.replace("**", "")
    
    # Normalize dialogue for natural spoken delivery
    cleaned = normalize_spoken_dialogue(cleaned)
    
    emotion_str = ", ".join(emotions) if emotions else None
    return cleaned, emotion_str

def parse_sections(script_text: str) -> Dict[str, str]:
    """Parses a multi-line script string into structured sections based on headers."""
    sections = {}
    
    # Try to parse as JSON first
    json_text = script_text.strip()
    if json_text.startswith("```json"):
        json_text = json_text[7:]
    if json_text.startswith("```"):
        json_text = json_text[3:]
    if json_text.endswith("```"):
        json_text = json_text[:-3]
    json_text = json_text.strip()
    
    if json_text.startswith("{") and json_text.endswith("}"):
        try:
            data = json.loads(json_text)
            for k, v in data.items():
                sections[k.strip().lower()] = str(v).strip()
            return sections
        except json.JSONDecodeError:
            pass
            
    current_section = None
    current_lines = []
    
    # Standardize headers (English, Spanish, French, Italian)
    header_mapping = {
        "title": "title", "título": "title", "titre": "title", "titolo": "title",
        "hook": "hook", "gancho": "hook", "gancio": "hook",
        "context": "context", "contexto": "context", "contexte": "context", "contesto": "context",
        "content": "content", "contenido": "content", "contenu": "content", "contenuto": "content",
        "pattern interrupt": "interrupt", "interruptor": "interrupt", "interrupteur": "interrupt", "interruzione": "interrupt",
        "example": "example", "exemple": "example", "ejemplo": "example", "esempio": "example",
        "payoff": "payoff", "resultado": "payoff", "résultat": "payoff", "risultato": "payoff",
        "cta": "cta"
    }
    
    for line in script_text.splitlines():
        line_str = line.strip()
        
        # Check if line is a header
        # Strip stars and lowercase to identify
        stripped_header = line_str.replace("*", "").replace("/", "").strip().lower()
        
        found_header = None
        matched_kw = None
        if stripped_header:
            # Check if any known header keyword is in this line
            for kw, section_name in header_mapping.items():
                if stripped_header == kw or (len(stripped_header) < 50 and (stripped_header.startswith(kw) or stripped_header.endswith(kw))):
                    found_header = section_name
                    matched_kw = kw
                    break
        
        if found_header:
            if current_section and current_lines:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = found_header
            current_lines = []
            # Check if there is inline text after the header keyword / colon
            cleaned_line = re.sub(r"^[\s\*\#\/\-_]*", "", line_str)
            if ":" in cleaned_line:
                after_colon = cleaned_line.split(":", 1)[1].strip()
                if after_colon:
                    current_lines.append(after_colon)
        else:
            if current_section:
                current_lines.append(line)
                
    if current_section and current_lines:
        sections[current_section] = "\n".join(current_lines).strip()
        
    return sections

def parse_content_dialogue(content_text: str) -> List[Dict[str, str]]:
    """Parses dialogue turns from the CONTENT section.
    Returns a list of segments: [{'speaker': str, 'text': str, 'emotion': str}]
    """
    segments = []
    current_speaker = None
    current_emotion = None
    pending_text = []

    def flush_segment():
        nonlocal pending_text, current_speaker, current_emotion
        if pending_text and current_speaker:
            text_str = " ".join(pending_text).strip()
            cleaned_text, inline_emotions = clean_text_and_extract_emotions(text_str)
            if cleaned_text:
                spk = "Narrator" if current_speaker.strip().lower() == "narrator" else current_speaker
                segments.append({
                    "speaker": spk,
                    "text": cleaned_text,
                    "emotion": inline_emotions or current_emotion or "neutral"
                })
            pending_text = []

    lines = content_text.splitlines()
    for line in lines:
        line_str = line.strip()
        if not line_str:
            flush_segment()
            continue
            
        # 1. Skip pure stage directions like "(Pattern Interrupt)" or "(Sourire)" on their own line
        if line_str.startswith("(") and line_str.endswith(")"):
            direction = line_str[1:-1].strip()
            current_emotion = direction
            continue

        # 2. Match Type B: **Speaker (Emotion) :** text
        match_b = re.match(r"^\*\*([^*:]+)\s*:\*\*\s*(.*)$", line_str)
        if match_b:
            flush_segment()
            speaker_part = match_b.group(1).strip()
            text_part = match_b.group(2).strip()
            speaker_name, speaker_emotion = extract_parenthetical(speaker_part)
            current_speaker = speaker_name
            current_emotion = speaker_emotion
            if text_part:
                pending_text.append(text_part)
            continue

        # 3. Match Type A: [Speaker] text
        match_a = re.match(r"^\[([^\]]+)\]\s*(.*)$", line_str)
        if match_a:
            flush_segment()
            speaker_part = match_a.group(1).strip()
            text_part = match_a.group(2).strip()
            speaker_name, speaker_emotion = extract_parenthetical(speaker_part)
            current_speaker = speaker_name
            current_emotion = speaker_emotion
            if text_part:
                pending_text.append(text_part)
            continue

        # 4. Match Type C: Speaker: text
        match_c = re.match(r"^([A-ZÀ-ÿa-zA-Z\s_]+)(?:\s*\(([^)]+)\))?\s*:\s*(.*)$", line_str)
        if match_c:
            speaker_part = match_c.group(1).strip()
            if speaker_part.lower() not in ["subject", "http", "https", "note", "tip", "hi", "best"]:
                flush_segment()
                current_speaker = speaker_part
                current_emotion = match_c.group(2) or None
                text_part = match_c.group(3).strip()
                if text_part:
                    pending_text.append(text_part)
                continue

        # 5. Match Type D: Speaker name on its own line (uppercase, length <= 20)
        match_d = re.match(r"^([A-ZÁÉÍÓÚÑa-zA-Z\s\-_]+)(?:\s*\(([^)]+)\))?$", line_str)
        if match_d:
            speaker_part = match_d.group(1).strip()
            if speaker_part.isupper() and 1 < len(speaker_part) <= 20:
                flush_segment()
                current_speaker = speaker_part
                current_emotion = match_d.group(2) or None
                continue

        # 6. Fallback: treat as continuation of current speaker
        if current_speaker:
            pending_text.append(line_str)
        else:
            # If no speaker is set yet, default to Narrator
            current_speaker = "Narrator"
            pending_text.append(line_str)

    flush_segment()
    return segments

def extract_language_from_label(label: str) -> str:
    """Helper to detect language from metadata label.
    Example: 'Spanish | Work | Negotiating Salary' -> 'spanish'
    """
    label_lower = label.lower()
    if "spanish" in label_lower or "español" in label_lower:
        return "spanish"
    elif "french" in label_lower or "français" in label_lower:
        return "french"
    elif "italian" in label_lower or "italiano" in label_lower:
        return "italian"
    return "english"  # default

def get_script_segments(script_id: str, script_text: str, label: str) -> List[Dict[str, str]]:
    """Splits a full script into a chronological sequence of segments to be voiced."""
    language = extract_language_from_label(label)
    sections = parse_sections(script_text)
    
    all_segments = []
    
    # Determine the order of sections to vocalize
    known_order = [
        "hook", "context", "setup", "mystery", "clues", "challenge", "pressure", "thinking_time",
        "content", "dialogue", "dialogue_part_1", "dialogue_part_2", "dialogue_part_3", "dialogue_part_4",
        "comparison_a", "comparison_b", "fact_1", "fact_2", "fact_3", "item_3", "item_2", "item_1",
        "discovery", "core_learning", "example", "reveal", "answer", "surprise", "emphasis", "explanation", "interrupt",
        "payoff", "takeaway", "cta"
    ]
    existing_keys = list(sections.keys())
    
    if any(k in known_order for k in existing_keys):
        section_order = [k for k in known_order if k in existing_keys]
        for k in existing_keys:
            if k not in known_order and k != "title":
                section_order.append(k)
    else:
        section_order = [k for k in existing_keys if k != "title"]
    
    segment_idx = 1
    for sec in section_order:
        sec_text = sections.get(sec)
        if not sec_text:
            continue
            
        if sec == "content" or "dialogue" in sec:
            # CONTENT/DIALOGUE has dialogue segments
            dialogue_turns = parse_content_dialogue(sec_text)
            for turn in dialogue_turns:
                all_segments.append({
                    "id": script_id,
                    "index": segment_idx,
                    "section": sec,
                    "speaker": turn["speaker"],
                    "text": turn["text"],
                    "emotion": turn["emotion"],
                    "language": language,
                    "is_dialogue": True
                })
                segment_idx += 1
        else:
            # Other sections are spoken by Narrator
            # Split into paragraphs to maintain pacing
            paragraphs = [p.strip() for p in sec_text.split("\n\n") if p.strip()]
            for p in paragraphs:
                cleaned_p, p_emotion = clean_text_and_extract_emotions(p)
                if cleaned_p:
                    all_segments.append({
                        "id": script_id,
                        "index": segment_idx,
                        "section": sec,
                        "speaker": "Narrator",
                        "text": cleaned_p,
                        "emotion": p_emotion or "neutral",
                        "language": language,
                        "is_dialogue": False
                    })
                    segment_idx += 1
                    
    return all_segments

def load_pending_scripts(prompts_path: Path, metadata_path: Path, completed_ids: set) -> List[Dict]:
    """Loads scripts and their metadata for all IDs not in completed_ids.
    Robustly handles CSVs whether they contain header rows or not.
    """
    if not prompts_path.exists() or not metadata_path.exists():
        return []
        
    # Read metadata
    metadata_map = {}
    with metadata_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        first_row = next(reader, None)
        if first_row:
            # Check if the CSV has a header row
            has_headers = len(first_row) >= 8 and first_row[0].strip().upper() == "ID" and first_row[6].strip().upper() == "LABEL"
            
            # Helper to process row
            def process_meta_row(r):
                if len(r) >= 7:
                    # Column 0: ID, Column 6: LABEL
                    metadata_map[r[0].strip()] = {"ID": r[0].strip(), "LABEL": r[6].strip()}
            
            if not has_headers:
                process_meta_row(first_row)
            
            for row in reader:
                process_meta_row(row)

    # Read prompts
    pending = []
    with prompts_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        first_row = next(reader, None)
        if first_row:
            # Check if the CSV has a header row
            has_headers = len(first_row) >= 2 and first_row[0].strip().upper() == "ID" and first_row[1].strip().upper() == "SCRIPT"
            
            rows_to_process = []
            
            def process_prompt_row(r):
                if len(r) >= 2:
                    rows_to_process.append((r[0].strip(), r[1].strip()))
            
            if not has_headers:
                process_prompt_row(first_row)
                
            for row in reader:
                process_prompt_row(row)
                
            for script_id, script_text in rows_to_process:
                if not script_id or script_id in completed_ids:
                    continue
                    
                meta = metadata_map.get(script_id, {})
                label = meta.get("LABEL", "english")
                
                pending.append({
                    "id": script_id,
                    "script": script_text,
                    "label": label
                })
            
    return pending
