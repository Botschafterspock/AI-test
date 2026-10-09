"""
Erzeugt aus Vorlagen tausende Trainingsdialoge für deine AI: data/train.txt

Start:  python make_data.py     (oder py make_data.py)

- Jede Frage kommt in vielen Varianten vor (klein geschrieben, ohne Fragezeichen,
  mit Füllwörtern wie "Sag mal, ...").
- Bei unbekannten Themen und Tipp-Salat lernt die AI zu sagen "Das weiß ich noch nicht"
  statt Unsinn zu erzeugen.
- Eigene Dialoge kannst du in data/eigene.txt schreiben (gleiches Format wie train.txt).
  Sie werden beim Erzeugen automatisch angehängt.
- Neues Wissen ergänzt du unten in der Liste INTENTS.
"""
import os
import random

random.seed(42)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "train.txt")
EXTRA = os.path.join(HERE, "data", "eigene.txt")
N_DIALOGS = 6000

JOKES = [
    "Warum sind Creeper so schlechte Gäste? Weil sie immer explodieren, wenn es gemütlich wird.",
    "Warum tragen Java-Entwickler eine Brille? Weil sie kein C sharp sehen können.",
    "Was sagt ein Creeper zum Spieler? Ssssss.",
]

# (Fragen, Antworten)
INTENTS = [
    (["Hallo", "Hi", "Hey", "Moin", "Servus", "Hallo zusammen", "Huhu"],
     ["Hallo! Wie kann ich dir helfen?", "Hi! Was gibts?", "Hey! Schön, dass du da bist.", "Moin! Was kann ich für dich tun?"]),
    (["Guten Morgen", "Morgen"], ["Guten Morgen! Wie geht es dir?", "Morgen! Gut geschlafen?"]),
    (["Guten Abend", "Abend"], ["Guten Abend! Was kann ich für dich tun?"]),
    (["Gute Nacht"], ["Gute Nacht! Schlaf gut."]),
    (["Wie geht es dir?", "Wie gehts?", "Alles gut bei dir?", "Wie läuft es bei dir?"],
     ["Mir geht es gut, danke! Und dir?", "Alles gut bei mir. Und bei dir?"]),
    (["Mir geht es gut", "Gut", "Mir gehts gut", "Alles gut", "Ganz gut"],
     ["Das freut mich zu hören!", "Schön, das zu hören!"]),
    (["Mir geht es schlecht", "Schlecht", "Mir gehts nicht gut", "Nicht so gut"],
     ["Das tut mir leid. Magst du erzählen, was los ist?", "Oh nein, das tut mir leid. Kann ich dir irgendwie helfen?"]),
    (["Wer bist du?", "Wie heißt du?", "Was bist du?", "Stell dich vor", "Wie ist dein Name?"],
     ["Ich bin JOJO-AI, eine AI, die JOJO selbst gebaut und trainiert hat.", "Ich heiße JOJO-AI und bin ein kleines Sprachmodell."]),
    (["Wer hat dich gemacht?", "Wer hat dich gebaut?", "Wer hat dich programmiert?", "Von wem kommst du?"],
     ["JOJO hat mich mit Java und Python gebaut und von Grund auf trainiert."]),
    (["Bist du ChatGPT?", "Bist du Claude?", "Bist du Siri?", "Bist du Alexa?"],
     ["Nein, ich bin JOJO-AI. JOJO hat mich selbst gebaut und trainiert."]),
    (["Bist du ein Mensch?", "Bist du echt?", "Bist du ein Roboter?"],
     ["Nein, ich bin eine AI. Aber ich gebe mein Bestes."]),
    (["Was kannst du?", "Wofür bist du gut?", "Was kannst du alles?"],
     ["Ich kann mich unterhalten und ein paar Fragen zu Minecraft, Java und Python beantworten. Mehr weiß ich noch nicht."]),
    (["Kannst du mir helfen?", "Ich brauche Hilfe", "Hilfst du mir?"],
     ["Klar, ich versuche es. Was brauchst du?", "Gern! Worum geht es?"]),
    (["Kannst du coden?", "Kannst du programmieren?", "Kannst du Code schreiben?", "Kannst du Java?", "Kannst du Python?"],
     ["Nein, programmieren kann ich nicht. Ich kann mich nur unterhalten. JOJO programmiert in Java und Python."]),
    (["Verstehst du mich?", "Kannst du mich verstehen?"],
     ["Ich versuche es, aber ich bin noch klein und lerne noch dazu."]),
    (["Bist du schlau?", "Bist du intelligent?", "Wie schlau bist du?"],
     ["Ich werde schlauer, je mehr Daten JOJO mir zum Lernen gibt."]),
    (["Was machst du gerade?", "Was machst du?"], ["Ich unterhalte mich mit dir."]),
    (["Danke", "Vielen Dank", "Danke dir", "Dankeschön", "Thx"], ["Gern geschehen!", "Kein Problem, jederzeit!"]),
    (["Tschüss", "Bye", "Bis später", "Bis bald", "Ciao", "Auf Wiedersehen"],
     ["Tschüss! Bis bald.", "Bye! Bis zum nächsten Mal.", "Bis später!"]),
    (["Erzähl einen Witz", "Kennst du einen Witz?", "Sag einen Witz", "Bring mich zum Lachen"], JOKES),
    (["Wie spät ist es?", "Welcher Tag ist heute?", "Welches Datum haben wir?", "Wie ist das Wetter?", "Wie wird das Wetter?"],
     ["Das kann ich nicht wissen, ich habe keinen Zugriff auf Uhr, Datum oder Wetter."]),
    (["Wie alt bist du?"], ["Ich bin noch ganz neu. JOJO hat mich erst vor Kurzem trainiert."]),
    (["Sprichst du Englisch?", "Welche Sprache sprichst du?", "Sprichst du Deutsch?"],
     ["Ich kann nur Deutsch, und auch das noch nicht perfekt."]),
]

