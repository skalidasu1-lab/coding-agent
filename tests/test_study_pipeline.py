import itertools
import json
import os
import tempfile
import unittest
from types import SimpleNamespace as NS

from study import tasks
from study.design import MAX_STUDENT_PROMPTS, Clarity, Policy
from study.logger import append_jsonl, read_jsonl
from study.participants import register_participant
from study.scripted_student import ScriptedStudent
from study.session import run_task_session
from study.terminal_student import TerminalStudent
from tests.test_agent import FakeClient, reply, tool_call

HAVE_TASKS = bool(tasks.task_ids())
T1 = "t1_temperature"


def solution_text(task_id):
    with open(os.path.join(tasks.TASKS_DIR, task_id, "solution", "main.py")) as f:
        return f.read()


def write_main(call_id, task_id=T1):
    args = {"file_path": "main.py", "content": solution_text(task_id)}
    return reply(tool_calls=[tool_call(call_id, "write_file", json.dumps(args))])


def ask(call_id, question):
    return reply(tool_calls=[tool_call(call_id, "ask_user", json.dumps({"question": question}))])


class StubStudent:
    def __init__(self, follow_up=None):
        self.follow_up = follow_up
        self.answers = []

    def first_prompt(self, task, clarity):
        return "make the program"

    def answer(self, question):
        self.answers.append(question)
        return "an answer"

    def review(self, final, project_dir):
        return self.follow_up

    def rating(self):
        return 5


class BrokenClient:
    def __init__(self):
        def boom(**kwargs):
            raise RuntimeError("network down")
        self.chat = NS(completions=NS(create=boom))


class LoggerTests(unittest.TestCase):
    def test_round_trip_and_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "nested", "log.jsonl")
            self.assertEqual(read_jsonl(path), [])
            append_jsonl(path, {"a": 1})
            append_jsonl(path, {"b": 2})
            self.assertEqual(read_jsonl(path), [{"a": 1}, {"b": 2}])


class ParticipantTests(unittest.TestCase):
    def test_registration_balances_sequences(self):
        ids = [f"t{i}" for i in range(6)]
        with tempfile.TemporaryDirectory() as tmp:
            records = [register_participant(tmp, ids) for _ in range(12)]
        self.assertEqual([r["participant_id"] for r in records[:3]], ["P001", "P002", "P003"])
        for position in range(6):
            cells = {(r["plan"][position]["policy"], r["plan"][position]["clarity"])
                     for r in records[:6]}
            self.assertEqual(len(cells), 6)
        self.assertEqual(records[6]["plan"], records[0]["plan"])

    def test_needs_exactly_six_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                register_participant(tmp, ["a", "b"])


class TerminalStudentTests(unittest.TestCase):
    def make(self, inputs):
        outputs = []
        feed = iter(inputs)
        student = TerminalStudent(input_fn=lambda prompt="": next(feed), output_fn=outputs.append)
        return student, outputs

    def test_plain_text_is_the_next_request_and_files_are_listed(self):
        student, out = self.make(["", "/files", "make it blue"])
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, "main.py"), "w").close()
            result = student.review("All done", tmp)
        self.assertEqual(result, "make it blue")
        self.assertTrue(any("main.py" in line for line in out))

    def test_done_ends_the_task(self):
        student, _ = self.make(["/done"])
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(student.review("ok", tmp))

    def test_run_command_runs_the_program(self):
        student, out = self.make(["/run", "/done"])
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "main.py"), "w") as f:
                f.write("print('hi')\n")
            student.review("ok", tmp)
        self.assertIn("hi", out)
        self.assertEqual(student.program_runs, 1)

    def test_rating_retries_until_valid(self):
        student, _ = self.make(["9", "x", "4"])
        self.assertEqual(student.rating(), 4)


@unittest.skipUnless(HAVE_TASKS, "task bank not generated (study/tasks is git-ignored)")
class SessionTests(unittest.TestCase):
    def setUp(self):
        self.task = tasks.load_task(T1)

    def test_correct_on_the_first_try(self):
        client = FakeClient([write_main("1"), reply(content="Done.")])
        record = run_task_session(client, "m", self.task, Policy.NEVER, Clarity.CLEAR,
                                  ScriptedStudent(self.task), participant_id="P001", position=2)
        self.assertTrue(record["passed"])
        self.assertEqual(record["end_reason"], "student_done")
        self.assertEqual(record["student_prompts"], 1)
        self.assertEqual(record["rounds"], 2)
        self.assertEqual(record["total_tokens"], 30)
        self.assertEqual(record["prompts"][0], self.task["intent"])
        self.assertEqual(record["position"], 2)

    def test_wrong_first_try_leads_to_a_second_prompt(self):
        client = FakeClient([reply(content="Finished."), write_main("1"), reply(content="Fixed.")])
        record = run_task_session(client, "m", self.task, Policy.NEVER, Clarity.VAGUE,
                                  ScriptedStudent(self.task))
        self.assertEqual(record["student_prompts"], 2)
        self.assertTrue(record["passed"])
        self.assertIn("exactly what I want", record["prompts"][1])
        self.assertEqual(record["rounds"], 3)

    def test_questions_are_answered_and_logged(self):
        client = FakeClient([ask("1", "What format should the output take?"),
                             write_main("2"), reply(content="Done.")])
        record = run_task_session(client, "m", self.task, Policy.WHEN_UNCLEAR, Clarity.VAGUE,
                                  ScriptedStudent(self.task))
        self.assertEqual(record["n_questions"], 1)
        self.assertIn("1 decimal place", record["questions"][0]["answer"])
        self.assertTrue(record["passed"])

    def test_never_ask_policy_refuses_questions(self):
        student = StubStudent()
        client = FakeClient([ask("1", "Which input?"), reply(content="ok")])
        record = run_task_session(client, "m", self.task, Policy.NEVER, Clarity.VAGUE, student)
        self.assertEqual(record["n_questions"], 0)
        self.assertEqual(student.answers, [])

    def test_stops_after_the_maximum_number_of_prompts(self):
        client = FakeClient([reply(content="ok")] * MAX_STUDENT_PROMPTS)
        record = run_task_session(client, "m", self.task, Policy.NEVER, Clarity.VAGUE,
                                  StubStudent(follow_up="again"))
        self.assertEqual(record["student_prompts"], MAX_STUDENT_PROMPTS)
        self.assertEqual(record["end_reason"], "max_prompts")

    def test_stops_at_the_time_limit(self):
        client = FakeClient([reply(content="ok")])
        clock = itertools.count(0, 800).__next__
        record = run_task_session(client, "m", self.task, Policy.NEVER, Clarity.VAGUE,
                                  StubStudent(follow_up="again"), clock=clock)
        self.assertEqual(record["end_reason"], "time_limit")
        self.assertEqual(record["student_prompts"], 1)

    def test_technical_failure_is_flagged_and_not_rated(self):
        record = run_task_session(BrokenClient(), "m", self.task, Policy.NEVER, Clarity.VAGUE,
                                  StubStudent())
        self.assertTrue(record["technical_failure"])
        self.assertEqual(record["end_reason"], "technical_failure")
        self.assertIn("network down", record["failure"])
        self.assertIsNone(record["rating"])


if __name__ == "__main__":
    unittest.main()