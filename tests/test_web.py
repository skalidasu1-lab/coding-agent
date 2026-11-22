import os
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from study import tasks, web_app
from study.design import Clarity
from study.web_student import SessionCancelled, WebStudent
from tests.test_agent import FakeClient, reply
from tests.test_study_pipeline import write_main

HAVE_TASKS = len(tasks.analysed_task_ids()) == 6 and tasks.PRACTICE_ID in tasks.task_ids()
LOCAL = "http://127.0.0.1:8000"
TASK = {"title": "T", "intent": "do it", "ambiguities": []}


def wait_until(condition, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if condition():
            return True
        time.sleep(0.01)
    return False


def start_thread(function, *args):
    outcome = {}

    def target():
        try:
            outcome["value"] = function(*args)
        except BaseException as e:  # noqa: BLE001
            outcome["error"] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    return thread, outcome


class WebStudentTests(unittest.TestCase):
    def test_first_prompt_waits_then_returns_the_text(self):
        student = WebStudent()
        thread, outcome = start_thread(student.first_prompt, TASK, Clarity.VAGUE)
        self.assertTrue(wait_until(lambda: student.waiting == "prompt"))
        self.assertEqual(student.events[0]["type"], "task")
        self.assertEqual(student.submit("prompt", "  hello  "), "ok")
        thread.join(5)
        self.assertEqual(outcome["value"], "hello")
        self.assertIsNone(student.waiting)

    def test_wrong_or_invalid_input_is_rejected(self):
        student = WebStudent()
        thread, outcome = start_thread(student.first_prompt, TASK, Clarity.CLEAR)
        self.assertTrue(wait_until(lambda: student.waiting == "prompt"))
        self.assertEqual(student.submit("rating", rating=3), "not_waiting")
        self.assertEqual(student.submit("prompt", "   "), "invalid")
        self.assertEqual(student.submit("prompt", "x" * 5000), "invalid")
        self.assertEqual(student.waiting, "prompt")
        self.assertEqual(student.submit("prompt", "ok"), "ok")
        thread.join(5)
        self.assertEqual(student.submit("prompt", "late"), "not_waiting")

    def test_review_commands(self):
        student = WebStudent()
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "main.py"), "w") as f:
                f.write("print('hi')\n")
            thread, outcome = start_thread(student.review, "All done", tmp)
            self.assertTrue(wait_until(lambda: student.waiting == "review"))
            self.assertEqual(student.events[0]["type"], "assistant")
            self.assertEqual(student.submit("files"), "ok")
            self.assertTrue(wait_until(
                lambda: any(e["type"] == "output" for e in student.events) and student.waiting == "review"))
            self.assertEqual(student.submit("run", ""), "ok")
            self.assertTrue(wait_until(
                lambda: any(e["type"] == "output" and "hi" in e["text"] for e in student.events)
                and student.waiting == "review"))
            self.assertEqual(student.program_runs, 1)
            self.assertEqual(student.submit("prompt", "make it blue"), "ok")
            thread.join(5)
        self.assertEqual(outcome["value"], "make it blue")

    def test_done_ends_the_task(self):
        student = WebStudent()
        with tempfile.TemporaryDirectory() as tmp:
            thread, outcome = start_thread(student.review, "ok", tmp)
            self.assertTrue(wait_until(lambda: student.waiting == "review"))
            self.assertEqual(student.submit("done"), "ok")
            thread.join(5)
        self.assertIsNone(outcome["value"])

    def test_rating_must_be_between_one_and_five(self):
        student = WebStudent()
        thread, outcome = start_thread(student.rating)
        self.assertTrue(wait_until(lambda: student.waiting == "rating"))
        self.assertEqual(student.submit("rating", rating=0), "invalid")
        self.assertEqual(student.submit("rating", rating=6), "invalid")
        self.assertEqual(student.submit("rating", rating=4), "ok")
        thread.join(5)
        self.assertEqual(outcome["value"], 4)

    def test_cancelling_stops_the_waiting_thread(self):
        student = WebStudent()
        thread, outcome = start_thread(student.first_prompt, TASK, Clarity.VAGUE)
        self.assertTrue(wait_until(lambda: student.waiting == "prompt"))
        student.cancelled.set()
        thread.join(5)
        self.assertIsInstance(outcome["error"], SessionCancelled)
        self.assertIsNone(student.waiting)


