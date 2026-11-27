"""Localized narration and acting directions for Studio voice synthesis."""

import re

NARRATOR = {
    "english": (
        "Open with natural curiosity and relaxed conversational flow. Stress the unexpected detail early, and let long questions breathe naturally before a light lift at the very end.",
        "Build anticipation with timing and a steady conversational register.",
        "Give the reveal a brief beat. Slow slightly on the detail that resolves the question, then return to a conversational rhythm.",
        "Speak warmly as in everyday conversation, with a settled ending.",
        "Keep your usual speaking register and conversational volume, including in quotes. Create contrast through timing and word stress.",
    ),
    "french": (
        "Accrochez l’auditeur avec une curiosité naturelle. Appuyez tôt le détail inattendu et laissez les questions longues respirer naturellement avant une légère montée finale.",
        "Créez l'attente par le rythme, dans un registre de conversation stable.",
        "Laissez un bref temps avant la révélation. Ralentissez sur le détail qui répond à la question, puis reprenez un rythme naturel.",
        "Parlez chaleureusement, comme dans une conversation, avec une fin posée.",
        "Gardez votre registre et votre volume de conversation, citations comprises. Créez le contraste par le rythme et l’accentuation.",
    ),
    "italian": (
        "Apri con curiosità naturale. Dai risalto al dettaglio inatteso e lascia respirare le domande lunghe con naturalezza, salendo leggermente solo sulla chiusura.",
        "Crea attesa con il ritmo e mantieni un registro colloquiale stabile.",
        "Prenditi un istante prima della rivelazione. Rallenta sul dettaglio che risponde alla domanda, poi torna al ritmo della conversazione.",
        "Parla con calore, come in una conversazione, e chiudi con calma.",
        "Mantieni il registro e il volume della conversazione anche nelle citazioni. Crea contrasto con il ritmo e gli accenti.",
    ),
    "spanish": (
        "Abre con curiosidad natural y ritmo relajado. Destaca pronto el detalle inesperado y deja que las preguntas largas respiren con naturalidad, subiendo suavemente solo en las últimas palabras.",
        "Crea expectativa con el ritmo y mantén un registro conversacional estable.",
        "Deja un breve momento antes de revelar la respuesta. Baja un poco el ritmo en el detalle decisivo y vuelve al ritmo de conversación.",
        "Habla con calidez, como en una conversación, y termina con calma.",
        "Mantén tu registro y volumen de conversación, también en las citas. Crea contraste con el ritmo y el énfasis.",
    ),
}

