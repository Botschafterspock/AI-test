"""
Trainiert deine eigene AI auf CHAT und CODE (Java + Python) - komplett von Grund auf.

Start:  py train_all.py

Was es macht:
  1. Sammelt alle .java- und .py-Dateien aus den Ordnern in CODE_DIRS (Standard: dein ganzer
     Projekte-Ordner, also der Ordner ÜBER AI_test, z. B. D:\\Temp\\code mc).
  2. Mischt sie mit deinen Chat-Dialogen aus data/train.txt.
  3. Trainiert ein Modell (arbeitet mit Bytes, kann also jedes Zeichen).
  4. Speichert:  model_all.pt (bestes Modell)  und  model_all_last.pt (zum Weitertrainieren).

Danach:  py server_smart.py
Nutze nur Code, den du selbst geschrieben hast oder verwenden darfst (Lizenzen!).
"""
import hashlib
import math
import os
import random
import time

import torch
from gpt import GPT

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
CHAT_PATH = os.path.join(HERE, "data", "train.txt")
BEST_PATH = os.path.join(HERE, "model_all.pt")
LAST_PATH = os.path.join(HERE, "model_all_last.pt")
LOG_PATH = os.path.join(HERE, "train_all_log.txt")
STOP_PATH = os.path.join(HERE, "STOP_TRAINING")

# ---------- Einstellungen ----------
# Ordner mit Code, aus dem die AI lernen soll. Standard: alle deine Projekte neben AI_test.
# Weitere Ordner einfach in die Liste schreiben, z. B. r"D:\Temp\mein-anderer-code"
CODE_DIRS = [os.path.dirname(PROJECT_ROOT)]
EXTENSIONS = (".java", ".py")
SKIP_DIRS = {"target", "bin", "build", "out", ".git", ".idea", ".settings", "node_modules",
             "__pycache__", "venv", ".venv", "data", "libs"}
MAX_FILE_BYTES = 300_000_000_000          # größere Dateien werden übersprungen

HOURS = float(os.environ.get("AI_TRAIN_HOURS", "12"))
EVAL_EVERY = 250                  # alle X Schritte: auswerten + speichern
PATIENCE = 0                      # 0 = nicht wegen ausbleibender Verbesserung abbrechen
LEARNING_RATE = 6e-4
MIN_LR = 6e-5
DROPOUT = 0.1
RESUME = True
# -----------------------------------

if os.name == "nt":  # Windows: Energiesparmodus während des Trainings verhindern
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    except Exception:
        pass

CODE_DIRS = [
    os.path.dirname(PROJECT_ROOT),
    r"D:\Temp\code mc",
   ]


def log(msg):
    print(msg, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def collect_code():
    docs, seen = [], set()
    for root_dir in CODE_DIRS:
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS and not d.startswith(".")]
            for fn in filenames:
                if not fn.lower().endswith(EXTENSIONS):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    if os.path.getsize(path) > MAX_FILE_BYTES:
                        continue
                    with open(path, "r", encoding="utf-8") as f:
                        code = f.read()
                except (OSError, UnicodeDecodeError):
                    continue
                code = code.replace("\r\n", "\n").strip("\n")
                if len(code) < 40:
                    continue
                h = hashlib.md5(code.encode("utf-8")).hexdigest()
                if h in seen:
                    continue
                seen.add(h)
                docs.append(f"<<<FILE {fn}>>>\n{code}\n<<<END>>>\n\n")
    return docs


code_docs = collect_code()
code_bytes = sum(len(d.encode("utf-8")) for d in code_docs)

chat_blocks = []
if os.path.exists(CHAT_PATH):
    with open(CHAT_PATH, "r", encoding="utf-8") as f:
        chat_text = f.read().replace("\r\n", "\n")
    chat_blocks = [b.strip("\n") + "\n\n" for b in chat_text.split("\n\n") if b.strip()]
chat_bytes = sum(len(b.encode("utf-8")) for b in chat_blocks)

log(f"Code: {len(code_docs)} Dateien, {code_bytes / 1e6:.2f} MB | Chat: {len(chat_blocks)} Dialoge, {chat_bytes / 1e6:.2f} MB")
if code_bytes < 300_000:
    log("ACHTUNG: Das ist wenig Code (unter 300 KB). Die AI lernt dann nur deinen Stil nachzuplappern. "
        "Füge in CODE_DIRS weitere Ordner mit Code hinzu, den du verwenden darfst.")

segments = code_docs + chat_blocks
random.Random(1337).shuffle(segments)
raw = "".join(segments).encode("utf-8")
if len(raw) < 20_000:
    raise SystemExit("Zu wenig Trainingsdaten gefunden. Prüfe CODE_DIRS und data/train.txt.")

if os.environ.get("DRY_RUN"):
    raise SystemExit("DRY_RUN: Daten sind okay, es wird nicht trainiert.")

device = "cuda" if torch.cuda.is_available() else "cpu"
torch.manual_seed(1337)

if device == "cuda":      # mit GPU: größeres Modell
    BLOCK_SIZE, N_EMBD, N_HEAD, N_LAYER, BATCH_SIZE = 256, 384, 6, 6, 32
