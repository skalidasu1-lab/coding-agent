import json
import os

SESSIONS_FILE = "sessions.jsonl"
PARTICIPANTS_FILE = "participants.jsonl"


def append_jsonl(path: str, record: dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def read_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]