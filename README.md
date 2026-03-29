# QuickKart SupportOps OpenEnv

This repository is a **real-world OpenEnv environment** for training and evaluating agents on customer-support operations.

It is intentionally built like a production support floor, not a toy:
- tiered ticket routing (Tier-1 -> Tier-2 -> Tier-3)
- SLA pressure and queue aging
- knowledge-base consultation
- escalation discipline
- ticket reopen risk
- shift-handoff quality debt
- tier-capacity bottlenecks

## Why this is not a template clone

I modeled this after realistic e-commerce operations patterns (UPI disputes, courier delays, SSO incidents, incident bridge failures, COD reconciliation). The hard task includes multi-region incident traffic and constrained specialist capacity.

## OpenEnv Interface

Core loop is standard and typed:
- `POST /reset`
- `POST /step`
- `GET /state`

Pydantic models are defined in [models.py](C:\Users\biswa\OneDrive\Documents\Playground\models.py).

Environment logic is in [support_env.py](C:\Users\biswa\OneDrive\Documents\Playground\support_env.py).

## Tasks (easy -> medium -> hard)

1. `easy`: Tier-1 daily consumer queue (shipping, billing, account)
2. `medium`: mixed partner + consumer queue with selective Tier-2 escalation
3. `hard`: multi-region incident day, overlapping outages, finance control issues, strict SLAs

Each task has deterministic scenarios and deterministic grading criteria.

## Action Space

`SupportAction.action_type`:
- `select_ticket`
- `classify_ticket`
- `consult_kb`
- `respond`
- `escalate`
- `close_ticket`
- `defer`

## Reward Design

Primary shaping (requested):
- Good reply: `+0.2`
- Correct solution: `+0.5`
- Close successfully: `+1.0`
- Delay / wrong action: `-0.1`
- Escalation: `-0.3`

Additional shaping for realism:
- queue pressure penalty while backlog remains
- shift handoff penalty for unresolved notes
- tier-capacity overflow penalty for escalated queues
- reopen penalty when weak closure quality causes regression

## Grader Design (`0.0-1.0`)

Final score blends:
- resolution rate
- first-response quality
- resolution-time quality
- first-contact resolution
- CSAT normalization
- escalation quality
- priority fairness
- reopen control

Extra grader/KPI signals:
- `priority_fairness`
- `unnecessary_escalation_rate`
- `reopen_rate`
- `tier_queue_pressure`

## Additional Required Endpoints

- `GET /tasks`
- `POST /grader`
- `POST /baseline`

And app-facing endpoints:
- `POST /auth/login`
- `GET /tickets`
- `GET /ticket/{ticket_id}`
- `GET /knowledge-base`
- `GET /kpis`

## Baseline Inference

Baseline script: [baseline.py](C:\Users\biswa\OneDrive\Documents\Playground\baseline.py)

Modes:
- **OpenAI mode** if `OPENAI_API_KEY` is set (uses Chat Completions at temperature 0)
- **Heuristic fallback** if no key is available or API call fails

Run:

```bash
python baseline.py
```

Optional env vars:
- `OPENAI_API_KEY`
- `OPENAI_BASELINE_MODEL` (default `gpt-4.1-mini`)
- `OPENAI_BASELINE_TIMEOUT`
- `OPENAI_BASE_URL`

## Frontend App (login -> result)

React UI is served by FastAPI and provides:
- login page
- ticket dashboard
- conversation workspace
- action panel
- live KPI cards
- final grader output
- baseline comparison output

Files:
- [server/static/index.html](C:\Users\biswa\OneDrive\Documents\Playground\server\static\index.html)
- [server/static/app.jsx](C:\Users\biswa\OneDrive\Documents\Playground\server\static\app.jsx)
- [server/static/styles.css](C:\Users\biswa\OneDrive\Documents\Playground\server\static\styles.css)

## Setup

```bash
pip install -r requirements.txt
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Open:
- `http://localhost:8000`
- `http://localhost:8000/docs`

## Tests

```bash
python -m pytest -q tests -p no:cacheprovider
```

## Validation

```bash
python scripts/validate_submission.py
```

## Docker

```bash
docker build -t openenv-customer-support .
docker run --rm -p 8000:8000 openenv-customer-support
```

## Hugging Face Space

Repo is Docker-space ready with [openenv.yaml](C:\Users\biswa\OneDrive\Documents\Playground\openenv.yaml) + [Dockerfile](C:\Users\biswa\OneDrive\Documents\Playground\Dockerfile).
