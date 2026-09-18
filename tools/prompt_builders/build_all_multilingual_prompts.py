"""
build_all_multilingual_prompts.py
Adapts and standardizes all expressions for French, Spanish, and Italian into:
- *_READY_PROMPTS_EXPRESSION.csv
- *_READY_PROMPTS_GAME.csv
- *_READY_PROMPTS_ROLEPLAY.csv
"""

import csv
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

def clean_val(v: str) -> str:
    if not v:
        return ""
    v = v.replace("\r", " ").replace("\n", " ")
    v = re.sub(r"\s+", " ", v).strip()
    return v

def generate_french_rows():
    p = BASE_DIR / "input" / "csv" / "french" / "expressions_list" / "FRENCH_READY_PROMPTS_EXPRESSION.csv"
    with open(p, encoding="utf-8-sig") as f:
        raw_rows = list(csv.reader(f))[1:]

    # FE01 and FE02 exist
    fe01 = raw_rows[0]
    fe02 = raw_rows[1]

    # Filter out duplicates at index 2 and 3 ("tomber dans les pommes" and "poser un lapin")
    filtered_raw = [fe01, fe02]
    for r in raw_rows[2:]:
        expr = clean_val(r[1]).lower()
        if expr in ["tomber dans les pommes", "poser un lapin"]:
            continue
        filtered_raw.append(r)

    print(f"French total after removing duplicates: {len(filtered_raw)}")

    def get_french_meta(expr, raw_subj, raw_ctx):
        expr_clean = clean_val(expr)
        raw_subj = clean_val(raw_subj).lower()
        raw_ctx = clean_val(raw_ctx)

        # Subject categorization
        if "false_friend" in raw_subj:
            subj = "Faux-amis anglais-français"
            lex = "Faux-amis et vocabulaire"
            emo = "Surprise & Clarté"
            angle = f"Pourquoi le mot français '{expr_clean.split()[0]}' ne signifie absolument pas ce que les anglophones croient"
            scenario = f"Au travail avec un collègue étranger : PERSON_ONE utilise '{expr_clean.split()[0]}' dans un mauvais sens par confusion avec l'anglais. PERSON_TWO sourit avec bienveillance et lui explique la vraie nuance en contexte : '{raw_ctx}'."
        elif raw_subj in ["expressions", "idiom"]:
            subj = "Expressions idiomatiques françaises"
            lex = "Expressions imagées"
            emo = "Curiosité & Humour"
            angle = f"L'origine surprenante et l'utilisation quotidienne de l'expression '{expr_clean}'"
            scenario = f"Dans une discussion animée entre amis : PERSON_ONE traverse une situation typique et PERSON_TWO s'exclame avec humour : '{expr_clean} !', illustrant parfaitement son sens : '{raw_ctx}'."
        elif raw_subj == "verb":
            subj = "Verbes et constructions"
            lex = "Verbes du quotidien"
            emo = "Aha Moment & Précision"
            angle = f"La règle essentielle pour maîtriser la construction du verbe '{expr_clean}' sans hésiter"
            scenario = f"Pendant une pause café : PERSON_ONE hésite sur la tournure exacte du verbe. PERSON_TWO lui donne l'exemple parfait tiré de la vie réelle : '{raw_ctx}'."
        elif raw_subj == "adjective":
            subj = "Place et accord des adjectifs"
            lex = "Description et style"
            emo = "Aha Moment & Subtilité"
            angle = f"Comment changer la place de l'adjectif dans '{expr_clean}' transforme radicalement le sens"
            scenario = f"En commentant une rencontre marquante : PERSON_ONE emploie l'adjectif avant le nom, et PERSON_TWO montre avec enthousiasme la différence subtile : '{raw_ctx}'."
        elif raw_subj == "vocabulary":
            subj = "Nuances de vocabulaire français"
            lex = "Vocabulaire du quotidien"
            emo = "Clarté & Confiance"
            angle = f"La clé infaillible pour ne plus jamais confondre '{expr_clean}' à l'oral"
            scenario = f"En préparant une sortie entre amis : PERSON_ONE confond les deux termes et PERSON_TWO lui rappelle la distinction naturelle : '{raw_ctx}'."
        elif raw_subj in ["grammar", "structure", "phrase"]:
            subj = "Grammaire et structures françaises"
            lex = "Grammaire pratique"
            emo = "Aha Moment & Clarté"
            angle = f"Le secret pour utiliser naturellement la structure '{expr_clean}' comme un vrai natif"
            scenario = f"Dans une conversation quotidienne : PERSON_ONE commet une petite erreur classique. PERSON_TWO le rassure et reformule naturellement : '{raw_ctx}'."
        elif raw_subj == "preposition":
            subj = "Prépositions et expressions de lieu"
            lex = "Prépositions et repères"
            emo = "Précision & Aisance"
            angle = f"Comment choisir la bonne préposition avec '{expr_clean}' sans faire d'erreur"
            scenario = f"En réservant un trajet de vacances : PERSON_ONE s'interroge sur la préposition correcte. PERSON_TWO confirme avec assurance la formule exacte : '{raw_ctx}'."
        elif raw_subj == "collocation":
            subj = "Collocations et tournures courantes"
            lex = "Communication quotidienne"
            emo = "Naturel & Aisance"
            angle = f"Pourquoi les natifs utilisent systématiquement la collocation '{expr_clean}'"
            scenario = f"Dans une situation de tous les jours : PERSON_ONE utilise une formulation trop littérale. PERSON_TWO lui suggère avec complaisance l'expression naturelle : '{raw_ctx}'."
        elif raw_subj == "noun":
            subj = "Genre et accords des noms français"
            lex = "Noms et vocabulaire"
            emo = "Surprise & Clarté"
            angle = f"Le piège du genre masculin/féminin pour '{expr_clean}' enfin démystifié"
            scenario = f"En rédigeant un message : PERSON_ONE hésite sur le genre grammatical de '{expr_clean}'. PERSON_TWO lui confirme avec le sourire la bonne tournure : '{raw_ctx}'."
        elif raw_subj == "time":
            subj = "Expressions temporelles françaises"
            lex = "Temps et durées"
            emo = "Clarté & Repères"
            angle = f"Comment maîtriser le repère temporel '{expr_clean}' dans toutes vos conversations"
            scenario = f"En racontant une anecdote récente : PERSON_ONE emploie '{expr_clean}' pour situer l'action dans le temps. PERSON_TWO écoute avec intérêt : '{raw_ctx}'."
        else:
            subj = "Français pratique et expressions"
            lex = "Communication générale"
            emo = "Confiance & Curiosité"
            angle = f"La formule indispensable '{expr_clean}' pour parler un français fluide et authentique"
            scenario = f"Dans un échange naturel : PERSON_ONE et PERSON_TWO discutent avec aisance, employant avec justesse : '{raw_ctx}'."

        return subj, angle, lex, emo, scenario

    expr_rows = []
    game_rows = []
    role_rows = []

    for i, r in enumerate(filtered_raw, start=1):
        cid = f"FE{i:02d}"
        gid = f"FG{i:02d}"
        rid = f"FR{i:02d}"

        if i == 1:
            expr_rows.append(fe01)
            game_rows.append([gid, fe01[1], fe01[2], fe01[5]])
            role_rows.append([
                rid,
                "Dans un café parisien : un jeune homme attend nerveusement depuis 45 minutes en fixant sa montre. Son amie arrive tout sourire et lui demande avec malice s'il vient encore de se faire poser un lapin.",
                fe01[2], fe01[5], fe01[6]
            ])
            continue
        elif i == 2:
            expr_rows.append(fe02)
            game_rows.append([gid, fe02[1], fe02[2], fe02[5]])
            role_rows.append([
                rid,
                "Dans une salle de sport : un débutant s'effondre sur un banc, essoufflé après une série intense. Son coach lui tend une gourde d'eau en souriant et lui dit : 'Respire un grand coup, ne me tombe pas dans les pommes !'",
                fe02[2], fe02[5], fe02[6]
            ])
            continue

        raw_expr = clean_val(r[1])
        raw_subj = clean_val(r[2])
        raw_ctx = clean_val(r[3])

        subj, angle, lex, emo, scenario = get_french_meta(raw_expr, raw_subj, raw_ctx)

        expr_rows.append([cid, raw_expr, subj, raw_ctx, angle, lex, emo])
        game_rows.append([gid, raw_expr, subj, lex])
        role_rows.append([rid, scenario, subj, lex, emo])

    return expr_rows, game_rows, role_rows

