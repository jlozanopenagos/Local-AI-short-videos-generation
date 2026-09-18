"""
overhaul_italian_suite.py
Overhauls:
1. ITALIAN_READY_PROMPTS_ROLEPLAY.csv (all 96 rows with rich, varied, funny, high-stakes micro-settings)
2. ITALIAN_READY_PROMPTS_GAME.csv (verifies alignment and cleans encoding)
3. ITALIAN_READY_PROMPTS_FUN_FACTS.csv (expands from 5 to 15 viral linguistic curiosities)
"""

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3] / "input" / "csv" / "italian" / "expressions_list"

ROLEPLAY_SCENARIOS_ITALIAN = {
    "IR01": "Davanti all'aula d'esame universitario prima dell'orale decisivo: due studenti tesissimi ripassano gli appunti che tremano nelle mani. Uno fa un respiro profondo e l'amica gli stringe le spalle con energia: 'Forza, in bocca al lupo! E guai a te se rispondi grazie!'",
    "IR02": "All'uscita da un centro commerciale a Milano: uno mostra fiero quattro borse piene di vestiti e scarpe appena comprati, mentre l'amico controlla lo scontrino disperato: 'Ma come fai a finire lo stipendio il primo del mese? Hai proprio le mani bucate!'",
    "IR03": "Davanti al portone dell'ufficio prima di chiedere un aumento al capo severo: un collega trema e vorrebbe scappare a prendere un altro caffè, ma l'altro lo spinge verso l'ascensore: 'Basta rimandare da tre mesi, entra e prendi il toro per le corna!'",
    "IR04": "In cucina alle nove di sera con gli amici che bussano alla porta affamati: uno va nel panico perché il frigo è vuoto, mentre l'altro tira fuori aglio, olio e peperoncino: 'Stai calmo, butto giù gli spaghetti e ti risolvo la cena in quattro e quattr'otto!'",
    "IR05": "Davanti al cancello VIP di un concerto sold-out: due fan senza biglietto vedono un varco secondario semi-aperto con un addetto distratto. Uno esita preoccupato, ma l'altro gli fa l'occhiolino: 'Al massimo ci dicono di no: tentar non nuoce!'",
    "IR06": "Sotto un acquazzone improvviso senza ombrello e con il telefono scarico: un amico si ripara sotto un cornicione bagnato quando all'improvviso si ferma l'auto dell'altro che abbassa il finestrino: 'Sali al volo! Direi che sono capitato a fagiolo!'",
    "IR07": "Al cenone di Capodanno in una trattoria tipica a Roma: un turista alza il calice di prosecco gridando a tutto il ristorante 'Buon ano a tutti!', facendo soffocare dal ridere i camerieri prima che l'amico gli chiarisca la differenza della doppia 'n'.",
    "IR08": "In una sessione di studio per un progetto universitario: uno studente si vanta di aver completato tutta la presentazione ma dice 'È il mio fato!', e l'amico scoppia a ridere: 'Il tuo fato è il destino, io ti ho chiesto se il lavoro l'hai FATTO con due t!'",
    "IR09": "Durante l'organizzazione della cena di Natale: un compagno di stanza anglofono dice preoccupato 'A cena avrò solo due parenti, mia madre e mio padre!', e l'amico italiano ride divertito: 'Due parenti? Quelli sono i genitori! I parenti sono i venti cugini e zii che stanno arrivando!'",
    "IR10": "In una boutique di abbigliamento a Milano provando una sciarpa: un cliente straniero tocca il cashmere ed esclama 'Questo tessuto è così morboso!', e il commesso sobbalza prima che l'amico chiarisca: 'Morboso è macabro, questa sciarpa è morbidissima!'",
    "IR11": "Alla reception di un hotel di lusso a Firenze: un turista mostra la sua reflex al receptionist chiedendo 'Dov'è la mia camera?', e il receptionist perplesso gli indica la stanza al terzo piano: 'Questa è la macchina fotografica, la camera è la stanza con letto!'",
    "IR12": "In centro città cercando un posto per studiare: uno studente straniero entra in una libreria chiedendo di prendere in prestito tre libri gratis per un mese, e il libraio gli sorride divertito: 'Qui si comprano i libri, per il prestito devi andare in biblioteca!'",
    "IR13": "In un'edicola alla stazione ferroviaria: un viaggiatore chiede 'Avete l'ultimo magazzino di moda?', e l'edicolante indica i binari merci prima che l'amico intervenga: 'I magazzini sono i depositi, per le riviste devi chiedere la rivista!'",
    "IR14": "In una gelateria in pieno agosto a Napoli: un turista straniero tremante sotto il condizionatore chiede 'Un cono gelato molto caldo per favore', lasciando il gelataio pietrificato con la paletta in mano prima che l'amico corregga la traduzione.",
    "IR15": "Durante un weekend in campagna in Toscana: due amici vedono un cartello che indica una fattoria didattica. Uno esclama stupito 'Ma costruiscono automobili in mezzo alle colline?', e l'altro ride: 'Non è una factory o una fabbrica, è un'azienda agricola con gli animali!'",
    "IR16": "Durante una riunione di redazione per una rivista d'arte contemporanea: due giornalisti discutono animatamente: 'Un confronto leale tra colleghi stimola nuove idee, non è affatto uno scontro personale!'",
    "IR17": "Al bancone dell'accettazione di uno studio medico dentistico: l'assistente sorride al paziente in sala d'attesa: 'Attualmente il dottore sta terminando una visita urgente, vi farà accomodare tra due minuti.'",
    "IR18": "Firmando il contratto di locazione per un appartamento universitario a Bologna: 'Segnalateci tempestivamente via email ogni eventuale anomalia o guasto alla caldaia.'",
    "IR19": "Ammirando una fotografia di Piazza San Marco su una rivista di viaggi: 'Amo profondamente Venezia e ci vado ogni autunno prima della stagione dell'acqua alta.'",
    "IR20": "Al mercato rionale di Campo de' Fiori davanti a una cassetta di arance siciliane profumate: 'Queste arance sono freschissime e dolci, ne prendo volentieri due chili per le spremute!'",
    "IR21": "Incontrando per caso un caro compagno di liceo davanti a un caffè storico: 'Ciao Marco! Come stai? Sto benissimo, sono a Roma solo per qualche giorno di vacanza.'",
    "IR22": "Davanti alla vetrina illuminata di una storica pasticceria napoletana: 'Mi piace molto la torta caprese, ma mi piacciono ancora di più le sfogliatelle ricce calde!'",
    "IR23": "Mostrando una vecchia fotografia in bianco e nero conservata nel portafoglio: 'Mia madre insegnava lettere classiche al liceo prima di trasferirsi in campagna.'",
    "IR24": "Durante il brindisi della domenica a tavola riuniti con tutti i parenti: 'La mia famiglia si ritrova sempre in questa cascina per festeggiare insieme la vendemmia.'",
    "IR25": "Il lunedì mattina davanti alla macchinetta del caffè raccontando il fine settimana: 'Ieri sera sono andato a teatro alla Scala con Giulia per assistere alla prima dell'opera.'",
    "IR26": "Uscendo sazi e sorridenti da una verace pizzeria nei vicoli di Spaccanapoli: 'Ho mangiato una pizza margherita con mozzarella di bufala davvero indimenticabile!'",
    "IR27": "Cercando una storica bottega di liuteria nei vicoli rinascimentali: 'Sai a che ora chiude il laboratorio e conosci personalmente il maestro artigiano?'",
    "IR28": "Controllando i tabelloni luminosi alla stazione Centrale di Milano: 'Stasera esco con gli amici a bere un aperitivo sui Navigli, ma domattina parto presto per Torino in treno.'",
    "IR29": "Assaggiando le specialità gastronomiche a una sagra toscana sulle colline: 'Quel borgo medievale arroccato è bellissimo, e questo piatto di pici al ragù è davvero squisito.'",
    "IR30": "Aspettando che il risotto ai funghi porcini si raffreddi sul piatto: 'Questo risotto è molto profumato e cremoso, ma scotta troppo: aspetta un istante prima di assaggiare.'",
    "IR31": "Organizzando una gita fuori porta domenicale sui laghi lombardi: 'Ci vogliono due ore di macchina per arrivare a Bellagio, ma io ci metto solo dieci minuti a prepararmi lo zaino.'",
    "IR32": "Cucinando la cena in un accogliente appartamento ascoltando un radiodramma: 'Mentre cucinavo le tagliatelle al tartufo, durante la telefonata con papà è suonato il campanello.'",
    "IR33": "Sotto la tettoia della stazione durante un violento nubifragio con tuoni: 'Il treno regionale è bloccato a causa del nubifragio, ma grazie alla sala d'aspetto aspettiamo al coperto.'",
    "IR34": "Decidendo l'itinerario nel centro storico pedonale a traffico limitato: 'Quando il tempo è bello andiamo volentieri a piedi; muoversi in macchina nei vicoli è una follia.'",
    "IR35": "Con le borse di tela intrecciata al mercato ortofrutticolo del sabato mattina: 'Vado al mercato rionale presto per fare la spesa di frutta di stagione e formaggi freschi.'",
    "IR36": "Sulla carrozza panoramica di un treno ad alta velocità che attraversa gli Appennini: 'Viaggiare in treno è comodo e rilassante, ti godi il paesaggio senza stress da traffico.'",
    "IR37": "Davanti al motore aperto di una vecchia Vespa che non vuole saperne di ripartire: 'Non è un problema di benzina: dobbiamo esaminare a fondo questo problema all'accensione.'",
    "IR38": "Nell'aula magna universitaria durante l'apertura del simposio accademico: 'Il tema principale della conferenza di oggi è la transizione energetica sostenibile.'",
    "IR39": "Fuori da una sala cinematografica d'essai tra locandine d'epoca: 'Amiamo il cinema d'autore italiano del dopoguerra, da Visconti a Pasolini.'",
    "IR40": "Sul ponte di Castel Sant'Angelo a Roma con il Tevere dorato al tramonto: 'Tieni fermo il cellulare e scattami una foto ricordo splendida con la basilica sullo sfondo.'",
    "IR41": "Sollevando una pesante valigia di cuoio sul portabagagli dell'auto: 'Tiene saldamente la valigia con la mano destra e solleva con forza senza piegare la schiena.'",
    "IR42": "Spalancando le imposte di legno su un balcone affacciato sul golfo di Napoli: 'Oggi è un giorno luminoso e sereno, perfetto per fare una gita in barca a Capri.'",
    "IR43": "Passeggiando per i vicoli silenziosi e suggestivi di Trastevere a mezzanotte: 'Durante la notte le vie della città vecchia diventano magiche e piene di fascino.'",
    "IR44": "Sul marciapiede del binario ferroviario mentre l'altoparlante annuncia la partenza: 'Controlla di avere il biglietto convalidato prima di salire sul treno regionale.'",
    "IR45": "Scendendo da un autobus urbano affollato durante l'orario di punta: 'Attento al gradino e fai attenzione alla borsa quando scendi dall'autobus in piazza.'",
    "IR46": "Seduti al tavolino di un bar con una granita al limone in mano: 'Penso spesso alle prossime vacanze al mare; e tu, cosa pensi della nuova collega di lavoro?'",
    "IR47": "In un accogliente borgo medievale dell'Umbria accolti con pane e olio nuovo: 'In questo piccolo borgo la gente è straordinariamente accogliente e calorosa con i viaggiatori.'",
    "IR48": "Al colloquio di lavoro quando il titolare dell'azienda invita all'informalità: 'Tra colleghi in ufficio possiamo darci del tu, ma davanti ai clienti formali preferisco dare del lei.'",
    "IR49": "Durante una videochiamata dall'estero con la famiglia la domenica sera: 'Quando sono lontano dall'Italia mi manca tantissimo il profumo della cucina casalinga.'",
    "IR50": "Passeggiando sul lungomare quando improvvisamente il cielo si tinge di grigio scuro: 'Raccogliamo i teli e affrettiamoci verso il bar: prendi l'impermeabile perché sta per piovere!'",
    "IR51": "Sulla porta di casa prima di partire per un lungo fine settimana fuori porta: 'Ricordati di controllare le finestre e chiudi bene il gas prima di uscire di casa.'",
    "IR52": "Ringraziando calorosamente il vicino di casa per aver annaffiato le piante: 'Grazie mille per la gentilezza e l'aiuto! — Ma figurati, ci mancherebbe altro, è stato un piacere!'",
    "IR53": "Quando un amico si scusa mortificato per essere arrivato con cinque minuti di ritardo: 'Scusami tanto per l'attesa! — Ma figurati, non c'è assolutamente di che, ero appena arrivato!'",
    "IR54": "Strappando l'ultima pagina del calendario alla vigilia delle vacanze estive: 'Ho fatto le valigie e spento il computer: non vedo l'ora di partire per le meritate ferie al mare!'",
    "IR55": "In cima alla ripida scalinata del campanile panoramico ammirando i tetti della città: 'La salita a gradini è stata faticosa, ma la vista mozzafiato dall'alto vale davvero la pena.'",
    "IR56": "Portando una scatola di pasticcini freschi la domenica mattina: 'Oggi andrò a trovare i miei nonni in campagna per trascorrere il pomeriggio insieme.'",
    "IR57": "Tentando di spostare un pesante divano in velluto attraverso un corridoio stretto: 'Per favore, potresti darmi una mano ad afferrare questo angolo prima che scivoli a terra?'",
    "IR58": "Passeggiando per le vie eleganti del centro prima di andare a cena: 'Diamo un'occhiata alle vetrine illuminate dei negozi del centro prima di sederci al tavolo.'",
    "IR59": "Al tavolo di lavoro quando un collega fa una battuta involontariamente goffa: 'Ha fatto finta di niente con grande tatto per non creare tensioni e ha cambiato argomento.'",
    "IR60": "Tagliando il traguardo di una dura escursione di trekking sulle cime alpine: 'La salita tra le rocce era ripida ed estenuante, ma con grinta e tenacia ce l'abbiamo fatta!'",
    "IR61": "Raccontando l'esperienza di convivenza in uno studentato universitario: 'Abbiamo caratteri diversi, ma vado incredibilmente d'accordo con tutti i miei compagni di corso.'",
    "IR62": "Durante una riunione societaria decisiva per il lancio del nuovo prodotto: 'I tempi di consegna sono strettissimi, è arrivato il momento di prendere una decisione definitiva.'",
    "IR63": "Sul vagone silenzioso di un treno ad alta velocità quando squilla un telefono: 'Quel tono di suoneria continuo e acuto dà molto fastidio a tutti i passeggeri che riposano.'",
    "IR64": "Rientrando a casa sudati e impolverati dopo dieci chilometri di corsa campestre: 'Bevo un bicchiere d'acqua, faccio una doccia calda e mi rilasso finalmente sul divano.'",
    "IR65": "Al bancone di un bar all'angolo nelle prime ore del mattino: 'Al mattino per iniziare bene la giornata preferisco fare colazione con un cappuccino schiumoso e un cornetto.'",
    "IR66": "Alla fine di una conferenza scientifica alzando la mano dal fondo della sala: 'Scusi professore, posso fare una domanda rapida per chiarire l'ultimo grafico mostrato?'",
    "IR67": "A una festa tra amici presentandosi con un sorriso caloroso: 'Ciao a tutti, sono Francesca, è un vero piacere sincero di fare la vostra conoscenza!'",
    "IR68": "Dopo quattro ore di pagaia in kayak sul lago al tramonto: 'I nostri stomaci reclamano cibo: dopo questa remata abbiamo una fame da lupi!'",
    "IR69": "Al termine di una combattuta partita di calcetto tra amici: 'Passami subito quella bottiglia d'acqua fresca, ho una sete incredibile dopo aver corso per un'ora.'",
    "IR70": "Alla fermata del tram mentre soffia una tramontana gelida a dicembre: 'Allaccia bene la sciarpa e mettiti il cappotto pesante se hai freddo alle orecchie.'",
    "IR71": "Entrando in una stanza chiusa sotto il sole cocente di luglio: 'Accendiamo subito l'aria condizionata perché in questa stanza esposta a sud fa troppo caldo.'",
    "IR72": "Sbadigliando sul divano mentre scorrono i titoli di testa del film serale: 'Ieri sera sono crollato a letto prestissimo perché avevo un sonno arretrato insostenibile.'",
    "IR73": "Incoraggiando un allievo alla sua prima lezione di guida o di sci: 'Respira piano e mantieni la concentrazione: non devi avere alcuna paura di sbagliare all'inizio.'",
    "IR74": "Controllando i conti della spesa comune dopo aver verificato gli scontrini: 'Ho rifatto la somma delle spese e ti confermo che avevi perfettamente ragione tu fin dal principio.'",
    "IR75": "Davanti alla mappa constatando di aver imboccato l'uscita autostradale sbagliata: 'Guardando il cartello ha ammesso senza esitazione di avere avuto torto sulla direzione.'",
    "IR76": "Guardando l'orologio correndo verso i binari della metropolitana: 'Scusami se scappo via senza fermarmi, ma ho molta fretta perché la coincidenza parte tra tre minuti.'",
    "IR77": "Chiudendo lo schermo del computer portatile dopo dieci ore ininterrotte: 'Spengo tutto: ho davvero un bisogno assoluto di una passeggiata all'aria aperta e di silenzio.'",
    "IR78": "Trovando un posto auto gratuito proprio davanti all'ingresso del teatro: 'In pieno sabato sera a teatro abbiamo avuto la straordinaria fortuna di trovare l'ultimo posto libero.'",
    "IR79": "In una fredda serata autunnale guardando la pioggia sui vetri: 'Stasera ho proprio voglia di gustare una pizza margherita fumante con un bicchiere di buon vino rosso.'",
    "IR80": "Pianificando le attività del tempo libero per la stagione autunnale: 'Questo mese ho la ferma intenzione di iscrivermi a un corso intensivo di chitarra acustica.'",
    "IR81": "Festeggiando il secondo anniversario di lavoro nella bottega artigiana: 'Studio e sperimento le tecniche del restauro del legno antico con dedizione da due anni.'",
    "IR82": "Quando la serata volge al termine e gli ospiti salutano i padroni di casa: 'È mezzanotte passata e domattina la sveglia suona presto, è proprio l'ora di andare via.'",
    "IR83": "Prima di alzarsi dal tavolino del caffè all'aperto controllando gli effetti personali: 'Ricordati di dare un'occhiata alla sedia per non lasciare il portafoglio o gli occhiali.'",
    "IR84": "Sentendo il fischio dei freni riecheggiare sulla banchina della stazione: 'Guarda il tabellone luminoso: il treno Frecciarossa è appena arrivato al binario tre.'",
    "IR85": "Festeggiando la consegna della tesi di laurea in segreteria studenti: 'Tra notti insonni e revisioni dell'ultimo minuto, è riuscito brillantemente a consegnare la tesi.'",
    "IR86": "Finito il pranzo domenicale mentre tutti sparecchiano allegramente: 'Subito dopo aver sparecchiato la tavola, papà si è messo a preparare il caffè con la moka napoletana.'",
    "IR87": "In pasticceria preparando la crema pasticcera per la torta: 'Prendi il panetto di burro dal frigo! In italiano il burro è la morbida crema di latte, non l'asinello spagnolo!'",
    "IR88": "Davanti alla tromba delle scale con l'ascensore fuori servizio per manutenzione: 'L'ascensore è fermo per guasto: dobbiamo salire a piedi fino al quarto piano con le borse!'",
    "IR89": "Al bar commentando la partita di campionato della squadra del cuore: 'La nostra difesa ha subito una forte pressione per tutti i novanta minuti di gioco.'",
    "IR90": "Prima di attraversare una strada trafficata sulle strisce pedonali: 'Fermati sul marciapiede e prenditi un secondo: dobbiamo guardare bene prima di attraversare la strada.'",
    "IR91": "Osservando un giovane cameriere impeccabile e premuroso in trattoria: 'Quel ragazzo è estremamente educato: ringrazia con garbo e tratta ogni cliente con grande rispetto.'",
    "IR92": "Tentando di parcheggiare un furgone voluminoso in un vicolo medievale acciottolato: 'Questa viuzza è strettissima e il furgone è molto largo, rischiamo di rigare le fiancate!'",
    "IR93": "Passeggiando per le vie del centro cercando un souvenir speciale: 'Entriamo in quel piccolo negozio di legatoria artigianale a comprare un taccuino in pelle.'",
    "IR94": "Durante un colloquio di lavoro discutendo i carichi di mansioni: 'Voglio dare il massimo, ma non puoi pretendere che completi tre progetti complessi in un solo giorno!'",
    "IR95": "A bordo del taxi indicando l'ingresso dell'albergo all'autista: 'Mi scusi autista, potrebbe fermare la macchina proprio qui davanti al portone principale?'",
    "IR96": "Un genitore premuroso che vede il bambino arrampicarsi su un muretto fangoso: 'Attento ai rami bagnati! In italiano diciamo salire per andare in alto, non confonderlo col francese salir!'",
}

