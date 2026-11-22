from call_function import available_functions
from functions.ask_user import schema_ask_user
from prompts import POLICY_PROMPTS, STUDY_BASE_PROMPT
from study.design import MAX_QUESTIONS, Policy


def build_system_prompt(policy: Policy) -> str:
    return STUDY_BASE_PROMPT + "\n\n" + POLICY_PROMPTS[policy]


def tools_for_policy(policy: Policy) -> list[dict]:
    if policy == Policy.NEVER:
        return list(available_functions)
    return list(available_functions) + [schema_ask_user]


def max_questions_for_policy(policy: Policy) -> int:
    return 0 if policy == Policy.NEVER else MAX_QUESTIONS