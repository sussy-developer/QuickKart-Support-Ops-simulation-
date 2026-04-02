
# QuickKart‑Support‑Ops

## 🛒 QuickKart SupportOps OpenEnv

A real-world OpenEnv environment for training and evaluating agents on customer-support operations.
This is not a toy system — it is designed to replicate a production-grade support floor, including real operational constraints, decision trade-offs, and system pressure.

---

## 🎯 Main Purpose
- **Simulate authentic support workflows** – from simple Tier‑1 queries to complex multi‑region incidents.
- **Provide a unified UI** – a premium React dashboard with glass‑morphism styling, showing tickets, KPIs, and action panels.
- **Automated grading** – scores agents on response time, resolution speed, First‑Contact‑Resolution (FCR), CSAT, priority fairness, and escalation quality.
- **Baseline comparison** – a built‑in heuristic/OpenAI baseline for quick sanity checks.

---

## 🚀 Project Purpose

QuickKart SupportOps OpenEnv is built to:
- Train AI agents for real customer support workflows
- Simulate production-level support environments
- Evaluate decisions under SLA pressure & queue dynamics
- Benchmark agents using deterministic grading metrics

---

## 🧠 Key Features

- 🎯 Tiered ticket routing (Tier-1 → Tier-2 → Tier-3)
- ⏱ SLA pressure & queue aging
- 📚 Knowledge-base consultation
- ⚠️ Escalation discipline & penalties
- 🔁 Ticket reopen risk
- 🔄 Shift handoff quality debt
- 🚧 Tier-capacity bottlenecks
- 🌍 Multi-region incident simulation (Hard mode)

---

## 🏗️ Core Components
- Environment Engine → **support_env.py**
- Data Models → **models.py**
- API Layer → **FastAPI**
- Frontend UI → **React (served via FastAPI)**
- Baseline Agent → **baseline.py**

---

## 🛠️ Project Structure
```
Meta‑ai/
├─ server/               # FastAPI backend
│   ├─ app.py            # Entry point
│   └─ static/           # React UI (app.jsx, styles.css, signin.jsx, …)
├─ models.py             # Pydantic schemas
├─ support_env.py        # Core OpenEnv logic
├─ baseline.py           # Baseline inference
├─ requirements.txt      # Python deps
├─ Dockerfile            # Container definition
└─ README.md             # ← This file
```


---

## 🖥️ UI Overview
```
+---------------------------+   +---------------------------+
|  QuickKart Operations     |   |  Top‑bar (Dashboard)      |
|  Center Logo + Motto      |   |  - User name & role       |
|  "Login to dashboard …"   |   |  - Task selector          |
+---------------------------+   +---------------------------+
|  Login Card (centered)    |
|  • Email input            |
|  • Password input         |
|  • "Forgot password?"    |
|  • Login button (center)  |
+---------------------------+
|  Floating shapes (Cube,   |
|  Capsule, Flower)         |
+---------------------------+
|  Main App (after login)   |
|  • KPI grid               |
|  • Ticket list            |
|  • Conversation panel    |
|  • Action panel (classify,|
|    consult KB, respond,   |
|    escalate, close)       |
|  • Event log & baseline   |
+---------------------------+
```
*The login page uses a **centered card** with the logo and motto in the top‑left corner. The “Forgot password?” link sits just above the login button.*

---

## 🔘 Button Functions
| Button | Location | Action |
|--------|----------|--------|
| **Log In** | Login card | Submits credentials, creates `auth` session, then calls `bootstrapAfterLogin()` to load tasks & KB. |
| **Reset Episode** | Top‑bar | Calls `resetEpisode(selectedTask)` – re‑initialises the environment for the chosen task. |
| **Run Baseline** | Top‑bar | Executes `/baseline` endpoint, displays average score for reference. |
| **Classify Ticket** | Action panel | Sends `classify_ticket` with selected category. |
| **Consult KB** | Action panel | Sends `consult_kb` with chosen knowledge‑base article. |
| **Respond** | Action panel | Sends `respond` with selected response template and custom text. |
| **Escalate** | Action panel | Sends `escalate` to move ticket to Tier‑2/3. |
| **Close Ticket** | Action panel | Sends `close_ticket` to finalize the ticket. |
| **Delete Logs / Scores** | Bottom panels | Clears event log or baseline scores. |

---

## 🔁 Core Workflow

                 [ Reset Environment ]
                          |
                          v
                 [ Receive Tickets ]
                          |
                          v
                  [ Select Ticket ]
                          |
                          v
                 [ Classify Ticket ]
                          |
                          v
           [ Consult Knowledge Base ]
                          |
                          v
                    [ Take Action ]
                    /      |      \
                   /       |       \
                  v        v        v
           [ Respond ] [ Escalate ] [ Defer ]
                |           |           |
                v           v           v
        [ Resolve Ticket ] [ Tier 2/3 Queue ] [ Backlog Queue ]
                |           |           |
                v           v           v
         [ Close Ticket ] [ Capacity Check ] [ Queue Aging ]
                \           |           /
                 \          |          /
                  \         |         /
                   v        v        v
                 [   Grader Evaluation   ]


