from __future__ import annotations

import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from baseline import run_baseline_evaluation
from models import (
    BaselineResponse,
    GraderRequest,
    GraderResponse,
    LoginRequest,
    LoginResponse,
    ResetRequest,
    StepResult,
    SupportAction,
    UserProfile,
)
from support_env import CustomerSupportEnv


APP_ROOT = Path(__file__).resolve().parent
STATIC_DIR = APP_ROOT / "static"

app = FastAPI(title="OpenEnv Customer Support Ops Center", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

_env_lock = threading.Lock()
_env = CustomerSupportEnv(task_id="easy", seed=42)


@app.get("/", include_in_schema=False)
def ui() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    if not payload.email or not payload.password:
        raise HTTPException(status_code=400, detail="email and password are required")

    role = "admin" if "admin" in payload.email.lower() else "agent"
    profile = UserProfile(name=payload.email.split("@")[0].title(), email=payload.email, role=role)
    return LoginResponse(token=f"demo-{uuid.uuid4()}", user=profile)


@app.post("/reset", response_model=StepResult)
def reset(payload: ResetRequest) -> StepResult:
    with _env_lock:
        obs = _env.reset(task_id=payload.task_id, seed=payload.seed)
        return StepResult(observation=obs, reward=0.0, done=False, info={"episode_id": _env.episode_id})


@app.post("/step", response_model=StepResult)
def step(action: SupportAction) -> StepResult:
    with _env_lock:
        observation, reward, done, info = _env.step(action)
        return StepResult(observation=observation, reward=reward, done=done, info=info)


@app.get("/state")
def state() -> dict:
    with _env_lock:
        return _env.state().model_dump()


@app.get("/tasks")
def tasks() -> dict:
    with _env_lock:
        descriptors = [task.model_dump() for task in _env.task_descriptors()]
    return {"tasks": descriptors}


@app.get("/tickets")
def tickets() -> dict:
    with _env_lock:
        observation = _env.observation()
        rows = [ticket.model_dump() for ticket in observation.ticket_summaries]
    return {"active_ticket_id": _env.active_ticket_id, "tickets": rows}


@app.get("/queue")
def queue() -> dict:
    return tickets()


@app.get("/ticket/{ticket_id}")
def ticket_detail(ticket_id: str) -> dict:
    with _env_lock:
        detail = _env.ticket_detail(ticket_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="ticket not found")
    return detail.model_dump()


@app.get("/knowledge-base")
def knowledge_base() -> dict:
    with _env_lock:
        items = [row.model_dump() for row in _env.knowledge_base_records()]
    return {"articles": items}


@app.get("/kpis")
def kpis() -> dict:
    with _env_lock:
        observation = _env.observation()
    return observation.kpis.model_dump()


@app.post("/grader", response_model=GraderResponse)
def grader(payload: GraderRequest) -> GraderResponse:
    with _env_lock:
        return _env.grade_episode(task_id=payload.task_id)


@app.post("/baseline", response_model=BaselineResponse)
def baseline() -> BaselineResponse:
    return run_baseline_evaluation()


def main() -> None:
    import uvicorn

    uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
