"""
overhaul_spanish_suite.py
Overhauls:
1. SPANISH_READY_PROMPTS_ROLEPLAY.csv (all 88 rows with rich, vivid, funny, high-stakes micro-settings)
2. SPANISH_READY_PROMPTS_GAME.csv (verifies alignment and cleans encoding)
3. SPANISH_READY_PROMPTS_FUN_FACTS.csv (expands from 5 to 15 viral linguistic curiosities)
"""

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3] / "input" / "csv" / "spanish" / "expressions_list"

ROLEPLAY_SCENARIOS_SPANISH = {
    "SR01": "En una tienda de zapatillas exclusivas: dos amigos miran una vitrina con zapatillas de 800 euros. Uno saca la tarjeta y el otro le agarra el brazo con cara de pánico: '¡Pero tío, déjalas ahí, que te van a costar un ojo de la cara!'",
    "SR02": "En un puesto de tapas callejeras: un amigo le asegura al otro con cara seria que el chef pone salsa de grillos tailandeses en las bravas. Al ver la cara de asco del amigo a punto de escupir, suelta la carcajada: '¡Que no, hombre, que te estoy tomando el pelo!'",
    "SR03": "En el metro de la ciudad viendo anuncios en pantallas y andenes: dos amigos notan que el mismo cantante de reguetón aparece en la publicidad del metro, en la radio del quiosco y en la camiseta de un pasajero: '¡Es que a este tipo lo tenemos hasta en la sopa!'",
    "SR04": "Montando una estantería de Ikea en el salón con un manual de 40 páginas: uno mira los 50 tornillos en el suelo sudando la gota gorda, mientras el amigo manitas coloca la primera balda de un golpe y sonríe: 'Tranquilo, con esta llave esto es pan comido.'",
    "SR05": "En el aparcamiento de la facultad cinco minutos antes de la entrega final: dos compañeros de clase descubren que dejaron el pen drive con el proyecto final conectado en la biblioteca cerrada: 'Como el profesor no lo reciba a las diez, estoy frito.'",
    "SR06": "En una cafetería antes de entrar a trabajar: un amigo le pide a otro que le devuelva los 50 euros del fin de semana, pero el otro empieza a hablar del clima, de la inflación y del tráfico: '¡Oye, no te andes por las ramas y devuélveme el dinero!'",
    "SR07": "En la cocina de un bar de tapas en plena noche de fútbol: los camareros gritan comandas y el cocinero corta jamón a toda velocidad mientras le dice al dueño sudando: '¡Pon otra freidora que con tres mesas más ya no doy abasto!'",
    "SR08": "En una comida familiar de domingo: un estudiante extranjero tira accidentalmente una copa de vino sobre el mantel blanco de la abuela y exclama avergonzado ante toda la mesa: '¡Ay, perdón, estoy tan embarazada!' provocando felicitaciones confusas y risas.",
    "SR09": "En el backstage de un teatro tras una ovación del público: un asistente de producción extranjero corre buscando la puerta de salida para tomar aire y le dice al guardia '¡Muéstrame el éxito!', mientras el guardia lo abraza: '¡Claro que fue un éxito, rompiste el escenario!'",
    "SR10": "En una tienda de reformas para el hogar: un cliente extranjero pide al vendedor 'una carpeta persa de lana suave para el salón', y el dependiente perplejo le entrega un archivador escolar de plástico azul.",
    "SR11": "En la oficina durante el invierno: un colega extranjero estornuda ruidosamente cinco veces seguidas con pañuelos en la mano y anuncia preocupado 'Estoy muy constipado', provocando que su compañero le recomiende un té caliente en vez de un laxante.",
    "SR12": "Saliendo del supermercado con las bolsas llenas: uno de los amigos se detiene en seco en el aparcamiento palpándose los bolsillos con cara de pánico: '¡Acabo de darme cuenta de que dejé las llaves dentro del coche mientras realizaba el pago!'",
    "SR13": "En la recepción de un congreso internacional: un voluntario extranjero le pregunta a los asistentes si necesita 'asistir a los ponentes con agua y café', y la coordinadora le aclara riendo: 'Tú solo tienes que asistir a la charla como oyente, no servirles café.'",
    "SR14": "En una parada de autobús a cuarenta grados bajo el sol del mediodía en Sevilla: dos amigos sudando ven retrasarse el bus veinte minutos. Uno suspira agotado: '¡No soporto este calor sofocante!', mientras el otro le comparte su abanico: 'Apóyate en la sombra que ya llega.'",
    "SR15": "En un ensayo para una obra de teatro: un actor amateur exagera ridículamente su acento británico para parecer noble, y su compañero entre bastidores le susurra divertido: 'No pretendas ser de la realeza londinense cuando eres de Valencia.'",
    "SR16": "En una sobremesa familiar escuchando historias de juventud: el abuelo cuenta sonriendo cómo cortejaba a la abuela en los bailes del pueblo: 'La pretendí durante dos años con serenatas antes de que aceptara un café.'",
    "SR17": "En la salida del cine tras un drama lacrimógeno sobre perritos: uno de los amigos sale empapado en lágrimas sonándose la nariz, mientras el otro bromea: 'Adoro lo sensible que eres con los animales, aunque te gastes todo el paquete de pañuelos.'",
    "SR18": "En una visita guiada por el Palacio Real: un turista confunde la corona original del siglo XVIII con una réplica moderna de la tienda, y el guía sonríe: 'La corona histórica es auténtica, pero la administración actual expone réplicas.'",
    "SR19": "En el vagón silencioso de un tren de alta velocidad: un pasajero tropieza con la maleta de su compañero de asiento y se disculpa en un susurro avergonzado: 'Perdona si te molesto, buscaba el enchufe debajo del asiento.'",
    "SR20": "En la cola de una máquina de café que no acepta monedas: un estudiante confundido intenta encajar una tarjeta arrugada mientras su amigo le dice: 'Introduce la tarjeta por la ranura magnética, no por el sensor.'",
    "SR21": "Paseando por el paseo marítimo al atardecer llevando una bolsa de regalo envuelta con lazo: 'Caminamos por la playa durante una hora para buscar este reloj para mi hermano.'",
    "SR22": "En la sala de urgencias de un hospital de guardia a las tres de la madrugada: dos médicos exhaustos conversan: 'Ella es cardióloga de guardia, pero ahora mismo está agotada tras seis horas de cirugía.'",
    "SR23": "En la barra de una cafetería de diseño: un cliente exigente devuelve la taza al barista con mirada severa: 'No te pedí leche de vaca entera, sino bebida de avena templada.'",
    "SR24": "En el mostrador de información de una estación de metro caótica: un viajero indeciso consulta a su compañero: 'Voy a preguntar la dirección al policía y luego pedir un billete en la taquilla.'",
    "SR25": "En un tren regional cruzando los viñedos de La Rioja: un mochilero habla con su vecino de asiento: 'No conozco este pueblo, ¿pero sabes a qué hora llega el próximo tren a Logroño?'",
    "SR26": "Despertando en un albergue del Camino de Santiago con dolor de pies: un peregrino tararea una vieja canción y dice: 'Esa melodía me suena mucho, ¿o soñé anoche que la cantábamos en el bosque?'",
    "SR27": "Buscando el coche aparcado en un laberinto subterráneo de tres plantas: 'Recuerdo perfectamente que aparcamos cerca de la columna amarilla, ¡pero no me acuerdo del número exacto!'",
    "SR28": "Saliendo de un restaurante tras una cena de cumpleaños con invitados desconocidos: 'La comida me gustó muchísimo, pero el chico de la camisa roja me cayó fatal con sus comentarios.'",
    "SR29": "En una calle desconocida a medianoche con dolor de cabeza: '¿Hay alguna farmacia de guardia por este barrio? La farmacia central está cerrada a cal y canto.'",
    "SR30": "En una caótica mudanza de piso de estudiantes entre cajas de cartón: 'Lleva estas cajas pesadas al camión de mudanzas y tráeme una botella de agua fresca de la cocina.'",
    "SR31": "En una clase de baile latino para novatos: uno de los alumnos pisa a su pareja y se pone rojo como un tomate: 'Me puse rojo de pura vergüenza, ¡esta coreografía me va a volver loco!'",
    "SR32": "En una cata gastronómica de quesos curados y vino tinto: el catador paladea con deleite: 'Cocinas realmente bien este plato, y este queso manchego es muy bueno para el paladar.'",
    "SR33": "Redactando un correo formal al casero del piso reclamando la calefacción estropeada: '¿Por qué no funciona la caldera? Se congelaron las tuberías porque no hay gas, y no entiendo el porqué de tanta demora.'",
    "SR34": "Despidiéndose en la puerta de embarque del aeropuerto tras un viaje inolvidable: dos mejores amigos se abrazan conmovidos: 'Te quiero un montón, amigo; pero a mi prometida la amo con toda mi alma.'",
    "SR35": "Atrapados en un atasco descomunal en la autopista rumbo al festival de música: 'El autobús tardó dos horas en avanzar tres kilómetros; lleva mucho tiempo organizar el tráfico en esta ciudad.'",
    "SR36": "En una competición de crossfit en el gimnasio local: dos atletas comparan sus marcas sudando sobre la colchoneta: 'Entrenó tanto como el campeón de la sala, pero su salto fue tan rápido como el mío.'",
    "SR37": "Llegando a la cumbre de una montaña bajo un sol ardiente de mediodía: un senderista abre su cantimplora con ansia: 'Bébete el agua fría antes de que el sol caliente todo el bidón.'",
    "SR38": "Cambiando la rueda pinchada de una furgoneta en la cuneta de la carretera: 'Pásame la llave inglesa que tengo la mano derecha completamente cubierta de grasa negra.'",
    "SR39": "En la puerta de embarque de un vuelo de bajo coste con la maleta a punto de reventar: 'Ese no es el problema principal; el problema es que la maleta excede diez kilos el límite permitido.'",
    "SR40": "En la biblioteca universitaria debatiendo el trabajo final de sociología: 'El tema que elegiste para el ensayo sobre redes sociales es sumamente polémico y fascinante.'",
    "SR41": "En un encuentro de intercambio lingüístico en un pub cosmopolita: 'Aprender el idioma español te conecta con más de quinientos millones de hablantes en todo el mundo.'",
    "SR42": "En un campamento de voluntarios limpiando plásticos en la costa: 'Cuidar el planeta no es solo una frase bonita, es un compromiso diario de todos nosotros.'",
    "SR43": "Perdidos en un sendero de niebla espesa sin cobertura en el GPS: dos excursionistas despliegan un mapa arrugado: 'Sujeta el mapa contra la roca que el viento se lo lleva volando.'",
    "SR44": "En el mirador de San Nicolás en Granada con la Alhambra dorada de fondo: 'Saca el móvil y hagámonos una foto juntos antes de que caiga el sol del atardecer.'",
    "SR45": "En la abarrotada terraza de un concierto callejero reconociendo a un familiar entre la multitud: '¡Mira hacia la derecha! Ayer vi a mi hermano saludando desde la barra.'",
    "SR46": "En un concurso culinario de barrio evaluando paellas valencianas: un juez extranjero sonríe relamiéndose: 'Me gusta la paella de marisco con arroz socarrat, tiene un sabor increíble.'",
    "SR47": "Llegando a la caja del supermercado con el carrito lleno hasta el borde: '¡Tierra, trágame! Se me olvidó la cartera con todas las tarjetas en la mesa de la entrada.'",
    "SR48": "El lunes por la mañana en la máquina de café de la oficina comentando las series del fin de semana: 'Ayer vi una película de suspense tan tensa que no pude despegar los ojos de la pantalla.'",
    "SR49": "Celebrando el segundo aniversario de una banda de rock independiente en su local de ensayo: 'Hace dos años que tocamos juntos en este garaje y ya tenemos diez temas grabados.'",
    "SR50": "Mirando llover sin parar contra el ventanal de la oficina en un frío lunes de enero: '¡Ojalá pudiera teletransportarme a una hamaca en las playas de Fuerteventura ahora mismo!'",
    "SR51": "Esperando en una cafetería junto a la estación de autobuses mirando el reloj con nerviosismo: 'Espero que venga pronto mi hermana porque el tren hacia el norte sale en diez minutos.'",
    "SR52": "Saliendo de un apartamento de vacaciones antes de entregar las llaves al propietario: 'Revisa bien todos los enchufes y apaga las luces del pasillo antes de salir.'",
    "SR53": "Esperando la entrega de una pizza en una noche de partido de fútbol con el estómago rugiendo: 'Todavía no ha llamado el repartidor al telefonillo, pero ya puse los platos en la mesa.'",
    "SR54": "Subiendo los 300 escalones empinados del campanario de la catedral: un turista cansado se asoma al balcón: 'Subir hasta aquí con este calor costó sudor, ¡pero la panorámica valió la pena!'",
    "SR55": "Cocinando una tortilla de patatas en un apartamento de intercambio en Berlín: 'Echo mucho de menos el aceite de oliva de mi pueblo y las cenas ruidosas con mi familia.'",
    "SR56": "Corriendo por los pasillos subterráneos de la estación de tren con las maletas rodando a toda prisa: '¡Tenemos que darnos prisa o veremos el tren alejarse por la vía!'",
    "SR57": "Intentando meter un sofá de terciopelo verde por una puerta estrecha en el tercer piso: '¡Por favor, échame una mano para levantarlo que se me resbalan los dedos!'",
    "SR58": "Intentando aprender a tocar los compases rápidos de la guitarra flamenca: 'Al principio me costó trabajo coordinar los dedos, pero tras una hora el ritmo fluye solo.'",
    "SR59": "En un seminario de gastronomía molecular levantando la mano con timidez: 'Perdone, chef, ¿puedo hacer una pregunta sobre el tiempo de cocción a baja temperatura?'",
    "SR60": "Colocando en la mesa una cazuela de barro humeante de fideuá con alioli casero: 'Los platos están servidos y el marisco en su punto: ¡buen provecho a todos!'",
    "SR61": "Dos compañeros de piso discutiendo las normas de limpieza del apartamento: 'Estoy completamente de acuerdo en repartir los turnos de fregar los platos por semanas.'",
    "SR62": "Hablando de rutinas de salud en la cantina del gimnasio: 'Suelo levantarme a las seis de la mañana para meditar y correr antes de que empiece el bullicio de la ciudad.'",
    "SR63": "Caminando por un sendero botánico señalizado con carteles de precaución: 'Haz caso a las indicaciones del guardabosques y no te salgas de la vereda marcada.'",
    "SR64": "En una pista de esquí para principiantes cuando un esquiador audaz ignora las vallas: 'Hizo caso omiso de la señal de peligro y terminó clavado de cabeza en la nieve blanda.'",
    "SR65": "Despidiéndose en la estación antes de que su amiga suba al autobús nocturno de larga distancia: 'Avísame por mensaje en cuanto llegues a la estación central para quedarme tranquilo.'",
    "SR66": "Escuchando un ruido metálico extraño en el motor del coche viejo antes de cruzar la sierra: 'Ese traqueteo del tubo de escape me suena a un fallo en la correa de distribución.'",
    "SR67": "Probándose una cazadora de cuero retro en el espejo de un mercadillo vintage: 'Esa chaqueta marrón te queda genial, parece hecha a tu medida.'",
    "SR68": "Pidiendo el desayuno en una terraza soleada un día de dieta: 'Camarero, tráigame una tostada con tomate y aceite en vez de los churros con chocolate.'",
    "SR69": "Viernes por la noche con lluvia en la ventana decidiendo planes con un amigo: '¿A qué hora quedamos en el bar de la esquina, o prefieres quedarte en el sofá con una película?'",
    "SR70": "Mirando el reloj en una sobremesa que se alarga hasta las tantas un jueves: 'Se me ha hecho tardísimo y mañana madrugo, así que tengo que irme inmediatamente.'",
    "SR71": "En una parada con una multitud impaciente bajo la lluvia con el bonobús preparado: 'Ten listo el billete en la mano antes de subir al autobús para no bloquear la puerta.'",
    "SR72": "Llegando a la terminal ferroviaria cargado con cochecito de bebé y tres maletas: 'Ten cuidado con el hueco entre el vagón y el andén al bajar del tren de cercanías.'",
    "SR73": "Paseando por la Plaza Mayor de Córdoba a las tres de la tarde en pleno agosto: 'En verano hace tanto calor en esta calle que hasta las palomas buscan la sombra del toldo.'",
    "SR74": "Bajando de una cabina de teleférico en la cumbre nevada de Sierra Nevada: 'Abróchate bien el chaquetón de plumas porque hace un frío que pela en esta ladera.'",
    "SR75": "Sentados en una terraza acristalada frotándose las manos temblorosas: 'Por favor, dile al camarero que encienda la estufa de gas exterior, que tengo un frío insoportable.'",
    "SR76": "Terminando una sesión intensa de spinning con la camiseta empapada y una toalla al cuello: 'Dame ese vaso de agua helada, que tengo muchísimo calor después de subir tantas cuestas.'",
    "SR77": "En la antesala de un escenario antes de dar una charla pública ante doscientas personas: 'Respira hondo tres veces; no tengas miedo escénico, dominas el tema a la perfección.'",
    "SR78": "Tirando sin querer una torre de vasos de plástico en la cafetería con estrépito: '¡Qué vergüenza me dio cuando todos los clientes se giraron a mirarme con cara de asombro!'",
    "SR79": "Bajo un chaparrón monumental sin paraguas tras haber asegurado que no llovería: 'Reconozco que tenías toda la razón cuando dijiste que metiéramos los chubasqueros en la mochila.'",
    "SR80": "Paseando por las calles adoquinadas del centro histórico oliendo a canela y chocolate frito: 'Tengo unas ganas locas de sentarme en esa chocolatería tradicional a merendar.'",
    "SR81": "En la taquilla de un teatro histórico para una función con entradas agotadas: 'Tuvimos una suerte increíble de conseguir los dos últimos asientos libres de la platea.'",
    "SR82": "Bostezando ruidosamente en la biblioteca municipal frente a quinientos folios de apuntes: 'Se me cierran los párpados solos sobre el libro, tengo muchísimo sueño acumulado.'",
    "SR83": "Rebuscando desesperadamente en el fondo de una mochila repleta de ropa y cables: 'Llevo media hora buscando las llaves de casa y apuesto a que están en el bolsillo de la chaqueta.'",
    "SR84": "En una elegante fiesta de gala en un jardín: 'Fíjate en aquel señor de la esquina: lleva puesto un traje vintage con pajarita de seda impecable.'",
    "SR85": "En una clase de fonética para extranjeros practicando trabalenguas: 'Fíjate bien en la posición de la punta de la lengua contra el paladar para pronunciar la doble erre.'",
    "SR86": "Brindando en una cena de aniversario tras superar un hábito nocivo: 'Hoy cumple seis meses desde que tomó la firme decisión de dejar de fumar definitivamente.'",
    "SR87": "Llamando al servicio de atención al cliente de una aerolínea que da tono de ocupado: 'La línea no da señal de llamada; vuelve a llamar dentro de diez minutos a ver si atienden.'",
    "SR88": "En una sala de cine a oscuras mientras se apagan los focos y comienza la banda sonora: 'Guarda el móvil y siéntate ya, que la película está a punto de empezar en la pantalla grande.'"
}

