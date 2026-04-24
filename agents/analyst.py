import anthropic
import json

SYSTEM_PROMPT = """You are a NOC Analyst Agent. You receive a raw incident description and a triage classification.

Your job is to:
1. Identify the most likely root cause(s)
2. Assess blast radius (what else could be affected)
3. Recommend whether this requires human escalation or can be auto-remediated

Respond ONLY with a valid JSON object containing:
- root_causes: list of strings (most likely causes, ordered by probability)
- blast_radius: string describing potential downstream impact
- escalate_recommended: boolean (true = human review needed)
- escalation_reason: string (only populated if escalate_recommended is true, else empty string)
- confidence: one of "low", "medium", "high"

No preamble, no markdown fences."""


def analyst_agent(incident: str, triage: dict, api_key: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)

    context = f"""Incident description:
{incident}

Triage classification:
- Severity: {triage.get('severity')}
- Category: {triage.get('category')}
- Affected service: {triage.get('affected_service')}
- Keywords: {', '.join(triage.get('keywords', []))}
- Summary: {triage.get('summary')}"""

    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=768,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Analyze this incident:\n\n{context}"}
        ]
    )

    raw = message.content[0].text.strip()
    return json.loads(raw)
