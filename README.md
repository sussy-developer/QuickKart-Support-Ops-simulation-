<<<<<<< HEAD
# QuickKart‑Support‑Ops

**QuickKart‑Support‑Ops** is a realistic OpenEnv simulation of an e‑commerce customer‑support operations center. It mimics a production‑grade support floor with tiered ticket routing, SLA pressure, knowledge‑base consultation, escalation discipline, and shift‑handoff debt. The environment is built to train, evaluate, and benchmark AI agents (including LLM‑based policies) on real‑world support KPIs.

---

## 🎯 Main Purpose
- **Simulate authentic support workflows** – from simple Tier‑1 queries to complex multi‑region incidents.
- **Provide a unified UI** – a premium React dashboard with glass‑morphism styling, showing tickets, KPIs, and action panels.
- **Automated grading** – scores agents on response time, resolution speed, First‑Contact‑Resolution (FCR), CSAT, priority fairness, and escalation quality.
- **Baseline comparison** – a built‑in heuristic/OpenAI baseline for quick sanity checks.

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

## 🤝 Contributing
Feel free to open issues or pull requests. Contributions that add new tasks, improve UI aesthetics, or enhance the grading metrics are especially welcome.

---

*Happy hacking!*
=======
# QuickKart-Support-Ops-simulation-
>>>>>>> d782de0e5427430b50e6f756dbb7912d66f17ef1
