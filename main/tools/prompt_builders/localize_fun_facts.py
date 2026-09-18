"""
localize_fun_facts.py
Localizes FUN_FACTS prompts for French, Spanish, and Italian to use the video's target language.
"""

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

french_fun_facts = [
    [
        "FF01",
        "Pourquoi les nombres français font des maths (Quatre-vingts)",
        "LANGUAGE_HISTORY",
        "ONE_BIG_CURIOSITY",
        "Les nombres français 70 (soixante-dix), 80 (quatre-vingts = 4 fois 20) et 90 (quatre-vingt-dix) utilisent un système vicésimal (base 20) hérité des Gaulois celtes et des Vikings. En revanche, le français suisse et belge utilise le système décimal régulier : septante, huitante et nonante.",
        "Pourquoi le français vous oblige-t-il à résoudre une équation mathématique juste pour dire le chiffre 80 ?",
        "Amusement & Surprise"
    ],
    [
        "FF02",
        "Le mot Oiseau brise toutes les règles de prononciation",
        "PRONUNCIATION_CURIOSITIES",
        "ONE_BIG_CURIOSITY",
        "Le mot français 'oiseau' contient toutes les voyelles fondamentales (A, E, I, O, U), pourtant aucune d'entre elles n'est prononcée avec le son de sa propre lettre. Il se prononce simplement /wa.zo/.",
        "Ce mot français contient toutes les voyelles de l'alphabet, mais vous n'en prononcez AUCUNE !",
        "Surprise & Fascination"
    ],
    [
        "FF03",
        "Un mot français avec 3 lettres E consécutives",
        "WORD_CURIOSITIES",
        "CHALLENGE",
        "Le participe passé féminin 'créée' (du verbe créer) contient trois lettres E d'affilée : le premier avec accent aigu (é), le deuxième pour l'accord féminin muet (e), et même un quatrième au pluriel (créées = 4 E).",
        "Pouvez-vous deviner le vrai mot de la langue française qui s'écrit avec TROIS lettres 'E' d'affilée ?",
        "Défi ludique & Curiosité"
    ],
    [
        "FF04",
        "4 mots français qui se prononcent exactement pareil",
        "PRONUNCIATION_CURIOSITIES",
        "3_FACTS",
        "Ver (l'animal), Verre (pour boire), Vers (en direction de ou poésie) et Vert (la couleur) se prononcent tous de façon 100% identique /vɛʁ/ malgré des étymologies et orthographes totalement différentes.",
        "4 mots français complètement différents qui se prononcent exactement de la même manière : comment font les natifs pour se comprendre ?",
        "Humour & Incrédulité"
    ],
    [
        "FF05",
        "Le français a été la langue officielle de l'Angleterre pendant 300 ans",
        "LANGUAGE_HISTORY",
        "MYSTERY",
        "Après la conquête de Guillaume le Conquérant en 1066, le français anglo-normand a été la langue officielle de la cour d'Angleterre, de la justice et de l'aristocratie pendant plus de 300 ans. C'est pourquoi plus de 30% du vocabulaire anglais moderne vient en fait du français.",
        "La raison historique fascinante pour laquelle l'anglais et le français partagent des milliers de mots identiques.",
        "Mystère & Découverte"
    ]
]

spanish_fun_facts = [
    [
        "SF01",
        "El signo de interrogación invertido se inventó en 1754",
        "LANGUAGE_HISTORY",
        "ONE_BIG_CURIOSITY",
        "La Real Academia Española instauró los signos de interrogación (¿) y exclamación (¡) invertidos en 1754 para que los lectores en voz alta supieran con qué entonación empezar antes de llegar al final de las frases largas.",
        "El español es el único idioma en el mundo que te avisa con un signo al revés antes de que empiece una pregunta.",
        "Curiosidad & Fascinación"
    ],
    [
        "SF02",
        "Más de 4.000 palabras en español provienen del árabe",
        "ETYMOLOGY",
        "3_FACTS",
        "Más de 4.000 palabras en español provienen directamente de ocho siglos de presencia árabe en Al-Ándalus. Casi todas las palabras que empiezan por 'al-' (almohada, alcázar, albaricoque) más 'ojalá' (wa sha Allah) y 'aceite' tienen raíces árabes.",
        "3 palabras en español que usas todos los días y que en realidad son puro árabe camuflado.",
        "Descubrimiento & Sorpresa"
    ],
    [
        "SF03",
        "La intraducible sobremesa española",
        "CULTURAL_DIFFERENCES",
        "ONE_BIG_CURIOSITY",
        "'Sobremesa' describe el sagrado ritual social de quedarse sentado alrededor de la mesa después de comer, tomando café y conversando durante horas con amigos y familiares. No tiene una sola palabra equivalente en muchos idiomas.",
        "Un ritual español tan sagrado culturalmente que otros idiomas ni siquiera tienen una palabra para definirlo.",
        "Calidez & Fascinación"
    ],
    [
        "SF04",
        "La letra Ñ se inventó para ahorrar papel",
        "LANGUAGE_HISTORY",
        "MYSTERY",
        "Los monjes copistas medievales, para ahorrar el costoso pergamino, dejaron de escribir la doble 'nn' latina (como 'annus' -> 'año'). En su lugar, colocaron una pequeña 'n' abreviada encima de la letra, creando la famosa virgulilla de la Ñ.",
        "La letra más representativa del español fue inventada por monjes medievales para ahorrar dinero en pergamino.",
        "Humor & Asombro"
    ],
    [
        "SF05",
        "Embarazada NO significa avergonzada (Embarrassed)",
        "WORD_CURIOSITIES",
        "CHALLENGE",
        "'Embarazada' en español significa que estás esperando un bebé, mientras que 'embarrassed' se traduce como avergonzado o avergonzada. Decir 'estoy embarazada' por error no anuncia un sonrojo, ¡anuncia un bebé sorpresa!",
        "El falso amigo más peligroso del español que puede hacerte anunciar un embarazo por accidente.",
        "Reto divertido & Humor"
    ]
]