def generate_spanish_rows():
    p = BASE_DIR / "input" / "csv" / "spanish" / "expressions_list" / "SPANISH_READY_PROMPTS_EXPRESSION.csv"
    with open(p, encoding="utf-8-sig") as f:
        raw_rows = list(csv.reader(f))[1:]

    se01 = raw_rows[0]
    se02 = raw_rows[1]

    print(f"Spanish total rows: {len(raw_rows)}")

    def get_spanish_meta(expr, raw_subj, raw_ctx):
        expr_clean = clean_val(expr)
        raw_subj = clean_val(raw_subj).lower()
        raw_ctx = clean_val(raw_ctx)

        if "false_friend" in raw_subj:
            subj = "Falsos amigos en español"
            lex = "Falsos amigos y vocabulario"
            emo = "Sorpresa & Claridad"
            angle = f"Por qué la palabra '{expr_clean.split()[0]}' es una trampa clásica para los que aprenden español"
            scenario = f"En una conversación cotidiana: PERSON_ONE confunde '{expr_clean.split()[0]}' con una palabra de otro idioma. PERSON_TWO reacciona con una sonrisa y le aclara el verdadero sentido nativo: '{raw_ctx}'."
        elif raw_subj in ["expresiones", "idiom"]:
            subj = "Modismos populares en español"
            lex = "Modismos y coloquialismos"
            emo = "Curiosidad & Humor"
            angle = f"El curioso significado y el origen popular de la expresión '{expr_clean}'"
            scenario = f"Entre amigos en una terraza: PERSON_ONE comenta una situación insólita y PERSON_TWO interviene con gracia diciendo: '¡{expr_clean}!', ilustrando perfectamente: '{raw_ctx}'."
        elif raw_subj == "preposition":
            subj = "Preposiciones y régimen verbal"
            lex = "Preposiciones y enlaces"
            emo = "Aha Moment & Precisión"
            angle = f"El secreto para usar correctamente la preposición con '{expr_clean}' sin titubear"
            scenario = f"Al planificar una actividad diaria: PERSON_ONE duda sobre la preposición adecuada. PERSON_TWO le muestra con total seguridad el uso natural: '{raw_ctx}'."
        elif raw_subj in ["grammar", "structure", "phrase"]:
            subj = "Gramática y estructuras en español"
            lex = "Gramática práctica"
            emo = "Aha Moment & Confianza"
            angle = f"La clave para dominar la estructura '{expr_clean}' y sonar como un auténtico nativo"
            scenario = f"En una charla animada: PERSON_ONE comete una leve duda gramatical, y PERSON_TWO le explica de manera muy práctica la fórmula natural: '{raw_ctx}'."
        elif raw_subj == "vocabulary":
            subj = "Vocabulario y diferencias sutiles"
            lex = "Vocabulario y contrastes"
            emo = "Claridad & Confianza"
            angle = f"La diferencia exacta que necesitas conocer para no confundir nunca '{expr_clean}'"
            scenario = f"Al describir una experiencia: PERSON_ONE se confunde entre dos términos parecidos. PERSON_TWO le aclara el matiz exacto con amabilidad: '{raw_ctx}'."
        elif raw_subj == "spelling":
            subj = "Ortografía y acentuación en español"
            lex = "Ortografía y redacción"
            emo = "Claridad & Precisión"
            angle = f"La regla de oro para distinguir de golpe '{expr_clean}' al escribir y al hablar"
            scenario = f"Al escribir un mensaje en el móvil: PERSON_ONE duda sobre la ortografía de '{expr_clean}'. PERSON_TWO le recuerda el truco infalible: '{raw_ctx}'."
        elif raw_subj == "verb":
            subj = "Verbos y perífrasis verbales"
            lex = "Verbos cotidianos"
            emo = "Aha Moment & Soltura"
            angle = f"Cómo utilizar con total naturalidad el verbo '{expr_clean}' en cualquier situación"
            scenario = f"Durante una pausa en el trabajo: PERSON_ONE usa el verbo en un contexto real. PERSON_TWO asiente y refuerza la frase natural: '{raw_ctx}'."
        elif raw_subj == "noun":
            subj = "Género y particularidades de los sustantivos"
            lex = "Sustantivos y artículos"
            emo = "Sorpresa & Claridad"
            angle = f"El truco definitivo para acertar siempre con el género de '{expr_clean}'"
            scenario = f"En una tienda o mercado: PERSON_ONE duda sobre el artículo correcto de '{expr_clean}'. PERSON_TWO le confirma con naturalidad la forma exacta: '{raw_ctx}'."
        elif raw_subj == "adverb":
            subj = "Adverbios y marcadores temporales"
            lex = "Tiempo y aspecto"
            emo = "Claridad & Precisión"
            angle = f"Cómo marcar los tiempos y matices con '{expr_clean}' de forma impecable"
            scenario = f"Al coordinar un encuentro: PERSON_ONE utiliza '{expr_clean}' para precisar el momento exacto. PERSON_TWO comprende al instante: '{raw_ctx}'."
        elif raw_subj in ["collocation", "expression"]:
            subj = "Frases cotidianas y colocaciones"
            lex = "Comunicación cotidiana"
            emo = "Naturalidad & Soltura"
            angle = f"La expresión espontánea '{expr_clean}' que todo hispanohablante usa a diario"
            scenario = f"En el día a día: PERSON_ONE busca la palabra precisa y PERSON_TWO le sugiere la expresión coloquial idónea: '{raw_ctx}'."
        else:
            subj = "Español práctico y cotidiano"
            lex = "Comunicación general"
            emo = "Confianza & Fluidez"
            angle = f"La expresión indispensable '{expr_clean}' para hablar con fluidez y naturalidad"
            scenario = f"En un diálogo distendido: PERSON_ONE y PERSON_TWO conversan animadamente empleando con soltura: '{raw_ctx}'."

        return subj, angle, lex, emo, scenario

    expr_rows = []
    game_rows = []
    role_rows = []

    for i, r in enumerate(raw_rows, start=1):
        cid = f"SE{i:02d}"
        gid = f"SG{i:02d}"
        rid = f"SR{i:02d}"

        if i == 1:
            expr_rows.append(se01)
            game_rows.append([gid, se01[1], se01[2], se01[5]])
            role_rows.append([
                rid,
                "En una tienda de ropa exclusiva: un cliente mira con asombro la etiqueta de precio de una chaqueta. Su amigo se acerca sorprendido y le dice: '¡Oye, déjala ahí, esa chaqueta cuesta un ojo de la cara!'",
                se01[2], se01[5], se01[6]
            ])
            continue
        elif i == 2:
            expr_rows.append(se02)
            game_rows.append([gid, se02[1], se02[2], se02[5]])
            role_rows.append([
                rid,
                "En una cafetería con amigos: uno cuenta una historia inverosímil con expresión muy seria y convence a su amigo. Al ver su reacción de sorpresa total, se ríe y le confiesa: '¡No te lo creas, solo te estaba tomando el pelo!'",
                se02[2], se02[5], se02[6]
            ])
            continue

        raw_expr = clean_val(r[1])
        raw_subj = clean_val(r[2])
        raw_ctx = clean_val(r[3])

        subj, angle, lex, emo, scenario = get_spanish_meta(raw_expr, raw_subj, raw_ctx)

        expr_rows.append([cid, raw_expr, subj, raw_ctx, angle, lex, emo])
        game_rows.append([gid, raw_expr, subj, lex])
        role_rows.append([rid, scenario, subj, lex, emo])

    return expr_rows, game_rows, role_rows

