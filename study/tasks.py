import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

from config import clean_env

TASKS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks")
FALLBACK_ANSWER = "No preference, use your best judgment."
PRACTICE_ID = "t0_practice"


def task_ids() -> list[str]:
    if not os.path.isdir(TASKS_DIR):
        return []
    return sorted(
        name for name in os.listdir(TASKS_DIR)
        if os.path.isdir(os.path.join(TASKS_DIR, name))
    )
def analysed_task_ids() -> list[str]:
    """The six tasks used in the analysis (the practice task is excluded)."""
    return [t for t in task_ids() if t != PRACTICE_ID]


def load_task(task_id: str) -> dict:
    with open(os.path.join(TASKS_DIR, task_id, "task.json")) as f:
        return json.load(f)


def canned_answer(task: dict, question: str) -> str:
    """Scripted student: answers every ambiguity whose keywords appear in the question."""
    lowered = question.lower()
    answers = [
        item["answer"]
        for item in task["ambiguities"]
        if any(keyword in lowered for keyword in item["keywords"])
    ]
    return " ".join(answers) if answers else FALLBACK_ANSWER


def grade(task_id: str, project_dir: str) -> dict:
    """Run the hidden tests against a copy of project_dir. The tests are never
    placed in the folder the agent works in."""
    hidden = os.path.join(TASKS_DIR, task_id, "hidden_tests", "test_hidden.py")
    with tempfile.TemporaryDirectory() as tmp:
        work = os.path.join(tmp, "work")
        shutil.copytree(project_dir, work, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(hidden, os.path.join(work, "test_hidden.py"))
        try:
            result = subprocess.run(
                [sys.executable, "-m", "unittest", "test_hidden"],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=60,
                env=clean_env(),
            )
        except subprocess.TimeoutExpired:
            return {"passed": False, "score": 0.0, "ran": 0, "failed": 0, "timeout": True}

    report = result.stderr
    ran_match = re.search(r"Ran (\d+) test", report)
    ran = int(ran_match.group(1)) if ran_match else 0
    failed = 0
    failed_match = re.search(r"FAILED \(([^)]*)\)", report)
    if failed_match:
        failed = sum(int(n) for n in re.findall(r"=(\d+)", failed_match.group(1)))
    score = (ran - failed) / ran if ran else 0.0
    return {
        "passed": result.returncode == 0 and ran > 0,
        "score": round(score, 3),
        "ran": ran,
        "failed": failed,
        "timeout": False,
    }