italian_fun_facts = [
    [
        "IF01",
        "L'alfabeto italiano ha soltanto 21 lettere",
        "LANGUAGE_CURIOSITIES",
        "ONE_BIG_CURIOSITY",
        "L'alfabeto italiano standard ha soltanto 21 lettere autoctone. Le lettere J, K, W, X e Y non fanno parte dell'alfabeto nativo e si usano solo nei prestiti linguistici come 'jeans', 'kiwi' o 'weekend'.",
        "L'italiano ha bandito 5 lettere dal suo alfabeto e gli italiani non ne hanno mai sentito la mancanza!",
        "Curiosità & Sorpresa"
    ],
    [
        "IF02",
        "L'amichevole saluto Ciao ha origine dagli schiavi veneziani",
        "ETYMOLOGY",
        "MYSTERY",
        "'Ciao' deriva dall'antico saluto dialettale veneziano 's-ciào vostro' o 's-ciavo', che significava 'sono vostro schiavo / umile servitore' (dal latino medievale 'sclavus'). Con i secoli i veneziani lo hanno abbreviato in 'ciao', trasformandolo nel saluto informale più celebre al mondo.",
        "Il saluto italiano più amichevole e famoso al mondo nasconde un'origine storica incredibilmente oscura.",
        "Sorpresa & Fascinazione"
    ],
    [
        "IF03",
        "I gesti italiani sono una vera e propria seconda grammatica",
        "CULTURAL_DIFFERENCES",
        "3_FACTS",
        "I linguisti hanno catalogato oltre 250 gesti distinti delle mani usati in Italia. Nati durante i secoli di dominazioni straniere e forti differenze dialettali, formano un linguaggio universale silenzioso e ricchissimo.",
        "3 gesti delle mani italiani capaci di comunicare frasi intere e complesse senza aprire bocca.",
        "Divertimento & Scoperta"
    ],
    [
        "IF04",
        "Quando l'Italia fu unificata quasi nessuno parlava italiano",
        "LANGUAGE_HISTORY",
        "ONE_BIG_CURIOSITY",
        "Al momento dell'unificazione nel 1861, solo circa il 2,5% della popolazione parlava italiano standard; tutti gli altri parlavano dialetti e lingue regionali distinte come siciliano, napoletano o veneziano. L'italiano moderno si basa sul capolavoro fiorentino del Trecento di Dante Alighieri.",
        "Quando l'Italia divenne una nazione unita, praticamente quasi nessun italiano parlava la lingua italiana!",
        "Incredulità & Storia"
    ],
    [
        "IF05",
        "La parola comune più lunga della lingua italiana",
        "EXTREMES",
        "CHALLENGE",
        "'Precipitevolissimevolmente' (26 lettere) significa 'con grandissima fretta e precipitazione'. Fu coniata dal poeta Francesco Moneti nel 1677 ed è considerata la parola d'uso comune più lunga della lingua italiana.",
        "Riesci a pronunciare la parola di 26 lettere più lunga dell'italiano senza annodarti la lingua?",
        "Sfida giocosa & Divertimento"
    ]
]

header = ["ID", "TOPIC", "PILLAR", "FORMAT", "FACT_DETAILS", "HOOK_ANGLE", "EMOTIONAL_TRIGGER"]

def write_fun_facts(lang, rows):
    p = BASE_DIR / "input" / "csv" / lang / "expressions_list" / f"{lang.upper()}_READY_PROMPTS_FUN_FACTS.csv"
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"[{lang.upper()}] Written localized FUN_FACTS to {p.name}")

def main():
    write_fun_facts("french", french_fun_facts)
    write_fun_facts("spanish", spanish_fun_facts)
    write_fun_facts("italian", italian_fun_facts)
    print("All FUN_FACTS files successfully localized into their video languages!")

if __name__ == "__main__":
    main()
