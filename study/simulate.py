import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

from config import make_client  # noqa: E402
from study.design import CELLS  # noqa: E402
from study.logger import SESSIONS_FILE, append_jsonl, read_jsonl  # noqa: E402
from study.scripted_student import ScriptedStudent  # noqa: E402
from study.session import run_task_session  # noqa: E402
from study.tasks import analysed_task_ids, load_task  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Run scripted students through the study conditions")
    parser.add_argument("--model", required=True)
    parser.add_argument("--data-dir", default=os.path.join("study_data", "simulation"))
    parser.add_argument("--tasks", nargs="*", default=analysed_task_ids())
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--limit", type=int, default=2, help="Maximum sessions in this call")
    args = parser.parse_args()

    load_dotenv()
    client = make_client()
    path = os.path.join(args.data_dir, SESSIONS_FILE)
    done = {
        (r["task_id"], r["policy"], r["clarity"], r["repeat"])
        for r in read_jsonl(path) if not r["technical_failure"]
    }

    ran = 0
    for repeat in range(args.repeats):
        for task_id in args.tasks:
            task = load_task(task_id)
            for policy, clarity in CELLS:
                if (task_id, policy.value, clarity.value, repeat) in done:
                    continue
                if ran >= args.limit:
                    print("Reached --limit. Run the same command again to continue.")
                    return
                record = run_task_session(client, args.model, task, policy, clarity,
                                          ScriptedStudent(task), participant_id="SIM", temperature=0)
                record["repeat"] = repeat
                append_jsonl(path, record)
                ran += 1
                print(f"{task_id} {policy.value}/{clarity.value} repeat {repeat}: "
                      f"passed={record['passed']} tokens={record['total_tokens']} "
                      f"questions={record['n_questions']} ({record['end_reason']})")
                if record["failure"] == "rate_limit":
                    print("Rate limit reached. Try again later.")
                    return
    print("All requested sessions are done.")


if __name__ == "__main__":
    main()