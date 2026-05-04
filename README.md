# AI Incident Orchestrator

A production-deployed multi-agent pipeline that processes infrastructure incidents end-to-end using specialized Claude AI agents — from raw alert intake through root cause analysis, escalation decision, runbook retrieval, and final incident report.

**Live:** [orchestrator.ado-runner.com](https://orchestrator.ado-runner.com)

---

## Architecture

```
Incident Input
 ↓
 Triage Agent → Severity classification, category detection
 ↓
 Analyst Agent → Root cause analysis, blast radius assessment
 ↓
[Escalation Gate] → Deterministic human-in-the-loop decision point
 ↓
 ┌────────────────────────────────┐
 │ LOW/MEDIUM │ HIGH/CRITICAL
 ↓ ↓
Runbook Agent Human Review Flag
(calls RAG Runbook API) (pipeline pauses)
 ↓ ↓
 └───────────────┬────────────────┘
 ↓
 Summary Agent → Structured incident report
 ↓
 Telegram Dispatch → Real-time NOC notification
```

Each agent is a discrete Claude API call with a scoped system prompt, receiving only the context it needs — no shared state, no framework magic.

---

## Agent Breakdown

| Agent | Model | Responsibility |
|-------|-------|----------------|
| **Triage Agent** | Claude Haiku | Classifies severity (low/medium/high/critical), category, affected service |
| **Analyst Agent** | Claude Haiku | Root cause candidates, blast radius, escalation recommendation |
| **Escalation Gate** | Deterministic Python | Enforces human-in-the-loop rules — no LLM required |
| **Runbook Agent** | HTTP client | Queries the [RAG Runbook Assistant](https://runbooks.ado-runner.com) for remediation steps |
| **Summary Agent** | Claude Haiku | Produces structured final report, dispatches Telegram notification |

### Escalation Rules

The gate is intentionally deterministic (not LLM-driven) to ensure predictable behavior:

- `critical` severity → **always escalate**
- `high` + analyst recommends escalation → **escalate**
- analyst high-confidence escalation flag → **escalate**
- everything else → **auto-remediate via Runbook Agent**

---

## Stack

- **Backend:** Python, Flask, Gunicorn
- **AI:** Anthropic Claude Haiku (`claude-haiku-4-5-20251001`)
- **RAG Integration:** [RAG Runbook Assistant](https://runbooks.ado-runner.com) (Project #4)
- **Notifications:** Telegram Bot API
- **Streaming:** Server-Sent Events (SSE) for real-time pipeline visibility
- **Infrastructure:** Nginx, systemd, Cloudflare

---

## Integration with ADOstack

This project is the convergence point of the ADOstack infrastructure suite:

- **AI Infra Monitor** (Project #1) generates alerts → feeds into incident input
- **AI Incident Logger** (Project #2) logs structured incidents → can pipe directly to orchestrator
- **RAG Runbook Assistant** (Project #4) → called by Runbook Agent for remediation
- **Telegram** → unified notification channel across all projects

---

## Deployment

### 1. Clone and install

```bash
git clone https://github.com/ohdasdiego/ai-incident-orchestrator
cd ai-incident-orchestrator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment variables

```bash
export ANTHROPIC_API_KEY=your_key
export TELEGRAM_BOT_TOKEN=your_token
export TELEGRAM_CHAT_ID=your_chat_id
export RUNBOOK_API_URL=https://runbooks.ado-runner.com/query
```

### 3. Systemd service

```bash
sudo cp ai-incident-orchestrator.service /etc/systemd/system/
sudo systemctl enable ai-incident-orchestrator
sudo systemctl start ai-incident-orchestrator
```

### 4. Nginx

```bash
sudo cp nginx.conf /etc/nginx/sites-available/orchestrator.ado-runner.com
sudo ln -s /etc/nginx/sites-available/orchestrator.ado-runner.com /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

> **Note:** The Nginx config disables proxy buffering (`proxy_buffering off`) — required for SSE streaming to work correctly through the reverse proxy.

---

## Why No Framework?

This pipeline is intentionally built with raw Python + the Anthropic SDK rather than LangChain, LlamaIndex, or similar orchestration frameworks. The goal is demonstrable understanding of agentic patterns — context passing, prompt scoping, deterministic gates, tool calls — without framework abstraction hiding what's happening.

---

## ADOStack

| # | Project | Live | Role |
|---|---------|------|------|
| 1 | [AI Infra Monitor](https://github.com/ohdasdiego/ai-infra-monitor) | [monitor.ado-runner.com](https://monitor.ado-runner.com) | Metric collection + AI health analysis |
| 2 | [AI Incident Logger](https://github.com/ohdasdiego/ai-incident-logger) | [incidents.ado-runner.com](https://incidents.ado-runner.com) | Threshold alerting + incident records |
| 3 | [Code Auditor](https://github.com/ohdasdiego/code-auditor) | CLI | AI-powered code review |
| 4 | [RAG Runbook Assistant](https://github.com/ohdasdiego/rag-runbook-assistant) | [runbooks.ado-runner.com](https://runbooks.ado-runner.com) | Vector search over IT runbooks |
| 5 | [K8s Event Summarizer](https://github.com/ohdasdiego/k8s-event-summarizer) | [k8s.ado-runner.com](https://k8s.ado-runner.com) | Kubernetes cluster health digests |
| **6** | **AI Incident Orchestrator** | **[orchestrator.ado-runner.com](https://orchestrator.ado-runner.com)** | **← You are here** |
| 7 | [On-Call Assistant](https://github.com/ohdasdiego/oncall-assistant) | [oncall.ado-runner.com](https://oncall.ado-runner.com) | Incident response + escalation routing |

---

## Roadmap

- [ ] Scheduled triggers — auto-run pipeline on new incidents from ai-incident-logger instead of manual input only
- [ ] Pipeline history log — persist past runs to SQLite with searchable archive and replay
- [ ] Feedback loop — auto-create structured incidents in ai-incident-logger from orchestrator output
- [ ] Confidence scoring UI — visualize each agent’s confidence level alongside its output
- [ ] Slack/PagerDuty notification support alongside Telegram
- [ ] Custom escalation thresholds — per-incident override of severity rules via UI
- [ ] Multi-incident batch mode — process a queue of alerts in sequence with summary rollup
- [ ] Agent output diffing — compare results across multiple runs of the same incident
