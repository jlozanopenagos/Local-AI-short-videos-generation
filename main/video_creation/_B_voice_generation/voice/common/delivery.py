"""Localized narration and acting directions for Studio voice synthesis."""

import re

NARRATOR = {
    "english": (
        "Open with immediate curiosity. Stress the unexpected word early, then carry the question forward in one thought.",
        "Build anticipation with timing and a steady conversational register.",
        "Give the reveal a brief beat. Slow slightly on the detail that resolves the question, then return to a conversational rhythm.",
        "Speak warmly as in everyday conversation, with a settled ending.",
        "Read quoted words in your own narrator voice, at your usual pitch.",
    ),
    "french": (
        "Accrochez l’auditeur dès les premiers mots. Appuyez tôt le détail inattendu, puis menez la question d’un seul élan.",
        "Créez l'attente par le rythme, dans un registre de conversation stable.",
        "Laissez un bref temps avant la révélation. Ralentissez sur le détail qui répond à la question, puis reprenez un rythme naturel.",
        "Parlez chaleureusement, comme dans une conversation, avec une fin posée.",
        "Lisez les citations avec votre voix de narrateur, à votre hauteur habituelle.",
    ),
    "italian": (
        "Apri con curiosità immediata. Dai subito risalto alla parola inattesa e porta avanti la domanda in un solo slancio.",
        "Crea attesa con il ritmo e mantieni un registro colloquiale stabile.",
        "Prenditi un istante prima della rivelazione. Rallenta sul dettaglio che risponde alla domanda, poi torna al ritmo della conversazione.",
        "Parla con calore, come in una conversazione, e chiudi con calma.",
        "Leggi le citazioni con la tua voce di narratore e la tua altezza abituale.",
    ),
    "spanish": (
        "Abre con curiosidad desde las primeras palabras. Destaca pronto el detalle inesperado y lleva la pregunta de un solo impulso.",
        "Crea expectativa con el ritmo y mantén un registro conversacional estable.",
        "Deja un breve momento antes de revelar la respuesta. Baja un poco el ritmo en el detalle decisivo y vuelve al ritmo de conversación.",
        "Habla con calidez, como en una conversación, y termina con calma.",
        "Lee las citas con tu propia voz de narrador, en tu registro habitual.",
    ),
}

