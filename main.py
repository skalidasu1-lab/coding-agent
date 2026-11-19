import argparse
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

from agent import run_agent
from config import MAX_ROUNDS
from prompts import system_prompt


def main():
    parser = argparse.ArgumentParser(description="Chatbot")
    parser.add_argument("user_prompt", type=str, help="User prompt")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--workdir", default="calculator", help="Folder the agent may work in")
    parser.add_argument("--model", default="openrouter/free", help="Model to use")
    args = parser.parse_args()

    if not os.path.isdir(args.workdir):
        raise RuntimeError(f"Working directory not found: {args.workdir}")

    load_dotenv()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if api_key is None:
        raise RuntimeError("OPENROUTER_API_KEY not found. Check your .env file.")

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": args.user_prompt},
    ]

    if args.verbose:
        print(f"User prompt: {args.user_prompt}")

    stats = run_agent(client, args.model, messages, args.workdir, MAX_ROUNDS, verbose=args.verbose)

    if args.verbose:
        print(
            f"Rounds: {stats['rounds']}, "
            f"Prompt tokens: {stats['prompt_tokens']}, "
            f"Response tokens: {stats['completion_tokens']}"
        )

    if stats["error"] == "rate_limit":
        print("Error: OpenRouter rate limit reached (probably the free daily limit). Try again later.")
        sys.exit(1)

    if not stats["finished"]:
        print("Error: reached the maximum number of rounds without a final response.")
        sys.exit(1)

    print("Final response:")
    print(stats["final"])


if __name__ == "__main__":
    main()