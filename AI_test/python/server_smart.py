"""
Schlauerer Server für deine eigene AI: Antworten aus deinem Wissen, mit Tippfehler-Toleranz.

Start:  py server_smart.py

Er liest Frage-Antwort-Paare aus data/train.txt und data/wissen.txt.
Zusätzliche Befehle:
  /lerne <Frage> => <Antwort>   speichert neues Wissen in data/wissen.txt
  /reload                       liest die Wissensdateien erneut ein
  /code <Anfang>                vervollständigt Code mit model_all.pt
"""
import difflib
import math
import os
import random
import re
from collections import Counter
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
KNOWLEDGE_FILES = ["train.txt", "wissen.txt"]
LEARN_FILE = os.path.join(DATA_DIR, "wissen.txt")

PORT = 8080
AI_NAME = "JOJO-AI"
THRESHOLD = 0.40
CODE_TEMPERATURE = 0.6
MAX_CODE_BYTES = 1200

STOP = {"was", "ist", "sind", "wie", "wer", "wo", "wann", "warum", "wieso", "du", "dein", "deine", "dir",
        "dich", "ich", "mir", "mich", "mein", "meine", "bist", "hast", "kannst", "kennst", "weißt", "weisst",
        "kann", "können", "erkläre", "erklär", "erklären", "erzähl", "erzähle", "etwas", "über", "von", "vom",
        "mit", "ein", "eine", "einen", "einem", "einer", "der", "die", "das", "den", "dem", "des", "es",
        "bitte", "und", "oder", "auch", "nicht", "noch", "schon", "gern", "gerne", "hilfst", "gibt", "zeig"}
FILLER = {"sag", "mal", "äh", "kurze", "frage", "okay", "hey", "hi", "hallo", "moin"}
UNKNOWN_A = ["Das weiß ich noch nicht. JOJO hat mir dazu nichts beigebracht.",
             "Dazu kann ich leider nichts sagen, das steht nicht in meinem Wissen.",
             "Da muss ich passen, das habe ich nicht gelernt. Mit /lerne kannst du es mir beibringen."]
GIBBERISH_A = ["Das habe ich nicht verstanden. Kannst du es anders sagen?",
               "Hm, damit kann ich nichts anfangen. Magst du es nochmal versuchen?"]
NAME_RE = re.compile(r"^(ich heiße|ich heisse|mein name ist|nenn mich|ich bin)\s+([^\s.,!?]{2,20})\s*[.!]?$", re.I)


def tokens_of(text):
    toks = re.findall(r"\w+", text.lower())
    stripped = [t for t in toks if t not in FILLER]
    return stripped if stripped else toks


def grams_of(text):
    s = " " + text + " "
    return Counter(s[i:i + 3] for i in range(len(s) - 2))


def similar(a, b):
    if a == b:
        return True
    return len(a) >= 4 and len(b) >= 4 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.78


class Knowledge:
    def __init__(self):
        entries = {}
        overridden = set()
        for fname in KNOWLEDGE_FILES:
            path = os.path.join(DATA_DIR, fname)
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                text = f.read().replace("\r\n", "\n")
            for block in text.split("\n\n"):
                lines = block.strip().split("\n")
                if len(lines) < 2 or not lines[0].startswith("User:") or not lines[1].startswith("AI:"):
                    continue
                q, a = lines[0][5:].strip(), lines[1][3:].strip()
                if NAME_RE.match(q):
                    continue
                toks = tokens_of(q)
                if not toks or not a:
                    continue
                key = " ".join(toks)
                entry = entries.setdefault(key, {"answers": [], "tokens": toks})
                if fname == "wissen.txt" and key not in overridden:
                    entry["answers"] = []
                    overridden.add(key)
                if a not in entry["answers"]:
                    entry["answers"].append(a)

        self.items = list(entries.items())
        self.vocab = {t for _, entry in self.items for t in entry["tokens"]}
        df = Counter()
        for key, _ in self.items:
            df.update(grams_of(key).keys())
        n = len(self.items)
        self.idf = {gram: math.log((n + 1) / (count + 1)) + 1 for gram, count in df.items()}
        self.vecs = [self._vector(key) for key, _ in self.items]

    def _vector(self, text):
        vector = {gram: count * self.idf.get(gram, 1.0) for gram, count in grams_of(text).items()}
        norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
        return {gram: value / norm for gram, value in vector.items()}

    def answer(self, text):
        toks = tokens_of(text)
        if not toks:
            return random.choice(GIBBERISH_A)
        key = " ".join(toks)
        content = [token for token in toks if token not in STOP]
        vector = self._vector(key)
        scored = []
        for (entry_key, entry), entry_vector in zip(self.items, self.vecs):
            score = sum(weight * entry_vector.get(gram, 0.0) for gram, weight in vector.items())
            scored.append((score, entry_key, entry))
        scored.sort(key=lambda item: -item[0])
        for score, _, entry in scored[:8]:
            if score < THRESHOLD:
                break
            entry_content = [token for token in entry["tokens"] if token not in STOP]
            if content and entry_content and not any(
                    similar(token, known) for token in content for known in entry_content):
                continue
            return random.choice(entry["answers"])
        known = any(
            token in self.vocab
            or difflib.get_close_matches(token, self.vocab, n=1, cutoff=0.72)
            for token in toks
        )
        return random.choice(UNKNOWN_A if known else GIBBERISH_A)