ACTING = {
    "english": (
        "Speak with urgent nervous energy: start quickly, hesitate tensely before the key phrase, then push through breathlessly.",
        "Answer with genuine warmth and calm reassurance, letting the end of the thought settle smoothly.",
        "Speak with playful amusement and a clear grin in your voice, letting a lighthearted chuckle lift the punch line.",
        "Speak with sharp, incredulous disbelief: lean strongly into the question with a startled beat before the surprising word.",
        "Begin with a palpable, audible sigh of relief, then let your voice brighten happily toward the end.",
        "Speak with sharp frustration and exasperation: hit the first words with a clipped, irritated edge and punch the source of annoyance.",
        "Speak with bold, resolute determination: crisp firm onset, steady vocal conviction, and a decisive landing.",
        "Sound genuinely flustered and embarrassed: hesitate awkwardly as if caught red-handed, then drop slightly into sheepish admission.",
        "Speak with upbeat, bright optimism and lift the hopeful possibility with lively energy.",
        "Speak with warm, spirited encouragement, giving the other person an energetic push forward on what to do next.",
        "Explain clearly and earnestly as if clearing up a real misunderstanding, stressing the key insight.",
        "Speak with genuine anger and heated indignation: sharp, forceful attack, tight vocal intensity, and emphatic stress on the accusation.",
        "Speak with real fear and startled alarm: tight, breathless voice, quickened pace, and trembling urgency on the threat.",
        "Speak with unmistakable shock and stunned disbelief: sudden startled lift on the opening words, wide-eyed breathless reaction.",
        "Speak with bright, joyful excitement: lively upbeat momentum, smiling resonance, and an energetic lift on the climax.",
        "Speak with dry, deadpan seriousness and understated comedic timing, holding a steady, unbothered tone.",
        "Speak with proud, triumphant confidence: chest-forward resonance, smug upward lift, and bold emphasis.",
    ),
    "french": (
        "Parlez avec une urgence nerveuse : partez vite, hésitez avec tension avant le mot clé, puis reprenez d'un souffle rapide.",
        "Répondez avec chaleur et calme rassurant, en posant doucement la fin de la phrase.",
        "Parlez avec un amusement malicieux et un vrai sourire dans la voix, avec une touche rieuse avant la chute.",
        "Parlez avec une incrédulité vive et franche : appuyez fortement la question avec un bref arrêt stupéfait avant le mot surprenant.",
        "Commencez par un vrai relâchement soulagé, puis éclairez joyeusement la fin de la phrase.",
        "Parlez avec une frustration franche et agacée : attaquez sèchement les premiers mots et appuyez fortement la cause de l'agacement.",
        "Parlez avec une détermination ferme et assurée : attaque nette, conviction stable et chute décidée.",
        "Paraissez vraiment gêné et pris de court : hésitez maladroitement, puis terminez d'un ton plus bas et confus.",
        "Parlez avec une confiance joyeuse et lumineuse : donnez de l'élan enthousiaste à cette belle possibilité.",
        "Encouragez l'autre avec un élan chaleureux et dynamique, en appuyant fermement ce qu'il peut faire ensuite.",
        "Expliquez avec clarté et sincérité comme pour dissiper un vrai malentendu, en marquant l'idée clé.",
        "Parlez avec une vraie colère indignée : attaque sèche et tendue, intensité vocale marquée et accent ferme sur le reproche.",
        "Parlez avec une peur réelle et de l'alarme : voix serrée et essoufflée, débit pressé et tremblement inquiet.",
        "Parlez avec un choc net et une stupéfaction sincère : sursaut vocal dès les premiers mots et réaction vive coupée de souffle.",
        "Parlez avec une joie vive et un enthousiasme débordant : rythme dynamique, voix souriante et élan brillant sur la chute.",
        "Parlez d'un ton pince-sans-rire, sec et sérieux, avec un calme imperturbable au service de l'humour.",
        "Parlez avec une fierté assurée et triomphante : voix pleine, sourire confiant et accent appuyé sur la réussite.",
    ),
    "italian": (
        "Parla con urgenza nervosa: inizia in fretta, esita con tensione prima della parola chiave e poi riprendi col fiato corto.",
        "Rispondi con calore autentico e calma rassicurante, lasciando che il finale si posi dolcemente.",
        "Parla con divertimento giocoso e un chiaro sorriso nella voce, lasciando brillare la battuta finale.",
        "Parla con incredulità viva e sorpresa: spingi forte sulla domanda con una breve esitazione stupita prima della parola sorprendente.",
        "Inizia con un chiaro sospiro di sollievo, poi illumina il finale con energia allegra.",
        "Parla con frustrazione decisa e impaziente: dai un attacco secco alle prime parole e calca con fastidio sulla causa.",
        "Parla con fermezza e decisione: attacco sicuro, voce piena di convinzione e chiusura netta.",
        "Mostra vero imbarazzo come colto in flagrante: esita un istante impacciato, poi chiudi con tono più sommesso.",
        "Parla con ottimismo brillante e vitale, dando slancio entusiasta alle parole che aprono una soluzione.",
        "Dai all'altra persona una spinta affettuosa ed energica, sottolineando con forza cosa può fare subito.",
        "Spiega con chiarezza e sincerità come per chiarire un vero equivoco, dando forte rilievo all'idea chiave.",
        "Parla con vera rabbia e indignazione accesa: attacco duro e teso, grande intensità emotiva e accento deciso sull'accusa.",
        "Parla con paura autentica e allarme: voce tesa e affannata, ritmo incalzante e urgenza tremante.",
        "Parla con shock improvviso e stupore sincero: scatto vocale sulle prime parole e reazione intensa senza fiato.",
        "Parla con gioia esplosiva ed entusiasmo contagioso: ritmo vivace, voce sorridente e slancio brillante sul finale.",
        "Parla con tono serio, asciutto e impassibile, mantenendo una calma ironica e tagliente.",
        "Parla con orgoglio fiero e sicuro: voce piena, tono trionfante e accento marcato sul risultato.",
    ),
    "spanish": (
        "Habla con urgencia nerviosa: empieza rápido, vacila con tensión antes de la palabra clave y sigue con aliento agitado.",
        "Responde con calidez genuina y calma tranquilizadora, dejando que el final se asiente con suavidad.",
        "Habla con diversión juguetona y una sonrisa clara en la voz, dejando que un toque risueño levante el remate.",
        "Habla con incredulidad viva y asombro: carga con fuerza la pregunta y titubea sorprendido antes de la palabra clave.",
        "Empieza soltando un claro suspiro de alivio y ilumina el final con alegría genuina.",
        "Habla con frustración real y fastidio: marca secamente las primeras palabras y golpea con enfado la causa del problema.",
        "Habla con determinación firme y segura: entrada decidida, convicción plena y cierre contundente.",
        "Suena sinceramente avergonzado y apurado: vacila un instante incómodo y cierra con un tono más bajo y apenado.",
        "Habla con optimismo brillante y energía positiva, impulsando con entusiasmo la buena posibilidad.",
        "Dale a la otra persona un empujón afectuoso y lleno de ánimo, destacando con firmeza su siguiente paso.",
        "Explica con claridad y cercanía como aclarando un malentendido real, marcando la idea decisiva.",
        "Habla con enojo auténtico e indignación encendida: ataque seco y firme, tensión vocal clara y énfasis fuerte en el reclamo.",
        "Habla con miedo real y alarma: voz tensa y entrecortada, ritmo acelerado y urgencia temblorosa.",
        "Habla con shock repentino y asombro total: arranque sobresaltado, reacción intensa y tono atónito.",
        "Habla con alegría vibrante y entusiasmo genuino: ritmo vivo, voz sonriente y empuje energético en el remate.",
        "Habla con seriedad seca e inexpresiva, manteniendo un tono firme e imperturbable de humor seco.",
        "Habla con orgullo seguro y triunfante: voz plena, sonrisa confiada y énfasis claro en el logro.",
    ),
}