def overhaul_italian_roleplay():
    csv_file = BASE_DIR / "ITALIAN_READY_PROMPTS_ROLEPLAY.csv"
    with open(csv_file, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    updated_count = 0
    for r in rows:
        cid = r["ID"].strip().upper()
        if cid in ROLEPLAY_SCENARIOS_ITALIAN:
            r["ROLEPLAY_SCENARIO"] = ROLEPLAY_SCENARIOS_ITALIAN[cid]
            updated_count += 1

    fieldnames = list(rows[0].keys())
    with open(csv_file, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Updated {updated_count}/{len(rows)} Italian Roleplay scenarios in {csv_file.name}")

# --- 2. ITALIAN FUN FACTS (15 Viral Curiosities) ---
FUN_FACTS_ITALIAN = [
    {
        "ID": "IF01",
        "TOPIC": "L'alfabeto italiano ha soltanto 21 lettere",
        "PILLAR": "LANGUAGE_CURIOSITIES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "L'alfabeto italiano standard ha soltanto 21 lettere autoctone. Le lettere J, K, W, X e Y non fanno parte dell'alfabeto nativo e si usano solo nei prestiti linguistici come 'jeans', 'kiwi' o 'weekend'.",
        "HOOK_ANGLE": "L'italiano ha bandito 5 lettere dal suo alfabeto e gli italiani non ne hanno mai sentito la mancanza!",
        "EMOTIONAL_TRIGGER": "Curiosità & Sorpresa"
    },
    {
        "ID": "IF02",
        "TOPIC": "L'amichevole saluto Ciao ha origine dagli schiavi veneziani",
        "PILLAR": "ETYMOLOGY",
        "FORMAT": "MYSTERY",
        "FACT_DETAILS": "'Ciao' deriva dall'antico saluto dialettale veneziano 's-ciào vostro' o 's-ciavo', che significava 'sono vostro schiavo / umile servitore' (dal latino medievale 'sclavus'). Con i secoli i veneziani lo hanno abbreviato in 'ciao', trasformandolo nel saluto informale più celebre al mondo.",
        "HOOK_ANGLE": "Il saluto italiano più amichevole e famoso al mondo nasconde un'origine storica incredibilmente oscura.",
        "EMOTIONAL_TRIGGER": "Sorpresa & Fascinazione"
    },
    {
        "ID": "IF03",
        "TOPIC": "I gesti italiani sono una vera e propria seconda grammatica",
        "PILLAR": "CULTURAL_DIFFERENCES",
        "FORMAT": "3_FACTS",
        "FACT_DETAILS": "I linguisti hanno catalogato oltre 250 gesti distinti delle mani usati in Italia. Nati durante i secoli di dominazioni straniere e forti differenze dialettali, formano un linguaggio universale silenzioso e ricchissimo.",
        "HOOK_ANGLE": "3 gesti delle mani italiani capaci di comunicare frasi intere e complesse senza aprire bocca.",
        "EMOTIONAL_TRIGGER": "Divertimento & Scoperta"
    },
    {
        "ID": "IF04",
        "TOPIC": "Quando l'Italia fu unificata quasi nessuno parlava italiano",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "Al momento dell'unificazione nel 1861, solo circa il 2,5% della popolazione parlava italiano standard; tutti gli altri parlavano dialetti e lingue regionali distinte come siciliano, napoletano o veneziano. L'italiano moderno si basa sul capolavoro fiorentino del Trecento di Dante Alighieri.",
        "HOOK_ANGLE": "Quando l'Italia divenne una nazione unita, praticamente quasi nessun italiano parlava la lingua italiana!",
        "EMOTIONAL_TRIGGER": "Incredulità & Storia"
    },
    {
        "ID": "IF05",
        "TOPIC": "La parola comune più lunga della lingua italiana",
        "PILLAR": "EXTREMES",
        "FORMAT": "CHALLENGE",
        "FACT_DETAILS": "'Precipitevolissimevolmente' (26 lettere) significa 'con grandissima fretta e precipitazione'. Fu coniata dal poeta Francesco Moneti nel 1677 ed è considerata la parola d'uso comune più lunga della lingua italiana.",
        "HOOK_ANGLE": "Riesci a pronunciare la parola di 26 lettere più lunga dell'italiano senza annodarti la lingua?",
        "EMOTIONAL_TRIGGER": "Sfida giocosa & Divertimento"
    },
    {
        "ID": "IF06",
        "TOPIC": "Il tabù sacro del cappuccino dopo le 11 del mattino",
        "PILLAR": "CULTURAL_DIFFERENCES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "Per la cultura gastronomica italiana, ordinare un cappuccino dopo mezzogiorno o dopo un pasto è un sacrilegio. Per gli italiani il latte caldo mescolato al caffè è esclusivamente una bevanda da colazione; berlo a stomaco pieno dopo pranzo ostacola la digestione.",
        "HOOK_ANGLE": "Perché ordinare un cappuccino alle 14:00 fa inorridire qualsiasi cameriere in Italia?",
        "EMOTIONAL_TRIGGER": "Umorismo & Curiosità"
    },
    {
        "ID": "IF07",
        "TOPIC": "L'intraducibile parola italiana: L'abbiocco",
        "PILLAR": "WORD_CURIOSITIES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "'L'abbiocco' è quel torpore irresistibile, quella sonnolenza dolce e pesante che ti assale dopo un abbondante piatto di pasta o un pranzo festivo. In inglese o spagnolo non esiste una sola parola che catturi esattamente questa sensazione.",
        "HOOK_ANGLE": "L'Italia ha una parola perfetta per quel coma da carboidrati che ti colpisce dopo mangiato!",
        "EMOTIONAL_TRIGGER": "Simpatia & Verità"
    },
    {
        "ID": "IF08",
        "TOPIC": "Perché quasi tutte le parole italiane finiscono con una vocale?",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "L'italiano ha conservato la naturale dolcezza del latino volgare toscano, dove le consonanti finali si sono gradualmente attenuate o trasformate in vocali per ragioni eufoniche (bellezza del suono). Questo rende l'italiano una delle lingue più cantabili e melodiche al mondo.",
        "HOOK_ANGLE": "Hai mai notato che il 99% delle parole italiane finisce con una vocale? Ecco il segreto della sua melodia!",
        "EMOTIONAL_TRIGGER": "Fascino & Rivelazione"
    },
    {
        "ID": "IF09",
        "TOPIC": "Le doppie consonanti possono cambiarti la vita in Italia",
        "PILLAR": "PRONUNCIATION_CURIOSITIES",
        "FORMAT": "3_FACTS",
        "FACT_DETAILS": "In italiano, raddoppiare una consonante cambia radicalmente il significato: 'penne' (la pasta) vs 'pene' (anatomia), 'anno' (365 giorni) vs 'ano', 'pala' (attrezzo) vs 'palla' (da gioco). Una sola consonante può trasformare un complimento in una gaffe colossale!",
        "HOOK_ANGLE": "3 parole italiane in cui una singola lettera doppia fa la differenza tra ordinare la cena o fare una figuraccia epica!",
        "EMOTIONAL_TRIGGER": "Umorismo & Attenzione"
    },
    {
        "ID": "IF10",
        "TOPIC": "Il superpotere emotivo della parola 'Magari!'",
        "PILLAR": "WORD_CURIOSITIES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "'Magari' (dal greco 'makarie', beato te) è una delle parole più espressive della lingua italiana: da sola può significare 'magari fosse vero!' (speranza intensa), 'forse' (possibilità), o un malinconico rimpianto. È un intero stato d'animo condensato in sei lettere.",
        "HOOK_ANGLE": "Una sola parola italiana di 6 lettere che esprime desiderio, speranza e rimpianto contemporaneamente!",
        "EMOTIONAL_TRIGGER": "Poesia & Bellezza"
    },
    {
        "ID": "IF11",
        "TOPIC": "L'origine dell'Aperitivo: nato a Torino nel 1786",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "La parola 'aperitivo' viene dal latino 'aperire' (aprire, cioè stimolare l'appetito). Il rito sociale moderno è nato a Torino nel 1786 quando il distillatore Antonio Benedetto Carpano inventò il Vermut, vino aromatizzato con erbe e spezie servito con piccoli stuzzichini prima di cena.",
        "HOOK_ANGLE": "Dov'è nato esattamente il sacro rito dell'Aperitivo che tutto il mondo invidia all'Italia?",
        "EMOTIONAL_TRIGGER": "Cultura & Fascino"
    },
    {
        "ID": "IF12",
        "TOPIC": "Perché il mondo della musica classica parla solo italiano",
        "PILLAR": "LANGUAGE_HISTORY",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "Dall'opera lirica di Monteverdi e Verdi agli spartiti moderni in tutto il mondo, i termini musicali sono rimasti universali in lingua italiana: allegro, adagio, crescendo, pianissimo, forte, staccato, soprano, orchestra. L'Italia è stata la culla della notazione musicale moderna.",
        "HOOK_ANGLE": "Perché anche i musicisti in Giappone o in America leggono i loro spartiti in lingua italiana?",
        "EMOTIONAL_TRIGGER": "Orgoglio & Storia"
    },
    {
        "ID": "IF13",
        "TOPIC": "Il termine affettuoso intraducibile: Pantofolaio",
        "PILLAR": "WORD_CURIOSITIES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "'Pantofolaio' descrive con ironia e tenerezza chi ama stare a casa comodo in pantofole e tuta, rifiutando feste rumorose per godersi il divano, una tisana e un bel libro o film. In inglese si dice 'couch potato', ma 'pantofolaio' ha un tocco molto più caloroso e familiare.",
        "HOOK_ANGLE": "La deliziosa parola italiana per chi ama stare a casa in ciabatte e rifiuta ogni invito a uscire!",
        "EMOTIONAL_TRIGGER": "Simpatia & Sorriso"
    },
    {
        "ID": "IF14",
        "TOPIC": "La leggenda metropolitana degli 'Spaghetti alla Bolognese'",
        "PILLAR": "CULTURAL_DIFFERENCES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "In nessun ristorante autentico di Bologna troverete mai gli 'spaghetti alla bolognese': è un piatto inventato all'estero. A Bologna il celebre ragù si serve rigorosamente con le 'tagliatelle all'uovo', perché la sfoglia ruvida trattiene la carne, a differenza dello spaghetto liscio!",
        "HOOK_ANGLE": "Il piatto italiano più famoso all'estero che in realtà NON ESISTE nella cucina italiana autentica!",
        "EMOTIONAL_TRIGGER": "Sorpresa & Verità"
    },
    {
        "ID": "IF15",
        "TOPIC": "L'incredibile mistero del Congiuntivo italiano",
        "PILLAR": "LANGUAGE_CURIOSITIES",
        "FORMAT": "ONE_BIG_CURIOSITY",
        "FACT_DETAILS": "Il congiuntivo è il modo verbale dell'incertezza, del dubbio, dei sogni e dei sentimenti ('credo che sia', 'vorrei che tu venissi'). È considerato il banco di prova supremo non solo per chi studia l'italiano, ma anche per gli stessi italiani, che spesso vi inciampano nei talk show televisivi!",
        "HOOK_ANGLE": "Il tempo verbale italiano che fa tremare anche i madrelingua e che esprime l'anima poetica del dubbio.",
        "EMOTIONAL_TRIGGER": "Empatia & Umorismo"
    }
]

def overhaul_italian_fun_facts():
    csv_file = BASE_DIR / "ITALIAN_READY_PROMPTS_FUN_FACTS.csv"
    fieldnames = ["ID", "TOPIC", "PILLAR", "FORMAT", "FACT_DETAILS", "HOOK_ANGLE", "EMOTIONAL_TRIGGER"]
    with open(csv_file, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(FUN_FACTS_ITALIAN)
    print(f"[OK] Updated {len(FUN_FACTS_ITALIAN)} Italian Fun Facts in {csv_file.name}")

if __name__ == "__main__":
    overhaul_italian_roleplay()
    overhaul_italian_fun_facts()
