import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv  # noqa: E402
from openai import OpenAI  # noqa: E402

from agent import run_agent  # noqa: E402
from call_function import available_functions  # noqa: E402
from config import MAX_ROUNDS, clean_env  # noqa: E402
from prompts import system_prompt  # noqa: E402

TASKS_DIR = os.path.join(ROOT, "evals", "tasks")
RESULTS_FILE = os.path.join(ROOT, "evals", "results.jsonl")


def tests_pass(project_dir):
    try:
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=60,
            env=clean_env(),
        )
    except subprocess.TimeoutExpired:
        return False
    return result.returncode == 0


def copy_task(task_name, destination):
    shutil.copytree(
        os.path.join(TASKS_DIR, task_name, "project"),
        destination,
        ignore=shutil.ignore_patterns("__pycache__"),
    )


def load_results():
    if not os.path.exists(RESULTS_FILE):
        return []
    with open(RESULTS_FILE) as f:
        return [json.loads(line) for line in f if line.strip()]


def save_result(record):
    with open(RESULTS_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")


def run_task(client, model, variant, task_name, tools, prompt_text, max_rounds):
    with open(os.path.join(TASKS_DIR, task_name, "prompt.txt")) as f:
        user_prompt = f.read().strip()

    record = {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model,
        "variant": variant,
        "task": task_name,
        "status": "ok",
        "passed": False,
        "finished": False,
        "rounds": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "seconds": 0.0,
        "error": None,
    }

    with tempfile.TemporaryDirectory() as tmp:
        project = os.path.join(tmp, "project")
        copy_task(task_name, project)

        if tests_pass(project):
            record["status"] = "invalid_task"
            return record

        messages = [
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": user_prompt},
        ]
        start = time.time()
        try:
            stats = run_agent(client, model, messages, project, max_rounds, tools=tools)
        except Exception as e:
            record["status"] = "error"
            record["error"] = f"{type(e).__name__}: {e}"
            return record
        record["seconds"] = round(time.time() - start, 1)

        if stats["error"] == "rate_limit":
            return None

        record["finished"] = stats["finished"]
        record["rounds"] = stats["rounds"]
        record["prompt_tokens"] = stats["prompt_tokens"]
        record["completion_tokens"] = stats["completion_tokens"]
        record["passed"] = tests_pass(project)

    return record


def check_tasks(names):
    """Confirm every task's tests fail before the agent touches it. Uses no model requests."""
    for name in names:
        with tempfile.TemporaryDirectory() as tmp:
            project = os.path.join(tmp, "project")
            copy_task(name, project)
            status = "tests FAIL as expected" if not tests_pass(project) else "PROBLEM: tests already pass"
        print(f"{name}: {status}")


def print_report():
    latest = {}
    for r in load_results():
        if r["status"] == "ok":
            latest[(r["model"], r["variant"], r["task"])] = r

    groups = {}
    for (model, variant, _task), r in latest.items():
        groups.setdefault((model, variant), []).append(r)

    print("| Model | Tools | Fixed | Avg rounds | Avg tokens |")
    print("| --- | --- | --- | --- | --- |")
    for (model, variant), rows in sorted(groups.items()):
        fixed = sum(1 for r in rows if r["passed"])
        avg_rounds = sum(r["rounds"] for r in rows) / len(rows)
        avg_tokens = sum(r["prompt_tokens"] + r["completion_tokens"] for r in rows) / len(rows)
        print(f"| {model} | {variant} | {fixed}/{len(rows)} | {avg_rounds:.1f} | {avg_tokens:.0f} |")

    columns = sorted(groups)
    tasks = sorted({task for (_m, _v, task) in latest})
    print()
    print("| Task | " + " | ".join(f"{m} ({v})" for m, v in columns) + " |")
    print("| --- |" + " --- |" * len(columns))
    for task in tasks:
        cells = []
        for m, v in columns:
            r = latest.get((m, v, task))
            cells.append("-" if r is None else ("pass" if r["passed"] else "fail"))
        print(f"| {task} | " + " | ".join(cells) + " |")


def main():
    parser = argparse.ArgumentParser(description="Run the agent on small bug-fixing tasks")
    parser.add_argument("--model", default="openrouter/free")
    parser.add_argument("--tasks", nargs="*", help="Task folder names (default: all)")
    parser.add_argument("--max-rounds", type=int, default=MAX_ROUNDS)
    parser.add_argument("--disable-tools", nargs="*", default=[], help="Tool names to hide from the model")
    parser.add_argument("--rerun", action="store_true", help="Run tasks that already have a result")
    parser.add_argument("--check", action="store_true", help="Check the tasks fail at baseline, then exit")
    parser.add_argument("--report", action="store_true", help="Print the results tables, then exit")
    args = parser.parse_args()

    names = args.tasks or sorted(os.listdir(TASKS_DIR))

    if args.check:
        check_tasks(names)
        return
    if args.report:
        print_report()
        return

    load_dotenv()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if api_key is None:
        raise RuntimeError("OPENROUTER_API_KEY not found. Check your .env file.")
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    variant = "all tools" if not args.disable_tools else "without " + ", ".join(args.disable_tools)
    tools = [t for t in available_functions if t["function"]["name"] not in args.disable_tools]
    prompt_text = "\n".join(
        line
        for line in system_prompt.splitlines()
        if not any(tool in line for tool in args.disable_tools)
    )

    done = {
        r["task"]
        for r in load_results()
        if r["model"] == args.model and r["variant"] == variant and r["status"] == "ok"
    }

    for name in names:
        if name in done and not args.rerun:
            print(f"skip {name} (already has a result for this model and tool set)")
            continue

        record = run_task(client, args.model, variant, name, tools, prompt_text, args.max_rounds)
        if record is None:
            print("Rate limit reached. Run the same command again later; finished tasks are kept.")
            break

        save_result(record)
        outcome = "PASSED" if record["passed"] else "failed"
        print(f"{name}: {outcome} ({record['status']}, {record['rounds']} rounds, {record['seconds']}s)")


if __name__ == "__main__":
    main()