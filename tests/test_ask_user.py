import json
import tempfile
import unittest

from agent import run_agent
from call_function import available_functions
from functions.ask_user import schema_ask_user
from tests.test_agent import FakeClient, reply, tool_call, tool_messages


def ask(call_id, question):
    return reply(tool_calls=[tool_call(call_id, "ask_user", json.dumps({"question": question}))])


class AskUserTests(unittest.TestCase):
    def run_with(self, replies, callback, max_questions=3, tools=None):
        client = FakeClient(replies)
        messages = [{"role": "user", "content": "x"}]
        with tempfile.TemporaryDirectory() as tmp:
            stats = run_agent(
                client, "m", messages, tmp, max_rounds=6,
                tools=tools if tools is not None else available_functions + [schema_ask_user],
                ask_callback=callback, max_questions=max_questions,
            )
        return stats, messages

    def test_answer_is_passed_to_the_model_and_recorded(self):
        asked = []

        def callback(question):
            asked.append(question)
            return "Use two arguments."

        stats, messages = self.run_with([ask("1", "Which input?"), reply(content="done")], callback)
        self.assertEqual(asked, ["Which input?"])
        self.assertEqual(stats["questions"], [{"question": "Which input?", "answer": "Use two arguments."}])
        self.assertEqual(tool_messages(messages)[0]["content"], "Use two arguments.")
        self.assertTrue(stats["finished"])

    def test_question_cap_is_enforced(self):
        replies = [ask(str(i), f"q{i}") for i in range(3)] + [reply(content="done")]
        stats, messages = self.run_with(replies, lambda q: "ok", max_questions=2)
        self.assertEqual(len(stats["questions"]), 2)
        self.assertIn("no more questions", tool_messages(messages)[2]["content"])

    def test_tool_is_refused_when_not_offered(self):
        called = []
        stats, messages = self.run_with(
            [ask("1", "Which input?"), reply(content="done")],
            lambda q: called.append(q) or "x",
            tools=available_functions,
        )
        self.assertEqual(called, [])
        self.assertIn("Unknown function", tool_messages(messages)[0]["content"])

    def test_bad_arguments_become_an_error_message(self):
        bad = reply(tool_calls=[tool_call("1", "ask_user", "{}")])
        stats, messages = self.run_with([bad, reply(content="done")], lambda q: "x")
        self.assertTrue(tool_messages(messages)[0]["content"].startswith("Error:"))
        self.assertEqual(stats["questions"], [])

    def test_tokens_are_recorded_per_round(self):
        stats, _ = self.run_with([ask("1", "Which input?"), reply(content="done")], lambda q: "ok")
        self.assertEqual(len(stats["per_round"]), 2)
        self.assertEqual(stats["prompt_tokens"], 20)
        self.assertEqual(stats["completion_tokens"], 10)


if __name__ == "__main__":
    unittest.main()