ACTING = {
    "english": (
        "Start quickly, hesitate before the key phrase, then recover.",
        "Answer warmly and let the end of the thought settle.",
        "Let a slight smile interrupt the rhythm before the punch line.",
        "Lean into the question, with a brief hesitation before the surprising word.",
        "Start with a soft release, then let the ending brighten.",
        "Give the first words a clipped edge, then stress the point of frustration in your speaking register.",
        "Start with a firm onset and carry the thought steadily into a decisive ending.",
        "Hesitate briefly as if caught off guard, then finish quietly and matter-of-factly.",
        "Speak with the upbeat confidence that this can work. Give the good possibility a lift.",
        "Give the other person a gentle push forward. Land firmly on what they can do next.",
        "Explain as if answering a genuine question. Stress the idea that clears up the misunderstanding.",
    ),
    "french": (
        "Partez vite, hésitez avant le mot clé, puis reprenez.",
        "Répondez avec chaleur et posez la fin de la phrase.",
        "Laissez entendre un léger sourire avant la chute.",
        "Appuyez la question et hésitez brièvement avant le mot surprenant.",
        "Relâchez le début avec douceur, puis éclaircissez la fin.",
        "Attaquez brièvement les premiers mots, puis appuyez la source de la frustration dans votre registre habituel.",
        "Commencez avec fermeté et menez la phrase jusqu’à une fin décidée.",
        "Hésitez brièvement, comme pris au dépourvu, puis terminez plus doucement.",
        "Parlez avec la confiance joyeuse que la situation va s’arranger. Donnez de l’élan à cette possibilité.",
        "Donnez à l’autre un élan chaleureux. Appuyez fermement ce qu’il peut faire ensuite.",
        "Expliquez comme en réponse à une vraie question. Appuyez l’idée qui dissipe le malentendu.",
    ),
    "italian": (
        "Inizia in fretta, esita prima della parola chiave e poi riprendi.",
        "Rispondi con calore e lascia che il finale si posi.",
        "Lascia sentire un leggero sorriso prima della battuta.",
        "Dai rilievo alla domanda ed esita prima della parola sorprendente.",
        "Inizia con un leggero sospiro di sollievo, poi illumina il finale.",
        "Dai un attacco secco alle prime parole, poi sottolinea la causa della frustrazione nel tuo registro abituale.",
        "Inizia con fermezza e porta la frase verso un finale deciso.",
        "Esita un istante per l’imbarazzo, poi chiudi con un tono più sommesso.",
        "Parla con la fiducia di chi vede una possibilità concreta. Dai slancio alle parole che aprono quella possibilità.",
        "Dai all’altra persona una spinta affettuosa. Sottolinea con decisione cosa può fare adesso.",
        "Spiega come se rispondessi a una domanda sincera. Dai rilievo all’idea che chiarisce il malinteso.",
    ),
    "spanish": (
        "Empieza rápido, vacila antes de la palabra clave y retoma el ritmo.",
        "Responde con calidez y deja que el final se asiente.",
        "Deja oír una ligera sonrisa antes del remate.",
        "Destaca la pregunta y titubea antes de la palabra sorprendente.",
        "Suelta el aire suavemente al inicio y aligera el final.",
        "Marca brevemente las primeras palabras y destaca la causa de la frustración en tu registro habitual.",
        "Empieza con firmeza y mantén el ritmo hasta un final decidido.",
        "Vacila un instante por la vergüenza y termina con un tono más bajo y natural.",
        "Habla con la confianza de quien ve una salida. Dale impulso a las palabras que abren esa posibilidad.",
        "Dale a la otra persona un empujón afectuoso. Destaca con firmeza lo que puede hacer ahora.",
        "Explica como si respondieras a una pregunta sincera. Destaca la idea que aclara el malentendido.",
    ),
}

GAME_CHALLENGE = {
    "english": "Ask a single learner the quiz question. Give each option the same weight and a clear beat.",
    "french": "Posez la question à un seul élève. Donnez le même relief et un rythme clair à chaque option.",
    "italian": "Fai la domanda a una sola persona. Dai lo stesso rilievo e un ritmo chiaro a ogni opzione.",
    "spanish": "Hazle la pregunta a una persona. Da el mismo énfasis y un ritmo claro a cada opción.",
}

INTENT_NAMES = ("urgency", "reassurance", "amusement", "disbelief", "relief", "frustration", "determination", "embarrassment", "optimism", "encouragement", "explanation")

TURN_CUES = (
    ("anxi", "ansia", "ansios", "panic", "nerv", "angoiss", "worri"),
    ("calm", "tranquil", "rassur", "reassur", "rilassat", "relax"),
    ("smirk", "chuckl", "souri", "scherz", "brom", "teas", "amused", "sarcas", "divertid"),
    ("surpris", "baffl", "confus", "skept", "stupit", "sorpren", "incredul", "asombr", "confund"),
    ("reliev", "soulag", "sollev", "alivi", "soddisfatt"),
    ("frustr", "exasp", "agacé", "molest", "infastid"),
    ("determin", "détermin", "resuelt", "risolut"),
    ("embarrass", "fluster", "gêné", "avergonz", "imbarazz"),
    ("optim", "ottimist", "hopeful", "speranz"),
    ("encourag", "alent", "animand", "incoragg"),
    ("explicat", "explanat", "esplicativ", "spiegand"),
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


def roleplay_turn_direction(language: str, intent: int | None, previous_line: str = "") -> str:
    """Give the actor a delivery cue and context without changing the spoken text."""
    direction = delivery_direction(language, "", False, intent, video_type="roleplay")
    previous = continuous_narration(previous_line).replace("«", "").replace("»", "")
    if not previous:
        return direction
    if len(previous) > 200:
        _, _, previous = previous[-200:].partition(" ")
    reaction = _ROLEPLAY_REACTION.get(language, _ROLEPLAY_REACTION["english"])
    return f"{direction} {reaction.format(previous=previous)}"
