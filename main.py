import argparse
import os
import sys

from dotenv import load_dotenv

from agent import run_agent
from config import MAX_ROUNDS, make_client
from prompts import system_prompt


def main():
    parser = argparse.ArgumentParser(description="Chatbot")
    parser.add_argument("user_prompt", type=str, help="User prompt")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--workdir", default="calculator", help="Folder the agent may work in")
    parser.add_argument("--model", default="openrouter/free", help="Model to use")
    parser.add_argument("--max-rounds", type=int, default=MAX_ROUNDS,
                        help="Maximum model requests per run")
    args = parser.parse_args()

    if not os.path.isdir(args.workdir):
        raise RuntimeError(f"Working directory not found: {args.workdir}")

    load_dotenv()
    client = make_client()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": args.user_prompt},
    ]

    if args.verbose:
        print(f"User prompt: {args.user_prompt}")

    stats = run_agent(client, args.model, messages, args.workdir, args.max_rounds,
                      verbose=args.verbose)

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
        print(f"Error: reached the maximum of {args.max_rounds} rounds without a final response. "
              "Try again with --max-rounds 30, or a clearer request.")
        sys.exit(1)

    print("Final response:")
    print(stats["final"])


if __name__ == "__main__":
    main()