from __future__ import annotations

import json
import os
from typing import Any

import requests

from models import BaselineResponse, BaselineTaskScore, SupportAction
from support_env import CustomerSupportEnv


PRIORITY_RANK = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
ALLOWED_CATEGORIES = {"billing", "technical", "account", "shipping", "general"}
ALLOWED_RESPONSES = {
    "apology_ack",
    "refund_processed",
    "replace_item",
    "shipping_update",
    "password_reset_link",
    "verify_identity",
    "troubleshoot_steps",
    "outage_acknowledged",
    "policy_explanation",
    "unsupported_reply",
}
ALLOWED_TIERS = {"tier1", "tier2", "tier3"}


class OpenAIPlanner:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_BASELINE_MODEL", "gpt-4.1-mini")
        self.timeout = float(os.getenv("OPENAI_BASELINE_TIMEOUT", "20"))
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def plan(self, task_id: str, subject: str, message: str) -> dict[str, str] | None:
        if not self.enabled:
            return None

        prompt = (
            "You are a support operations baseline policy. "
            "Return ONLY JSON with keys category, kb_article, response_code, target_tier. "
            "Valid categories: billing, technical, account, shipping, general. "
            "Valid response codes: apology_ack, refund_processed, replace_item, shipping_update, "
            "password_reset_link, verify_identity, troubleshoot_steps, outage_acknowledged, policy_explanation, unsupported_reply. "
            "Valid tiers: tier1, tier2, tier3. "
            f"Task difficulty: {task_id}. Ticket subject: {subject}. Ticket message: {message}."
        )

        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": "Output strict JSON only."},
                {"role": "user", "content": prompt},
            ],
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            cleaned = content.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`")
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].strip()
            parsed = json.loads(cleaned)
            return self._sanitize_plan(parsed)
        except Exception:
            return None

    def _sanitize_plan(self, plan: dict[str, Any]) -> dict[str, str]:
        category = str(plan.get("category", "general")).lower()
        response_code = str(plan.get("response_code", "apology_ack")).lower()
        target_tier = str(plan.get("target_tier", "tier1")).lower()
        kb_article = str(plan.get("kb_article", "KB-BILL-REFUND")).upper()

        if category not in ALLOWED_CATEGORIES:
            category = "general"
        if response_code not in ALLOWED_RESPONSES:
            response_code = "apology_ack"
        if target_tier not in ALLOWED_TIERS:
            target_tier = "tier1"

        return {
            "category": category,
            "response_code": response_code,
            "target_tier": target_tier,
            "kb_article": kb_article,
        }


def _infer_category(subject: str, message: str) -> str:
    text = f"{subject} {message}".lower()
    if any(token in text for token in ["error", "outage", "crash", "api", "timeout", "sync", "incident"]):
        return "technical"
    if any(token in text for token in ["password", "otp", "login", "sso", "account", "identity"]):
        return "account"
    if any(
        token in text
        for token in ["delivery", "shipment", "courier", "package", "damaged", "replacement", "order delayed"]
    ):
        return "shipping"
    if any(token in text for token in ["refund", "charge", "invoice", "gst", "tax", "payment", "upi"]):
        return "billing"
    return "general"


def _pick_kb(category: str, subject: str, message: str) -> str:
    text = f"{subject} {message}".lower()
    if category == "account" and any(token in text for token in ["sso", "outage", "token"]):
        return "KB-TECH-OUTAGE"
    if category == "billing" and any(token in text for token in ["invoice", "gst", "tax", "cod"]):
        return "KB-BILL-INVOICE"
    if category == "shipping" and "damaged" in text:
        return "KB-SHP-DAMAGE"
    if category == "account" and any(token in text for token in ["suspicious", "identity", "fraud", "otp"]):
        return "KB-SEC-VERIFY"
    if category == "technical" and any(token in text for token in ["outage", "incident", "all stores", "bridge"]):
        return "KB-TECH-OUTAGE"

    default_map = {
        "billing": "KB-BILL-REFUND",
        "shipping": "KB-SHP-TRACK",
        "account": "KB-ACC-RESET",
        "technical": "KB-TECH-API",
        "general": "KB-BILL-REFUND",
    }
    return default_map[category]


def _pick_response(category: str, subject: str, message: str) -> str:
    text = f"{subject} {message}".lower()
    if category == "billing" and any(token in text for token in ["fraud", "unauthorized", "high-value"]):
        return "verify_identity"
    if category == "shipping" and "damaged" in text:
        return "replace_item"
    if category == "billing" and any(token in text for token in ["charge", "refund", "pending", "upi"]):
        return "refund_processed"
    if category == "billing" and any(token in text for token in ["invoice", "gst", "tax", "cod"]):
        return "policy_explanation"
    if category == "account" and any(token in text for token in ["suspicious", "fraud", "locked"]):
        return "verify_identity"
    if category == "account" and any(token in text for token in ["sso", "outage", "token"]):
        return "outage_acknowledged"
    if category == "account":
        return "password_reset_link"
    if category == "technical" and any(token in text for token in ["outage", "incident", "all stores", "bridge"]):
        return "outage_acknowledged"
    if category == "technical":
        return "troubleshoot_steps"
    if category == "shipping":
        return "shipping_update"
    return "apology_ack"


def _target_tier(subject: str, message: str, category: str) -> str:
    text = f"{subject} {message}".lower()
    if any(token in text for token in ["all stores", "regional", "outage", "incident bridge", "warehouse"]):
        return "tier3"
    if category in {"technical", "account"} and any(token in text for token in ["error", "timeout", "suspicious", "fraud", "token", "sso"]):
        return "tier2"
    if category == "billing" and any(token in text for token in ["fraud", "unauthorized", "high-value", "reconciliation"]):
        return "tier2"
    if category == "shipping" and any(token in text for token in ["medical", "urgent", "insulin"]):
        return "tier2"
    return "tier1"


def _make_plan(planner: OpenAIPlanner, task_id: str, subject: str, message: str) -> dict[str, str]:
    llm_plan = planner.plan(task_id=task_id, subject=subject, message=message)
    if llm_plan:
        return llm_plan

    category = _infer_category(subject, message)
    return {
        "category": category,
        "kb_article": _pick_kb(category, subject, message),
        "response_code": _pick_response(category, subject, message),
        "target_tier": _target_tier(subject, message, category),
    }


def run_baseline_evaluation(prefer_openai: bool = True) -> BaselineResponse:
    env = CustomerSupportEnv(task_id="easy", seed=17)
    planner = OpenAIPlanner()
    if not prefer_openai:
        planner.api_key = None
    task_scores: list[BaselineTaskScore] = []

    for task_id in ["easy", "medium", "hard"]:
        observation = env.reset(task_id=task_id, seed=17)
        done = False
        ticket_plans: dict[str, dict[str, str]] = {}

        while not done:
            pending = [ticket for ticket in observation.ticket_summaries if ticket.status != "closed"]
            if not pending:
                break

            pending.sort(key=lambda row: (PRIORITY_RANK[row.priority], row.ticket_id, row.reopen_count))
            target = pending[0]

            if not observation.current_ticket or observation.current_ticket.ticket_id != target.ticket_id:
                observation, _, done, _ = env.step(SupportAction(action_type="select_ticket", ticket_id=target.ticket_id))
                continue

            current = observation.current_ticket
            if current.ticket_id not in ticket_plans:
                ticket_plans[current.ticket_id] = _make_plan(
                    planner=planner,
                    task_id=task_id,
                    subject=current.subject,
                    message=current.customer_message,
                )
            plan = ticket_plans[current.ticket_id]

            if current.predicted_category is None:
                observation, _, done, _ = env.step(
                    SupportAction(
                        action_type="classify_ticket",
                        ticket_id=current.ticket_id,
                        category=plan["category"],
                    )
                )
                continue

            tier_rank = {"tier1": 1, "tier2": 2, "tier3": 3}
            desired_tier = plan["target_tier"]
            if tier_rank[current.current_tier] < tier_rank[desired_tier]:
                observation, _, done, _ = env.step(
                    SupportAction(
                        action_type="escalate",
                        ticket_id=current.ticket_id,
                        escalation_target=desired_tier,
                    )
                )
                continue

            if plan["kb_article"] not in current.kb_consulted:
                observation, _, done, _ = env.step(
                    SupportAction(
                        action_type="consult_kb",
                        ticket_id=current.ticket_id,
                        kb_article_id=plan["kb_article"],
                    )
                )
                continue

            if current.status != "resolved":
                observation, _, done, _ = env.step(
                    SupportAction(
                        action_type="respond",
                        ticket_id=current.ticket_id,
                        response_code=plan["response_code"],
                        response_text="OpenAI/heuristic baseline support reply",
                    )
                )
                continue

            observation, _, done, _ = env.step(
                SupportAction(action_type="close_ticket", ticket_id=current.ticket_id)
            )

        grade = env.grade_episode(task_id=task_id)
        task_scores.append(
            BaselineTaskScore(
                task_id=task_id,
                score=grade.score,
                steps_used=env.step_count,
                total_reward=round(env.cumulative_reward, 4),
                final_kpis=observation.kpis,
            )
        )

    average = sum(task.score for task in task_scores) / len(task_scores)
    return BaselineResponse(average_score=round(average, 4), tasks=task_scores)


def main() -> None:
    result = run_baseline_evaluation(prefer_openai=True)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
