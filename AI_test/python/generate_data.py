import argparse
import json
import os
import random
from urllib.error import URLError
from urllib.request import Request, urlopen

HERE = os.path.dirname(os.path.abspath(__file__))
CHAT_PATH = os.path.join(HERE, "data", "train.txt")
PENDING_PATH = os.path.join(HERE, "data", "generated_pending.txt")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
MAX_ANSWER_BYTES = 256
SEED_QUESTIONS = (
    "Wie lese ich eine Datei zeilenweise in Python?",
    "Was ist ein Generator in Python?",
    "Was unterscheidet eine Liste von einem Tupel in Python?",
    "Wozu dient __name__ == '__main__' in Python?",
    "Wie parse ich JSON in Python?",
    "Was ist ein Type Hint in Python?",
    "Wie sortiere ich eine Liste mit einer eigenen Regel in Python?",
    "Was macht enumerate in einer Python-Schleife?",
    "Wie fange ich eine bestimmte Ausnahme in Python ab?",
    "Was ist ein Decorator in Python?",
    "Was ist der Unterschied zwischen einer Java-Klasse und einem Interface?",
    "Was unterscheidet Overloading und Overriding in Java?",
    "Wozu dient try-with-resources in Java?",
    "Was speichert eine HashMap in Java?",
    "Was bedeuten Generics in Java?",
    "Wofür verwendet man ein Enum in Java?",
    "Was macht die Java Virtual Machine?",
    "Was ist ein Konstruktor in Java?",
    "Was ist der Unterschied zwischen Array und ArrayList in Java?",
    "Was bedeutet package-private in Java?",
    "Was bedeutet der Scope einer Maven-Abhängigkeit?",
    "Was ist der Unterschied zwischen git merge und git rebase?",
    "Wozu dient ein Git-Branch?",
    "Was bedeutet ein Merge-Konflikt in Git?",
    "Was ist ein Minecraft-Chunk?",
    "Warum muss ein Minecraft-Plugin zur Serverversion passen?",
    "Wo finde ich die Ursache eines Minecraft-Serverfehlers?",
    "Was ist ein Permission-Knoten bei einem Server-Plugin?",
    "Was macht ein Redstone-Komparator?",
    "Wie erkennt ein Beobachterblock eine Änderung?",
    "Wozu dient ein Scheduler in einem Minecraft-Plugin?",
    "Warum sollte ein Plugin keine lange Arbeit im Hauptthread ausführen?",
    "Was ist ein Transformer in einem Sprachmodell?",
    "Was bedeutet die Batch-Größe beim Training eines Modells?",
    "Was bewirkt die Lernrate beim Training?",
    "Wozu dient ein Validierungsdatensatz?",
    "Was bedeutet es, wenn der Validierungsverlust steigt?",
    "Was ist Fine-Tuning bei einem Sprachmodell?",
    "Was ist eine Halluzination bei einer AI?",
    "Warum kann ein Sprachmodell trotz flüssiger Sprache falsch liegen?",
)


def read_blocks(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as file:
        text = file.read().replace("\r\n", "\n")
    return [block.strip("\n") for block in text.split("\n\n") if block.strip()]


def teacher_candidates(questions):
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "answer": {"type": "string"},
                    },
                    "required": ["question", "answer"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["items"],
        "additionalProperties": False,
    }
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "keep_alive": 0,
        "format": schema,
        "options": {"temperature": 0.2},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Du erstellst hochwertige deutschsprachige Trainingsbeispiele. "
                    "Beantworte jede vorgegebene Frage sachlich korrekt, direkt und in 1 bis 3 kurzen Sätzen. "
                    "Erfinde keine Details. Gib genau eine Antwort je Frage zurueck und veraendere die Fragen nicht. "
                    "Jede Antwort muss unter 180 Zeichen bleiben."
                ),
            },
            {
                "role": "user",
                "content": "Erstelle Antworten fuer diese Fragen: " + json.dumps(questions, ensure_ascii=False),
            },
        ],
    }
    request = Request(
        OLLAMA_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=240) as response:
        result = json.loads(response.read().decode("utf-8"))
    content = result["message"]["content"]
    return json.loads(content).get("items", [])


def format_candidate(question, answer):
    question = question.strip()
    answer = answer.strip()
    if not question or not answer or "\ufffd" in question + answer:
        return None
    if "\n" in question or "\n" in answer:
        return None
    block = f"User: {question}\nAI: {answer}"
    if len(block.encode("utf-8")) > MAX_ANSWER_BYTES:
        return None
    return block


def teacher_review(candidates):
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "answer": {"type": "string"},
                        "approved": {"type": "boolean"},
                        "reason": {"type": "string"},
                    },
                    "required": ["question", "answer", "approved", "reason"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["items"],
        "additionalProperties": False,
    }
    examples = [
        {"question": block.splitlines()[0][len("User: "):],
         "answer": block.splitlines()[1][len("AI: "):]} 
        for block in candidates
    ]
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "keep_alive": 0,
        "format": schema,
        "options": {"temperature": 0},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Du bist ein strenger technischer Faktenpruefer. Bewerte jedes Beispiel unabhaengig. "
                    "approved ist nur dann true, wenn die Antwort fachlich korrekt, relevant und nicht irrefuehrend ist. "
                    "Bei Unsicherheit, fehlenden wichtigen Unterschieden oder Fehlern muss approved false sein. "
                    "Gib Frage und Antwort exakt unveraendert zurueck."
                ),
            },
            {
                "role": "user",
                "content": "Pruefe diese Trainingsbeispiele: " + json.dumps(examples, ensure_ascii=False),
            },
        ],
    }
    request = Request(
        OLLAMA_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=240) as response:
        result = json.loads(response.read().decode("utf-8"))
    reviewed = json.loads(result["message"]["content"]).get("items", [])
    return {
        (item.get("question", "").strip().casefold(), item.get("answer", "").strip().casefold()): item
        for item in reviewed
        if item.get("approved") is True
    }


