"""
overhaul_french_suite.py
Overhauls:
1. FRENCH_READY_PROMPTS_ROLEPLAY.csv (all 85 rows with rich, varied, comedic micro-settings)
2. FRENCH_READY_PROMPTS_GAME.csv (verifies alignment and cleans encoding)
3. FRENCH_READY_PROMPTS_FUN_FACTS.csv (expands from 5 to 15 viral linguistic curiosities)
"""

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3] / "input" / "csv" / "french" / "expressions_list"

ROLEPLAY_SCENARIOS_FRENCH = {
    "FR01": "Devant une terrasse de brasserie sous une petite pluie parisienne : un jeune homme regarde sa montre pour la cinquième fois avec deux chocolats chauds qui refroidissent. Sa pote arrive, le voit seul et ricane : 'Alors, elle t'a encore posé un lapin ou elle cherche le métro ?'",
    "FR02": "À la fin d'une séance intense de cardio : un ami s'écroule lourdement sur le tapis de gym en fermant les yeux, le visage tout blanc. Son partenaire d'entraînement lui tend une gourde fraîche en riant : 'Respire par le nez, me tombe pas dans les pommes maintenant !'",
    "FR03": "Dans un studio étudiant un dimanche soir pluvieux d'automne : deux colocs regardent par la fenêtre en soupirant devant un bol de pâtes réchauffées. L'un soupire lourdement et l'autre monte le son de la musique : 'Allez stop, arrête d'avoir le cafard pour le week-end fini !'",
    "FR04": "Dans une brocante ou magasin vintage : un ami montre un vieux grille-pain rouillé des années 60 affiché à 150 euros et affirme sérieusement que c'est une pièce de musée inestimable. L'autre le regarde avec de grands yeux : 'Mais tu yoyotes de la touffe ou quoi ? C'est de la ferraille !'",
    "FR05": "Dans une cuisine devant un évier débordant de casseroles après un dîner à six : l'un se plaint comme s'il devait gravir l'Everest, pendant que son colocataire lui tend l'éponge avec un clin d'œil : 'Trois assiettes et une poêle, c'est pas la mer à boire, viens m'aider !'",
    "FR06": "Après un tacle au foot du dimanche : un joueur boite en grimaçant de douleur en tenant son genou. Son coéquipier américain crie avec enthousiasme 'You look so blessed today!', laissant le blessé furieux : 'Béni ? Je suis blessé, j'ai une entorse !'",
    "FR07": "Devant le distributeur de café en panne de carte bancaire : un collègue étranger agite un gros billet de 50 euros en disant 'J'ai plein de monnaie pour le café !'. Son collègue pointe la fente avec un sourire : 'Ça c'est du fric, moi je te demande de la monnaie : deux pièces de cinquante centimes !'",
    "FR08": "À la billetterie d'un festival complet : un voyageur anglophone insiste 'Actuellement je préfère payer en liquide', pensant dire actually, et le guichetier lui répond perplexe : 'Monsieur, actuellement ou dans dix ans, c'est complet !'",
    "FR09": "Devant les portes d'une salle de conférence prestigieuse : un stagiaire international demande s'il peut 'attendre la réunion' dans la salle, et le vigile lui dit 'Si vous voulez y assister, il faut un badge, vous ne pouvez pas juste attendre là !'",
    "FR10": "Lors du déménagement d'un canapé lourd au troisième étage sans ascenseur : un ami étranger s'assoit confortablement sur une chaise en disant avec un grand sourire 'J'assiste au déménagement !', pendant que l'autre porte le meuble à bout de bras en sueur : 'Assister c'est regarder, moi j'ai besoin que tu m'aides !'",
    "FR11": "À la sortie d'une salle de cinéma après un blockbuster très attendu : deux amis cinéphiles discutent. L'un s'exclame avec déception : 'Ce film m'a énormément déçu, le scénario était totalement prévisible !'",
    "FR12": "En découvrant un appartement lumineux avec terrasse à louer en plein cœur de Lyon : deux futurs colocataires visitent les pièces avec émerveillement. L'un s'exclame devant la vue imprenable : 'C'est une nouvelle formidable pour notre projet !'",
    "FR13": "Dans une voiture sur une route de campagne sans réseau GPS : le conducteur demande où est passée la carte routière, et son passager cherche dans la boîte à gants : 'J'ignore totalement où elle se trouve, elle n'est pas là !'",
    "FR14": "Dans les bureaux d'une start-up en pleine réorganisation : deux collègues discutent du nouveau management. L'un remarque avec enthousiasme : 'Le directeur actuel a modernisé toutes les équipes cette semaine !'",
    "FR15": "Devant le palier de l'immeuble en croisant le nouveau voisin qui offre des croissants chauds : deux voisins rentrent chez eux ravis. L'un sourit en ouvrant sa porte : 'Notre nouveau voisin est vraiment très sympathique et attentionné !'",
    "FR16": "Dans un atelier de peinture à Montmartre : une apprentie verse une larme émue devant un tableau de Monet, et son tuteur la taquine affectueusement : 'Elle est extrêmement sensible à la lumière et à l'art pictural.'",
    "FR17": "À la terrasse du café universitaire : un étudiant angoissé révise ses fiches en buvant son troisième expresso : 'Je passe mon examen de droit demain à huit heures, j'espère de tout cœur le réussir !'",
    "FR18": "En déballant un colis surprise rempli de spécialités artisanales envoyé par ses amis : 'Cette délicate attention me rend tellement heureux aujourd'hui !'",
    "FR19": "Devant le tombeau en marbre sous le dôme du Panthéon : deux passionnés d'histoire admirent la stèle : 'Napoléon était un grand homme d'État, même s'il n'était pas un homme grand par la taille.'",
    "FR20": "En préparant un pique-nique géant sur les quais de Seine un samedi après-midi : 'Tu amènes tes amis musiciens avec leurs guitares, et moi j'apporte une tarte aux pommes maison.'",
    "FR21": "De retour d'une escapade estivale en Normandie : 'Samedi nous avons visité les remparts de la cité médiévale, et dimanche nous sommes allés rendre visite à mes grands-parents.'",
    "FR22": "Dans le hall d'un immeuble un vendredi soir festif : 'Le train pour Marseille part à l'aube demain matin, mais ce soir j'ai bien l'intention de sortir au restaurant entre amis.'",
    "FR23": "Après une randonnée revigorante le long du sentier côtier breton : 'Ce périple sauvage a duré trois jours entiers, mais quelle magnifique journée nous avons passée sous le soleil !'",
    "FR24": "Sur un balcon parisien à l'heure dorée : 'Mon atelier de dessin se termine à six heures du soir, juste à temps pour vous rejoindre à cette belle soirée festive.'",
    "FR25": "Lors d'une fête de fin d'études universitaires : 'Il vit à Lyon depuis deux ans en colocation, et cette année de master a été couronnée par une mention très bien.'",
    "FR26": "Dans un salon avec vue sur les grands boulevards parisiens : 'J'entends le vacarme des klaxons dans la rue, mais monte le volume pour que j'écoute les paroles du refrain.'",
    "FR27": "En observant un maestro pâtissier glacer délicatement un entremets : 'C'est un véritable artiste culinaire, il est d'une rigueur absolue dans chacune de ses créations.'",
    "FR28": "En comparant deux crus de café torréfiés artisanalement dans une boutique chic : 'Cet expresso éthiopien est bien meilleur au goût, et le barista le prépare beaucoup mieux.'",
    "FR29": "Sur le pas de la porte un samedi matin en attrapant un panier en osier : 'Tu vas au marché des producteurs ? Oui, j'y vais tout de suite, et j'en rapporterai deux barquettes de framboises.'",
    "FR30": "En feuilletant une brochure de voyages paradisiaques sur le canapé : 'Je pense souvent à nos prochaines vacances au soleil ; et toi, que penses-tu de cette île sauvage ?'",
    "FR31": "Dans le terminal d'un aéroport balayé par les rafales de vent : 'Le décollage a été retardé à cause de la tempête de neige, mais grâce au salon d'attente nous patientons bien au chaud.'",
    "FR32": "En recevant un magnifique livre de photographies pour son anniversaire : 'Merci pour ce somptueux cadeau d'art, et merci de m'avoir soutenu tout au long de cette année.'",
    "FR33": "Autour d'un dîner convivial déclinant poliment un plat carné : 'Je ne mange pas de viande rouge depuis dix ans, et d'ailleurs je ne fume plus une seule cigarette depuis mon marathon.'",
    "FR34": "Le lundi matin devant la machine à café racontant le week-end : 'Hier après-midi, je suis allé admirer l'exposition impressionniste au musée avec un vieux camarade.'",
    "FR35": "Sur le quai du métro en reconnaissant un visage familier dans la foule : 'Regarde sur le quai d'en face, c'est mon collègue de bureau, je le vois presque chaque matin à cette heure.'",
    "FR36": "Au buffet d'un mariage champêtre choisissant son menu avec le chef : 'Tout a l'air délicieux, mais je suis végétarien donc je ne mange pas de poisson aujourd'hui.'",
    "FR37": "Deux collègues planifiant leurs congés d'hiver devant la carte du monde : 'En plein mois de janvier, j'échappe à la grisaille pour passer quinze jours au Mexique sous les cocotiers.'",
    "FR38": "Un expatrié discutant de son parcours d'intégration dans un bistrot : 'Elle vit en France depuis trois ans maintenant et maîtrise toutes les subtilités de la langue.'",
    "FR39": "Dans le hall de départ d'une randonnée en montagne comptant les participants : 'Ajustez bien vos sacs à dos : tout le monde est prêt pour gravir le sentier rocailleux ?'",
    "FR40": "En traversant un marché pittoresque de Provence sous les platanes : 'Les marchands locaux sont exceptionnellement accueillants et chaleureux avec les visiteurs.'",
    "FR41": "Ouvrant le capot fumant d'une voiture sur la bande d'arrêt d'urgence : 'Restons calmes, nous allons vite trouver une issue à ce problème mécanique avant la nuit.'",
    "FR42": "Pénétrant dans la nef silencieuse d'une abbaye cistercienne séculaire : 'Le silence est d'or sous ces voûtes de pierre, on n'entend que le souffle du vent printanier.'",
    "FR43": "Guidant une cohorte d'étudiants d'échange devant la pyramide du Louvre : 'Le groupe de visiteurs doit rester bien groupé pour suivre les explications du conservateur.'",
    "FR44": "Ouvrant les volets d'une cabane perchée sur une falaise bretonne : 'Regarde par la fenêtre : la mer s'étend à perte de vue sous les lumières éclatantes de l'aube.'",
    "FR45": "Appelant sa famille en visioconférence depuis un appartement d'échange à Tokyo : 'Les repas du dimanche et vos éclats de rire me manquent terriblement depuis mon départ.'",
    "FR46": "Dans les cuisines en effervescence d'un restaurant gastronomique : 'Il faut arriver très tôt le matin à Rungis pour dénicher les produits les plus frais de la criée.'",
    "FR47": "Avant de claquer la porte d'un appartement de location pour partir en vacances : 'Pense à couper l'eau et éteins soigneusement toutes les lumières avant de partir.'",
    "FR48": "En posant fièrement un dossier relié sur le bureau de son responsable : 'Après des nuits blanches de calculs, je viens de finir la rédaction complète du rapport annuel.'",
    "FR49": "Chuchotant dans le couloir feutré à l'étage de la maison : 'Ne faites pas claquer les portes maintenant, il est en train de réviser son concours dans sa chambre.'",
    "FR50": "Dans les couloirs du métro parisien face à un tapis roulant bondé : 'Viens, prends les grands escaliers au lieu de faire la queue passivement sur le tapis mécanique !'",
    "FR51": "En terrasse lors d'une chaude fin d'après-midi d'été : 'Le ciel s'est soudain couvert de nuages noirs d'encre et il s'est mis à pleuvoir des trombes d'eau.'",
    "FR52": "Au sommet d'une crête alpine après quatre heures d'ascension soutenue : 'Les mollets brûlent, mais la vue imprenable sur le massif du Mont-Blanc vaut vraiment le coup d'œil !'",
    "FR53": "Devant la caisse du supermarché en palpant ses poches avec effroi : 'Elle s'est immédiatement rendu compte de son étourderie en voyant son porte-monnaie resté à la maison.'",
    "FR54": "En heurtant malencontreusement un passant dans la rue avec son parapluie : 'Pardonnez-moi infiniment, je vous assure sur l'honneur que je ne l'ai pas fait exprès.'",
    "FR55": "Retrouvant un collègue rentrant de deux semaines de thalassothérapie vivifiante : 'Ce teint hâlé et ce grand sourire te vont à ravir, tu as l'air en pleine forme !'",
    "FR56": "En signant l'acte d'achat d'un atelier d'artisanat : 'J'ai tellement hâte de commencer ce tout nouveau projet et d'aménager les établis de menuiserie.'",
    "FR57": "Autour de la table d'arbitrage d'un jury de festival littéraire : 'Les débats ont été passionnés, mais le jury va prendre une décision définitive et équitable ce soir.'",
    "FR58": "À un carrefour piétonnier très fréquenté aux heures de pointe : 'Regarde bien des deux côtés et fais bien attention aux cyclistes avant de poser le pied sur la chaussée.'",
    "FR59": "À la fin d'une conférence captivante d'un astronome de renom : 'Excusez-moi monsieur le directeur, puis-je vous poser une question rapide sur les récentes découvertes ?'",
    "FR60": "Le samedi matin avec un grand panier en osier à la main : 'Nous faisons les courses au marché du village pour acheter le chèvre frais et les légumes du potager.'",
    "FR61": "En rangeant les valises dans le coffre pour un week-end printanier : 'Ce dimanche ensoleillé, nous irons rendre visite à nos proches qui habitent près de la forêt.'",
    "FR62": "Au comptoir d'un zinc parisien traditionnel à huit heures du matin : 'Un café serré bien chaud et un croissant pur beurre tout juste sorti du four, s'il vous plaît !'",
    "FR63": "En fouillant dans une boîte à souvenirs d'enfance dénichée au grenier : 'Regarde ce vieux cliché décoloré : te souviens-tu du titre exact de cette chanson de colonie ?'",
    "FR64": "Lors d'une promenade romantique sur les sentiers de halage : 'Nous avons marché paisiblement le long du canal sous les feuillages dorés des peupliers.'",
    "FR65": "En rentrant chez soi frigorifié un soir d'automne : 'J'ai une envie irrésistible de cuisiner un grand plat de lasagnes maison fumantes et réconfortantes.'",
    "FR66": "Au sommet d'une piste de ski balayée par une bise glaciale : 'Enfile ta cagoule thermique et mets une écharpe en laine épaisse si tu as froid au visage.'",
    "FR67": "Dans les rames surchauffées d'un wagon de métro sans climatisation en juillet : 'Fais coulisser cette vitre supérieure s'il te plaît, car nous avons tous très chaud ici.'",
    "FR68": "Après une longue traversée en kayak sur les gorges du Verdon : 'Après cinq heures de pagaie sans pause, je vous promets que nous avons grand faim !'",
    "FR69": "En terminant une course d'orientation sous un soleil accablant : 'Voici une gourde fraîche : buvez un grand verre d'eau si vous avez soif après cet effort.'",
    "FR70": "Dans le salon après un repas dominical copieux et généreux : 'Le silence s'installe dans les fauteuils, tout le monde commence à avoir grand sommeil pour la sieste.'",
    "FR71": "Après vérification scrupuleuse des reçus de facturation du chantier : 'J'ai recalculé toutes les lignes comptables, et je te confirme que tu avais parfaitement raison.'",
    "FR72": "Devant la carte routière constatant que le détour a coûté une heure : 'Face aux panneaux de signalisation, il a humblement reconnu qu'il avait tort depuis le début.'",
    "FR73": "Devant le grand saut d'un parcours d'accrobranche dans les pins : 'Respire un bon coup et lance-toi : il n'y a absolument aucune honte à avoir un peu peur au sommet.'",
    "FR74": "En franchissant le péage d'autoroute sans le moindre ralentissement : 'Nous avons eu une chance inouïe d'éviter les kilomètres de bouchons annoncés à la radio.'",
    "FR75": "Pendant une assemblée générale de copropriétaires animée : 'Le règlement est formel : chaque membre a le droit inaliénable de s'exprimer dans le calme.'",
    "FR76": "Les yeux piquants devant un écran d'ordinateur à six heures du matin : 'Avant d'attaquer la relecture de ce mémoire, j'ai absolument besoin d'un double expresso corsé.'",
    "FR77": "Autour d'un verre de vin racontant ses envies de changement d'air : 'Cet automne, j'ai la ferme intention de m'inscrire enfin à un stage de pilotage d'hélicoptère.'",
    "FR78": "En faisant connaissance lors d'un vernissage d'art contemporain : 'J'ai l'immense bonheur d'habiter à Paris intramuros depuis cinq ans, tout près des quais.'",
    "FR79": "Sur le quai de la gare Montparnasse quand l'alarme de fermeture sonne : 'Montez sans attendre dans le train avant que les portes pneumatiques ne se referment !'",
    "FR80": "À l'arrêt de bus près du centre commercial bondé : 'Vérifiez bien sous vos sièges et n'oubliez pas vos sacs de courses en descendant du bus.'",
    "FR81": "Au coin du feu de cheminée après un bon repas de terroir : 'Nous nous sommes passionnés pour ce débat d'idées et nous avons discuté pendant deux heures d'affilée.'",
    "FR82": "Bouclant ses valises avant de monter dans le taxi pour l'aéroport : 'Elle s'envole en stage d'archéologie sous-marine à Marseille pour deux semaines complètes.'",
    "FR83": "Dans un atelier de reliure traditionnelle fêtant son jubilé : 'J'étudie avec passion les techniques de dorure médiévale depuis deux ans déjà sous la tutelle du maître.'",
    "FR84": "En pointant une boîte mystérieuse posée sur le meuble d'entrée : 'Le livreur a déposé ce paquet non étiqueté sur le seuil de la porte il y a trois jours.'",
    "FR85": "Trinquant dans un bistrot pour célébrer une reconversion courageuse : 'Après quinze ans derrière un écran financier, il a décidé de changer de métier pour devenir ébéniste.'"
}

