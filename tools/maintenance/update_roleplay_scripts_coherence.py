"""
update_roleplay_scripts_coherence.py

Rebuilds the 10 English roleplay scripts (ER01 - ER10) to guarantee:
1. Strict 4-part dialogue structure (7 keys total: title, hook, DIALOGUE_PART_1..4, PAYOFF).
2. Strict turn causality (zero hallucinated quotes; target phrase explicitly uttered in Part 1).
3. Explicit uppercase word-stress / minimal-pair notation (REcord vs reCORD, PREsent vs preSENT, etc.).
4. Calibrated 60-80s runtime budget (strictly 145-180 words).
5. Scrapes updated state files to review CSV.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.auditing.scrapper_script import process_scripts

ROLEPLAYS_CATALOG = {
    "ER01": {
        "title": "Stage Fright Secrets",
        "hook": "Ever hear someone wish you harm right before the biggest moment of your life? Watch what happens backstage.",
        "DIALOGUE_PART_1": "PERSON_ONE (Nervous): My audition starts in five minutes, my hands are trembling and I'm sweating buckets!\nPERSON_TWO (Encouraging): Take a deep breath! You practiced all week, so walk out there and break a leg!",
        "DIALOGUE_PART_2": "PERSON_ONE (Shocked): Break a leg?! Are you seriously wishing me broken bones right before I sing?\nPERSON_TWO (Chuckling): It's an old theater superstition! Saying good luck brings bad vibes, so performers say break a leg instead.",
        "DIALOGUE_PART_3": "PERSON_ONE (Baffled): So wishing me broken bones actually means you want me to give a legendary performance?\nPERSON_TWO (Smirking): Exactly! You bend your knees taking bow after bow when the crowd goes wild.",
        "DIALOGUE_PART_4": "PERSON_ONE (Relieved): Okay, that makes me feel ten times better. My knees are ready for those bows!\nPERSON_TWO (Hilarious): Perfect! Now get out on that stage and smash it!",
        "PAYOFF": "When the spotlight turns on, real pros don't wish for luck; they own the room. Have you ever performed on stage? Drop your story in the comments!"
    },
    "ER02": {
        "title": "The Coding Crisis",
        "hook": "Ever panic over a massive problem only to watch someone solve it in seconds? Here is how natives describe it.",
        "DIALOGUE_PART_1": "PERSON_ONE (Panicked): This database algorithm has three hundred lines of errors and the deadline is midnight!\nPERSON_TWO (Relaxed): Hand me the keyboard. Don't stress, fixing this syntax bug is a piece of cake.",
        "DIALOGUE_PART_2": "PERSON_ONE (Baffled): A piece of cake?! I've been pulling my hair out for four hours and you're talking about pastry?\nPERSON_TWO (Chuckling): It's an idiom! When a task requires zero struggle and finishes effortlessly, we call it a piece of cake.",
        "DIALOGUE_PART_3": "PERSON_ONE (Curious): So whenever an assignment looks terrifying but ends up being super simple, it's cake?\nPERSON_TWO (Smirking): Exactly. Just like devouring a sweet slice of dessert with your afternoon coffee.",
        "DIALOGUE_PART_4": "PERSON_ONE (Relieved): Look at that, the code compiles with zero warnings! That truly was a piece of cake.\nPERSON_TWO (Laughing): Told you! Now let's celebrate with some actual dessert!",
        "PAYOFF": "Next time you face a tough challenge, attack it with confidence until it's simple. What was your easiest victory this year? Tell me below!"
    },
    "ER03": {
        "title": "The Studio Sound Check",
        "hook": "One tiny syllable shift completely transforms what you're saying in the studio. Hear how the rhythm changes everything.",
        "DIALOGUE_PART_1": "PERSON_ONE (Impatient): The microphones are set up, so did you listen to our new audio REcord?\nPERSON_TWO (Skeptical): Listen closely: you hold a vinyl REcord in your hands, but today we need to reCORD the vocals!",
        "DIALOGUE_PART_2": "PERSON_ONE (Baffled): Wait, did you just say the exact same word twice with two different voices?\nPERSON_TWO (Chuckling): Not the same word! A REcord with a heavy front punch is the noun, but to reCORD with a rising climb is the action.",
        "DIALOGUE_PART_3": "PERSON_ONE (Thoughtful): So front beat REcord is the physical album, and back beat reCORD is singing into the microphone?\nPERSON_TWO (Smirking): Exactly! The front punch holds the object, while the rising beat pushes the energy forward.",
        "DIALOGUE_PART_4": "PERSON_ONE (Excited): Got it! Step behind the glass and let's reCORD this hit track right now!\nPERSON_TWO (Grinning): Now that is music to my ears. Roll the tape!",
        "PAYOFF": "Master the rhythm and your English sounds instantly authentic. Hear the beat in your words! Drop your favorite song in the comments below!"
    },
    "ER04": {
        "title": "The Boardroom Present",
        "hook": "Are you giving a gift or giving a speech? Watch how shifting word stress saves this corporate meeting.",
        "DIALOGUE_PART_1": "PERSON_ONE (Nervous): The executive team just sat down, and my hands are trembling before I PREsent!\nPERSON_TWO (Smirking): Calm down! A PREsent is the gift in a box; today you are going to preSENT the annual report.",
        "DIALOGUE_PART_2": "PERSON_ONE (Baffled): Wait, so my stress was on the wrong syllable the entire morning?\nPERSON_TWO (Chuckling): Totally! Front punch PREsent is the noun, but back punch preSENT is the verb you need on stage.",
        "DIALOGUE_PART_3": "PERSON_ONE (Aha): So the front beat PREsent sits under the Christmas tree, and the rising beat preSENT delivers the pitch?\nPERSON_TWO (Encouraging): Spot on! Drop your voice on the front for the gift, climb on the back for the action.",
        "DIALOGUE_PART_4": "PERSON_ONE (Determined): Understood. The slide deck is our PREsent to the company, and I will preSENT it with swagger!\nPERSON_TWO (Laughing): That's the spirit! Now go command that boardroom!",
        "PAYOFF": "Clear pronunciation gives you instant authority in every professional setting. Speak with pride and own the room! Drop your best pitch below!"
    },
    "ER05": {
        "title": "The Blueprint Projection",
        "hook": "Ever confuse the work on your desk with the image on the wall? Here is the secret stress shift.",
        "DIALOGUE_PART_1": "PERSON_ONE (Frustrated): The client is walking through the door and we need to PROject our blueprints!\nPERSON_TWO (Deadpan): Hold on. The PROject is the folder in your hand; you want to proJECT the image onto the wall!",
        "DIALOGUE_PART_2": "PERSON_ONE (Shocked): Did you really just correct my pronunciation five seconds before the pitch begins?\nPERSON_TWO (Chuckling): Yes, because saying you will PROject sounds like you're throwing a binder at the client's head!",
        "DIALOGUE_PART_3": "PERSON_ONE (Baffled): So heavy front beat PROject is the binder, and rising back beat proJECT is throwing the light?\nPERSON_TWO (Smirking): Exactly! Front beat holds the assignment, back beat beams the visual onto the screen.",
        "DIALOGUE_PART_4": "PERSON_ONE (Relieved): Makes total sense. Flip the switch and let's proJECT this magnificent PROject!\nPERSON_TWO (Grinning): Perfect execution. Let's win this contract together!",
        "PAYOFF": "One syllable shift is the difference between a great presentation and a funny disaster. Speak like a leader! Drop your thoughts below!"
    },
    "ER06": {
        "title": "The Gate Permit Panic",
        "hook": "Airport stress turns simple English into comedy. Watch what happens when boarding gate confusion peaks.",
        "DIALOGUE_PART_1": "PERSON_ONE (Impatient): The gate agent said we need an official PERmit to board this international flight!\nPERSON_TWO (Deadpan): Listen to her words: she asked if the airline perMITTED rolling bags inside the cabin.",
        "DIALOGUE_PART_2": "PERSON_ONE (Baffled): Wait, so nobody is canceling our tickets? I thought she demanded a stamped government document!\nPERSON_TWO (Chuckling): No paper needed! You heard 'permit' and panicked before noticing she used it as a verb.",
        "DIALOGUE_PART_3": "PERSON_ONE (Relieved): So front beat PERmit is the piece of paper, and back beat perMIT is granting permission?\nPERSON_TWO (Smirking): Exactly. Heavy front beat holds the ticket, while the rising back beat gives the green light.",
        "DIALOGUE_PART_4": "PERSON_ONE (Grinning): Got it! No more heart attacks at international security gates.\nPERSON_TWO (Laughing): Great. Now grab your backpack before they perMIT this plane to take off without us!",
        "PAYOFF": "One misplaced rhythm and you're sweating at the departure terminal. Speak with clarity and travel with confidence! Tell me your airport story below!"
    },
    "ER07": {
        "title": "The Courtroom Object",
        "hook": "Is it a physical item or a heated courtroom challenge? Hear how stress flips the whole meaning.",
        "DIALOGUE_PART_1": "PERSON_ONE (Conspiratorial): Look at that strange mystery OBject on the evidence table; do you think the defense will obJECT?\nPERSON_TWO (Impressed): Listen to how naturally you just flipped the stress between those two words!",
        "DIALOGUE_PART_2": "PERSON_ONE (Curious): Did I really do that? I didn't even realize my voice changed pitch.\nPERSON_TWO (Chuckling): You dropped your voice heavily onto OBject for the item, then climbed up onto obJECT for the protest.",
        "DIALOGUE_PART_3": "PERSON_ONE (Thoughtful): So the physical OBject sits on the table, while the lawyer stands up to loudly obJECT?\nPERSON_TWO (Smirking): Spot on! Nouns take the heavy front punch, while verbs climb high on the second beat.",
        "DIALOGUE_PART_4": "PERSON_ONE (Determined): Nobody can obJECT to a rule that clear and simple!\nPERSON_TWO (Laughing): Sustained! Now let's examine this fascinating OBject together.",
        "PAYOFF": "When your ear catches the natural music of speech, speaking becomes effortless. Speak with certainty! Share your favorite courtroom drama line below!"
    },
    "ER08": {
        "title": "The Contract Crunch",
        "hook": "Signing a deal or feeling your muscles tighten? Watch how one word captures both sensations.",
        "DIALOGUE_PART_1": "PERSON_ONE (Tense): Before we sign this massive business CONtract, my neck muscles conTRACT from pure anxiety!\nPERSON_TWO (Smirking): Notice how your vocal cadence just separated the legal agreement from your physical tension?",
        "DIALOGUE_PART_2": "PERSON_ONE (Baffled): You're analyzing my stress patterns while our entire business future is on the line?\nPERSON_TWO (Chuckling): Always! Front punch CONtract is the document, but rising back beat conTRACT is your muscles squeezing.",
        "DIALOGUE_PART_3": "PERSON_ONE (Aha): So the paper CONtract rests on the desk, while cold weather causes metal pipes to conTRACT?\nPERSON_TWO (Encouraging): Exactly! Noun gets the front anchor, verb gets the energetic second syllable.",
        "DIALOGUE_PART_4": "PERSON_ONE (Relieved): My neck feels looser already. Hand me the pen and let's sign this historic CONtract!\nPERSON_TWO (Grinning): Perfect! Now let's celebrate a winning deal.",
        "PAYOFF": "Business English is all about precision and confidence under pressure. Own your vocabulary! Have you ever signed a big deal? Share below!"
    },
    "ER09": {
        "title": "The Salary Increase",
        "hook": "Are profits climbing, or are you getting a raise? Here is the secret stress shift behind the money.",
        "DIALOGUE_PART_1": "PERSON_ONE (Eager): Our company sales inCREASE every single week, so when do we get a salary INcrease?\nPERSON_TWO (Smirking): Hear that sharp rhythm flip you just delivered? That was textbook native English.",
        "DIALOGUE_PART_2": "PERSON_ONE (Curious): I was just asking for more money, but did the pronunciation actually change?\nPERSON_TWO (Chuckling): Totally! Front beat INcrease is the noun raise, but rising back beat inCREASE is the action of growing.",
        "DIALOGUE_PART_3": "PERSON_ONE (Thoughtful): So an INcrease lands in my bank account, while customer subscriptions inCREASE every month?\nPERSON_TWO (Encouraging): Exactly right! The front punch holds the paycheck, the back climb describes the growth.",
        "DIALOGUE_PART_4": "PERSON_ONE (Determined): Let's show the boss this chart and demand that well-deserved INcrease right now!\nPERSON_TWO (Laughing): Lead the way, my friend. Let's get that money!",
        "PAYOFF": "The right words spoken with the right rhythm make your case irresistible. Step up and ask for what you deserve! Drop your thoughts below!"
    },
    "ER10": {
        "title": "The Temperature Drop",
        "hook": "Catching a sudden discount or feeling the temperature plunge? Watch how this word shifts under pressure.",
        "DIALOGUE_PART_1": "PERSON_ONE (Excited): The airline announced a huge DEcrease in flight tickets, but will baggage fees deCREASE too?\nPERSON_TWO (Amused): Listen to that cadence! You nailed the contrast between the discount and the action.",
        "DIALOGUE_PART_2": "PERSON_ONE (Baffled): Wait, so my stress fell on the right syllables without me even overthinking it?\nPERSON_TWO (Chuckling): Exactly! Front punch DEcrease is the noun discount, but rising beat deCREASE is the cost dropping.",
        "DIALOGUE_PART_3": "PERSON_ONE (Curious): So the store advertises a DEcrease, while winter temperatures deCREASE below freezing?\nPERSON_TWO (Smirking): Spot on! Heavy front beat holds the thing, rising climb drives the downward trend.",
        "DIALOGUE_PART_4": "PERSON_ONE (Relieved): Now my vacation stress can deCREASE knowing I saved hundreds on this DEcrease!\nPERSON_TWO (Laughing): Pack your sunglasses, we are heading to the beach!",
        "PAYOFF": "When you master syllable rhythm, native speakers understand you instantly. Speak with confidence and own the language! Drop your dream destination below!"
    }
}


def update_all_roleplays():
    state_dir = PROJECT_ROOT / "state" / "english" / "roleplay"
    if not state_dir.exists():
        print(f"Directory {state_dir} does not exist.")
        return

    updated = 0
    print("=" * 65)
    print("UPDATING ENGLISH ROLEPLAY SCRIPTS (COHERENCE & 4-PART VISUALS)")
    print("=" * 65)

    for sid, script_dict in ROLEPLAYS_CATALOG.items():
        state_file = state_dir / f"script_{sid}.json"
        if not state_file.exists():
            print(f"Warning: {state_file.name} not found.")
            continue

        with state_file.open("r", encoding="utf-8") as f:
            state = json.load(f)

        words = sum(len(str(v).split()) for k, v in script_dict.items() if k != "title")

        # Update script in state
        content_meta = state.get("content_metadata") or {}
        content_meta["script"] = script_dict
        state["content_metadata"] = content_meta
        state["script_text"] = json.dumps(script_dict, ensure_ascii=False, indent=2)

        with state_file.open("w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=4)

        updated += 1
        print(f"[{sid}] Updated successfully -> {words} spoken words across 6 sections (4 dialogue parts)")

    print("=" * 65)
    print(f"Successfully updated {updated} English roleplay scripts!")
    print("Regenerating review CSV in output/scripts_to_see...")
    print("=" * 65)

    process_scripts(
        base_dir=PROJECT_ROOT,
        target_languages=["english"],
        target_types=["roleplay"],
        include_tags=True,
        include_title=True
    )
    print("Done!")


if __name__ == "__main__":
    update_all_roleplays()
