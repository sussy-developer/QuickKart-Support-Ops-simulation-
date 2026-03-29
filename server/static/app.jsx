
const { useEffect, useMemo, useState } = React;

const CATEGORY_OPTIONS = ["billing", "technical", "account", "shipping", "general"];
const RESPONSE_OPTIONS = [
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
];
const ESCALATION_OPTIONS = ["tier2", "tier3"];

const api = {
  async get(path) {
    const response = await fetch(path);
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  },
  async post(path, payload = {}) {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  },
};

function App() {
  const [email, setEmail] = useState("example@gmail.com");
  const [password, setPassword] = useState("1234");
  const [auth, setAuth] = useState(null);
  const [authError, setAuthError] = useState("");

  const [tasks, setTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState("easy");
  const [kbArticles, setKbArticles] = useState([]);

  const [observation, setObservation] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [activeTicketId, setActiveTicketId] = useState(null);
  const [ticketDetail, setTicketDetail] = useState(null);

  const [category, setCategory] = useState("billing");
  const [kbArticle, setKbArticle] = useState("KB-BILL-REFUND");
  const [responseCode, setResponseCode] = useState("apology_ack");
  const [responseText, setResponseText] = useState("Manual agent reply from operations center");
  const [escalationTarget, setEscalationTarget] = useState("tier2");

  const [events, setEvents] = useState([]);
  const [grader, setGrader] = useState(null);
  const [baseline, setBaseline] = useState(null);
  const [busy, setBusy] = useState(false);

  const isDone = useMemo(() => Boolean(grader), [grader]);

  function addEvent(message) {
    const timestamp = new Date().toLocaleTimeString();
    setEvents((prev) => [`${timestamp} - ${message}`, ...prev].slice(0, 30));
  }

  async function refreshTicketData(preferredTicketId = null) {
    const ticketPayload = await api.get("/tickets");
    const rows = ticketPayload.tickets || [];
    const active = preferredTicketId || ticketPayload.active_ticket_id || rows[0]?.ticket_id || null;
    setTickets(rows);
    setActiveTicketId(active);

    if (active) {
      const details = await api.get(`/ticket/${active}`);
      setTicketDetail(details);
    } else {
      setTicketDetail(null);
    }
  }

  async function resetEpisode(taskId = selectedTask) {
    setBusy(true);
    try {
      const payload = await api.post("/reset", { task_id: taskId, seed: 42 });
      setObservation(payload.observation);
      setGrader(null);
      addEvent(`Episode reset for ${taskId.toUpperCase()} task.`);
      await refreshTicketData(payload.observation.current_ticket?.ticket_id);
    } catch (error) {
      addEvent(`Reset failed: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function sendAction(action) {
    setBusy(true);
    try {
      const payload = await api.post("/step", action);
      setObservation(payload.observation);
      addEvent(`${action.action_type} => reward ${payload.reward.toFixed(3)} | ${payload.observation.last_feedback}`);
      await refreshTicketData(payload.observation.current_ticket?.ticket_id || action.ticket_id);

      if (payload.done) {
        const finalGrade = payload.info?.grader || (await api.post("/grader", { task_id: payload.observation.task_id }));
        setGrader(finalGrade);
        addEvent(`Episode completed with grader score ${finalGrade.score.toFixed(4)}.`);
      }
    } catch (error) {
      addEvent(`Action failed: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function runBaseline() {
    setBusy(true);
    try {
      const payload = await api.post("/baseline", {});
      setBaseline(payload);
      addEvent(`Baseline finished. Average score ${payload.average_score.toFixed(4)}.`);
    } catch (error) {
      addEvent(`Baseline failed: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function bootstrapAfterLogin() {
    const [taskPayload, kbPayload] = await Promise.all([api.get("/tasks"), api.get("/knowledge-base")]);
    setTasks(taskPayload.tasks || []);
    setKbArticles(kbPayload.articles || []);

    const initialTask = taskPayload.tasks?.[0]?.task_id || "easy";
    setSelectedTask(initialTask);
    await resetEpisode(initialTask);
  }

  async function handleLogin(event) {
    event.preventDefault();
    setAuthError("");
    setBusy(true);
    try {
      const payload = await api.post("/auth/login", { email, password });
      setAuth(payload);
      addEvent(`Logged in as ${payload.user.role}.`);
      await bootstrapAfterLogin();
    } catch (error) {
      setAuthError("Login failed. Use any non-empty email/password.");
      addEvent(`Login failed: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!auth) return;
    if (!kbArticles.length) return;
    setKbArticle(kbArticles[0].article_id);
  }, [auth, kbArticles]);

  if (!auth) {
    return (
      <main className="login-shell">
        <section className="login-card">
          <p className="eyebrow">QuickKart Support AI</p>
          <h1>Operations Center Login</h1>
          <p className="subtitle">Simulate real customer-support handling with OpenEnv step/reset/state loops.</p>
          <form onSubmit={handleLogin} className="login-form">
            <label>
              Email
              <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="example@gmail.com" />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="1234"
              />
            </label>
            <button className="btn primary" type="submit" disabled={busy}>
              {busy ? "Signing in..." : "Login"}
            </button>
          </form>
          {authError && <p className="error-text">{authError}</p>}
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">OpenEnv Customer Support Simulation</p>
          <h1>QuickKart Operations Center</h1>
          <p className="subtitle">
            Login to dashboard to ticket handling to grader result. Train agents on real support KPIs: response time,
            resolution speed, FCR, and CSAT.
          </p>
        </div>

        <div className="topbar-actions">
          <span className="welcome">{auth.user.name} ({auth.user.role})</span>
          <label>
            Task
            <select value={selectedTask} onChange={(e) => setSelectedTask(e.target.value)}>
              {tasks.map((task) => (
                <option key={task.task_id} value={task.task_id}>
                  {task.task_id.toUpperCase()} - {task.title}
                </option>
              ))}
            </select>
          </label>
          <button className="btn" onClick={() => resetEpisode(selectedTask)} disabled={busy}>
            Reset Episode
          </button>
          <button className="btn ghost" onClick={runBaseline} disabled={busy}>
            Run Baseline
          </button>
        </div>
      </header>

      <section className="kpi-grid">
        <article className="kpi-card">
          <h3>Average Resolution Time</h3>
          <p>{observation?.kpis?.average_resolution_time ?? "-"}</p>
        </article>
        <article className="kpi-card">
          <h3>First Response Time</h3>
          <p>{observation?.kpis?.first_response_time ?? "-"}</p>
        </article>
        <article className="kpi-card">
          <h3>FCR Rate</h3>
          <p>{observation?.kpis ? `${(observation.kpis.first_contact_resolution_rate * 100).toFixed(1)}%` : "-"}</p>
        </article>
        <article className="kpi-card">
          <h3>CSAT</h3>
          <p>{observation?.kpis?.csat ?? "-"}</p>
        </article>
        <article className="kpi-card">
          <h3>Cumulative Reward</h3>
          <p>{observation?.cumulative_reward?.toFixed(3) ?? "0.000"}</p>
        </article>
        <article className="kpi-card">
          <h3>Priority Fairness</h3>
          <p>{observation?.kpis ? `${(observation.kpis.priority_fairness * 100).toFixed(1)}%` : "-"}</p>
        </article>
        <article className="kpi-card">
          <h3>Unnecessary Escalation</h3>
          <p>{observation?.kpis ? `${(observation.kpis.unnecessary_escalation_rate * 100).toFixed(1)}%` : "-"}</p>
        </article>
        <article className="kpi-card">
          <h3>Reopen Rate</h3>
          <p>{observation?.kpis ? `${(observation.kpis.reopen_rate * 100).toFixed(1)}%` : "-"}</p>
        </article>
        <article className="kpi-card">
          <h3>Tier Queue Pressure</h3>
          <p>{observation?.kpis?.tier_queue_pressure?.toFixed(2) ?? "0.00"}</p>
        </article>
      </section>

      <section className="workspace-grid">
        <article className="panel tickets-panel">
          <h2>Ticket Dashboard</h2>
          <div className="ticket-list">
            {tickets.map((ticket) => (
              <button
                key={ticket.ticket_id}
                className={`ticket-row ${ticket.ticket_id === activeTicketId ? "active" : ""}`}
                onClick={() => sendAction({ action_type: "select_ticket", ticket_id: ticket.ticket_id })}
                disabled={busy || ticket.status === "closed"}
              >
                <div>
                  <strong>{ticket.ticket_id}</strong>
                  <p>{ticket.subject}</p>
                </div>
                <div className="ticket-meta">
                  <span className={`badge ${ticket.priority}`}>{ticket.priority}</span>
                  <span className={`badge status-${ticket.status}`}>{ticket.status}</span>
                  {ticket.reopen_count > 0 && <span className="badge reopened">reopen x{ticket.reopen_count}</span>}
                </div>
              </button>
            ))}
          </div>
        </article>

        <article className="panel conversation-panel">
          <h2>Ticket Conversation</h2>
          {!ticketDetail && <p className="muted">Select a ticket from the dashboard.</p>}
          {ticketDetail && (
            <>
              <div className="ticket-header">
                <h3>{ticketDetail.ticket_id} - {ticketDetail.subject}</h3>
                <p>
                  Customer: <strong>{ticketDetail.customer_name}</strong> | Tier: <strong>{ticketDetail.current_tier}</strong>
                </p>
                <p>
                  Category: <strong>{ticketDetail.predicted_category || "unclassified"}</strong> | KB consulted: {ticketDetail.kb_consulted.join(", ") || "none"}
                </p>
                <p>
                  Reopen Count: <strong>{ticketDetail.reopen_count || 0}</strong>
                </p>
              </div>
              <div className="conversation-feed">
                {ticketDetail.conversation.map((turn, index) => (
                  <div key={`${turn.step_index}-${index}`} className={`chat-turn ${turn.speaker}`}>
                    <span>{turn.speaker}</span>
                    <p>{turn.message}</p>
                  </div>
                ))}
              </div>
            </>
          )}
        </article>

        <article className="panel actions-panel">
          <h2>Agent Actions</h2>
          <label>
            Category
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              {CATEGORY_OPTIONS.map((row) => (
                <option key={row} value={row}>{row}</option>
              ))}
            </select>
          </label>
          <button
            className="btn"
            disabled={busy || !activeTicketId}
            onClick={() => sendAction({ action_type: "classify_ticket", ticket_id: activeTicketId, category })}
          >
            Classify Ticket
          </button>

          <label>
            Knowledge Base Article
            <select value={kbArticle} onChange={(e) => setKbArticle(e.target.value)}>
              {kbArticles.map((row) => (
                <option key={row.article_id} value={row.article_id}>{row.article_id} - {row.title}</option>
              ))}
            </select>
          </label>
          <button
            className="btn"
            disabled={busy || !activeTicketId}
            onClick={() => sendAction({ action_type: "consult_kb", ticket_id: activeTicketId, kb_article_id: kbArticle })}
          >
            Consult KB
          </button>

          <label>
            Response Template
            <select value={responseCode} onChange={(e) => setResponseCode(e.target.value)}>
              {RESPONSE_OPTIONS.map((row) => (
                <option key={row} value={row}>{row}</option>
              ))}
            </select>
          </label>
          <label>
            Response Text
            <textarea value={responseText} onChange={(e) => setResponseText(e.target.value)} rows={3} />
          </label>
          <button
            className="btn primary"
            disabled={busy || !activeTicketId}
            onClick={() =>
              sendAction({
                action_type: "respond",
                ticket_id: activeTicketId,
                response_code: responseCode,
                response_text: responseText,
              })
            }
          >
            Send Reply
          </button>

          <label>
            Escalate To
            <select value={escalationTarget} onChange={(e) => setEscalationTarget(e.target.value)}>
              {ESCALATION_OPTIONS.map((row) => (
                <option key={row} value={row}>{row}</option>
              ))}
            </select>
          </label>
          <button
            className="btn danger"
            disabled={busy || !activeTicketId}
            onClick={() => sendAction({ action_type: "escalate", ticket_id: activeTicketId, escalation_target: escalationTarget })}
          >
            Escalate
          </button>

          <button
            className="btn success"
            disabled={busy || !activeTicketId}
            onClick={() => sendAction({ action_type: "close_ticket", ticket_id: activeTicketId })}
          >
            Close Ticket
          </button>
        </article>
      </section>

      <section className="bottom-grid">
        <article className="panel">
          <h2>Episode Result</h2>
          {!grader && <p className="muted">Complete all tickets to get final grader score.</p>}
          {grader && (
            <div className="result-box">
              <p><strong>Task:</strong> {grader.task_id}</p>
              <p><strong>Final Score:</strong> {grader.score.toFixed(4)}</p>
              <p>{grader.summary}</p>
              <pre>{JSON.stringify(grader.metrics, null, 2)}</pre>
            </div>
          )}
          {isDone && <p className="highlight">Final result generated. You can reset and run another task.</p>}
        </article>

        <article className="panel">
          <h2>Baseline Scores</h2>
          {!baseline && <p className="muted">Run baseline to compare OpenAI-enabled policy (with heuristic fallback).</p>}
          {baseline && <pre>{JSON.stringify(baseline, null, 2)}</pre>}
          {baseline && (
            <button className="btn ghost" style={{ marginTop: '1rem' }} onClick={() => setBaseline(null)}>
              Delete Scores
            </button>
          )}
        </article>

        <article className="panel">
          <h2>Event Log</h2>
          <div className="event-log">
            {events.map((line, index) => (
              <p key={index}>{line}</p>
            ))}
          </div>
          {events.length > 0 && (
            <button className="btn ghost" style={{ marginTop: '1rem' }} onClick={() => setEvents([])}>
              Delete Logs
            </button>
          )}
        </article>
      </section>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
