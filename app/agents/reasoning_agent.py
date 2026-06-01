from typing import Optional

from app.llm.gpt_client import GPTClient


class ReasoningAgent:
    """Clinical reasoning layer backed by online GPT-5.0 model."""

    def __init__(self, llm_client: Optional[GPTClient] = None):
        self.llm_client = llm_client or GPTClient()

    def summarize(self, context: dict, findings: list[dict]) -> str:
        try:
            summary = self.llm_client.generate_summary(context, findings)
            if summary:
                return summary
        except Exception:
            pass

        return self._deterministic_summary(findings)

    def _deterministic_summary(self, findings: list[dict]) -> str:
        if not findings:
            return (
                "Patient has recent blood pressure monitoring with no immediate hypertension care gaps. "
                "Continue routine follow-up and medication adherence checks."
            )

        finding_text = "; ".join(item["message"] for item in findings)
        return (
            "Patient context suggests uncontrolled or insufficiently monitored hypertension. "
            f"Key concerns: {finding_text} "
            "Recommend follow-up visit and BP management plan review."
        )
