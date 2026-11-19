import json
import os
import tempfile
import unittest
from types import SimpleNamespace as NS

from agent import run_agent


def reply(content=None, tool_calls=None):
    return NS(
        choices=[NS(message=NS(content=content, tool_calls=tool_calls))],
        usage=NS(prompt_tokens=10, completion_tokens=5),
    )


def tool_call(call_id, name, arguments):
    return NS(id=call_id, function=NS(name=name, arguments=arguments))


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kwargs):
        return self.replies.pop(0)


def tool_messages(messages):
    return [m for m in messages if isinstance(m, dict) and m.get("role") == "tool"]


class RunAgentTests(unittest.TestCase):
    def test_runs_a_tool_then_finishes(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "a.txt"), "w") as f:
                f.write("hello")
            client = FakeClient([
                reply(tool_calls=[tool_call("1", "get_file_content", json.dumps({"file_path": "a.txt"}))]),
                reply(content="done"),
            ])
            messages = [{"role": "user", "content": "read it"}]
            stats = run_agent(client, "m", messages, tmp, max_rounds=5)

        self.assertTrue(stats["finished"])
        self.assertEqual(stats["final"], "done")
        self.assertEqual(stats["rounds"], 2)
        self.assertEqual(stats["prompt_tokens"], 20)
        result = tool_messages(messages)[0]
        self.assertEqual(result["content"], "hello")
        self.assertEqual(result["tool_call_id"], "1")

    def test_bad_json_becomes_an_error_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = FakeClient([
                reply(tool_calls=[tool_call("1", "get_files_info", "{'directory': '.'}")]),
                reply(content="ok"),
            ])
            messages = [{"role": "user", "content": "x"}]
            stats = run_agent(client, "m", messages, tmp, max_rounds=5)

        self.assertTrue(stats["finished"])
        self.assertTrue(tool_messages(messages)[0]["content"].startswith("Error:"))

    def test_repeated_calls_are_blocked_and_the_round_cap_applies(self):
        with tempfile.TemporaryDirectory() as tmp:
            same = lambda i: reply(tool_calls=[tool_call(str(i), "get_files_info", "{}")])
            client = FakeClient([same(1), same(2), same(3)])
            messages = [{"role": "user", "content": "x"}]
            stats = run_agent(client, "m", messages, tmp, max_rounds=3)

        self.assertFalse(stats["finished"])
        self.assertEqual(stats["rounds"], 3)
        self.assertIn("already made this exact call", tool_messages(messages)[2]["content"])


if __name__ == "__main__":
    unittest.main()