GAME_CHALLENGE = {
    "english": "Ask a single learner the quiz question. Give each option the same weight and a clear beat.",
    "french": "Posez la question à un seul élève. Donnez le même relief et un rythme clair à chaque option.",
    "italian": "Fai la domanda a una sola persona. Dai lo stesso rilievo e un ritmo chiaro a ogni opzione.",
    "spanish": "Hazle la pregunta a una persona. Da el mismo énfasis y un ritmo claro a cada opción.",
}

INTENT_NAMES = (
    "urgency", "reassurance", "amusement", "disbelief", "relief",
    "frustration", "determination", "embarrassment", "optimism",
    "encouragement", "explanation", "anger", "fear", "shock",
    "excitement", "deadpan", "pride",
)

TURN_CUES = (
    ("anxi", "ansia", "ansios", "panic", "nerv", "angoiss", "worri", "preocup", "agobiad", "épuis", "epuis", "urgent"),
    ("calm", "tranquil", "rassur", "reassur", "rilassat", "relax", "pazient", "bienveill", "rassicurat"),
    ("smirk", "chuckl", "souri", "scherz", "brom", "teas", "amused", "sarcas", "divertid", "grin", "laugh", "riend", "ridend", "moqu", "sonrien", "smil", "hilarious", "playful", "ironi", "burl"),
    ("surpris", "baffl", "confus", "skept", "stupit", "sorpren", "incredul", "asombr", "confund", "perplex", "desconcert", "scepti", "escéptic", "esceptic", "scettic"),
    ("reliev", "soulag", "sollev", "alivi", "soddisfatt", "éclair", "eclair"),
    ("frustr", "exasp", "agacé", "agace", "molest", "infastid", "annoy", "impatien", "énerv", "enerv"),
    ("determin", "détermin", "resuelt", "risolut", "confident", "segur"),
    ("embarrass", "fluster", "gêné", "gene", "avergonz", "imbarazz"),
    ("optim", "ottimist", "hopeful", "speranz"),
    ("encourag", "alent", "animand", "incoragg"),
    ("explicat", "explanat", "esplicativ", "spiegand", "chiaro", "aclar"),
    ("angry", "furious", "mad", "heated", "enoj", "enfad", "arrabbi", "colère", "colere", "confrontativ", "furios", "indign"),
    ("scared", "terrif", "afraid", "fear", "peur", "miedo", "paura", "spavent", "fright", "trembl", "asustad"),
    ("shock", "choqu", "scioccat", "stunn", "atónit", "atonit"),
    ("excit", "happy", "joy", "enthousias", "entusias", "feliz", "alegr", "emozion", "emocion", "hyped", "celebrat", "delight", "euphor"),
    ("deadpan", "serio", "serious", "dry", "sec", "impassib", "conspirat"),
    ("proud", "fier", "fiero", "orgull", "triumph", "boast"),
)


