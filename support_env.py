
from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from typing import Literal

from models import (
    ActionLogEntry,
    ConversationTurn,
    GraderResponse,
    KpiSnapshot,
    KnowledgeArticle,
    SupportAction,
    SupportObservation,
    SupportState,
    TaskDescriptor,
    TicketRuntimeState,
    TicketSummary,
    VisibleTicket,
)


TierValue = Literal["tier1", "tier2", "tier3"]

TIER_RANK: dict[TierValue, int] = {"tier1": 1, "tier2": 2, "tier3": 3}
PRIORITY_RANK = {"urgent": 0, "high": 1, "medium": 2, "low": 3}


@dataclass(frozen=True)
class TicketScenario:
    ticket_id: str
    subject: str
    customer_name: str
    customer_message: str
    true_category: Literal["billing", "technical", "account", "shipping", "general"]
    priority: Literal["low", "medium", "high", "urgent"]
    required_tier: TierValue
    preferred_response_codes: list[str]
    recommended_kb_articles: list[str]
    requires_kb: bool
    first_contact_expected: bool
    sla_first_response_steps: int
    sla_resolution_steps: int


@dataclass(frozen=True)
class SupportTask:
    task_id: str
    title: str
    difficulty: Literal["easy", "medium", "hard"]
    objective: str
    max_steps: int
    tickets: list[TicketScenario]