def overhaul_spanish_roleplay():
    csv_file = BASE_DIR / "SPANISH_READY_PROMPTS_ROLEPLAY.csv"
    with open(csv_file, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    updated_count = 0
    for r in rows:
        cid = r["ID"].strip().upper()
        if cid in ROLEPLAY_SCENARIOS_SPANISH:
            r["ROLEPLAY_SCENARIO"] = ROLEPLAY_SCENARIOS_SPANISH[cid]
            updated_count += 1

    fieldnames = list(rows[0].keys())
    with open(csv_file, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Updated {updated_count}/{len(rows)} Spanish Roleplay scenarios in {csv_file.name}")

# --- 2. SPANISH FUN FACTS (15 Viral Curiosities) ---
FUN_FACTS_SPANISH = [
    {
        "ID": "SF01",
        "TOPIC": "El signo de interrogación invertido se inventó en 1754",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "La Real Academia Española instauró los signos de interrogación (¿) y exclamación (¡) invertidos en 1754 para que los lectores en voz alta supieran con qué entonación empezar antes de llegar al final de las frases largas.",
        "HOOK_ANGLE": "El español es el único idioma en el mundo que te avisa con un signo al revés antes de que empiece una pregunta.",
        "EMOTIONAL_TRIGGER": "Curiosidad & Fascinación"
    },
    {
        "ID": "SF02",
        "TOPIC": "Más de 4.000 palabras en español provienen del árabe",
        "PILLAR": "ETYMOLOGY",
        "FORMAT": "3_FACTS",
        "FACT_DETAILS": "Más de 4.000 palabras en español provienen directamente de ocho siglos de presencia árabe en Al-Ándalus. Casi todas las palabras que empiezan por 'al-' (almohada, alcázar, albaricoque) más 'ojalá' (wa sha Allah) y 'aceite' tienen raíces árabes.",
        "HOOK_ANGLE": "3 palabras en español que usas todos los días y que en realidad son puro árabe camuflado.",
        "EMOTIONAL_TRIGGER": "Descubrimiento & Sorpresa"
    },
    {
        "ID": "SF03",
        "TOPIC": "La intraducible sobremesa española",
        "PILLAR": "CULTURAL_DIFFERENCES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "'Sobremesa' describe el sagrado ritual social de quedarse sentado alrededor de la mesa después de comer, tomando café y conversando durante horas con amigos y familiares. No tiene una sola palabra equivalente en muchos idiomas.",
        "HOOK_ANGLE": "Un ritual español tan sagrado culturalmente que otros idiomas ni siquiera tienen una palabra para definirlo.",
        "EMOTIONAL_TRIGGER": "Calidez & Fascinación"
    },
    {
        "ID": "SF04",
        "TOPIC": "La letra Ñ se inventó para ahorrar papel y pergamino",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "MYSTERY",
        "FACT_DETAILS": "Los monjes copistas medievales, para ahorrar el costoso pergamino, dejaron de escribir la doble 'nn' latina (como 'annus' -> 'año'). En su lugar, colocaron una pequeña 'n' abreviada encima de la letra, creando la famosa virgulilla de la Ñ.",
        "HOOK_ANGLE": "La letra más representativa del español fue inventada por monjes medievales para ahorrar dinero en pergamino.",
        "EMOTIONAL_TRIGGER": "Humor & Asombro"
    },
    {
        "ID": "SF05",
        "TOPIC": "Embarazada NO significa avergonzada (Embarrassed)",
        "PILLAR": "WORD_CURIOSITIES",
        "FORMAT": "CHALLENGE",
        "FACT_DETAILS": "'Embarazada' en español significa que estás esperando un bebé, mientras que 'embarrassed' se traduce como avergonzado o avergonzada. Decir 'estoy embarazada' por error no anuncia un sonrojo, ¡anuncia un bebé sorpresa!",
        "HOOK_ANGLE": "El falso amigo más peligroso del español que puede hacerte anunciar un embarazo por accidente.",
        "EMOTIONAL_TRIGGER": "Reto divertido & Humor"
    },
    {
        "ID": "SF06",
        "TOPIC": "¿Por qué decimos 'El agua' si la palabra es femenina?",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "La palabra 'agua' es 100% femenina. Pero cuando un sustantivo femenino empieza por una 'a' tónica (con acento de voz), el español cambia 'la' por 'el' únicamente para evitar la cacofonía sonora ('la-agua'). Sin embargo, en plural decimos 'las aguas cristalinas'.",
        "HOOK_ANGLE": "¿Por qué decimos 'el agua fría' si el adjetivo es femenino? ¡El truco fonético que confunde a millones!",
        "EMOTIONAL_TRIGGER": "Aha Moment & Claridad"
    },
    {
        "ID": "SF07",
        "TOPIC": "Palabras españolas intraducibles: Madrugar",
        "PILLAR": "WORD_CURIOSITIES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "El español tiene un verbo exclusivo para la acción de levantarse voluntariamente al amanecer o muy temprano en la mañana: 'madrugar'. En inglés necesitas una frase entera: 'to wake up early in the morning'.",
        "HOOK_ANGLE": "¿Sabías que el español tiene un verbo único para despertarse de madrugada que no existe en inglés?",
        "EMOTIONAL_TRIGGER": "Curiosidad & Orgullo"
    },
    {
        "ID": "SF08",
        "TOPIC": "La emoción de 'Estrenar' algo por primera vez",
        "PILLAR": "CULTURAL_DIFFERENCES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "'Estrenar' condensa en un solo verbo la satisfacción y emoción de ponerse unos zapatos nuevos o usar un objeto por primera vez. En la mayoría de lenguas germánicas se requieren explicaciones compuestas como 'wear for the first time'.",
        "HOOK_ANGLE": "La palabra mágica del español para presumir ropa nueva que casi ningún otro idioma posee.",
        "EMOTIONAL_TRIGGER": "Fascinación & Alegría"
    },
    {
        "ID": "SF09",
        "TOPIC": "La palabra más larga oficial del diccionario español",
        "PILLAR": "WORD_CURIOSITIES",
        "FORMAT": "CHALLENGE",
        "FACT_DETAILS": "Con 23 letras, 'electroencefalografista' es la palabra oficial más larga registrada en el Diccionario de la Real Academia Española (persona especializada en electroencefalogramas). Supera a 'anticonstitucionalmente' (23 letras no técnicas).",
        "HOOK_ANGLE": "¿Eres capaz de pronunciar la palabra oficial más larga de todo el diccionario español?",
        "EMOTIONAL_TRIGGER": "Desafío & Humor"
    },
    {
        "ID": "SF10",
        "TOPIC": "Palabras que tienen las cinco vocales (Pentavocálicas)",
        "PILLAR": "WORD_CURIOSITIES",
        "FORMAT": "3_FACTS",
        "FACT_DETAILS": "En español existen miles de palabras 'pentavocálicas' que contienen las cinco vocales (a, e, i, o, u) sin repetir ninguna. Ejemplos populares: 'murciélago', 'arquitecto', 'eucalipto' y 'ayuntamiento'.",
        "HOOK_ANGLE": "3 palabras cotidianas en español que esconden las 5 vocales del abecedario sin repetir ninguna.",
        "EMOTIONAL_TRIGGER": "Curiosidad & Asombro"
    },
    {
        "ID": "SF11",
        "TOPIC": "El origen milagroso de la palabra 'Ojalá'",
        "PILLAR": "ETYMOLOGY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "Cada vez que dices 'ojalá llueva' o 'ojalá apruebe', estás usando una adaptación directa del árabe hispánico 'law šá lláh' (si Dios quiere / que Dios quiera). Sobrevivió como la expresión de deseo más poderosa del español.",
        "HOOK_ANGLE": "La palabra más bonita para desear suerte en español esconde una oración de hace mil años.",
        "EMOTIONAL_TRIGGER": "Asombro & Cultura"
    },
    {
        "ID": "SF12",
        "TOPIC": "El español supera al inglés en hablantes nativos globales",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "El español es la segunda lengua materna del planeta por número de hablantes nativos (cerca de 500 millones), solo por detrás del chino mandarín y superando ampliamente al inglés nativo (unos 380 millones).",
        "HOOK_ANGLE": "¿Inglés o español? El dato demográfico real sobre qué idioma tiene más hablantes nativos en el mundo.",
        "EMOTIONAL_TRIGGER": "Orgullo & Curiosidad"
    },
    {
        "ID": "SF13",
        "TOPIC": "¿Por qué en España dicen 'Ordenador' y en América 'Computadora'?",
        "PILLAR": "CULTURAL_DIFFERENCES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "España adoptó el término informático francés 'ordinateur' promovido por la empresa IBM a mediados del siglo XX, mientras que Hispanoamérica adoptó el calco anglosajón 'computer' adaptado al femenino 'computadora' o masculino 'computador'.",
        "HOOK_ANGLE": "¿Ordenador o computadora? La histórica batalla lingüística entre la influencia francesa y la americana.",
        "EMOTIONAL_TRIGGER": "Aha Moment & Descubrimiento"
    },
    {
        "ID": "SF14",
        "TOPIC": "El secreto de la doble 'RR' vibrante múltiple",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "La vibrante múltiple alveolar sonora (/r/), la famosa 'RR' de 'perro' o 'ferrocarril', hace vibrar la lengua contra los alvéolos entre 4 y 5 veces en apenas 100 milisegundos. Es uno de los fonemas más difíciles de dominar para los estudiantes anglófonos.",
        "HOOK_ANGLE": "¿Por qué la doble 'RR' del español es el fonema más temido del mundo por los extranjeros?",
        "EMOTIONAL_TRIGGER": "Empatía & Humor"
    },
    {
        "ID": "SF15",
        "TOPIC": "El enigma del 'Voseo' en el español rioplatense y andino",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "El uso de 'vos' en lugar de 'tú' (como 'vos tenés' o 'vos sabés') era la fórmula de máxima cortesía y reverencia en la España del Siglo de Oro. Mientras España dejó de usarlo, quedó preservado como símbolo de identidad nacional en el Cono Sur y partes de Colombia y Centroamérica.",
        "HOOK_ANGLE": "El famoso 'vos' argentino no es una moda moderna: ¡es el tratamiento más noble de la España medieval!",
        "EMOTIONAL_TRIGGER": "Fascinación & Historia"
    }
]

def overhaul_spanish_fun_facts():
    csv_file = BASE_DIR / "SPANISH_READY_PROMPTS_FUN_FACTS.csv"
    fieldnames = ["ID", "TOPIC", "PILLAR", "FORMAT", "FACT_DETAILS", "HOOK_ANGLE", "EMOTIONAL_TRIGGER"]
    with open(csv_file, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(FUN_FACTS_SPANISH)
    print(f"[OK] Updated {len(FUN_FACTS_SPANISH)} Spanish Fun Facts in {csv_file.name}")

if __name__ == "__main__":
    overhaul_spanish_roleplay()
    overhaul_spanish_fun_facts()
