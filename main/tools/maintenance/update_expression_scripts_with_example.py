"""
update_expression_scripts_with_example.py

Enriches all existing EXPRESSION scripts across English, French, Italian, and Spanish
with authentic in-context example sentences ("example"), normalizes legacy keys,
and updates state files and review CSVs.
"""

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.auditing.scrapper_script import process_scripts

# Curated, highly natural in-context example phrases for all existing scripts
EXAMPLES_CATALOG = {
    # ENGLISH (EE01 - EE10)
    "EE01": "For example, right before she walked onto the stage: 'You've practiced all week, now go out there and break a leg!'",
    "EE02": "For example, after finishing the final exam in ten minutes: 'Don't worry about that test, it was a piece of cake!'",
    "EE03": "For example in the studio: 'We finished the vinyl record, so now let's record the live performance with energy!'",
    "EE04": "For example at the meeting: 'I have a special present for the team, and I will present our strategy now.'",
    "EE05": "For example in architecture: 'Our big design project is complete, so let's project the blueprints onto the screen.'",
    "EE06": "For example at city hall: 'You need an official parking permit before the city council will permit you to park here.'",
    "EE07": "For example in court: 'That strange physical object is critical evidence, and the defense will definitely object to it.'",
    "EE08": "For example in business: 'Make sure you read the employment contract carefully before your responsibilities contract any further.'",
    "EE09": "For example in finance: 'We noticed a massive salary increase this quarter as profits continue to increase every month.'",
    "EE10": "For example in sales: 'The sudden decrease in production costs will steadily decrease our overall prices this winter.'",

    # FRENCH (FE01 - FE10)
    "FE01": "Par exemple, en attendant au café : 'J'ai attendu plus d'une heure sous la pluie, il m'a encore posé un lapin !'",
    "FE02": "Par exemple, après une semaine harassante : 'Ouvre vite la fenêtre, avec cette chaleur étouffante je vais tomber dans les pommes !'",
    "FE03": "Par exemple, un dimanche pluvieux d'hiver : 'Ce temps gris et froid me donne le cafard, je préfère rester sous la couette.'",
    "FE04": "Par exemple, devant une idée farfelue : 'Vendre ton appartement pour acheter une île déserte ? Mais tu yoyotes complètement de la touffe !'",
    "FE05": "Par exemple, pour réconforter un collègue : 'Remplir ce formulaire ne prend que deux minutes, franchement, c'est pas la mer à boire !'",
    "FE06": "Par exemple, après un accident de vélo : 'Le cycliste est tombé lourdement et il est blessé au genou, appelons vite les secours.'",
    "FE07": "Par exemple, à la boulangerie le matin : 'Le croissant coûte un euro cinquante, avez-vous de la monnaie sur ce billet ?'",
    "FE08": "Par exemple, lors d'un appel professionnel : 'Je suis actuellement en réunion avec la direction, puis-je vous rappeler dans dix minutes ?'",
    "FE09": "Par exemple, devant la station de métro : 'Je t'attends sur le quai depuis vingt minutes, dépêche-toi le train arrive !'",
    "FE10": "Par exemple, en réservant une place : 'Des milliers de passionnés sont venus assister à la conférence internationale ce matin.'",

    # ITALIAN (IE01 - IE10)
    "IE01": "Per esempio, prima dell'esame all'università: 'Hai studiato giorno e notte, in bocca al lupo per domani mattina!'",
    "IE02": "Per esempio, durante lo shopping del sabato: 'Ha speso tutto lo stipendio nel primo pomeriggio, ha proprio le mani bucate!'",
    "IE03": "Per esempio, affrontando una crisi sul lavoro: 'Basta rimandare la decisione importante, dobbiamo prendere il toro per le corna e risolverla.'",
    "IE04": "Per esempio, preparando una cena veloce: 'Mentre apparecchi il tavolo, ti preparo un piatto di pasta delizioso in quattro e quattr'otto!'",
    "IE05": "Per esempio, prima di inviare la candidatura: 'Invia quel curriculum per la posizione dei tuoi sogni, in fondo tentar non nuoce!'",
    "IE06": "Per esempio, quando un amico offre un passaggio: 'Stava per scoppiare il temporale e sei arrivato con l'auto, capiti proprio a fagiolo!'",
    "IE07": "Per esempio, parlando delle vacanze estive: 'L'anno scorso abbiamo viaggiato in Sicilia ed è stata un'esperienza davvero indimenticabile.'",
    "IE08": "Per esempio, dopo una bella sorpresa: 'Abbiamo fatto un lavoro straordinario insieme, non è stato solo merito del fato.'",
    "IE09": "Per esempio, durante il pranzo di Natale: 'Tutti i miei parenti, tra zii e cugini, si riuniscono a tavola per festeggiare insieme.'",
    "IE10": "Per esempio, provando una coperta invernale: 'Questo maglione di pura lana vergine è incredibilmente morbido e caldo sulla pelle.'",

    # SPANISH (SE01 - SE12)
    "SE01": "Por ejemplo, al pedir la cuenta: '¡Ochenta euros por dos cafés y una tostada! ¡Esto cuesta un ojo de la cara!'",
    "SE02": "Por ejemplo, entre risas con amigos: '¿Que te has comprado un coche deportivo rojo? ¡Venga ya, me estás tomando el pelo!'",
    "SE03": "Por ejemplo, hablando de una canción viral: 'Pones la radio, abres TikTok y ahí suena, ¡esa canción está hasta en la sopa!'",
    "SE04": "Por ejemplo, al salir de una prueba: 'El examen práctico de conducir fue facilísimo, para mí fue pan comido.'",
    "SE05": "Por ejemplo, al olvidar una entrega crucial: 'Si el profesor descubre que no entregué el proyecto final hoy, estoy completamente frito.'",
    "SE06": "Por ejemplo, en una reunión tensa: 'Deja de andarte por las ramas con rodeos y dime la cifra exacta del problema.'",
    "SE07": "Por ejemplo, en un restaurante lleno: 'Con tantos pedidos entrando a la vez en la cocina, los camareros no damos abasto hoy.'",
    "SE08": "Por ejemplo, dando una gran noticia familiar: 'Mi hermana mayor nos anunció emocionada que está embarazada de su primer hijo.'",
    "SE09": "Por ejemplo, celebrando el estreno: 'La presentación de la nueva aplicación fue un éxito rotundo en toda la ciudad.'",
    "SE10": "Por ejemplo, organizando la oficina: 'Guarda todos los contratos firmados dentro de esta carpeta azul para no perderlos jamás.'",
    "SE11": "Por ejemplo, en pleno invierno: 'Con este frío he pillado un buen constipado, tengo la nariz tapada y mucha tos.'",
    "SE12": "Por ejemplo, al llegar al aeropuerto: 'Al llegar al mostrador de facturación, me di cuenta de que había olvidado el pasaporte en casa.'",
}


