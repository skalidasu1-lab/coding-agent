# coding-agent

[![tests](https://github.com/skalidasu1-lab/coding-agent/actions/workflows/tests.yml/badge.svg)](https://github.com/skalidasu1-lab/coding-agent/actions/workflows/tests.yml)

A small AI coding agent. Give it a task in plain English, and it decides which tools to use, runs them, reads the results, and repeats until it has an answer. It can list, read, write and run files inside one folder that you choose.

Started from Boot.dev's "Build an AI Agent" course and extended with hardened tools, error handling, a configurable working folder, and unit tests.

![demo](docs/demo.gif)

## How it works

1. The program sends the conversation and the tool descriptions to the model.
2. The model replies with either text (the final answer) or tool calls.
3. The program runs each requested tool and adds the result to the conversation.
4. The loop repeats, up to a fixed number of rounds, until the model answers with text.

| Tool | Purpose |
| --- | --- |
| `get_files_info` | List files and sizes in a folder |
| `get_file_content` | Read a file (truncated at 10,000 characters) |
| `write_file` | Create or overwrite a file |
| `run_python_file` | Run a Python file with a 30-second timeout |

## Setup

```bash
git clone https://github.com/skalidasu1-lab/coding-agent.git
cd coding-agent
uv sync
cp .env.example .env   # then put your OpenRouter key in .env
```

## Usage

```bash
uv run main.py "how does the calculator render results?" --verbose
uv run main.py "Fix the bug: 3 + 7 * 2 shouldn't be 20." --workdir calculator
```

Use `--workdir` to choose the folder the agent may touch. Work on a copy of any project and commit first, so you can undo changes.

## Tests

```bash
uv run python -m unittest discover -s tests -t . -v
```

The tests check the path guardrails: `../` traversal, absolute paths, sibling folders with a similar name, symlinks, truncation, and that API keys are not passed to code the agent runs. They do not call the model.

## Limitations and safety

- This is a learning project. The agent can run Python code it writes, and the folder check restricts tool arguments, **not what a running script can do**. It is not a sandbox.
- Do not point it at important folders, and do not expose it to other users.
- Quality depends on the model. The free `openrouter/free` model is inconsistent, and free accounts have a daily request limit.
- `write_file` replaces whole files, so long files can lose content when rewritten.