def append_blocks(path, blocks):
    if not blocks:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    current = ""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as file:
            current = file.read()
    with open(path, "a", encoding="utf-8", newline="\n") as file:
        if current and not current.endswith("\n\n"):
            file.write("\n" if current.endswith("\n") else "\n\n")
        file.write("\n\n".join(blocks) + "\n\n")


def auto_train_check(candidate, known_answers, reviewed):
    question, answer_line = candidate.splitlines()
    answer = answer_line[len("AI: "):].strip()
    if len(answer) < 20:
        return False, "Antwort zu kurz"
    if answer.casefold() in known_answers:
        return False, "Antwort kommt bereits im Datensatz vor"
    if any(phrase in answer.casefold() for phrase in ("weiß ich nicht", "nicht gelernt", "kann ich nicht")):
        return False, "Antwort ist eine Wissenslücke oder Verweigerung"
    review_key = (question[len("User: "):].strip().casefold(), answer.casefold())
    if review_key not in reviewed:
        return False, "nicht vom Faktenprüfer bestätigt"
    return True, reviewed[review_key].get("reason", "vom Faktenprüfer bestätigt")


def main():
    parser = argparse.ArgumentParser(description="Erzeugt Trainingsdialoge mit Ollama als Teacher; Ollama wird danach entladen.")
    parser.add_argument("--preview", action="store_true", help="Zeigt Kandidaten, ohne Dateien zu ändern.")
    parser.add_argument("--count", type=int, default=20, help="Maximale Kandidatenzahl (1 bis 40).")
    args = parser.parse_args()
    if not 1 <= args.count <= len(SEED_QUESTIONS):
        parser.error(f"--count muss zwischen 1 und {len(SEED_QUESTIONS)} liegen.")

    if args.preview:
        print(f"Vorschau: Ollama-Teacher {OLLAMA_MODEL}; es werden keine Dateien geändert.")

    known_blocks = set(read_blocks(CHAT_PATH)) | set(read_blocks(PENDING_PATH))
    known_questions = {
        block.splitlines()[0].casefold()
        for block in known_blocks
        if block.startswith("User: ") and "\n" in block
    }
    known_answers = {
        block.splitlines()[1][len("AI: "):].strip().casefold()
        for block in known_blocks
        if len(block.splitlines()) == 2 and block.splitlines()[1].startswith("AI: ")
    }
    available_questions = [
        question for question in SEED_QUESTIONS
        if f"User: {question}".casefold() not in known_questions
    ]
    questions = random.SystemRandom().sample(available_questions, min(args.count, len(available_questions)))
    if not questions:
        print("Keine neuen Seed-Fragen vorhanden; Trainingsdaten bleiben unverändert.")
        return

    candidates = []
    try:
        generated = teacher_candidates(questions)
    except (URLError, TimeoutError, OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"Ollama konnte keine Trainingsbeispiele erzeugen: {error}")
        print("Es wird keine Antwort des eigenen Modells als Ersatz verwendet.")
        return

    requested = {question.casefold(): question for question in questions}
    for item in generated:
        question_text = item.get("question", "").strip()
        answer = item.get("answer", "")
        question = requested.get(question_text.casefold())
        if question is None:
            continue
        candidate = format_candidate(question, answer)
        if candidate is None or candidate in known_blocks:
            continue
        candidates.append(candidate)
        known_blocks.add(candidate)

    try:
        reviewed = teacher_review(candidates) if candidates else {}
    except (URLError, TimeoutError, OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"Ollama-Faktenprüfung fehlgeschlagen; nichts wird automatisch übernommen: {error}")
        if not args.preview:
            append_blocks(PENDING_PATH, candidates)
        return

    print(f"Ollama-Teacher: {OLLAMA_MODEL}")
    if not candidates:
        print("Keine neuen Kandidaten erzeugt; Trainingsdaten bleiben unverändert.")
        return
    print(f"Neue Kandidaten: {len(candidates)} von maximal {args.count}.")

    accepted = []
    rejected = []
    for candidate in candidates:
        is_acceptable, reason = auto_train_check(candidate, known_answers, reviewed)
        if args.preview:
            label = "AUTO-ÜBERNEHMEN" if is_acceptable else "ABLEHNEN"
            print(f"\n[{label}: {reason}]\n{candidate}")
        if is_acceptable:
            accepted.append(candidate)
            known_answers.add(candidate.splitlines()[1][len("AI: "):].strip().casefold())
        else:
            rejected.append(candidate)

    if args.preview:
        return

    append_blocks(PENDING_PATH, rejected)
    append_blocks(CHAT_PATH, accepted)
    print(f"Automatisch übernommen: {len(accepted)} | Zur Sicherheit zurückgestellt: {len(rejected)}.")
    if rejected:
        print(f"Zurückgestellte Entwürfe: {PENDING_PATH}")


if __name__ == "__main__":
    main()