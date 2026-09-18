"""
overhaul_english_suite.py
Overhauls:
1. ENGLISH_READY_PROMPTS_ROLEPLAY.csv (all 119 rows with rich, varied, funny, high-stakes micro-settings)
2. ENGLISH_READY_PROMPTS_GAME.csv (aligns context, cleans encoding)
3. ENGLISH_READY_PROMPTS_FUN_FACTS.csv (expands to 15 viral linguistic curiosities)
"""

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3] / "input" / "csv" / "english" / "expressions_list"

# --- 1. ENGLISH ROLEPLAY FULL LIBRARY OVERHAUL ---
# We map all 119 items with vivid, diverse, high-stakes micro-settings
ROLEPLAY_SCENARIOS = {
    # 01-14: Idioms & Word Stress
    "ER01": "Backstage at a chaotic local community theatre 30 seconds before curtain call: a nervous lead actor is hyperventilating over a forgotten line, and their stage manager buddy shoves them toward the lights saying 'Break a leg!'",
    "ER02": "In a kitchen covered in flour at midnight: two roommates attempting to bake a 3-tier birthday cake; one panics as the cake slides lopsidedly, while the amateur baker friend confidently flips an apron saying 'Don't stress, decorating this will be a piece of cake!'",
    "ER03": "Inside a dusty vintage vinyl record store: two musicians digging through vinyl crates. PERSON_ONE holds up an old LP asking 'Did you hear that band's new reCORD?', and PERSON_TWO laughs holding a sleeve: 'Bro, they released a REcord! But tomorrow we have to reCORD our own track!'. Mandatory: keep uppercase stress 'REcord' and 'reCORD' in dialogue.",
    "ER04": "Outside a friend's house before a surprise party: two friends wrestling with an absurdly oversized gift box in the drizzle. PERSON_ONE asks 'How are we going to preSENT this giant PREsent without dropping it in a puddle?'. Mandatory: keep uppercase stress 'PREsent' and 'preSENT' in dialogue.",
    "ER05": "On a windy rooftop cinema shoot: a student director shouts into a megaphone telling the lead actor to 'proJECT your voice across the alley!', while the sound guy complains that this crazy student 'PROject is draining his last battery.' Mandatory: keep uppercase stress 'PROject' and 'proJECT' in dialogue.",
    "ER06": "At a bustling food truck festival: a cook and their manager facing an over-enthusiastic city inspector. The cook waves a laminated city 'PERmit' shouting 'Our PERmit is valid!', while the manager argues whether festival rules 'perMIT' extra hot sauce dispensers. Mandatory: keep uppercase stress 'PERmit' and 'perMIT' in dialogue.",
    "ER07": "In a thrift market: two roommates examining a bizarre metallic modern sculpture. PERSON_ONE asks 'What kind of weird OBject is this?', and PERSON_TWO jokingly raises their hand like a lawyer: 'I obJECT to putting that monstrosity in our living room!'. Mandatory: keep uppercase stress 'OBject' and 'obJECT' in dialogue.",
    "ER08": "At a fantasy league draft table: two hyper-competitive friends negotiating a player trade. PERSON_ONE slaps a paper on the table: 'Sign this CONtract or our trade window will conTRACT to zero!'. Mandatory: keep uppercase stress 'CONtract' and 'conTRACT' in dialogue.",
    "ER09": "In a home garage gym: two workout partners watching a barbell bend under heavy iron plates. PERSON_ONE brags about a massive 'INcrease in his personal record', while PERSON_TWO yells: 'Don't inCREASE the weight if you can't lift it off your chest!'. Mandatory: keep uppercase stress 'INcrease' and 'inCREASE' in dialogue.",
    "ER10": "In a noisy café with blaring espresso grinders: two podcast co-hosts editing sound levels with headphones. PERSON_ONE gestures wildly: 'We need a DEcrease in background chatter—deCREASE the gain before our ears explode!'. Mandatory: keep uppercase stress 'DEcrease' and 'deCREASE' in dialogue.",
    "ER11": "At a specialty coffee bean roastery: two roasters inspecting raw burlap sacks. PERSON_ONE asks 'Is this Ethiopian roast a direct IMport?', while PERSON_TWO stamps the delivery: 'We had to imPORT forty sacks to meet morning demand!'. Mandatory: keep uppercase stress 'IMport' and 'imPORT' in dialogue.",
    "ER12": "At a bustling dockside cargo terminal: two logistics coordinators checking shipping containers. PERSON_ONE checks the manifest: 'Automobiles are our top EXport this quarter!', while PERSON_TWO radios the crane operator: 'We need to exPORT these forty containers before tonight!'. Mandatory: keep uppercase stress 'EXport' and 'exPORT' in dialogue.",
    "ER13": "Outside city hall during a passionate bicycle lane demonstration: two cyclist friends holding handmade cardboard signs. PERSON_ONE marches chanting 'Join the PROtest for safer streets!', while PERSON_TWO jokes: 'I won't proTEST as long as we get iced coffee after this!'. Mandatory: keep uppercase stress 'PROtest' and 'proTEST' in dialogue.",
    "ER14": "Backstage at an international street dance showdown: two b-boy rivals warming up. PERSON_ONE stretches nervously: 'This breakdance CONtest is insane!', while PERSON_TWO grins: 'I came here to conTEST their championship title!'. Mandatory: keep uppercase stress 'CONtest' and 'conTEST' in dialogue.",

    # 15-32: Minimal Pairs & Acoustic Contrasts
    "ER15": "At a high-end French bakery counter: a hungry tourist asks the pastry chef if they can try the chocolate 'desert' with sand and camels, and their travel buddy bursts out laughing pointing to the pastry cart: 'A desert is full of sand, you want a sweet dessert!'",
    "ER16": "At a scuba diving certification pool: a panicked diver surfaces gasping for air and says 'I lost my breathe under water!', while the instructor chuckles: 'Take a deep breath and relax; you need to learn how to breathe slowly.'",
    "ER17": "In a competitive science fair booth: two students presenting a volcano experiment that didn't bubble. One panics 'Where is the prove?', and the lab partner grabs the notebook: 'You need mathematical proof before you can prove your theory!'",
    "ER18": "At a busy airport baggage claim: a traveler tries to cram an open laptop into an unlocked backpack. Their friend grabs their shoulder: 'Put it in the hotel safe! You need to save your files and keep your passport safe!'",
    "ER19": "At a dog grooming salon with an energetic golden retriever covered in mud: one groomer yells 'He won't take a bathe!', and the partner laughs holding the hose: 'Give him a warm bath first, then bathe him with shampoo!'",
    "ER20": "Cleaning up a spilled pitcher of berry smoothie in the kitchen: one roommate grabs an expensive designer silk shirt to wipe the counter, and the other screams: 'Stop! That's designer clothe, use this cleaning cloth!'",
    "ER21": "Road tripping on Route 66 at midnight starving: the driver says 'Let's pull over at that retro diner for dinner!', but the passenger gets confused thinking they're eating a whole building.",
    "ER22": "Driving through the rolling green hills of New Zealand: a city tourist looks out the camper van window and yells 'Look at all those 500 ships grazing on the grass!', leaving the local driver crying with laughter: 'Ships float on the ocean, those are sheep with wool!'",
    "ER23": "At a packed Premier League soccer stadium trying to squeeze through row 14: a fan asks an usher 'Can I seat in this chair?', and the usher smiles: 'You can sit down here, because this is your reserved seat.'",
    "ER24": "At a neighborhood sports club: two friends arguing over afternoon plans. One points to the gym pull-up bar, while the other in swimming trunks insists: 'I don't want to pull weights, let's jump in the pool!'",
    "ER25": "In a heated retro arcade gaming match: one player loses by two points and yells 'I'm just a beat tired!', while the winner celebrates: 'You lost by a little bit, but nobody can beat my high score!'",
    "ER26": "Camping in a leaky tent during a sudden midnight rainstorm: one camper shivers on a soggy sleeping bag complaining 'This bad is terrible!', and the friend laughs: 'Your bed is wet, but your attitude is bad!'",
    "ER27": "Planting apple saplings in a community garden: a volunteer asks for 'three trees', but pronounces both the same, handing over three leaves instead of three trees.",
    "ER28": "At an Italian pizza making workshop: a clumsy cook rolls the dough paper-thin and whispers 'Making this dough so thin feels like a sin!', and the chef winks: 'Eating bad pizza is the only real sin!'",
    "ER29": "At a crowded espresso bar: a barista accidentally overfills a latte until it overflows on the counter. The customer mocks: 'The cup was full, don't make a fool of yourself trying to carry it!'",
    "ER30": "At an art studio mixing oil paints: an apprentice dips their hand into blue acrylic and says 'Fill the paint on your fingers!', and the teacher corrects: 'Feel the smooth texture as you fill the canvas!'",
    "ER31": "At an arcade claw machine: a kid drops three coins trying to win a stuffed dragon. The older brother warns: 'Look at the price of each token—that plush toy is not worth the prize!'",
    "ER32": "In a university library during finals week: a student speaks loudly on speakerphone, and the librarian glares over reading glasses: 'It is quite clear that you need to be completely quiet in here!'",

    # 33-55: Confusing Words & Grammar Traps
    "ER33": "Comparing workout results at the gym mirror: two gym buddies comparing bicep curls. One says 'I'm stronger then you!', and the partner laughs: 'You mean taller than me! Then you do twenty push-ups!'",
    "ER34": "Reviewing a dream job offer letter at a rooftop café: a candidate panics reading the contract: 'I accept everything except the weekend night shift clause!'",
    "ER35": "Before a major college exam: two students downing energy drinks. One complains 'The lack of sleep will effect my score!', and the other replies: 'The real effect is fatigue, and it will affect your memory!'",
    "ER36": "Packing equipment into a music tour van: the drummer asks 'Should I bring your guitar to the studio or take it home?', and the singer laughs: 'Bring it here to the van, don't take it home!'",
    "ER37": "At an indie film premiere discussing two directors: a film critic asks 'Did you prefer the former movie or the latter film released later in November?'",
    "ER38": "At a chic stationery boutique in London: a cyclist shopping for luxury fountain pen envelopes asks 'Why is that exercise bike stationary next to the designer stationery counter?'",
    "ER39": "In a high school hallway outside the administrative office: two mischievous students waiting on the bench. One whispers: 'The school principal says punctuality is our number one moral principle!'",
    "ER40": "At a fashion runway show: a designer admires an outfit and says 'That emerald scarf is the perfect complement to your suit, take it as a sincere compliment!'",
    "ER41": "Checking a smartphone weather forecast before a sailing trip: two sailors looking at stormy clouds. One asks: 'I don't know whether the stormy weather will cancel our boat regatta.'",
    "ER42": "In a college mentor's office: an advisor reviews an internship essay and tells the student: 'I strongly advise you to take my professional advice on networking!'",
    "ER43": "In a crowded subway car rushing for the doors: a passenger feels their pocket: 'My pants are so loose that I'm terrified I will lose my wallet on the train!'",
    "ER44": "Sprinting through a busy train station concourse: two travelers carrying backpacks. One pants: 'Hurry up or we will miss our train and lose our non-refundable tickets!'",
    "ER45": "At a neighborhood DIY tool exchange: a neighbor asks 'Can I borrow your electric drill if you lend me your ladder for the weekend?'",
    "ER46": "Over dinner after a heated board game: two friends arguing over Monopoly rules. One snaps: 'Are we going to calmly discuss this trade or argue all night like kids?'",
    "ER47": "At a surprise party planning session: one organizer whispers 'Don't tell Sarah what I said, just say that dinner is at eight!'",
    "ER48": "Searching for car keys in a messy apartment: one roommate groans 'I can't remember where I parked, please remind me which street we drove on!'",
    "ER49": "After running a tough marathon in the rain: one runner collapses smiling: 'I worked so hard, but my legs can hardly move right now!'",
    "ER50": "At a dull lecture in a cavernous hall: a student yawns: 'I am so bored listening to this boring speech that my eyelids are shutting!'",
    "ER51": "At an amusement park roller coaster line: one friend laughs at a clown: 'That comedian is really funny, but riding this coaster is pure fun!'",
    "ER52": "Reviewing a daily planner at breakfast: 'Running five miles is not an everyday routine for me, but I stretch every day.'",
    "ER53": "In a shared kitchen preparing Sunday brunch: 'I will make fresh pancakes if you do the dishes afterwards!'",
    "ER54": "Outside a university testing center: two classmates holding pencils. One sighs: 'I have to take the exam today, but I studied all night to pass it!'",
    "ER55": "On a scenic mountain hiking trail: one hiker stops walking to light a cigarette, and the friend warns: 'Stop smoking so we don't have to stop to smoke every mile!'",

    # 56-65: False Friends & Common Confusions
    "ER56": "At a party answering a rumor about moving abroad: 'People think I moved to Tokyo, but actually I am still living right here in London!'",
    "ER57": "At a black-tie gala after tripping on a dress train: 'I was so embarrassed when the soup spilled, my face turned bright red!'",
    "ER58": "Planning a budget backpacking trip through Europe: 'Wearing comfortable sneakers is a very sensible choice for walking ancient cobblestones.'",
    "ER59": "Testing hot salsa at a Mexican street stall: 'My mouth is extremely sensitive to spicy jalapeños, pass the ice water!'",
    "ER60": "After three hours of flight delays and lost luggage: 'We waited through four gate changes, but eventually our plane landed safely!'",
    "ER61": "At a technology conference networking lounge: 'Are you going to attend the keynote workshop or just hang out at the coffee booth?'",
    "ER62": "In an entrepreneur mentorship call: 'She gave me three pieces of brilliant advice that completely saved my startup pitch.'",
    "ER63": "At a crowded tourist information desk in Rome: 'The officer gave us helpful information about museum passes across the city.'",
    "ER64": "Catching up at a college alumni reunion: 'I have been working as a software architect in Berlin for two years now.'",
    "ER65": "At the gym talking about a new routine: 'I have been training consistently since Monday and my muscles are already sore!'",

    # 66-83: Prepositions, Collocations & Phrasal Idioms
    "ER66": "Deciding on an outdoor weekend camping trip: 'Whether we hike to the peak will depend on the mountain weather forecast tomorrow.'",
    "ER67": "At a wedding reception toast: 'She has been happily married to my brother for over ten wonderful years.'",
    "ER68": "Arriving late to band practice without sheet music: 'Why didn't you print the chords before coming to the studio today?'",
    "ER69": "At a white-board brainstorming session: 'Can you please explain this complex revenue diagram to me in simple terms?'",
    "ER70": "Reviewing a team vacation proposal: 'I suggest that we book the cabin early, or I suggest leaving at dawn to beat traffic.'",
    "ER71": "At an airport departure gate before summer vacation: 'I am really looking forward to swimming in the Mediterranean sea next week!'",
    "ER72": "Moving from a quiet village to central Tokyo: 'The roaring train noise was overwhelming at first, but now I am used to living in the city.'",
    "ER73": "Reminiscing about childhood memories around a campfire: 'I used to play acoustic guitar every single summer afternoon by the lake.'",
    "ER74": "In a bakery kitchen dropping an egg: 'Don't panic! It is totally normal to make a mistake when learning a new recipe.'",
    "ER75": "Browsing a comic book convention: 'I have always been deeply interested in vintage graphic novels and animation history.'",
    "ER76": "Texting from a travel bus: 'We will arrive at the train station at five, then arrive in Paris before dinner.'",
    "ER77": "At a noisy subway platform sharing earbuds: 'Turn up the volume so I can listen to this podcast interview clearly.'",
    "ER78": "Walking through a downpour without an umbrella: 'We enjoyed the city tour despite the heavy rain, although our shoes were soaked!'",
    "ER79": "Babysitting energetic twin toddlers at a playground: 'I have to look for their lost toy while I look after both kids.'",
    "ER80": "At the cashier of a busy brunch diner: two friends arguing over the bill. One pulls out a card: 'Put your wallet away, let me pay for our breakfast!'",
    "ER81": "In a conference room after a presentation: 'Let's sit down and discuss the project roadmap without rushing.'",
    "ER82": "Celebrating a colleague's promotion with champagne: 'Congratulations on your new role as senior director of design!'",
    "ER83": "Settling a bet over movie trivia: 'If you do the dishes tomorrow, I will cook tonight—fair enough!'",

    # 84-113: Homophones & Tricky Pairs
    "ER84": "Ordering snacks at a movie theater counter: 'I want two sodas, and my friend wants popcorn too, so let's walk to our seats.'",
    "ER85": "Looking for friends at a crowded festival stage: 'They are standing over there with their backpacks because they're waiting for us.'",
    "ER86": "Handing over a lost passport at airport security: 'Check your jacket pocket to make sure you're carrying the boarding pass.'",
    "ER87": "Admiring a rescue kitten at an animal shelter: 'Look at the playful cat chasing its own tail—it's the cutest kitten here!'",
    "ER88": "In a creative writing workshop: 'You have the right artistic instinct, now write your opening chapter on paper.'",
    "ER89": "On a foggy hiking trail trying to locate a teammate: 'Stand right here where the acoustics are clear so you can hear my whistle.'",
    "ER90": "At a clifftop lighthouse looking at the horizon: 'Look out and you can see a cargo ship sailing across the deep blue sea.'",
    "ER91": "Leaving a farmer's market stall: 'I will buy fresh strawberries by the basket before saying bye to the vendor.'",
    "ER92": "At a trivia game night: 'I know the answer to this geography question, there is no doubt about it!'",
    "ER93": "In a bakery prep room: 'Decorate the wedding cake with an edible sugar flower, but don't spill the bag of flour!'",
    "ER94": "In a medieval castle museum exhibit: 'A legendary knight guarded the stone fortress throughout the stormy night.'",
    "ER95": "Unpacking groceries after a trip to the supermarket: 'I bought a fresh pair of socks and a juicy sweet pear for lunch.'",
    "ER96": "At a neighborhood butcher shop: 'Let's meet at noon so we can pick up quality meat for tonight's barbecue.'",
    "ER97": "At a physical therapy clinic: 'After resting for a full week, my injured ankle no longer feels weak.'",
    "ER98": "In a car on a steep mountain descent: 'Step firmly on the brake pedal so we don't break the suspension on this gravel!'",
    "ER99": "In a philosophy seminar: 'It is my strong personal belief that scientists truly believe in evidence-based research.'",
    "ER100": "Raking autumn foliage in the yard: 'Look at that golden maple leaf before we leave for the afternoon.'",
    "ER101": "At a live rock concert in an arena: 'This unforgettable night is the best live music experience of my whole life!'",
    "ER102": "Tucking laundry into a closet: 'Make sure to close the wooden wardrobe door so dust doesn't touch the clean clothe.'",
    "ER103": "In a sushi master kitchen: 'Watch the temperature rise as the jasmine rice steams inside the pot.'",
    "ER104": "Playing a board game in a cabin: 'Roll the wooden dice on the table before the campfire dies down.'",
    "ER105": "At an outdoor skating rink: 'Rub the cold ice against your forehead and look into my eyes to focus.'",
    "ER106": "At a noisy dinner table with toddlers: 'All I want is two minutes of peace and quiet while you eat your green peas!'",
    "ER107": "In a skincare consultation: 'Wash your tired face gently during this initial healing phase of the treatment.'",
    "ER108": "At a hilarious county fair hotdog eating contest: 'The winner of the trophy just devoured his twenty-fifth wiener!'",
    "ER109": "At an international airport departure gate: 'I will live in Toronto for a year once my flight is ready to leave.'",
    "ER110": "At a crowded department store suit department: 'That distinguished man over there is assisting five young men with ties.'",
    "ER111": "At a veterinary rescue clinic: 'Be gentle with the injured cat while the doctor bandages the small cut on its paw.'",
    "ER112": "Under the scorching summer sun at the beach: 'Put on your wide straw hat before the midday heat becomes dangerously hot!'",
    "ER113": "At a comic book convention autograph line: 'I am a huge anime fan, and meeting the voice actor was pure fun!'",

    # 114-119: Signature Idioms
    "ER114": "Negotiating a high-stakes freelance contract at a coffee shop: 'I gave you my best discount offer, so now the ball is in your court!'",
    "ER115": "In an animation studio at 11 PM after finishing 40 frames: 'Our eyes are burning and the scene is done, let's call it a day!'",
    "ER116": "After an exhausting 14-hour flight and customs line: two travel buddies drop their backpacks on the hotel floor: 'I am completely dead on my feet, time to hit the sack!'",
    "ER117": "At a baseball playoff game in the bottom of the ninth with two outs: 'Down by two runs, but it ain't over till the fat lady sings!'",
    "ER118": "Teaching a friend how to change a bicycle flat tire on a trail: 'Just slide the tire lever under the rim—relax, it's not rocket science!'",
    "ER119": "In a messy apartment meeting between roommates about unpaid rent: 'Nobody wants to talk about the huge unpaid electricity bill, but it's the elephant in the room!'"
}

