from fastapi.testclient import TestClient

from server.app import app


def test_api_roundtrip() -> None:
    with TestClient(app) as client:
        login = client.post("/auth/login", json={"email": "agent@quickkart.com", "password": "demo123"})
        assert login.status_code == 200

        tasks = client.get("/tasks")
        assert tasks.status_code == 200
        assert len(tasks.json()["tasks"]) >= 3

        reset = client.post("/reset", json={"task_id": "hard", "seed": 9})
        assert reset.status_code == 200

        tickets = client.get("/tickets")
        assert tickets.status_code == 200
        target = tickets.json()["tickets"][0]["ticket_id"]

        step = client.post("/step", json={"action_type": "select_ticket", "ticket_id": target})
        assert step.status_code == 200
        payload = step.json()
        assert "observation" in payload

        invalid = client.post("/step", json={"action_type": "classify_ticket", "ticket_id": target})
        assert invalid.status_code == 422

        state = client.get("/state")
        assert state.status_code == 200

        grader = client.post("/grader", json={"task_id": "hard"})
        assert grader.status_code == 200
        assert 0.0 <= grader.json()["score"] <= 1.0

        baseline = client.post("/baseline")
        assert baseline.status_code == 200
        assert 0.0 <= baseline.json()["average_score"] <= 1.0
