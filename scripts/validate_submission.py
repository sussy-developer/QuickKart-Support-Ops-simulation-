from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models import SupportAction
from server.app import app


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_openenv_yaml() -> None:
    file_path = ROOT / "openenv.yaml"
    _assert(file_path.exists(), "openenv.yaml is missing")

    payload = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    required_fields = ["spec_version", "name", "type", "runtime", "app", "port"]
    for field in required_fields:
        _assert(field in payload, f"openenv.yaml missing required field: {field}")

    _assert(payload["runtime"] == "fastapi", "runtime must be fastapi")


def validate_files_exist() -> None:
    for rel in ["Dockerfile", "README.md", "baseline.py", "support_env.py", "models.py"]:
        _assert((ROOT / rel).exists(), f"Required file missing: {rel}")


def validate_api_surface() -> None:
    with TestClient(app) as client:
        health = client.get("/health")
        _assert(health.status_code == 200, "GET /health failed")

        login = client.post("/auth/login", json={"email": "agent@quickkart.com", "password": "demo123"})
        _assert(login.status_code == 200, "POST /auth/login failed")

        tasks = client.get("/tasks")
        _assert(tasks.status_code == 200, "GET /tasks failed")
        task_payload = tasks.json()["tasks"]
        _assert(len(task_payload) >= 3, "Need at least 3 tasks")

        task_ids = {task["task_id"] for task in task_payload}
        for expected in {"easy", "medium", "hard"}:
            _assert(expected in task_ids, f"Missing required task {expected}")

        reset = client.post("/reset", json={"task_id": "easy", "seed": 42})
        _assert(reset.status_code == 200, "POST /reset failed")
        reset_obs = reset.json()["observation"]
        _assert(reset_obs["task_id"] == "easy", "reset did not select easy task")

        tickets = client.get("/tickets")
        _assert(tickets.status_code == 200, "GET /tickets failed")
        rows = tickets.json()["tickets"]
        _assert(len(rows) > 0, "tickets list must not be empty")

        first_ticket = rows[0]["ticket_id"]
        step_1 = client.post("/step", json={"action_type": "select_ticket", "ticket_id": first_ticket})
        _assert(step_1.status_code == 200, "POST /step select_ticket failed")

        step_2 = client.post(
            "/step",
            json={
                "action_type": "classify_ticket",
                "ticket_id": first_ticket,
                "category": "billing",
            },
        )
        _assert(step_2.status_code == 200, "POST /step classify_ticket failed")

        kb = client.get("/knowledge-base")
        _assert(kb.status_code == 200, "GET /knowledge-base failed")

        state = client.get("/state")
        _assert(state.status_code == 200, "GET /state failed")

        grader = client.post("/grader", json={"task_id": "easy"})
        _assert(grader.status_code == 200, "POST /grader failed")
        grader_score = grader.json()["score"]
        _assert(0.0 <= grader_score <= 1.0, "Grader score out of range")

        baseline = client.post("/baseline")
        _assert(baseline.status_code == 200, "POST /baseline failed")
        baseline_payload = baseline.json()
        _assert(len(baseline_payload["tasks"]) >= 3, "Baseline must return all tasks")
        _assert(0.0 <= baseline_payload["average_score"] <= 1.0, "Baseline average out of range")

        schema = task_payload[0]["action_schema"]
        schema_text = json.dumps(schema)
        for token in [
            "select_ticket",
            "classify_ticket",
            "consult_kb",
            "respond",
            "escalate",
            "close_ticket",
            "defer",
        ]:
            _assert(token in schema_text, f"Action schema missing token {token}")

        _ = SupportAction(action_type="defer")


def main() -> None:
    validate_files_exist()
    validate_openenv_yaml()
    validate_api_surface()
    print("Validation succeeded: OpenEnv customer-support environment is submission-ready.")


if __name__ == "__main__":
    main()