class CustomerSupportEnv:
    """OpenEnv-compatible customer support operations simulation."""

    def __init__(self, task_id: str = "easy", seed: int = 42) -> None:
        self._tasks = self._build_tasks()
        self._knowledge_base = self._build_knowledge_base()
        self._rng = random.Random(seed)
        self._seed = seed

        if task_id not in self._tasks:
            raise ValueError(f"Unknown task_id: {task_id}")

        self._selected_task_id = task_id
        self._selected_task = self._tasks[task_id]

        self.episode_id = ""
        self.done = False
        self.step_count = 0
        self.cumulative_reward = 0.0
        self.active_ticket_id: str | None = None
        self.queue_order: list[str] = []
        self.tickets: dict[str, TicketRuntimeState] = {}
        self.action_history: list[ActionLogEntry] = []
        self.current_shift = 1
        self.shift_length = 6
        self.shift_handoff_count = 0
        self.tier_capacity: dict[TierValue, int] = {"tier1": 999, "tier2": 2, "tier3": 1}
        self.last_feedback = "Environment created"

        self.reset(task_id=task_id, seed=seed)

    @property
    def selected_task(self) -> SupportTask:
        return self._selected_task

    def reset(self, task_id: str | None = None, seed: int | None = None) -> SupportObservation:
        if task_id is not None:
            if task_id not in self._tasks:
                raise ValueError(f"Unknown task_id: {task_id}")
            self._selected_task_id = task_id
            self._selected_task = self._tasks[task_id]

        if seed is not None:
            self._seed = seed
            self._rng = random.Random(seed)

        self.episode_id = str(uuid.uuid4())
        self.done = False
        self.step_count = 0
        self.cumulative_reward = 0.0
        self.action_history = []
        self.current_shift = 1
        self.shift_handoff_count = 0
        self.last_feedback = "Episode reset. Pick a ticket and start working the queue."

        scenarios = list(self.selected_task.tickets)
        self._rng.shuffle(scenarios)

        self.queue_order = [ticket.ticket_id for ticket in scenarios]
        self.tickets = {}

        for scenario in scenarios:
            self.tickets[scenario.ticket_id] = TicketRuntimeState(
                ticket_id=scenario.ticket_id,
                subject=scenario.subject,
                customer_name=scenario.customer_name,
                customer_message=scenario.customer_message,
                true_category=scenario.true_category,
                required_tier=scenario.required_tier,
                preferred_response_codes=scenario.preferred_response_codes,
                recommended_kb_articles=scenario.recommended_kb_articles,
                requires_kb=scenario.requires_kb,
                priority=scenario.priority,
                status="open",
                current_tier="tier1",
                has_pending_handoff_note=True,
                sla_first_response_steps=scenario.sla_first_response_steps,
                sla_resolution_steps=scenario.sla_resolution_steps,
                first_contact_expected=scenario.first_contact_expected,
                conversation=[
                    ConversationTurn(
                        speaker="customer",
                        message=scenario.customer_message,
                        step_index=0,
                    )
                ],
            )

        self.active_ticket_id = self._next_active_ticket()
        return self._observation()

    def state(self) -> SupportState:
        return SupportState(
            episode_id=self.episode_id,
            done=self.done,
            selected_task=self._selected_task_id,
            step_count=self.step_count,
            max_steps=self.selected_task.max_steps,
            active_ticket_id=self.active_ticket_id,
            queue_order=self.queue_order,
            tickets={ticket_id: ticket.model_copy(deep=True) for ticket_id, ticket in self.tickets.items()},
            cumulative_reward=round(self.cumulative_reward, 4),
            action_history=self.action_history.copy(),
        )
    def step(self, action: SupportAction) -> tuple[SupportObservation, float, bool, dict]:
        if self.done:
            return self._observation(), 0.0, True, {
                "warning": "Episode already completed. Call reset() to start a new one."
            }

        reward = 0.0
        info: dict[str, object] = {}
        note = ""

        ticket_id = action.ticket_id or self.active_ticket_id
        ticket = self.tickets.get(ticket_id) if ticket_id else None

        if action.action_type == "select_ticket":
            if not ticket:
                reward -= 0.1
                note = "Delay / wrong action: selected unknown ticket."
            elif ticket.status == "closed":
                reward -= 0.1
                note = "Delay / wrong action: ticket already closed."
            else:
                self.active_ticket_id = ticket.ticket_id
                note = f"Working on ticket {ticket.ticket_id}."

        elif action.action_type == "classify_ticket":
            if not ticket or not action.category:
                reward -= 0.1
                note = "Delay / wrong action: missing ticket or category."
            else:
                ticket.predicted_category = action.category
                ticket.has_pending_handoff_note = False
                if ticket.status == "open":
                    ticket.status = "in_progress"

                if action.category == ticket.true_category:
                    reward += 0.2
                    note = "Good reply signal: ticket category classified correctly."
                else:
                    reward -= 0.1
                    note = "Delay / wrong action: category classification is incorrect."

        elif action.action_type == "consult_kb":
            if not ticket or not action.kb_article_id:
                reward -= 0.1
                note = "Delay / wrong action: missing ticket or knowledge article."
            elif action.kb_article_id not in self._knowledge_base:
                reward -= 0.1
                note = "Delay / wrong action: unknown knowledge-base article."
            elif action.kb_article_id in ticket.kb_consulted:
                reward -= 0.1
                note = "Delay / wrong action: repeated knowledge lookup."
            else:
                ticket.kb_consulted.append(action.kb_article_id)
                ticket.has_pending_handoff_note = False
                if ticket.status == "open":
                    ticket.status = "in_progress"

                if action.kb_article_id in ticket.recommended_kb_articles:
                    reward += 0.2
                    note = "Good reply signal: consulted a relevant knowledge article."
                else:
                    reward -= 0.1
                    note = "Delay / wrong action: consulted an irrelevant article."

        elif action.action_type == "respond":
            if not ticket or not action.response_code:
                reward -= 0.1
                note = "Delay / wrong action: response missing ticket or response code."
            else:
                if ticket.first_response_step is None:
                    ticket.first_response_step = self.step_count + 1
                ticket.has_pending_handoff_note = False
                if ticket.status == "open":
                    ticket.status = "in_progress"

                ticket.responses.append(action.response_code)
                outbound = action.response_text or self._render_response_text(action.response_code)
                ticket.conversation.append(
                    ConversationTurn(
                        speaker="agent",
                        message=outbound,
                        step_index=self.step_count + 1,
                    )
                )

                quality = self._response_quality(ticket=ticket, response_code=action.response_code)
                if quality > 0.0:
                    reward += 0.2
                else:
                    reward -= 0.1

                solved = self._is_solution_valid(ticket=ticket, response_code=action.response_code)
                if solved and ticket.status not in {"resolved", "closed"}:
                    ticket.status = "resolved"
                    ticket.resolution_step = self.step_count + 1
                    ticket.conversation.append(
                        ConversationTurn(
                            speaker="system",
                            message="Issue appears solved. Close the ticket to complete it.",
                            step_index=self.step_count + 1,
                        )
                    )
                    reward += 0.5
                    note = "Correct solution delivered."
                elif quality > 0.0:
                    note = "Good reply sent, but ticket still needs further action."
                    follow_up = self._customer_follow_up(ticket=ticket, response_code=action.response_code)
                    ticket.conversation.append(
                        ConversationTurn(
                            speaker="customer",
                            message=follow_up,
                            step_index=self.step_count + 1,
                        )
                    )
                else:
                    note = "Delay / wrong action: low-quality response sent."
                    ticket.conversation.append(
                        ConversationTurn(
                            speaker="customer",
                            message="This response does not solve my issue. Please help properly.",
                            step_index=self.step_count + 1,
                        )
                    )
        elif action.action_type == "escalate":
            if not ticket or not action.escalation_target:
                reward -= 0.1
                note = "Delay / wrong action: missing escalation data."
            elif TIER_RANK[action.escalation_target] <= TIER_RANK[ticket.current_tier]:
                reward -= 0.1
                note = "Delay / wrong action: escalation target must be higher tier."
            else:
                ticket.current_tier = action.escalation_target
                ticket.escalations += 1
                ticket.has_pending_handoff_note = True
                ticket.status = "escalated"
                ticket.conversation.append(
                    ConversationTurn(
                        speaker="system",
                        message=f"Ticket escalated to {action.escalation_target.upper()}.",
                        step_index=self.step_count + 1,
                    )
                )
                reward -= 0.3
                note = "Escalation penalty applied."

        elif action.action_type == "close_ticket":
            if not ticket:
                reward -= 0.1
                note = "Delay / wrong action: ticket does not exist."
            elif ticket.status != "resolved":
                reward -= 0.1
                note = "Delay / wrong action: cannot close unresolved ticket."
            else:
                ticket.status = "closed"
                ticket.close_step = self.step_count + 1
                ticket.conversation.append(
                    ConversationTurn(
                        speaker="system",
                        message="Ticket closed successfully.",
                        step_index=self.step_count + 1,
                    )
                )
                reward += 1.0
                note = "Ticket closed successfully."

                if self._should_reopen(ticket):
                    ticket.status = "open"
                    ticket.close_step = None
                    ticket.resolution_step = None
                    ticket.reopen_count += 1
                    ticket.has_pending_handoff_note = True
                    ticket.conversation.append(
                        ConversationTurn(
                            speaker="customer",
                            message="Issue reopened: the original fix did not hold after verification.",
                            step_index=self.step_count + 1,
                        )
                    )
                    reward -= 0.65
                    note = "Ticket reopened after quality audit."
                else:
                    self.active_ticket_id = self._next_active_ticket()

        elif action.action_type == "defer":
            reward -= 0.1
            note = "Delay / wrong action: customer is waiting for support."

        else:
            reward -= 0.1
            note = "Delay / wrong action: unknown action type."

        self.step_count += 1

        unresolved = self._unresolved_ticket_count()
        if unresolved > 0:
            queue_pressure_penalty = min(0.08, 0.01 * unresolved)
            reward -= queue_pressure_penalty

        shift_note, shift_penalty = self._apply_shift_handoff_mechanic()
        if shift_note:
            note = f"{note} {shift_note}".strip()
            reward -= shift_penalty

        capacity_note, capacity_penalty = self._apply_tier_capacity_pressure()
        if capacity_note:
            note = f"{note} {capacity_note}".strip()
            reward -= capacity_penalty

        if self._all_tickets_closed():
            self.done = True
            if note:
                note += " "
            note += "All tickets are closed."

        if self.step_count >= self.selected_task.max_steps and not self.done:
            self.done = True
            reward -= 0.2
            if note:
                note += " "
            note += "Step budget exhausted."

        if self.done:
            grade = self.grade_episode(task_id=self._selected_task_id)
            info["grader"] = grade.model_dump()
            reward += 0.2 * grade.score

        self.cumulative_reward += reward
        self.last_feedback = note or "Action processed."
        self.action_history.append(
            ActionLogEntry(
                step_index=self.step_count,
                action_type=action.action_type,
                ticket_id=ticket_id,
                reward_delta=round(reward, 4),
                note=self.last_feedback,
            )
        )

        return self._observation(), round(reward, 4), self.done, info

    def grade_episode(self, task_id: str | None = None) -> GraderResponse:
        selected_task = self._tasks[task_id or self._selected_task_id]
        tickets = [self.tickets[item.ticket_id] for item in selected_task.tickets if item.ticket_id in self.tickets]

        total = len(tickets)
        closed = [ticket for ticket in tickets if ticket.status == "closed"]

        resolution_rate = (len(closed) / total) if total else 0.0

        first_response_scores: list[float] = []
        resolution_time_scores: list[float] = []
        csat_scores: list[float] = []

        for ticket in tickets:
            if ticket.first_response_step is None:
                first_response_scores.append(0.0)
            else:
                delta = ticket.first_response_step - ticket.created_step
                first_response_scores.append(max(0.0, 1.0 - max(0, delta - 1) / ticket.sla_first_response_steps))

            if ticket.close_step is None:
                resolution_time_scores.append(0.0)
            else:
                delta = ticket.close_step - ticket.created_step
                resolution_time_scores.append(max(0.0, 1.0 - max(0, delta - 1) / ticket.sla_resolution_steps))

            csat_scores.append((self._ticket_csat(ticket) - 1.0) / 4.0)

        first_response_score = (sum(first_response_scores) / len(first_response_scores)) if first_response_scores else 0.0
        resolution_time_score = (sum(resolution_time_scores) / len(resolution_time_scores)) if resolution_time_scores else 0.0

        fcr_numerator = len(
            [
                ticket
                for ticket in closed
                if len(ticket.responses) == 1
                and ticket.escalations == 0
                and ticket.first_contact_expected
            ]
        )
        fcr_rate = (fcr_numerator / len(closed)) if closed else 0.0

        csat_normalized = (sum(csat_scores) / len(csat_scores)) if csat_scores else 0.0

        high_tier_expected = [ticket for ticket in tickets if ticket.required_tier != "tier1"]
        escalated_properly = [
            ticket
            for ticket in high_tier_expected
            if TIER_RANK[ticket.current_tier] >= TIER_RANK[ticket.required_tier]
        ]
        escalation_help = (
            len(escalated_properly) / len(high_tier_expected)
            if high_tier_expected
            else 1.0
        )
        unnecessary_escalations = len(
            [ticket for ticket in tickets if ticket.required_tier == "tier1" and ticket.escalations > 0]
        )
        unnecessary_escalation_rate = self._unnecessary_escalation_rate(tickets)
        priority_fairness = self._priority_fairness(tickets)
        reopen_rate = self._reopen_rate(tickets)
        reopen_control = 1.0 - reopen_rate
        escalation_discipline = max(0.0, 1.0 - (unnecessary_escalations / max(1, total)))
        escalation_quality = 0.6 * escalation_help + 0.4 * escalation_discipline

        score = (
            (0.3 * resolution_rate)
            + (0.15 * first_response_score)
            + (0.15 * resolution_time_score)
            + (0.1 * fcr_rate)
            + (0.1 * csat_normalized)
            + (0.1 * escalation_quality)
            + (0.05 * priority_fairness)
            + (0.05 * reopen_control)
        )
        score = max(0.0, min(1.0, score))

        return GraderResponse(
            task_id=selected_task.task_id,
            score=round(score, 4),
            metrics={
                "resolution_rate": round(resolution_rate, 4),
                "first_response_score": round(first_response_score, 4),
                "resolution_time_score": round(resolution_time_score, 4),
                "fcr_rate": round(fcr_rate, 4),
                "csat_normalized": round(csat_normalized, 4),
                "escalation_quality": round(escalation_quality, 4),
                "priority_fairness": round(priority_fairness, 4),
                "unnecessary_escalation_rate": round(unnecessary_escalation_rate, 4),
                "reopen_rate": round(reopen_rate, 4),
            },
            summary=(
                f"Support quality {score:.2f}: resolution={resolution_rate:.2f}, "
                f"first_response={first_response_score:.2f}, fairness={priority_fairness:.2f}, "
                f"reopen_rate={reopen_rate:.2f}."
            ),
        )
    def observation(self) -> SupportObservation:
        return self._observation()

    def task_descriptors(self) -> list[TaskDescriptor]:
        schema = SupportAction.model_json_schema()
        return [
            TaskDescriptor(
                task_id=task.task_id,
                title=task.title,
                difficulty=task.difficulty,
                objective=task.objective,
                max_steps=task.max_steps,
                ticket_count=len(task.tickets),
                action_schema=schema,
            )
            for task in self._tasks.values()
        ]

    def ticket_summaries(self) -> list[TicketSummary]:
        rows = []
        for ticket_id in self.queue_order:
            ticket = self.tickets[ticket_id]
            rows.append(
                TicketSummary(
                    ticket_id=ticket.ticket_id,
                    subject=ticket.subject,
                    priority=ticket.priority,
                    status=ticket.status,
                    current_tier=ticket.current_tier,
                    predicted_category=ticket.predicted_category,
                    escalations=ticket.escalations,
                    reopen_count=ticket.reopen_count,
                    responses_sent=len(ticket.responses),
                )
            )
        return rows

    def ticket_detail(self, ticket_id: str) -> VisibleTicket | None:
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            return None
        return self._visible_ticket(ticket)

    def knowledge_base_records(self) -> list[KnowledgeArticle]:
        return list(self._knowledge_base.values())

    def _observation(self) -> SupportObservation:
        queue_total = len(self.queue_order)
        queue_closed = len([ticket for ticket in self.tickets.values() if ticket.status == "closed"])
        queue_escalated = len([ticket for ticket in self.tickets.values() if ticket.status == "escalated"])
        queue_open = queue_total - queue_closed

        current = self.tickets.get(self.active_ticket_id) if self.active_ticket_id else None

        return SupportObservation(
            task_id=self.selected_task.task_id,
            task_title=self.selected_task.title,
            objective=self.selected_task.objective,
            step_count=self.step_count,
            max_steps=self.selected_task.max_steps,
            queue_total=queue_total,
            queue_open=max(0, queue_open),
            queue_escalated=queue_escalated,
            queue_closed=queue_closed,
            current_ticket=self._visible_ticket(current) if current else None,
            ticket_summaries=self.ticket_summaries(),
            kpis=self._kpi_snapshot(),
            cumulative_reward=round(self.cumulative_reward, 4),
            last_feedback=self.last_feedback,
        )

    def _visible_ticket(self, ticket: TicketRuntimeState) -> VisibleTicket:
        return VisibleTicket(
            ticket_id=ticket.ticket_id,
            subject=ticket.subject,
            customer_name=ticket.customer_name,
            customer_message=ticket.customer_message,
            priority=ticket.priority,
            status=ticket.status,
            current_tier=ticket.current_tier,
            predicted_category=ticket.predicted_category,
            reopen_count=ticket.reopen_count,
            kb_consulted=list(ticket.kb_consulted),
            conversation=ticket.conversation[-8:],
        )

    def _kpi_snapshot(self) -> KpiSnapshot:
        tickets = list(self.tickets.values())
        first_response_times = [
            ticket.first_response_step - ticket.created_step
            for ticket in tickets
            if ticket.first_response_step is not None
        ]
        resolution_times = [
            ticket.close_step - ticket.created_step
            for ticket in tickets
            if ticket.close_step is not None
        ]
        closed = [ticket for ticket in tickets if ticket.status == "closed"]
        fcr = (
            len(
                [
                    ticket
                    for ticket in closed
                    if len(ticket.responses) == 1
                    and ticket.escalations == 0
                    and ticket.first_contact_expected
                ]
            )
            / len(closed)
            if closed
            else 0.0
        )

        csat_values = [self._ticket_csat(ticket) for ticket in tickets if ticket.status == "closed"]
        priority_fairness = self._priority_fairness(tickets)
        unnecessary_escalation_rate = self._unnecessary_escalation_rate(tickets)
        reopen_rate = self._reopen_rate(tickets)
        tier_queue_pressure = sum(ticket.tier_queue_wait_steps for ticket in tickets) / max(1, len(tickets))

        return KpiSnapshot(
            average_resolution_time=round(sum(resolution_times) / len(resolution_times), 3)
            if resolution_times
            else None,
            first_response_time=round(sum(first_response_times) / len(first_response_times), 3)
            if first_response_times
            else None,
            first_contact_resolution_rate=round(fcr, 4),
            csat=round(sum(csat_values) / len(csat_values), 3) if csat_values else None,
            closed_tickets=len(closed),
            escalated_tickets=len([ticket for ticket in tickets if ticket.escalations > 0]),
            priority_fairness=round(priority_fairness, 4),
            unnecessary_escalation_rate=round(unnecessary_escalation_rate, 4),
            reopen_rate=round(reopen_rate, 4),
            tier_queue_pressure=round(tier_queue_pressure, 4),
        )

    def _ticket_csat(self, ticket: TicketRuntimeState) -> float:
        score = 5.0
        if ticket.first_response_step is None:
            score -= 2.0
        else:
            first_response_delay = ticket.first_response_step - ticket.created_step
            if first_response_delay > ticket.sla_first_response_steps:
                score -= 1.0

        if ticket.close_step is None:
            score -= 1.5
        else:
            resolution_delay = ticket.close_step - ticket.created_step
            if resolution_delay > ticket.sla_resolution_steps:
                score -= 1.0

        if ticket.predicted_category != ticket.true_category:
            score -= 0.6

        score -= 0.6 * ticket.escalations
        if len(ticket.responses) > 2:
            score -= 0.4
        score -= 0.5 * ticket.reopen_count

        return max(1.0, min(5.0, score))

    def _apply_shift_handoff_mechanic(self) -> tuple[str, float]:
        new_shift = (self.step_count // self.shift_length) + 1
        if new_shift <= self.current_shift:
            return "", 0.0

        self.current_shift = new_shift
        missing_handoff_notes = 0
        for ticket in self.tickets.values():
            if ticket.status in {"open", "in_progress", "escalated"} and ticket.has_pending_handoff_note:
                missing_handoff_notes += 1

        self.shift_handoff_count += missing_handoff_notes
        if missing_handoff_notes == 0:
            return "Shift handoff clean: no unresolved-note debt.", 0.0

        penalty = min(0.3, 0.05 * missing_handoff_notes)
        return (
            f"Shift handoff penalty: {missing_handoff_notes} tickets lacked updated notes.",
            penalty,
        )

    def _apply_tier_capacity_pressure(self) -> tuple[str, float]:
        overflow = 0
        for tier in ("tier2", "tier3"):
            escalated = [
                ticket
                for ticket in self.tickets.values()
                if ticket.status == "escalated" and ticket.current_tier == tier
            ]
            capacity = self.tier_capacity[tier]
            if len(escalated) <= capacity:
                continue

            tier_overflow = len(escalated) - capacity
            overflow += tier_overflow
            for ticket in escalated:
                ticket.tier_queue_wait_steps += 1

        if overflow == 0:
            return "", 0.0

        penalty = min(0.24, 0.04 * overflow)
        return f"Tier queue pressure: overflow of {overflow} escalated tickets.", penalty

    def _should_reopen(self, ticket: TicketRuntimeState) -> bool:
        if ticket.reopen_count > 0:
            return False

        first_response_delay = (
            ticket.first_response_step - ticket.created_step
            if ticket.first_response_step is not None
            else ticket.sla_first_response_steps + 3
        )
        if first_response_delay > (ticket.sla_first_response_steps + 2):
            return True
        if len(ticket.responses) >= 3:
            return True
        if ticket.escalations > 1 and ticket.priority in {"low", "medium"}:
            return True
        return False

    def _priority_fairness(self, tickets: list[TicketRuntimeState]) -> float:
        urgent_or_high = [ticket for ticket in tickets if ticket.priority in {"urgent", "high"}]
        low_or_medium = [ticket for ticket in tickets if ticket.priority in {"low", "medium"}]
        if not urgent_or_high or not low_or_medium:
            return 1.0

        high_resolved = len([ticket for ticket in urgent_or_high if ticket.status == "closed"]) / len(urgent_or_high)
        low_resolved = len([ticket for ticket in low_or_medium if ticket.status == "closed"]) / len(low_or_medium)
        return max(0.0, 1.0 - abs(high_resolved - low_resolved))

    def _unnecessary_escalation_rate(self, tickets: list[TicketRuntimeState]) -> float:
        escalated = [ticket for ticket in tickets if ticket.escalations > 0]
        if not escalated:
            return 0.0
        unnecessary = [ticket for ticket in escalated if ticket.required_tier == "tier1"]
        return len(unnecessary) / len(escalated)

    def _reopen_rate(self, tickets: list[TicketRuntimeState]) -> float:
        if not tickets:
            return 0.0
        reopened = [ticket for ticket in tickets if ticket.reopen_count > 0]
        return len(reopened) / len(tickets)
    def _next_active_ticket(self) -> str | None:
        unresolved = [ticket_id for ticket_id in self.queue_order if self.tickets[ticket_id].status != "closed"]
        if not unresolved:
            return None
        unresolved.sort(
            key=lambda ticket_id: (
                PRIORITY_RANK[self.tickets[ticket_id].priority],
                self.queue_order.index(ticket_id),
            )
        )
        return unresolved[0]

    def _unresolved_ticket_count(self) -> int:
        return len([ticket for ticket in self.tickets.values() if ticket.status != "closed"])

    def _all_tickets_closed(self) -> bool:
        return all(ticket.status == "closed" for ticket in self.tickets.values())

    def _response_quality(self, ticket: TicketRuntimeState, response_code: str) -> float:
        if response_code == "unsupported_reply":
            return 0.0
        if response_code in ticket.preferred_response_codes:
            return 1.0

        category_fallback = {
            "billing": {"policy_explanation", "refund_processed"},
            "technical": {"troubleshoot_steps", "outage_acknowledged"},
            "account": {"password_reset_link", "verify_identity"},
            "shipping": {"shipping_update", "replace_item"},
            "general": {"apology_ack", "policy_explanation"},
        }

        if response_code in category_fallback[ticket.true_category]:
            return 0.6
        if response_code == "apology_ack":
            return 0.4
        return 0.0

    def _is_solution_valid(self, ticket: TicketRuntimeState, response_code: str) -> bool:
        if ticket.predicted_category != ticket.true_category:
            return False
        if response_code not in ticket.preferred_response_codes:
            return False
        if TIER_RANK[ticket.current_tier] < TIER_RANK[ticket.required_tier]:
            return False
        if ticket.requires_kb and not any(article in ticket.kb_consulted for article in ticket.recommended_kb_articles):
            return False
        return True

    def _render_response_text(self, response_code: str) -> str:
        templates = {
            "apology_ack": "I am sorry for the inconvenience. I am reviewing this now.",
            "refund_processed": "Your refund has been initiated and you will receive confirmation shortly.",
            "replace_item": "I have arranged a replacement order at no extra cost.",
            "shipping_update": "I checked your shipment and shared the latest courier update with ETA.",
            "password_reset_link": "I sent a secure password reset link to your registered email.",
            "verify_identity": "Please complete identity verification so we can secure and unlock your account.",
            "troubleshoot_steps": "Please follow these troubleshooting steps while I monitor the case.",
            "outage_acknowledged": "This is a known incident and our specialists are actively restoring service.",
            "policy_explanation": "I explained the policy and the next action available to resolve this.",
            "unsupported_reply": "Please wait.",
        }
        return templates[response_code]

    def _customer_follow_up(self, ticket: TicketRuntimeState, response_code: str) -> str:
        if response_code in {"apology_ack", "policy_explanation", "unsupported_reply"}:
            return "Thanks, but I still need this issue solved today."
        if ticket.current_tier == "tier1" and ticket.required_tier != "tier1":
            return "I need someone from a higher technical team to resolve this."
        if ticket.predicted_category != ticket.true_category:
            return "This sounds like a different issue than what I reported."
        return "Please confirm once this is fully closed from your side."

    def _build_knowledge_base(self) -> dict[str, KnowledgeArticle]:
        rows = [
            KnowledgeArticle(
                article_id="KB-BILL-REFUND",
                title="Refund and Charge Reversal Policy",
                category="billing",
                summary="Workflow for initiating refunds, charge reversals, and SLA expectations.",
            ),
            KnowledgeArticle(
                article_id="KB-BILL-INVOICE",
                title="Tax Invoice Correction Guide",
                category="billing",
                summary="How to correct GST/VAT invoice mismatches and compliance details.",
            ),
            KnowledgeArticle(
                article_id="KB-SHP-TRACK",
                title="Shipment Delay and Courier Escalation",
                category="shipping",
                summary="Steps for delayed packages, courier tracing, and replacement eligibility.",
            ),
            KnowledgeArticle(
                article_id="KB-SHP-DAMAGE",
                title="Damaged Product Replacement Flow",
                category="shipping",
                summary="Image proof checklist and immediate replacement process.",
            ),
            KnowledgeArticle(
                article_id="KB-ACC-RESET",
                title="Password Reset and Account Recovery",
                category="account",
                summary="Secure reset flow and account takeover prevention checklist.",
            ),
            KnowledgeArticle(
                article_id="KB-SEC-VERIFY",
                title="Identity Verification Escalation",
                category="account",
                summary="Tier-2 verification playbook for suspicious account activity.",
            ),
            KnowledgeArticle(
                article_id="KB-TECH-API",
                title="API Error Triage Runbook",
                category="technical",
                summary="Root-cause isolation for 5xx errors and integration failures.",
            ),
            KnowledgeArticle(
                article_id="KB-TECH-OUTAGE",
                title="Major Incident and Outage SOP",
                category="technical",
                summary="Tier-3 incident communication and restoration workflow.",
            ),
        ]
        return {row.article_id: row for row in rows}
    def _build_tasks(self) -> dict[str, SupportTask]:
        easy_tickets = [
            TicketScenario(
                ticket_id="E-101",
                subject="Delivery Partner order delayed beyond promised date",
                customer_name="Ram Patra",
                customer_message="My order #QK1832 was due yesterday and still has no delivery scan on BlueDart.",
                true_category="shipping",
                priority="high",
                required_tier="tier1",
                preferred_response_codes=["shipping_update"],
                recommended_kb_articles=["KB-SHP-TRACK"],
                requires_kb=False,
                first_contact_expected=True,
                sla_first_response_steps=2,
                sla_resolution_steps=6,
            ),
            TicketScenario(
                ticket_id="E-102",
                subject="Received damaged blender",
                customer_name="Pornavo",
                customer_message="The blender jar arrived cracked. I want a replacement or refund.",
                true_category="shipping",
                priority="high",
                required_tier="tier1",
                preferred_response_codes=["replace_item"],
                recommended_kb_articles=["KB-SHP-DAMAGE"],
                requires_kb=False,
                first_contact_expected=True,
                sla_first_response_steps=2,
                sla_resolution_steps=6,
            ),
            TicketScenario(
                ticket_id="E-103",
                subject="Cannot log in to account",
                customer_name="Soha Hansa",
                customer_message="I forgot my password and login keeps failing after 3 attempts.",
                true_category="account",
                priority="medium",
                required_tier="tier1",
                preferred_response_codes=["password_reset_link"],
                recommended_kb_articles=["KB-ACC-RESET"],
                requires_kb=False,
                first_contact_expected=True,
                sla_first_response_steps=2,
                sla_resolution_steps=5,
            ),
            TicketScenario(
                ticket_id="E-104",
                subject="UPI charged twice for same order",
                customer_name="Lakshman Patel",
                customer_message="I see a duplicate UPI charge for order #QK2044. Please refund one charge.",
                true_category="billing",
                priority="high",
                required_tier="tier1",
                preferred_response_codes=["refund_processed"],
                recommended_kb_articles=["KB-BILL-REFUND"],
                requires_kb=False,
                first_contact_expected=True,
                sla_first_response_steps=2,
                sla_resolution_steps=6,
            ),
        ]

        medium_tickets = [
            TicketScenario(
                ticket_id="M-201",
                subject="Android app crashes after checkout on v6.2.1",
                customer_name="Meera Reddy",
                customer_message="After latest update, checkout crashes with error 502 every time.",
                true_category="technical",
                priority="high",
                required_tier="tier2",
                preferred_response_codes=["troubleshoot_steps"],
                recommended_kb_articles=["KB-TECH-API"],
                requires_kb=True,
                first_contact_expected=False,
                sla_first_response_steps=2,
                sla_resolution_steps=8,
            ),
            TicketScenario(
                ticket_id="M-202",
                subject="Refund pending for 10 days",
                customer_name="Rahul Verma",
                customer_message="Your app says refund initiated, but bank statement still shows full charge.",
                true_category="billing",
                priority="medium",
                required_tier="tier1",
                preferred_response_codes=["refund_processed"],
                recommended_kb_articles=["KB-BILL-REFUND"],
                requires_kb=False,
                first_contact_expected=True,
                sla_first_response_steps=3,
                sla_resolution_steps=7,
            ),
            TicketScenario(
                ticket_id="M-203",
                subject="Suspicious login lockout after midnight attempts",
                customer_name="Sana Khan",
                customer_message="My account was locked after suspicious login alerts and OTP is not working.",
                true_category="account",
                priority="high",
                required_tier="tier2",
                preferred_response_codes=["verify_identity"],
                recommended_kb_articles=["KB-SEC-VERIFY"],
                requires_kb=True,
                first_contact_expected=False,
                sla_first_response_steps=2,
                sla_resolution_steps=8,
            ),
            TicketScenario(
                ticket_id="M-204",
                subject="Package marked delivered but missing",
                customer_name="Vivek Joshi",
                customer_message="Tracking says delivered at 2 PM, but I never received the package.",
                true_category="shipping",
                priority="medium",
                required_tier="tier1",
                preferred_response_codes=["shipping_update"],
                recommended_kb_articles=["KB-SHP-TRACK"],
                requires_kb=False,
                first_contact_expected=True,
                sla_first_response_steps=3,
                sla_resolution_steps=7,
            ),
            TicketScenario(
                ticket_id="M-205",
                subject="Partner API timeout in Razorpay webhook",
                customer_name="Kiran Retail Ops",
                customer_message="Webhook callbacks timeout with intermittent 504 errors since morning.",
                true_category="technical",
                priority="urgent",
                required_tier="tier2",
                preferred_response_codes=["troubleshoot_steps"],
                recommended_kb_articles=["KB-TECH-API"],
                requires_kb=True,
                first_contact_expected=False,
                sla_first_response_steps=2,
                sla_resolution_steps=9,
            ),
        ]
        hard_tickets = [
            TicketScenario(
                ticket_id="H-301",
                subject="Regional checkout outage during festival flash sale",
                customer_name="Metro Bazaar Enterprise",
                customer_message="All stores in South region cannot complete checkout. Incident started 20 minutes ago.",
                true_category="technical",
                priority="urgent",
                required_tier="tier3",
                preferred_response_codes=["outage_acknowledged"],
                recommended_kb_articles=["KB-TECH-OUTAGE"],
                requires_kb=True,
                first_contact_expected=False,
                sla_first_response_steps=1,
                sla_resolution_steps=10,
            ),
            TicketScenario(
                ticket_id="H-302",
                subject="Fraudulent high-value transactions",
                customer_name="Neha Shah",
                customer_message="I see three unauthorized high-value charges in one hour.",
                true_category="billing",
                priority="urgent",
                required_tier="tier2",
                preferred_response_codes=["verify_identity"],
                recommended_kb_articles=["KB-SEC-VERIFY", "KB-BILL-REFUND"],
                requires_kb=True,
                first_contact_expected=False,
                sla_first_response_steps=1,
                sla_resolution_steps=9,
            ),
            TicketScenario(
                ticket_id="H-303",
                subject="Enterprise SSO outage for warehouse staff",
                customer_name="Vayu Logistics IT",
                customer_message="SSO login fails for all 300 employees with token validation error.",
                true_category="account",
                priority="urgent",
                required_tier="tier3",
                preferred_response_codes=["outage_acknowledged"],
                recommended_kb_articles=["KB-TECH-OUTAGE", "KB-SEC-VERIFY"],
                requires_kb=True,
                first_contact_expected=False,
                sla_first_response_steps=1,
                sla_resolution_steps=10,
            ),
            TicketScenario(
                ticket_id="H-304",
                subject="Damaged medical item replacement needed today",
                customer_name="Arjun Mehta",
                customer_message="Insulin cooler arrived broken. I need urgent replacement for tomorrow travel.",
                true_category="shipping",
                priority="high",
                required_tier="tier2",
                preferred_response_codes=["replace_item"],
                recommended_kb_articles=["KB-SHP-DAMAGE"],
                requires_kb=True,
                first_contact_expected=False,
                sla_first_response_steps=2,
                sla_resolution_steps=8,
            ),
            TicketScenario(
                ticket_id="H-305",
                subject="Tax invoice mismatch",
                customer_name="Ujjwal Finance",
                customer_message="Invoice GST number is incorrect and blocks month-end filing.",
                true_category="billing",
                priority="high",
                required_tier="tier2",
                preferred_response_codes=["policy_explanation"],
                recommended_kb_articles=["KB-BILL-INVOICE"],
                requires_kb=True,
                first_contact_expected=False,
                sla_first_response_steps=2,
                sla_resolution_steps=8,
            ),
            TicketScenario(
                ticket_id="H-306",
                subject="Draft orders disappearing on cross-device sync",
                customer_name="Vedic Merchandising",
                customer_message="Saved draft orders vanish after sync. Need root cause and immediate fix.",
                true_category="technical",
                priority="high",
                required_tier="tier2",
                preferred_response_codes=["troubleshoot_steps"],
                recommended_kb_articles=["KB-TECH-API"],
                requires_kb=True,
                first_contact_expected=False,
                sla_first_response_steps=2,
                sla_resolution_steps=9,
            ),
            TicketScenario(
                ticket_id="H-307",
                subject="COD reconciliation mismatch across two states",
                customer_name="QuickKart Finance Control",
                customer_message="Cash-on-delivery ledger mismatches courier payout in Karnataka and Telangana.",
                true_category="billing",
                priority="high",
                required_tier="tier2",
                preferred_response_codes=["policy_explanation"],
                recommended_kb_articles=["KB-BILL-INVOICE", "KB-BILL-REFUND"],
                requires_kb=True,
                first_contact_expected=False,
                sla_first_response_steps=2,
                sla_resolution_steps=9,
            ),
            TicketScenario(
                ticket_id="H-308",
                subject="Incident bridge: OMS API and courier callback both failing",
                customer_name="Night Ops Command Center",
                customer_message="Order Management API 5xx and courier callbacks are both down; incident bridge is active.",
                true_category="technical",
                priority="urgent",
                required_tier="tier3",
                preferred_response_codes=["outage_acknowledged"],
                recommended_kb_articles=["KB-TECH-OUTAGE", "KB-TECH-API"],
                requires_kb=True,
                first_contact_expected=False,
                sla_first_response_steps=1,
                sla_resolution_steps=11,
            ),
        ]

        return {
            "easy": SupportTask(
                task_id="easy",
                title="Tier-1 Daily Queue (Consumer Retail)",
                difficulty="easy",
                objective="Resolve common consumer tickets quickly with first-contact success.",
                max_steps=24,
                tickets=easy_tickets,
            ),
            "medium": SupportTask(
                task_id="medium",
                title="Mixed Escalation Queue (Partner + Consumer)",
                difficulty="medium",
                objective="Balance first-contact fixes with selective Tier-2 escalations under realistic SLA pressure.",
                max_steps=34,
                tickets=medium_tickets,
            ),
            "hard": SupportTask(
                task_id="hard",
                title="Operations Center Incident Day (Multi-Region)",
                difficulty="hard",
                objective="Coordinate multi-region incidents, billing risk, and account outages with tier-capacity limits.",
                max_steps=56,
                tickets=hard_tickets,
            ),
        }