---





## 📈 Workflow Diagram (ASCII/Dotted Text)
```
+-------------------+      +-------------------+      +-------------------+
|   User opens      | ---> |   Login Page      | ---> |   Authenticated   |
|   https://...     |      |   (email, pwd)    |      |   Dashboard       |
+-------------------+      +-------------------+      +-------------------+
        |                         |                         |
        |                         v                         v
        |                +-------------------+   +-------------------+
        |                |   Click Log In    |   |   Invalid login   |
        |                +-------------------+   +-------------------+
        |                         |                         |
        v                         v                         |
+-------------------+   +-------------------+               |
|   Load Tasks &    |   |   Show error      | <-------------+
|   Knowledge‑Base  |   +-------------------+               |
+-------------------+                                         
        |                                                     
        v                                                     
+-------------------+      +-------------------+      +-------------------+
|   Select Task     | ---> |   Reset Episode   | ---> |   Observe State   |
+-------------------+      +-------------------+      +-------------------+
        |                         |                         |
        v                         v                         v
+-------------------+   +-------------------+   +-------------------+
|   Ticket List     |   |   Action Panel    |   |   KPI Grid        |
|   (select ticket) |   |   (classify,      |   |   (metrics)       |
|                   |   |    consult, ...) |   |                   |
+-------------------+   +-------------------+   +-------------------+
        |                         |                         |
        v                         v                         v
+-------------------+   +-------------------+   +-------------------+
|   Conversation    |   |   Send Action     |   |   Update KPIs     |
|   Panel (chat)    |   |   (API call)      |   |   (live)          |
+-------------------+   +-------------------+   +-------------------+
        |                         |                         |
        v                         v                         v
+-------------------+   +-------------------+   +-------------------+
|   Episode Done?   |<--|   Receive Reward  |<--|   Grader (final)  |
+-------------------+   +-------------------+   +-------------------+
        |
        v
+-------------------+
|   Show Grader     |
|   Score & Summary |
+-------------------+
```
*The diagram shows the high‑level flow from login → task selection → ticket handling → grading.*

---

## 📦 Running Locally
```bash
# Install dependencies (already in Dockerfile)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start the FastAPI server
uvicorn server.app:app --host 0.0.0.0 --port 8000
```
Visit `http://localhost:8000` to see the UI.

---

## 🚀 Deploy to Hugging Face Spaces (Docker)
1. Create a new **Docker** Space on Hugging Face.
2. Clone the empty repo, copy this project, commit, and push.
3. Add any needed secrets (e.g., `OPENAI_API_KEY`).
4. Hugging Face will automatically build the Dockerfile and expose port 8000.

---

## 🎮 OpenEnv Interface
```
Core Loop
POST /reset
POST /step
GET /state
```
## Additional Endpoints
```
GET /tasks
POST /grader
POST /baseline
```
## App-Facing Endpoints
```
POST /auth/login
GET /tickets
GET /ticket/{ticket_id}
GET /knowledge-base
GET /kpis
```
---


### 🎯 Task Levels

| Difficulty | Description |
| :--- | :--- |
| 🟢 Easy | Tier-1 consumer issues (shipping, billing, account) |
| 🟡 Medium | Mixed queues + selective Tier-2 escalation |
| 🔴 Hard | Multi-region incidents, outages, strict SLAs |


Each task includes deterministic scenarios + deterministic grading.

---

# 🏆 Reward Design
## Positive Rewards
- Good reply → +0.2
- Correct solution → +0.5
- Close successfully → +1.0
- 
## Penalties
- Delay / wrong action → -0.1
- Escalation → -0.3
  
## Realism-Based Penalties
- Queue pressure (backlog)
- Shift handoff quality issues
- Tier-capacity overflow
- Ticket reopen risk


---


## 🤖 Baseline Inference
```
Baseline script: baseline.py
```

## Modes
```
OpenAI Mode → Activated if OPENAI_API_KEY is set
Heuristic Mode → Fallback if API key is unavailable or request fails
```
---

## ▶️ Run
```
python baseline.py
```

---

## 🔧 Optional Environment Variables
```
OPENAI_API_KEY
OPENAI_BASELINE_MODEL=gpt-4.1-mini
OPENAI_BASELINE_TIMEOUT
OPENAI_BASE_URL
```

---

## ⚙️ Setup
Install dependencies and start the server:

```
pip install -r requirements.txt
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```
---

## 🌐 Open in Browser
```
http://localhost:8000
http://localhost:8000/docs
```

--- 

## 🧪 Tests

Run test suite:

```
python -m pytest -q tests -p no:cacheprovider
```

---

## ✅ Validation
 Validate your submission:
```
python scripts/validate_submission.py
```


## 🐳 Docker
Build and run using Docker:

```
docker build -t openenv-customer-support .
docker run --rm -p 8000:8000 openenv-customer-support
```

🤗 Hugging Face Space

This repository is Docker-ready and can be deployed directly using:
```
openenv.yaml
Dockerfile
```

---
