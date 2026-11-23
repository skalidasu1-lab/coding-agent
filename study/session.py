import os
import shutil
import tempfile
import time
from datetime import datetime, timezone

from agent import run_agent
from study.conditions import build_system_prompt, max_questions_for_policy, tools_for_policy
from study.design import MAX_AGENT_ROUNDS, MAX_STUDENT_PROMPTS, TASK_TIME_LIMIT_SECONDS
from study.safety import flag_suspicious
from study.tasks import grade


def run_task_session(client, model, task, policy, clarity, student, participant_id="",
                     position=0, temperature=0, keep_dir=None, clock=time.time) -> dict:
    """Run one task with one student and return a record for the log."""
    started = clock()
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    messages = [{"role": "system", "content": build_system_prompt(policy)}]
    tools = tools_for_policy(policy)
    max_questions = max_questions_for_policy(policy)

    prompts: list[str] = []
    questions: list[dict] = []
    per_round: list[dict] = []
    tool_log: list[dict] = [] 
    round_cap_hits = 0
    prompt_tokens = completion_tokens = rounds = 0
    final_text = None
    end_reason = None
    failure = None

    with tempfile.TemporaryDirectory() as tmp:
        project = os.path.join(tmp, "project")
        os.makedirs(project)

        prompt = student.first_prompt(task, clarity)
        while True:
            prompts.append(prompt)
            messages.append({"role": "user", "content": prompt})
            try:
                stats = run_agent(
                    client, model, messages, project, MAX_AGENT_ROUNDS,
                    tools=tools, temperature=temperature,
                    ask_callback=student.answer,
                    max_questions=max(0, max_questions - len(questions)),
                )
            except Exception as e:
                failure = f"{type(e).__name__}: {e}"
                end_reason = "technical_failure"
                break

            prompt_tokens += stats["prompt_tokens"]
            completion_tokens += stats["completion_tokens"]
            rounds += stats["rounds"]
            questions.extend(stats["questions"])
            per_round.extend(stats["per_round"])
            tool_log.extend(stats["tool_log"])
            round_cap_hits += int(stats.get("hit_round_cap", False))

            if stats["error"] == "rate_limit":
                failure = "rate_limit"
                end_reason = "technical_failure"
                break

            final_text = stats["final"]
            if len(prompts) >= MAX_STUDENT_PROMPTS:
                end_reason = "max_prompts"
                break
            if clock() - started >= TASK_TIME_LIMIT_SECONDS:
                end_reason = "time_limit"
                break

            follow_up = student.review(final_text, project)
            if follow_up is None:
                end_reason = "student_done"
                break
            prompt = follow_up

        result = grade(task["id"], project)
        if keep_dir:
            shutil.copytree(project, keep_dir, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))

    wall_seconds = round(clock() - started, 1)
    rating = None if failure else student.rating()

    return {
        "participant_id": participant_id,
        "position": position,
        "task_id": task["id"],
        "policy": policy.value,
        "clarity": clarity.value,
        "model": model,
        "temperature": temperature,
        "started_at": started_at,
        "wall_seconds": wall_seconds,
        "agent_seconds": round(sum(r["seconds"] for r in per_round), 2),
        "student_prompts": len(prompts),
        "prompts": prompts,
        "n_questions": len(questions),
        "questions": questions,
        "rounds": rounds,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "per_round": per_round,
        "final_response": final_text,
        "end_reason": end_reason,
        "technical_failure": failure is not None,
        "failure": failure,
        "passed": result["passed"],
        "score": result["score"],
        "tests_ran": result["ran"],
        "rating": rating,
        "program_runs": getattr(student, "program_runs", None),
        "tool_log": tool_log,
        "suspicious": flag_suspicious(tool_log),
        "round_cap_hits": round_cap_hits,
    }