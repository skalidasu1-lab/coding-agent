import os
from datetime import datetime, timezone

from study.design import assignment
from study.logger import PARTICIPANTS_FILE, append_jsonl, read_jsonl


def register_participant(data_dir: str, task_ids: list[str]) -> dict:
    """Create the next participant (P001, P002, ...) with a counterbalanced plan."""
    if len(task_ids) != 6:
        raise ValueError("The design needs exactly 6 analysed tasks.")
    path = os.path.join(data_dir, PARTICIPANTS_FILE)
    index = len(read_jsonl(path))
    plan = [
        {"position": position, "task_id": task_ids[position],
         "policy": policy.value, "clarity": clarity.value}
        for position, policy, clarity in assignment(index)
    ]
    record = {
        "participant_id": f"P{index + 1:03d}",
        "index": index,
        "sequence": index % 6,
        "plan": plan,
        "registered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    append_jsonl(path, record)
    return record


def find_participant(data_dir: str, participant_id: str) -> dict | None:
    for record in read_jsonl(os.path.join(data_dir, PARTICIPANTS_FILE)):
        if record["participant_id"] == participant_id:
            return record
    return None