from datetime import date

# keyword → drug class; used by both the active-antihypertensive check and the
# resistant-hypertension class counter so the two stay in sync.
_DRUG_CLASS_MAP: dict[str, str] = {
    "lisinopril": "ACE_INHIBITOR",
    "enalapril": "ACE_INHIBITOR",
    "ramipril": "ACE_INHIBITOR",
    "captopril": "ACE_INHIBITOR",
    "benazepril": "ACE_INHIBITOR",
    "quinapril": "ACE_INHIBITOR",
    "losartan": "ARB",
    "valsartan": "ARB",
    "irbesartan": "ARB",
    "olmesartan": "ARB",
    "telmisartan": "ARB",
    "hydrochlorothiazide": "THIAZIDE",
    "chlorthalidone": "THIAZIDE",
    "indapamide": "THIAZIDE",
    "amlodipine": "CCB",
    "verapamil": "CCB",
    "diltiazem": "CCB",
    "nifedipine": "CCB",
    "felodipine": "CCB",
    "metoprolol": "BETA_BLOCKER",
    "carvedilol": "BETA_BLOCKER",
    "atenolol": "BETA_BLOCKER",
    "bisoprolol": "BETA_BLOCKER",
    "propranolol": "BETA_BLOCKER",
    "labetalol": "BETA_BLOCKER",
    "furosemide": "LOOP_DIURETIC",
    "bumetanide": "LOOP_DIURETIC",
    "torsemide": "LOOP_DIURETIC",
    "doxazosin": "ALPHA_BLOCKER",
    "prazosin": "ALPHA_BLOCKER",
    "terazosin": "ALPHA_BLOCKER",
    "hydralazine": "VASODILATOR",
    "minoxidil": "VASODILATOR",
}

# Flat keyword tuple derived from _DRUG_CLASS_MAP — used for the active-medication check.
_ANTIHYPERTENSIVE_KEYWORDS = tuple(_DRUG_CLASS_MAP.keys())


def _has_active_antihypertensive(medications: list[dict]) -> bool:
    for med in medications:
        if med.get("status") != "active":
            continue
        display = (med.get("display") or "").lower()
        if any(kw in display for kw in _ANTIHYPERTENSIVE_KEYWORDS):
            return True
    return False


def _count_antihypertensive_classes(medications: list[dict]) -> int:
    classes: set[str] = set()
    for med in medications:
        display = (med.get("display") or "").lower()
        for keyword, drug_class in _DRUG_CLASS_MAP.items():
            if keyword in display:
                classes.add(drug_class)
                break
    return len(classes)


class MonitoringAgent:
    """Rule-based hypertension monitoring."""

    def evaluate(self, observations: list[dict], medications: list[dict] | None = None) -> list[dict]:
        if medications is None:
            medications = []
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
            if systolic >= 130 and not _has_active_antihypertensive(medications):
                findings.append(
                    {
                        "type": "UNTREATED_HYPERTENSION",
                        "severity": "HIGH",
                        "message": (
                            f"BP is {systolic}/{diastolic} mmHg with no active "
                            "antihypertensive medications on record."
                        ),
                    }
                )

        n_classes = _count_antihypertensive_classes(medications)
        if n_classes >= 4:
            findings.append(
                {
                    "type": "RESISTANT_HYPERTENSION",
                    "severity": "HIGH",
                    "message": (
                        f"Patient is on {n_classes} distinct antihypertensive drug "
                        "classes, meeting the operational definition of resistant hypertension."
                    ),
                }
            )

        sorted_obs = sorted(observations, key=lambda x: x.get("observed_on", ""))
        if len(sorted_obs) >= 3:
            last3 = sorted_obs[-3:]
            systolics = [float(o["systolic"]) for o in last3]
            avg_delta = (systolics[-1] - systolics[0]) / (len(last3) - 1)
            if avg_delta > 5:
                trend, severity = "WORSENING", "HIGH"
            elif avg_delta < -5:
                trend, severity = "IMPROVING", "LOW"
            else:
                trend, severity = "STABLE", "LOW"
            findings.append(
                {
                    "type": "BP_TREND",
                    "severity": severity,
                    "message": (
                        f"BP trend over last 3 readings is {trend} "
                        f"(avg Δ {avg_delta:+.1f} mmHg/reading)."
                    ),
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