def generate_italian_rows():
    p = BASE_DIR / "input" / "csv" / "italian" / "expressions_list" / "ITALIAN_READY_PROMPTS_EXPRESSION.csv"
    with open(p, encoding="utf-8-sig") as f:
        raw_rows = list(csv.reader(f))[1:]

    ie01 = raw_rows[0]
    ie02 = raw_rows[1]

    print(f"Italian total rows: {len(raw_rows)}")

    def get_italian_meta(expr, raw_subj, raw_ctx, idx):
        expr_clean = clean_val(expr)
        raw_subj = clean_val(raw_subj).lower()
        raw_ctx = clean_val(raw_ctx)

        # Disambiguate row 96 which is false friend with French salir
        if idx == 96 and "fra" in raw_subj:
            expr_clean = "salir (falso amico francese)"

        if "false_friend" in raw_subj:
            if "esp" in raw_subj:
                subj = "Falsi amici spagnolo-italiano"
            elif "fra" in raw_subj:
                subj = "Falsi amici francese-italiano"
            else:
                subj = "Falsi amici inglese-italiano"
            lex = "Falsi amici e vocabolario"
            emo = "Sorpresa & Chiarezza"
            angle = f"Perché la parola '{expr_clean.split()[0]}' trae facilmente in inganno chi impara l'italiano"
            scenario = f"Durante una conversazione informale: PERSON_ONE fraintende '{expr_clean.split()[0]}' a causa della somiglianza con un'altra lingua. PERSON_TWO sorride amichevolmente e gli svela il significato reale in italiano: '{raw_ctx}'."
        elif raw_subj in ["modi di dire", "idiom"]:
            subj = "Espressioni idiomatiche italiane"
            lex = "Modi di dire e proverbi"
            emo = "Curiosità & Umorismo"
            angle = f"Il fascino e la storia autentica dietro il celebre modo di dire '{expr_clean}'"
            scenario = f"Al bar con gli amici: PERSON_ONE descrive un episodio buffo e PERSON_TWO interviene prontamente con ironia esclamando: '{expr_clean}!', commentando: '{raw_ctx}'."
        elif raw_subj == "pronunciation":
            subj = "Pronuncia e doppie consonanti"
            lex = "Fonetica e pronuncia"
            emo = "Sorpresa & Sicurezza"
            angle = f"La fondamentale differenza di suono in '{expr_clean}' che evita figuracce colossali"
            scenario = f"Durante una lezione di lingua: PERSON_ONE pronuncia la parola con una sola consonante invece che doppia. PERSON_TWO gli mostra con una risata complice il contrasto di significato: '{raw_ctx}'."
        elif raw_subj == "preposition":
            subj = "Preposizioni e reggenze verbali"
            lex = "Preposizioni e movimento"
            emo = "Aha Moment & Precisione"
            angle = f"Il segreto pratico per non sbagliare mai la preposizione con '{expr_clean}'"
            scenario = f"Alla stazione o in viaggio: PERSON_ONE è indeciso sulla preposizione corretta. PERSON_TWO gli suggerisce con sicurezza la formula naturale usata da tutti: '{raw_ctx}'."
        elif raw_subj in ["grammar", "structure", "phrase"]:
            subj = "Grammatica e costrutti italiani"
            lex = "Grammatica pratica"
            emo = "Aha Moment & Chiarezza"
            angle = f"Come padroneggiare la struttura '{expr_clean}' e parlare come un vero italiano"
            scenario = f"In una chiacchierata quotidiana: PERSON_ONE esprime un pensiero con incertezza, e PERSON_TWO riformula la frase con estrema spontaneità: '{raw_ctx}'."
        elif raw_subj == "vocabulary":
            subj = "Vocabolario e sfumature d'uso"
            lex = "Vocabolario e contrasti"
            emo = "Chiarezza & Sicurezza"
            angle = f"La regola semplice ed efficace per distinguere '{expr_clean}' senza dubbi"
            scenario = f"Parlando del tempo o dei progetti: PERSON_ONE confonde due termini simili. PERSON_TWO chiarisce il contrasto con un esempio cristallino: '{raw_ctx}'."
        elif raw_subj == "noun":
            subj = "Genere e particolarità dei sostantivi"
            lex = "Sostantivi e articoli"
            emo = "Sorpresa & Precisione"
            angle = f"L'inganno del genere maschile o femminile in '{expr_clean}' finalmente chiarito"
            scenario = f"In una galleria o in centro: PERSON_ONE usa l'articolo sbagliato per '{expr_clean}'. PERSON_TWO gli ricorda sorridendo la particolarità del sostantivo: '{raw_ctx}'."
        elif raw_subj in ["verb", "phrasal_verb"]:
            subj = "Verbi pronominali e perifrasi"
            lex = "Verbi del quotidiano"
            emo = "Aha Moment & Fluidità"
            angle = f"Come adoperare il verbo '{expr_clean}' per dare dinamismo al tuo discorso"
            scenario = f"A fine giornata: PERSON_ONE impiega il verbo in un momento spontaneo. PERSON_TWO annuisce con complicità dicendo: '{raw_ctx}'."
        elif raw_subj == "adverb":
            subj = "Avverbi e marcatori temporali"
            lex = "Tempo e durata"
            emo = "Precisione & Chiarezza"
            angle = f"Come esprimere il tempo e le sfumature con l'avverbio '{expr_clean}'"
            scenario = f"Aspettando un arrivo: PERSON_ONE esclama '{expr_clean}' guardando l'orologio. PERSON_TWO risponde con soddisfazione: '{raw_ctx}'."
        elif raw_subj in ["collocation", "expression"]:
            subj = "Espressioni comuni e formule comunicative"
            lex = "Conversazione quotidiana"
            emo = "Naturalezza & Cordialità"
            angle = f"La formula di cortesia o espressione naturale '{expr_clean}' da usare subito"
            scenario = f"In un incontro amichevole: PERSON_ONE e PERSON_TWO si scambiano battute calorose usando la tipica espressione italiana: '{raw_ctx}'."
        else:
            subj = "Italiano pratico e quotidiano"
            lex = "Comunicazione generale"
            emo = "Fiducia & Spontaneità"
            angle = f"La parola essenziale '{expr_clean}' per interagire con scioltezza in ogni occasione"
            scenario = f"In una vivace discussione in piazza: PERSON_ONE e PERSON_TWO dialogano con entusiasmo usando: '{raw_ctx}'."

        return expr_clean, subj, angle, lex, emo, scenario

    expr_rows = []
    game_rows = []
    role_rows = []

    for i, r in enumerate(raw_rows, start=1):
        cid = f"IE{i:02d}"
        gid = f"IG{i:02d}"
        rid = f"IR{i:02d}"

        if i == 1:
            expr_rows.append(ie01)
            game_rows.append([gid, ie01[1], ie01[2], ie01[5]])
            role_rows.append([
                rid,
                "Davanti all'università prima dell'esame decisivo: uno studente visibilmente agitato ripassa i suoi appunti tremando. La sua compagna di corso lo rassicura con un sorriso luminoso e gli augura con energia: 'In bocca al lupo!'",
                ie01[2], ie01[5], ie01[6]
            ])
            continue
        elif i == 2:
            expr_rows.append(ie02)
            game_rows.append([gid, ie02[1], ie02[2], ie02[5]])
            role_rows.append([
                rid,
                "In un centro commerciale a Milano: un ragazzo sfoggia tre sacchetti di vestiti appena comprati. Il suo amico lo guarda sconvolto e scherza dicendo: 'Ma hai proprio le mani bucate oggi!'",
                ie02[2], ie02[5], ie02[6]
            ])
            continue

        raw_expr = clean_val(r[1])
        raw_subj = clean_val(r[2])
        raw_ctx = clean_val(r[3])

        expr_clean, subj, angle, lex, emo, scenario = get_italian_meta(raw_expr, raw_subj, raw_ctx, i)

        expr_rows.append([cid, expr_clean, subj, raw_ctx, angle, lex, emo])
        game_rows.append([gid, expr_clean, subj, lex])
        role_rows.append([rid, scenario, subj, lex, emo])

    return expr_rows, game_rows, role_rows