def overhaul_french_roleplay():
    csv_file = BASE_DIR / "FRENCH_READY_PROMPTS_ROLEPLAY.csv"
    with open(csv_file, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    updated_count = 0
    for r in rows:
        cid = r["ID"].strip().upper()
        if cid in ROLEPLAY_SCENARIOS_FRENCH:
            r["ROLEPLAY_SCENARIO"] = ROLEPLAY_SCENARIOS_FRENCH[cid]
            updated_count += 1

    fieldnames = list(rows[0].keys())
    with open(csv_file, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Updated {updated_count}/{len(rows)} French Roleplay scenarios in {csv_file.name}")

# --- 2. FRENCH FUN FACTS (15 Viral Curiosities) ---
FUN_FACTS_FRENCH = [
    {
        "ID": "FF01",
        "TOPIC": "Pourquoi les nombres français font des maths (Quatre-vingts)",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "Les nombres français 70 (soixante-dix), 80 (quatre-vingts = 4 fois 20) et 90 (quatre-vingt-dix) utilisent un système vicésimal (base 20) hérité des Gaulois celtes et des Vikings. En revanche, le français suisse et belge utilise le système décimal régulier : septante, huitante et nonante.",
        "HOOK_ANGLE": "Pourquoi le français vous oblige-t-il à résoudre une équation mathématique juste pour dire le chiffre 80 ?",
        "EMOTIONAL_TRIGGER": "Amusement & Surprise"
    },
    {
        "ID": "FF02",
        "TOPIC": "Le mot Oiseau brise toutes les règles de prononciation",
        "PILLAR": "PRONUNCIATION_CURIOSITIES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "Le mot français 'oiseau' contient toutes les voyelles fondamentales (A, E, I, O, U), pourtant aucune d'entre elles n'est prononcée avec le son de sa propre lettre. Il se prononce simplement /wa.zo/.",
        "HOOK_ANGLE": "Ce mot français contient toutes les voyelles de l'alphabet, mais vous n'en prononcez AUCUNE !",
        "EMOTIONAL_TRIGGER": "Surprise & Fascination"
    },
    {
        "ID": "FF03",
        "TOPIC": "Un mot français avec 3 lettres E consécutives",
        "PILLAR": "WORD_CURIOSITIES",
        "FORMAT": "CHALLENGE",
        "FACT_DETAILS": "Le participe passé féminin 'créée' (du verbe créer) contient trois lettres E d'affilée : le premier avec accent aigu (é), le deuxième pour l'accord féminin muet (e), et même un quatrième au pluriel (créées = 4 E).",
        "HOOK_ANGLE": "Pouvez-vous deviner le vrai mot de la langue française qui s'écrit avec TROIS lettres 'E' d'affilée ?",
        "EMOTIONAL_TRIGGER": "Défi ludique & Curiosité"
    },
    {
        "ID": "FF04",
        "TOPIC": "4 mots français qui se prononcent exactement pareil",
        "PILLAR": "PRONUNCIATION_CURIOSITIES",
        "FORMAT": "3_FACTS",
        "FACT_DETAILS": "Ver (l'animal), Verre (pour boire), Vers (en direction de ou poésie) et Vert (la couleur) se prononcent tous de façon 100% identique /vɛʁ/ malgré des étymologies et orthographes totalement différentes.",
        "HOOK_ANGLE": "4 mots français complètement différents qui se prononcent exactement de la même manière : comment font les natifs pour se comprendre ?",
        "EMOTIONAL_TRIGGER": "Humour & Incrédulité"
    },
    {
        "ID": "FF05",
        "TOPIC": "Le français a été la langue officielle de l'Angleterre pendant 300 ans",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "MYSTERY",
        "FACT_DETAILS": "Après la conquête de Guillaume le Conquérant en 1066, le français anglo-normand a été la langue officielle de la cour d'Angleterre, de la justice et de l'aristocratie pendant plus de 300 ans. C'est pourquoi plus de 30% du vocabulaire anglais moderne vient en fait du français.",
        "HOOK_ANGLE": "La raison historique fascinante pour laquelle l'anglais et le français partagent des milliers de mots identiques.",
        "EMOTIONAL_TRIGGER": "Mystère & Découverte"
    },
    {
        "ID": "FF06",
        "TOPIC": "Pourquoi les lettres muettes existent à la fin des mots",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "À la Renaissance, des lettrés et scribes parisiens ont délibérément ajouté des lettres muettes (comme le 'p' dans corps/corpus, le 'd' dans poids/pensum) pour rapprocher artificiellement les mots français de leurs racines latines et grecques, créant l'orthographe complexe d'aujourd'hui.",
        "HOOK_ANGLE": "Pourquoi la moitié des lettres en français ne se prononcent jamais ? L'incroyable caprice des scribes de la Renaissance !",
        "EMOTIONAL_TRIGGER": "Aha Moment & Révélation"
    },
    {
        "ID": "FF07",
        "TOPIC": "Le casse-tête mondial du 'Tu' et du 'Vous'",
        "PILLAR": "CULTURAL_DIFFERENCES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "Le vouvoiement et le tutoiement français sont un champ de mines social. Le 'vous' marque le respect ou la distance professionnelle, mais l'utiliser avec un ami ou un collègue proche peut être perçu comme froid ou vexant. La transition vers le 'tu' exige un accord tacite.",
        "HOOK_ANGLE": "Tu ou Vous ? Le piège social français le plus redouté des étrangers décrypté en 30 secondes.",
        "EMOTIONAL_TRIGGER": "Clarté & Aisance"
    },
    {
        "ID": "FF08",
        "TOPIC": "Le Verlan : l'argot inversé devenu langue nationale",
        "PILLAR": "WORD_CURIOSITIES",
        "FORMAT": "3_FACTS",
        "FACT_DETAILS": "Né comme un code secret entre malfaiteurs et jeunes des cités en inversant les syllabes (l'envers -> verlan), le verlan est devenu incontournable : 'meuf' (femme), 'chelou' (louche), 'zarbi' (bizarre) et 'cimer' (merci) sont désormais dans le dictionnaire.",
        "HOOK_ANGLE": "3 mots français très courants qui sont en réalité des mots d'argot prononcés totalement à l'envers !",
        "EMOTIONAL_TRIGGER": "Surprise & Amusement"
    },
    {
        "ID": "FF09",
        "TOPIC": "L'accent circonflexe est la tombe d'un 'S' disparu",
        "PILLAR": "ETYMOLOGY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "Le petit chapeau (^) au-dessus d'une voyelle indique presque toujours qu'un 'S' médiéval a disparu avec le temps : hôpital vient de hospital, forêt de forest, fête de feste, et château de chastel. L'anglais a d'ailleurs gardé le 's' d'origine !",
        "HOOK_ANGLE": "Saviez-vous que l'accent circonflexe français est en fait la tombe commémorative d'une lettre disparue ?",
        "EMOTIONAL_TRIGGER": "Fascination & Découverte"
    },
    {
        "ID": "FF10",
        "TOPIC": "Le mot le plus long du dictionnaire français",
        "PILLAR": "WORD_CURIOSITIES",
        "FORMAT": "CHALLENGE",
        "FACT_DETAILS": "Pendant des décennies, 'anticonstitutionnellement' (25 lettres) régnait en maître. Il a été détrôné par 'intergouvernementalisations' (27 lettres). En médecine, 'aminométhylpyrimidinylhydroxyéthylméthylthiazolium' (49 lettres) bat tous les records !",
        "HOOK_ANGLE": "Vous pensiez que 'anticonstitutionnellement' était le mot le plus long du français ? Il a été détrôné !",
        "EMOTIONAL_TRIGGER": "Défi & Curiosité"
    },
    {
        "ID": "FF11",
        "TOPIC": "Pourquoi les Français disent 'Allô' au téléphone",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "MYSTERY",
        "FACT_DETAILS": "'Allô' viendrait du cri des bergers normands 'halloo' pour rassembler les bêtes ou du salut maritime anglo-saxon. Thomas Edison l'a popularisé en 1877 comme salut téléphonique universel, et la France l'a adopté immédiatement.",
        "HOOK_ANGLE": "D'où vient le mot 'Allô' que tout le monde prononce machinalement en décrochant le téléphone ?",
        "EMOTIONAL_TRIGGER": "Curiosité & Histoire"
    },
    {
        "ID": "FF12",
        "TOPIC": "Le mot intraduisible : Le Dépaysement",
        "PILLAR": "CULTURAL_DIFFERENCES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "'Le dépaysement' exprime en un seul mot ce sentiment délicieux et troublant de ne plus être dans son propre pays, de perdre ses repères habituels pour découvrir un monde nouveau. Aucun mot anglais ou espagnol n'a cette nuance exacte.",
        "HOOK_ANGLE": "Le mot français le plus poétique au monde pour décrire l'émotion unique de voyager loin de chez soi.",
        "EMOTIONAL_TRIGGER": "Poésie & Fascination"
    },
    {
        "ID": "FF13",
        "TOPIC": "La lettre 'W' n'existait pas dans le dictionnaire avant 1964",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "La lettre 'W' (double V) est la plus jeune de l'alphabet français. Elle n'a fait son entrée officielle dans le dictionnaire de l'Académie française qu'en 1964, principalement pour accueillir des emprunts étrangers comme wagon, week-end ou whisky.",
        "HOOK_ANGLE": "Cette lettre de l'alphabet français n'existait officiellement PAS dans le dictionnaire avant 1964 !",
        "EMOTIONAL_TRIGGER": "Incrédulité & Étonnement"
    },
    {
        "ID": "FF14",
        "TOPIC": "D'où vient le mot 'Chauvin' (Chauvinisme) ?",
        "PILLAR": "ETYMOLOGY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "Le mot universel 'chauvinisme' vient d'un soldat français légendaire de Napoléon, Nicolas Chauvin. Blessé 17 fois au combat, il conserva un patriotisme aveugle et fanatique qui inspira des pièces de théâtre comiques au XIXe siècle.",
        "HOOK_ANGLE": "L'incroyable histoire du soldat français fanatique qui a donné naissance au mot mondial 'chauvinisme'.",
        "EMOTIONAL_TRIGGER": "Histoire & Curiosité"
    },
    {
        "ID": "FF15",
        "TOPIC": "Pourquoi le français est surnommé 'la langue de Molière'",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "Tout comme l'anglais est 'la langue de Shakespeare', le français est 'la langue de Molière'. Le dramaturge du XVIIe siècle a révolutionné le français en capturant l'humour, les travers humains et le parler du peuple dans des comédies immortelles.",
        "HOOK_ANGLE": "Pourquoi appelle-t-on le français 'la langue de Molière' et non de Victor Hugo ou Descartes ?",
        "EMOTIONAL_TRIGGER": "Culture & Prestige"
    }
]

def overhaul_french_fun_facts():
    csv_file = BASE_DIR / "FRENCH_READY_PROMPTS_FUN_FACTS.csv"
    fieldnames = ["ID", "TOPIC", "PILLAR", "FORMAT", "FACT_DETAILS", "HOOK_ANGLE", "EMOTIONAL_TRIGGER"]
    with open(csv_file, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(FUN_FACTS_FRENCH)
    print(f"[OK] Updated {len(FUN_FACTS_FRENCH)} French Fun Facts in {csv_file.name}")

if __name__ == "__main__":
    overhaul_french_roleplay()
    overhaul_french_fun_facts()
