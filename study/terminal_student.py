import os
import shlex
import subprocess
import sys

from config import child_kwargs, clean_env
from study.design import Clarity

CLARITY_INSTRUCTIONS = {
    Clarity.VAGUE: "Write your request in ONE short sentence, the way you would in a quick chat.",
    Clarity.CLEAR: "Describe the whole program completely, listing every requirement.",
}

HELP = ("Type your next request, or: /run <arguments> to try the program, "
        "/files to list files, /done if the program does what you wanted.")


class TerminalStudent:
    """The student side of a session, in the terminal."""

    def __init__(self, input_fn=input, output_fn=print):
        self.inp = input_fn
        self.out = output_fn
        self.program_runs = 0

    def _read(self, prompt: str) -> str:
        while True:
            text = self.inp(prompt).strip()
            if text:
                return text

    def first_prompt(self, task, clarity):
        self.out(f"\n=== Task: {task['title']} ===")
        self.out("What you want:\n" + task["intent"])
        self.out("\n" + CLARITY_INSTRUCTIONS[clarity])
        text = self._read("Your request> ")
        self.out("(The assistant is working. This can take a minute.)")
        return text

    def answer(self, question):
        self.out(f"\nThe assistant asks: {question}")
        return self._read("Your answer> ")

    def review(self, final, project_dir):
        self.out("\nAssistant: " + (final or "(The assistant did not finish.)"))
        self.out(HELP)
        while True:
            line = self.inp("> ").strip()
            if not line:
                continue
            lowered = line.lower()
            if lowered == "/done":
                return None
            if lowered == "/files":
                self.out("\n".join(sorted(os.listdir(project_dir))) or "(no files yet)")
                continue
            if lowered.startswith("/run"):
                self.run_program(project_dir, line[4:].strip())
                continue
            self.out("(The assistant is working. This can take a minute.)")
            return line

    def run_program(self, project_dir, args_text):
        script = os.path.join(project_dir, "main.py")
        if not os.path.isfile(script):
            self.out("main.py was not found yet.")
            return
        try:
            args = shlex.split(args_text)
        except ValueError as e:
            self.out(f"Could not read the arguments: {e}")
            return
        self.program_runs += 1
        try:
            result = subprocess.run(
                [sys.executable, "main.py", *args], cwd=project_dir,
                capture_output=True, text=True, timeout=10, env=clean_env(),**child_kwargs(),
            )
        except subprocess.TimeoutExpired:
            self.out("The program did not finish within 10 seconds.")
            return
        self.out(f"[exit code {result.returncode}]")
        if result.stdout:
            self.out(result.stdout.rstrip())
        if result.stderr:
            self.out(result.stderr.rstrip())

    def rating(self):
        while True:
            text = self.inp("How satisfied are you with the result? 1 (not at all) to 5 (very): ").strip()
            if text in {"1", "2", "3", "4", "5"}:
                return int(text)