kb = Knowledge()


def reply(text):
    match = NAME_RE.match(text.strip())
    if match:
        word = match.group(2)
        if match.group(1).lower() != "ich bin" or word[0].isupper():
            name = word[0].upper() + word[1:]
            return random.choice([f"Schön dich kennenzulernen, {name}!", f"Hallo {name}, freut mich!"])
    return kb.answer(text)


def learn(arg):
    if "=>" not in arg:
        return "Format: /lerne <Frage> => <Antwort>"
    question, answer = (part.strip().replace("\n", " ") for part in arg.split("=>", 1))
    if not question or not answer:
        return "Format: /lerne <Frage> => <Antwort>"
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LEARN_FILE, "a", encoding="utf-8") as f:
        f.write(f"User: {question}\nAI: {answer}\n\n")
    global kb
    kb = Knowledge()
    return f"Gelernt! Auf \"{question}\" antworte ich jetzt: {answer}"


_code = {}


def complete_code(prefix):
    if "m" not in _code:
        _code["m"] = None
        path = os.path.join(HERE, "model_all.pt")
        if os.path.exists(path):
            try:
                import torch
                from gpt import GPT
                device = "cuda" if torch.cuda.is_available() else "cpu"
                checkpoint = torch.load(path, map_location=device)
                model = GPT(**checkpoint["config"]).to(device)
                model.load_state_dict(checkpoint["model"])
                model.eval()
                _code["m"] = (torch, model, device)
            except Exception as error:
                print("Code-Modell konnte nicht geladen werden:", error)
    if _code["m"] is None:
        return "Für /code fehlt model_all.pt. Erst trainieren: py train_all.py"
    torch, model, device = _code["m"]
    looks_java = any(key in prefix for key in ("public ", "class ", "import java", ";", "void "))
    prompt = f"<<<FILE {'Main.java' if looks_java else 'main.py'}>>>\n{prefix}"
    ids = torch.tensor([list(prompt.encode("utf-8"))], dtype=torch.long, device=device)
    generated = []

    def stop(token):
        generated.append(token)
        return bytes(generated[-9:]) == b"<<<END>>>"

    output = model.generate(ids, MAX_CODE_BYTES, CODE_TEMPERATURE, 20, stop_fn=stop)
    text = bytes(output[0, ids.size(1):].tolist()).decode("utf-8", errors="ignore")
    return prefix + text.replace("<<<END>>>", "").rstrip()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, text):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send(200, f"{AI_NAME} läuft ({len(kb.items)} bekannte Fragen).")

    def do_POST(self):
        if self.path != "/chat":
            return self._send(404, "Nicht gefunden")
        try:
            length = int(self.headers.get("Content-Length", 0))
            text = self.rfile.read(length).decode("utf-8").strip()
        except (ValueError, UnicodeDecodeError) as error:
            return self._send(400, f"Ungültige Anfrage: {error}")
        if not text:
            return self._send(400, "Leere Nachricht")
        try:
            global kb
            if text.startswith("/lerne"):
                return self._send(200, learn(text[6:]))
            if text.startswith("/reload"):
                kb = Knowledge()
                return self._send(200, f"Neu geladen: {len(kb.items)} bekannte Fragen.")
            if text.startswith("/code"):
                prefix = text[5:].lstrip()
                answer = complete_code(prefix) if prefix else "Schreib den Anfang des Codes hinter /code."
                return self._send(200, answer)
            return self._send(200, reply(text.replace("\n", " ")))
        except Exception as error:
            return self._send(500, f"Fehler: {error}")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    print(f"{AI_NAME} (schlau) läuft auf http://localhost:{PORT} mit {len(kb.items)} bekannten Fragen")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
