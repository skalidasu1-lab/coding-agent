import math

import numpy as np

from study.design import Clarity, Policy, assignment

TASKS = [f"t{i}" for i in range(1, 7)]


def fake_records(n_participants: int = 30, seed: int = 0) -> list[dict]:
    """Synthetic sessions in the real log format. For testing the analysis only."""
    rng = np.random.default_rng(seed)
    records = []
    for p in range(n_participants):
        person = rng.normal(0, 0.2)
        for position, policy, clarity in assignment(p):
            asks = policy != Policy.NEVER
            vague = clarity == Clarity.VAGUE
            effect = -0.22 if (vague and asks) else 0.0
            tokens = int(4000 * math.exp(person + effect + 0.03 * position + rng.normal(0, 0.1)))
            p_success = 0.8 if (asks or not vague) else 0.5
            records.append({
                "participant_id": f"P{p + 1:03d}",
                "position": position,
                "task_id": TASKS[position],
                "policy": policy.value,
                "clarity": clarity.value,
                "total_tokens": tokens,
                "passed": bool(rng.random() < p_success),
                "n_questions": int(rng.integers(1, 4)) if asks else 0,
                "student_prompts": int(rng.integers(1, 4)),
                "wall_seconds": float(rng.normal(420, 60)),
                "rating": int(rng.integers(2, 6)),
                "technical_failure": False,
                "prompts": ["make the program"],
            })
    return records