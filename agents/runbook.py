import requests


def runbook_agent(analyst: dict, runbook_api_url: str) -> dict:
    """
    Calls the RAG Runbook Assistant to retrieve remediation steps
    based on the analyst's root cause findings.
    """
    root_causes = analyst.get("root_causes", [])
    affected = analyst.get("blast_radius", "")

    # Build a focused query from analyst output
    query = f"Remediation steps for: {', '.join(root_causes[:2])}"
    if affected:
        query += f". Affected scope: {affected}"

    try:
        response = requests.post(
            runbook_api_url,
            json={"query": query},
            timeout=15,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        data = response.json()

        return {
            "query_sent": query,
            "runbook_response": data.get("answer") or data.get("response") or str(data),
            "source": "RAG Runbook Assistant",
            "status": "success"
        }

    except requests.exceptions.Timeout:
        return {
            "query_sent": query,
            "runbook_response": "Runbook API timed out. Manual lookup required.",
            "source": "RAG Runbook Assistant",
            "status": "timeout"
        }
    except requests.exceptions.RequestException as e:
        return {
            "query_sent": query,
            "runbook_response": f"Runbook API unavailable: {str(e)}",
            "source": "RAG Runbook Assistant",
            "status": "error"
        }