# (Nominativ, Akkusativ, Antwort) -> wird zu mehreren Fragen
FACTS = [
    ("Minecraft", "Minecraft", "Minecraft ist ein Spiel, in dem man Blöcke abbaut, baut und Abenteuer erlebt."),
    ("ein Creeper", "einen Creeper", "Ein Creeper ist ein grünes Monster in Minecraft, das sich anschleicht und explodiert."),
    ("ein Zombie", "einen Zombie", "Ein Zombie ist ein Gegner in Minecraft, der nachts auftaucht und im Sonnenlicht brennt."),
    ("ein Skelett", "ein Skelett", "Ein Skelett ist ein Gegner in Minecraft, der mit Pfeilen schießt."),
    ("ein Enderman", "einen Enderman", "Ein Enderman ist ein hohes schwarzes Monster, das sich teleportiert und wütend wird, wenn man ihm in die Augen schaut."),
    ("der Enderdrache", "den Enderdrachen", "Der Enderdrache ist der Endboss von Minecraft. Er lebt im End."),
    ("ein Dorfbewohner", "einen Dorfbewohner", "Dorfbewohner leben in Dörfern in Minecraft. Mit ihnen kann man handeln."),
    ("ein Diamant", "einen Diamanten", "Diamanten sind wertvolle Erze, die man tief unter der Erde findet. Man baut daraus starke Werkzeuge."),
    ("Redstone", "Redstone", "Redstone ist ein Material in Minecraft, mit dem man Schaltungen und Maschinen baut."),
    ("der Nether", "den Nether", "Der Nether ist eine gefährliche Dimension in Minecraft mit Lava und Piglins."),
    ("das End", "das End", "Das End ist eine Dimension in Minecraft, in der der Enderdrache lebt."),
    ("eine Werkbank", "eine Werkbank", "An einer Werkbank stellt man in Minecraft Werkzeuge und Gegenstände her."),
    ("Obsidian", "Obsidian", "Obsidian ist ein sehr harter schwarzer Block, der entsteht, wenn Wasser auf Lava trifft."),
    ("ein Netherportal", "ein Netherportal", "Ein Netherportal ist ein Portal aus Obsidian, mit dem man in den Nether reist."),
    ("Paper", "Paper", "Paper ist eine schnelle Server-Software für Minecraft, die Plugins unterstützt."),
    ("Spigot", "Spigot", "Spigot ist eine Minecraft-Server-Software, die Plugins unterstützt."),
    ("Bukkit", "Bukkit", "Bukkit ist eine Schnittstelle, mit der man Plugins für Minecraft-Server schreibt."),
    ("Fabric", "Fabric", "Fabric ist ein leichtgewichtiger Mod-Loader für Minecraft."),
    ("Forge", "Forge", "Forge ist ein Mod-Loader für Minecraft."),
    ("NeoForge", "NeoForge", "NeoForge ist ein Mod-Loader für Minecraft und der Nachfolger von Forge."),
    ("ein Plugin", "ein Plugin", "Ein Plugin erweitert einen Minecraft-Server um neue Funktionen, zum Beispiel neue Befehle."),
    ("eine Mod", "eine Mod", "Eine Mod verändert oder erweitert das Spiel, zum Beispiel mit neuen Blöcken oder Items."),
    ("ein Modpack", "ein Modpack", "Ein Modpack ist eine Sammlung von Mods, die zusammen als Paket installiert wird."),
    ("ein OP", "einen OP", "Ein OP ist ein Operator, also ein Spieler mit Admin-Rechten auf dem Server."),
    ("eine Whitelist", "eine Whitelist", "Eine Whitelist ist eine Liste von Spielern, die auf den Server dürfen."),
    ("ein Minecraft-Server", "einen Minecraft-Server", "Ein Minecraft-Server ist ein Computer, auf dem man mit anderen zusammen spielen kann."),
    ("Java", "Java", "Java ist eine Programmiersprache. Minecraft und viele Plugins sind damit geschrieben."),
    ("Python", "Python", "Python ist eine einfache Programmiersprache, die oft für KI und Skripte benutzt wird."),
    ("Eclipse", "Eclipse", "Eclipse ist eine Entwicklungsumgebung, in der man zum Beispiel Java-Programme schreibt."),
    ("Maven", "Maven", "Maven ist ein Build-Tool für Java-Projekte."),
    ("eine AI", "eine AI", "Eine AI ist ein Programm, das aus Daten lernt, um Aufgaben wie Sprache zu verstehen."),
    ("eine GPU", "eine GPU", "Eine GPU ist eine Grafikkarte. Sie kann auch das Training einer AI stark beschleunigen."),
    ("ein Sprachmodell", "ein Sprachmodell", "Ein Sprachmodell ist eine AI, die vorhersagt, welcher Text als Nächstes kommt."),
]

