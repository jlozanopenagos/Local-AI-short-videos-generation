"""
visual/languages/french.py — French visual palette, idiom markers, and Francophone Cultural World Atlas.
"""
from __future__ import annotations

from .base import CulturalWorld, LanguageVisualProfile

FRENCH_CULTURAL_WORLDS: tuple[CulturalWorld, ...] = (
    CulturalWorld(
        id="fr_marais_friperie",
        title="Marais Vintage Friperie",
        region="Paris (Le Marais), France",
        category="shop",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("shopping", "fashion", "urban", "friendship"),
        setting_prompt=(
            "chic Parisian Marais vintage friperie boutique with checkerboard parquet flooring, "
            "curved brass garment rails lined with retro corduroy jackets and silk scarves, gilt wall mirrors, "
            "arched stone window overlooking a cobblestone Paris lane, and a polished oak cashier counter"
        ),
        focal_props=("brass coat hangers", "striped vintage leather satchel", "emerald silk neck scarf", "polaroid camera"),
        wardrobe_cue="tailored vintage corduroy jacket or striped wool blazer over collared shirt, pleated trousers, and leather ankle boots",
        explicit_keywords=("friperie", "thrift", "vintage", "vêtement", "vetement", "clothes", "boutique", "jacket", "veste"),
    ),
    CulturalWorld(
        id="fr_boulangerie",
        title="Parisian Boulangerie-Pâtisserie",
        region="Paris, France",
        category="food_market",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "morning", "celebration", "shopping"),
        setting_prompt=(
            "classic sunlit Parisian boulangerie-pâtisserie with clean pale marble pastry counter, "
            "wicker baskets brimming with golden braided baguettes and flaky croissants, tiered brass glass cloches "
            "displaying pastel macarons and éclairs, scalloped mint wainscoting, and mosaic tile floor"
        ),
        focal_props=("wicker bread basket", "golden braided baguettes", "tiered brass pastry cloche", "pastel macarons on porcelain tray"),
        wardrobe_cue="crisp Breton striped knit sweater or tailored camel overshirt, cuffed chinos or midi skirt, and leather loafers",
        explicit_keywords=("boulangerie", "pâtisserie", "patisserie", "bakery", "croissant", "baguette", "pain", "bread", "cake", "gâteau", "gateau"),
    ),
    CulturalWorld(
        id="fr_seine_bouquinistes",
        title="Seine Riverbank Bouquinistes",
        region="Paris, France",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("books", "culture", "history", "friendship", "urban"),
        setting_prompt=(
            "iconic deep-green open-air bouquiniste bookstalls hinged along the limestone Seine riverbank parapet, "
            "neat stacks of colorful vintage illustrated hardcovers and brass bookmarks, golden plane trees dropping autumn leaves, "
            "shimmering turquoise river water, and distant limestone Gothic spires in soft golden mist"
        ),
        focal_props=("stack of colorful clothbound books", "vintage brass magnifying glass", "canvas tote bag", "rolled watercolor sketch"),
        wardrobe_cue="structured camel wool cardigan over collared shirt, tailored dark trousers, woven scarf, and suede desert boots",
        explicit_keywords=("bouquiniste", "seine", "livre", "book", "bookshop", "reading", "roman", "poème"),
    ),
    CulturalWorld(
        id="fr_lyon_traboule",
        title="Lyon Bouchon & Traboule Courtyard",
        region="Lyon (Vieux Lyon), France",
        category="food_market",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "history", "friendship", "celebration"),
        setting_prompt=(
            "ochre Renaissance stone courtyard off a Vieux Lyon traboule passage with vaulted carved staircases, "
            "warm wrought-iron terrace railing, red-and-white checkered outdoor bistro tables set with copper pots and ceramic pitchers, "
            "and amber wall lanterns glowing against warm terracotta stone"
        ),
        focal_props=("glazed earthenware pitcher", "checkered woven napkin basket", "polished copper sauté pan", "stone balustrade"),
        wardrobe_cue="forest-green overshirt over crisp chambray button-down, dark chinos, and classic leather derbies",
        explicit_keywords=("bouchon", "traboule", "lyon", "restaurant", "dîner", "diner", "repas", "lunch"),
    ),
    CulturalWorld(
        id="fr_provence_marche",
        title="Provence Lavender & Olive Marché",
        region="Aix-en-Provence, France",
        category="food_market",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "shopping", "nature", "money"),
        setting_prompt=(
            "sun-drenched Provençal morning square market under blue-and-cream striped canvas awnings, "
            "woven wicker panniers overflowing with purple lavender bundles, sunlit heirloom tomatoes, glazed yellow-and-cobalt olive pitchers, "
            "platanus shade trees, and warm honey-limestone shuttered facades behind"
        ),
        focal_props=("wicker market basket", "lavender bouquet", "glazed cobalt ceramic pitcher", "brass balance scale"),
        wardrobe_cue="breezy off-white linen button-up with rolled sleeves, olive cotton trousers or tiered sundress, and braided leather sandals",
        explicit_keywords=("marché", "marche", "provence", "lavande", "market", "olive", "panier", "fruits", "légumes"),
    ),
    CulturalWorld(
        id="fr_fromagerie",
        title="Parisian Artisan Fromagerie",
        region="Paris, France",
        category="food_market",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "shopping", "culture", "money"),
        setting_prompt=(
            "warm stone-tiled corner fromagerie shop with straw-lined oak shelving holding golden-rinded cheese wheels under curved glass bells, "
            "a cool marble cutting counter with wooden paddles, hanging copper weights, and frosted leaded glass transoms"
        ),
        focal_props=("wooden tasting board", "curved brass bell dome", "waxed parchment wrap", "woven straw basket"),
        wardrobe_cue="navy cotton chore jacket over crisp striped shirt, tailored trousers, and cognac leather loafers",
        explicit_keywords=("fromagerie", "fromage", "cheese", "épicerie", "epicerie"),
    ),
    CulturalWorld(
        id="fr_montmartre_tertre",
        title="Montmartre Place du Tertre",
        region="Paris (Montmartre), France",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("music", "culture", "friendship", "urban", "celebration"),
        setting_prompt=(
            "cobblestone hilltop square in Montmartre bordered by cream limestone townhouses with crimson wooden shutters, "
            "sunlit chestnut trees, wooden outdoor painter easels dotting the terrace edge, wrought-iron streetlamps, "
            "and warm Paris rooftops glowing in golden afternoon light"
        ),
        focal_props=("wooden painter palette", "rolled charcoal sketchbook", "accordion case", "vintage streetlamp post"),
        wardrobe_cue="textured charcoal knit polo or cropped trench jacket, tailored trousers or pleated skirt, burgundy beret accent, and polished boots",
        explicit_keywords=("montmartre", "peintre", "portrait", "place", "square", "quartier"),
    ),
    CulturalWorld(
        id="fr_metro_guimard",
        title="Art Nouveau Métro Archway",
        region="Paris, France",
        category="transit_civic",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("travel", "urban", "morning", "friendship"),
        setting_prompt=(
            "iconic sculpted botanical-green cast-iron Guimard Art Nouveau Métro entrance arch curving down stone steps "
            "under glowing amber tulip streetlamps, flanked by cream Haussmann apartment balconies and wide Parisian boulevard trees"
        ),
        focal_props=("embossed transit card sleeve", "folded pocket city map", "leather crossbody bag", "wrought-iron railing"),
        wardrobe_cue="tailored slate wool bomber or belted gabardine coat over striped knit top, tailored trousers, and crisp court sneakers",
        explicit_keywords=("métro", "metro", "subway", "station", "arrêt", "banlieue", "commute"),
    ),
    CulturalWorld(
        id="fr_zinc_brasserie",
        title="Left Bank Brasserie Zinc Terrace",
        region="Paris (Saint-Germain), France",
        category="food_market",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "friendship", "coffee", "celebration", "urban"),
        setting_prompt=(
            "classic Left Bank sidewalk brasserie terrace featuring woven amber rattan bistro chairs facing the sunlit street beside a gleaming "
            "pewter zinc corner bar framed by bevelled glass dividers, burgundy canvas awning overhead, and porcelain demi-tasse cups"
        ),
        focal_props=("porcelain coffee cup and saucer", "curved pewter bar rim", "carafe of citrus water", "brass tray"),
        wardrobe_cue="tailored espresso tweed blazer or silk-scarf cardigan over ivory button-down, high-waisted trousers, and oxford shoes",
        explicit_keywords=("brasserie", "café", "cafe", "bistrot", "bistro", "terrasse", "espresso", "thé"),
    ),
    CulturalWorld(
        id="fr_bordeaux_disquaire",
        title="Bordeaux Vinyl Disquaire",
        region="Bordeaux, France",
        category="shop",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("music", "shopping", "friendship", "celebration"),
        setting_prompt=(
            "warm honey-limestone vaulted indie vinyl disquaire shop in historic Bordeaux packed with oak crate bins of colorful artwork record sleeves, "
            "a vintage wood-trimmed turntable listening station with retro headphones, brass globe lamps, and sunlit arched doorway"
        ),
        focal_props=("colorful 12-inch vinyl record sleeve", "silver over-ear headphones", "retro walnut turntable", "brass sleeve stand"),
        wardrobe_cue="cropped emerald suede or denim overshirt over ribbed turtleneck, relaxed straight trousers, and suede sneakers",
        explicit_keywords=("disquaire", "vinyle", "vinyl", "musique", "music", "chanson", "song", "concert", "disque"),
    ),
    CulturalWorld(
        id="fr_strasbourg_bridge",
        title="Strasbourg Petite-France Timber Bridge",
        region="Strasbourg (Alsace), France",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("travel", "history", "nature", "friendship"),
        setting_prompt=(
            "picturesque Strasbourg Petite-France wooden canal footbridge framed by tall half-timbered Alsatian houses, "
            "railings cascading with coral geranium flower boxes, stone canal lock gates below, and soaring sandstone spire silhouette in the distance"
        ),
        focal_props=("wicker canal picnic tote", "vintage rangefinder camera", "ceramic thermos", "carved timber railing"),
        wardrobe_cue="quilted olive vest over warm cable-knit fisherman sweater, dark corduroys, and stitched leather lace-up boots",
        explicit_keywords=("strasbourg", "alsace", "pont", "bridge", "canal", "rivière"),
    ),
    CulturalWorld(
        id="fr_nice_promenade",
        title="Nice Promenade des Anglais",
        region="Nice (Côte d'Azur), France",
        category="coastal_nature",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "tactile_props"),
        vibe_tags=("coastal", "travel", "sports", "celebration"),
        setting_prompt=(
            "sun-bright Nice Promenade des Anglais limestone walkway curving beside royal-turquoise Mediterranean waves, "
            "iconic cobalt-blue slatted seaside benches under swaying palm fronds, Belle Époque cream facade balustrade, and bright coastal horizon"
        ),
        focal_props=("woven straw sunhat", "cobalt striped towel bundle", "vintage sunglasses", "glass citrus soda bottle"),
        wardrobe_cue="breezy sky-blue short-sleeve linen resort shirt, cream pleated shorts or flowing linen trousers, and canvas espadrilles",
        explicit_keywords=("nice", "promenade", "plage", "mer", "beach", "sea", "côte", "soleil"),
    ),
    CulturalWorld(
        id="fr_saint_malo_creperie",
        title="Saint-Malo Brittany Crêperie Pier",
        region="Saint-Malo (Brittany), France",
        category="coastal_nature",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "coastal", "travel", "friendship"),
        setting_prompt=(
            "weathered granite ramparts and striped blue-and-white maritime crêperie stall along Saint-Malo harbor wall, "
            "glowing cast-iron galette griddles, speckled stoneware bowls on timber outdoor table, and Atlantic sailboats beyond stone seawall"
        ),
        focal_props=("wooden galette turner", "ceramic cider bolée bowl", "striped marinière tote", "lighthouse stone wall"),
        wardrobe_cue="classic navy-and-ivory striped marinière sweater under yellow waxed sailcloth jacket, cuffed chinos, and boat shoes",
        explicit_keywords=("crêperie", "creperie", "crêpe", "crepe", "bretagne", "port", "bateau", "boat"),
    ),
    CulturalWorld(
        id="fr_galerie_vivienne",
        title="Galerie Vivienne Covered Passage",
        region="Paris, France",
        category="transit_civic",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("shopping", "history", "urban", "fashion"),
        setting_prompt=(
            "luminous 19th-century Galerie Vivienne covered arcade with intricate terracotta-and-ivory geometric mosaic floors, "
            "soaring arched iron-and-glass skylight roof bathing carved oak storefronts, brass lanterns, and quiet colonnaded arches in soft daylight"
        ),
        focal_props=("leather-bound sketchbook", "waxed paper book parcel", "brass umbrella handle", "mosaic column base"),
        wardrobe_cue="tailored taupe houndstooth blazer over fine turtleneck, dark pleated trousers, and glossy penny loafers",
        explicit_keywords=("galerie", "passage", "arcade", "vitrine", "shopwindow"),
    ),
    CulturalWorld(
        id="fr_gare_de_lyon",
        title="Gare de Lyon Grand Concourse",
        region="Paris, France",
        category="transit_civic",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "monumental"),
        vibe_tags=("travel", "history", "urban", "celebration"),
        setting_prompt=(
            "monumental Belle Époque railway hall at Gare de Lyon with soaring teal iron roof trusses, golden sculpted limestone arches, "
            "gleaming sleek high-speed passenger train noses beside a clean platform, and vintage leather suitcases near a curved brass lamp bench"
        ),
        focal_props=("tan belted leather weekender bag", "rolled folding travel itinerary", "brass pocket watch", "vintage station trunk"),
        wardrobe_cue="smart cognac wool overcoat or structured utility jacket over striped oxford shirt, dark denim or trousers, and Chelsea boots",
        explicit_keywords=("gare", "train", "quai", "platform", "tgv", "valise", "voyage", "billet", "ticket", "railway"),
    ),
    CulturalWorld(
        id="fr_luxembourg_pond",
        title="Jardin du Luxembourg Toy-Sailboat Pond",
        region="Paris (6th Arr.), France",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "tactile_props"),
        vibe_tags=("nature", "sports", "friendship", "celebration"),
        setting_prompt=(
            "classic octagonal stone basin in Jardin du Luxembourg surrounded by sage-green metal garden chairs, "
            "colorful painted wooden vintage model sailboats skimming sunlit rippled water, formal geometric chestnut avenues, and distant limestone palace facade"
        ),
        focal_props=("handcrafted striped wooden toy sailboat", "bamboo boat steering rod", "sketch pad", "park chair"),
        wardrobe_cue="sage-green knitted cardigan over crisp collar shirt, cream pleated chinos, and leather saddle shoes",
        explicit_keywords=("jardin", "parc", "park", "garden", "banc", "bench", "arbre", "voilier"),
    ),
    CulturalWorld(
        id="fr_biarritz_boardwalk",
        title="Biarritz Atlantic Surf Boardwalk",
        region="Biarritz (Basque Coast), France",
        category="coastal_nature",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("sports", "coastal", "friendship", "travel"),
        setting_prompt=(
            "amber timber boardwalk above Biarritz Grande Plage lined with striped coral-and-cream wooden beach cabanas, "
            "vibrant twin-fin surfboards resting against weathered driftwood railing, white cliff headland lighthouse behind rolling teal surf"
        ),
        focal_props=("waxed retro striped surfboard", "canvas beach pack", "stainless flask", "sunscreen stick"),
        wardrobe_cue="relaxed terracotta utility overshirt open over striped knit tee, tailored chino boardshorts, and suede slip-on sneakers",
        explicit_keywords=("surf", "biarritz", "sport", "vague", "wave", "atlantique"),
    ),
    CulturalWorld(
        id="fr_librairie_bd",
        title="Bande Dessinée Comic Bookshop",
        region="Angoulême / Brussels, Francophone Europe",
        category="shop",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("books", "music", "friendship", "school"),
        setting_prompt=(
            "cozy wooden bande dessinée comic bookshop featuring tall oak shelves packed horizontally and vertically with vibrant illustrated hardcovers, "
            "a rolling brass library ladder, warm yellow reading alcove lamp, and clear rounded bow window onto rainy cobblestones"
        ),
        focal_props=("thick colorful hardcover comic album", "wooden display easel", "canvas satchel", "brass reading lamp"),
        wardrobe_cue="warm mustard corduroy overshirt over patterned collar shirt, dark straight jeans, and burgundy canvas high-tops",
        explicit_keywords=("librairie", "bande dessinée", "bd", "comic", "lecture", "bibliothèque", "library", "étudier"),
    ),
    CulturalWorld(
        id="fr_toulouse_capitole",
        title="Toulouse Pink-Brick Capitole Arcade",
        region="Toulouse (Occitanie), France",
        category="street_plaza",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "monumental"),
        vibe_tags=("urban", "history", "celebration", "friendship"),
        setting_prompt=(
            "soaring rose-terracotta brick vaulted arcade lining Toulouse Place du Capitole with tall neoclassical limestone columns, "
            "black wrought-iron pendant lanterns, warm sunset reflections across broad plaza flagstones, and violet flower planters"
        ),
        focal_props=("crimson leather portfolio", "acoustic guitar gig strap", "terracotta teacup", "arched brick pillar"),
        wardrobe_cue="ochre structured cotton blazer over navy collared shirt, crisp cream trousers, and suede loafers",
        explicit_keywords=("toulouse", "capitole", "brique", "arcade", "boulevard", "ville", "rue", "street"),
    ),
    CulturalWorld(
        id="fr_chamonix_chalet",
        title="Chamonix Alpine Chalet Terrace",
        region="Chamonix (French Alps), France",
        category="coastal_nature",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("sports", "travel", "nature", "winter"),
        setting_prompt=(
            "carved dark-pine Alpine chalet terrace deck looking directly up at jagged snow-covered Mont Blanc granite peaks under crisp cerulean sky, "
            "steaming stoneware hot-chocolate mugs on sturdy wooden bench, vintage wooden skis leaning against log wall"
        ),
        focal_props=("vintage wooden touring skis", "steaming ceramic mug", "woven wool mountain blanket", "alpine daypack"),
        wardrobe_cue="crimson-and-navy heritage Alpine down puffer vest over Nordic patterned wool sweater, insulated trousers, and winter trail boots",
        explicit_keywords=("montagne", "chamonix", "alpes", "ski", "neige", "snow", "hiver", "chalet"),
    ),
    CulturalWorld(
        id="fr_quebec_champlain",
        title="Old Québec Rue du Petit-Champlain",
        region="Québec City, Canada",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("travel", "history", "winter", "shopping"),
        setting_prompt=(
            "storybook cobblestone Rue du Petit-Champlain in Old Québec winding past steep tin-roofed fieldstone shops with forest-green shutters, "
            "glowing wrought-iron carriage lamps, stacked maplewood barrels, and the fairytale green-turret château silhouette towering above"
        ),
        focal_props=("glazed maple syrup stoneware jug", "carved birch walking stick", "knit tartan scarf", "iron lantern railing"),
        wardrobe_cue="emerald plaid wool flannel overshirt under belted duffel coat, corduroy trousers, and lined leather boots",
        explicit_keywords=("québec", "quebec", "canada", "érable", "neige"),
    ),
    CulturalWorld(
        id="fr_brussels_galeries",
        title="Brussels Galeries Royales Arcade & Chocolaterie",
        region="Brussels, Belgium",
        category="food_market",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("food", "shopping", "history", "celebration"),
        setting_prompt=(
            "soaring Belle Époque Brussels Galeries Royales stone arcade with arched glass-coffered barrel ceiling, "
            "warm mahogany chocolaterie counter showcasing jewel-toned praline pyramids and silk-ribbon ballotin boxes"
        ),
        focal_props=("porcelain praline tasting tray", "brass-clasped ribbon box", "leather satchel", "arched marble column"),
        wardrobe_cue="deep burgundy velvet collar jacket over crisp striped blouse or button-down, tailored charcoal slacks, and glossy brogues",
        explicit_keywords=("chocolat", "praline", "gaufre", "bruxelles", "belgique", "sucrerie"),
    ),
    # ── Landmark Worlds (Monumental Scale for FUN_FACTS & Wonder Shots) ──
    CulturalWorld(
        id="fr_landmark_eiffel",
        title="Eiffel Tower Champ-de-Mars Esplanade",
        region="Paris, France",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "travel", "celebration", "urban"),
        setting_prompt=(
            "grand Champs-de-Mars gravel esplanade in Paris looking straight up toward the colossal riveted iron lattice arches of the Eiffel Tower "
            "rising majestically into an amber-and-lavender golden-hour sky above manicured clipped lindens and classic green park lamps"
        ),
        focal_props=("brass folding pocket telescope", "bound architectural sketchbook", "woven picnic hamper", "wrought-iron balustrade"),
        wardrobe_cue="structured camel trench jacket over striped knit top, tailored navy trousers, and polished leather loafers",
        explicit_keywords=("tour eiffel", "eiffel", "monument", "architecture", "paris"),
    ),
    CulturalWorld(
        id="fr_landmark_louvre",
        title="Louvre Glass Pyramid Twilight Courtyard",
        region="Paris, France",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "culture", "travel", "urban"),
        setting_prompt=(
            "expansive Cour Napoléon flagstone plaza of the Louvre where the luminous faceted glass-and-steel pyramid glows warm amber at twilight, "
            "mirrored in triangular reflecting pools and framed by soaring sculpted limestone Renaissance palace wings"
        ),
        focal_props=("marble miniature column compass", "linen art folder", "vintage brass camera", "stone fountain rim"),
        wardrobe_cue="sleek midnight-blue wool blazer over crisp cream shirt, tailored anthracite trousers, and black Chelsea boots",
        explicit_keywords=("louvre", "musée", "museum", "pyramide", "palais", "art"),
    ),
    CulturalWorld(
        id="fr_landmark_mont_st_michel",
        title="Mont-Saint-Michel Tidal Causeway",
        region="Normandy, France",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "travel", "coastal", "nature"),
        setting_prompt=(
            "dramatic granite stone causeway leading toward the soaring medieval abbey spire and fortified ramparts of Mont-Saint-Michel rising skyward "
            "from silver wet tidal sandbars under towering sunlit sea clouds and circling coastal gulls"
        ),
        focal_props=("folded tide chart scroll with wave doodles", "brass compass", "canvas windbreaker pack", "granite sea wall"),
        wardrobe_cue="slate windproof coastal parka over cream cable-knit sweater, rugged dark twill trousers, and waterproof leather boots",
        explicit_keywords=("mont-saint-michel", "abbaye", "marée", "normandie", "château", "castle", "medieval"),
    ),
    CulturalWorld(
        id="fr_landmark_versailles",
        title="Versailles Hall of Mirrors",
        region="Versailles, France",
        category="landmark",
        indoor_outdoor="interior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "celebration", "culture"),
        setting_prompt=(
            "soaring Royal Hall of Mirrors gallery with seventeen towering arched glass mirrors reflecting sunlit formal French gardens through tall arched windows, "
            "polychrome herringbone marble floor, crystal chandeliers, and gilded allegorical ceiling vault"
        ),
        focal_props=("ornate gilded brass pocket compass", "crimson velvet ribbon satchel", "ivory opera glasses", "marble pedestal"),
        wardrobe_cue="tailored royal-navy jacquard blazer over crisp ruffled or pleated collared shirt, tailored slacks, and buckled dress loafers",
        explicit_keywords=("versailles", "château", "palace", "roi", "histoire", "history", "galerie des glaces"),
    ),
    CulturalWorld(
        id="fr_landmark_pont_du_gard",
        title="Pont du Gard Roman Aqueduct",
        region="Occitanie, France",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "nature", "travel"),
        setting_prompt=(
            "colossal three-tier honey-limestone Roman aqueduct arches of the Pont du Gard towering majestically over emerald Gardon river rapids "
            "and limestone canyon scrub bathed in dramatic Provençal sunbeams"
        ),
        focal_props=("weathered stone surveyor plumb line", "rolled cream parchment architectural arch sketch", "canteen", "sandstone boulder"),
        wardrobe_cue="ochre utility field overshirt over white ribbed knit tee, khaki cargo chinos, and sturdy trail sneakers",
        explicit_keywords=("romain", "aqueduc", "pont du gard", "antiquité", "pierre"),
    ),
    CulturalWorld(
        id="fr_landmark_garnier",
        title="Palais Garnier Grand Staircase",
        region="Paris, France",
        category="landmark",
        indoor_outdoor="interior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("music", "history", "celebration", "culture"),
        setting_prompt=(
            "breathtaking Palais Garnier Opera foyer featuring sweeping twin staircases carved from rose, emerald, and ivory marble rising toward "
            "tiered crimson-velvet balconies, gilded bronze candelabra, and soaring frescoed rotunda dome"
        ),
        focal_props=("mother-of-pearl opera glasses", "crimson velvet concert folio", "brass balustrade", "violin case"),
        wardrobe_cue="tailored deep-plum tailored jacket over silk collar blouse or dress shirt, dark pleated trousers, and patent loafers",
        explicit_keywords=("opéra", "opera", "garnier", "théâtre", "theater", "spectacle", "musique", "ballet"),
    ),
)