def turn_intent(label: str, inferred: str) -> int | None:
    for signal in (label, inferred):
        text = (signal or "").casefold()
        for intent, cues in enumerate(TURN_CUES):
            if any(cue in text for cue in cues):
                return intent
    return None


_TEACHING_NARRATION = {
    "english": (
        "Demonstrate the expression as it would sound in conversation, with a clear stress on the key words.",
        "Explain the idea to a curious listener. Connect each sentence to the last and stress the detail that makes it click.",
        "Finish with the satisfaction of having answered the opening question. Let the last phrase land.",
        "Give the expression itself clear, natural stress. Ease the pace briefly on the part that explains what it means.",
    ),
    "french": (
        "Montrez comment l’expression sonne dans une vraie conversation et appuyez les mots clés.",
        "Expliquez l’idée à une personne curieuse. Reliez les phrases et appuyez le détail qui éclaire le sujet.",
        "Terminez avec la satisfaction d’avoir répondu à la question de départ. Posez la dernière phrase.",
        "Faites ressortir l’expression avec un accent naturel. Ralentissez brièvement au moment d’en éclairer le sens.",
    ),
    "italian": (
        "Mostra come suona l’espressione in una vera conversazione e dai risalto alle parole chiave.",
        "Spiega l’idea a una persona curiosa. Collega le frasi e sottolinea il dettaglio che chiarisce il concetto.",
        "Chiudi con la soddisfazione di aver risposto alla domanda iniziale. Lascia che l’ultima frase si posi.",
        "Dai risalto all’espressione con un accento naturale. Rallenta brevemente mentre ne chiarisci il significato.",
    ),
    "spanish": (
        "Muestra cómo suena la expresión en una conversación real y destaca las palabras clave.",
        "Explica la idea a una persona curiosa. Enlaza las frases y destaca el detalle que aclara el tema.",
        "Cierra con la satisfacción de haber respondido a la pregunta inicial. Deja que la última frase se asiente.",
        "Destaca la expresión con un énfasis natural. Baja un poco el ritmo justo al aclarar su significado.",
    ),
}


_GAME_NARRATOR = {
    "english": (
        "Invite the viewer into the quiz with a quick, playful opening. Land on what they have to guess.",
        "Give the viewer a moment to decide. Keep the suspense in your timing and keep your voice steady.",
        "Reveal the answer with a brief lift. Stress the correct phrase clearly, then settle into the explanation.",
    ),
    "french": (
        "Invitez l’auditeur à jouer avec une entrée vive et malicieuse. Mettez en avant ce qu’il doit deviner.",
        "Laissez un moment pour choisir. Faites monter l’attente par le rythme, avec une voix posée.",
        "Révélez la réponse avec un bref élan. Appuyez clairement l’expression correcte, puis posez l’explication.",
    ),
    "italian": (
        "Invita chi ascolta a giocare con un’apertura rapida e vivace. Dai risalto a ciò che deve indovinare.",
        "Lascia un momento per scegliere. Crea attesa con il ritmo e mantieni la voce stabile.",
        "Svela la risposta con un breve slancio. Dai risalto alla frase giusta, poi passa a una spiegazione più distesa.",
    ),
    "spanish": (
        "Invita al público a jugar con una entrada ágil y juguetona. Destaca lo que hay que adivinar.",
        "Deja un momento para elegir. Crea expectativa con el ritmo y mantén la voz estable.",
        "Revela la respuesta con un pequeño impulso. Destaca la frase correcta y pasa a una explicación más pausada.",
    ),
}

_ROLEPLAY_NARRATOR = {
    "english": (
        "Set the scene quickly. Stress what’s at stake for the characters, then leave room for their first line.",
        "React to what just happened with warm recognition. Give the useful phrase clear stress and finish the thought.",
    ),
    "french": (
        "Plantez le décor rapidement. Appuyez l’enjeu pour les personnages, puis laissez place à leur première réplique.",
        "Réagissez à ce qui vient de se passer avec une complicité chaleureuse. Appuyez la phrase à retenir et posez la fin.",
    ),
    "italian": (
        "Imposta la scena in fretta. Dai risalto a ciò che conta per i personaggi, poi lascia spazio alla loro prima battuta.",
        "Reagisci con calore a ciò che è appena successo. Dai risalto alla frase da ricordare e chiudi il pensiero.",
    ),
    "spanish": (
        "Sitúa la escena con rapidez. Destaca lo que está en juego para los personajes y deja paso a su primera frase.",
        "Reacciona con calidez a lo que acaba de ocurrir. Marca la frase que conviene recordar y cierra la idea.",
    ),
}

