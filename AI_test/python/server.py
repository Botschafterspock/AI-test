"""
Backend für deine eigene AI: lädt dein selbst trainiertes Modell (model.pt)
und beantwortet Chat-Anfragen vom Java-Client.

Vorher:  python train.py
Start:   python server.py
"""
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import torch
from gpt import GPT

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "model_last.pt")

# ---------- Einstellungen ----------
PORT = 8080
AI_NAME = "JOJO-AI"
TEMPERATURE = 0.3       # niedriger = sicherer, höher = kreativer/chaotischer
TOP_K = 15
MAX_REPLY_CHARS = 300
CONTEXT_MESSAGES = 1    # so viele letzte Nachrichten sieht die AI
# -----------------------------------

device = "cuda" if torch.cuda.is_available() else "cpu"

if not os.path.exists(MODEL_PATH):
    raise SystemExit("model.pt fehlt. Erst trainieren: python train.py")

ckpt = torch.load(MODEL_PATH, map_location=device)
chars = ckpt["chars"]
stoi = {c: i for i, c in enumerate(chars)}
itos = {i: c for i, c in enumerate(chars)}
model = GPT(**ckpt["config"]).to(device)
model.load_state_dict(ckpt["model"])
model.eval()

sessions = {}


def encode(s):
    return [stoi[c] for c in s if c in stoi]  # unbekannte Zeichen werden übersprungen


def reply(history):
    prompt = ""
    for m in history[-CONTEXT_MESSAGES:]:
        if m["role"] == "user":
            prompt += f"User: {m['content']}\n"
        else:
            prompt += f"AI: {m['content']}\n\n"
    prompt += "AI:"

    ids = torch.tensor([encode(prompt)], dtype=torch.long, device=device)
    out = model.generate(ids, MAX_REPLY_CHARS, TEMPERATURE, TOP_K,
                         stop_fn=lambda t: itos[t] == "\n")
    text = "".join(itos[i] for i in out[0, ids.size(1):].tolist())
    return text.strip() or "..."


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, text):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/chat":
            return self._send(404, "Nicht gefunden")
        session_id = self.headers.get("X-Session", "default")
        length = int(self.headers.get("Content-Length", 0))
        user_text = self.rfile.read(length).decode("utf-8").strip().replace("\n", " ")
        if not user_text:
            return self._send(400, "Leere Nachricht")

        history = sessions.setdefault(session_id, [])
        history.append({"role": "user", "content": user_text})
        try:
            answer = reply(history)
        except Exception as e:
            history.pop()
            return self._send(500, f"Fehler im Modell: {e}")
        history.append({"role": "assistant", "content": answer})
        del history[:-40]
        self._send(200, answer)

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    print(f"{AI_NAME} läuft auf http://localhost:{PORT}  (eigenes Modell, Gerät: {device})")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
