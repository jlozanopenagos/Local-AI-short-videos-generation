"""
build_all_ready_prompts.py
Adapts and standardizes all newly added raw expressions across English, French, Spanish, and Italian.
Generates fully-populated CSVs for EXPRESSION, GAME, and ROLEPLAY.
"""

import csv
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

def clean_text(t: str) -> str:
    if not t:
        return ""
    # Normalize whitespace and quotes
    t = re.sub(r"\s+", " ", t).strip()
    return t

def main():
    print("Starting adaptation of all language expression queues...")

    # ==========================================
    # 1. ENGLISH (EE114 - EE119)
    # ==========================================
    eng_dir = BASE_DIR / "input" / "csv" / "english" / "expressions_list"
    eng_expr_path = eng_dir / "ENGLISH_READY_PROMPTS_EXPRESSION.csv"
    eng_game_path = eng_dir / "ENGLISH_READY_PROMPTS_GAME.csv"
    eng_role_path = eng_dir / "ENGLISH_READY_PROMPTS_ROLEPLAY.csv"

    english_new_data = [
        {
            "id_num": 114,
            "expr": "The ball is in your court",
            "subj": "Popular English Idioms",
            "ctx": "Explaining that it is someone else's turn to make a decision or take action (I've given you all the information; now the ball is in your court.)",
            "angle": "How a simple tennis phrase became a universal metaphor for responsibility in decision-making",
            "lex": "Daily Tasks & Decision-making",
            "emo": "Relief & Curiosity",
            "scenario": "In an office conference room: PERSON_ONE finishes laying out the project strategy and slides the file across the table to PERSON_TWO with a confident smile, saying: 'I've given you all the key data—now the ball is in your court!'"
        },
        {
            "id_num": 115,
            "expr": "Call it a day",
            "subj": "Popular English Idioms",
            "ctx": "To stop working or stop doing an activity because you are tired, have done enough, or it is getting late (I'm exhausted, let's call it a day.)",
            "angle": "Why saying you are 'calling' a day means officially wrapping up hard work",
            "lex": "Work & Daily Routine",
            "emo": "Relief & Relaxation",
            "scenario": "Late evening in a quiet office: PERSON_ONE rubs their tired eyes while staring at a spreadsheet. PERSON_TWO gently closes their laptop, smiles warmly, and says: 'We've made great progress tonight, let's call it a day!'"
        },
        {
            "id_num": 116,
            "expr": "Hit the sack",
            "subj": "Popular English Idioms",
            "ctx": "To go to bed or go to sleep, used informally when you are exhausted (It's almost midnight. I'm going to hit the sack.)",
            "angle": "How old straw-filled mattress sacks created one of English's most common sleep idioms",
            "lex": "Daily Routine & Sleep",
            "emo": "Relief & Curiosity",
            "scenario": "In a cozy living room late at night: PERSON_ONE yawns loudly and checks their phone. PERSON_TWO hands them a glass of water with a smile, and PERSON_ONE says: 'I can barely keep my eyes open, I'm going to hit the sack!'"
        },
        {
            "id_num": 117,
            "expr": "It ain't over till the fat lady sings",
            "subj": "Popular English Idioms",
            "ctx": "Things are not over yet; keep fighting and trying until the very end, especially in sports or tough challenges (We are down by one point, but it ain't over till the fat lady sings.)",
            "angle": "How grand opera finales inspired the ultimate underdog sports comeback phrase",
            "lex": "Sports & Determination",
            "emo": "Hope & Motivation",
            "scenario": "On the sidelines of a championship basketball game: PERSON_ONE sits with their head in their hands with thirty seconds left. PERSON_TWO claps their hands firmly, locks eyes with them, and rallies the team: 'Don't quit now—it ain't over till the fat lady sings!'"
        },
        {
            "id_num": 118,
            "expr": "It's not rocket science",
            "subj": "Popular English Idioms",
            "ctx": "Explaining that a task is simple, straightforward, and easy to understand (Don't worry, learning this software isn't rocket science.)",
            "angle": "Why rocket science became the global benchmark for comparing effortless tasks",
            "lex": "Learning & Problem Solving",
            "emo": "Encouragement & Relief",
            "scenario": "In a computer lab: PERSON_ONE looks completely overwhelmed trying to configure a new app. PERSON_TWO steps in with a reassuring grin, clicks two buttons, and says: 'Take a breath, you've got this—it's not rocket science!'"
        },
        {
            "id_num": 119,
            "expr": "The elephant in the room",
            "subj": "Popular English Idioms",
            "ctx": "An obvious major problem or controversial issue that everyone is aware of but avoids discussing (The elephant in the room is that our budget is almost gone.)",
            "angle": "How an impossible-to-miss giant animal became the symbol for awkward unspoken truths",
            "lex": "Communication & Conflicts",
            "emo": "Curiosity & Tension",
            "scenario": "In a tense board meeting: Everyone sits in awkward silence glancing at each other. PERSON_ONE clears their throat, looks directly at PERSON_TWO, and says: 'Are we going to keep dancing around the topic, or should we finally address the elephant in the room?'"
        }
    ]

    # Update ENGLISH_READY_PROMPTS_EXPRESSION.csv
    with open(eng_expr_path, encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
    eng_expr_header = reader[0]
    eng_expr_rows = [r for r in reader[1:] if any(r) and int(r[0].replace("EE", "")) < 114]
    
    for item in english_new_data:
        cid = f"EE{item['id_num']:02d}"
        eng_expr_rows.append([
            cid, item["expr"], item["subj"], item["ctx"], item["angle"], item["lex"], item["emo"]
        ])

    with open(eng_expr_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(eng_expr_header)
        writer.writerows(eng_expr_rows)
    print(f"Updated {eng_expr_path.name}: {len(eng_expr_rows)} rows.")

    # Update ENGLISH_READY_PROMPTS_GAME.csv
    with open(eng_game_path, encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
    eng_game_header = reader[0]
    eng_game_rows = [r for r in reader[1:] if any(r) and int(r[0].replace("EG", "")) < 114]
    for item in english_new_data:
        cid = f"EG{item['id_num']:02d}"
        eng_game_rows.append([cid, item["expr"], item["subj"], item["lex"]])

    with open(eng_game_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(eng_game_header)
        writer.writerows(eng_game_rows)
    print(f"Updated {eng_game_path.name}: {len(eng_game_rows)} rows.")

    # Update ENGLISH_READY_PROMPTS_ROLEPLAY.csv
    with open(eng_role_path, encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
    eng_role_header = reader[0]
    eng_role_rows = [r for r in reader[1:] if any(r) and int(r[0].replace("ER", "")) < 114]
    for item in english_new_data:
        cid = f"ER{item['id_num']:02d}"
        eng_role_rows.append([cid, item["scenario"], item["subj"], item["lex"], item["emo"]])

    with open(eng_role_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(eng_role_header)
        writer.writerows(eng_role_rows)
    print(f"Updated {eng_role_path.name}: {len(eng_role_rows)} rows.")

    return 0

if __name__ == "__main__":
    main()
