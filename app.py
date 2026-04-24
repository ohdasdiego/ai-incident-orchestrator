import os
import json
import requests
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from agents.triage import triage_agent
from agents.analyst import analyst_agent
from agents.escalation import escalation_gate
from agents.runbook import runbook_agent
from agents.summary import summary_agent
from notifications import send_telegram

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
RUNBOOK_API_URL = os.environ.get("RUNBOOK_API_URL", "https://runbooks.ado-runner.com/query")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/orchestrate", methods=["POST"])
def orchestrate():
    data = request.get_json()
    incident_input = data.get("incident", "").strip()

    if not incident_input:
        return jsonify({"error": "No incident provided"}), 400

    def generate():
        try:
            # Stage 1: Triage
            yield _event("stage", {"stage": "triage", "status": "running"})
            triage_result = triage_agent(incident_input, ANTHROPIC_API_KEY)
            yield _event("stage_result", {"stage": "triage", "status": "done", "result": triage_result})

            # Stage 2: Analysis
            yield _event("stage", {"stage": "analyst", "status": "running"})
            analyst_result = analyst_agent(incident_input, triage_result, ANTHROPIC_API_KEY)
            yield _event("stage_result", {"stage": "analyst", "status": "done", "result": analyst_result})

            # Stage 3: Escalation Gate
            yield _event("stage", {"stage": "escalation", "status": "running"})
            escalation_result = escalation_gate(triage_result, analyst_result)
            yield _event("stage_result", {"stage": "escalation", "status": "done", "result": escalation_result})

            runbook_result = None
            if escalation_result["decision"] == "auto":
                # Stage 4a: Runbook (auto-remediation)
                yield _event("stage", {"stage": "runbook", "status": "running"})
                runbook_result = runbook_agent(analyst_result, RUNBOOK_API_URL)
                yield _event("stage_result", {"stage": "runbook", "status": "done", "result": runbook_result})
            else:
                # Stage 4b: Escalate to human
                yield _event("stage", {"stage": "runbook", "status": "skipped",
                                       "result": {"message": "Escalated to human review — runbook bypassed."}})

            # Stage 5: Summary
            yield _event("stage", {"stage": "summary", "status": "running"})
            summary_result = summary_agent(
                incident_input, triage_result, analyst_result,
                escalation_result, runbook_result, ANTHROPIC_API_KEY
            )
            yield _event("stage_result", {"stage": "summary", "status": "done", "result": summary_result})

            # Telegram notification
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                send_telegram(summary_result, escalation_result, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)

            yield _event("complete", {"status": "success"})

        except Exception as e:
            yield _event("error", {"message": str(e)})

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


def _event(event_type, data):
    return f"data: {json.dumps({'type': event_type, **data})}\n\n"


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5001)
