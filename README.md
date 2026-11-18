# coding-agent

A small AI coding agent that can read, write and run Python code. Given a task in plain English, it decides which tools to use, runs them, looks at the results, and keeps going until it has an answer.

Built while following the Boot.dev "Build an AI Agent" course, using Python, the `openai` SDK and [OpenRouter](https://openrouter.ai).

## How it works

The agent runs in a loop. Each round it sends the whole conversation to the model, and the model either asks to call a tool or gives a final answer. The program runs the requested tool, adds the result to the conversation, and asks again. The loop is capped at 20 rounds.

Tools the model can call:

- `get_files_info`: list files in a directory
- `get_file_content`: read a file (truncated at 10,000 characters)
- `write_file`: create or overwrite a file
- `run_python_file`: run a Python file (30-second timeout)

## Safety

- All tools are restricted to the `calculator/` folder. Paths are checked, so the model cannot read or write anywhere else.
- The working directory is set by the program, never by the model.
- Even so, this is a **learning project**. It can run arbitrary Python code. Do not use it on anything important and do not give it to other people to use.

## Setup

1. Install [uv](https://docs.astral.sh/uv/).
2. Clone the repo and install dependencies:
   ```bash
   git clone https://github.com/skalidasu1-lab/coding-agent.git
   cd coding-agent
   uv sync
   ```
3. Create an API key on OpenRouter and put it in a `.env` file in the project root:
   ```
   OPENROUTER_API_KEY='your_key_here'
   ```

## Usage

```bash
uv run main.py "how does the calculator render results to the console?"
uv run main.py "Fix the bug: 3 + 7 * 2 shouldn't be 20." --verbose
```

`--verbose` prints the prompt, token counts, and each tool call with its result.

## Project layout

- `main.py`: command-line entry point and the agent loop
- `call_function.py`: tool schemas and the dispatcher that runs tool calls
- `prompts.py`: the system prompt
- `functions/`: the four tools
- `calculator/`: a small calculator app the agent works on