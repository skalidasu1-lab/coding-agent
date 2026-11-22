import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from config import child_kwargs, clean_env  # noqa: E402
from study import tasks  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def main():
    # 1. Private data is git-ignored and untracked
    private = [("study_data", "study_data/probe")]
    tasks_in_repo = os.path.realpath(tasks.TASKS_DIR).startswith(os.path.realpath(ROOT) + os.sep)
    if tasks_in_repo:
        private += [("study/tasks", "study/tasks/probe"), ("study/task_bank.py", "study/task_bank.py")]
    for path, probe in private:
        check(f"{path} is git-ignored", git("check-ignore", "-q", probe).returncode == 0)
        tracked = git("ls-files", path).stdout.strip()
        check(f"{path} has no tracked files", tracked == "", tracked.splitlines()[0] if tracked else "")

    # 2. The task bank and the grading
    ids = tasks.task_ids()
    check("task bank has the practice task and six analysed tasks",
          len(ids) == 7 and tasks.PRACTICE_ID in ids, f"found {len(ids)}")
    for task_id in ids:
        solution = os.path.join(tasks.TASKS_DIR, task_id, "solution")
        check(f"reference solution passes the hidden tests: {task_id}",
              tasks.grade(task_id, solution)["passed"])

    # 3. Secrets are not passed to child processes
    os.environ["PREFLIGHT_FAKE_API_KEY"] = "x"
    check("secrets are removed from child environments", "PREFLIGHT_FAKE_API_KEY" not in clean_env())
    del os.environ["PREFLIGHT_FAKE_API_KEY"]

    # 4. Resource limits work
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "big.py")
        with open(script, "w") as f:
            f.write("open('x.bin', 'wb').write(b'0' * (50 * 1024 * 1024))\n")
        outcome = subprocess.run([sys.executable, script], cwd=tmp, capture_output=True, text=True,
                                 timeout=30, env=clean_env(), **child_kwargs())
    check("child processes cannot write huge files", outcome.returncode != 0)

    # 5. Endpoint reminder
    base = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    if "localhost" in base or "127.0.0.1" in base:
        print(f"[INFO] endpoint {base}: local model, no API key is involved")
    else:
        print(f"[INFO] endpoint {base}: the API key is in this machine's environment.")
        print("       Model-written code could in principle read it. Supervise sessions,")
        print("       use a machine or account with nothing private, and report this in the paper.")

    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()