FRENCH_PROFILE = LanguageVisualProfile(
    language="french",
    lang_code="F",
    aliases=("fr", "français", "francais"),
    palette_mood=(
        "BRAND PALETTE MOOD (FRENCH): Elegant, warm, cultured, friendly.\n"
        "Key Accent Colors: French Blue, Deep Teal, and restrained Red.\n"
    ),
    idiom_markers=(
        "expression idiomatique",
        "poser un lapin", "yeux de la tête", "coup de foudre", "dans les pommes", "du gâteau",
    ),
    idiom_environments=(
        (("du gâteau",), "sunlit Parisian boulangerie-pâtisserie counter showcasing an elaborate towering multi-tier frosted cake with one slice missing beneath arched brass glass cloches and herringbone mosaic floor"),
        (("dans les pommes",), "golden-hour Normandy orchard market terrace framed by woven wicker apple baskets, warm stoneware tea mugs on an oak table, and crimson orchard trees behind"),
        (("yeux de la tête",), "chic Parisian haute-couture boutique along a Haussmann boulevard (featuring: luxury velvet display pedestals, gilt mirrors, marble counter)"),
        (("poser un lapin",), "charming Left Bank cobblestone brasserie terrace beside an ornate antique plaza lamp post (featuring: outdoor rattan table with untouched porcelain cup)"),
    ),
    cultural_cue="French and Francophone shops, boulevards, historic passages, coastal piers, markets, and landmarks",
    cultural_worlds=FRENCH_CULTURAL_WORLDS,
)
