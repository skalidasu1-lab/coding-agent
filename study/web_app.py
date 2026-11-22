import argparse
import os
import secrets
import threading

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from config import make_client
from study.design import Clarity, Policy
from study.logger import SESSIONS_FILE, append_jsonl, read_jsonl
from study.participants import find_participant, register_participant
from study.session import run_task_session
from study.tasks import PRACTICE_ID, analysed_task_ids, load_task
from study.web_student import SessionCancelled, WebStudent

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_FILE = os.path.join(ROOT, "frontend", "index.html")
LOCAL_HOSTS = {"127.0.0.1", "localhost"}
ADMIN_CODE = os.environ.get("STUDY_ADMIN_CODE") or secrets.token_urlsafe(6)

SETTINGS = {"model": "", "data_dir": "study_data", "temperature": 0.0}
STATE = {"session": None}
STATE_LOCK = threading.Lock()
TECHNICAL_MESSAGE = "A technical problem occurred. Please call the experimenter."

app = FastAPI(title="Coding assistant study")


def host_name(value: str) -> str:
    value = value.split("://", 1)[-1].split("/", 1)[0]
    return value.rsplit(":", 1)[0] if ":" in value else value


@app.middleware("http")
async def only_local(request: Request, call_next):
    if host_name(request.headers.get("host", "")) not in LOCAL_HOSTS:
        return JSONResponse({"detail": "Forbidden"}, status_code=403)
    origin = request.headers.get("origin")
    if origin and host_name(origin) not in LOCAL_HOSTS:
        return JSONResponse({"detail": "Forbidden"}, status_code=403)
    return await call_next(request)


class WebSession:
    """Runs one participant through the whole study in a background thread."""

    def __init__(self, participant: dict, student: WebStudent, client):
        self.participant = participant
        self.student = student
        self.client = client
        self.finished = False
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        try:
            self.run_all()
        except SessionCancelled:
            self.student.emit("error", text="The session was cancelled.")
        except Exception as e:
            self.student.emit("error", text=TECHNICAL_MESSAGE)
            print(f"Session error: {type(e).__name__}: {e}")
        finally:
            self.finished = True

    def run_all(self):
        pid = self.participant["participant_id"]
        data_dir = SETTINGS["data_dir"]
        model = SETTINGS["model"]
        temperature = SETTINGS["temperature"]
        student = self.student
        sessions_path = os.path.join(data_dir, SESSIONS_FILE)

        student.emit("started", participant_id=pid)
        student.emit("say", text="Practice task (not recorded). Try the buttons to see how they work.")
        run_task_session(self.client, model, load_task(PRACTICE_ID), Policy.WHEN_UNCLEAR,
                         Clarity.VAGUE, student, participant_id=pid, temperature=temperature)

        done = {
            r["position"] for r in read_jsonl(sessions_path)
            if r["participant_id"] == pid and not r["technical_failure"]
        }
        plan = self.participant["plan"]
        for step in plan:
            if step["position"] in done:
                continue
            student.emit("say", text=f"Task {step['position'] + 1} of {len(plan)}")
            task = load_task(step["task_id"])
            while True:
                record = run_task_session(
                    self.client, model, task, Policy(step["policy"]), Clarity(step["clarity"]),
                    student, participant_id=pid, position=step["position"], temperature=temperature,
                    keep_dir=os.path.join(data_dir, "projects", f"{pid}_pos{step['position']}"),
                )
                append_jsonl(sessions_path, record)
                if not record["technical_failure"]:
                    break
                print(f"Technical failure for {pid}: {record['failure']}")
                if not student.ask_retry(TECHNICAL_MESSAGE):
                    break
        student.emit("finished")


class StartRequest(BaseModel):
    code: str = ""
    participant_id: str | None = None
    consent_confirmed: bool = False


class SendRequest(BaseModel):
    kind: str
    text: str = ""
    rating: int | None = None


@app.get("/")
def index():
    return FileResponse(INDEX_FILE)


@app.post("/api/start")
def start(body: StartRequest):
    if not secrets.compare_digest(body.code, ADMIN_CODE):
        return JSONResponse({"detail": "Wrong experimenter code."}, status_code=403)
    if not body.consent_confirmed:
        return JSONResponse({"detail": "Confirm that consent is signed and the pre-survey is done."},
                            status_code=400)
    if not SETTINGS["model"]:
        return JSONResponse({"detail": "The server was started without a model."}, status_code=500)
    with STATE_LOCK:
        current = STATE["session"]
        if current is not None and not current.finished:
            return JSONResponse({"detail": "A session is already running."}, status_code=409)
        data_dir = SETTINGS["data_dir"]
        if body.participant_id:
            participant = find_participant(data_dir, body.participant_id)
            if participant is None:
                return JSONResponse({"detail": "Unknown participant ID."}, status_code=404)
        else:
            participant = register_participant(data_dir, analysed_task_ids())
        session = WebSession(participant, WebStudent(), make_client())
        STATE["session"] = session
        session.thread.start()
    return {"participant_id": participant["participant_id"]}


@app.get("/api/events")
def events(after: int = 0):
    session = STATE["session"]
    if session is None:
        return {"active": False, "events": [], "waiting": None, "finished": False}
    new_events, waiting = session.student.events_after(max(after, 0))
    return {"active": True, "events": new_events, "waiting": waiting, "finished": session.finished}


@app.post("/api/send")
def send(body: SendRequest):
    session = STATE["session"]
    if session is None or session.finished:
        return JSONResponse({"detail": "No active session."}, status_code=409)
    result = session.student.submit(body.kind, body.text, body.rating)
    if result == "invalid":
        return JSONResponse({"detail": "That input is not valid."}, status_code=400)
    if result == "not_waiting":
        return JSONResponse({"detail": "The assistant is not waiting for that right now."}, status_code=409)
    return {"ok": True}


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description="Run the study web interface (localhost only)")
    parser.add_argument("--model", required=True)
    parser.add_argument("--data-dir", default="study_data")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    load_dotenv()
    SETTINGS.update(model=args.model, data_dir=args.data_dir, temperature=args.temperature)
    print(f"\nExperimenter code: {ADMIN_CODE}")
    print(f"Open http://127.0.0.1:{args.port} in a browser on this machine.\n")
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
