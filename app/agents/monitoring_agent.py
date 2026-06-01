from datetime import date

class MonitoringAgent:
    """Rule-based hypertension monitoring."""

    def evaluate(self, observations: list[dict]) -> list[dict]:
        findings: list[dict] = []
        latest = max(observations, key=lambda item: item.get("observed_on", ""), default=None)

        if latest:
            systolic = float(latest.get("systolic", 0))
            diastolic = float(latest.get("diastolic", 0))
            if systolic >= 140 or diastolic >= 90:
                findings.append(
                    {
                        "type": "HIGH_BP",
                        "severity": "HIGH",
                        "message": f"Latest BP is elevated ({systolic}/{diastolic} mmHg).",
                    }
                )

        if latest:
            observed_on = date.fromisoformat(latest["observed_on"])
            days_since_obs = (date.today() - observed_on).days
            if days_since_obs > 30:
                findings.append(
                    {
                        "type": "MISSING_BP_DATA",
                        "severity": "MEDIUM",
                        "message": f"No blood pressure reading for {days_since_obs} days.",
                    }
                )
        else:
            findings.append(
                {
                    "type": "NO_BP_HISTORY",
                    "severity": "HIGH",
                    "message": "No blood pressure observations found.",
                }
            )

        return findings
