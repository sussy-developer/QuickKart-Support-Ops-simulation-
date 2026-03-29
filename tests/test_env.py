from models import SupportAction
from support_env import CustomerSupportEnv


def test_reset_and_step_contract() -> None:
    env = CustomerSupportEnv(task_id="easy", seed=42)
    obs = env.reset(task_id="easy", seed=42)
    assert obs.task_id == "easy"
    assert obs.queue_total == 4

    target = obs.ticket_summaries[0].ticket_id
    obs, reward, done, _ = env.step(SupportAction(action_type="select_ticket", ticket_id=target))
    assert obs.current_ticket is not None
    assert done is False
    assert isinstance(reward, float)


def test_close_unresolved_ticket_penalty() -> None:
    env = CustomerSupportEnv(task_id="easy", seed=7)
    obs = env.reset(task_id="easy", seed=7)
    target = obs.ticket_summaries[0].ticket_id
    _, reward, _, _ = env.step(SupportAction(action_type="close_ticket", ticket_id=target))
    assert reward < 0.0
    assert env.tickets[target].status != "closed"


def test_shift_handoff_penalty_is_applied() -> None:
    env = CustomerSupportEnv(task_id="easy", seed=11)
    env.reset(task_id="easy", seed=11)
    reward = 0.0
    for _ in range(6):
        _, reward, _, _ = env.step(SupportAction(action_type="defer"))
    assert reward < -0.1
    assert "Shift handoff" in env.last_feedback


def test_ticket_can_reopen_after_weak_resolution_path() -> None:
    env = CustomerSupportEnv(task_id="easy", seed=42)
    obs = env.reset(task_id="easy", seed=42)
    target = obs.ticket_summaries[0].ticket_id
    runtime = env.tickets[target]

    env.step(SupportAction(action_type="select_ticket", ticket_id=target))
    env.step(
        SupportAction(
            action_type="classify_ticket",
            ticket_id=target,
            category=runtime.true_category,
        )
    )

    # Add extra customer touches before final valid solve to trigger reopen logic.
    env.step(SupportAction(action_type="respond", ticket_id=target, response_code="apology_ack"))
    env.step(SupportAction(action_type="respond", ticket_id=target, response_code="apology_ack"))
    env.step(
        SupportAction(
            action_type="respond",
            ticket_id=target,
            response_code=runtime.preferred_response_codes[0],
        )
    )
    env.step(SupportAction(action_type="close_ticket", ticket_id=target))

    assert env.tickets[target].reopen_count == 1
    assert env.tickets[target].status == "open"


def test_grader_score_range() -> None:
    env = CustomerSupportEnv(task_id="medium", seed=3)
    obs = env.reset(task_id="medium", seed=3)

    while not env.done:
        current = obs.current_ticket
        if current is None:
            pending = [row for row in obs.ticket_summaries if row.status != "closed"]
            if not pending:
                break
            obs, _, _, _ = env.step(SupportAction(action_type="select_ticket", ticket_id=pending[0].ticket_id))
            continue

        if current.predicted_category is None:
            obs, _, _, _ = env.step(
                SupportAction(
                    action_type="classify_ticket",
                    ticket_id=current.ticket_id,
                    category="technical",
                )
            )
            continue

        if current.status != "resolved":
            obs, _, _, _ = env.step(
                SupportAction(
                    action_type="respond",
                    ticket_id=current.ticket_id,
                    response_code="apology_ack",
                )
            )
            continue

        obs, _, _, _ = env.step(SupportAction(action_type="close_ticket", ticket_id=current.ticket_id))

    grade = env.grade_episode(task_id="medium")
    assert 0.0 <= grade.score <= 1.0
