"""
visual/languages/english.py — English visual palette, heteronyms, idiom markers, and Global Anglophone Cultural World Atlas.
"""
from __future__ import annotations

from .base import CulturalWorld, LanguageVisualProfile

ENGLISH_HETERONYM_DOMAINS = {
    "record": "vintage Soho indie vinyl record shop and acoustic listening room (featuring: warm oak record crates, glowing analog turntable console, acoustic paneled listening booth, red-brick street window)",
    "permit": "metropolitan transit hub and brass security gatehouse (featuring: striped transit entry barrier, glass attendant booth, grand station concourse, wooden waiting bench)",
    "project": "dramatic sunset rooftop film set overlooking harbor bridge towers (featuring: cinema camera on heavy tripod, brass megaphone, clapperboard without text, warm string bulbs)",
    "present": "festive celebratory reception marble banquet hall (featuring: long dressed banquet table, velvet curtain alcove, elaborate ribbon-wrapped gift box centerpiece, sunlit terrace)",
    "object": "historic maritime curiosity archive and museum hall (featuring: oak-and-glass specimen cabinets, brass scales, antique compasses, carved vaulted stone ceiling)",
    "contract": "stately paneled mahogany law library or varsity athletic club terrace (featuring: green-glass brass reading lamps, bound leather volumes, oak table, sunlit stadium arches)",
    "conduct": "gilded symphony concert hall and tiered balcony (featuring: curved orchestra podium, polished wooden music stands without notes, gleaming brass instruments, crimson velvet seating)",
    "desert": "golden red-rock sandstone desert canyon overlook camp (featuring: woven canvas expedition tent, brass star-compass map table, glowing sunset dune ridge)",
    "increase": "bustling glass-and-timber harbor logistics boardwalk (featuring: wooden shipping crates, brass cargo pulleys, moored container ships beyond, bustling dock counter)",
    "decrease": "quiet twilight Oxford collegiate oak library alcove (featuring: green-glass brass banker lamps, towering arched stained window overlooking evening spires, quiet mahogany reading table)",
    "import": "international maritime harbor quay and Victorian timber warehouse pier (featuring: moored freight vessel beyond harbor wall, stamped timber cargo crates, dockyard cranes)",
    "export": "sunny coastal container wharf and ocean shipping promenade (featuring: stacked colorful timber crates, harbor viewing railing, glistening cargo ships on bay)",
    "protest": "historic stone civic town hall steps and public square (featuring: grand sandstone columns, brass speaking lectern, sunny cobblestone gathering plaza)",
    "refuse": "vibrant community vintage swap-meet and upcycled craft plaza (featuring: wooden sorting tables, colorful salvaged bike frames, striped canvas awnings)",
    "rebel": "cobblestone indie zine & vintage jacket corner in historic red-brick district (featuring: colorful graphic patch displays without words, brick railway arches, vinyl crates)",
    "address": "grand civic auditorium stage or stately oak study hall (featuring: carved mahogany podium stage, arched plaster gallery, towering bookshelves)",
}