NAMES = ["JOJO", "Max", "Anna", "Lukas", "Lena", "Tim", "Sophie", "Jonas", "Laura", "Felix", "Marie", "Paul",
         "Julia", "Leon", "Emma", "Ben", "Mia", "Noah", "Hannah", "Finn", "Clara", "Elias", "Nina", "David",
         "Sarah", "Tom", "Lisa", "Jan", "Katharina", "Moritz"]

UNKNOWN_TOPICS = ["Fußball", "Bitcoin", "Pizza", "Mathe", "Chemie", "Schach", "Kaffee", "Musik", "Yoga",
                  "Fotografie", "Kochen", "Politik", "Geschichte", "Physik", "Astronomie", "Basketball",
                  "Tennis", "Philosophie", "Religion", "Urlaub", "Medizin", "Mode", "Kino", "Reiten",
                  "Gitarre", "Schokolade", "Eishockey", "Biologie", "Malen", "Tanzen"]
UNKNOWN_Q = ["Was ist {t}?", "Kennst du {t}?", "Erzähl mir etwas über {t}", "Was weißt du über {t}?"]
UNKNOWN_A = ["Das weiß ich noch nicht. JOJO hat mir dazu nichts beigebracht.",
             "Dazu kann ich leider nichts sagen, das steht nicht in meinen Trainingsdaten.",
             "Da muss ich passen, das habe ich nicht gelernt."]
GIBBERISH_A = ["Das habe ich nicht verstanden. Kannst du es anders sagen?",
               "Hm, damit kann ich nichts anfangen. Magst du es nochmal versuchen?"]

FILL = ["", "", "", "Sag mal, ", "Hey, ", "Kurze Frage: ", "Äh, ", "Okay, "]


def vary(q):
    prefix = random.choice(FILL)
    if prefix and q[:1].isupper() and not q.split()[0] in ("Java", "Python", "Minecraft", "Paper", "Eclipse"):
        q = q[0].lower() + q[1:]
    q = prefix + q
    r = random.random()
    if r < 0.2:
        q = q.lower()
    elif r < 0.3:
        q = q.rstrip("?!.")
    return q


def block(q, a):
    return f"User: {q}\nAI: {a}\n\n"


# Fakten in normale Intents umwandeln
for nom, acc, answer in FACTS:
    qs = [f"Was ist {nom}?", f"Erkläre mir {acc}", f"Erklär mir {acc} bitte", f"Kannst du mir {acc} erklären?"]
    INTENTS.append((qs, [answer]))

blocks = []

# Jede Frage mit jeder Antwort mindestens einmal unverändert
for qs, ans in INTENTS:
    for q in qs:
        blocks.append(block(q, random.choice(ans)))

# Zufällige Varianten
for _ in range(N_DIALOGS):
    kind = random.choices(["intent", "name", "unknown", "gibberish"], weights=[75, 6, 12, 7])[0]
    if kind == "intent":
        qs, ans = random.choice(INTENTS)
        blocks.append(block(vary(random.choice(qs)), random.choice(ans)))
    elif kind == "name":
        n = random.choice(NAMES)
        q = random.choice(["Ich heiße {n}", "Mein Name ist {n}", "Ich bin {n}", "Nenn mich {n}"]).format(n=n)
        a = random.choice(["Schön dich kennenzulernen, {n}!", "Hallo {n}, freut mich!"]).format(n=n)
        blocks.append(block(q, a))
    elif kind == "unknown":
        q = random.choice(UNKNOWN_Q).format(t=random.choice(UNKNOWN_TOPICS))
        blocks.append(block(vary(q), random.choice(UNKNOWN_A)))
    else:
        g = "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(random.randint(1, 9)))
        blocks.append(block(g, random.choice(GIBBERISH_A)))

random.shuffle(blocks)
text = "".join(blocks)

if os.path.exists(EXTRA):
    with open(EXTRA, "r", encoding="utf-8") as f:
        extra = f.read().replace("\r\n", "\n").strip()
    if extra:
        text += extra + "\n\n"
        print(f"Eigene Dialoge aus {EXTRA} angehängt.")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(text)
print(f"Fertig: {len(blocks)} Dialoge, {len(text):,} Zeichen -> {OUT}")