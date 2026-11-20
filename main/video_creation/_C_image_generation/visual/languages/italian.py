"""
visual/languages/italian.py — Italian visual palette, idiom markers, and regional Cultural World Atlas.
"""
from __future__ import annotations

from .base import CulturalWorld, LanguageVisualProfile

ITALIAN_CULTURAL_WORLDS: tuple[CulturalWorld, ...] = (
    CulturalWorld(
        id="it_trastevere_gelateria",
        title="Trastevere Artisan Gelateria",
        region="Rome (Trastevere), Italy",
        category="food_market",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "shopping", "friendship", "summer"),
        setting_prompt=(
            "sun-warmed Roman Trastevere artisan gelateria framed by clean sage pastel tiles and an arched terracotta doorway, "
            "polished steel pozzetti canisters and swirled pistachio, strawberry, and lemon gelato under curved clear glass, "
            "ivy cascading down ochre plaster walls onto cobblestones outside"
        ),
        focal_props=("waffle cone with twin gelato scoops", "steel gelato spade", "ceramic cup tray", "striped street awning"),
        wardrobe_cue="breezy butter-yellow linen short-sleeve camp shirt, terracotta tailored shorts or pleated midi skirt, and woven leather sandals",
        explicit_keywords=("gelateria", "gelato", "cono", "pistacchio", "dolce", "ice cream"),
    ),
    CulturalWorld(
        id="it_pasticceria_bar",
        title="Classic Italian Espresso Bar & Pasticceria",
        region="Milan / Rome, Italy",
        category="food_market",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "coffee", "morning", "shopping"),
        setting_prompt=(
            "authentic neighborhood Italian espresso bar and pasticceria featuring a gleaming vintage brass-and-chrome lever coffee machine "
            "behind a veined Carrara marble stand-up counter, tall glass cloches stacked with dusted cornetti and cream cannoli, "
            "and warm walnut shelves lined with striped tin canisters"
        ),
        focal_props=("fluted glass cappuccino cup", "porcelain pastry tongs", "powdered cornetto on saucer", "brass sugar bowl"),
        wardrobe_cue="tailored olive linen blazer or fine knit cardigan over crisp striped button-down, cream chinos, and brown penny loafers",
        explicit_keywords=("pasticceria", "colazione", "cornetto", "cannolo", "espresso", "cappuccino", "barista", "caffè"),
    ),
    CulturalWorld(
        id="it_murano_bottega",
        title="Venetian Mask & Murano Glass Bottega",
        region="Venice, Italy",
        category="shop",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("shopping", "culture", "history", "celebration"),
        setting_prompt=(
            "jewel-toned Venetian artisanal glass and carnival mask bottega glowing with suspended cobalt and amber blown-glass pendant globes, "
            "sculpted feathered Venetian half-masks arranged on crimson velvet shelves, timber ceiling beams, and arched leaded window facing sunlit canal water"
        ),
        focal_props=("feathered cobalt carnival mask", "iridescent blown-glass orb", "velvet display pillow", "brass mirror"),
        wardrobe_cue="tailored crimson velveteen jacket or cobalt knit sweater over crisp collar shirt, dark slacks, and suede derbies",
        explicit_keywords=("venezia", "murano", "vetro", "maschera", "carnevale", "bottega", "glass"),
    ),
    CulturalWorld(
        id="it_spaccanapoli_pizzeria",
        title="Spaccanapoli Wood-Fired Pizzeria",
        region="Naples (Campania), Italy",
        category="food_market",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "celebration", "friendship"),
        setting_prompt=(
            "bustling historic Spaccanapoli street-corner pizzeria showcasing a domed terracotta-mosaic wood-fired oven glowing warm orange, "
            "marble prep counter topped with fresh basil pots, copper olive-oil cruet, ceramic tomato bowls, and sunlit narrow Neapolitan stone street beyond"
        ),
        focal_props=("long wooden pizza peel", "glazed ceramic olive oil cruet", "terracotta basil pot", "checkered cloth"),
        wardrobe_cue="crisp sky-blue rolled-sleeve Oxford shirt, navy belted chino trousers or denim overskirt, and classic canvas sneakers",
        explicit_keywords=("pizzeria", "pizza", "napoli", "forno", "pasta", "trattoria", "osteria", "cucina", "restaurant"),
    ),
    CulturalWorld(
        id="it_mercato_centrale",
        title="Florence Mercato Centrale Iron Pavilion",
        region="Florence (Tuscany), Italy",
        category="food_market",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("food", "shopping", "history", "urban"),
        setting_prompt=(
            "soaring 19th-century Florentine Mercato Centrale hall crowned by towering cast-iron arches and sunlit clerestory skylights, "
            "stone stalls hung with braided garlic, copper ladles, dark-green glass olive-oil flasks, and overflowing crates of golden lemons and figs"
        ),
        focal_props=("wicker market basket", "glass olive oil flask", "brass market weighing scoop", "striped cloth apron fold"),
        wardrobe_cue="rust-ochre suede jacket or knit polo over chambray shirt, tailored dark trousers, and cognac boots",
        explicit_keywords=("mercato", "firenze", "market", "frutta", "verdura", "spesa"),
    ),
    CulturalWorld(
        id="it_bologna_portico",
        title="Bologna Terracotta Portico Bookstall",
        region="Bologna (Emilia-Romagna), Italy",
        category="street_plaza",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("books", "school", "history", "urban"),
        setting_prompt=(
            "iconic Bologna endless vaulted portico arcade built of warm burnt-sienna brick columns casting rhythmic sunlit arches across terracotta pavement, "
            "wooden outdoor book carts piled with clothbound volumes, and classic parked city bicycles leaning beside stone plinths"
        ),
        focal_props=("stack of vintage bound notebooks", "olive canvas messenger bag", "brass fountain pen", "classic bicycle bell"),
        wardrobe_cue="warm camel wool cardigan over collared shirt, dark plaid or twill trousers, leather satchel, and polished oxfords",
        explicit_keywords=("bologna", "portico", "università", "libro", "studio", "scuola", "compiti", "esame"),
    ),
    CulturalWorld(
        id="it_positano_lemon",
        title="Positano Amalfi Lemon Grove Pergola",
        region="Amalfi Coast (Campania), Italy",
        category="coastal_nature",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("coastal", "nature", "food", "summer"),
        setting_prompt=(
            "sun-dappled chestnut-wood pergola dripping with bright yellow Amalfi lemons and glossy green leaves overlooking Positano cliffside pastel villas "
            "and shimmering sapphire sea, complete with hand-painted Majolica ceramic terrace table and glass carafe of lemonade"
        ),
        focal_props=("Majolica ceramic pitcher", "woven basket of bright lemons", "hand-painted tile tray", "woven straw visor"),
        wardrobe_cue="crisp white embroidered linen shirt or coastal sundress with cobalt silk kerchief, sand chinos, and espadrilles",
        explicit_keywords=("limone", "amalfi", "positano", "costiera", "sole", "mare", "spiaggia"),
    ),
    CulturalWorld(
        id="it_brera_tram",
        title="Milan Brera Sartoria & Vintage Tram Corner",
        region="Milan (Lombardy), Italy",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("fashion", "travel", "urban", "shopping"),
        setting_prompt=(
            "elegant cobblestone corner in Milan's Brera district beside a tailor shop bow window draped in plaid wool bolts and velvet swatches, "
            "while a classic mustard-yellow and cream Milanese vintage tram glides smoothly down polished steel street tracks under wrought-iron lamps"
        ),
        focal_props=("tailor measuring tape draped cleanly", "rolled wool fabric swatch", "leather portfolio", "brass tram pole"),
        wardrobe_cue="sharp double-breasted charcoal blazer over striped oxford shirt, tailored herringbone trousers, and sleek black loafers",
        explicit_keywords=("milano", "tram", "vestiti", "abito", "moda", "sartoria", "giacca", "shop"),
    ),
    CulturalWorld(
        id="it_campo_de_fiori",
        title="Rome Campo de' Fiori Morning Market",
        region="Rome, Italy",
        category="food_market",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "shopping", "money", "urban"),
        setting_prompt=(
            "vibrant Roman Campo de' Fiori square bustling beneath striped burgundy and cream parasols over wooden market crates piled high with "
            "blood oranges, purple artichokes, golden sunflowers, and amber olive bottles against warm travertine Renaissance townhouses"
        ),
        focal_props=("linen market tote overflowing with sunflowers", "paper-wrapped orange bundle", "brass pocket coins", "wooden crate"),
        wardrobe_cue="sage-green safari overshirt over crisp cream tee, belted high-waisted trousers, and vintage leather sneakers",
        explicit_keywords=("roma", "piazza", "mercato", "fiori", "prezzo", "comprare"),
    ),
    CulturalWorld(
        id="it_sicily_granita",
        title="Sicilian Baroque Steps & Granita Kiosk",
        region="Noto / Catania (Sicily), Italy",
        category="food_market",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "summer", "celebration", "travel"),
        setting_prompt=(
            "glowing honey-gold limestone Sicilian Baroque staircase beside a turquoise hand-painted Majolica ceramic street kiosk topped with "
            "scalloped lemon-yellow awning, glass pedestal dishes of mulberry granita and brioche, and potted terracotta cacti"
        ),
        focal_props=("tall stemmed glass of berry granita", "fluffy golden brioche", "hand-painted ceramic fan", "sculpted stone balustrade"),
        wardrobe_cue="coral-terracotta short-sleeve resort shirt, ivory linen trousers or flared skirt, and woven straw cross-body bag",
        explicit_keywords=("sicilia", "granita", "estate", "caldo", "scale", "barocco"),
    ),
    CulturalWorld(
        id="it_lake_como_pier",
        title="Lake Como Riva Wooden Boat Pier",
        region="Bellagio / Lake Como, Italy",
        category="coastal_nature",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("travel", "coastal", "nature", "friendship"),
        setting_prompt=(
            "mirror-calm cobalt Lake Como harbor framed by misty green Alpine slopes and cypress villa gardens, where a glossy mahogany wooden speedboat "
            "rests gently against a weathered stone jetty with coiled hemp mooring rope and brass cleats"
        ),
        focal_props=("coiled hemp boat rope", "brass marine compass", "cobalt folded knit cardigan", "vintage leather duffel"),
        wardrobe_cue="navy cable-knit V-neck vest over crisp sky-blue shirt, ivory tailored chinos, and suede deck moccasins",
        explicit_keywords=("lago", "como", "barca", "viaggio", "acqua", "montagna"),
    ),
    CulturalWorld(
        id="it_verona_courtyard",
        title="Verona Pink-Marble Courtyard",
        region="Verona (Veneto), Italy",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("friendship", "history", "celebration", "culture"),
        setting_prompt=(
            "quiet romantic Verona courtyard paved in smooth rose-pink Verona marble bordered by weathered terracotta arches, "
            "ornate wrought-iron Juliet balcony above spilling with lavender-purple wisteria vines, and a moss-trimmed stone garden wellhead"
        ),
        focal_props=("bound poetry notebook", "terracotta flower pot", "brass courtyard key", "carved iron balcony rail"),
        wardrobe_cue="burgundy structured corduroy jacket or tailored cream lace-collar vest, olive trousers, and ankle leather boots",
        explicit_keywords=("verona", "balcone", "cortile", "amico", "amore", "famiglia"),
    ),
    CulturalWorld(
        id="it_turin_galleria",
        title="Turin Neoclassical Galleria Arcade",
        region="Turin (Piedmont), Italy",
        category="transit_civic",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("coffee", "shopping", "history", "urban"),
        setting_prompt=(
            "stately Turin neoclassical Subalpina glass-vaulted arcade with gleaming black-and-white diamond marble floors, "
            "towering arched cast-iron skylight vaults, gilded bronze lamp standards, and curved mahogany chocolate-house bow windows"
        ),
        focal_props=("porcelain bicerin glass in brass holder", "folded newspaper prop with abstract lines", "leather glove", "marble pillar"),
        wardrobe_cue="tailored slate herringbone coat over burgundy turtleneck, tailored trousers, and glossy oxford shoes",
        explicit_keywords=("torino", "galleria", "cioccolato", "città", "centro"),
    ),
    CulturalWorld(
        id="it_cinque_terre_cove",
        title="Cinque Terre Pastel Fishing Cove",
        region="Vernazza (Liguria), Italy",
        category="coastal_nature",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "tactile_props"),
        vibe_tags=("coastal", "travel", "summer", "friendship"),
        setting_prompt=(
            "sun-drenched Ligurian fishing cove tucked beneath stacked apricot, coral, and seafoam cliffside cottages, "
            "where bright cobalt-and-yellow wooden gozzo skiffs rest along the stone harbor ramp above crystal emerald Mediterranean surf"
        ),
        focal_props=("painted wooden oar", "striped beach canvas bag", "terracotta focaccia basket", "stone harbor bollard"),
        wardrobe_cue="seafoam short-sleeve knit polo, cuffed sand chinos or linen culottes, and braided coastal sandals",
        explicit_keywords=("mare", "porto", "liguria", "cinque terre", "pesca", "vacanza"),
    ),
    CulturalWorld(
        id="it_vespa_officina",
        title="Vintage Vespa & Scooter Corner",
        region="Siena / Rome, Italy",
        category="street_plaza",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("travel", "urban", "friendship", "sports"),
        setting_prompt=(
            "charming cobblestone Italian neighborhood archway outside a vintage scooter garage featuring glossy mint-green and cherry-red retro scooters "
            "with round chrome mirrors, leather open-face helmets resting on wooden crates, and sunlit ochre shutters behind"
        ),
        focal_props=("glossy striped vintage scooter helmet", "leather riding gloves", "chrome rear mirror", "folded road map"),
        wardrobe_cue="cognac leather moto jacket over crisp striped rugby polo, dark indigo selvedge jeans, and scuffed Chelsea boots",
        explicit_keywords=("vespa", "motorino", "strada", "guidare", "patente", "traffico"),
    ),
    CulturalWorld(
        id="it_tuscan_frantoio",
        title="Tuscan Stone Olive Mill Courtyard",
        region="Val d'Orcia (Tuscany), Italy",
        category="food_market",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "nature", "family", "autumn"),
        setting_prompt=(
            "golden Tuscan limestone farmhouse courtyard framed by ancient arched barn doors, giant weathered terracotta olive-oil amphoras, "
            "rustic wooden harvest table with woven bread cloth, and rolling golden hillside cypress avenues glowing in sunset haze"
        ),
        focal_props=("hand-thrown terracotta olive jug", "woven olive harvest basket", "rustic loaf board", "stone archway"),
        wardrobe_cue="warm caramel corduroy overshirt over ivory henley shirt, olive twill trousers, and sturdy leather lace-ups",
        explicit_keywords=("toscana", "campagna", "olio", "ulivo", "campi", "nonni", "casa"),
    ),
    CulturalWorld(
        id="it_roman_mercatino",
        title="Roman Mercatino Vinyl & Vintage Stall",
        region="Rome (Monti), Italy",
        category="shop",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("music", "shopping", "friendship", "urban"),
        setting_prompt=(
            "lively weekend outdoor antique mercatino stall in Rome's Monti neighborhood beneath a terracotta-striped canopy, "
            "wooden crates brimming with colorful retro Italian vinyl LP jackets, chrome film cameras, and brass candleholders against ivy walls"
        ),
        focal_props=("vintage silver 35mm film camera", "colorful vinyl record sleeve", "brass pocket compass", "velvet tray"),
        wardrobe_cue="mustard knit sweater vest over crisp white blouse or collared shirt, wide dark trousers, and retro suede trainers",
        explicit_keywords=("mercatino", "musica", "canzone", "disco", "fotocamera", "usato", "regalo"),
    ),
    CulturalWorld(
        id="it_grand_canal_pier",
        title="Venice Grand Canal Vaporetto Pier",
        region="Venice (Veneto), Italy",
        category="transit_civic",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "monumental"),
        vibe_tags=("travel", "coastal", "history", "urban"),
        setting_prompt=(
            "ornate Venetian wooden floating vaporetto landing pier flanked by spiraled crimson-and-white timber mooring poles, "
            "rippling emerald Grand Canal water, passing black-and-gold gondolas, and carved Gothic rose palazzo arches in golden mist"
        ),
        focal_props=("leather travel satchel", "brass lantern post", "striped canal ticket folder", "coiled mooring rope"),
        wardrobe_cue="tailored cobalt trench coat or peacoat over striped knit shirt, dark tailored trousers, and weather-proof ankle boots",
        explicit_keywords=("stazione", "battello", "gondola", "canale", "biglietto", "partenza"),
    ),
    CulturalWorld(
        id="it_sardinia_marina",
        title="Sardinian Sailboat Marina Promenade",
        region="Alghero (Sardinia), Italy",
        category="coastal_nature",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "tactile_props"),
        vibe_tags=("coastal", "sports", "summer", "travel"),
        setting_prompt=(
            "sun-bleached Sardinian limestone harbor promenade beside clear aquamarine marina water where crisp white sailboats with cobalt rigging "
            "bob gently along wooden docks, bordered by medieval honey-stone sea bastions and flowering magenta bougainvillea"
        ),
        focal_props=("braided sailing line", "canvas duffle", "tinted sunglasses", "wooden dock cleat"),
        wardrobe_cue="crisp sky-blue and white striped cotton shirt, rolled white chinos, and tan deck shoes",
        explicit_keywords=("sardegna", "vela", "spiaggia", "porto", "nuoto", "estate"),
    ),
    CulturalWorld(
        id="it_piazza_campetto",
        title="Italian Neighborhood Piazza Campetto",
        region="Apulia / Central Italy",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("sports", "friendship", "family", "urban"),
        setting_prompt=(
            "warm limestone Southern Italian neighborhood square with a gently splashing carved stone lion fountain, "
            "forest-green wooden window shutters framing sunlit cream facades, classic striped leather soccer ball by arched steps, and warm evening glow"
        ),
        focal_props=("classic panel leather soccer ball", "brass fountain spout", "linen scarf", "carved stone stoop"),
        wardrobe_cue="royal-blue track-inspired knit cardigan over crisp collared jersey polo, tailored navy shorts or chinos, and retro indoor court sneakers",
        explicit_keywords=("calcio", "partita", "pallone", "amici", "piazza", "sport", "giocare"),
    ),
    CulturalWorld(
        id="it_dolomites_ortisei",
        title="Dolomites Ortisei Alpine Timber Piazza",
        region="South Tyrol (Dolomites), Italy",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("travel", "winter", "sports", "nature"),
        setting_prompt=(
            "charming Ladin Alpine village square in the Dolomites featuring intricately painted timber chalets with carved flower balconies, "
            "wooden artisan toy-carving window displays, and colossal pale limestone Dolomite spires flushing rose-gold against snowy sky behind"
        ),
        focal_props=("hand-carved wooden alpine figurine", "wool mittens", "metal thermos", "carved larch railing"),
        wardrobe_cue="forest-green boiled wool loden jacket over warm cream turtleneck, dark corduroys, and shearling-trim hiking boots",
        explicit_keywords=("dolomiti", "montagna", "neve", "freddo", "inverno"),
    ),
    CulturalWorld(
        id="it_palermo_ballaro",
        title="Palermo Ballarò Mosaic Spice & Citrus Market",
        region="Palermo (Sicily), Italy",
        category="food_market",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "shopping", "culture", "money"),
        setting_prompt=(
            "kaleidoscopic historic Palermo Ballarò street market beneath glowing crimson and saffron sun canopies draped across narrow Arab-Norman alleys, "
            "stacked pyramids of scarlet blood oranges, ceramic bowls of pistachio kernels, and bright hand-painted donkey carts"
        ),
        focal_props=("hand-painted Sicilian cart wheel prop", "wicker citrus basket", "copper spice scoop", "terracotta olive bowl"),
        wardrobe_cue="amber-ochre utility overshirt over crisp linen tee, terracotta chinos or patterned skirt, and leather cross-strap sandals",
        explicit_keywords=("palermo", "arancia", "spese", "soldi", "mercato", "cibo"),
    ),
    # ── Landmark Worlds (Monumental Scale for FUN_FACTS & Wonder Shots) ──
    CulturalWorld(
        id="it_landmark_colosseum",
        title="Rome Colosseum Travertine Arches",
        region="Rome, Italy",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "travel", "culture", "urban"),
        setting_prompt=(
            "monumental Via dei Fori Imperiali cobblestone approach looking straight up at the colossal four-story travertine stone arches "
            "and weathered arcades of the Roman Colosseum towering into golden-amber Roman sunset clouds alongside ancient Roman pine silhouettes"
        ),
        focal_props=("marble Roman column fragment prop", "leather bound travel journal", "brass compass", "cobblestone bollard"),
        wardrobe_cue="tailored olive cotton trench jacket over ivory striped knit shirt, dark pleated trousers, and chestnut leather loafers",
        explicit_keywords=("colosseo", "colosseum", "roma", "antico", "storia", "history", "impero"),
    ),
    CulturalWorld(
        id="it_landmark_duomo",
        title="Florence Duomo & Piazzale Overlook",
        region="Florence (Tuscany), Italy",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "culture", "travel"),
        setting_prompt=(
            "sweeping Renaissance Florentine piazza and stone terrace gazing upward at Brunelleschi's colossal ribbed terracotta Cathedral dome "
            "clad in gleaming green, pink, and white Carrara marble filigree beneath warm Tuscan amber sunlight"
        ),
        focal_props=("carved wooden architectural dome model", "rolled geometric sketch", "brass dividers", "marble balustrade"),
        wardrobe_cue="burgundy structured corduroy blazer over cream shirt, sand pleated chinos, and leather oxford shoes",
        explicit_keywords=("duomo", "brunelleschi", "rinascimento", "cupola", "firenze"),
    ),
    CulturalWorld(
        id="it_landmark_pisa",
        title="Pisa Piazza dei Miracoli Leaning Tower",
        region="Pisa (Tuscany), Italy",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "travel", "celebration"),
        setting_prompt=(
            "emerald lawn and ivory stone pathway of Pisa's Piazza dei Miracoli framing the dramatic marble colonnaded tiers of the Leaning Tower "
            "tilting cleanly skyward in luminous sunlit crispness beside carved Romanesque cathedral marble arches"
        ),
        focal_props=("brass plumb bob level", "vintage folding camera", "blank sketch notebook", "carved marble curb"),
        wardrobe_cue="crisp emerald knit vest over crisp white button-up, tailored navy trousers, and retro white-and-navy sneakers",
        explicit_keywords=("pisa", "torre", "campanile", "meraviglia"),
    ),
    CulturalWorld(
        id="it_landmark_san_marco",
        title="Venice St. Mark's Campanile & Byzantine Arches",
        region="Venice, Italy",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "culture", "travel", "urban"),
        setting_prompt=(
            "majestic pink-and-white patterned limestone Piazza San Marco looking skyward at the towering brick bell tower campanile "
            "and shimmering golden mosaic domes of St. Mark's Basilica framed by sunlit Procuratie colonnades and drifting pigeons"
        ),
        focal_props=("brass winged-lion medallion prop", "leather sketchbook", "ivory silk pocket scarf", "marble colonnade base"),
        wardrobe_cue="structured camel pea jacket over dark striped turtleneck, slim grey flannel trousers, and glossy ankle boots",
        explicit_keywords=("san marco", "basilica", "campanile", "venezia"),
    ),
    CulturalWorld(
        id="it_landmark_trevi",
        title="Trevi Fountain Baroque Cascade",
        region="Rome, Italy",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "travel", "celebration", "money"),
        setting_prompt=(
            "theatrical Roman Baroque travertine amphitheater of the Trevi Fountain soaring above a luminous turquoise marble cascade "
            "with monumental sculpted marble Triton figures, crashing water spray illuminated by warm golden facade lanterns"
        ),
        focal_props=("gleaming brass wish coin", "marble fountain ledge", "woven gelato napkin", "leather backpack"),
        wardrobe_cue="navy utility blazer over crisp striped collared blouse or tee, terracotta trousers, and clean leather loafers",
        explicit_keywords=("fontana", "trevi", "moneta", "desiderio"),
    ),
    CulturalWorld(
        id="it_landmark_pompeii",
        title="Pompeii Ancient Forum & Mount Vesuvius",
        region="Pompeii (Campania), Italy",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "travel", "nature"),
        setting_prompt=(
            "expansive sun-baked basalt flagstones and weathered volcanic stone colonnade ruins of Pompeii's ancient Forum stretching directly toward "
            "the towering hazy silhouette of Mount Vesuvius rising majestically behind olive trees"
        ),
        focal_props=("archaeologist trowel & brush pouch", "terracotta oil lamp replica", "rolled site scroll with doodles", "stone plinth"),
        wardrobe_cue="stone-khaki belted safari overshirt over crisp white knit polo, dark olive cargo trousers, and rugged suede boots",
        explicit_keywords=("pompei", "vesuvio", "vulcano", "rovine", "antico"),
    ),
)

ITALIAN_PROFILE = LanguageVisualProfile(
    language="italian",
    lang_code="I",
    aliases=("it", "italiano"),
    palette_mood=(
        "BRAND PALETTE MOOD (ITALIAN): Warm, passionate, stylish, vibrant.\n"
        "Key Accent Colors: Mediterranean Blue, Olive Green, Warm Terracotta, and Sunlit Gold.\n"
    ),
    idiom_markers=(
        "in bocca al lupo", "occhio della testa", "mani bucate", "lucciole per lanterne",
    ),
    idiom_environments=(
        (("in bocca al lupo",), "historic Italian opera theater and performing arts stage (featuring: ornate dressing room mirror, crimson velvet wings, carved proscenium stage)"),
        (("occhio della testa",), "chic Milanese haute-couture boutique gallery along cobblestone Quadrilatero promenade (featuring: velvet mannequin pedestals, marble counter, sunlit arcade)"),
    ),
    cultural_cue="Italian regional piazzas, gelaterias, historic markets, coastal coves, porticos, and landmarks",
    cultural_worlds=ITALIAN_CULTURAL_WORLDS,
)
