import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

from config import make_client  # noqa: E402
from study.design import Clarity, Policy  # noqa: E402
from study.logger import SESSIONS_FILE, append_jsonl, read_jsonl  # noqa: E402
from study.participants import find_participant, register_participant  # noqa: E402
from study.session import run_task_session  # noqa: E402
from study.tasks import PRACTICE_ID, analysed_task_ids, load_task  # noqa: E402
from study.terminal_student import TerminalStudent  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Run one participant through the study")
    parser.add_argument("--model", required=True)
    parser.add_argument("--data-dir", default="study_data")
    parser.add_argument("--participant-id", help="Resume an existing participant")
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--skip-practice", action="store_true")
    args = parser.parse_args()

    load_dotenv()
    client = make_client()

    if args.participant_id:
        participant = find_participant(args.data_dir, args.participant_id)
        if participant is None:
            sys.exit(f"Unknown participant: {args.participant_id}")
    else:
        participant = register_participant(args.data_dir, analysed_task_ids())

    pid = participant["participant_id"]
    sessions_path = os.path.join(args.data_dir, SESSIONS_FILE)
    print(f"\nParticipant ID: {pid}  (the participant enters this in the survey forms)")
    input("Check that the consent form is signed and the pre-survey is done, then press Enter... ")

    if not args.skip_practice:
        print("\nPractice task (not recorded). Try /run, /files and /done.")
        run_task_session(client, args.model, load_task(PRACTICE_ID), Policy.WHEN_UNCLEAR,
                         Clarity.VAGUE, TerminalStudent(), participant_id=pid,
                         temperature=args.temperature)

    finished = {
        r["position"] for r in read_jsonl(sessions_path)
        if r["participant_id"] == pid and not r["technical_failure"]
    }
    for step in participant["plan"]:
        if step["position"] in finished:
            continue
        task = load_task(step["task_id"])
        while True:
            record = run_task_session(
                client, args.model, task, Policy(step["policy"]), Clarity(step["clarity"]),
                TerminalStudent(), participant_id=pid, position=step["position"],
                temperature=args.temperature,
                keep_dir=os.path.join(args.data_dir, "projects", f"{pid}_pos{step['position']}"),
            )
            append_jsonl(sessions_path, record)
            if not record["technical_failure"]:
                break
            print("\nA technical problem occurred:", record["failure"])
            if input("Retry this task? [y/N] ").strip().lower() != "y":
                break
        print(f"\nTask {step['position'] + 1} of {len(participant['plan'])} finished.")

    print(f"\nAll tasks done. Ask {pid} to complete the post-survey with this ID.")


if __name__ == "__main__":
    main()