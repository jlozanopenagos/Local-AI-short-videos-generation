"""
video_creation/_D_music_generation/prompts_catalog.py

Standing Music Bank Prompt Catalog for LingoVerse Shorts Automation.
Provides 10 distinctly orchestrated musical prompts for each (language, video_type) pair
(16 categories x 10 tracks = 160 unique jams).

Every jam features a distinct musical archetype, tempo (BPM), instrumentation, and groove
tailored directly to the emotional triggers discovered across all input CSV queues and state metadata.
"""

from typing import Dict, List, Any

# Structure: MUSIC_BANK_CATALOG[language][video_type] = List[Dict[str, Any]]
MUSIC_BANK_CATALOG: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "english": {
        "expression": [
            {
                "id": "jam_01",
                "filename": "jam_01_aha_confidence.wav",
                "name": "Golden Lightbulb",
                "emotion_slug": "aha_confidence",
                "matching_emotions": ["aha moment & confidence", "aha", "confidence", "clarity & confidence"],
                "bpm": 88,
                "style": "Warm Neo-Soul Lo-Fi",
                "instrumentation": "Fender Rhodes electric piano, smooth walking bassline, subtle vinyl crackle, brushed snare",
                "prompt": "Warm neo-soul lo-fi hip hop, warm Fender Rhodes electric piano chords, smooth electric bass, light vinyl crackle, mellow brushed snare, 88 BPM, confident and enlightened mood, clean instrumental background music, no vocals"
            },
            {
                "id": "jam_02",
                "filename": "jam_02_curiosity_clarity.wav",
                "name": "Mind Unlocked",
                "emotion_slug": "curiosity_clarity",
                "matching_emotions": ["curiosity & clarity", "clarity", "curiosity"],
                "bpm": 82,
                "style": "Acoustic Fingerstyle Chill",
                "instrumentation": "Nylon acoustic guitar, wooden shaker, warm upright bass, gentle glockenspiel accent",
                "prompt": "Chill acoustic fingerstyle guitar, gentle wooden shaker, warm upright acoustic bass, subtle glockenspiel accents, 82 BPM, curious and insightful atmosphere, clean acoustic recording, instrumental background music, no vocals"
            },
            {
                "id": "jam_03",
                "filename": "jam_03_curiosity_tension.wav",
                "name": "Secret Clue",
                "emotion_slug": "curiosity_tension",
                "matching_emotions": ["curiosity & tension", "tension", "intrigue"],
                "bpm": 95,
                "style": "Minimal Mystery Trip-Hop",
                "instrumentation": "Muted electric guitar plucks, subtle analog sub-bass, soft ticking percussion, warm tape delay",
                "prompt": "Minimal mystery lo-fi trip-hop, muted electric guitar staccato plucks, warm analog sub-bass, soft ticking percussion, atmospheric tape delay, 95 BPM, intriguing and suspenseful mood, instrumental background music, no vocals"
            },
            {
                "id": "jam_04",
                "filename": "jam_04_encouragement_relief.wav",
                "name": "Breathe Easy",
                "emotion_slug": "encouragement_relief",
                "matching_emotions": ["encouragement & relief", "relief", "encouragement"],
                "bpm": 76,
                "style": "Breezy Indie Chillhop",
                "instrumentation": "Acoustic guitar strums, soft ambient piano, mellow bass, gentle rimshot groove",
                "prompt": "Breezy indie chillhop, acoustic guitar chords, warm melodic piano, soothing mellow bass, gentle rimshot groove, 76 BPM, uplifting relief and reassuring warmth, instrumental background music, no vocals"
            },
            {
                "id": "jam_05",
                "filename": "jam_05_hope_motivation.wav",
                "name": "Rise & Shine",
                "emotion_slug": "hope_motivation",
                "matching_emotions": ["hope & motivation", "hope", "motivation", "optimism"],
                "bpm": 104,
                "style": "Upbeat Indie Pop Groove",
                "instrumentation": "Bouncy clean electric guitar, bright piano octaves, driving kick and clap, melodic synth bass",
                "prompt": "Upbeat indie pop groove, bouncy clean electric rhythm guitar, bright melodic piano, crisp handclaps and kick, melodic synth bassline, 104 BPM, inspiring and motivational energy, instrumental background music, no vocals"
            },
            {
                "id": "jam_06",
                "filename": "jam_06_relief_relaxation.wav",
                "name": "Sunday Porch",
                "emotion_slug": "relief_relaxation",
                "matching_emotions": ["relief & relaxation", "relaxation", "calm", "ease"],
                "bpm": 72,
                "style": "Laid-back Boom-Bap Chill",
                "instrumentation": "Muted upright piano, double bass, relaxed boom-bap drum loop, warm tape warmth",
                "prompt": "Laid-back boom-bap chill, dusty upright piano chords, deep warm double bass, relaxed lo-fi drum groove, soft vinyl ambiance, 72 BPM, deeply relaxing and peaceful feeling, instrumental background music, no vocals"
            },
            {
                "id": "jam_07",
                "filename": "jam_07_surprise_curiosity.wav",
                "name": "Wait, What?",
                "emotion_slug": "surprise_curiosity",
                "matching_emotions": ["surprise & curiosity", "surprise", "wonder"],
                "bpm": 90,
                "style": "Playful Jazz-Hop",
                "instrumentation": "Pizzicato string stabs, muted trumpet accents, bouncy hip hop beat, funky electric bass",
                "prompt": "Playful jazz-hop beat, bouncy pizzicato string stabs, subtle muted trumpet fills, funky warm electric bassline, crisp hip hop drums, 90 BPM, quirky and surprising vibe, instrumental background music, no vocals"
            },
            {
                "id": "jam_08",
                "filename": "jam_08_humor_clarity.wav",
                "name": "Witty Wink",
                "emotion_slug": "humor_clarity",
                "matching_emotions": ["humor & clarity", "humor", "witty", "playful"],
                "bpm": 98,
                "style": "Bouncy Funk Lo-Fi",
                "instrumentation": "Slap bass accents, groovy wah-wah guitar, punchy claps, cheerful electric organ",
                "prompt": "Bouncy funk lo-fi groove, punchy bass groove with subtle slap accents, clean rhythmic wah guitar, cheerful electric organ chops, light claps, 98 BPM, witty comedic charm and clarity, instrumental background music, no vocals"
            },
            {
                "id": "jam_09",
                "filename": "jam_09_relief_confidence.wav",
                "name": "Mastered It",
                "emotion_slug": "relief_confidence",
                "matching_emotions": ["relief & confidence", "confidence & clarity", "mastery"],
                "bpm": 86,
                "style": "Smooth R&B Chillhop",
                "instrumentation": "Velvet electric keys, smooth synth bass, crisp hi-hats, subtle finger snaps",
                "prompt": "Smooth R&B chillhop, velvet lush electric keys, deep warm 808 bass, crisp finger snaps, tight hi-hats, 86 BPM, confident stylish swagger and ease, instrumental background music, no vocals"
            },
            {
                "id": "jam_10",
                "filename": "jam_10_discovery_flow.wav",
                "name": "Urban Flow",
                "emotion_slug": "discovery_flow",
                "matching_emotions": ["discovery", "natural", "flow", "general"],
                "bpm": 84,
                "style": "Classic Instrumental Hip-Hop",
                "instrumentation": "Jazzy piano sample, warm sub, crisp boom bap snare, ambient street cafe texture",
                "prompt": "Classic instrumental hip hop, jazzy melodic piano loop, warm round bassline, crisp boom bap snare, tape saturation, 84 BPM, natural storytelling flow and focus, instrumental background music, no vocals"
            }
        ],
        "roleplay": [
            {
                "id": "jam_01",
                "filename": "jam_01_dialogue_bounce.wav",
                "name": "Coffee Talk",
                "emotion_slug": "dialogue_bounce",
                "matching_emotions": ["dialogue", "natural", "conversation", "clarity & confidence"],
                "bpm": 92,
                "style": "Bouncy Coffeehouse Beat",
                "instrumentation": "Warm acoustic guitar chords, bouncy electric bass, light percussion, subtle Rhodes",
                "prompt": "Warm coffeehouse acoustic lo-fi, melodic acoustic guitar chords, bouncy electric bass, gentle shaker and rimshot, soft electric keys, 92 BPM, conversational and lively dialogue mood, instrumental background music, no vocals"
            },
            {
                "id": "jam_02",
                "filename": "jam_02_humor_banter.wav",
                "name": "Playful Banter",
                "emotion_slug": "humor_banter",
                "matching_emotions": ["humor & relief", "humor & clarity", "relief & humor", "humor"],
                "bpm": 100,
                "style": "Quirky Funk Hop",
                "instrumentation": "Staccato pizzicato strings, funky clavinet, bouncy bass, crisp finger snaps",
                "prompt": "Quirky funk hop, staccato pizzicato strings, rhythmic clavinet chops, bouncy walking bassline, crisp finger snaps and claps, 100 BPM, humorous friendly banter and comic timing, instrumental background music, no vocals"
            },
            {
                "id": "jam_03",
                "filename": "jam_03_awkward_tension.wav",
                "name": "Awkward Pause",
                "emotion_slug": "awkward_tension",
                "matching_emotions": ["curiosity & tension", "tension", "beginner", "nervous"],
                "bpm": 85,
                "style": "Minimalist Ticking Lo-Fi",
                "instrumentation": "Soft pizzicato cello, ticking woodblock percussion, muted guitar, subtle bass drone",
                "prompt": "Minimalist ticking lo-fi, soft pizzicato cello plucks, subtle woodblock clock-like percussion, muted electric guitar chords, 85 BPM, light awkward tension and comedic suspense, instrumental background music, no vocals"
            },
            {
                "id": "jam_04",
                "filename": "jam_04_supportive_friend.wav",
                "name": "Got Your Back",
                "emotion_slug": "supportive_friend",
                "matching_emotions": ["encouragement & relief", "relief & confidence", "supportive", "friendly"],
                "bpm": 80,
                "style": "Soulful Acoustic Lo-Fi",
                "instrumentation": "Warm acoustic guitar strums, sweet electric piano, melodic bass, brushed cymbals",
                "prompt": "Soulful acoustic lo-fi, gentle acoustic guitar strums, sweet Fender Rhodes electric piano, melodic warm bass, soft brushed cymbals, 80 BPM, supportive heartwarming friendly mood, instrumental background music, no vocals"
            },
            {
                "id": "jam_05",
                "filename": "jam_05_aha_realization.wav",
                "name": "Now I Get It",
                "emotion_slug": "aha_realization",
                "matching_emotions": ["aha moment & confidence", "aha", "relief & curiosity"],
                "bpm": 90,
                "style": "Uplifting Chillhop",
                "instrumentation": "Lush Rhodes chords, subtle glockenspiel chime, smooth drum beat, groovy bass",
                "prompt": "Uplifting chillhop, lush Rhodes piano chords, subtle glockenspiel chime, smooth boom-bap drums, groovy electric bassline, 90 BPM, bright moment of realization and mutual relief, instrumental background music, no vocals"
            },
            {
                "id": "jam_06",
                "filename": "jam_06_smooth_negotiation.wav",
                "name": "Street Smart",
                "emotion_slug": "smooth_negotiation",
                "matching_emotions": ["confidence & clarity", "street", "clever", "smart"],
                "bpm": 88,
                "style": "Jazzy Urban Hip-Hop",
                "instrumentation": "Muted jazz guitar, upright bass walk, smooth ride cymbal, soft vinyl",
                "prompt": "Jazzy urban hip hop beat, muted jazz archtop guitar chords, walking upright bass, smooth ride cymbal and snare, vinyl crackle, 88 BPM, clever stylish urban atmosphere, instrumental background music, no vocals"
            },
            {
                "id": "jam_07",
                "filename": "jam_07_chill_hangout.wav",
                "name": "After Hours",
                "emotion_slug": "chill_hangout",
                "matching_emotions": ["relief & relaxation", "relaxation", "hangout", "casual"],
                "bpm": 75,
                "style": "Warm Bedroom Lo-Fi",
                "instrumentation": "Detuned tape piano, deep bass, gentle hip hop drums, rain ambiance",
                "prompt": "Warm bedroom lo-fi, gentle detuned tape piano, deep round bass, slow relaxed hip hop drums, subtle cozy room ambiance, 75 BPM, casual relaxed hangout vibe, instrumental background music, no vocals"
            },
            {
                "id": "jam_08",
                "filename": "jam_08_surprised_reaction.wav",
                "name": "Double Take",
                "emotion_slug": "surprised_reaction",
                "matching_emotions": ["surprise & curiosity", "surprise", "amusement"],
                "bpm": 96,
                "style": "Sprightly Bop Hop",
                "instrumentation": "Vibraphone stabs, bouncy upright bass, crisp rim clicks, muted horn",
                "prompt": "Sprightly bop hop, resonant vibraphone stabs, bouncy upright acoustic bass, crisp rim clicks, subtle muted brass accent, 96 BPM, surprised amusing comedic reaction, instrumental background music, no vocals"
            },
            {
                "id": "jam_09",
                "filename": "jam_09_hopeful_friendship.wav",
                "name": "Sunny Sidewalk",
                "emotion_slug": "hopeful_friendship",
                "matching_emotions": ["hope & motivation", "encouragement", "warmth"],
                "bpm": 102,
                "style": "Bright Indie Folk-Hop",
                "instrumentation": "Acoustic guitar strumming, cheerful whistling sample, driving kick, warm bass",
                "prompt": "Bright indie folk-hop, rhythmic acoustic guitar strumming, subtle cheerful whistle melody, driving warm kick and snap, sunny melodic bassline, 102 BPM, optimistic friendship and camaraderie, instrumental background music, no vocals"
            },
            {
                "id": "jam_10",
                "filename": "jam_10_climax_payoff.wav",
                "name": "Nailed the Line",
                "emotion_slug": "climax_payoff",
                "matching_emotions": ["payoff", "confidence", "victory", "relief"],
                "bpm": 94,
                "style": "Triumphant Neo-Soul",
                "instrumentation": "Warm brass synth chords, punchy bass groove, triumphant piano chords, tight drums",
                "prompt": "Triumphant neo-soul chillhop, warm brass synth pads, punchy driving bass groove, bright piano chords, tight crisp drums, 94 BPM, rewarding victory and punchy conversational payoff, instrumental background music, no vocals"
            }
        ],
        "game": [
            {
                "id": "jam_01",
                "filename": "jam_01_quiz_countdown.wav",
                "name": "Clock is Ticking",
                "emotion_slug": "quiz_countdown",
                "matching_emotions": ["urgent", "countdown", "pressure", "challenging"],
                "bpm": 115,
                "style": "Ticking Suspense Trap-Hop",
                "instrumentation": "Ticking clock hi-hats, 808 sub-bass, anxious synth plucks, driving snare",
                "prompt": "Ticking suspense trap-hop beat, realistic ticking clock percussion, deep 808 sub-bass, anxious staccato synth plucks, driving snare, 115 BPM, urgent quiz show countdown and game pressure, instrumental background music, no vocals"
            },
            {
                "id": "jam_02",
                "filename": "jam_02_trivia_groove.wav",
                "name": "Showtime Trivia",
                "emotion_slug": "trivia_groove",
                "matching_emotions": ["excitement", "energetic", "game show", "excitement / challenge"],
                "bpm": 108,
                "style": "Funky Game Show Beat",
                "instrumentation": "Punchy funk bassline, rhythmic electric piano, brass hits, snappy drums",
                "prompt": "Funky modern game show beat, punchy syncopated funk bassline, rhythmic electric piano chords, subtle brass stabs, snappy upbeat drums, 108 BPM, high-energy trivia entertainment, instrumental background music, no vocals"
            },
            {
                "id": "jam_03",
                "filename": "jam_03_challenge_focus.wav",
                "name": "Brain Teaser",
                "emotion_slug": "challenge_focus",
                "matching_emotions": ["focus", "challenge", "clarity", "excitement and focus"],
                "bpm": 96,
                "style": "Concentration Chillhop",
                "instrumentation": "Marimba arpeggios, tight kick and snap, warm sub-bass, subtle ticking percussion",
                "prompt": "Concentration chillhop, hypnotic marimba arpeggios, tight crisp kick and finger snap, deep warm sub-bass, soft ticking rhythm, 96 BPM, deep focus and intellectual puzzle solving, instrumental background music, no vocals"
            },
            {
                "id": "jam_04",
                "filename": "jam_04_retro_arcade.wav",
                "name": "Pixel Challenge",
                "emotion_slug": "retro_arcade",
                "matching_emotions": ["witty", "playful", "arcade", "energetic and challenging"],
                "bpm": 112,
                "style": "Chiptune Electro-Funk",
                "instrumentation": "8-bit synth leads, funky bass guitar, energetic drums, arcade sound FX accents",
                "prompt": "Playful chiptune electro-funk, retro 8-bit synth arpeggios, funky slap bassline, energetic punchy drums, 112 BPM, playful arcade trivia challenge, instrumental background music, no vocals"
            },
            {
                "id": "jam_05",
                "filename": "jam_05_tension_buildup.wav",
                "name": "Under The Lights",
                "emotion_slug": "tension_buildup",
                "matching_emotions": ["tension", "urgent, challenging", "suspense"],
                "bpm": 102,
                "style": "Dramatic Game Show Tension",
                "instrumentation": "Pulsing synth bass, subtle orchestral strings, heart-beat kick drum, rising riser pad",
                "prompt": "Dramatic modern game show tension, pulsing synth bassline, subtle cinematic staccato strings, heartbeat thumping kick drum, rising atmospheric tension, 102 BPM, intense quiz suspense, instrumental background music, no vocals"
            },
            {
                "id": "jam_06",
                "filename": "jam_06_triumphant_reveal.wav",
                "name": "Got It Right!",
                "emotion_slug": "triumphant_reveal",
                "matching_emotions": ["triumph", "excitement, challenge, triumph", "answer", "victory"],
                "bpm": 110,
                "style": "Upbeat Victory Pop-Funk",
                "instrumentation": "Bright brass stabs, celebratory piano chords, groovy bass, driving upbeat rhythm",
                "prompt": "Upbeat victory pop-funk, bright celebratory brass fanfare stabs, energetic piano chords, groovy bass, punchy clapping rhythm, 110 BPM, triumphant success and exciting quiz answer reveal, instrumental background music, no vocals"
            },
            {
                "id": "jam_07",
                "filename": "jam_07_fast_fingers.wav",
                "name": "Fast Fingers",
                "emotion_slug": "fast_fingers",
                "matching_emotions": ["quick challenge", "urgent, enthusiastic", "speed"],
                "bpm": 120,
                "style": "High-Speed Nu-Disco Hop",
                "instrumentation": "Four-on-the-floor kick, funky rhythm guitar, bright synthesizer, lively bass",
                "prompt": "High-speed nu-disco hop, energetic four-on-the-floor kick, funky rhythmic electric guitar, bright shimmering synth, driving lively bassline, 120 BPM, fast rapid-fire trivia adrenaline, instrumental background music, no vocals"
            },
            {
                "id": "jam_08",
                "filename": "jam_08_mystery_trivia.wav",
                "name": "Native or Weird?",
                "emotion_slug": "mystery_trivia",
                "matching_emotions": ["native or weird?", "what does it really mean?", "mystery"],
                "bpm": 94,
                "style": "Sly Detective Hop",
                "instrumentation": "Pizzicato strings, sly walking upright bass, vibraphone notes, crisp brushed snare",
                "prompt": "Sly detective hip hop, curious pizzicato strings, sly walking upright acoustic bass, subtle vibraphone notes, crisp brushed snare, 94 BPM, investigative trivia mystery, instrumental background music, no vocals"
            },
            {
                "id": "jam_09",
                "filename": "jam_09_competition_clash.wav",
                "name": "The Final Round",
                "emotion_slug": "competition_clash",
                "matching_emotions": ["competitive", "energetic, competitive", "excited, competitive"],
                "bpm": 114,
                "style": "Energetic Breakbeat Funk",
                "instrumentation": "Rhythmic breakbeat drums, aggressive funk bass, energetic piano chops, crowd hype texture",
                "prompt": "Energetic breakbeat funk, punchy breakbeat drum loop, aggressive rhythmic funk bassline, sharp piano chops, 114 BPM, high-stakes competition and exciting championship quiz energy, instrumental background music, no vocals"
            },
            {
                "id": "jam_10",
                "filename": "jam_10_playful_quizzer.wav",
                "name": "Smart Cookie",
                "emotion_slug": "playful_quizzer",
                "matching_emotions": ["witty", "amusement", "excitement/witty", "clarity"],
                "bpm": 104,
                "style": "Bouncy Cartoon Chillhop",
                "instrumentation": "Xylophone melody, bouncy tuba/synth bass, punchy rimshot, cheerful handclaps",
                "prompt": "Bouncy cartoon chillhop, cheerful xylophone melody, punchy bouncy tuba bass, crisp rimshot, playful handclaps, 104 BPM, witty lighthearted language test, instrumental background music, no vocals"
            }
        ],
        "fun_facts": [
            {
                "id": "jam_01",
                "filename": "jam_01_curious_wonder.wav",
                "name": "Did You Know?",
                "emotion_slug": "curious_wonder",
                "matching_emotions": ["curiosity & surprise", "curiosity", "wonder", "discovery"],
                "bpm": 86,
                "style": "Inquisitive Marimba Lo-Fi",
                "instrumentation": "Wooden marimba melody, warm electric piano, smooth upright bass, soft shaker",
                "prompt": "Inquisitive lo-fi beat, warm wooden marimba melody, gentle Fender Rhodes piano, smooth acoustic upright bass, soft shaker, 86 BPM, fascinating curiosity and mind-blowing discovery, instrumental background music, no vocals"
            },
            {
                "id": "jam_02",
                "filename": "jam_02_mystery_origins.wav",
                "name": "Lost in History",
                "emotion_slug": "mystery_origins",
                "matching_emotions": ["mystery", "etymology", "history", "origins"],
                "bpm": 80,
                "style": "Atmospheric Ancient-Hop",
                "instrumentation": "Muted acoustic harp plucks, deep sub-bass, tape-saturated vinyl drums, eerie warm synth pad",
                "prompt": "Atmospheric historical lo-fi hip hop, muted acoustic harp plucks, deep warm sub-bass, dusty tape vinyl drums, eerie warm ambient pad, 80 BPM, ancient origins and fascinating linguistic mystery, instrumental background music, no vocals"
            },
            {
                "id": "jam_03",
                "filename": "jam_03_quirky_science.wav",
                "name": "Brain Tickle",
                "emotion_slug": "quirky_science",
                "matching_emotions": ["challenge & curiosity", "quirky", "intellectual", "challenge"],
                "bpm": 96,
                "style": "Playful Quirky Jazzhop",
                "instrumentation": "Pizzicato violin, vibraphone, bouncy acoustic bass, crisp finger snaps",
                "prompt": "Playful quirky jazzhop, rhythmic pizzicato violin, cheerful vibraphone, bouncy acoustic bass, crisp rhythmic finger snaps, 96 BPM, intellectual amusement and weird fascinating facts, instrumental background music, no vocals"
            },
            {
                "id": "jam_04",
                "filename": "jam_04_playful_challenge.wav",
                "name": "Can You Pronounce It?",
                "emotion_slug": "playful_challenge",
                "matching_emotions": ["playful challenge & amusement", "challenge", "pronunciation"],
                "bpm": 105,
                "style": "Upbeat Whimsical Hop",
                "instrumentation": "Glockenspiel chime, punchy bass, energetic acoustic guitar, snappy drums",
                "prompt": "Upbeat whimsical hop, bright glockenspiel chime, punchy bassline, energetic acoustic guitar strums, snappy clapping drums, 105 BPM, playful tongue-twister challenge and fun, instrumental background music, no vocals"
            },
            {
                "id": "jam_05",
                "filename": "jam_05_mind_blown.wav",
                "name": "Secret Unveiled",
                "emotion_slug": "mind_blown",
                "matching_emotions": ["surprise", "fascination", "mind blown", "records"],
                "bpm": 90,
                "style": "Cinematic Chillhop",
                "instrumentation": "Ambient piano chords, deep cinematic cello, modern boom-bap beat, subtle reverse effects",
                "prompt": "Cinematic modern chillhop, lush emotional ambient piano chords, deep warm cello swells, crisp modern boom-bap beat, subtle reverse sound effects, 90 BPM, astonishing mind-blown revelation, instrumental background music, no vocals"
            },
            {
                "id": "jam_06",
                "filename": "jam_06_cultural_travel.wav",
                "name": "Across the Ocean",
                "emotion_slug": "cultural_travel",
                "matching_emotions": ["regional", "cultural", "dialect", "travel"],
                "bpm": 88,
                "style": "Sunny Global Lo-Fi",
                "instrumentation": "Acoustic ukulele, warm nylon guitar, bongo percussion, soft bass",
                "prompt": "Sunny global lo-fi, gentle acoustic ukulele chords, warm nylon acoustic guitar, light bongo and shaker percussion, smooth bass, 88 BPM, cultural exploration and regional differences, instrumental background music, no vocals"
            },
            {
                "id": "jam_07",
                "filename": "jam_07_language_myth.wav",
                "name": "Myth Busted",
                "emotion_slug": "language_myth",
                "matching_emotions": ["myth", "debunk", "false fact", "surprise"],
                "bpm": 98,
                "style": "Groovy Detective Hop",
                "instrumentation": "Funky wah-wah guitar, upright bass, ride cymbal, retro detective brass swell",
                "prompt": "Groovy detective hop, rhythmic funk wah-wah guitar, cool walking upright bass, smooth ride cymbal, subtle retro brass swell, 98 BPM, myth busting and revealing the real truth, instrumental background music, no vocals"
            },
            {
                "id": "jam_08",
                "filename": "jam_08_record_breaker.wav",
                "name": "Extreme Language",
                "emotion_slug": "record_breaker",
                "matching_emotions": ["records & extremes", "longest word", "extreme"],
                "bpm": 112,
                "style": "Energetic Electro-Chill",
                "instrumentation": "Arpeggiated synthesizer, driving kick, warm synth bass, melodic bells",
                "prompt": "Energetic electro-chill beat, fast arpeggiated analog synthesizer, driving clean kick, warm synth bassline, melodic sparkling bells, 112 BPM, record-breaking extremes and amazing world facts, instrumental background music, no vocals"
            },
            {
                "id": "jam_09",
                "filename": "jam_09_lighthearted_curio.wav",
                "name": "Weird But True",
                "emotion_slug": "lighthearted_curio",
                "matching_emotions": ["amusement", "lighthearted", "curio", "fun"],
                "bpm": 84,
                "style": "Warm Cozy Lo-Fi",
                "instrumentation": "Rhodes electric piano, mellow upright bass, vinyl hiss, sleepy drum beat",
                "prompt": "Warm cozy lo-fi beat, mellow Rhodes electric piano chords, soft walking upright bass, warm vinyl hiss, sleepy gentle drum beat, 84 BPM, weird entertaining facts and relaxed storytelling, instrumental background music, no vocals"
            },
            {
                "id": "jam_10",
                "filename": "jam_10_grand_discovery.wav",
                "name": "Eureka!",
                "emotion_slug": "grand_discovery",
                "matching_emotions": ["discovery", "eureka", "fascination", "payoff"],
                "bpm": 94,
                "style": "Inspiring Modern Chillhop",
                "instrumentation": "Bright acoustic piano, uplifting strings pad, groovy bass, crisp finger snaps",
                "prompt": "Inspiring modern chillhop, bright acoustic grand piano melody, uplifting warm string pad, groovy melodic bass, crisp finger snaps, 94 BPM, grand eureka discovery and inspiring educational takeaway, instrumental background music, no vocals"
            }
        ]
    },
    "french": {
        "expression": [
            {
                "id": "jam_01",
                "filename": "jam_01_paris_cafe_lofi.wav",
                "name": "Café de Flore",
                "emotion_slug": "paris_cafe_lofi",
                "matching_emotions": ["naturel & aisance", "aisance", "clarté & repères", "détente"],
                "bpm": 84,
                "style": "Parisian Lo-Fi Chanson",
                "instrumentation": "Subtle French accordion, warm acoustic nylon guitar, brushed jazz drums, double bass",
                "prompt": "Parisian lo-fi chanson beat, gentle French accordion melody, warm acoustic nylon guitar chords, soft brushed jazz drums, warm acoustic double bass, 84 BPM, natural Parisian charm and relaxed eloquence, instrumental background music, no vocals"
            },
            {
                "id": "jam_02",
                "filename": "jam_02_gypsy_swing_hop.wav",
                "name": "Montmartre Swing",
                "emotion_slug": "gypsy_swing_hop",
                "matching_emotions": ["curiosité & humour", "surprise & humour", "humour"],
                "bpm": 102,
                "style": "Gypsy Jazz Hip-Hop",
                "instrumentation": "Manouche acoustic rhythm guitar, playful violin stabs, bouncy upright bass, hip hop beat",
                "prompt": "Gypsy jazz hip hop, acoustic Manouche rhythm guitar strum, playful swinging acoustic violin, bouncy upright bass, crisp hip hop beat, 102 BPM, witty French humor and playful expression, instrumental background music, no vocals"
            },
            {
                "id": "jam_03",
                "filename": "jam_03_aha_subtlety.wav",
                "name": "Subtilité Française",
                "emotion_slug": "aha_subtlety",
                "matching_emotions": ["aha moment & subtilité", "aha moment & précision", "subtilité", "précision"],
                "bpm": 86,
                "style": "Elegant French Chillhop",
                "instrumentation": "Warm Rhodes piano, delicate clarinet accents, deep melodic bass, light vinyl hiss",
                "prompt": "Elegant French chillhop, warm Fender Rhodes chords, delicate acoustic clarinet accents, deep round bassline, light vinyl hiss, 86 BPM, subtle linguistic precision and enlightened aha moment, instrumental background music, no vocals"
            },
            {
                "id": "jam_04",
                "filename": "jam_04_clarte_confiance.wav",
                "name": "Clarté Pure",
                "emotion_slug": "clarte_confiance",
                "matching_emotions": ["clarté & confiance", "confiance & curiosité", "confiance"],
                "bpm": 90,
                "style": "Sophisticated Neo-Soul",
                "instrumentation": "Mellow electric guitar, bright acoustic piano, punchy electric bass, clean rimshot",
                "prompt": "Sophisticated neo-soul beat, mellow French electric guitar chords, bright acoustic piano accents, punchy electric bass, clean crisp rimshot, 90 BPM, confident French fluency and absolute clarity, instrumental background music, no vocals"
            },
            {
                "id": "jam_05",
                "filename": "jam_05_seine_stroll.wav",
                "name": "Bords de Seine",
                "emotion_slug": "seine_stroll",
                "matching_emotions": ["naturel", "aisance", "précision & aisance"],
                "bpm": 78,
                "style": "Breezy French Acoustic Hop",
                "instrumentation": "Acoustic fingerpicking guitar, soft accordion pads, warm acoustic bass, gentle shaker",
                "prompt": "Breezy French acoustic hip hop, intricate fingerpicking acoustic guitar, soft warm accordion pads, acoustic double bass, gentle wooden shaker, 78 BPM, effortless native fluency and relaxed walking cadence, instrumental background music, no vocals"
            },
            {
                "id": "jam_06",
                "filename": "jam_06_surprise_clarte.wav",
                "name": "Tiens, Donc!",
                "emotion_slug": "surprise_clarte",
                "matching_emotions": ["surprise & clarté", "surprise", "curiosité"],
                "bpm": 94,
                "style": "Bouncy French Jazzhop",
                "instrumentation": "Pizzicato strings, warm vibraphone, walking bass, light snare bounce",
                "prompt": "Bouncy French jazzhop, staccato pizzicato strings, warm shimmering vibraphone, walking double bass, light bouncy snare groove, 94 BPM, surprising discovery and instant French clarity, instrumental background music, no vocals"
            },
            {
                "id": "jam_07",
                "filename": "jam_07_bistro_groove.wav",
                "name": "Le Zinc",
                "emotion_slug": "bistro_groove",
                "matching_emotions": ["humour", "détente", "quotidien"],
                "bpm": 98,
                "style": "Funky Parisian Bistro Beat",
                "instrumentation": "Upright piano, muted trumpet, funky upright bass, finger snaps",
                "prompt": "Funky Parisian bistro beat, charming upright piano riff, subtle muted trumpet stabs, funky upright bass, crisp finger snaps, 98 BPM, authentic street-smart French expression, instrumental background music, no vocals"
            },
            {
                "id": "jam_08",
                "filename": "jam_08_aha_clarte.wav",
                "name": "Eurêka Parisien",
                "emotion_slug": "aha_clarte",
                "matching_emotions": ["aha moment & clarté", "clarté", "découverte"],
                "bpm": 88,
                "style": "Lush Chanson Lo-Fi",
                "instrumentation": "Lush electric piano, French nylon guitar, smooth bass, vinyl rain",
                "prompt": "Lush chanson lo-fi, warm electric piano chords, classical French nylon guitar, smooth melodic bass, vinyl rain texture, 88 BPM, satisfying moment of native understanding, instrumental background music, no vocals"
            },
            {
                "id": "jam_09",
                "filename": "jam_09_nocturne_chill.wav",
                "name": "Paris la Nuit",
                "emotion_slug": "nocturne_chill",
                "matching_emotions": ["mystère", "subtilité", "calme"],
                "bpm": 74,
                "style": "Nocturne French Lo-Fi",
                "instrumentation": "Intimate upright piano, soft cello drone, slow hip hop beat, ambient night sounds",
                "prompt": "Nocturne French lo-fi, intimate moody upright piano, soft cello drone, slow gentle boom-bap beat, distant Parisian street ambiance, 74 BPM, poetic nocturnal French vibe, instrumental background music, no vocals"
            },
            {
                "id": "jam_10",
                "filename": "jam_10_esprit_vif.wav",
                "name": "L'Esprit Vif",
                "emotion_slug": "esprit_vif",
                "matching_emotions": ["général", "dynamique", "motivation"],
                "bpm": 104,
                "style": "Upbeat French Indie Hop",
                "instrumentation": "Acoustic guitar strumming, bright accordion accents, punchy kick and clap, melodic bass",
                "prompt": "Upbeat French indie hop, crisp acoustic guitar rhythm, bright cheerful accordion accents, punchy kick and clap, melodic walking bassline, 104 BPM, lively witty French spirit, instrumental background music, no vocals"
            }
        ],
        "roleplay": [
            {
                "id": "jam_01",
                "filename": "jam_01_terrasse_dialogue.wav",
                "name": "À la Terrasse",
                "emotion_slug": "terrasse_dialogue",
                "matching_emotions": ["dialogue", "naturel & aisance", "conversation"],
                "bpm": 88,
                "style": "Bistro Terrace Lo-Fi",
                "instrumentation": "Warm French accordion, acoustic rhythm guitar, upright bass, soft brush drums",
                "prompt": "Bistro terrace lo-fi, melodic French accordion, acoustic rhythm guitar, smooth upright bass, soft brush drums, 88 BPM, authentic cafe dialogue and natural French conversation, instrumental background music, no vocals"
            },
            {
                "id": "jam_02",
                "filename": "jam_02_repartie_motivee.wav",
                "name": "Bonne Répartie",
                "emotion_slug": "repartie_motivee",
                "matching_emotions": ["curiosité & humour", "surprise & humour", "humour"],
                "bpm": 100,
                "style": "French Swing Hop",
                "instrumentation": "Pizzicato strings, Manouche guitar, bouncy bass, snap percussion",
                "prompt": "French swing hop, snappy pizzicato strings, Manouche gypsy guitar, bouncy bassline, rhythmic snaps, 100 BPM, quick witty French banter and playful roleplay, instrumental background music, no vocals"
            },
            {
                "id": "jam_03",
                "filename": "jam_03_hesitation_novice.wav",
                "name": "Le Débutant",
                "emotion_slug": "hesitation_novice",
                "matching_emotions": ["hésitation", "novice", "subtilité", "tension"],
                "bpm": 82,
                "style": "Minimal French Lo-Fi",
                "instrumentation": "Soft muted piano, hesitant clock-like woodblock, gentle cello, light vinyl",
                "prompt": "Minimal French lo-fi, soft muted piano, hesitant ticking woodblock, gentle cello notes, vinyl crackle, 82 BPM, humorous beginner hesitation and tension, instrumental background music, no vocals"
            },
            {
                "id": "jam_04",
                "filename": "jam_04_soutien_ami.wav",
                "name": "L'Ami Bienveillant",
                "emotion_slug": "soutien_ami",
                "matching_emotions": ["clarté & confiance", "bienveillance", "soutien"],
                "bpm": 78,
                "style": "Warm Chanson Acoustic",
                "instrumentation": "Acoustic guitar arpeggios, sweet accordion, deep warm bass, gentle rimshot",
                "prompt": "Warm chanson acoustic chill, fingerstyle acoustic guitar arpeggios, sweet accordion pad, deep warm acoustic bass, gentle rimshot, 78 BPM, supportive friendly guidance and warmth, instrumental background music, no vocals"
            },
            {
                "id": "jam_05",
                "filename": "jam_05_deblocage_magique.wav",
                "name": "Le Déclic",
                "emotion_slug": "deblocage_magique",
                "matching_emotions": ["aha moment & clarté", "aha moment & précision", "déclic"],
                "bpm": 92,
                "style": "Bright French Chillhop",
                "instrumentation": "Electric Rhodes keys, glockenspiel sparkle, punchy bass, crisp boom-bap",
                "prompt": "Bright French chillhop, warm electric Rhodes keys, subtle glockenspiel sparkle, punchy melodic bass, crisp boom-bap drums, 92 BPM, sudden French realization and shared triumph, instrumental background music, no vocals"
            },
            {
                "id": "jam_06",
                "filename": "jam_06_marchand_russe.wav",
                "name": "Au Marché",
                "emotion_slug": "marchand_russe",
                "matching_emotions": ["quotidien", "rue", "aisance"],
                "bpm": 96,
                "style": "Upbeat French Market Groove",
                "instrumentation": "Accordion chops, acoustic bass walk, tambourine, rhythmic guitar",
                "prompt": "Upbeat French market groove, lively accordion chops, walking acoustic bass, subtle tambourine, rhythmic acoustic guitar, 96 BPM, bustling Parisian street negotiation and daily life, instrumental background music, no vocals"
            },
            {
                "id": "jam_07",
                "filename": "jam_07_soir_detendu.wav",
                "name": "Apéro Entre Amis",
                "emotion_slug": "soir_detendu",
                "matching_emotions": ["clarté & repères", "détente", "apéro"],
                "bpm": 80,
                "style": "Relaxed French Lo-Fi",
                "instrumentation": "Upright piano, soft acoustic guitar, mellow double bass, light vinyl ambiance",
                "prompt": "Relaxed French lo-fi, gentle upright piano chords, soft acoustic guitar strums, mellow double bass, vinyl ambiance, 80 BPM, cozy evening apéro and friendly relaxed vibes, instrumental background music, no vocals"
            },
            {
                "id": "jam_08",
                "filename": "jam_08_surpris_amusant.wav",
                "name": "C'est Pas Vrai?!",
                "emotion_slug": "surpris_amusant",
                "matching_emotions": ["surprise & clarté", "surprise & humour", "surprise"],
                "bpm": 98,
                "style": "Playful French Funk-Hop",
                "instrumentation": "Vibraphone stabs, funky slap bass, saxophone riff, tight drums",
                "prompt": "Playful French funk-hop, vibraphone stabs, funky slap bass, humorous soprano saxophone accent, tight drums, 98 BPM, comical French surprise and amusing plot twist, instrumental background music, no vocals"
            },
            {
                "id": "jam_09",
                "filename": "jam_09_optimisme_paris.wav",
                "name": "Un Matin à Paris",
                "emotion_slug": "optimisme_paris",
                "matching_emotions": ["confiance & curiosité", "optimisme", "motivation"],
                "bpm": 104,
                "style": "Sunny Chanson Pop",
                "instrumentation": "Bright acoustic guitar, cheerful accordion, driving kick and handclaps, warm bass",
                "prompt": "Sunny chanson pop beat, bright acoustic guitar, cheerful accordion melody, driving kick and handclaps, warm walking bass, 104 BPM, optimistic morning energy and confident French speaking, instrumental background music, no vocals"
            },
            {
                "id": "jam_10",
                "filename": "jam_10_chute_parfaite.wav",
                "name": "Le Mot de la Fin",
                "emotion_slug": "chute_parfaite",
                "matching_emotions": ["payoff", "chute", "clôture", "confiance"],
                "bpm": 90,
                "style": "Triumphant Chanson Chill",
                "instrumentation": "Rich accordion crescendo, melodic piano, punchy bass groove, full drums",
                "prompt": "Triumphant chanson chill beat, rich warm accordion chords, melodic acoustic piano, punchy bass groove, full clean drums, 90 BPM, perfect punchline delivery and satisfying conclusion, instrumental background music, no vocals"
            }
        ],
        "game": [
            {
                "id": "jam_01",
                "filename": "jam_01_defi_chronometre.wav",
                "name": "Le Chrono Tourne",
                "emotion_slug": "defi_chronometre",
                "matching_emotions": ["urgent", "chronomètre", "pression", "défi"],
                "bpm": 116,
                "style": "French Suspense Beat",
                "instrumentation": "Ticking clock percussion, dramatic accordion swells, deep sub-bass, driving snare",
                "prompt": "French suspense beat, realistic ticking clock rhythm, dramatic subtle accordion swells, deep sub-bass, driving snare, 116 BPM, urgent French quiz countdown and suspense, instrumental background music, no vocals"
            },
            {
                "id": "jam_02",
                "filename": "jam_02_jeu_tele.wav",
                "name": "Le Grand Jeu",
                "emotion_slug": "jeu_tele",
                "matching_emotions": ["jeu télé", "excitation", "énergie"],
                "bpm": 110,
                "style": "Funky French Game Show",
                "instrumentation": "Punchy funk bass, rhythmic electric piano, bright brass stabs, snappy drums",
                "prompt": "Funky French game show groove, punchy bassline, rhythmic electric piano, bright brass stabs, snappy upbeat drums, 110 BPM, exciting French trivia show energy, instrumental background music, no vocals"
            },
            {
                "id": "jam_03",
                "filename": "jam_03_enigme_francaise.wav",
                "name": "L'Énigme",
                "emotion_slug": "enigme_francaise",
                "matching_emotions": ["énigme", "concentration", "mystère"],
                "bpm": 96,
                "style": "Inquisitive Parisian Hop",
                "instrumentation": "Marimba, muted accordion, warm acoustic bass, finger snap rhythm",
                "prompt": "Inquisitive Parisian hip hop, subtle marimba arpeggio, muted accordion chords, warm acoustic bass, finger snap rhythm, 96 BPM, intellectual French puzzle solving and focus, instrumental background music, no vocals"
            },
            {
                "id": "jam_04",
                "filename": "jam_04_retro_bistrot.wav",
                "name": "Quiz au Bistrot",
                "emotion_slug": "retro_bistrot",
                "matching_emotions": ["bistrot", "ludique", "amusant"],
                "bpm": 104,
                "style": "Playful Chanson Swing",
                "instrumentation": "Acoustic Manouche guitar, clarinet, walking bass, brush snare",
                "prompt": "Playful chanson swing, bouncy acoustic Manouche guitar, charming clarinet, walking upright bass, brush snare, 104 BPM, cheerful bistro trivia challenge, instrumental background music, no vocals"
            },
            {
                "id": "jam_05",
                "filename": "jam_05_suspense_reponse.wav",
                "name": "Trois Secondes!",
                "emotion_slug": "suspense_reponse",
                "matching_emotions": ["suspense", "pression", "attente"],
                "bpm": 102,
                "style": "Cinematic French Tension",
                "instrumentation": "Pulsing bass, staccato cello, ticking percussion, atmospheric tension pad",
                "prompt": "Cinematic French tension, pulsing electronic bass, staccato cello plucks, ticking countdown percussion, atmospheric pad, 102 BPM, tense quiz countdown before the reveal, instrumental background music, no vocals"
            },
            {
                "id": "jam_06",
                "filename": "jam_06_bravo_victoire.wav",
                "name": "Bonne Réponse!",
                "emotion_slug": "bravo_victoire",
                "matching_emotions": ["victoire", "bravo", "triomphe"],
                "bpm": 112,
                "style": "Celebratory French Pop-Funk",
                "instrumentation": "Brass fanfare, upbeat accordion, celebratory claps, driving bass",
                "prompt": "Celebratory French pop-funk, brass fanfare stabs, upbeat accordion melody, celebratory handclaps, driving punchy bassline, 112 BPM, triumphant celebration of correct answer, instrumental background music, no vocals"
            },
            {
                "id": "jam_07",
                "filename": "jam_07_duel_de_mots.wav",
                "name": "Duel de Mots",
                "emotion_slug": "duel_de_mots",
                "matching_emotions": ["compétition", "rapidité", "duel"],
                "bpm": 118,
                "style": "Fast French Electro-Swing",
                "instrumentation": "Electro-swing beat, vintage accordion sample, energetic bassline, crisp drums",
                "prompt": "Fast French electro-swing beat, vintage accordion sample, energetic modern bassline, crisp driving drums, 118 BPM, rapid-fire vocabulary duel and high-energy challenge, instrumental background music, no vocals"
            },
            {
                "id": "jam_08",
                "filename": "jam_08_piege_grammaire.wav",
                "name": "Le Piège",
                "emotion_slug": "piege_grammaire",
                "matching_emotions": ["piège", "astuce", "subtilité"],
                "bpm": 94,
                "style": "Sneaky Detective Lo-Fi",
                "instrumentation": "Pizzicato strings, sneaky bass, vibraphone notes, brushed hi-hats",
                "prompt": "Sneaky detective lo-fi, cheeky pizzicato strings, sneaky walking bass, subtle vibraphone notes, brushed hi-hats, 94 BPM, tricky French grammar trap and sneaky test, instrumental background music, no vocals"
            },
            {
                "id": "jam_09",
                "filename": "jam_09_vitesse_eclair.wav",
                "name": "Vitesse Éclair",
                "emotion_slug": "vitesse_eclair",
                "matching_emotions": ["vitesse", "réflexe", "rapide"],
                "bpm": 122,
                "style": "Driving French Nu-Disco",
                "instrumentation": "Four-on-the-floor beat, disco rhythm guitar, French house synth, driving bass",
                "prompt": "Driving French nu-disco, energetic four-on-the-floor beat, funk disco rhythm guitar, filtered French house synth, driving bass, 122 BPM, lightning fast language reflexes, instrumental background music, no vocals"
            },
            {
                "id": "jam_10",
                "filename": "jam_10_expert_natif.wav",
                "name": "Niveau Natif",
                "emotion_slug": "expert_natif",
                "matching_emotions": ["expert", "natif", "confiance"],
                "bpm": 100,
                "style": "Bouncy French Chill-Funk",
                "instrumentation": "Xylophone, French accordion accents, bouncy bass, tight rimshot",
                "prompt": "Bouncy French chill-funk, bright xylophone melody, French accordion accents, bouncy groove bass, tight rimshot, 100 BPM, satisfying test proving true native mastery, instrumental background music, no vocals"
            }
        ],
        "fun_facts": [
            {
                "id": "jam_01",
                "filename": "jam_01_curiosite_ludique.wav",
                "name": "Curiosité Française",
                "emotion_slug": "curiosite_ludique",
                "matching_emotions": ["amusement & surprise", "curiosité", "découverte"],
                "bpm": 86,
                "style": "Charming French Marimba Hop",
                "instrumentation": "Marimba, subtle accordion, acoustic double bass, light shaker",
                "prompt": "Charming French marimba hop, wooden marimba melody, subtle accordion chords, warm acoustic double bass, light shaker, 86 BPM, delightful curiosity and surprising French facts, instrumental background music, no vocals"
            },
            {
                "id": "jam_02",
                "filename": "jam_02_mystere_etymologie.wav",
                "name": "Les Origines Secrètes",
                "emotion_slug": "mystere_etymologie",
                "matching_emotions": ["mystère & découverte", "histoire", "étymologie"],
                "bpm": 80,
                "style": "Atmospheric Chanson Mystery",
                "instrumentation": "Muted harp, nostalgic piano, deep warm bass, vinyl crackle",
                "prompt": "Atmospheric chanson mystery, muted acoustic harp, nostalgic piano chords, deep warm bass, vinyl crackle, 80 BPM, ancient French language origins and intriguing mystery, instrumental background music, no vocals"
            },
            {
                "id": "jam_03",
                "filename": "jam_03_defi_ludique_facts.wav",
                "name": "Le Défi des Nombres",
                "emotion_slug": "defi_ludique_facts",
                "matching_emotions": ["défi ludique & curiosité", "défi", "chiffres"],
                "bpm": 98,
                "style": "Quirky French Jazzhop",
                "instrumentation": "Pizzicato strings, vibraphone, Manouche acoustic guitar, crisp finger snaps",
                "prompt": "Quirky French jazzhop, energetic pizzicato strings, cheerful vibraphone, Manouche acoustic guitar, crisp finger snaps, 98 BPM, quirky fun facts about French counting and eccentric rules, instrumental background music, no vocals"
            },
            {
                "id": "jam_04",
                "filename": "jam_04_humour_incredulite.wav",
                "name": "Pas Possible!",
                "emotion_slug": "humour_incredulite",
                "matching_emotions": ["humour & incrédulité", "incrédulité", "humour"],
                "bpm": 94,
                "style": "Comedic French Bistro Beat",
                "instrumentation": "Upright piano, muted trumpet wah, slap bass, funny brush snare",
                "prompt": "Comedic French bistro beat, lively upright piano, muted trumpet wah-wah, bouncy slap bass, funny brush snare, 94 BPM, hilarious disbelief and weird linguistic truths, instrumental background music, no vocals"
            },
            {
                "id": "jam_05",
                "filename": "jam_05_surprise_fascination.wav",
                "name": "Fascination Totale",
                "emotion_slug": "surprise_fascination",
                "matching_emotions": ["surprise & fascination", "fascination", "incroyable"],
                "bpm": 88,
                "style": "Cinematic French Chillhop",
                "instrumentation": "Lush accordion pad, grand piano, warm cello swell, modern boom-bap",
                "prompt": "Cinematic French chillhop, lush accordion pad, grand piano chords, warm cello swell, modern boom-bap drums, 88 BPM, breathtaking fascination with the French language, instrumental background music, no vocals"
            },
            {
                "id": "jam_06",
                "filename": "jam_06_terroir_regions.wav",
                "name": "Nos Régions",
                "emotion_slug": "terroir_regions",
                "matching_emotions": ["régions", "accent", "culture", "chocolatine"],
                "bpm": 84,
                "style": "Warm Folkloric Lo-Fi",
                "instrumentation": "Acoustic nylon guitar, rustic accordion, soft hand percussion, warm bass",
                "prompt": "Warm folkloric lo-fi, acoustic nylon guitar, rustic French accordion melody, soft hand percussion, warm round bass, 84 BPM, regional French diversity and cultural debates, instrumental background music, no vocals"
            },
            {
                "id": "jam_07",
                "filename": "jam_07_academie_mythe.wav",
                "name": "L'Académie Débunkée",
                "emotion_slug": "academie_mythe",
                "matching_emotions": ["mythe", "académie", "débunkage"],
                "bpm": 96,
                "style": "Cheeky French Detective",
                "instrumentation": "Wah guitar, walking bass, harpsichord accents, ride cymbal",
                "prompt": "Cheeky French detective hop, rhythmic wah-wah guitar, walking double bass, subtle harpsichord accents, smooth ride cymbal, 96 BPM, debunking French language myths and official rules, instrumental background music, no vocals"
            },
            {
                "id": "jam_08",
                "filename": "jam_08_record_extreme.wav",
                "name": "Les Mots Géants",
                "emotion_slug": "record_extreme",
                "matching_emotions": ["record", "extrême", "longueur"],
                "bpm": 110,
                "style": "Energetic French Electro-Hop",
                "instrumentation": "Synthesizer arpeggios, accordion riffs, driving electronic drums, deep bass",
                "prompt": "Energetic French electro-hop, synthesizer arpeggios, chopped accordion riffs, driving electronic drums, deep bassline, 110 BPM, incredible records and extreme French vocabulary, instrumental background music, no vocals"
            },
            {
                "id": "jam_09",
                "filename": "jam_09_anecdote_douce.wav",
                "name": "La Petite Histoire",
                "emotion_slug": "anecdote_douce",
                "matching_emotions": ["anecdote", "doux", "histoire"],
                "bpm": 76,
                "style": "Cozy Chanson Lo-Fi",
                "instrumentation": "Vintage upright piano, subtle accordion, vinyl crackle, gentle brush beat",
                "prompt": "Cozy chanson lo-fi, vintage upright piano melody, subtle warm accordion, vinyl crackle, gentle brush beat, 76 BPM, charming storytelling and fascinating historical anecdotes, instrumental background music, no vocals"
            },
            {
                "id": "jam_10",
                "filename": "jam_10_lecon_inoubliable.wav",
                "name": "Le Saviez-Vous?",
                "emotion_slug": "lecon_inoubliable",
                "matching_emotions": ["leçon", "mémorable", "découverte"],
                "bpm": 92,
                "style": "Inspiring French Acoustic Chill",
                "instrumentation": "Bright grand piano, accordion harmonies, melodic bass, crisp claps",
                "prompt": "Inspiring French acoustic chill, bright grand piano melody, accordion harmonies, melodic warm bass, crisp claps, 92 BPM, memorable educational discovery and delightful takeaway, instrumental background music, no vocals"
            }
        ]
    },
    "spanish": {
        "expression": [
            {
                "id": "jam_01",
                "filename": "jam_01_soltura_flamenca.wav",
                "name": "Soltura y Compás",
                "emotion_slug": "soltura_flamenca",
                "matching_emotions": ["naturalidad & soltura", "soltura", "naturalidad", "aisance"],
                "bpm": 90,
                "style": "Flamenco Lo-Fi Chill",
                "instrumentation": "Spanish nylon flamenco guitar, cajón groove, warm bass, palmas (handclaps)",
                "prompt": "Flamenco lo-fi chill beat, Spanish nylon flamenco guitar rasgueado, warm cajón groove, smooth bass, subtle palmas handclaps, 90 BPM, natural Spanish flair and fluent ease, instrumental background music, no vocals"
            },
            {
                "id": "jam_02",
                "filename": "jam_02_aha_confianza.wav",
                "name": "¡Ya Lo Tengo!",
                "emotion_slug": "aha_confianza",
                "matching_emotions": ["aha moment & confianza", "confianza", "claridad & confianza"],
                "bpm": 88,
                "style": "Latin Neo-Soul Chillhop",
                "instrumentation": "Warm electric piano, melodic Spanish nylon guitar, groovy bass, crisp shaker",
                "prompt": "Latin neo-soul chillhop, warm electric piano chords, melodic Spanish nylon guitar leads, groovy Latin bassline, crisp wooden shaker, 88 BPM, confident breakthrough and instant clarity, instrumental background music, no vocals"
            },
            {
                "id": "jam_03",
                "filename": "jam_03_curiosidad_humor.wav",
                "name": "Chiste Callejero",
                "emotion_slug": "curiosidad_humor",
                "matching_emotions": ["curiosidad & humor", "curiosidad & diversión", "humor", "diversión"],
                "bpm": 98,
                "style": "Playful Rumba Hop",
                "instrumentation": "Bouncy nylon guitar rumba strum, playful marimba, acoustic bass, bongo drums",
                "prompt": "Playful rumba hip hop, bouncy nylon guitar rumba strumming, cheerful marimba melody, warm acoustic bass, bongo drums, 98 BPM, witty Hispanic humor and cheerful curiosity, instrumental background music, no vocals"
            },
            {
                "id": "jam_04",
                "filename": "jam_04_sorpresa_claridad.wav",
                "name": "¡No Me Digas!",
                "emotion_slug": "sorpresa_claridad",
                "matching_emotions": ["sorpresa & claridad", "sorpresa & curiosidad", "sorpresa"],
                "bpm": 94,
                "style": "Bouncy Latin Jazzhop",
                "instrumentation": "Pizzicato strings, Latin piano montuno, upright bass, crisp rimshot",
                "prompt": "Bouncy Latin jazzhop, lively pizzicato strings, light Latin piano montuno chords, walking upright bass, crisp rimshot, 94 BPM, surprising colloquial revelation and clarity, instrumental background music, no vocals"
            },
            {
                "id": "jam_05",
                "filename": "jam_05_calidez_tarde.wav",
                "name": "Tarde de Sol",
                "emotion_slug": "calidez_tarde",
                "matching_emotions": ["calidez", "claridad & precisión", "precisión"],
                "bpm": 80,
                "style": "Sun-Drenched Spanish Chill",
                "instrumentation": "Acoustic nylon guitar arpeggios, warm Rhodes piano, deep melodic bass, gentle ocean shaker",
                "prompt": "Sun-drenched Spanish chill, gentle acoustic nylon guitar arpeggios, warm Fender Rhodes chords, deep melodic bass, soft ocean shaker, 80 BPM, warm Mediterranean breeze and relaxed precision, instrumental background music, no vocals"
            },
            {
                "id": "jam_06",
                "filename": "jam_06_aha_precision.wav",
                "name": "Al Pie de la Letra",
                "emotion_slug": "aha_precision",
                "matching_emotions": ["aha moment & precisión", "precisión & soltura", "precisión"],
                "bpm": 86,
                "style": "Sophisticated Bossa Chill",
                "instrumentation": "Nylon bossa guitar chords, subtle flute melody, acoustic double bass, light brushes",
                "prompt": "Sophisticated bossa nova chill, nylon bossa guitar chords, subtle warm flute melody, acoustic double bass, light brush snare, 86 BPM, precise native understanding and effortless flow, instrumental background music, no vocals"
            },
            {
                "id": "jam_07",
                "filename": "jam_07_ritmo_urbano.wav",
                "name": "Onda Urbana",
                "emotion_slug": "ritmo_urbano",
                "matching_emotions": ["urbano", "calle", "coloquial"],
                "bpm": 92,
                "style": "Urban Latin Lo-Fi",
                "instrumentation": "Muted electric guitar, 808 sub bass, tight reggaeton-infused lo-fi drums, vinyl hiss",
                "prompt": "Urban Latin lo-fi, muted rhythmic electric guitar, deep 808 sub bass, relaxed lo-fi boom-bap with subtle Latin swing, vinyl hiss, 92 BPM, modern urban street slang and youth vibes, instrumental background music, no vocals"
            },
            {
                "id": "jam_08",
                "filename": "jam_08_fiesta_amigos.wav",
                "name": "Entre Compadres",
                "emotion_slug": "fiesta_amigos",
                "matching_emotions": ["diversión", "amigos", "alegría"],
                "bpm": 104,
                "style": "Upbeat Spanish Rumba Pop",
                "instrumentation": "Acoustic guitars, handclaps, lively bass, bright percussion",
                "prompt": "Upbeat Spanish rumba pop beat, energetic acoustic guitars, festive handclaps, lively walking bassline, bright Latin percussion, 104 BPM, joyful camaraderie and lively native chatter, instrumental background music, no vocals"
            },
            {
                "id": "jam_09",
                "filename": "jam_09_misterio_origen.wav",
                "name": "Dicho Antiguo",
                "emotion_slug": "misterio_origen",
                "matching_emotions": ["curiosidad", "misterio", "historia"],
                "bpm": 78,
                "style": "Mysterious Spanish Acoustic",
                "instrumentation": "Spanish guitar tremolo, subtle cello, deep sub, slow boom-bap",
                "prompt": "Mysterious Spanish acoustic lo-fi, Spanish guitar tremolo melody, subtle dark cello, deep sub bass, slow boom-bap rhythm, 78 BPM, intriguing historic idiom and mysterious curiosity, instrumental background music, no vocals"
            },
            {
                "id": "jam_10",
                "filename": "jam_10_maestria_nativa.wav",
                "name": "Hablando Como Nativo",
                "emotion_slug": "maestria_nativa",
                "matching_emotions": ["general", "maestría", "confianza"],
                "bpm": 96,
                "style": "Triumphant Spanish Chillhop",
                "instrumentation": "Grand piano montuno, flamenco guitar flourishes, punchy bass, driving drums",
                "prompt": "Triumphant Spanish chillhop, grand piano montuno chords, flamenco guitar flourishes, punchy driving bass, crisp full drums, 96 BPM, true native Spanish mastery and satisfying triumph, instrumental background music, no vocals"
            }
        ],
        "roleplay": [
            {
                "id": "jam_01",
                "filename": "jam_01_charla_callejera.wav",
                "name": "Charla en la Plaza",
                "emotion_slug": "charla_callejera",
                "matching_emotions": ["dialogue", "conversación", "naturalidad & soltura"],
                "bpm": 92,
                "style": "Acoustic Plaza Lo-Fi",
                "instrumentation": "Nylon guitar strums, cajón percussion, melodic bass, soft shaker",
                "prompt": "Acoustic plaza lo-fi, rhythmic nylon guitar strums, warm cajón percussion, melodic electric bass, soft shaker, 92 BPM, lively conversational roleplay on a Spanish plaza, instrumental background music, no vocals"
            },
            {
                "id": "jam_02",
                "filename": "jam_02_broma_picaresca.wav",
                "name": "La Picaresca",
                "emotion_slug": "broma_picaresca",
                "matching_emotions": ["curiosidad & humor", "curiosidad & diversión", "humor"],
                "bpm": 100,
                "style": "Playful Spanish Funk-Hop",
                "instrumentation": "Staccato Spanish guitar, funky bass, clavinet, rhythmic palmas",
                "prompt": "Playful Spanish funk-hop, staccato nylon guitar plucks, funky groovy bass, clavinet accents, rhythmic palmas handclaps, 100 BPM, humorous Spanish banter and mischievous jokes, instrumental background music, no vocals"
            },
            {
                "id": "jam_03",
                "filename": "jam_03_apuro_novato.wav",
                "name": "En Apuros",
                "emotion_slug": "apuro_novato",
                "matching_emotions": ["tensión", "apuro", "novato", "duda"],
                "bpm": 84,
                "style": "Minimal Spanish Suspense Lo-Fi",
                "instrumentation": "Muted guitar picking, ticking cajón rim, cello drone, vinyl hiss",
                "prompt": "Minimal Spanish suspense lo-fi, muted nylon guitar picking, ticking cajón rim click, subtle cello drone, vinyl hiss, 84 BPM, awkward funny dilemma and beginner hesitation, instrumental background music, no vocals"
            },
            {
                "id": "jam_04",
                "filename": "jam_04_apoyo_amigo.wav",
                "name": "El Buen Amigo",
                "emotion_slug": "apoyo_amigo",
                "matching_emotions": ["claridad & confianza", "apoyo", "amistad"],
                "bpm": 80,
                "style": "Heartwarming Latin Acoustic",
                "instrumentation": "Warm nylon guitar arpeggios, gentle Rhodes, deep melodic bass, soft brushes",
                "prompt": "Heartwarming Latin acoustic chill, warm nylon guitar arpeggios, gentle Fender Rhodes piano, deep melodic bass, soft brush drums, 80 BPM, supportive friend encouraging and reassuring, instrumental background music, no vocals"
            },
            {
                "id": "jam_05",
                "filename": "jam_05_revelacion_rapida.wav",
                "name": "¡Eso Era!",
                "emotion_slug": "revelacion_rapida",
                "matching_emotions": ["aha moment & confianza", "aha moment & soltura", "revelación"],
                "bpm": 94,
                "style": "Bright Latin Chillhop",
                "instrumentation": "Bright nylon guitar chords, piano montuno, punchy bass, crisp snaps",
                "prompt": "Bright Latin chillhop, lively nylon guitar chords, uplifting piano montuno, punchy bassline, crisp finger snaps, 94 BPM, joyful moment of mutual understanding in dialogue, instrumental background music, no vocals"
            },
            {
                "id": "jam_06",
                "filename": "jam_06_regateo_mercado.wav",
                "name": "Regateo en el Mercado",
                "emotion_slug": "regateo_mercado",
                "matching_emotions": ["calle", "regateo", "coloquial"],
                "bpm": 98,
                "style": "Breezy Rumba-Hop",
                "instrumentation": "Rhythmic rumba guitar, bongo groove, walking bass, energetic claps",
                "prompt": "Breezy rumba-hop, rhythmic Spanish rumba guitar, bouncy bongo groove, walking bass, energetic claps, 98 BPM, street smart Spanish negotiation and market dialogue, instrumental background music, no vocals"
            },
            {
                "id": "jam_07",
                "filename": "jam_07_tapas_bar.wav",
                "name": "De Tapas",
                "emotion_slug": "tapas_bar",
                "matching_emotions": ["détente", "relajación", "amigos"],
                "bpm": 76,
                "style": "Cozy Tapas Bar Lo-Fi",
                "instrumentation": "Gentle classical guitar, upright bass, soft shaker, cozy room warmth",
                "prompt": "Cozy tapas bar lo-fi, gentle classical guitar melody, upright acoustic bass, soft shaker, cozy bar atmosphere, 76 BPM, relaxed evening with friends eating tapas, instrumental background music, no vocals"
            },
            {
                "id": "jam_08",
                "filename": "jam_08_asombro_comico.wav",
                "name": "¡Qué Barbaridad!",
                "emotion_slug": "asombro_comico",
                "matching_emotions": ["sorpresa & claridad", "sorpresa", "asombro"],
                "bpm": 102,
                "style": "Playful Latin Funk",
                "instrumentation": "Vibraphone stabs, Spanish guitar accents, slap bass, punchy drums",
                "prompt": "Playful Latin funk, shimmering vibraphone stabs, Spanish guitar accents, funky slap bass, punchy drums, 102 BPM, hilarious comedic surprise in dialogue, instrumental background music, no vocals"
            },
            {
                "id": "jam_09",
                "filename": "jam_09_optimismo_sol.wav",
                "name": "Mañana de Fiesta",
                "emotion_slug": "optimismo_sol",
                "matching_emotions": ["confianza", "optimismo", "energía"],
                "bpm": 106,
                "style": "Sunny Spanish Pop-Hop",
                "instrumentation": "Strummed acoustic guitar, lively hand percussion, driving kick, warm bass",
                "prompt": "Sunny Spanish pop-hop, bright strummed acoustic guitar, lively hand percussion, driving warm kick, melodic bass, 106 BPM, vibrant sunny optimism and confident communication, instrumental background music, no vocals"
            },
            {
                "id": "jam_10",
                "filename": "jam_10_remate_perfecto.wav",
                "name": "El Remate",
                "emotion_slug": "remate_perfecto",
                "matching_emotions": ["payoff", "remate", "confianza"],
                "bpm": 92,
                "style": "Triumphant Flamenco Fusion",
                "instrumentation": "Flamenco guitar crescendo, grand piano, punchy Latin drums, full bass",
                "prompt": "Triumphant flamenco fusion, passionate flamenco guitar crescendo, grand piano chords, punchy Latin drums, full warm bass, 92 BPM, punchy punchline finish and dialogue victory, instrumental background music, no vocals"
            }
        ],
        "game": [
            {
                "id": "jam_01",
                "filename": "jam_01_reloj_urgente.wav",
                "name": "Cuenta Regresiva",
                "emotion_slug": "reloj_urgente",
                "matching_emotions": ["urgente", "cuenta regresiva", "presión", "reto"],
                "bpm": 118,
                "style": "Spanish Suspense Trap-Hop",
                "instrumentation": "Ticking clock palmas, 808 sub bass, dramatic nylon guitar staccato, driving snare",
                "prompt": "Spanish suspense trap-hop beat, ticking clock percussion mixed with fast palmas, deep 808 sub bass, dramatic nylon guitar staccato plucks, driving snare, 118 BPM, urgent trivia countdown and high-pressure game, instrumental background music, no vocals"
            },
            {
                "id": "jam_02",
                "filename": "jam_02_concurso_latino.wav",
                "name": "¡A Jugar!",
                "emotion_slug": "concurso_latino",
                "matching_emotions": ["concurso", "emoción", "energía"],
                "bpm": 112,
                "style": "Funky Latin Game Show",
                "instrumentation": "Punchy Latin bassline, electric piano montuno, brass hits, snappy drums",
                "prompt": "Funky Latin game show groove, punchy syncopated bassline, electric piano montuno, brass hits, snappy upbeat drums, 112 BPM, high-energy Spanish trivia game excitement, instrumental background music, no vocals"
            },
            {
                "id": "jam_03",
                "filename": "jam_03_reto_mental.wav",
                "name": "Reto Mental",
                "emotion_slug": "reto_mental",
                "matching_emotions": ["concentración", "reto", "claridad"],
                "bpm": 96,
                "style": "Focus Marimba Hop",
                "instrumentation": "Marimba arpeggios, nylon guitar accents, warm sub bass, tight rimshot",
                "prompt": "Focus marimba hip hop, intricate marimba arpeggios, subtle nylon guitar accents, warm sub bass, tight crisp rimshot, 96 BPM, mental puzzle solving and intellectual clarity, instrumental background music, no vocals"
            },
            {
                "id": "jam_04",
                "filename": "jam_04_arcade_latino.wav",
                "name": "Trivia Arcade",
                "emotion_slug": "arcade_latino",
                "matching_emotions": ["arcade", "lúdico", "reto divertido"],
                "bpm": 110,
                "style": "Retro Latin Electro-Funk",
                "instrumentation": "8-bit synths, Latin percussion, funky slap bass, punchy kick",
                "prompt": "Retro Latin electro-funk, 8-bit chiptune synths, Latin bongo percussion, funky slap bass, punchy kick, 110 BPM, playful retro arcade game trivia, instrumental background music, no vocals"
            },
            {
                "id": "jam_05",
                "filename": "jam_05_segundos_finales.wav",
                "name": "Últimos Segundos",
                "emotion_slug": "segundos_finales",
                "matching_emotions": ["tensión", "suspenso", "presión"],
                "bpm": 104,
                "style": "Dramatic Flamenco Suspense",
                "instrumentation": "Pulsing synth bass, staccato flamenco guitar, ticking percussion, riser",
                "prompt": "Dramatic flamenco suspense, pulsing synth bass, staccato flamenco guitar plucks, ticking clock percussion, rising tension pad, 104 BPM, intense countdown before revealing the answer, instrumental background music, no vocals"
            },
            {
                "id": "jam_06",
                "filename": "jam_06_acierto_total.wav",
                "name": "¡Respuesta Correcta!",
                "emotion_slug": "acierto_total",
                "matching_emotions": ["triunfo", "acierto", "victoria"],
                "bpm": 114,
                "style": "Triumphant Latin Pop-Funk",
                "instrumentation": "Bright Latin brass, celebratory piano, driving bass, festive percussion",
                "prompt": "Triumphant Latin pop-funk, bright celebratory brass fanfare, celebratory piano chords, driving bass, festive percussion and claps, 114 BPM, exciting victory and celebration of the right answer, instrumental background music, no vocals"
            },
            {
                "id": "jam_07",
                "filename": "jam_07_velocidad_total.wav",
                "name": "Mente Rápida",
                "emotion_slug": "velocidad_total",
                "matching_emotions": ["rapidez", "velocidad", "reto rápido"],
                "bpm": 120,
                "style": "Energetic Latin Nu-Disco",
                "instrumentation": "Four-on-the-floor kick, rhythm guitar, bright synths, driving bass",
                "prompt": "Energetic Latin nu-disco, driving four-on-the-floor kick, rhythmic Latin guitar, bright shimmering synthesizers, driving bassline, 120 BPM, rapid-fire quick language reflexes, instrumental background music, no vocals"
            },
            {
                "id": "jam_08",
                "filename": "jam_08_trampa_gramatical.wav",
                "name": "La Trampa",
                "emotion_slug": "trampa_gramatical",
                "matching_emotions": ["trampa", "misterio", "duda"],
                "bpm": 94,
                "style": "Sneaky Detective Latin Hop",
                "instrumentation": "Pizzicato strings, upright bass, Spanish guitar accents, brushed snare",
                "prompt": "Sneaky detective Latin hip hop, mischievous pizzicato strings, walking upright acoustic bass, subtle Spanish guitar accents, brushed snare, 94 BPM, tricky language trap and detective test, instrumental background music, no vocals"
            },
            {
                "id": "jam_09",
                "filename": "jam_09_duelo_titanes.wav",
                "name": "Duelo de Sabios",
                "emotion_slug": "duelo_titanes",
                "matching_emotions": ["competencia", "duelo", "desafío"],
                "bpm": 116,
                "style": "High-Energy Breakbeat Rumba",
                "instrumentation": "Breakbeat drums, aggressive Latin bass, Spanish guitar riffs, claps",
                "prompt": "High-energy breakbeat rumba, breakbeat drum groove, aggressive Latin bassline, fiery Spanish guitar riffs, punchy claps, 116 BPM, high-stakes competition and championship trivia showdown, instrumental background music, no vocals"
            },
            {
                "id": "jam_10",
                "filename": "jam_10_maestro_quiz.wav",
                "name": "Nivel Maestro",
                "emotion_slug": "maestro_quiz",
                "matching_emotions": ["maestro", "experto", "satisfacción"],
                "bpm": 102,
                "style": "Bouncy Latin Chill-Funk",
                "instrumentation": "Marimba melody, Spanish guitar chords, bouncy bass, tight rimshot",
                "prompt": "Bouncy Latin chill-funk, bright marimba melody, Spanish nylon guitar chords, bouncy groovy bass, tight rimshot, 102 BPM, satisfying test proving true native mastery, instrumental background music, no vocals"
            }
        ],
        "fun_facts": [
            {
                "id": "jam_01",
                "filename": "jam_01_curiosidad_hispana.wav",
                "name": "Mundo Hispano",
                "emotion_slug": "curiosidad_hispana",
                "matching_emotions": ["curiosidad & fascinación", "curiosidad", "descubrimiento"],
                "bpm": 86,
                "style": "Warm Hispanic Marimba Chill",
                "instrumentation": "Warm marimba, acoustic Spanish guitar, double bass, soft shaker",
                "prompt": "Warm Hispanic marimba chill, melodious wooden marimba, gentle Spanish nylon guitar, acoustic double bass, soft shaker, 86 BPM, fascinating linguistic curiosities across Spanish-speaking countries, instrumental background music, no vocals"
            },
            {
                "id": "jam_02",
                "filename": "jam_02_origen_antiguo.wav",
                "name": "Palabras del Pasado",
                "emotion_slug": "origen_antiguo",
                "matching_emotions": ["etimología", "historia", "misterio", "orígenes"],
                "bpm": 80,
                "style": "Ancient Latin Atmosphere",
                "instrumentation": "Spanish nylon guitar, muted harp, deep warm bass, vintage tape vinyl",
                "prompt": "Ancient Latin atmosphere lo-fi, contemplative Spanish nylon guitar, muted acoustic harp, deep warm bass, vintage tape crackle, 80 BPM, ancient Arab and Latin roots of Spanish words, instrumental background music, no vocals"
            },
            {
                "id": "jam_03",
                "filename": "jam_03_reto_divertido_facts.wav",
                "name": "¿Sabías Que...?",
                "emotion_slug": "reto_divertido_facts",
                "matching_emotions": ["reto divertido & humor", "humor & asombro", "humor"],
                "bpm": 98,
                "style": "Playful Spanish Jazzhop",
                "instrumentation": "Pizzicato strings, bright vibraphone, bouncy Latin bass, handclaps",
                "prompt": "Playful Spanish jazzhop, lively pizzicato strings, bright vibraphone, bouncy Latin bass, rhythmic handclaps, 98 BPM, quirky fun facts about Spanish grammar and curious expressions, instrumental background music, no vocals"
            },
            {
                "id": "jam_04",
                "filename": "jam_04_humor_asombro.wav",
                "name": "Increíble Pero Real",
                "emotion_slug": "humor_asombro",
                "matching_emotions": ["humor & asombro", "asombro", "risa"],
                "bpm": 94,
                "style": "Cheeky Rumba Hop",
                "instrumentation": "Acoustic rumba guitar, upright piano, slap bass, funny bongo accents",
                "prompt": "Cheeky rumba hop, energetic acoustic rumba guitar, upright piano riff, slap bass, funny bongo accents, 94 BPM, hilarious linguistic surprises and mind-boggling false friends, instrumental background music, no vocals"
            },
            {
                "id": "jam_05",
                "filename": "jam_05_fascinacion_lengua.wav",
                "name": "La Riqueza del Idioma",
                "emotion_slug": "fascinacion_lengua",
                "matching_emotions": ["calidez & fascinación", "fascinación", "asombro"],
                "bpm": 88,
                "style": "Cinematic Spanish Chillhop",
                "instrumentation": "Spanish guitar, grand piano, warm cello swell, clean boom-bap",
                "prompt": "Cinematic Spanish chillhop, expressive Spanish nylon guitar, grand piano chords, warm cello swell, clean boom-bap drums, 88 BPM, awe-inspiring richness of the Spanish language, instrumental background music, no vocals"
            },
            {
                "id": "jam_06",
                "filename": "jam_06_diferencias_regionales.wav",
                "name": "De Madrid a Buenos Aires",
                "emotion_slug": "diferencias_regionales",
                "matching_emotions": ["regional", "dialectos", "acentos", "viaje"],
                "bpm": 84,
                "style": "Breezy Hispanic Fusion",
                "instrumentation": "Acoustic guitar, subtle bandoneón note, cajón, warm bass",
                "prompt": "Breezy Hispanic fusion, acoustic nylon guitar, subtle warm bandoneón accordion, gentle cajón percussion, warm bass, 84 BPM, regional Spanish differences and fascinating dialect quirks, instrumental background music, no vocals"
            },
            {
                "id": "jam_07",
                "filename": "jam_07_mito_desmentido.wav",
                "name": "Mito Desmontado",
                "emotion_slug": "mito_desmentido",
                "matching_emotions": ["mito", "desmentido", "verdad", "rae"],
                "bpm": 96,
                "style": "Detective Latin Groove",
                "instrumentation": "Wah-wah Spanish guitar, walking bass, vibraphone, ride cymbal",
                "prompt": "Detective Latin groove, rhythmic wah-wah Spanish guitar, walking double bass, subtle vibraphone, crisp ride cymbal, 96 BPM, debunking popular myths about Spanish words, instrumental background music, no vocals"
            },
            {
                "id": "jam_08",
                "filename": "jam_08_record_hispano.wav",
                "name": "Récords del Idioma",
                "emotion_slug": "record_hispano",
                "matching_emotions": ["récord", "extremos", "palabras largas"],
                "bpm": 110,
                "style": "Upbeat Latin Electro-Hop",
                "instrumentation": "Synth arpeggios, flamenco guitar riffs, electronic kick and clap, bass",
                "prompt": "Upbeat Latin electro-hop, synthesizer arpeggios, flamenco guitar riffs, punchy electronic kick and clap, deep bass, 110 BPM, shocking records and extreme words in the Spanish dictionary, instrumental background music, no vocals"
            },
            {
                "id": "jam_09",
                "filename": "jam_09_anecdota_calida.wav",
                "name": "Curiosidad Histórica",
                "emotion_slug": "anecdota_calida",
                "matching_emotions": ["anécdota", "calidez", "historia"],
                "bpm": 76,
                "style": "Cozy Spanish Lo-Fi",
                "instrumentation": "Vintage upright piano, acoustic guitar, vinyl hiss, gentle brushes",
                "prompt": "Cozy Spanish lo-fi, vintage upright piano, intimate nylon acoustic guitar, vinyl hiss, gentle brush drums, 76 BPM, heartwarming historical anecdotes and linguistic secrets, instrumental background music, no vocals"
            },
            {
                "id": "jam_10",
                "filename": "jam_10_gran_aprendizaje.wav",
                "name": "¡Qué Sabio!",
                "emotion_slug": "gran_aprendizaje",
                "matching_emotions": ["descubrimiento & sorpresa", "aprendizaje", "lección"],
                "bpm": 92,
                "style": "Inspiring Spanish Chill",
                "instrumentation": "Bright acoustic piano, Spanish guitar harmonies, melodic bass, snaps",
                "prompt": "Inspiring Spanish chill beat, bright acoustic grand piano melody, Spanish guitar harmonies, melodic warm bass, crisp finger snaps, 92 BPM, unforgettable educational revelation and viral takeaway, instrumental background music, no vocals"
            }
        ]
    },
    "italian": {
        "expression": [
            {
                "id": "jam_01",
                "filename": "jam_01_dolce_vita_lofi.wav",
                "name": "La Dolce Vita",
                "emotion_slug": "dolce_vita_lofi",
                "matching_emotions": ["naturalezza & cordialità", "cordialità", "naturalezza", "fluidità"],
                "bpm": 82,
                "style": "Italian Cinematic Lo-Fi",
                "instrumentation": "Acoustic mandolin, warm nylon guitar, smooth upright bass, soft brushed drums",
                "prompt": "Italian cinematic lo-fi, delicate acoustic mandolin melody, warm nylon acoustic guitar, smooth upright bass, soft brushed drums, 82 BPM, relaxed Italian elegance and natural Dolce Vita warmth, instrumental background music, no vocals"
            },
            {
                "id": "jam_02",
                "filename": "jam_02_aha_chiarezza.wav",
                "name": "Ecco Perché!",
                "emotion_slug": "aha_chiarezza",
                "matching_emotions": ["aha moment & chiarezza", "chiarezza", "chiarezza & sicurezza"],
                "bpm": 88,
                "style": "Mediterranean Chillhop",
                "instrumentation": "Warm Rhodes piano, acoustic nylon guitar, melodic bass, subtle vinyl crackle",
                "prompt": "Mediterranean chillhop, warm Fender Rhodes chords, acoustic nylon guitar leads, melodic electric bass, subtle vinyl crackle, 88 BPM, enlightened Italian aha moment and crystal clarity, instrumental background music, no vocals"
            },
            {
                "id": "jam_03",
                "filename": "jam_03_umorismo_sorpresa.wav",
                "name": "Ma Dai!",
                "emotion_slug": "umorismo_sorpresa",
                "matching_emotions": ["umorismo & sorpresa", "curiosità & umorismo", "umorismo", "sorpresa"],
                "bpm": 98,
                "style": "Playful Italian Swing Hop",
                "instrumentation": "Bouncy mandolin tremolo, pizzicato strings, swinging upright bass, finger snaps",
                "prompt": "Playful Italian swing hop, bouncy mandolin tremolo, playful pizzicato strings, swinging upright bass, crisp finger snaps, 98 BPM, witty Italian humor and expressive hand gesture vibes, instrumental background music, no vocals"
            },
            {
                "id": "jam_04",
                "filename": "jam_04_precisione_sicurezza.wav",
                "name": "Come si Deve",
                "emotion_slug": "precisione_sicurezza",
                "matching_emotions": ["aha moment & precisione", "precisione & chiarezza", "sicurezza", "precisione"],
                "bpm": 86,
                "style": "Sophisticated Italian Neo-Soul",
                "instrumentation": "Mellow electric guitar, grand piano accents, deep electric bass, clean rimshot",
                "prompt": "Sophisticated Italian neo-soul, mellow electric jazz guitar, grand piano accents, deep electric bassline, clean rimshot, 86 BPM, polished native Italian eloquence and confident precision, instrumental background music, no vocals"
            },
            {
                "id": "jam_05",
                "filename": "jam_05_sole_mediterraneo.wav",
                "name": "Sole di Mezzogiorno",
                "emotion_slug": "sole_mediterraneo",
                "matching_emotions": ["calma", "naturalezza", "cordialità"],
                "bpm": 76,
                "style": "Sun-Drenched Coastal Lo-Fi",
                "instrumentation": "Classical guitar arpeggios, gentle accordion pad, deep warm bass, soft shaker",
                "prompt": "Sun-drenched coastal Italian lo-fi, classical guitar arpeggios, gentle accordion pad, deep warm bass, soft shaker, 76 BPM, sun-drenched Amalfi coast ambiance and peaceful warmth, instrumental background music, no vocals"
            },
            {
                "id": "jam_06",
                "filename": "jam_06_sorpresa_precisione.wav",
                "name": "Proprio Così",
                "emotion_slug": "sorpresa_precisione",
                "matching_emotions": ["sorpresa & precisione", "sorpresa & sicurezza", "sorpresa"],
                "bpm": 92,
                "style": "Bouncy Italian Jazzhop",
                "instrumentation": "Vibraphone, acoustic guitar, walking double bass, crisp snare bounce",
                "prompt": "Bouncy Italian jazzhop, shimmering vibraphone, rhythmic acoustic guitar, walking double bass, crisp snare bounce, 92 BPM, surprising linguistic precision and Italian charm, instrumental background music, no vocals"
            },
            {
                "id": "jam_07",
                "filename": "jam_07_piazza_italiana.wav",
                "name": "In Piazza",
                "emotion_slug": "piazza_italiana",
                "matching_emotions": ["piazza", "quotidiano", "curiosità & ottimismo"],
                "bpm": 96,
                "style": "Breezy Italian Street Groove",
                "instrumentation": "Mandolin rhythm, upright piano, groovy bass, tambourine accents",
                "prompt": "Breezy Italian street groove, rhythmic mandolin strums, upright piano chords, groovy bass, subtle tambourine accents, 96 BPM, bustling lively Italian piazza atmosphere, instrumental background music, no vocals"
            },
            {
                "id": "jam_08",
                "filename": "jam_08_aha_fluidita.wav",
                "name": "Fluente e Naturale",
                "emotion_slug": "aha_fluidita",
                "matching_emotions": ["aha moment & fluidità", "fluidità", "ottimismo"],
                "bpm": 90,
                "style": "Smooth Italian Chillhop",
                "instrumentation": "Rhodes piano chords, Italian acoustic guitar, melodic bass, tight drums",
                "prompt": "Smooth Italian chillhop, warm Rhodes piano chords, lyrical Italian acoustic guitar, melodic bass, tight drums, 90 BPM, smooth flowing Italian mastery and effortless dialogue, instrumental background music, no vocals"
            },
            {
                "id": "jam_09",
                "filename": "jam_09_mistero_cinema.wav",
                "name": "Mistero a Cinecittà",
                "emotion_slug": "mistero_cinema",
                "matching_emotions": ["mistero", "cinema", "curiosità"],
                "bpm": 78,
                "style": "Vintage Morricone-Inspired Lo-Fi",
                "instrumentation": "Nylon guitar melody, subtle whistling, deep cinematic bass, slow boom-bap",
                "prompt": "Vintage Italian Morricone-inspired lo-fi, romantic nylon guitar melody, subtle evocative whistle, deep cinematic bass, slow vintage boom-bap, 78 BPM, nostalgic vintage Italian cinema mystery, instrumental background music, no vocals"
            },
            {
                "id": "jam_10",
                "filename": "jam_10_trionfo_italiano.wav",
                "name": "Perfetto!",
                "emotion_slug": "trionfo_italiano",
                "matching_emotions": ["trionfo", "perfezione", "sicurezza"],
                "bpm": 102,
                "style": "Uplifting Italian Pop-Funk",
                "instrumentation": "Italian brass stabs, bright grand piano, mandolin flourishes, punchy bass",
                "prompt": "Uplifting Italian pop-funk, cheerful brass stabs, bright grand piano, playful mandolin flourishes, punchy driving bass, 102 BPM, triumphant Italian expression mastery and pure joy, instrumental background music, no vocals"
            }
        ],
        "roleplay": [
            {
                "id": "jam_01",
                "filename": "jam_01_chiacchiere_bar.wav",
                "name": "Al Bar Italiano",
                "emotion_slug": "chiacchiere_bar",
                "matching_emotions": ["dialogue", "chiacchiere", "conversazione", "naturalezza"],
                "bpm": 90,
                "style": "Italian Bar Lo-Fi",
                "instrumentation": "Acoustic nylon guitar, mandolin accents, upright bass, soft brush drums",
                "prompt": "Italian bar lo-fi, acoustic nylon guitar, subtle mandolin accents, upright bass, soft brush drums, 90 BPM, lively espresso bar banter and authentic Italian dialogue, instrumental background music, no vocals"
            },
            {
                "id": "jam_02",
                "filename": "jam_02_battuta_pronta.wav",
                "name": "La Battuta Pronta",
                "emotion_slug": "battuta_pronta",
                "matching_emotions": ["umorismo & sorpresa", "curiosità & umorismo", "umorismo"],
                "bpm": 100,
                "style": "Bouncy Italian Swing-Hop",
                "instrumentation": "Pizzicato strings, swinging mandolin, bouncy bass, snappy claps",
                "prompt": "Bouncy Italian swing-hop, playful pizzicato strings, swinging mandolin rhythm, bouncy bassline, snappy claps, 100 BPM, quick Italian comedic timing and witty back-and-forth, instrumental background music, no vocals"
            },
            {
                "id": "jam_03",
                "filename": "jam_03_dubbio_comico.wav",
                "name": "Mamma Mia!",
                "emotion_slug": "dubbio_comico",
                "matching_emotions": ["dubbio", "tensione", "principiante", "esitazione"],
                "bpm": 82,
                "style": "Minimal Italian Comedy Lo-Fi",
                "instrumentation": "Soft muted piano, hesitant woodblock, cello note, vinyl crackle",
                "prompt": "Minimal Italian comedy lo-fi, soft muted piano, hesitant woodblock clock click, gentle cello note, vinyl crackle, 82 BPM, funny Italian dilemma and dramatic hesitation, instrumental background music, no vocals"
            },
            {
                "id": "jam_04",
                "filename": "jam_04_l_amico_fedele.wav",
                "name": "Un Vero Amico",
                "emotion_slug": "l_amico_fedele",
                "matching_emotions": ["chiarezza & sicurezza", "cordialità", "sostegno"],
                "bpm": 78,
                "style": "Warm Mediterranean Acoustic",
                "instrumentation": "Nylon guitar arpeggios, warm Rhodes, melodic bass, soft brush",
                "prompt": "Warm Mediterranean acoustic chill, lyrical nylon guitar arpeggios, warm Rhodes piano, melodic bassline, soft brush snare, 78 BPM, loyal friend helping and explaining with warm affection, instrumental background music, no vocals"
            },
            {
                "id": "jam_05",
                "filename": "jam_05_illuminazione.wav",
                "name": "Lampo di Genio",
                "emotion_slug": "illuminazione",
                "matching_emotions": ["aha moment & chiarezza", "aha moment & fluidità", "genio"],
                "bpm": 92,
                "style": "Bright Italian Chillhop",
                "instrumentation": "Bright Rhodes keys, mandolin sparkle, punchy bass, tight boom-bap",
                "prompt": "Bright Italian chillhop, warm Rhodes electric keys, subtle mandolin sparkle, punchy electric bass, tight boom-bap drums, 92 BPM, sudden Italian realization and shared victory, instrumental background music, no vocals"
            },
            {
                "id": "jam_06",
                "filename": "jam_06_mercato_rionale.wav",
                "name": "Al Mercato",
                "emotion_slug": "mercato_rionale",
                "matching_emotions": ["mercato", "strada", "fluidità"],
                "bpm": 98,
                "style": "Upbeat Italian Street Hop",
                "instrumentation": "Acoustic guitar rhythm, tambourine, walking bass, accordion chops",
                "prompt": "Upbeat Italian street hop, rhythmic acoustic guitar, lively tambourine, walking upright bass, cheerful accordion chops, 98 BPM, animated Italian market bargaining and everyday life, instrumental background music, no vocals"
            },
            {
                "id": "jam_07",
                "filename": "jam_07_serata_tranquilla.wav",
                "name": "Una Bella Serata",
                "emotion_slug": "serata_tranquilla",
                "matching_emotions": ["naturalezza", "calma", "serata"],
                "bpm": 75,
                "style": "Cozy Trattoria Lo-Fi",
                "instrumentation": "Classical guitar, warm acoustic bass, gentle shaker, cozy ambiance",
                "prompt": "Cozy trattoria lo-fi, classical guitar melody, warm acoustic bass, gentle shaker, intimate warm ambiance, 75 BPM, relaxed Italian dinner conversation and comfortable flow, instrumental background music, no vocals"
            },
            {
                "id": "jam_08",
                "filename": "jam_08_reazione_teatrale.wav",
                "name": "Che Sorpresa!",
                "emotion_slug": "reazione_teatrale",
                "matching_emotions": ["sorpresa & chiarezza", "sorpresa", "teatrale"],
                "bpm": 102,
                "style": "Theatrical Italian Funk",
                "instrumentation": "Vibraphone stabs, mandolin tremolo, slap bass, punchy drums",
                "prompt": "Theatrical Italian funk, vibraphone stabs, energetic mandolin tremolo, funky slap bass, punchy drums, 102 BPM, dramatic comedic Italian surprise and expressive reaction, instrumental background music, no vocals"
            },
            {
                "id": "jam_09",
                "filename": "jam_09_ottimismo_puro.wav",
                "name": "Tutto Bene!",
                "emotion_slug": "ottimismo_puro",
                "matching_emotions": ["curiosità & ottimismo", "ottimismo", "sicurezza"],
                "bpm": 106,
                "style": "Sunny Italian Pop-Hop",
                "instrumentation": "Bright acoustic guitar, mandolin melody, driving kick, celebratory handclaps",
                "prompt": "Sunny Italian pop-hop, bright strummed acoustic guitar, cheerful mandolin melody, driving kick, celebratory handclaps, 106 BPM, vibrant sunny optimism and confident Italian speech, instrumental background music, no vocals"
            },
            {
                "id": "jam_10",
                "filename": "jam_10_finale_perfetto.wav",
                "name": "Il Gran Finale",
                "emotion_slug": "finale_perfetto",
                "matching_emotions": ["payoff", "finale", "chiarezza & sicurezza"],
                "bpm": 94,
                "style": "Triumphant Italian Fusion",
                "instrumentation": "Mandolin crescendo, grand piano chords, punchy bass, crisp drums",
                "prompt": "Triumphant Italian fusion, dramatic mandolin crescendo, grand piano chords, punchy bassline, crisp drums, 94 BPM, memorable punchline payoff and roleplay climax, instrumental background music, no vocals"
            }
        ],
        "game": [
            {
                "id": "jam_01",
                "filename": "jam_01_tempo_scade.wav",
                "name": "Il Tempo Scade",
                "emotion_slug": "tempo_scade",
                "matching_emotions": ["urgente", "tempo", "pressione", "sfida"],
                "bpm": 118,
                "style": "Italian Suspense Beat",
                "instrumentation": "Ticking clock percussion, dramatic mandolin tremolo, deep sub bass, driving snare",
                "prompt": "Italian suspense beat, realistic ticking clock rhythm, dramatic mandolin tremolo, deep sub bass, driving snare, 118 BPM, urgent Italian quiz countdown and trivia tension, instrumental background music, no vocals"
            },
            {
                "id": "jam_02",
                "filename": "jam_02_gioco_a_premi.wav",
                "name": "Quiz Televisivo",
                "emotion_slug": "gioco_a_premi",
                "matching_emotions": ["quiz", "energia", "sfida giocosa"],
                "bpm": 110,
                "style": "Funky Italian Game Show",
                "instrumentation": "Punchy funk bass, electric piano, brass hits, snappy upbeat drums",
                "prompt": "Funky Italian game show groove, punchy bassline, electric piano chords, brass hits, snappy upbeat drums, 110 BPM, high-energy Italian trivia television show excitement, instrumental background music, no vocals"
            },
            {
                "id": "jam_03",
                "filename": "jam_03_concentrazione.wav",
                "name": "Indovinello",
                "emotion_slug": "concentrazione",
                "matching_emotions": ["concentrazione", "indovinello", "precisione"],
                "bpm": 96,
                "style": "Focus Marimba Hop",
                "instrumentation": "Marimba arpeggios, mandolin accents, warm sub bass, tight rimshot",
                "prompt": "Focus marimba hip hop, intricate marimba arpeggios, subtle mandolin accents, warm sub bass, tight crisp rimshot, 96 BPM, intellectual focus and language puzzle solving, instrumental background music, no vocals"
            },
            {
                "id": "jam_04",
                "filename": "jam_04_retro_arcade_it.wav",
                "name": "Sfida Arcade",
                "emotion_slug": "retro_arcade_it",
                "matching_emotions": ["arcade", "sfida giocosa", "divertimento"],
                "bpm": 112,
                "style": "Retro Italian Electro-Funk",
                "instrumentation": "8-bit synths, tambourine percussion, funky slap bass, energetic kick",
                "prompt": "Retro Italian electro-funk, 8-bit chiptune synths, Mediterranean tambourine, funky slap bass, energetic kick, 112 BPM, playful arcade trivia challenge, instrumental background music, no vocals"
            },
            {
                "id": "jam_05",
                "filename": "jam_05_ultimi_istanti.wav",
                "name": "Ultimi Istanti",
                "emotion_slug": "ultimi_istanti",
                "matching_emotions": ["tensione", "suspense", "attesa"],
                "bpm": 104,
                "style": "Dramatic Italian Tension",
                "instrumentation": "Pulsing synth bass, staccato cello, ticking percussion, rising pad",
                "prompt": "Dramatic Italian tension, pulsing electronic bass, staccato cello plucks, ticking clock percussion, rising tension pad, 104 BPM, intense countdown before the answer reveal, instrumental background music, no vocals"
            },
            {
                "id": "jam_06",
                "filename": "jam_06_esatto_vittoria.wav",
                "name": "Risposta Esatta!",
                "emotion_slug": "esatto_vittoria",
                "matching_emotions": ["vittoria", "esatto", "trionfo"],
                "bpm": 114,
                "style": "Triumphant Italian Pop-Funk",
                "instrumentation": "Italian brass fanfare, celebratory piano, driving bass, festive handclaps",
                "prompt": "Triumphant Italian pop-funk, celebratory brass fanfare stabs, celebratory piano chords, driving bass, festive handclaps, 114 BPM, exciting victory and celebration of the correct answer, instrumental background music, no vocals"
            },
            {
                "id": "jam_07",
                "filename": "jam_07_velocita_lampo.wav",
                "name": "Riflessi Lampo",
                "emotion_slug": "velocita_lampo",
                "matching_emotions": ["velocità", "riflessi", "rapido"],
                "bpm": 120,
                "style": "Energetic Italian Nu-Disco",
                "instrumentation": "Four-on-the-floor kick, rhythm guitar, bright synths, driving bass",
                "prompt": "Energetic Italian nu-disco, driving four-on-the-floor kick, rhythmic guitar chops, bright shimmering synths, driving bassline, 120 BPM, rapid-fire Italian trivia speed, instrumental background music, no vocals"
            },
            {
                "id": "jam_08",
                "filename": "jam_08_trabocchetto.wav",
                "name": "Il Trabocchetto",
                "emotion_slug": "trabocchetto",
                "matching_emotions": ["trabocchetto", "inganno", "mistero"],
                "bpm": 94,
                "style": "Sneaky Detective Italian Hop",
                "instrumentation": "Pizzicato strings, upright bass, mandolin accents, brushed snare",
                "prompt": "Sneaky detective Italian hip hop, cheeky pizzicato strings, walking upright acoustic bass, subtle mandolin accents, brushed snare, 94 BPM, tricky language trap and detective test, instrumental background music, no vocals"
            },
            {
                "id": "jam_09",
                "filename": "jam_09_duello_finale.wav",
                "name": "Duello di Parole",
                "emotion_slug": "duello_finale",
                "matching_emotions": ["duello", "competizione", "sfida"],
                "bpm": 116,
                "style": "High-Energy Breakbeat Italian",
                "instrumentation": "Breakbeat drums, aggressive bassline, mandolin riffs, claps",
                "prompt": "High-energy breakbeat Italian, breakbeat drum groove, aggressive bassline, dramatic mandolin riffs, punchy claps, 116 BPM, high-stakes competition and championship language battle, instrumental background music, no vocals"
            },
            {
                "id": "jam_10",
                "filename": "jam_10_maestro_italiano.wav",
                "name": "Da Vero Italiano",
                "emotion_slug": "maestro_italiano",
                "matching_emotions": ["maestro", "esperto", "soddisfazione"],
                "bpm": 102,
                "style": "Bouncy Italian Chill-Funk",
                "instrumentation": "Bright xylophone, mandolin chords, bouncy bass, tight rimshot",
                "prompt": "Bouncy Italian chill-funk, bright xylophone melody, mandolin chords, bouncy groovy bass, tight rimshot, 102 BPM, satisfying test proving true native Italian understanding, instrumental background music, no vocals"
            }
        ],
        "fun_facts": [
            {
                "id": "jam_01",
                "filename": "jam_01_curiosita_storia.wav",
                "name": "Curiosità d'Italia",
                "emotion_slug": "curiosita_storia",
                "matching_emotions": ["curiosità & sorpresa", "curiosità", "scoperta"],
                "bpm": 86,
                "style": "Charming Italian Marimba Hop",
                "instrumentation": "Marimba melody, acoustic nylon guitar, mandolin, double bass, shaker",
                "prompt": "Charming Italian marimba hop, wooden marimba melody, gentle acoustic nylon guitar, subtle mandolin, double bass, soft shaker, 86 BPM, fascinating curiosity and surprising Italian language facts, instrumental background music, no vocals"
            },
            {
                "id": "jam_02",
                "filename": "jam_02_lingua_dante.wav",
                "name": "La Lingua di Dante",
                "emotion_slug": "lingua_dante",
                "matching_emotions": ["incredulità & storia", "storia", "dante", "origini"],
                "bpm": 80,
                "style": "Historic Mediterranean Atmosphere",
                "instrumentation": "Nylon guitar, classical lute/mandolin, deep warm bass, vintage vinyl",
                "prompt": "Historic Mediterranean atmosphere lo-fi, classical nylon guitar, expressive mandolin, deep warm bass, vintage vinyl crackle, 80 BPM, ancient Latin origins and Dante's linguistic legacy, instrumental background music, no vocals"
            },
            {
                "id": "jam_03",
                "filename": "jam_03_sfida_giocosa.wav",
                "name": "Scioglilingua",
                "emotion_slug": "sfida_giocosa",
                "matching_emotions": ["sfida giocosa & divertimento", "divertimento", "scioglilingua"],
                "bpm": 98,
                "style": "Playful Italian Jazzhop",
                "instrumentation": "Pizzicato strings, vibraphone, mandolin, crisp finger snaps",
                "prompt": "Playful Italian jazzhop, lively pizzicato strings, cheerful vibraphone, fast mandolin rhythm, crisp finger snaps, 98 BPM, quirky fun facts about Italian tongue twisters and pronunciation, instrumental background music, no vocals"
            },
            {
                "id": "jam_04",
                "filename": "jam_04_incredulita_fatti.wav",
                "name": "Incredibile Ma Vero",
                "emotion_slug": "incredulita_fatti",
                "matching_emotions": ["incredulità", "sorpresa", "divertimento & scoperta"],
                "bpm": 94,
                "style": "Comedic Italian Bistro Hop",
                "instrumentation": "Upright piano, mandolin tremolo, slap bass, funny brush snare",
                "prompt": "Comedic Italian bistro hop, lively upright piano, mandolin tremolo, bouncy slap bass, funny brush snare, 94 BPM, unbelievable Italian facts and funny linguistic surprises, instrumental background music, no vocals"
            },
            {
                "id": "jam_05",
                "filename": "jam_05_sorpresa_fascinazione.wav",
                "name": "Fascino Italiano",
                "emotion_slug": "sorpresa_fascinazione",
                "matching_emotions": ["sorpresa & fascinazione", "fascinazione", "bellezza"],
                "bpm": 88,
                "style": "Cinematic Italian Chillhop",
                "instrumentation": "Mandolin pad, grand piano, warm cello swell, modern boom-bap",
                "prompt": "Cinematic Italian chillhop, lush mandolin pad, grand piano chords, warm cello swell, modern boom-bap drums, 88 BPM, breathtaking fascination with the musicality of the Italian language, instrumental background music, no vocals"
            },
            {
                "id": "jam_06",
                "filename": "jam_06_dialetti_regioni.wav",
                "name": "Da Nord a Sud",
                "emotion_slug": "dialetti_regioni",
                "matching_emotions": ["dialetti", "regioni", "accento", "cultura"],
                "bpm": 84,
                "style": "Warm Regional Italian Folk-Hop",
                "instrumentation": "Acoustic guitar, subtle accordion, tambourine, warm acoustic bass",
                "prompt": "Warm regional Italian folk-hop, acoustic guitar, subtle accordion, regional tambourine, warm acoustic bass, 84 BPM, rich Italian dialects from Naples to Venice, instrumental background music, no vocals"
            },
            {
                "id": "jam_07",
                "filename": "jam_07_gesti_parole.wav",
                "name": "Parlare Con le Mani",
                "emotion_slug": "gesti_parole",
                "matching_emotions": ["gesti", "mani", "miti", "cultura"],
                "bpm": 96,
                "style": "Cheeky Italian Groove",
                "instrumentation": "Wah guitar, walking bass, mandolin stabs, smooth ride cymbal",
                "prompt": "Cheeky Italian groove, rhythmic wah-wah guitar, walking double bass, lively mandolin stabs, smooth ride cymbal, 96 BPM, the secret language of Italian hand gestures and expression, instrumental background music, no vocals"
            },
            {
                "id": "jam_08",
                "filename": "jam_08_record_italiano.wav",
                "name": "Superlativi Italiani",
                "emotion_slug": "record_italiano",
                "matching_emotions": ["record", "estremi", "parole uniche"],
                "bpm": 110,
                "style": "Energetic Italian Electro-Hop",
                "instrumentation": "Synth arpeggios, mandolin riffs, electronic kick and clap, deep bass",
                "prompt": "Energetic Italian electro-hop, synthesizer arpeggios, chopped mandolin riffs, punchy electronic kick and clap, deep bass, 110 BPM, amazing records and untranslatable Italian words, instrumental background music, no vocals"
            },
            {
                "id": "jam_09",
                "filename": "jam_09_aneddoto_antico.wav",
                "name": "L'Aneddoto Segreto",
                "emotion_slug": "aneddoto_antico",
                "matching_emotions": ["aneddoto", "segreto", "storia"],
                "bpm": 76,
                "style": "Cozy Mediterranean Lo-Fi",
                "instrumentation": "Vintage piano, classical guitar, vinyl crackle, gentle brush beat",
                "prompt": "Cozy Mediterranean lo-fi, vintage piano melody, classical guitar, vinyl crackle, gentle brush beat, 76 BPM, charming storytelling and fascinating Italian cultural secrets, instrumental background music, no vocals"
            },
            {
                "id": "jam_10",
                "filename": "jam_10_scoperta_d_oro.wav",
                "name": "Meraviglia Italiana",
                "emotion_slug": "scoperta_d_oro",
                "matching_emotions": ["scoperta", "meraviglia", "lezione"],
                "bpm": 92,
                "style": "Inspiring Italian Chill",
                "instrumentation": "Grand piano, mandolin harmonies, melodic bass, crisp finger snaps",
                "prompt": "Inspiring Italian chill beat, bright grand piano melody, rich mandolin harmonies, melodic warm bass, crisp finger snaps, 92 BPM, memorable educational discovery and delightful Italian takeaway, instrumental background music, no vocals"
            }
        ]
    }
}

def get_bank_categories() -> List[tuple]:
    """Returns all 16 (language, video_type) category tuples."""
    categories = []
    for lang in ["english", "french", "spanish", "italian"]:
        for vt in ["expression", "roleplay", "game", "fun_facts"]:
            categories.append((lang, vt))
    return categories

def get_prompts_for_category(language: str, video_type: str) -> List[Dict[str, Any]]:
    """Returns the list of 10 prompts for the specified language and video type."""
    lang = language.strip().lower()
    vt = video_type.strip().lower()
    return MUSIC_BANK_CATALOG.get(lang, {}).get(vt, [])