class WebAppTests(unittest.TestCase):
    def setUp(self):
        web_app.STATE["session"] = None
        self.client = TestClient(web_app.app, base_url=LOCAL)

    def test_other_hosts_are_rejected(self):
        outside = TestClient(web_app.app, base_url="http://example.com")
        self.assertEqual(outside.get("/").status_code, 403)

    def test_foreign_origin_is_rejected(self):
        response = self.client.post("/api/start", json={"code": web_app.ADMIN_CODE},
                                    headers={"Origin": "http://example.com"})
        self.assertEqual(response.status_code, 403)

    def test_index_page_is_served_and_shows_no_token_counts(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Coding assistant study", response.text)
        self.assertNotIn("tokens", response.text.lower())

    def test_start_needs_the_experimenter_code_and_consent(self):
        wrong = self.client.post("/api/start", json={"code": "wrong", "consent_confirmed": True})
        self.assertEqual(wrong.status_code, 403)
        no_consent = self.client.post("/api/start", json={"code": web_app.ADMIN_CODE,
                                                          "consent_confirmed": False})
        self.assertEqual(no_consent.status_code, 400)

    def test_events_without_a_session(self):
        self.assertFalse(self.client.get("/api/events").json()["active"])

    def test_sending_without_a_session_is_a_conflict(self):
        response = self.client.post("/api/send", json={"kind": "prompt", "text": "x"})
        self.assertEqual(response.status_code, 409)


@unittest.skipUnless(HAVE_TASKS, "task bank not generated (study/tasks is git-ignored)")
class WebFlowTests(unittest.TestCase):
    def test_a_participant_finishes_the_practice_task_through_the_api(self):
        http = TestClient(web_app.app, base_url=LOCAL)
        web_app.STATE["session"] = None
        start_body = {"code": web_app.ADMIN_CODE, "consent_confirmed": True}
        with tempfile.TemporaryDirectory() as tmp:
            client = FakeClient([write_main("1", tasks.PRACTICE_ID), reply(content="Done.")])
            with patch.dict(web_app.SETTINGS, {"model": "m", "data_dir": tmp, "temperature": 0.0}), \
                    patch.object(web_app, "make_client", lambda: client):
                response = http.post("/api/start", json=start_body)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["participant_id"], "P001")
                session = web_app.STATE["session"]

                def waiting():
                    return http.get("/api/events").json()["waiting"]

                def two_tasks_and_prompt():
                    data = http.get("/api/events").json()
                    return (sum(e["type"] == "task" for e in data["events"]) == 2
                            and data["waiting"] == "prompt")

                try:
                    self.assertTrue(wait_until(lambda: waiting() == "prompt"))
                    self.assertEqual(http.post("/api/start", json=start_body).status_code, 409)
                    sent = http.post("/api/send", json={"kind": "prompt", "text": "greet people"})
                    self.assertEqual(sent.status_code, 200)
                    self.assertTrue(wait_until(lambda: waiting() == "review"))
                    self.assertEqual(http.post("/api/send", json={"kind": "done"}).status_code, 200)
                    self.assertTrue(wait_until(lambda: waiting() == "rating"))
                    bad = http.post("/api/send", json={"kind": "rating", "rating": 9})
                    self.assertEqual(bad.status_code, 400)
                    good = http.post("/api/send", json={"kind": "rating", "rating": 5})
                    self.assertEqual(good.status_code, 200)
                    self.assertTrue(wait_until(two_tasks_and_prompt))
                finally:
                    session.student.cancelled.set()
                    session.thread.join(5)
                    web_app.STATE["session"] = None
            self.assertTrue(session.finished)


if __name__ == "__main__":
    unittest.main()