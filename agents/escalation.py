def escalation_gate(triage: dict, analyst: dict) -> dict:
    """
    Deterministic escalation decision based on triage severity + analyst recommendation.
    
    Rules:
    - critical severity → always escalate
    - high severity + analyst recommends escalation → escalate
    - analyst recommends escalation with high confidence → escalate
    - everything else → auto-remediate
    """
    severity = triage.get("severity", "low")
    escalate_recommended = analyst.get("escalate_recommended", False)
    confidence = analyst.get("confidence", "low")
    escalation_reason = analyst.get("escalation_reason", "")

    if severity == "critical":
        return {
            "decision": "escalate",
            "reason": f"Critical severity — requires human review. {escalation_reason}".strip(),
            "severity": severity
        }

    if severity == "high" and escalate_recommended:
        return {
            "decision": "escalate",
            "reason": f"High severity with analyst escalation flag. {escalation_reason}".strip(),
            "severity": severity
        }

    if escalate_recommended and confidence == "high":
        return {
            "decision": "escalate",
            "reason": f"Analyst high-confidence escalation recommendation. {escalation_reason}".strip(),
            "severity": severity
        }

    return {
        "decision": "auto",
        "reason": "Within auto-remediation threshold — proceeding with runbook lookup.",
        "severity": severity
    }
