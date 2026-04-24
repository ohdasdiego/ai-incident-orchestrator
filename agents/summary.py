import anthropic
import re
import json

SYSTEM_PROMPT = """You are a NOC Summary Agent. You receive the full output of an incident orchestration pipeline and produce a final structured incident report.

Your report must be clear, concise, and actionable. Write for a NOC team lead who needs a quick brief.

Respond ONLY with a valid JSON object containing:
- title: short incident title (max 10 words)
- severity: the confirmed severity level
- status: one of "auto-remediated", "escalated", "pending-review"
- executive_summary: 2-3 sentence plain-English summary of what happened and what was done
- root_cause: the most likely root cause (one sentence)
- actions_taken: list of strings describing what the pipeline did
- next_steps: list of strings with recommended follow-up actions
- runbook_steps: string with remediation steps if available, else empty string

No preamble, no markdown fences."""


def summary_agent(
    incident: str,
    triage: dict,
    analyst: dict,
    escalation: dict,
    runbook: dict | None,
    api_key: str
) -> dict:
    client = anthropic.Anthropic(api_key=api_key)

    runbook_text = ""
    if runbook:
        runbook_text = f"\nRunbook Agent Output:\n{json.dumps(runbook, indent=2)}"

    context = f"""Original Incident:
{incident}

Triage Agent Output:
{json.dumps(triage, indent=2)}

Analyst Agent Output:
{json.dumps(analyst, indent=2)}

Escalation Gate Decision:
{json.dumps(escalation, indent=2)}
{runbook_text}"""

    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Generate the final incident report:\n\n{context}"}
        ]
    )

    raw = message.content[0].text.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw)
    if match:
        raw = match.group(1).strip()
    return json.loads(raw)