def normalize_script_dict(script_dict: dict, script_id: str) -> dict:
    """Normalizes legacy keys to canonical (hook, setup, discovery, example, payoff)."""
    norm = {}
    
    # Lowercase key map
    raw_lower = {k.strip().lower(): v for k, v in script_dict.items()}

    # Title
    norm["title"] = raw_lower.get("title", f"Script {script_id}")

    # Hook
    norm["hook"] = raw_lower.get("hook", "")

    # Setup (fallback to core_learning)
    norm["setup"] = raw_lower.get("setup") or raw_lower.get("core learning") or raw_lower.get("core_learning", "")

    # Discovery (fallback to emphasis)
    norm["discovery"] = raw_lower.get("discovery") or raw_lower.get("emphasis", "")

    # Example
    if script_id in EXAMPLES_CATALOG:
        norm["example"] = EXAMPLES_CATALOG[script_id]
    else:
        norm["example"] = raw_lower.get("example", "")

    # Payoff (fallback to loop_trigger)
    norm["payoff"] = raw_lower.get("payoff") or raw_lower.get("loop trigger") or raw_lower.get("loop_trigger", "")

    return norm


def update_all_expression_scripts():
    state_dir = PROJECT_ROOT / "state"
    languages = ["english", "french", "italian", "spanish"]

    updated_count = 0

    print("=" * 65)
    print("UPDATING EXPRESSION SCRIPTS WITH 'EXAMPLE' SECTION")
    print("=" * 65)

    for lang in languages:
        expr_dir = state_dir / lang / "expression"
        if not expr_dir.exists():
            continue

        for state_file in sorted(expr_dir.glob("script_*.json")):
            try:
                with state_file.open("r", encoding="utf-8") as f:
                    state = json.load(f)
            except Exception as e:
                print(f"[Error] reading {state_file.name}: {e}")
                continue

            script_id = state.get("id") or state_file.stem.replace("script_", "")
            
            content_meta = state.get("content_metadata") or {}
            current_script = content_meta.get("script") or {}
            
            if not current_script and "script_text" in state:
                try:
                    st = state["script_text"].strip()
                    if st.startswith("```json"):
                        st = st[7:]
                    if st.startswith("```"):
                        st = st[3:]
                    if st.endswith("```"):
                        st = st[:-3]
                    current_script = json.loads(st.strip())
                except Exception:
                    current_script = {}

            # Normalize & insert example
            new_script = normalize_script_dict(current_script, script_id)
            
            # Recalculate word count
            words = sum(len(str(v).split()) for k, v in new_script.items() if k != "title")

            # Update state dictionary
            content_meta["script"] = new_script
            state["content_metadata"] = content_meta
            state["script_text"] = json.dumps(new_script, ensure_ascii=False, indent=2)

            with state_file.open("w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=4)

            updated_count += 1
            print(f"[{script_id}] Updated successfully -> {words} spoken words across 5 sections")

    print("=" * 65)
    print(f"Successfully enriched {updated_count} expression scripts!")
    print("Regenerating review CSVs in output/scripts_to_see...")
    print("=" * 65)

    # Re-scrape to CSV
    process_scripts(
        base_dir=PROJECT_ROOT,
        target_types=["expression"],
        include_tags=True,
        include_title=True
    )
    print("Done!")


if __name__ == "__main__":
    update_all_expression_scripts()
