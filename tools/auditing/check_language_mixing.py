#!/usr/bin/env python3
"""
tools/check_language_mixing.py

Audits all 1,184 script state JSON files across all languages (English, French, Spanish, Italian)
and all video types (Expression, Game, Roleplay, Fun Facts) to detect:
1. Language contamination / mixing (e.g. English phrases in Italian/French/Spanish scripts,
   French phrases in Italian scripts, Italian phrases in French scripts).
2. Root causes of why the LLM leaked another language.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any

def main():
    base_dir = Path(__file__).resolve().parents[2]
    state_dir = base_dir / "state"

    # Distinct vocabularies & distinctive marker phrases per language
    FRENCH_MARKERS = [
        "pourquoi", "toujours", "maintenant", "beaucoup", "aussi", "avec",
        "trois secondes", "la bonne réponse", "arrêtez de deviner", "seuls les vrais natifs",
        "c'est parti", "à vous de jouer", "lequel est", "quelle est"
    ]

    ITALIAN_MARKERS = [
        "perché", "sempre", "adesso", "anche", "grazie", "allora", "quindi",
        "tre secondi", "la risposta esatta", "la risposta corretta", "tocca a te",
        "indovina", "solo i veri madrelingua", "qual è", "quale di queste"
    ]

    SPANISH_MARKERS = [
        "por qué", "siempre", "ahora", "también", "gracias", "entonces",
        "tres segundos", "la respuesta correcta", "la respuesta es", "adivina",
        "solo los verdaderos nativos", "cuál es", "cuál de estas"
    ]

    ENGLISH_MARKERS = [
        "the correct answer is", "three seconds on the clock", "stop guessing",
        "can you pass this", "only 10% get this right", "what does", "which one sounds natural",
        "actually mean", "speed is key", "choose a, b", "choose a, b, c", "quiz time",
        "test yourself", "drop your own example", "best one gets pinned"
    ]

    state_files = sorted(state_dir.rglob("script_*.json"))
    print(f"Auditing {len(state_files)} state JSON files for cross-language contamination...\n")

    contaminations: List[Dict[str, Any]] = []

    for sf in state_files:
        try:
            with sf.open("r", encoding="utf-8", errors="replace") as fp:
                data = json.load(fp)
        except Exception as e:
            continue

        sid = data.get("id", sf.stem.replace("script_", ""))
        
        # Resolve language and video type from path
        parts = sf.relative_to(state_dir).parts
        if len(parts) >= 2:
            lang = parts[0].lower()
            vtype = parts[1].lower()
        else:
            lang = "english"
            vtype = "expression"

        script_obj = data.get("content_metadata", {}).get("script", {})
        if not isinstance(script_obj, dict):
            continue

        for section_name, section_text in script_obj.items():
            if not isinstance(section_text, str) or not section_text.strip():
                continue

            text_lower = section_text.lower()

            # 1. English contamination in French, Spanish, Italian
            if lang in ("french", "spanish", "italian"):
                leaked_en = [m for m in ENGLISH_MARKERS if m in text_lower]
                if leaked_en:
                    contaminations.append({
                        "id": sid,
                        "language": lang,
                        "video_type": vtype,
                        "section": section_name,
                        "issue": f"English leak into {lang.capitalize()}",
                        "markers": leaked_en,
                        "text": section_text,
                        "path": sf
                    })

            # 2. French contamination in Italian or Spanish
            if lang in ("italian", "spanish"):
                # Filter out cognates or common words, check multi-word markers
                leaked_fr = [m for m in ["trois secondes", "la bonne réponse", "arrêtez de deviner", "seuls les vrais natifs", "c'est parti", "à vous de jouer"] if m in text_lower]
                if leaked_fr:
                    contaminations.append({
                        "id": sid,
                        "language": lang,
                        "video_type": vtype,
                        "section": section_name,
                        "issue": f"French leak into {lang.capitalize()}",
                        "markers": leaked_fr,
                        "text": section_text,
                        "path": sf
                    })

            # 3. Italian contamination in French or Spanish
            if lang in ("french", "spanish"):
                leaked_it = [m for m in ["tre secondi", "la risposta esatta", "la risposta corretta", "tocca a te", "solo i veri madrelingua"] if m in text_lower]
                if leaked_it:
                    contaminations.append({
                        "id": sid,
                        "language": lang,
                        "video_type": vtype,
                        "section": section_name,
                        "issue": f"Italian leak into {lang.capitalize()}",
                        "markers": leaked_it,
                        "text": section_text,
                        "path": sf
                    })

    # Summary
    print("=" * 80)
    print(f"CONTAMINATION AUDIT REPORT: Found {len(contaminations)} contaminated section(s)")
    print("=" * 80)

    # Group by script ID
    by_script: Dict[str, List[Dict[str, Any]]] = {}
    for c in contaminations:
        by_script.setdefault(c["id"], []).append(c)

    print(f"Total Affected Scripts: {len(by_script)} / {len(state_files)}\n")

    for sid, items in by_script.items():
        first = items[0]
        print(f"[{sid}] {first['language'].upper()}/{first['video_type'].upper()} ({first['path'].relative_to(base_dir)})")
        for item in items:
            print(f"  - Section '{item['section']}': {item['issue']}")
            print(f"    Detected Markers: {item['markers']}")
            print(f"    Text: \"{item['text'][:140]}...\"")
        print("-" * 80)

if __name__ == "__main__":
    main()
