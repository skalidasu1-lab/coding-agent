from openai import RateLimitError

from call_function import available_functions, call_function


def run_agent(client, model, messages, workdir, max_rounds, verbose=False, tools=None, temperature=0):
    """Run the tool-calling loop and return a dict describing what happened."""
    tools = available_functions if tools is None else tools
    stats = {
        "finished": False,
        "final": None,
        "error": None,
        "rounds": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
    }
    seen_calls: dict[tuple[str, str], int] = {}

    for _ in range(max_rounds):
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

        stats["rounds"] += 1
        if response.usage is not None:
            stats["prompt_tokens"] += response.usage.prompt_tokens
            stats["completion_tokens"] += response.usage.completion_tokens

        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            stats["final"] = message.content
            stats["finished"] = True
            return stats

        for tool_call in message.tool_calls:
            key = (tool_call.function.name, tool_call.function.arguments)
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