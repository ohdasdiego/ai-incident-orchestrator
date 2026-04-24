import anthropic
import json

SYSTEM_PROMPT = """You are a NOC Triage Agent. Your job is to classify incoming incidents quickly and accurately.

Given an incident description, extract:
- severity: one of "low", "medium", "high", "critical"
- category: one of "infrastructure", "application", "network", "security", "database", "unknown"
- affected_service: the primary service or component affected
- keywords: list of 3-5 relevant technical keywords
- summary: one sentence describing the incident

Respond ONLY with a valid JSON object. No preamble, no markdown fences."""


def triage_agent(incident: str, api_key: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Triage this incident:\n\n{incident}"}
        ]
    )

    raw = message.content[0].text.strip()
    return json.loads(raw)
