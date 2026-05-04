import requests


def send_telegram(summary: dict, escalation: dict, token: str, chat_id: str):
    """Send incident summary to Telegram channel."""
    decision = escalation.get("decision", "auto")
    status_label = "[ESCALATE]" if decision == "escalate" else "[AUTO]"
    severity = summary.get("severity", "unknown").upper()

    lines = [
        f"{status_label} *INCIDENT REPORT — {severity}*",
        f"*{summary.get('title', 'Incident')}*",
        "",
        f"*Status:* {summary.get('status', '—')}",
        f"*Root Cause:* {summary.get('root_cause', '—')}",
        "",
        f"*Summary:*",
        summary.get("executive_summary", ""),
    ]

    next_steps = summary.get("next_steps", [])
    if next_steps:
        lines.append("")
        lines.append("*Next Steps:*")
        for step in next_steps[:3]:
            lines.append(f"• {step}")

    message = "\n".join(lines)

    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            },
            timeout=10
        )
    except Exception as e:
        print(f"Telegram notification failed: {e}")
