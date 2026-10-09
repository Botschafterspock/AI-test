"""
Server für dein Chat+Code-Modell (model_all.pt).

Start:  py server_all.py
Im Java-Client:
  normal schreiben          -> Chat
  /code <Anfang des Codes>  -> die AI schreibt den Code weiter, z. B.
                               /code public class HelloPlugin extends JavaPlugin {
"""
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import torch
from gpt import GPT

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "model_all.pt")      # alternativ: model_all_last.pt

# ---------- Einstellungen ----------
PORT = 8080
AI_NAME = "JOJO-AI"
CHAT_TEMPERATURE = 0.3
CODE_TEMPERATURE = 0.6              # höher = kreativer, aber mehr Fehler
TOP_K = 20
MAX_CHAT_BYTES = 300
MAX_CODE_BYTES = 1200
CONTEXT_MESSAGES = 1                # so viele letzte Nachrichten sieht die AI im Chat
# -----------------------------------

device = "cuda" if torch.cuda.is_available() else "cpu"
if not os.path.exists(MODEL_PATH):
    raise SystemExit("model_all.pt fehlt. Erst trainieren: py train_all.py")
ckpt = torch.load(MODEL_PATH, map_location=device)
if ckpt.get("tokenizer") != "byte":
    raise SystemExit("Diese Datei ist kein Byte-Modell. Nutze server.py für model.pt.")
model = GPT(**ckpt["config"]).to(device)
model.load_state_dict(ckpt["model"])
model.eval()
sessions = {}


def encode(s):
    return torch.tensor([list(s.encode("utf-8"))], dtype=torch.long, device=device)


def decode(ids):
    return bytes(ids).decode("utf-8", errors="ignore")


def chat_reply(history):
    prompt = ""
    for m in history[-CONTEXT_MESSAGES:]:
        prompt += f"User: {m['content']}\n" if m["role"] == "user" else f"AI: {m['content']}\n\n"
    prompt += "AI:"
    ids = encode(prompt)
    out = model.generate(ids, MAX_CHAT_BYTES, CHAT_TEMPERATURE, TOP_K, stop_fn=lambda t: t == 10)
    return decode(out[0, ids.size(1):].tolist()).strip() or "..."


def complete_code(prefix):
    looks_java = any(k in prefix for k in ("public ", "class ", "import java", ";", "void "))
    name = "Main.java" if looks_java else "main.py"
    prompt = f"<<<FILE {name}>>>\n{prefix}"
    ids = encode(prompt)
    buf = []

    def stop(t):
        buf.append(t)
        return bytes(buf[-9:]) == b"<<<END>>>"

    out = model.generate(ids, MAX_CODE_BYTES, CODE_TEMPERATURE, TOP_K, stop_fn=stop)
    text = decode(out[0, ids.size(1):].tolist()).replace("<<<END>>>", "").rstrip()
    return prefix + text


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, text):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send(200, f"{AI_NAME} läuft. Chatte über den Java-Client.")

    def do_POST(self):
        if self.path != "/chat":
            return self._send(404, "Nicht gefunden")
        session_id = self.headers.get("X-Session", "default")
        length = int(self.headers.get("Content-Length", 0))
        user_text = self.rfile.read(length).decode("utf-8").strip()
        if not user_text:
            return self._send(400, "Leere Nachricht")

        try:
            if user_text.startswith("/code"):
                prefix = user_text[5:].lstrip()
                if not prefix:
                    return self._send(200, "Schreib den Anfang des Codes hinter /code, z. B. /code public class Test {")
                return self._send(200, complete_code(prefix))

            user_text = user_text.replace("\n", " ")
            history = sessions.setdefault(session_id, [])
            history.append({"role": "user", "content": user_text})
            answer = chat_reply(history)
            history.append({"role": "assistant", "content": answer})
            del history[:-40]
            self._send(200, answer)
        except Exception as e:
            self._send(500, f"Fehler im Modell: {e}")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    print(f"{AI_NAME} (Chat+Code) läuft auf http://localhost:{PORT}  (Gerät: {device})")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
