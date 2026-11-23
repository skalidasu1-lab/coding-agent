import json
import tempfile
import unittest
from types import SimpleNamespace as NS

import httpx
from openai import BadRequestError

from agent import run_agent
from tests.test_agent import FakeClient, reply, tool_call


def listing(call_id, directory):
    return reply(tool_calls=[tool_call(call_id, "get_files_info", json.dumps({"directory": directory}))])


class RecordingClient(FakeClient):
    def __init__(self, replies):
        super().__init__(replies)
        self.calls = []
        self.chat = NS(completions=NS(create=self._record))

    def _record(self, **kwargs):
        self.calls.append(kwargs)
        return self.replies.pop(0)


class RoundCapTests(unittest.TestCase):
    def run_it(self, client, max_rounds):
        with tempfile.TemporaryDirectory() as tmp:
            return run_agent(client, "m", [{"role": "user", "content": "x"}], tmp, max_rounds=max_rounds)

    def test_only_the_last_round_switches_tools_off(self):
        client = RecordingClient([listing("1", "."), listing("2", "a"), listing("3", "b")])
        stats = self.run_it(client, 3)
        self.assertNotIn("tool_choice", client.calls[0])
        self.assertNotIn("tool_choice", client.calls[1])
        self.assertEqual(client.calls[2]["tool_choice"], "none")
        self.assertTrue(stats["hit_round_cap"])
        self.assertFalse(stats["finished"])

    def test_a_text_answer_on_the_last_round_counts_as_finished(self):
        client = RecordingClient([listing("1", "."), reply(content="All done.")])
        stats = self.run_it(client, 2)
        self.assertTrue(stats["finished"])
        self.assertFalse(stats["hit_round_cap"])
        self.assertEqual(stats["final"], "All done.")

    def test_a_single_round_run_keeps_tools_available(self):
        client = RecordingClient([reply(content="ok")])
        self.run_it(client, 1)
        self.assertNotIn("tool_choice", client.calls[0])

    def test_provider_that_rejects_tool_choice_is_retried_without_it(self):
        class PickyClient(RecordingClient):
            def _record(self, **kwargs):
                self.calls.append(kwargs)
                if "tool_choice" in kwargs:
                    response = httpx.Response(400, request=httpx.Request("POST", "http://example.test"))
                    raise BadRequestError("tool_choice is not supported", response=response, body=None)
                return self.replies.pop(0)

        client = PickyClient([listing("1", "."), reply(content="done")])
        stats = self.run_it(client, 2)
        self.assertTrue(stats["finished"])
        self.assertEqual(len(client.calls), 3)  # round 1, round 2 with tool_choice, round 2 without


if __name__ == "__main__":
    unittest.main()