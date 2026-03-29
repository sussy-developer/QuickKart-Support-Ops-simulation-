from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

try:
    from openenv.core.env_server.types import Action, Observation, State  # type: ignore
except ImportError:  # pragma: no cover
    Action = BaseModel
    Observation = BaseModel
    State = BaseModel


TicketCategory = Literal["billing", "technical", "account", "shipping", "general"]
TicketPriority = Literal["low", "medium", "high", "urgent"]
TicketStatus = Literal["open", "in_progress", "escalated", "resolved", "closed"]
SupportTier = Literal["tier1", "tier2", "tier3"]
ResponseCode = Literal[
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
]
ActionType = Literal[
    "select_ticket",
    "classify_ticket",
    "consult_kb",
    "respond",
    "escalate",
    "close_ticket",
    "defer",
]


class KnowledgeArticle(BaseModel):
    article_id: str
    title: str
    category: TicketCategory
    summary: str


class ConversationTurn(BaseModel):
    speaker: Literal["customer", "agent", "system"]
    message: str
    step_index: int = Field(ge=0)


class TicketSummary(BaseModel):
    ticket_id: str
    subject: str
    priority: TicketPriority
    status: TicketStatus
    current_tier: SupportTier
    predicted_category: TicketCategory | None = None
    escalations: int = Field(ge=0)
    reopen_count: int = Field(default=0, ge=0)
    responses_sent: int = Field(ge=0)


class VisibleTicket(BaseModel):
    ticket_id: str
    subject: str
    customer_name: str
    customer_message: str
    priority: TicketPriority
    status: TicketStatus
    current_tier: SupportTier
    predicted_category: TicketCategory | None = None
    reopen_count: int = Field(default=0, ge=0)
    kb_consulted: list[str] = Field(default_factory=list)
    conversation: list[ConversationTurn] = Field(default_factory=list)


class KpiSnapshot(BaseModel):
    average_resolution_time: float | None = None
    first_response_time: float | None = None
    first_contact_resolution_rate: float = Field(ge=0.0, le=1.0)
    csat: float | None = None
    closed_tickets: int = Field(ge=0)
    escalated_tickets: int = Field(ge=0)
    priority_fairness: float = Field(default=1.0, ge=0.0, le=1.0)
    unnecessary_escalation_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    reopen_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    tier_queue_pressure: float = Field(default=0.0, ge=0.0)


class SupportAction(Action):
    action_type: ActionType
    ticket_id: str | None = None
    category: TicketCategory | None = None
    kb_article_id: str | None = None
    response_code: ResponseCode | None = None
    response_text: str | None = Field(default=None, max_length=600)
    escalation_target: SupportTier | None = None

    @model_validator(mode="after")
    def validate_action_payload(self) -> "SupportAction":
        if self.action_type == "select_ticket" and not self.ticket_id:
            raise ValueError("ticket_id is required for select_ticket")
        if self.action_type == "classify_ticket":
            if not self.ticket_id:
                raise ValueError("ticket_id is required for classify_ticket")
            if not self.category:
                raise ValueError("category is required for classify_ticket")
        if self.action_type == "consult_kb":
            if not self.ticket_id:
                raise ValueError("ticket_id is required for consult_kb")
            if not self.kb_article_id:
                raise ValueError("kb_article_id is required for consult_kb")
        if self.action_type == "respond":
            if not self.ticket_id:
                raise ValueError("ticket_id is required for respond")
            if not self.response_code:
                raise ValueError("response_code is required for respond")
        if self.action_type == "escalate":
            if not self.ticket_id:
                raise ValueError("ticket_id is required for escalate")
            if not self.escalation_target:
                raise ValueError("escalation_target is required for escalate")
        if self.action_type == "close_ticket" and not self.ticket_id:
            raise ValueError("ticket_id is required for close_ticket")
        return self


class SupportObservation(Observation):
    task_id: str
    task_title: str
    objective: str
    step_count: int = Field(ge=0)
    max_steps: int = Field(ge=1)
    queue_total: int = Field(ge=0)
    queue_open: int = Field(ge=0)
    queue_escalated: int = Field(ge=0)
    queue_closed: int = Field(ge=0)
    current_ticket: VisibleTicket | None = None
    ticket_summaries: list[TicketSummary] = Field(default_factory=list)
    kpis: KpiSnapshot
    cumulative_reward: float = 0.0
    last_feedback: str = "Episode initialized"


class ActionLogEntry(BaseModel):
    step_index: int = Field(ge=0)
    action_type: ActionType
    ticket_id: str | None = None
    reward_delta: float
    note: str


class TicketRuntimeState(BaseModel):
    ticket_id: str
    subject: str
    customer_name: str
    customer_message: str
    true_category: TicketCategory
    required_tier: SupportTier
    preferred_response_codes: list[ResponseCode]
    recommended_kb_articles: list[str]
    requires_kb: bool = False
    priority: TicketPriority
    status: TicketStatus
    current_tier: SupportTier
    predicted_category: TicketCategory | None = None
    kb_consulted: list[str] = Field(default_factory=list)
    responses: list[ResponseCode] = Field(default_factory=list)
    first_response_step: int | None = None
    resolution_step: int | None = None
    close_step: int | None = None
    reopen_count: int = Field(default=0, ge=0)
    tier_queue_wait_steps: int = Field(default=0, ge=0)
    has_pending_handoff_note: bool = False
    escalations: int = Field(default=0, ge=0)
    created_step: int = 0
    sla_first_response_steps: int = Field(ge=1)
    sla_resolution_steps: int = Field(ge=1)
    first_contact_expected: bool = True
    conversation: list[ConversationTurn] = Field(default_factory=list)


class SupportState(State):
    episode_id: str
    done: bool
    selected_task: str
    step_count: int = Field(ge=0)
    max_steps: int = Field(ge=1)
    active_ticket_id: str | None = None
    queue_order: list[str] = Field(default_factory=list)
    tickets: dict[str, TicketRuntimeState] = Field(default_factory=dict)
    cumulative_reward: float = 0.0
    action_history: list[ActionLogEntry] = Field(default_factory=list)


class StepResult(BaseModel):
    observation: SupportObservation
    reward: float
    done: bool
    info: dict[str, Any] = Field(default_factory=dict)


class ResetRequest(BaseModel):
    task_id: str = "easy"
    seed: int = 42


class GraderRequest(BaseModel):
    task_id: str | None = None


class GraderResponse(BaseModel):
    task_id: str
    score: float = Field(ge=0.0, le=1.0)
    metrics: dict[str, float] = Field(default_factory=dict)
    summary: str


class TaskDescriptor(BaseModel):
    task_id: str
    title: str
    difficulty: Literal["easy", "medium", "hard"]
    objective: str
    max_steps: int
    ticket_count: int
    action_schema: dict[str, Any]


class BaselineTaskScore(BaseModel):
    task_id: str
    score: float = Field(ge=0.0, le=1.0)
    steps_used: int = Field(ge=0)
    total_reward: float
    final_kpis: KpiSnapshot


class BaselineResponse(BaseModel):
    average_score: float = Field(ge=0.0, le=1.0)
    tasks: list[BaselineTaskScore]


class LoginRequest(BaseModel):
    email: str
    password: str


class UserProfile(BaseModel):
    name: str
    email: str
    role: Literal["agent", "admin"]


class LoginResponse(BaseModel):
    token: str
    user: UserProfile