else:                     # nur CPU: kleines Modell, sonst dauert es ewig
    BLOCK_SIZE, N_EMBD, N_HEAD, N_LAYER, BATCH_SIZE = 128, 192, 4, 4, 16

data = torch.frombuffer(bytearray(raw), dtype=torch.uint8)
data_hash = hashlib.sha256(raw).hexdigest()
split = int(0.95 * len(data))
train_data, val_data = data[:split], data[split:]
if len(val_data) <= BLOCK_SIZE + 1:
    val_data = train_data

config = dict(vocab_size=256, block_size=BLOCK_SIZE, n_embd=N_EMBD, n_head=N_HEAD,
              n_layer=N_LAYER, dropout=DROPOUT)
model = GPT(**config).to(device)
use_amp = device == "cuda" and torch.cuda.is_bf16_supported()
train_seed = int(os.environ.get("AI_TRAIN_SEED", "1337"))
torch.manual_seed(train_seed)
train_generator = torch.Generator().manual_seed(train_seed)

step = 0
best_val = float("inf")
if RESUME:
    src = BEST_PATH if os.path.exists(BEST_PATH) else (LAST_PATH if os.path.exists(LAST_PATH) else None)
    if src:
        ck = torch.load(src, map_location=device)
        if ck.get("config") == config and ck.get("tokenizer") == "byte":
            model.load_state_dict(ck["model"])
            step = ck.get("step", 0)
            if ck.get("data_hash") == data_hash and ck.get("eval_version") == 1:
                best_val = ck.get("best_val", float("inf"))
            else:
                log("Trainingsdaten oder Validierung geändert: Bestwert wird neu gemessen.")
            log(f"Setze Training fort (Schritt {step}) von {os.path.basename(src)}")
        else:
            log("Modell-Einstellungen haben sich geändert: starte neu. Alte Modelle bleiben als .alt erhalten.")
            for p in (LAST_PATH, BEST_PATH):
                if os.path.exists(p):
                    os.replace(p, p + ".alt")

log(f"Gerät: {device} | Modell: {sum(p.numel() for p in model.parameters()) / 1e6:.2f} Mio. Parameter | "
    f"Daten: {len(data) / 1e6:.2f} MB | Laufzeit max. {HOURS} h")

opt = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.1)


def get_batch(d, generator=None):
    ix = torch.randint(len(d) - BLOCK_SIZE - 1, (BATCH_SIZE,), generator=generator)
    x = torch.stack([d[i:i + BLOCK_SIZE] for i in ix]).long()
    y = torch.stack([d[i + 1:i + BLOCK_SIZE + 1] for i in ix]).long()
    return x.to(device), y.to(device)


# Reuse the same evaluation batches so best-checkpoint decisions are comparable.
eval_generator = torch.Generator().manual_seed(2025)
eval_batches = {
    name: [get_batch(d, eval_generator) for _ in range(20)]
    for name, d in (("train", train_data), ("val", val_data))
}


def loss_of(x, y):
    if use_amp:
        with torch.autocast("cuda", dtype=torch.bfloat16):
            return model(x, y)[1]
    return model(x, y)[1]


@torch.no_grad()
def estimate_loss():
    model.eval()
    out = {
        name: sum(loss_of(x, y).item() for x, y in batches) / len(batches)
        for name, batches in eval_batches.items()
    }
    model.train()
    return out


def save(path):
    torch.save({"model": model.state_dict(), "config": config, "tokenizer": "byte", "step": step,
                "best_val": best_val, "data_len": len(data), "data_hash": data_hash,
                "eval_version": 1}, path)


total_seconds = HOURS * 3600
start = time.time()
log("Training läuft. Strg+C bricht sauber ab (der Stand wird gespeichert).")

try:
    while True:
        if os.path.exists(STOP_PATH):
            log("Stoppsignal erkannt. Speichere den letzten Stand und beende das Training.")
            save(LAST_PATH)
            break

        elapsed = time.time() - start
        done = elapsed >= total_seconds
        frac = min(elapsed / total_seconds, 1.0)
        lr = MIN_LR + 0.5 * (LEARNING_RATE - MIN_LR) * (1 + math.cos(math.pi * frac))
        for g in opt.param_groups:
            g["lr"] = lr

        if step % EVAL_EVERY == 0 or done:
            l = estimate_loss()
            mark = ""
            if l["val"] < best_val:
                best_val = l["val"]
                save(BEST_PATH)
                mark = "  <- neues bestes Modell"
            save(LAST_PATH)
            log(f"Schritt {step:7d} | train {l['train']:.3f} | val {l['val']:.3f} | lr {lr:.5f} | "
                f"{elapsed / 60:.0f} min{mark}")
            if done:
                log("Zeit abgelaufen.")
                break
        loss = loss_of(*get_batch(train_data, train_generator))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        step += 1
except KeyboardInterrupt:
    log("Abgebrochen mit Strg+C. Speichere letzten Stand ...")
    save(LAST_PATH)

log(f"Fertig. Bestes Modell: {BEST_PATH} (val {best_val:.3f}). Jetzt: py server_smart.py")