_GAME_BEAT = {"title": 0, "hook": 0, "pressure": 1, "thinking_time": 1, "answer": 2, "reveal": 2}
_ROLEPLAY_BEAT = {"title": 0, "hook": 0, "payoff": 1, "cta": 1}


def delivery_direction(language: str, section: str, narrator: bool, intent: int | None, *, video_type: str = "") -> str:
    if not narrator and intent is not None:
        return ACTING.get(language, ACTING["english"])[intent]
    hook, suspense, reveal, conversational, identity = NARRATOR.get(language, NARRATOR["english"])
    kind = video_type.casefold()
    beat = None
    if narrator and kind == "game" and section == "challenge":
        beat = GAME_CHALLENGE.get(language, GAME_CHALLENGE["english"])
    elif narrator and kind == "game" and section in _GAME_BEAT:
        beat = _GAME_NARRATOR.get(language, _GAME_NARRATOR["english"])[_GAME_BEAT[section]]
    elif narrator and kind == "roleplay" and section in _ROLEPLAY_BEAT:
        beat = _ROLEPLAY_NARRATOR.get(language, _ROLEPLAY_NARRATOR["english"])[_ROLEPLAY_BEAT[section]]
    elif narrator and kind in {"expression", "fun_facts"}:
        example, explanation, closing, expression_reveal = _TEACHING_NARRATION.get(
            language, _TEACHING_NARRATION["english"],
        )
        teaching_beats = {"example": example, "explanation": explanation, "payoff": closing, "cta": closing}
        if kind == "expression":
            teaching_beats.update(discovery=expression_reveal, reveal=expression_reveal)
        beat = teaching_beats.get(section)
    if beat is None:
        if section in {"title", "hook"}:
            beat = hook
        elif section in ("setup", "mystery", "challenge", "pressure", "thinking_time"):
            beat = suspense
        elif section in ("discovery", "reveal", "answer", "surprise") or section.startswith("fact_"):
            beat = reveal
        else:
            beat = conversational
    return f"{beat} {identity}" if narrator else conversational


def continuous_narration(text: str) -> str:
    """Keep punctuation but remove delimiters that restart the ComfyUI clone."""
    return " ".join(re.sub(r"\[(?:pause|p):\d+(?:\.\d+)?\]", " ", text, flags=re.I).split())

_ROLEPLAY_REACTION = {
    "english": "React to the other person's previous line for context only: «{previous}». Speak only your own line.",
    "french": "Réagissez à la réplique précédente de l’autre personnage, donnée pour le contexte : «{previous}». Dites uniquement votre réplique.",
    "italian": "Reagisci alla battuta precedente dell’altra persona, qui solo per il contesto: «{previous}». Pronuncia soltanto la tua battuta.",
    "spanish": "Reacciona a la intervención anterior de la otra persona, solo como contexto: «{previous}». Di únicamente tu propia frase.",
}


_FALLBACK_EMOTION_TEMPLATE = {
    "english": "Act this line with clear, expressive {emotion} emotion and vivid conversational energy.",
    "french": "Jouez cette réplique avec une émotion claire et expressive ({emotion}) et une énergie conversationnelle vive.",
    "italian": "Recita questa battuta con un'emozione chiara ed espressiva ({emotion}) e vivace energia dialogica.",
    "spanish": "Actúa esta réplica con una emoción clara y expresiva ({emotion}) y energía conversacional viva.",
}


def roleplay_turn_direction(
    language: str,
    intent: int | None,
    previous_line: str = "",
    fallback_emotion: str = "",
) -> str:
    """Give the actor a vivid delivery cue and optional brief context without changing spoken text."""
    if intent is None and fallback_emotion and fallback_emotion.strip().lower() not in {"neutral", "none", "normal"}:
        tpl = _FALLBACK_EMOTION_TEMPLATE.get(language, _FALLBACK_EMOTION_TEMPLATE["english"])
        direction = tpl.format(emotion=fallback_emotion.strip())
    else:
        direction = delivery_direction(language, "", False, intent, video_type="roleplay")
    previous = continuous_narration(previous_line).replace("«", "").replace("»", "")
    if not previous:
        return direction
    if len(previous) > 120:
        _, _, previous = previous[-120:].partition(" ")
    reaction = _ROLEPLAY_REACTION.get(language, _ROLEPLAY_REACTION["english"])
    return f"{direction} {reaction.format(previous=previous)}"
