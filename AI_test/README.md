# AI_test - deine eigene AI (Java + Python, Maven)

Komplett eigene AI: ein kleines GPT-Sprachmodell, das du selbst trainierst.
Kein Ollama, kein Claude, keine API, kein fremdes vortrainiertes Modell.
Nur PyTorch als Rechenbibliothek.

## Struktur
- `pom.xml` - Maven, Java 1.8
- `src/main/java/de/jojo/ai/ChatClient.java` - Konsolen-Chat (Java-Client)
- `src/main/java/de/jojo/ai/GuiChatClient.java` - JavaFX-Chat-Oberfläche
- `python/gpt.py` - das Modell (Transformer)
- `python/train.py` - Training von Grund auf
- `python/server_smart.py` - beantwortet Chat-Anfragen aus `train.txt` und `wissen.txt`
- `python/data/train.txt` - deine Trainingsdaten

## Ablauf
1. Für CUDA auf Windows (RTX 50xx, im Ordner `AI_test`): `py -3.14 -m venv ..\.venv`, danach `..\.venv\Scripts\python.exe -m pip install --index-url https://download.pytorch.org/whl/cu130 --extra-index-url https://pypi.org/simple "torch==2.10.0+cu130"`. Das Training nimmt CUDA, wenn verfügbar, sonst automatisch die CPU.
2. Trainieren: `python python/train.py` (oder `start-train.bat`). Erzeugt `python/model.pt`.
3. Server starten: `start-server.bat` (oder `cd python` und `py server_smart.py`).
   Der Smart-Server verwendet die Frage-Antwort-Paare aus `python/data/train.txt`;
   mit `/lerne Frage => Antwort` kannst du Wissen in `python/data/wissen.txt` ergänzen.
   `/reload` lädt die Dateien erneut. `/code Anfang` verwendet optional `model_all.pt`,
   das mit `python/train_all.py` trainiert wird. Für den klassischen Modell-Chat bleibt
   `python/server_all.py` verfügbar.
4. Client starten: in Eclipse Rechtsklick auf `ChatClient.java` > Run As > Java Application
   (oder im Terminal `mvn compile exec:java`)
   Für die grafische Oberfläche: `start-gui-client.bat` (benötigt Maven und JDK 17+,
   alternativ `mvn -Pgui javafx:run`).
   Der normale Konsolen-Client bleibt über `start-client.bat` verfügbar.

`start-train.bat` startet in der sichtbaren Konsole einen durchgehenden 14-Tage-Trainingslauf. Vor dem Training erzeugt Ollama mit `qwen2.5:7b` einmalig bis zu 20 kurze Dialogbeispiele und wird danach entladen; Ollama läuft nicht im Chat. Das Training erzeugt `model_all.pt`, das der Smart-Server optional für `/code` lädt; alternativ ist `server_all.py` weiterhin als reiner Modell-Chat verfügbar. Das ist Datendestillation, kein Übertragen von Qwens Gewichten, und macht das eigene Modell nicht so leistungsfähig wie Qwen. Das Training stoppt nicht automatisch bei stagnierendem Validierungsverlust; nur `stop-train.bat`, ein Prozessfehler oder das Ende der 14 Tage beendet den Lauf. Bei einem Prozessfehler versucht der Wächter den gespeicherten Stand erneut zu starten. Der Rechner muss eingeschaltet und am Strom bleiben.

Eclipse-Import: File > Import > Maven > Existing Maven Projects.

## Wichtig: wie gut wird die AI?
Die AI kennt nur das, was in `data/train.txt` steht. Die mitgelieferten Beispiele
(ca. 35 Dialoge) reichen nur, damit der Ablauf funktioniert: Sie wird vor allem die
Beispiele nachplappern und bei neuen Fragen oft Unsinn erzeugen.

So wird sie besser:
- Mehr Daten: tausende Dialoge im Format `User: ...` / `AI: ...` (Leerzeile zwischen Dialogen)
- Länger trainieren (`STEPS` in `train.py`) und mit GPU (CUDA) trainieren
- Größeres Modell (`N_EMBD`, `N_LAYER`) - nur sinnvoll mit genug Daten und GPU
- Später: Wort-/BPE-Tokenizer statt einzelner Zeichen

Die Trainingsdaten musst du selbst schreiben oder sammeln (z. B. eigene Chatlogs,
Texte von dir, Minecraft-Wiki-Inhalte, die du verwenden darfst).
