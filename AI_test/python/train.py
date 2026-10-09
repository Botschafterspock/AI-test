"""
Langzeit-Training für deine eigene AI (z. B. über Nacht).

Start:  python train.py   (oder py train.py)

- Läuft HOURS Stunden und hört dann von selbst auf (oder früher mit Strg+C).
- Macht automatisch da weiter, wo es aufgehört hat (model_last.pt).
- Speichert regelmäßig:
    model.pt       = bestes Modell (niedrigster Val-Loss) -> das lädt der Server
    model_last.pt  = letzter Stand -> damit wird weitertrainiert
- Schreibt ein Protokoll in train_log.txt
- Verhindert unter Windows, dass der PC in den Energiesparmodus geht.
"""
import math
import os
import time
import torch
from gpt import GPT

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "data", "train.txt")
BEST_PATH = os.path.join(HERE, "model.pt")
LAST_PATH = os.path.join(HERE, "model_last.pt")
LOG_PATH = os.path.join(HERE, "train_log.txt")

# ---------- Einstellungen ----------
HOURS = 16.0             # so lange soll maximal trainiert werden
BLOCK_SIZE = 128
N_EMBD = 128
N_HEAD = 4
N_LAYER = 3
DROPOUT = 0.1
BATCH_SIZE = 16
LEARNING_RATE = 1e-3    # startet hier und sinkt über die Laufzeit auf MIN_LR
MIN_LR = 1e-4
EVAL_EVERY = 250        # alle X Schritte: Loss ausgeben und speichern
RESUME = True           # True = vorhandenes Modell weitertrainieren
PATIENCE = 0            # >0: vorzeitig stoppen, wenn der Val-Loss X Auswertungen
                        # in Folge nicht besser wurde. 0 = nie vorzeitig stoppen
# -----------------------------------

if os.name == "nt":  # Windows: Energiesparmodus während des Trainings verhindern
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    except Exception:
        pass

device = "cuda" if torch.cuda.is_available() else "cpu"
torch.manual_seed(1337)


def log(msg):
    print(msg, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


with open(DATA_PATH, "r", encoding="utf-8") as f:
    text = f.read().replace("\r\n", "\n")

chars = sorted(set(text))
stoi = {c: i for i, c in enumerate(chars)}
data = torch.tensor([stoi[c] for c in text], dtype=torch.long)

if len(data) < BLOCK_SIZE * 4:
    raise SystemExit(f"Zu wenig Trainingsdaten ({len(data)} Zeichen). Füge mehr Text in data/train.txt ein.")

split = int(0.9 * len(data))
train_data, val_data = data[:split], data[split:]
if len(val_data) <= BLOCK_SIZE + 1:
    val_data = train_data

config = dict(vocab_size=len(chars), block_size=BLOCK_SIZE, n_embd=N_EMBD,
              n_head=N_HEAD, n_layer=N_LAYER, dropout=DROPOUT)
model = GPT(**config).to(device)

step = 0
best_val = float("inf")

if RESUME:
    src = LAST_PATH if os.path.exists(LAST_PATH) else (BEST_PATH if os.path.exists(BEST_PATH) else None)
    if src:
        ck = torch.load(src, map_location=device)
        if ck["chars"] == chars and ck["config"] == config:
            model.load_state_dict(ck["model"])
            step = ck.get("step", 0)
            if ck.get("data_len") == len(data):
                best_val = ck.get("best_val", float("inf"))
            else:
                log("Trainingsdaten haben sich geändert: Val-Loss wird neu bewertet.")
            log(f"Setze Training fort (Schritt {step}) von {os.path.basename(src)}")
        else:
            log("Zeichensatz oder Modell-Einstellungen haben sich geändert: starte neu. "
                "Alte Modelle bleiben als .alt erhalten.")
            for p in (LAST_PATH, BEST_PATH):
                if os.path.exists(p):
                    os.replace(p, p + ".alt")

log(f"Daten: {len(text):,} Zeichen, {len(chars)} verschiedene Zeichen, Gerät: {device}, "
    f"Modell: {sum(p.numel() for p in model.parameters()) / 1e6:.2f} Mio. Parameter, Laufzeit: {HOURS} h")

opt = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)


def get_batch(d):
    ix = torch.randint(len(d) - BLOCK_SIZE - 1, (BATCH_SIZE,))
    x = torch.stack([d[i:i + BLOCK_SIZE] for i in ix])
    y = torch.stack([d[i + 1:i + BLOCK_SIZE + 1] for i in ix])
    return x.to(device), y.to(device)


@torch.no_grad()
def estimate_loss():
    model.eval()
    out = {}
    for name, d in (("train", train_data), ("val", val_data)):
        losses = [model(*get_batch(d))[1].item() for _ in range(20)]
        out[name] = sum(losses) / len(losses)
    model.train()
    return out


def save(path):
    torch.save({"model": model.state_dict(), "chars": chars, "config": config,
                "step": step, "best_val": best_val, "data_len": len(data)}, path)


total_seconds = HOURS * 3600
start = time.time()
bad_evals = 0
log("Training läuft. Mit Strg+C kannst du jederzeit sauber abbrechen (Stand wird gespeichert).")

try:
    while True:
        elapsed = time.time() - start
        done = elapsed >= total_seconds

        # Lernrate sinkt sanft über die Laufzeit (Cosinus)
        frac = min(elapsed / total_seconds, 1.0)
        lr = MIN_LR + 0.5 * (LEARNING_RATE - MIN_LR) * (1 + math.cos(math.pi * frac))
        for g in opt.param_groups:
            g["lr"] = lr

        if step % EVAL_EVERY == 0 or done:
            l = estimate_loss()
            mark = ""
            if l["val"] < best_val:
                best_val = l["val"]
                bad_evals = 0
                save(BEST_PATH)
                mark = "  <- neues bestes Modell"
            else:
                bad_evals += 1
            save(LAST_PATH)
            log(f"Schritt {step:7d} | train {l['train']:.3f} | val {l['val']:.3f} | "
                f"lr {lr:.5f} | {elapsed / 60:.0f} min{mark}")
            if done:
                log("Zeit abgelaufen.")
                break
            if PATIENCE and bad_evals >= PATIENCE:
                log(f"Val-Loss seit {PATIENCE} Auswertungen nicht besser: Training beendet.")
                break

        _, loss = model(*get_batch(train_data))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        step += 1
except KeyboardInterrupt:
    log("Abgebrochen mit Strg+C. Speichere letzten Stand ...")
    save(LAST_PATH)

log(f"Fertig. Bestes Modell: {BEST_PATH} (val {best_val:.3f}). Server neu starten, um es zu laden.")