from __future__ import annotations

from typing import Any

import requests

from models import GraderResponse, LoginResponse, ResetRequest, StepResult, SupportAction


class CustomerSupportClient:
    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def login(self, email: str, password: str) -> LoginResponse:
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return LoginResponse.model_validate(response.json())

    def reset(self, task_id: str = "easy", seed: int = 42) -> StepResult:
        payload = ResetRequest(task_id=task_id, seed=seed).model_dump()
        response = requests.post(f"{self.base_url}/reset", json=payload, timeout=self.timeout)
        response.raise_for_status()
        return StepResult.model_validate(response.json())

    def step(self, action: SupportAction) -> StepResult:
        response = requests.post(
            f"{self.base_url}/step",
            json=action.model_dump(exclude_none=True),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return StepResult.model_validate(response.json())

    def state(self) -> dict[str, Any]:
        response = requests.get(f"{self.base_url}/state", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def tasks(self) -> dict[str, Any]:
        response = requests.get(f"{self.base_url}/tasks", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def tickets(self) -> dict[str, Any]:
        response = requests.get(f"{self.base_url}/tickets", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def grader(self, task_id: str | None = None) -> GraderResponse:
        response = requests.post(
            f"{self.base_url}/grader",
            json={"task_id": task_id},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return GraderResponse.model_validate(response.json())

    def baseline(self) -> dict[str, Any]:
        response = requests.post(f"{self.base_url}/baseline", timeout=self.timeout)
        response.raise_for_status()
        return response.json()
