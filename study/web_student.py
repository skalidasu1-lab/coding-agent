import os
import queue
import threading

from study.terminal_student import CLARITY_INSTRUCTIONS, TerminalStudent

MAX_TEXT_LENGTH = 4000

ALLOWED = {
    "prompt": {"prompt"},
    "answer": {"answer"},
    "review": {"prompt", "run", "files", "done"},
    "rating": {"rating"},
    "technical": {"retry", "skip"},
}
TEXT_KINDS = {"prompt", "answer"}


class SessionCancelled(BaseException):
    """Raised inside the session thread when the experimenter cancels it."""


class WebStudent:
    """The student side of a session, driven by a browser through events and replies."""

    def __init__(self):
        self.events: list[dict] = []
        self.waiting: str | None = None
        self.lock = threading.Lock()
        self.inbox: queue.Queue = queue.Queue()
        self.cancelled = threading.Event()
        self._terminal = TerminalStudent(output_fn=self._output)  # reuse the /run logic

    @property
    def program_runs(self) -> int:
        return self._terminal.program_runs

    def emit(self, event_type: str, **data) -> None:
        with self.lock:
            self.events.append({"id": len(self.events) + 1, "type": event_type, **data})

    def _output(self, text) -> None:
        self.emit("output", text=str(text))

    def events_after(self, after: int):
        with self.lock:
            return list(self.events[after:]), self.waiting

    def submit(self, kind: str, text: str = "", rating: int | None = None) -> str:
        """Called by the web layer. Returns 'ok', 'not_waiting' or 'invalid'."""
        text = (text or "").strip()
        with self.lock:
            if self.waiting is None or kind not in ALLOWED[self.waiting]:
                return "not_waiting"
            if kind in TEXT_KINDS and (not text or len(text) > MAX_TEXT_LENGTH):
                return "invalid"
            if kind == "run" and len(text) > 200:
                return "invalid"
            if kind == "rating" and rating not in (1, 2, 3, 4, 5):
                return "invalid"
            self.waiting = None
        self.inbox.put({"kind": kind, "text": text, "rating": rating})
        return "ok"

    def _wait(self, kind: str) -> dict:
        with self.lock:
            self.waiting = kind
        while True:
            try:
                return self.inbox.get(timeout=0.25)
            except queue.Empty:
                if self.cancelled.is_set():
                    with self.lock:
                        self.waiting = None
                    raise SessionCancelled()

    # --- the interface that run_task_session expects from a student ---

    def first_prompt(self, task, clarity):
        self.emit("task", title=task["title"], intent=task["intent"],
                  instruction=CLARITY_INSTRUCTIONS[clarity])
        text = self._wait("prompt")["text"]
        self.emit("user", text=text)
        return text

    def answer(self, question):
        self.emit("question", text=question)
        text = self._wait("answer")["text"]
        self.emit("user", text=text)
        return text

    def review(self, final, project_dir):
        self.emit("assistant", text=final or "(The assistant did not finish.)")
        while True:
            reply = self._wait("review")
            kind = reply["kind"]
            if kind == "done":
                return None
            if kind == "files":
                self.emit("output", text="\n".join(sorted(os.listdir(project_dir))) or "(no files yet)")
            elif kind == "run":
                self._terminal.run_program(project_dir, reply["text"])
            else:
                self.emit("user", text=reply["text"])
                return reply["text"]

    def rating(self):
        self.emit("rating")
        return self._wait("rating")["rating"]

    def ask_retry(self, text: str) -> bool:
        self.emit("technical", text=text)
        return self._wait("technical")["kind"] == "retry"