from study.design import Clarity
from study.tasks import canned_answer, grade


class ScriptedStudent:
    """A simulated student who knows the full intent. Vague prompts are one short
    sentence. If the result is wrong, the student restates the full intent once."""

    def __init__(self, task: dict):
        self.task = task

    def first_prompt(self, task, clarity):
        if clarity == Clarity.CLEAR:
            return task["intent"]
        return f"Write a Python program: {task['title'].lower()}."

    def answer(self, question):
        return canned_answer(self.task, question)

    def review(self, final, project_dir):
        if grade(self.task["id"], project_dir)["passed"]:
            return None
        return "That's not quite right. Here is exactly what I want: " + self.task["intent"]

    def rating(self):
        return None  # a simulated student has no satisfaction to report