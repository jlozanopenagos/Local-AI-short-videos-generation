"""
visual/languages/spanish.py — Spanish visual palette, idiom markers, and Spain + Latin America Cultural World Atlas.
"""
from __future__ import annotations

from .base import CulturalWorld, LanguageVisualProfile

SPANISH_CULTURAL_WORLDS: tuple[CulturalWorld, ...] = (
    # ── Spain ──
    CulturalWorld(
        id="es_triana_taperia",
        title="Seville Triana Azulejo Tapería",
        region="Seville (Andalusia), Spain",
        category="food_market",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "friendship", "celebration", "shopping"),
        setting_prompt=(
            "vibrant Seville Triana corner tapería lined with hand-painted cobalt, emerald, and ochre glazed azulejo ceramic wall tiles, "
            "gleaming clean white marble counter topped with terracotta cazuela bowls of olives and oranges, wrought-iron amber wall lanterns, "
            "and sunlit orange trees visible beyond an open Moorish horseshoe arch"
        ),
        focal_props=("glazed terracotta tapas dish", "striped porcelain olive bowl", "folded linen napkin", "fan of painted ceramic tiles"),
        wardrobe_cue="crisp ivory rolled-sleeve linen shirt over emerald knit top, tailored tan chinos or flared skirt, and woven leather loafers",
        explicit_keywords=("tapería", "taperia", "tapas", "sevilla", "andalucía", "aceituna", "restaurante", "bar"),
    ),
    CulturalWorld(
        id="es_madrid_churreria",
        title="Madrid Classic Chocolatería & Churrería",
        region="Madrid, Spain",
        category="food_market",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "morning", "celebration", "friendship"),
        setting_prompt=(
            "historic century-old Madrid chocolatería and churrería with black-and-white checkered marble floors, rich mahogany wainscoting, "
            "beveled brass-framed mirrors, gleaming hammered copper chocolate urns behind the stone counter, and oval porcelain platters piled with crisp golden churro spirals"
        ),
        focal_props=("white porcelain cup of thick hot chocolate", "platter of crisp golden churros", "copper ladle", "folded striped scarf"),
        wardrobe_cue="tailored burgundy wool jacket or emerald cardigan over collared white shirt, dark pleated trousers, and Chelsea leather boots",
        explicit_keywords=("churrería", "churreria", "churros", "chocolate", "chocolatería", "madrid", "desayuno", "dulce"),
    ),
    CulturalWorld(
        id="es_boqueria_market",
        title="Barcelona La Boqueria Market Hall",
        region="Barcelona (Catalonia), Spain",
        category="food_market",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("food", "shopping", "money", "urban"),
        setting_prompt=(
            "soaring Modernista steel-and-stained-glass roof pavilion of Barcelona's La Boqueria market bathed in rainbow daylight, "
            "bursting wooden stalls stacked in vibrant pyramids of mangoes, dragonfruit, blood oranges, and striped juice bottles beside wrought-iron arch pillars"
        ),
        focal_props=("woven palm market basket", "chilled bright mango smoothie cup with paper straw", "pyramid of fresh figs", "brass vendor scale"),
        wardrobe_cue="mustard utility overshirt over striped knit tee, relaxed indigo straight trousers, and retro suede court trainers",
        explicit_keywords=("boqueria", "mercado", "barcelona", "fruta", "zumo", "comprar", "tienda"),
    ),
    CulturalWorld(
        id="es_albaicin_teteria",
        title="Granada Albaicín Tetería & Lantern Alley",
        region="Granada (Andalusia), Spain",
        category="street_plaza",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "culture", "friendship", "history"),
        setting_prompt=(
            "steep whitewashed cobblestone lane in Granada's Albaicín outside a glowing Moorish-style tetería hung with ruby, amber, and sapphire pierce-brass star lanterns, "
            "carved plaster horseshoe arches, low octagonal inlaid wooden tea tables with silver mint-tea pots, and terracotta cactus planters"
        ),
        focal_props=("engraved silver mint teapot", "amber jewel-toned tea glass", "mosaic tray", "carved cedar stool"),
        wardrobe_cue="warm terracotta patterned knit vest over crisp flowing shirt, olive wide-leg linen trousers, and leather ankle boots",
        explicit_keywords=("té", "tetería", "granada", "albaicín", "farol", "infusión"),
    ),
    CulturalWorld(
        id="es_valencia_horchateria",
        title="Valencia Modernista Horchatería Plaza",
        region="Valencia, Spain",
        category="food_market",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "summer", "urban", "friendship"),
        setting_prompt=(
            "sun-drenched Valencia plaza corner featuring an emerald-glazed Modernista ceramic horchatería facade with sculpted floral tile reliefs, "
            "shaded wrought-iron sidewalk tables topped with tall frosted glasses of creamy horchata and golden fartons beside leafy palm trees"
        ),
        focal_props=("tall glass goblet of chilled horchata", "glazed stoneware plate", "colorful tiled coaster", "woven sunhat"),
        wardrobe_cue="breezy cobalt camp-collar cotton shirt, cream tailored chino shorts or linen skirt, and canvas espadrilles",
        explicit_keywords=("valencia", "horchata", "horchatería", "naranja", "verano", "calor"),
    ),
    CulturalWorld(
        id="es_madrid_rastro",
        title="Madrid El Rastro Vintage Street Market",
        region="Madrid (La Latina), Spain",
        category="shop",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("shopping", "music", "fashion", "money"),
        setting_prompt=(
            "sloping cobblestone Madrid street bustling with cascading crimson and ochre striped market awnings of El Rastro outdoor vintage fair, "
            "wooden racks of retro varsity and suede jackets, brass sunburst mirrors, crates of classic cassettes, and iron wrought balconies above"
        ),
        focal_props=("vintage Polaroid camera", "brass magnifying glass", "retro patterned suede jacket on hanger", "stack of cassette tapes"),
        wardrobe_cue="retro cobalt-and-cream suede track jacket over striped rugby polo, straight-leg indigo denim, and suede sneakers",
        explicit_keywords=("rastro", "ropa", "vintage", "segunda mano", "barato", "caro", "mercado"),
    ),
    CulturalWorld(
        id="es_donostia_concha",
        title="San Sebastián Pintxos & La Concha Seafront",
        region="San Sebastián (Basque Country), Spain",
        category="coastal_nature",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "coastal", "travel", "friendship"),
        setting_prompt=(
            "iconic ornate white sculpted-iron coastal balustrade along San Sebastián's crescent Bay of La Concha overlooking emerald island bay waves, "
            "paired at an open limestone corner archway with a marble pintxos counter displaying vibrant skewered bites and oak cider barrels"
        ),
        focal_props=("wooden skewer pintxos plate", "wrought-iron white seafront railing", "striped canvas daypack", "brass seaside bench"),
        wardrobe_cue="navy-and-white fine stripe fisherman sweater over collared shirt, tailored sand chinos, and classic white leather sneakers",
        explicit_keywords=("pintxos", "san sebastián", "donostia", "mar", "bahía", "costa"),
    ),
    CulturalWorld(
        id="es_barcelona_luthier",
        title="Barcelona Gothic Quarter Guitar Luthier",
        region="Barcelona (Barri Gòtic), Spain",
        category="shop",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("music", "culture", "history", "school"),
        setting_prompt=(
            "warm honey-cedar acoustic guitar showroom nestled inside a medieval Barcelona stone archway with rows of glossy Spanish classical guitars hanging on cream limestone walls, "
            "carved rose-wood rosettes catching golden courtyard sunbeams through gothic mullioned windows (strictly a showcase gallery, zero workbench tools)"
        ),
        focal_props=("handcrafted Spanish nylon-string classical guitar", "leather guitar strap", "carved oak music stand", "ivory capo"),
        wardrobe_cue="tailored forest-green corduroy jacket over off-white collared shirt, dark slate trousers, and ankle suede boots",
        explicit_keywords=("guitarra", "música", "musica", "canción", "cancion", "tocar", "concierto", "flamenco"),
    ),
    CulturalWorld(
        id="es_malaga_chiringuito",
        title="Málaga Mediterranean Beach Chiringuito",
        region="Málaga (Costa del Sol), Spain",
        category="coastal_nature",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("coastal", "sports", "food", "summer"),
        setting_prompt=(
            "breezy woven-palm thatched chiringuito pergola rising right above warm golden Mediterranean sand in Málaga, "
            "cobalt-and-white striped beach umbrellas, a traditional colorful painted wooden jabega fishing skiff resting by rolling turquoise surf"
        ),
        focal_props=("painted wooden oar", "chilled pineapple coconut cup", "volleyball", "woven straw tote"),
        wardrobe_cue="coral-and-cream striped resort camp shirt, relaxed linen shorts or flowing skirt, and tan leather slide sandals",
        explicit_keywords=("playa", "chiringuito", "málaga", "mar", "arena", "vacaciones", "nadar"),
    ),
    CulturalWorld(
        id="es_plaza_mayor_arcade",
        title="Spanish Plaza Mayor Sandstone Arcade",
        region="Salamanca / Madrid, Spain",
        category="street_plaza",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "monumental"),
        vibe_tags=("urban", "history", "celebration", "travel"),
        setting_prompt=(
            "symmetrical soaring golden sandstone colonnade of a grand historic Spanish Plaza Mayor framed by warm crimson facade shutters, "
            "black iron carriage lanterns glowing along arched vault ceilings, paved stone promenade, and open evening courtyard"
        ),
        focal_props=("leather backpack", "plain kraft paper pastry cone", "brass pocket watch", "carved stone arcade pillar"),
        wardrobe_cue="camel structured wool trench over indigo button-down shirt, dark tailored trousers, and cognac lace-up boots",
        explicit_keywords=("plaza mayor", "ayuntamiento", "plaza", "ciudad", "paseo", "noche"),
    ),
    CulturalWorld(
        id="es_madrid_metro",
        title="Madrid Ceramic-Tiled Metro Concourse",
        region="Madrid, Spain",
        category="transit_civic",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("travel", "urban", "morning", "school"),
        setting_prompt=(
            "gleaming classic Madrid Metro underground concourse clad in crisp ivory diamond tiles with emerald trim bands, "
            "polished curved brass barrier rails, arched vaulted ceiling lamps, and a sleek cobalt-accented metro train gliding beside the platform"
        ),
        focal_props=("red transit pass holder", "yellow canvas tote backpack", "wired headphones", "polished brass railing"),
        wardrobe_cue="tailored slate wool bomber jacket over striped rugby polo, cuffed chinos, and crisp leather sneakers",
        explicit_keywords=("metro", "estación", "estacion", "tren", "viaje", "viajar", "billete", "aeropuerto"),
    ),
    # ── Latin America ──
    CulturalWorld(
        id="es_coyoacan_mercado",
        title="Mexico City Coyoacán Papel Picado Mercado",
        region="Mexico City (Coyoacán), Mexico",
        category="food_market",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "shopping", "celebration", "culture"),
        setting_prompt=(
            "vibrant Mexico City Coyoacán sunlit courtyard mercado strung overhead with crisp magenta, turquoise, and saffron perforated papel picado banners, "
            "glazed blue-and-white Talavera ceramic stalls piled with bright marigolds, golden mangoes, and clay mugs beside cobalt colonial plaster arches"
        ),
        focal_props=("glazed blue Talavera clay mug", "woven striped morral shoulder bag", "marigold flower garland", "painted ceramic bowl"),
        wardrobe_cue="cobalt-blue denim jacket with subtle floral woven trim over crisp white shirt, warm rust trousers, and brown leather huaraches",
        explicit_keywords=("méxico", "mexico", "coyoacán", "taco", "mercado", "fiesta", "celebración", "comida"),
    ),
    CulturalWorld(
        id="es_san_telmo_fair",
        title="Buenos Aires San Telmo Antique Fair",
        region="Buenos Aires, Argentina",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("shopping", "music", "history", "urban"),
        setting_prompt=(
            "historic cobblestone Plaza Dorrego in Buenos Aires' San Telmo filled with burgundy outdoor market tables displaying vintage brass gramophones, "
            "cut-glass soda siphons, leather mate gourds, and black-and-white photography frames beneath wrought-iron balconies and tipa shade trees"
        ),
        focal_props=("carved silver-trimmed calabash mate gourd & bombilla", "emerald glass soda siphon", "vintage brass horn", "leather satchel"),
        wardrobe_cue="smart charcoal blazer over sky-blue striped Oxford shirt, dark slim trousers, and suede desert boots",
        explicit_keywords=("argentina", "buenos aires", "san telmo", "tango", "feria", "antigüedades", "mate"),
    ),
    CulturalWorld(
        id="es_la_boca_caminito",
        title="Buenos Aires La Boca Caminito Pastel Alley",
        region="Buenos Aires (La Boca), Argentina",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("urban", "music", "sports", "friendship"),
        setting_prompt=(
            "world-famous Buenos Aires El Caminito alley featuring boldly painted corrugated zinc townhouses in saturated canary yellow, cobalt blue, "
            "crimson, and emerald green with sculpted iron balconies, hanging flowering vines, and cobblestone street corner"
        ),
        focal_props=("classic vintage leather football", "brass trumpet case", "wooden artist easel palette", "painted wrought-iron railing"),
        wardrobe_cue="crimson-and-cream striped knit sweater vest over crisp white polo, cuffed navy trousers, and retro court sneakers",
        explicit_keywords=("caminito", "boca", "fútbol", "futbol", "colores", "barrio", "calle"),
    ),
    CulturalWorld(
        id="es_bogota_candelaria",
        title="Bogotá La Candelaria Cobblestone Roastery",
        region="Bogotá (La Candelaria), Colombia",
        category="food_market",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("coffee", "food", "urban", "morning"),
        setting_prompt=(
            "steep cobblestone lane in Bogotá's La Candelaria neighborhood framed by colonial white-and-ochre adobe townhouses with clay tile eaves, "
            "open cedar doorframe into a glowing Colombian specialty coffee bar displaying woven burlap coffee sacks, ceramic pour-over drippers, and misty green Andean mountain slope behind"
        ),
        focal_props=("ceramic pour-over coffee carafe", "woven Wayuu geometric shoulder bag", "steaming clay mug", "roasted bean basket"),
        wardrobe_cue="warm forest-green quilted utility jacket over oatmeal knit polo, dark twill pants, and stitched leather boots",
        explicit_keywords=("colombia", "bogotá", "bogota", "café", "cafe", "desayuno", "mañana"),
    ),
    CulturalWorld(
        id="es_oaxaca_textiles",
        title="Oaxaca Artisan Craft & Alebrije Courtyard",
        region="Oaxaca, Mexico",
        category="shop",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("shopping", "culture", "history", "celebration"),
        setting_prompt=(
            "sunlit Oaxaca terracotta-walled artisan courtyard draped with vibrant hand-loomed cochineal-red, indigo, and saffron geometric wool tapestries, "
            "carved wooden pedestals holding fantastical polka-dotted turquoise and magenta alebrije sculptures, and earthen adobe columns"
        ),
        focal_props=("brightly painted wooden alebrije figure", "folded geometric indigo shawl", "terracotta clay cup", "wicker basket"),
        wardrobe_cue="emerald embroidered cotton guayabera overshirt over crisp white shirt, natural cotton chinos, and leather loafers",
        explicit_keywords=("oaxaca", "artesanía", "artesania", "alebrije", "color", "regalo", "tradición"),
    ),
    CulturalWorld(
        id="es_cartagena_balcony",
        title="Cartagena Bougainvillea Colonial Balcony",
        region="Cartagena de Indias, Colombia",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("coastal", "travel", "friendship", "summer"),
        setting_prompt=(
            "warm sunlit golden-yellow colonial facade in Cartagena Walled City cascading with lush magenta bougainvillea blossoms spilling over "
            "a carved dark cedar second-story balcony and cobalt wooden shutters onto breezy Caribbean cobblestone plaza"
        ),
        focal_props=("woven vueltiao palm hat", "cold passionfruit glass bottle", "wooden maracas", "carved colonial balcony post"),
        wardrobe_cue="breezy crisp ivory guayabera linen shirt with turquoise handkerchief accent, light khaki trousers, and woven leather espadrilles",
        explicit_keywords=("cartagena", "caribe", "calor", "balcón", "balcon", "verano", "flores"),
    ),
    CulturalWorld(
        id="es_roma_norte_books",
        title="CDMX Roma Norte Art-Deco Bookstore",
        region="Mexico City (Roma Norte), Mexico",
        category="shop",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("books", "school", "urban", "friendship"),
        setting_prompt=(
            "warm curved Art-Deco neighborhood bookshop in Mexico City's Roma Norte framed by emerald geometric tile arches and floor-to-ceiling oak bookshelves, "
            "soft amber globe lamps, and wide arched glass windows looking out onto purple flowering jacaranda trees lining a quiet avenue"
        ),
        focal_props=("stack of colorful clothbound novels", "linen book tote", "brass bookmark", "ceramic cup"),
        wardrobe_cue="soft lavender-grey ribbed cardigan over striped collared shirt, dark pleated trousers, and classic suede sneakers",
        explicit_keywords=("librería", "libreria", "libro", "libros", "leer", "biblioteca", "estudio", "escuela", "examen"),
    ),
    CulturalWorld(
        id="es_lima_barranco",
        title="Lima Barranco Bridge of Sighs & Murals",
        region="Lima (Barranco), Peru",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("friendship", "urban", "music", "coastal"),
        setting_prompt=(
            "romantic crimson-painted wooden Bridge of Sighs spanning a leafy bougainvillea ravine in Lima's bohemian Barranco district, "
            "framed by crisp coastal Pacific twilight haze, bold abstract geometric street art walls, and warm antique globe streetlamps"
        ),
        focal_props=("acoustic guitar case", "linen journal", "polaroid snapshots with colorful border only", "carved wooden bridge railing"),
        wardrobe_cue="mustard corduroy overshirt over olive striped collar tee, dark slim chinos, and canvas hi-top sneakers",
        explicit_keywords=("lima", "barranco", "puente", "amigo", "amiga", "arte", "mural", "cita"),
    ),
    CulturalWorld(
        id="es_cusco_stone_alley",
        title="Cusco Incan Stone Alley & Weaver Shop",
        region="Cusco (Andes), Peru",
        category="shop",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("history", "travel", "shopping", "culture"),
        setting_prompt=(
            "awe-inspiring narrow cobblestone alley in Cusco bordered by monumental interlocking gray granite Incan walls tilted gently skyward, "
            "framed by an electric-cobalt carved timber shop doorway hung with vibrant rainbow skeins of soft Andean wool and terracotta roofs above"
        ),
        focal_props=("skein bundle of rainbow Andean wool", "woven terracotta poncho fold", "carved gourd rattle", "granite stone wall"),
        wardrobe_cue="crimson-and-navy Andean patterned wool sweater beneath olive field jacket, dark sturdy trousers, and leather hiking boots",
        explicit_keywords=("cusco", "perú", "peru", "montaña", "historia", "lana", "suéter", "frío"),
    ),
    CulturalWorld(
        id="es_valparaiso_funicular",
        title="Valparaíso Colorful Funicular Hillside",
        region="Valparaíso, Chile",
        category="transit_civic",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("travel", "urban", "coastal", "friendship"),
        setting_prompt=(
            "dizzyingly steep, kaleidoscopic Pacific hillside staircase terrace in Valparaíso flanked by corrugated tin houses painted cobalt, coral, mint, and gold, "
            "where an iconic century-old wooden rail funicular ascends beside cerulean ocean harbor panoramas"
        ),
        focal_props=("canvas daypack", "brass harbor binoculars", "knitted wool beanie tucked in pocket", "iron hill railing"),
        wardrobe_cue="navy striped windbreaker over mustard crewneck knit shirt, cuffed grey denim jeans, and retro suede trainers",
        explicit_keywords=("chile", "valparaíso", "valparaiso", "cerro", "ascensor", "puerto", "subir"),
    ),
    CulturalWorld(
        id="es_havana_malecon",
        title="Havana Malecón Seawall & Classic Promenade",
        region="Havana, Cuba",
        category="coastal_nature",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "tactile_props"),
        vibe_tags=("music", "coastal", "travel", "celebration"),
        setting_prompt=(
            "golden-hour seafront promenade along Havana's curving stone Malecón seawall where ocean mist rises over bright turquoise Caribbean waves, "
            "framed by weathered pastel mint and coral neoclassical arcades and gleaming cherry-red and turquoise 1950s vintage convertibles cruising past"
        ),
        focal_props=("wooden clave percussion sticks", "brass horn mouthpiece", "woven Panama hat", "sunlit sea wall"),
        wardrobe_cue="breezy mint-green guayabera shirt tucked neatly into cream tailored trousers with dark woven loafers",
        explicit_keywords=("habana", "cuba", "malecón", "malecon", "coche", "auto", "música", "salsa"),
    ),
    CulturalWorld(
        id="es_antigua_arch",
        title="Antigua Santa Catalina Arch & Cobblestone Market",
        region="Antigua Guatemala, Guatemala",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("travel", "history", "shopping", "nature"),
        setting_prompt=(
            "sun-bright cobblestone colonial avenue in Antigua Guatemala framing the iconic marigold-yellow Santa Catalina Arch beneath crisp blue sky, "
            "towered behind by a misty symmetrical green volcano cone and vibrant street market stalls draped in rainbow woven belts"
        ),
        focal_props=("woven rainbow belt sash", "glazed green ceramic mug", "leather travel pack", "wooden street cart"),
        wardrobe_cue="terracotta rolled-sleeve oxford shirt with indigo knit cardigan over shoulder, sand chinos, and brown boots",
        explicit_keywords=("guatemala", "antigua", "arco", "volcán", "volcan", "pueblo", "mercado"),
    ),
    CulturalWorld(
        id="es_montevideo_rambla",
        title="Montevideo Rambla Sunset Mate Promenade",
        region="Montevideo, Uruguay",
        category="coastal_nature",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "tactile_props"),
        vibe_tags=("friendship", "coastal", "sports", "autumn"),
        setting_prompt=(
            "expansive stone riverside coastal boardwalk of Montevideo's Rambla at warm orange-and-violet sunset along Río de la Plata waves, "
            "with classic curved granite seawall promenade benches, glowing steel thermos and mate set, and palm-lined lighthouse headland behind"
        ),
        focal_props=("leather-wrapped stainless thermos & mate gourd", "classic soccer ball", "striped wool scarf", "granite promenade rail"),
        wardrobe_cue="warm olive crewneck sweater over crisp white collared shirt, navy chinos, and clean court sneakers",
        explicit_keywords=("uruguay", "montevideo", "rambla", "atardecer", "pasear", "compañero"),
    ),
    # ── Landmark Worlds (4 Spain + 4 Latin America — Monumental Scale) ──
    CulturalWorld(
        id="es_landmark_sagrada",
        title="Barcelona Sagrada Família Stained-Glass Nave",
        region="Barcelona (Catalonia), Spain",
        category="landmark",
        indoor_outdoor="interior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "culture", "travel", "celebration"),
        setting_prompt=(
            "soaring interior forest-like white stone hyperboloid columns inside Barcelona's Sagrada Família branching skyward into sunlit ribbed star vaults, "
            "while radiant beams of emerald, sapphire, gold, and ruby stained-glass light pour diagonally across polished stone paving"
        ),
        focal_props=("faceted crystal prism light catcher", "geometric stone spiral replica", "bound notebook", "carved pillar base"),
        wardrobe_cue="tailored cream twill jacket over olive knit shirt, dark indigo trousers, and classic leather loafers",
        explicit_keywords=("gaudí", "gaudi", "sagrada familia", "catedral", "arquitectura", "luz"),
    ),
    CulturalWorld(
        id="es_landmark_alhambra",
        title="Granada Alhambra Nasrid Arches & Pool",
        region="Granada (Andalusia), Spain",
        category="landmark",
        indoor_outdoor="semi_open",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "culture", "travel"),
        setting_prompt=(
            "exquisite Court of the Myrtles at Granada's Alhambra framing towering lacy carved stucco Nasrid colonnade arches and mosaic dadoes, "
            "mirrored flawlessly in a long still emerald reflecting pool bordered by manicured dark myrtle hedges beneath Sierra Nevada peaks"
        ),
        focal_props=("brass geometric astrolabe replica", "terracotta geometric tile fragment", "sketchpad", "marble column rim"),
        wardrobe_cue="deep saffron-ochre linen blazer over crisp white collared shirt, tailored olive trousers, and tan suede shoes",
        explicit_keywords=("alhambra", "palacio", "granada", "historia", "patio", "árabe"),
    ),
    CulturalWorld(
        id="es_landmark_plaza_espana",
        title="Seville Plaza de España Canal & Bridges",
        region="Seville (Andalusia), Spain",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "travel", "celebration", "urban"),
        setting_prompt=(
            "sweeping semicircular terracotta-brick colonnade and towering twin Renaissance towers of Seville's Plaza de España, "
            "ringed by an emerald moat canal crossed by arched cobalt-and-gold azulejo porcelain bridges and small wooden rowboats"
        ),
        focal_props=("painted wooden oar", "ceramic bridge finial detail", "woven straw sunhat", "terracotta balustrade"),
        wardrobe_cue="royal-cobalt linen overshirt over crisp cream top, terracotta pleated chinos or skirt, and clean leather sandals",
        explicit_keywords=("plaza de españa", "sevilla", "puente", "canal", "barca"),
    ),
    CulturalWorld(
        id="es_landmark_segovia",
        title="Segovia Roman Aqueduct Plaza",
        region="Segovia (Castile), Spain",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "travel", "urban"),
        setting_prompt=(
            "towering double-tiered unmortared pale-grey granite arches of the Roman Aqueduct of Segovia soaring dramatically across an azure Castilian sky "
            "above a sunlit stone cobblestone plaza ringed by terracotta-roofed townhouses"
        ),
        focal_props=("brass surveyor plumblines", "carved wooden arch block set", "leather messenger pack", "granite plaza step"),
        wardrobe_cue="chestnut suede jacket over navy knit shirt, crisp charcoal trousers, and Chelsea boots",
        explicit_keywords=("segovia", "acueducto", "romano", "piedra", "historia"),
    ),
    CulturalWorld(
        id="es_landmark_machu_picchu",
        title="Machu Picchu Andean Mist Terraces",
        region="Cusco Region, Peru",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "travel", "nature"),
        setting_prompt=(
            "breathtaking stepped emerald agricultural stone terraces and precision-cut Incan granite temple walls of Machu Picchu perched high in misty clouds "
            "above towering jagged green Wayna Picchu peak bathed in golden morning sunbeams"
        ),
        focal_props=("compass & canvas field pack", "stainless flask", "woven wool trail wrap", "moss-trimmed stone terrace"),
        wardrobe_cue="olive belted trail jacket over rust-orange merino knit sweater, durable khaki cargo trousers, and rugged leather hiking boots",
        explicit_keywords=("machu picchu", "inca", "andes", "perú", "ruinas", "naturaleza"),
    ),
    CulturalWorld(
        id="es_landmark_chichen_itza",
        title="Chichén Itzá El Castillo Pyramid",
        region="Yucatán, Mexico",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "travel", "celebration", "culture"),
        setting_prompt=(
            "colossal nine-tiered pale limestone Temple of Kukulcán pyramid rising steeply over a manicured emerald-green tropical lawn "
            "ringed by Yucatán jungle palms under radiant sunrays illuminating its sculpted stone serpent balustrades"
        ),
        focal_props=("pocket brass sundial compass", "carved jade amulet replica", "linen sun cap", "limestone plaza edge"),
        wardrobe_cue="sand-khaki linen camp shirt over terracotta tee, olive utility trousers, and breathable trail sneakers",
        explicit_keywords=("chichén itzá", "maya", "pirámide", "piramide", "yucatán", "méxico"),
    ),
    CulturalWorld(
        id="es_landmark_teotihuacan",
        title="Teotihuacán Avenue of the Dead & Sun Pyramid",
        region="State of Mexico, Mexico",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "travel", "nature"),
        setting_prompt=(
            "vast volcanic basalt Causeway of the Dead leading directly toward the colossal stepped Pyramid of the Sun glowing warm ochre against crisp azure highland sky "
            "and dramatic prickly-pear desert hills"
        ),
        focal_props=("polished obsidian prism stone", "wide woven brim hat", "canvas hydration sling", "volcanic stone stair"),
        wardrobe_cue="crimson-ochre lightweight field overshirt over cream shirt, sand chinos, and sturdy suede desert boots",
        explicit_keywords=("teotihuacán", "pirámide", "sol", "antiguo", "desierto"),
    ),
    CulturalWorld(
        id="es_landmark_el_ateneo",
        title="Buenos Aires El Ateneo Grand Splendid Theater-Bookshop",
        region="Buenos Aires, Argentina",
        category="landmark",
        indoor_outdoor="interior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("books", "culture", "history", "school"),
        setting_prompt=(
            "spectacular 1919 Beaux-Arts Buenos Aires theater transformed into a soaring golden bookshop cathedral with curved crimson velvet opera balconies packed with colorful clothbound shelves, "
            "a frescoed ceiling dome glowing under warm brass chandeliers, and sunlit velvet reading boxes"
        ),
        focal_props=("thick gold-spined hardcover volume", "velvet bookmark", "espresso porcelain cup", "carved gilded theater rail"),
        wardrobe_cue="tailored deep-navy wool coat over cream turtleneck, plaid pleated trousers or skirt, and glossy oxblood loafers",
        explicit_keywords=("teatro", "biblioteca", "buenos aires", "lectura", "ópera", "libros"),
    ),
)

