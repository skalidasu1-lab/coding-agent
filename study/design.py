from enum import Enum


class Policy(str, Enum):
    NEVER = "never_ask"
    WHEN_UNCLEAR = "ask_when_unclear"
    ALWAYS = "always_ask"


class Clarity(str, Enum):
    VAGUE = "vague"
    CLEAR = "clear"


CELLS = [(policy, clarity) for clarity in Clarity for policy in Policy]  # 6 cells

MAX_QUESTIONS = 3
MAX_STUDENT_PROMPTS = 8
MAX_AGENT_ROUNDS = 15
TASK_TIME_LIMIT_SECONDS = 12 * 60


def williams_row(n: int, k: int) -> list[int]:
    """Row k of a Williams design for even n: balanced for position and for
    which condition comes immediately before which."""
    first = [0]
    low, high = 1, n - 1
    take_low = True
    while len(first) < n:
        if take_low:
            first.append(low)
            low += 1
        else:
            first.append(high)
            high -= 1
        take_low = not take_low
    return [(x + k) % n for x in first]


def assignment(participant_index: int) -> list[tuple[int, Policy, Clarity]]:
    """Returns (task_index, policy, clarity) for each of the 6 positions."""
    n = len(CELLS)
    row = williams_row(n, participant_index % n)
    result = []
    for position in range(n):
        policy, clarity = CELLS[row[position]]
        result.append((position, policy, clarity))
    return result