ENGLISH_CULTURAL_WORLDS: tuple[CulturalWorld, ...] = (
    # ── United Kingdom (England, Scotland, Wales) ──
    CulturalWorld(
        id="en_soho_vinyl",
        title="London Soho Vinyl Record Shop",
        region="London (England), UK",
        category="shop",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("music", "shopping", "friendship", "urban"),
        setting_prompt=(
            "iconic narrow London Soho independent vinyl shop packed with oak LP bins displaying colorful abstract geometric album artwork sleeves, "
            "retro walnut turntable listening counter with coiled headphones, warm pendant lamps, and rain-slicked brick alley visible outside bow glass"
        ),
        focal_props=("vibrant illustrated vinyl record sleeve", "silver cushioned headphones", "walnut turntable tonearm", "ceramic tea mug"),
        wardrobe_cue="burgundy waxed cotton jacket or cropped tweed blazer over striped rugby collar shirt, tailored dark trousers, and Chelsea boots",
        explicit_keywords=("vinyl", "record", "music", "song", "album", "band", "concert", "soho"),
    ),
    CulturalWorld(
        id="en_borough_market",
        title="London Borough Market Victorian Viaduct",
        region="London (England), UK",
        category="food_market",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("food", "shopping", "urban", "money"),
        setting_prompt=(
            "bustling London Borough Market tucked beneath soaring heritage sage-green riveted cast-iron railway viaduct arches, "
            "overflowing timber stalls stacked with crusty sourdough loaves, aged cheddar wheels, crisp red apples, and hanging copper scales"
        ),
        focal_props=("wicker market basket with crusty sourdough", "wax-paper parcel", "brass vendor scale", "cast-iron pillar"),
        wardrobe_cue="olive quilted field coat over oatmeal fisherman knit sweater, dark indigo jeans, and sturdy leather brogues",
        explicit_keywords=("market", "borough", "bakery", "bread", "cheese", "pie", "pastry", "groceries"),
    ),
    CulturalWorld(
        id="en_notting_hill_books",
        title="Notting Hill Pastel Bookshop",
        region="London (England), UK",
        category="shop",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("books", "shopping", "friendship", "urban"),
        setting_prompt=(
            "charming London Notting Hill corner bookshop with mint-green and buttercream painted Georgian woodwork, "
            "curved bow display window overflowing with colorful clothbound book spines, oak sidewalk book trough, and pastel townhomes along cobbled mews"
        ),
        focal_props=("bundle of colorful hardcover books tied with twine", "cotton canvas book tote", "folding brass spectacles", "curved oak counter"),
        wardrobe_cue="soft camel wool cardigan over collared Peter Pan shirt, tartan pleated skirt or dark cords, and brown Oxford loafers",
        explicit_keywords=("bookshop", "bookstore", "book", "books", "reading", "library", "novel", "story"),
    ),
    CulturalWorld(
        id="en_oxford_quad",
        title="Oxford Honey-Stone Collegiate Quad",
        region="Oxford (England), UK",
        category="transit_civic",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("school", "history", "books", "autumn"),
        setting_prompt=(
            "stately honey-limestone Oxford college quadrangle rimmed by soaring Gothic vaulted cloister arches and golden autumn Virginia creeper vines, "
            "manicured emerald lawn, and classic vintage wicker-basket bicycles leaning neatly beside iron-studded oak doors"
        ),
        focal_props=("leather collegiate briefcase", "vintage bicycle with wicker front basket", "rolled striped college scarf", "carved stone archway"),
        wardrobe_cue="forest-green tailored blazer over crisp light-blue button-down, charcoal flannel trousers, burgundy striped scarf, and penny loafers",
        explicit_keywords=("oxford", "university", "college", "school", "study", "exam", "student", "homework", "assignment", "grade"),
    ),
    CulturalWorld(
        id="en_camden_lock",
        title="London Camden Canal Lock Market",
        region="London (England), UK",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("shopping", "urban", "travel", "food"),
        setting_prompt=(
            "lively brick Camden Canal Lock cobblestone bridge overlooking painted crimson-and-emerald wooden narrowboats moored in shimmering canal lock water, "
            "striped open-air craft stalls, and arched red-brick Victorian warehouse colonnades behind"
        ),
        focal_props=("striped knit canvas messenger bag", "steaming street-food paper bowl", "wooden canal lock lever", "camera strap"),
        wardrobe_cue="charcoal vintage denim trucker jacket over yellow-striped turtleneck, relaxed corduroy pants, and combat lace-up boots",
        explicit_keywords=("canal", "boat", "camden", "weekend", "vintage", "thrift"),
    ),
    CulturalWorld(
        id="en_cornwall_harbor",
        title="Cornwall Coastal Fish & Harbor Pier",
        region="St Ives / Cornwall (England), UK",
        category="coastal_nature",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "tactile_props"),
        vibe_tags=("coastal", "food", "nature", "travel"),
        setting_prompt=(
            "dramatic granite stone breakwater harbor pier in St Ives, Cornwall, with turquoise-and-red wooden fishing boats bobbing gently in clear Atlantic cove water, "
            "whitewashed cottages climbing emerald headlands, and crisp gulls wheeling past a stone harbour wall"
        ),
        focal_props=("striped kraft paper wrap", "wooden crab-pot creel basket", "coiled harbor rope", "lighthouse tower vista"),
        wardrobe_cue="canary-yellow coastal raincoat over navy cable-knit sweater, cuffed denim, and weather-proof Chelsea boots",
        explicit_keywords=("beach", "harbor", "harbour", "sea", "fish", "boat", "ocean", "coastal", "shore"),
    ),
    CulturalWorld(
        id="en_edinburgh_mile",
        title="Edinburgh Royal Mile Stone Close",
        region="Edinburgh (Scotland), UK",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("history", "books", "autumn", "urban"),
        setting_prompt=(
            "atmospheric dark-whinstone medieval stepped close off Edinburgh's Royal Mile arched overhead by carved stone flying masonry, "
            "warm glowing iron street lanterns, tartan wool throws in timber bow shopfronts, and dramatic volcanic crag silhouette in mist behind"
        ),
        focal_props=("woven emerald tartan wool scarf", "leather field journal", "antique brass lantern handle", "carved stone steps"),
        wardrobe_cue="deep navy double-breasted peacoat over forest tartan collared shirt, dark wool trousers, and laced leather boots",
        explicit_keywords=("edinburgh", "scotland", "castle", "stone", "rain", "weather", "cold", "winter"),
    ),
    CulturalWorld(
        id="en_cardiff_arcade",
        title="Cardiff Victorian Morgan Arcade",
        region="Cardiff (Wales), UK",
        category="shop",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("shopping", "history", "music", "coffee"),
        setting_prompt=(
            "ornate Victorian Cardiff Morgan Arcade glazed under curving carved dark-timber balconies and luminous glass skylights, "
            "Victorian brass bracket lamps, checkered tile walkway, and boutique tea & acoustic instrument shopfronts with clean clear glass bays"
        ),
        focal_props=("wooden acoustic ukulele prop", "tin teapot canister", "brass gallery rail", "vinyl satchel"),
        wardrobe_cue="plum herringbone blazer over cream collar blouse or shirt, tailored slate trousers, and glossy oxblood brogues",
        explicit_keywords=("wales", "cardiff", "arcade", "shop", "tea", "gift"),
    ),
    # ── Ireland ──
    CulturalWorld(
        id="en_dublin_temple_bar",
        title="Dublin Cobblestone Acoustic Corner",
        region="Dublin, Ireland",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("music", "friendship", "urban", "history"),
        setting_prompt=(
            "lively crimson-and-emerald painted timber storefront facades along a gleaming wet-cobblestone Dublin Cultural Quarter corner, "
            "glowing brass carriageway lamps, overflowing hanging flower baskets, and a dark-cherry wooden fiddle case leaning by carved paneled door"
        ),
        focal_props=("curved mahogany violin/fiddle case", "emerald tweed flat cap resting on ledge", "knit wool tote", "cobblestone kerb"),
        wardrobe_cue="emerald tweed sport jacket over textured cream knit sweater, indigo jeans, and chestnut leather boots",
        explicit_keywords=("dublin", "ireland", "fiddle", "music", "violin", "friend", "street"),
    ),
    CulturalWorld(
        id="en_galway_latin_quarter",
        title="Galway Colorful Harbor Quay",
        region="Galway, Ireland",
        category="coastal_nature",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("coastal", "travel", "food", "friendship"),
        setting_prompt=(
            "bright rainbow row of cobalt, saffron, coral, and sage cottages along Galway's Claddagh waterfront pier, "
            "traditional black-hulled Galway hooker wooden sailboats with russet sails moored beside medieval Spanish stone arches"
        ),
        focal_props=("canvas maritime backpack", "ceramic steaming soup bowl", "brass boat cleat", "russet sailcloth bundle"),
        wardrobe_cue="warm mustard cable-knit sweater under navy windproof shell, dark cords, and waterproof ankle boots",
        explicit_keywords=("galway", "quay", "sail", "harbor", "boat", "wind", "rain"),
    ),
    # ── United States ──
    CulturalWorld(
        id="en_retro_diner",
        title="American Retro Chrome & Turquoise Diner",
        region="Route 66 / Southwest, USA",
        category="food_market",
        indoor_outdoor="interior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "friendship", "celebration", "travel"),
        setting_prompt=(
            "vibrant mid-century 1950s American chrome-and-turquoise roadside diner featuring glossy black-and-white checkered floor tiles, "
            "swivel chrome bar stools along a speckled Formica counter, cherry-red vinyl booths, tall frosted milkshake glasses, and sunlit desert highway outside wraparound glass"
        ),
        focal_props=("tall fluted glass strawberry milkshake with striped straw", "glossy chrome napkin dispenser", "pancake stack", "retro jukebox chrome grille"),
        wardrobe_cue="teal-and-cream varsity letterman cardigan over striped collar polo, cuffed dark denim, and classic canvas high-tops",
        explicit_keywords=("diner", "milkshake", "burger", "pancake", "breakfast", "lunch", "restaurant", "cafe", "coffee"),
    ),
    CulturalWorld(
        id="en_brooklyn_stoop",
        title="Brooklyn Brownstone Stoop & Corner Bodega",
        region="New York (Brooklyn), USA",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("urban", "friendship", "food", "autumn"),
        setting_prompt=(
            "warm carved sandstone Brooklyn brownstone townhouse stoop strewn with golden-amber autumn maple leaves beside a sunlit corner neighborhood bodega "
            "displaying vibrant wooden fruit crates of apples and tangerines beneath striped awning and classic cast-iron fire escapes"
        ),
        focal_props=("kraft paper grocery bag with fresh bagel & apples", "striped knit backpack", "orange basketball", "sandstone handrail"),
        wardrobe_cue="forest-green wool overshirt over crisp plaid flannel button-down, relaxed khaki chinos, and retro high-top court sneakers",
        explicit_keywords=("brooklyn", "new york", "neighborhood", "apartment", "neighbor", "bagel", "basketball", "street"),
    ),
    CulturalWorld(
        id="en_sf_cable_car",
        title="San Francisco Cable Car Hill Street",
        region="San Francisco (California), USA",
        category="transit_civic",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("travel", "urban", "morning", "sports"),
        setting_prompt=(
            "steep iconic San Francisco cobblestone-trimmed street climbing past pastel Victorian bay-window townhouses, "
            "with an open-air burgundy-and-brass historic cable car cresting steel rail tracks against shimmering bay water and drifting morning mist"
        ),
        focal_props=("brass bell grip handle", "canvas commuter pack", "insulated travel tumbler", "folding map"),
        wardrobe_cue="layered ochre windbreaker over navy striped sweater, dark slim jeans, and clean suede sneakers",
        explicit_keywords=("san francisco", "tram", "hill", "cable car", "steep", "commute", "street"),
    ),
    CulturalWorld(
        id="en_seattle_pier",
        title="Seattle Pike Place Harbor Pier",
        region="Seattle (Washington), USA",
        category="coastal_nature",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("coastal", "food", "travel", "morning"),
        setting_prompt=(
            "weathered Puget Sound cedar timber waterfront pier overlooking crisp emerald-and-white harbor ferries crossing misty Puget Sound toward jagged snow-capped Olympic Mountains, "
            "flanked by glowing arched craft and flower-free fruit stalls and espresso cart"
        ),
        focal_props=("reusable ceramic travel cup", "canvas rainy-day tote", "fresh red apple crate", "timber pier bollard"),
        wardrobe_cue="rust-orange weatherproof parka over plaid collared shirt, indigo denim jeans, and sturdy trail sneakers",
        explicit_keywords=("seattle", "ferry", "pier", "rain", "mist", "mountain", "coffee"),
    ),
    CulturalWorld(
        id="en_central_park_bridge",
        title="Central Park Bow Bridge Autumn",
        region="New York (Manhattan), USA",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "tactile_props"),
        vibe_tags=("nature", "autumn", "friendship", "sports"),
        setting_prompt=(
            "ornate Victorian cast-iron Bow Bridge arching gracefully over mirror-still Central Park lake framed by fiery scarlet and amber autumn maples, "
            "floating rowboats, and tall sunlit Art-Deco limestone towers rising cleanly above the treetops"
        ),
        focal_props=("wooden rowboat oar", "woven tartan throw", "sketch notebook", "ornate cast-iron bridge filigree"),
        wardrobe_cue="camel tailored trench coat over burgundy crewneck sweater, dark trousers, and crisp suede desert boots",
        explicit_keywords=("park", "central park", "bridge", "autumn", "fall", "lake", "nature", "tree", "walk"),
    ),
    CulturalWorld(
        id="en_chicago_l_corner",
        title="Chicago Elevated Rail & Blues Corner",
        region="Chicago (Illinois), USA",
        category="transit_civic",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("music", "urban", "travel", "night"),
        setting_prompt=(
            "dramatic riveted dark-green steel Chicago Elevated rail trestle arcing overhead across a classic brick corner intersection where a sleek silver train passes above, "
            "casting warm golden twilight reflections onto a corner vintage brass saxophone & blues record storefront"
        ),
        focal_props=("polished brass alto saxophone case", "vinyl record crate", "leather satchel", "steel bridge girder"),
        wardrobe_cue="deep-cobalt wool varsity jacket over Oxford shirt, dark straight chinos, and black leather boots",
        explicit_keywords=("chicago", "train", "station", "jazz", "blues", "saxophone", "city", "subway"),
    ),
    CulturalWorld(
        id="en_nola_balcony",
        title="New Orleans French Quarter Iron-Lace Balcony",
        region="New Orleans (Louisiana), USA",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("music", "celebration", "friendship", "culture"),
        setting_prompt=(
            "storybook New Orleans French Quarter street corner under an intricate black wrought-iron lace second-story gallery hung with cascading ferns, "
            "pastel turquoise and coral shuttered Creole townhouses, brass gas-lantern sconces, and a gleaming brass trumpet resting beside wooden shutters"
        ),
        focal_props=("gleaming brass trumpet", "powdered beignet pastry plate", "beaded festive necklace strands", "iron gallery column"),
        wardrobe_cue="crisp sage-green linen camp shirt, cream tailored trousers, woven fedora resting nearby, and tan leather loafers",
        explicit_keywords=("new orleans", "jazz", "trumpet", "brass", "party", "celebration", "balcony"),
    ),
    CulturalWorld(
        id="en_venice_skate_bowl",
        title="Venice Beach Coastal Skate Bowl",
        region="Los Angeles (California), USA",
        category="coastal_nature",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "tactile_props"),
        vibe_tags=("sports", "summer", "friendship", "coastal"),
        setting_prompt=(
            "sun-drenched Venice Beach seaside concrete skate bowl curving beside bright golden Pacific sand, tall towering silhouettes of California fan palms "
            "glowing against a peach-and-violet sunset ocean sky"
        ),
        focal_props=("maple wood skateboard with striped deck", "canvas daypack", "reusable insulated water flask", "concrete coping rim"),
        wardrobe_cue="retro cobalt-and-cream striped rugby polo over white undershirt, relaxed olive skate chinos, and suede vulcanized sneakers",
        explicit_keywords=("skate", "skateboard", "california", "beach", "sport", "exercise", "sun", "summer"),
    ),
    # ── Canada ──
    CulturalWorld(
        id="en_toronto_kensington",
        title="Toronto Kensington Market Vintage Thrift",
        region="Toronto (Ontario), Canada",
        category="shop",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("shopping", "fashion", "urban", "food"),
        setting_prompt=(
            "eclectic Kensington Market lane in Toronto bordered by painted emerald and mustard Victorian bay-and-gable houses "
            "bursting with outdoor racks of vintage varsity jackets, colorful knitted sweaters, overflowing fruit stalls, and festive warm string lights"
        ),
        focal_props=("retro plaid wool overshirt on wooden hanger", "striped knit toque beanie", "milk crate of apples", "canvas tote"),
        wardrobe_cue="forest-and-navy plaid wool flannel jacket over crisp collar shirt, cuffed corduroy pants, and leather hiking sneakers",
        explicit_keywords=("toronto", "canada", "thrift", "jacket", "winter", "clothes", "market"),
    ),
    CulturalWorld(
        id="en_vancouver_granville",
        title="Vancouver Granville Island Timber Harbor Market",
        region="Vancouver (British Columbia), Canada",
        category="food_market",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "coastal", "shopping", "nature"),
        setting_prompt=(
            "bright Pacific Northwest cedar-beam public harbor pavilion at Granville Island overlooking gleaming blue False Creek sailboat marinas and dark evergreen mountains, "
            "stalls piled with wild Pacific berries, golden honey jars, and maple pastries"
        ),
        focal_props=("wooden berry punnet basket", "amber glass honey jar", "insulated outdoor tumbler", "timber dock rail"),
        wardrobe_cue="slate quilted fleece vest over teal-and-cream flannel button-up, khaki trail chinos, and rugged leather boots",
        explicit_keywords=("vancouver", "island", "harbor", "honey", "berries", "nature"),
    ),
    # ── Australia & New Zealand ──
    CulturalWorld(
        id="en_sydney_wharf",
        title="Sydney Circular Quay Ferry Wharf",
        region="Sydney (New South Wales), Australia",
        category="coastal_nature",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("coastal", "travel", "sports", "summer"),
        setting_prompt=(
            "sun-bright weathered timber Circular Quay ferry wharf stretching over sparkling cobalt Sydney Harbour where classic emerald-and-gold ferries "
            "and crisp white sailboat spinnakers glide beneath sweeping steel harbor bridge arches"
        ),
        focal_props=("striped canvas beach pack", "chilled citrus glass bottle", "tinted sunglasses", "heavy hemp harbor bollard"),
        wardrobe_cue="sky-blue short-sleeve linen resort shirt, cream pleated chino shorts or midi skirt, and crisp white leather trainers",
        explicit_keywords=("sydney", "australia", "ferry", "harbour", "ocean", "sail", "summer"),
    ),
    CulturalWorld(
        id="en_melbourne_hosier",
        title="Melbourne Hosier Lane Mural & Espresso Alley",
        region="Melbourne (Victoria), Australia",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("urban", "coffee", "friendship", "music"),
        setting_prompt=(
            "famous narrow bluestone cobblestone laneway in Melbourne wrapped in vibrant layered geometric street murals painted in bold swirling emerald, coral, and gold shapes, "
            "warm glowing iron hole-in-the-wall espresso window with gleaming copper machine and small wooden alleyway stools"
        ),
        focal_props=("ceramic flat-white coffee cup", "canvas portfolio sleeve", "vintage 35mm camera", "bluestone curb"),
        wardrobe_cue="charcoal cropped utility jacket over crisp white collared knit polo, wide slate trousers, and chunky black derbies",
        explicit_keywords=("melbourne", "alley", "laneway", "espresso", "art", "street"),
    ),
    CulturalWorld(
        id="en_bondi_boardwalk",
        title="Bondi Ocean Pool Sandstone Boardwalk",
        region="Sydney (Bondi), Australia",
        category="coastal_nature",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "tactile_props"),
        vibe_tags=("sports", "coastal", "summer", "health"),
        setting_prompt=(
            "dramatic sculpted sandstone cliff boardwalk beside Bondi's turquoise rock-cut ocean lap pool as clean white Pacific surf splashes against white concrete sea walls "
            "under dazzling Australian coastal sunlight"
        ),
        focal_props=("turquoise foam surfboard", "striped cotton beach towel", "insulated water bottle", "coastal stainless rail"),
        wardrobe_cue="crisp coral-and-cream camp shirt, lightweight sand shorts, woven visor hat, and coastal deck sneakers",
        explicit_keywords=("pool", "swim", "surf", "bondi", "wave", "ocean", "gym", "workout", "athletic"),
    ),
    CulturalWorld(
        id="en_queenstown_jetty",
        title="Queenstown Lake Wakatipu Alpine Jetty",
        region="Queenstown (South Island), New Zealand",
        category="coastal_nature",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("nature", "travel", "sports", "winter"),
        setting_prompt=(
            "serene weathered cedar timber jetty extending across crystal-clear glacial-blue Lake Wakatipu framed directly by towering jagged Remarkables mountain peaks "
            "dusted with crisp snow and golden autumn lakeside willows"
        ),
        focal_props=("rugged alpine daypack", "stainless steel thermos", "wooden canoe paddle", "mountain trail compass"),
        wardrobe_cue="forest-emerald windproof fleece jacket over cream waffle knit top, dark hiking trousers, and waterproof trail boots",
        explicit_keywords=("new zealand", "queenstown", "lake", "mountain", "hiking", "nature", "trail"),
    ),
    CulturalWorld(
        id="en_auckland_devonport",
        title="Auckland Devonport Waterfront Bookshop Corner",
        region="Auckland (North Island), New Zealand",
        category="shop",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("books", "coastal", "morning", "friendship"),
        setting_prompt=(
            "sunlit Victorian timber verandah bookshop facing turquoise Waitematā Harbour across leafy Pohutukawa crimson blossoms, "
            "warm rimu wood interior shelves stacked with colorful clothbound books and brass ferry bell near the veranda post"
        ),
        focal_props=("clothbound travel atlas", "canvas harbor tote", "porcelain teacup", "painted wooden verandah railing"),
        wardrobe_cue="mustard knit cardigan over collared chambray shirt, cuffed ivory chinos, and canvas slip-on shoes",
        explicit_keywords=("auckland", "veranda", "harbor", "bookstore", "reading"),
    ),
    # ── Wider Global Anglophone World (Caribbean, Africa, Southeast Asia) ──
    CulturalWorld(
        id="en_kingston_vinyl_market",
        title="Kingston Tropical Music & Fruit Plaza",
        region="Kingston, Jamaica",
        category="food_market",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("music", "food", "summer", "celebration"),
        setting_prompt=(
            "sun-drenched Caribbean open-air Kingston music & fruit courtyard framed by bright teal and marigold painted timber stalls "
            "stacked with yellow-gold pineapples, ripe mangoes, wooden crate boxes of classic dub-and-reggae 7-inch vinyl sleeves, and warm palm shade"
        ),
        focal_props=("wooden crate of colorful 7-inch vinyl singles", "fresh cut pineapple goblet", "woven straw market hat", "acoustic bongo drum"),
        wardrobe_cue="breezy canary-gold and emerald short-sleeve knit camp shirt, tailored khaki trousers, and leather sandals",
        explicit_keywords=("jamaica", "kingston", "reggae", "tropical", "mango", "pineapple", "music"),
    ),
    CulturalWorld(
        id="en_cape_town_bokaap",
        title="Cape Town Bo-Kaap Colorful Cobblestone Slope",
        region="Cape Town, South Africa",
        category="street_plaza",
        indoor_outdoor="exterior",
        staging_tags=("layered_depth", "threshold", "tactile_props", "monumental"),
        vibe_tags=("urban", "travel", "history", "friendship"),
        setting_prompt=(
            "steep cobblestone Cape Malay street in Cape Town's Bo-Kaap lined with vivid magenta, tangerine, turquoise, and lime Georgian-stucco homes, "
            "carved wooden stoop balustrades, and the colossal flat-topped sandstone wall of Table Mountain rising into clear blue sky behind"
        ),
        focal_props=("woven striped tote", "spiced clay teapot tray", "leather camera bag", "painted stone stoop"),
        wardrobe_cue="crisp terracotta denim overshirt over striped knit shirt, relaxed cream chinos, and clean court sneakers",
        explicit_keywords=("cape town", "south africa", "mountain", "colorful", "street", "neighborhood"),
    ),
    CulturalWorld(
        id="en_singapore_katong",
        title="Singapore Katong Peranakan Shophouse Lane",
        region="Singapore (Katong), Southeast Asia",
        category="street_plaza",
        indoor_outdoor="semi_open",
        staging_tags=("layered_depth", "threshold", "tactile_props"),
        vibe_tags=("food", "shopping", "culture", "summer"),
        setting_prompt=(
            "ornate Peranakan heritage five-foot-way colonnade in Singapore's Katong clad in pastel coral, mint, and baby-blue glazed floral ceramic facade tiles, "
            "swung wooden louver shutters, suspended crimson silk lanterns, and ceramic teaware displays along shady arched arcade"
        ),
        focal_props=("hand-painted floral porcelain tea bowl", "woven bamboo steamer basket", "striped parasol", "carved shophouse pillar"),
        wardrobe_cue="mint-green structured linen camp shirt over crisp white tee, tailored dark-navy shorts or pleated trousers, and woven loafers",
        explicit_keywords=("singapore", "katong", "lantern", "tea", "tiles", "asian", "market"),
    ),
    # ── Global Anglophone Landmarks (Monumental Scale for FUN_FACTS & Wonder Shots) ──
    CulturalWorld(
        id="en_landmark_tower_bridge",
        title="London Tower Bridge Bascule Walkway",
        region="London (England), UK",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "travel", "urban"),
        setting_prompt=(
            "grand Thames riverside granite embankment looking straight up at the twin Victorian Gothic stone towers, powder-blue suspension chains, "
            "and soaring high-level steel walkways of London's Tower Bridge glowing amber against drifting English clouds"
        ),
        focal_props=("brass folding spyglass", "leather satchel", "riverfront wrought-iron bollard", "rolled architectural blueprint with wavy geometric lines"),
        wardrobe_cue="structured camel trench coat over burgundy knit turtleneck, dark tailored trousers, and polished leather loafers",
        explicit_keywords=("london", "tower bridge", "thames", "bridge", "britain", "england"),
    ),
    CulturalWorld(
        id="en_landmark_nhm",
        title="London Natural History Museum Hintze Hall",
        region="London (England), UK",
        category="landmark",
        indoor_outdoor="interior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "school", "culture", "nature"),
        setting_prompt=(
            "awe-inspiring Romanesque terracotta cathedral nave of London Natural History Museum's Hintze Hall featuring towering sculpted cream-and-sienna archways, "
            "grand double marble staircases, and a colossal suspended ocean whale skeleton floating overhead in sunlit vaulted glass daylight"
        ),
        focal_props=("magnifier loupe", "fossil ammonite specimen replica", "field sketchbook with charcoal fossil sketches", "carved terracotta balustrade"),
        wardrobe_cue="sage-green wool blazer over striped collared shirt, charcoal flannel trousers, and chestnut leather oxford boots",
        explicit_keywords=("museum", "dinosaur", "whale", "fossil", "science", "history"),
    ),
    CulturalWorld(
        id="en_landmark_stonehenge",
        title="Stonehenge Golden-Dawn Ring",
        region="Wiltshire (England), UK",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("history", "nature", "travel"),
        setting_prompt=(
            "colossal weathered Neolithic sarsen sandstone monoliths and towering horizontal lintels of Stonehenge casting long amber dawn shadows "
            "across silver morning mist and emerald Wiltshire downs beneath luminous golden rays"
        ),
        focal_props=("brass astronomer pocket sundial", "canvas field sling", "leather notebook", "wooden fence rail"),
        wardrobe_cue="warm rust-brown corduroy jacket over cream fisherman cable-knit sweater, dark twill trousers, and leather trail boots",
        explicit_keywords=("stonehenge", "ancient", "stones", "dawn", "sun", "monument"),
    ),
    CulturalWorld(
        id="en_landmark_grand_central",
        title="Grand Central Terminal Celestial Concourse",
        region="New York City, USA",
        category="landmark",
        indoor_outdoor="interior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("travel", "history", "urban", "celebration"),
        setting_prompt=(
            "breathtaking main Beaux-Arts limestone concourse of Grand Central Terminal where towering 60-foot arched windows slice dramatic volumetric golden sunbeams "
            "across gleaming marble floors beneath a soaring turquoise ceiling dome painted with golden zodiac constellations"
        ),
        focal_props=("gleaming four-faced brass concourse lamp post", "tan belted leather weekender", "brass pocket watch", "marble stair rail"),
        wardrobe_cue="navy herringbone overcoat over crisp striped oxford shirt, tailored taupe trousers, and glossy brown loafers",
        explicit_keywords=("grand central", "terminal", "station", "concourse", "new york", "train"),
    ),
    CulturalWorld(
        id="en_landmark_golden_gate",
        title="Golden Gate Bridge Marin Overlook",
        region="San Francisco (California), USA",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("travel", "coastal", "nature"),
        setting_prompt=(
            "dramatic Marin Headlands cliffside viewpoint gazing directly up at the colossal vermilion-orange Art-Deco suspension towers and sweeping steel cables "
            "of the Golden Gate Bridge soaring through silvery Pacific marine layer fog above deep sapphire bay swells"
        ),
        focal_props=("brass scenic binoculars on post", "windbreaker hood strap", "canvas pack", "carved stone overlook wall"),
        wardrobe_cue="teal color-blocked windbreaker jacket over striped knit shirt, indigo denim jeans, and retro suede trainers",
        explicit_keywords=("golden gate", "bridge", "fog", "california", "bay"),
    ),
    CulturalWorld(
        id="en_landmark_cliffs_moher",
        title="Cliffs of Moher Atlantic Stone Overlook",
        region="County Clare, Ireland",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("coastal", "nature", "travel", "history"),
        setting_prompt=(
            "sheer dizzying dark-shale sea cliffs of Moher plunging 700 feet into foaming Atlantic rollers beneath sweeping sunlit emerald headlands "
            "and a historic stone watchtower silhouette rising along rugged flagstone trail"
        ),
        focal_props=("wooden ash walking stick", "woven Aran wool scarf", "weatherproof pack", "flagstone cliff wall"),
        wardrobe_cue="navy hooded waxed rain parka over cream fisherman cable-knit jumper, rugged olive trousers, and waterproof boots",
        explicit_keywords=("cliff", "cliffs", "atlantic", "ocean", "ireland", "nature", "coast"),
    ),
    CulturalWorld(
        id="en_landmark_banff_louise",
        title="Banff Lake Louise Glacial Peaks Boathouse",
        region="Banff (Alberta), Canada",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("nature", "travel", "coastal", "sports"),
        setting_prompt=(
            "glistening jade-turquoise waters of Lake Louise framed by a classic crimson-timber Canadian canoe boathouse, bright red cedar canoes gliding softly, "
            "and colossal snow-crowned Rocky Mountain glacier peaks rising steeply into crisp sapphire sky"
        ),
        focal_props=("lacquered cedar canoe paddle", "crimson canoe bow", "knit mountain toque", "timber dock deck"),
        wardrobe_cue="burgundy heritage flannel-lined field jacket over oatmeal Henley knit top, dark trail pants, and laced leather boots",
        explicit_keywords=("banff", "lake", "glacier", "canoe", "canada", "mountains", "peak"),
    ),
    CulturalWorld(
        id="en_landmark_sydney_opera",
        title="Sydney Opera Sails & Harbor Twilight",
        region="Sydney (New South Wales), Australia",
        category="landmark",
        indoor_outdoor="exterior",
        staging_tags=("monumental", "layered_depth", "tactile_props"),
        vibe_tags=("music", "culture", "travel", "coastal", "celebration"),
        setting_prompt=(
            "iconic Bennelong Point granite promenade looking straight up at the soaring sculptural white-and-cream ceramic-tiled geometric roof shells "
            "of the Sydney Opera House glowing warmly at sunset beside glistening indigo Pacific harbor waves"
        ),
        focal_props=("mother-of-pearl opera glasses", "brass promenade telescope", "sleek leather folder", "pink granite seawall"),
        wardrobe_cue="crisp sage-green linen blazer over ivory silk collar blouse or shirt, tailored charcoal trousers, and clean leather loafers",
        explicit_keywords=("opera", "sydney", "architecture", "theater", "theatre", "concert", "stage"),
    ),
)

