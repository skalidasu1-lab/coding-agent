import argparse
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
from config import MAX_ROUNDS
from prompts import system_prompt
from call_function import available_functions, call_function


def main():
    parser = argparse.ArgumentParser(description="Chatbot")
    parser.add_argument("user_prompt", type=str, help="User prompt")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--workdir", default="calculator", help="Folder the agent may work in")
    args = parser.parse_args()

    if not os.path.isdir(args.workdir):
        raise RuntimeError(f"Working directory not found: {args.workdir}")

    load_dotenv()
    api_key = os.environ.get("OPENROUTER_API_KEY")

    if api_key is None:
        raise RuntimeError("OPENROUTER_API_KEY not found. Check your .env file.")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": args.user_prompt},
    ]

    if args.verbose:
        print(f"User prompt: {args.user_prompt}")

    seen_calls: dict[tuple[str, str], int] = {}

    for _ in range(MAX_ROUNDS):
        try:
            response = client.chat.completions.create(
                model="openrouter/free",
                messages=messages,
                tools=available_functions,
                temperature=0,
            )
        except RateLimitError:
            print("Error: OpenRouter rate limit reached (probably the free daily limit). Try again later.")
            sys.exit(1)

        if response.usage is None:
            raise RuntimeError("No usage data in the response. The API request may have failed.")

        if args.verbose:
            print(f"Prompt tokens: {response.usage.prompt_tokens}")
            print(f"Response tokens: {response.usage.completion_tokens}")

        message = response.choices[0].message
        messages.append(message)

        if message.tool_calls:
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

                result_message = call_function(
                    tool_call, working_directory=args.workdir, verbose=args.verbose
                )
                if not result_message["content"]:
                    raise RuntimeError("Tool call returned no content.")
                if args.verbose:
                    print(f"-> {result_message['content']}")
                messages.append(result_message)
        else:
            print("Final response:")
            print(message.content)
            return

    print("Error: reached the maximum number of rounds without a final response.")
    sys.exit(1)


if __name__ == "__main__":
    main()