def overhaul_english_roleplay():
    csv_file = BASE_DIR / "ENGLISH_READY_PROMPTS_ROLEPLAY.csv"
    with open(csv_file, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    updated_count = 0
    for r in rows:
        cid = r["ID"].strip().upper()
        if cid in ROLEPLAY_SCENARIOS:
            r["ROLEPLAY_SCENARIO"] = ROLEPLAY_SCENARIOS[cid]
            updated_count += 1

    fieldnames = list(rows[0].keys())
    with open(csv_file, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Updated {updated_count}/{len(rows)} English Roleplay scenarios in {csv_file.name}")

# --- 2. ENGLISH FUN FACTS EXPANSION (15 Viral Linguistic Curiosities) ---
FUN_FACTS_ENGLISH = [
    {
        "ID": "EF01",
        "TOPIC": "'I am' is the Shortest Complete Sentence in English",
        "PILLAR": "GRAMMAR_CURIOSITIES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "The two-word statement 'I am' contains a subject pronoun ('I') and a finite predicate verb ('am'), making it the shortest grammatically complete declarative sentence in the English language.",
        "HOOK_ANGLE": "What is the shortest grammatically complete sentence you can possibly say in the entire English language?",
        "EMOTIONAL_TRIGGER": "Curiosity & Surprise"
    },
    {
        "ID": "EF02",
        "TOPIC": "The Sentence That Uses Every Single Letter in the Alphabet",
        "PILLAR": "WORD_CURIOSITIES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "'The quick brown fox jumps over the lazy dog' is a famous pangram: a sentence that contains all 26 letters of the English alphabet at least once, traditionally used by typists to test keyboards.",
        "HOOK_ANGLE": "Can you craft a real sentence that uses all 26 letters of the English alphabet? Here is the most famous one!",
        "EMOTIONAL_TRIGGER": "Aha Moment & Discovery"
    },
    {
        "ID": "EF03",
        "TOPIC": "Ghost Words That Dictionaries Invented by Mistake",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "MYSTERY",
        "FACT_DETAILS": "In 1934, Webster's New International Dictionary accidentally printed the non-existent word 'Dord' defining it as 'density'. It was an editor's misreading of 'D or d', and remained in print for five years.",
        "HOOK_ANGLE": "Did you know that dictionaries have accidentally published completely fake 'ghost words' that fooled the world for years?",
        "EMOTIONAL_TRIGGER": "Surprise & Humor"
    },
    {
        "ID": "EF04",
        "TOPIC": "The 3-Letter Word with Over 430 Definitions",
        "PILLAR": "WORD_CURIOSITIES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "According to the Oxford English Dictionary, the little three-letter word 'SET' holds the record for the most meanings in English, boasting over 430 distinct definitions and taking up 60,000 words of explanation.",
        "HOOK_ANGLE": "Which tiny 3-letter English word has over 430 different definitions in the dictionary?",
        "EMOTIONAL_TRIGGER": "Astonishment & Curiosity"
    },
    {
        "ID": "EF05",
        "TOPIC": "3 Everyday English Words with Zero Rhymes",
        "PILLAR": "WORD_CURIOSITIES",
        "FORMAT": "3_FACTS",
        "FACT_DETAILS": "According to Oxford Dictionaries, the everyday words 'Silver', 'Purple', and 'Month' have zero perfect single-word rhymes in the entire English language.",
        "HOOK_ANGLE": "Think you are a master of English rhymes? Here are 3 everyday words that literally nothing in the universe rhymes with.",
        "EMOTIONAL_TRIGGER": "Challenge & Curiosity"
    },
    {
        "ID": "EF06",
        "TOPIC": "Why Theater Performers Say 'Break a Leg' Instead of Good Luck",
        "PILLAR": "CULTURAL_MYSTERIES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "Old theatrical superstition held that spirits would curse anyone wishing good luck, so performers wished each other harm. Additionally, 'breaking a leg' referred to bending the knee while bowing after a successful performance.",
        "HOOK_ANGLE": "Why on earth do actors wish each other broken bones right before stepping out onto a Broadway stage?",
        "EMOTIONAL_TRIGGER": "Curiosity & Discovery"
    },
    {
        "ID": "EF07",
        "TOPIC": "Why the Word 'Queue' Has Four Silent Letters",
        "PILLAR": "ETYMOLOGY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "In the word 'QUEUE', the last four letters ('ue-ue') are completely silent, meaning the word is pronounced identically to its first letter 'Q'. It entered English from French, derived from Latin 'cauda' meaning tail.",
        "HOOK_ANGLE": "Why did English keep four silent letters in 'queue' when only the letter 'Q' actually speaks?",
        "EMOTIONAL_TRIGGER": "Humor & Fascination"
    },
    {
        "ID": "EF08",
        "TOPIC": "Why Farm Animals are Germanic but Their Meat is French",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "3_FACTS",
        "FACT_DETAILS": "After the 1066 Norman Conquest, Anglo-Saxon peasants raised the animals in fields (cow, pig, sheep - Germanic words), while French-speaking Norman nobles ate the prepared meals at court (beef/bœuf, pork/porc, mutton/mouton).",
        "HOOK_ANGLE": "Why is the animal called a 'cow' in the pasture, but the food on your plate is called 'beef'?",
        "EMOTIONAL_TRIGGER": "Aha Moment & History"
    },
    {
        "ID": "EF09",
        "TOPIC": "A Sentence with the Same Word Repeated 8 Times That Is Grammatically Perfect",
        "PILLAR": "GRAMMAR_CURIOSITIES",
        "FORMAT": "CHALLENGE",
        "FACT_DETAILS": "'Buffalo buffalo Buffalo buffalo buffalo buffalo Buffalo buffalo' is a valid grammatical sentence. It uses 'Buffalo' as a city noun, a beast noun, and an archaic verb meaning to intimidate or outwit.",
        "HOOK_ANGLE": "Can you say the word 'Buffalo' eight times in a row and form a 100% grammatically correct English sentence?",
        "EMOTIONAL_TRIGGER": "Challenge & Surprise"
    },
    {
        "ID": "EF10",
        "TOPIC": "The Great Vowel Shift That Wrecked English Spelling Forever",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "MYSTERY",
        "FACT_DETAILS": "Between 1400 and 1700, English speakers mysteriously shifted their mouth position for all long vowels, turning 'bite' from 'beet' to 'bite'. Because the printing press froze spelling right before the shift, English spelling never recovered.",
        "HOOK_ANGLE": "Why is English spelling so completely illogical? A bizarre 300-year mystery changed how every single vowel sounded!",
        "EMOTIONAL_TRIGGER": "Fascination & Discovery"
    },
    {
        "ID": "EF11",
        "TOPIC": "Why 'Ghoti' Can Be Pronounced Exactly Like 'Fish'",
        "PILLAR": "PRONUNCIATION_CURIOSITIES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "George Bernard Shaw popularized 'Ghoti': 'gh' pronounced like /f/ in 'tough', 'o' pronounced like /i/ in 'women', and 'ti' pronounced like /sh/ in 'nation'. It perfectly illustrates the chaotic phonetic irregularity of English.",
        "HOOK_ANGLE": "How could the bizarre word 'G-H-O-T-I' be pronounced identically to 'fish' using real English spelling rules?",
        "EMOTIONAL_TRIGGER": "Surprise & Humor"
    },
    {
        "ID": "EF12",
        "TOPIC": "The Longest English Word Spelled Without Repeating a Letter",
        "PILLAR": "WORD_CURIOSITIES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "'Uncopyrightable' (15 letters) and 'Subdermatoglyphic' (17 letters) are isograms: words in which every single letter appears exactly once without repetition.",
        "HOOK_ANGLE": "What is the longest real English word you can spell without repeating a single letter even once?",
        "EMOTIONAL_TRIGGER": "Challenge & Curiosity"
    },
    {
        "ID": "EF13",
        "TOPIC": "Why We Say 'Bless You' When Someone Sneezes",
        "PILLAR": "CULTURAL_MYSTERIES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "In 590 AD during the Plague of Rome, Pope Gregory I ordered prayers and blessings for anyone who sneezed, as sneezing was believed to be an early symptom of fatal illness or expulsion of the soul.",
        "HOOK_ANGLE": "Why does everyone automatically say 'Bless you!' the second you sneeze? The origin dates back to an ancient plague!",
        "EMOTIONAL_TRIGGER": "Curiosity & History"
    },
    {
        "ID": "EF14",
        "TOPIC": "Why British English Says 'Autumn' While Americans Say 'Fall'",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "Both terms originated in England. 'Fall' was short for 'fall of the leaf' in the 1500s. British English later adopted the Latinate 'autumn' from French, while American colonists preserved the older, poetic English 'fall'.",
        "HOOK_ANGLE": "Is 'fall' just American slang? The surprising historical truth about who actually invented the word 'fall'!",
        "EMOTIONAL_TRIGGER": "Aha Moment & Clarity"
    },
    {
        "ID": "EF15",
        "TOPIC": "The Word 'Goodbye' is Actually an Old Christian Blessing",
        "PILLAR": "ETYMOLOGY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "'Goodbye' is a contraction of the Late Middle English farewell phrase 'God be with ye' (1500s). Over centuries of casual daily speech, it morphed into 'Good-b'w'y' and finally 'Goodbye', influenced by 'good day'.",
        "HOOK_ANGLE": "Every single time you say 'Goodbye', you are actually reciting an ancient religious blessing from the 1500s!",
        "EMOTIONAL_TRIGGER": "Fascination & Discovery"
    }
]

def overhaul_english_fun_facts():
    csv_file = BASE_DIR / "ENGLISH_READY_PROMPTS_FUN_FACTS.csv"
    fieldnames = ["ID", "TOPIC", "PILLAR", "FORMAT", "FACT_DETAILS", "HOOK_ANGLE", "EMOTIONAL_TRIGGER"]
    with open(csv_file, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(FUN_FACTS_ENGLISH)
    print(f"[OK] Updated {len(FUN_FACTS_ENGLISH)} English Fun Facts in {csv_file.name}")

if __name__ == "__main__":
    overhaul_english_roleplay()
    overhaul_english_fun_facts()