ENGLISH_PROFILE = LanguageVisualProfile(
    language="english",
    lang_code="E",
    aliases=("en", "eng", "american", "british"),
    palette_mood=(
        "BRAND PALETTE MOOD (ENGLISH): Warm, vibrant, natural, cinematic.\n"
        "Key Accent Colors: Forest Green, Warm Ochre, Rich Amber, Slate Blue, Cream.\n"
    ),
    idiom_markers=(
        "idiom", "saying", "figurative", "slang", "proverb", "idiomatic expression",
        "piece of cake", "break a leg", "bite the bullet", "spill the beans",
        "under the weather", "cost an arm and a leg", "burn the midnight oil",
        "hit the nail on the head", "once in a blue moon", "barking up the wrong tree",
        "cold feet", "see eye to eye", "ball is in your court", "cross that bridge",
        "call it a day", "cut corners", "easy as pie", "drop in the ocean",
        "rule of thumb", "through the grapevine", "pull someone's leg",
        "actions speak louder", "beat around the bush", "blessing in disguise",
    ),
    idiom_environments=(
        (("piece of cake", "easy as pie"), "charming Notting Hill cream-and-mint Georgian patisserie tea parlor (featuring: marble pedestal display counter showcasing an elaborate towering multi-tier frosted cake with a single slice removed, arched sunny bay window)"),
        (("break a leg",), "historic London West End theater and performing arts stage (featuring: vintage star dressing room mirror, crimson velvet backstage curtains, grand wooden proscenium auditorium)"),
        (("spill the beans",), "vibrant Borough Market artisan kitchen counter and corner stall (featuring: rustic marble prep bar with oversized tipped ceramic jars spilling colorful heirloom beans, hanging copper pans)"),
        (("under the weather",), "cozy rain-misted Edinburgh cobblestone cottage porch overlooking the harbor (featuring: timber garden bench with warm tartan wool blanket, steaming stoneware tea mugs on wooden stool, golden lantern glow)"),
        (("burn the midnight oil",), "quiet late-evening Oxford collegiate oak library alcove (featuring: green-glass brass banker lamps glowing beside stained arched lancet windows, towering mahogany bookshelves, starry skyline)"),
        (("cost an arm and a leg",), "chic Mayfair luxury haute-couture boutique gallery (featuring: extravagant velvet display pedestals, gilt mirrors, marble counter, historic arcade)"),
    ),
    heteronym_domains=ENGLISH_HETERONYM_DOMAINS,
    cultural_cue=(
        "Global Anglophone cities, vinyl shops, harbor piers, historic arcades, markets, and landmarks "
        "across England, Scotland, Wales, Ireland, USA, Canada, Australia, New Zealand, Jamaica, South Africa, and Singapore"
    ),
    cultural_worlds=ENGLISH_CULTURAL_WORLDS,
)
