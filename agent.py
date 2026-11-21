import json
import time

from openai import RateLimitError

from call_function import available_functions, call_function

ASK_TOOL_NAME = "ask_user"


def handle_question(tool_call, ask_callback, max_questions, stats):
    def reply(text):
        return {"role": "tool", "tool_call_id": tool_call.id, "content": text}

    try:
        arguments = json.loads(tool_call.function.arguments or "{}")
        question = str(arguments["question"]).strip()
    except (json.JSONDecodeError, KeyError, TypeError):
        return reply("Error: ask_user needs a JSON object with a 'question' string.")
    if not question:
        return reply("Error: the question was empty.")
    if ask_callback is None or len(stats["questions"]) >= max_questions:
        return reply("Error: no more questions are allowed. Use your best judgment and continue.")

    answer = ask_callback(question)
    stats["questions"].append({"question": question, "answer": answer})
    return reply(answer)


def run_agent(client, model, messages, workdir, max_rounds, verbose=False, tools=None,
              temperature=0, ask_callback=None, max_questions=0):
    """Run the tool-calling loop and return a dict describing what happened."""
    tools = available_functions if tools is None else tools
    allowed = {tool["function"]["name"] for tool in tools}
    stats = {
        "finished": False,
        "final": None,
        "error": None,
        "rounds": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "questions": [],
        "per_round": [],
    }
    seen_calls: dict[tuple[str, str], int] = {}

    for _ in range(max_rounds):
        started = time.time()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                temperature=temperature,
            )
        except RateLimitError:
            stats["error"] = "rate_limit"
            return stats
        elapsed = round(time.time() - started, 2)

        round_prompt = round_completion = 0
        if response.usage is not None:
            round_prompt = response.usage.prompt_tokens
            round_completion = response.usage.completion_tokens
        stats["rounds"] += 1
        stats["prompt_tokens"] += round_prompt
        stats["completion_tokens"] += round_completion
        stats["per_round"].append({
            "prompt_tokens": round_prompt,
            "completion_tokens": round_completion,
            "seconds": elapsed,
        })

        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            stats["final"] = message.content
            stats["finished"] = True
            return stats

        for tool_call in message.tool_calls:
            name = tool_call.function.name

            if name not in allowed:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": f"Error: Unknown function: {name}",
                })
                continue

            if name == ASK_TOOL_NAME:
                messages.append(handle_question(tool_call, ask_callback, max_questions, stats))
                continue

            key = (name, tool_call.function.arguments)
            seen_calls[key] = seen_calls.get(key, 0) + 1
            if seen_calls[key] > 2:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": "Error: you already made this exact call several times. Use the earlier results and give your final answer.",
                })
                continue

            result_message = call_function(tool_call, working_directory=workdir, verbose=verbose)
            if not result_message["content"]:
                result_message["content"] = "Error: the tool returned no content."
            if verbose:
                print(f"-> {result_message['content']}")
            messages.append(result_message)

    return stats