SPANISH_PROFILE = LanguageVisualProfile(
    language="spanish",
    lang_code="S",
    aliases=("es", "español", "espanol", "castellano", "latam"),
    palette_mood=(
        "BRAND PALETTE MOOD (SPANISH): Warm, energetic, expressive, welcoming.\n"
        "Key Accent Colors: Warm Cream, Orange, Terracotta, and Botanical Green.\n"
    ),
    idiom_markers=(
        "dicho", "modismo", "idiotismo", "refrán", "locución idiomática", "expresión idiomática",
        "costar un ojo", "ojo de la cara", "tomar el pelo", "en las nubes", "pan comido",
    ),
    idiom_environments=(
        (("pan comido",), "sunlit Seville azulejo-tiled pastelería counter showcasing an elaborate towering multi-tier cake with one slice missing beneath Moorish ceramic arches and golden morning rays"),
        (("ojo de la cara",), "chic metropolitan boutique along an ornate Madrid cobblestone promenade (featuring: extravagant luxury mannequin pedestals, marble counter, velvet curtains)"),
    ),
    cultural_cue=(
        "Spanish and Latin American plazas, colorful streets, historic markets, coastal boardwalks, "
        "and landmarks across Spain, Mexico, Argentina, Colombia, Peru, Chile, Cuba, Guatemala, and Uruguay"
    ),
    cultural_worlds=SPANISH_CULTURAL_WORLDS,
)