def write_csv_files(lang, expr_rows, game_rows, role_rows):
    d = BASE_DIR / "input" / "csv" / lang / "expressions_list"

    expr_header = ["ID", "EXPRESSION", "SUBJECT", "CONTEXT", "ANGLE", "LEXICAL_FIELD", "EMOTIONAL_TRIGGER"]
    game_header = ["ID", "EXPRESSION", "SUBJECT", "LEXICAL_FIELD"]
    role_header = ["ID", "ROLEPLAY_SCENARIO", "SUBJECT", "LEXICAL_FIELD", "EMOTIONAL_TRIGGER"]

    p_expr = d / f"{lang.upper()}_READY_PROMPTS_EXPRESSION.csv"
    p_game = d / f"{lang.upper()}_READY_PROMPTS_GAME.csv"
    p_role = d / f"{lang.upper()}_READY_PROMPTS_ROLEPLAY.csv"

    with open(p_expr, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(expr_header)
        w.writerows(expr_rows)

    with open(p_game, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(game_header)
        w.writerows(game_rows)

    with open(p_role, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(role_header)
        w.writerows(role_rows)

    print(f"[{lang.upper()}] Written {len(expr_rows)} rows across EXPRESSION, GAME, and ROLEPLAY.")

def main():
    print("Generating French prompts...")
    fr_expr, fr_game, fr_role = generate_french_rows()
    write_csv_files("french", fr_expr, fr_game, fr_role)

    print("Generating Spanish prompts...")
    sp_expr, sp_game, sp_role = generate_spanish_rows()
    write_csv_files("spanish", sp_expr, sp_game, sp_role)

    print("Generating Italian prompts...")
    it_expr, it_game, it_role = generate_italian_rows()
    write_csv_files("italian", it_expr, it_game, it_role)

    print("All language prompts successfully generated!")

if __name__ == "__main__":
    main()
