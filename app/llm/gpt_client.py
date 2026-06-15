import json
from typing import Any, Dict, List

import requests

from app.core.config import GPT_API_KEY, GPT_API_URL, GPT_MODEL, GPT_TIMEOUT_SECONDS


class GPTClient:
    """Minimal GPT-5.0 HTTP client for online model providers.

    Expects `GPT_API_KEY` and optional `GPT_API_URL` in config. Uses a simple
    POST request to the Responses-style endpoint and returns the text output.
    """

    def __init__(
        self,
        api_key: str = GPT_API_KEY,
        api_url: str = GPT_API_URL,
        model: str = GPT_MODEL,
        timeout_seconds: float = GPT_TIMEOUT_SECONDS,
    ):
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate_summary(self, context: Dict[str, Any], findings: List[Dict[str, Any]]) -> str:
        """Generate a concise clinician-facing summary using GPT-5.0.

        Mirrors the previous client `generate_summary` interface so callers
        can be swapped without additional changes.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        prompt = self._summary_prompt(context, findings)
        payload = {"model": self.model, "input": prompt}

        resp = requests.post(self.api_url, headers=headers, json=payload, timeout=self.timeout_seconds)
        resp.raise_for_status()
        parsed = resp.json()

        # Support common response shapes: OpenAI Responses API or Chat completions
        if isinstance(parsed, dict):
            # Responses API: 'output' is a list of items with 'content' or 'text'
            output = parsed.get("output") or parsed.get("outputs")
            if isinstance(output, list) and output:
                parts = []
                for item in output:
                    if isinstance(item, dict):
                        # item may have 'content' which can be text or list
                        content = item.get("content") or item.get("text") or item.get("message")
                        if isinstance(content, list):
                            for c in content:
                                if isinstance(c, dict) and c.get("type") == "output_text":
                                    parts.append(c.get("text", ""))
                                elif isinstance(c, str):
                                    parts.append(c)
                        elif isinstance(content, str):
                            parts.append(content)
                    elif isinstance(item, str):
                        parts.append(item)
                if parts:
                    return "".join(parts).strip()

            # Chat/completions style: 'choices' -> [{'message': {'content': '...'}}]
            choices = parsed.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    message = first.get("message") or first.get("text") or first.get("output")
                    if isinstance(message, dict) and message.get("content"):
                        return message["content"].strip()
                    if isinstance(message, str):
                        return message.strip()

        # Fallback: return raw text body
        return json.dumps(parsed)

    def _summary_prompt(self, context: Dict[str, Any], findings: List[Dict[str, Any]]) -> str:
        ctx = context.get("context", {})
        last_bp: str = ctx.get("last_bp", "unknown")
        last_visit: str = str(ctx.get("last_visit", "unknown"))
        conditions: list = ctx.get("conditions", [])
        active_meds: list = ctx.get("active_medications", [])

        _COMORBIDITY_KEYWORDS = {
            "obesity": "obesity",
            "prediabetes": "prediabetes",
            "diabetes mellitus": "diabetes mellitus",
            "stroke": "prior stroke/TIA",
            "transient ischemic": "prior stroke/TIA",
            "chronic kidney": "CKD",
            "ischemic heart": "ischemic heart disease",
            "heart failure": "heart failure",
            "atrial fibrillation": "atrial fibrillation",
        }
        flagged: list[str] = []
        for cond in conditions:
            for keyword, label in _COMORBIDITY_KEYWORDS.items():
                if keyword in cond and label not in flagged:
                    flagged.append(label)

        comorbidity_line = ", ".join(flagged) if flagged else "none identified"
        meds_line = "; ".join(active_meds) if active_meds else "none on record"
        finding_lines = "\n".join(
            f"  [{f.get('type', '?')} / {f.get('severity', '?')}] {f.get('message', '')}"
            for f in findings
        ) or "  none"

        return (
            "You are a clinical reasoning assistant supporting a hypertension care-gap portal.\n"
            "Apply AHA/ACC 2017 guidelines: Stage 1 HTN ≥130/80 mmHg, Stage 2 HTN ≥140/90 mmHg.\n"
            "JNC 8 first-line drug classes: thiazide diuretics, ACE inhibitors, ARBs, calcium channel blockers.\n\n"
            "--- Patient Data ---\n"
            f"Last recorded BP : {last_bp} mmHg\n"
            f"Last visit       : {last_visit}\n"
            f"Active medications: {meds_line}\n"
            f"Relevant comorbidities: {comorbidity_line}\n\n"
            "--- Monitoring Findings ---\n"
            f"{finding_lines}\n\n"
            "--- Instructions ---\n"
            "1. Classify the BP gap as one of: UNTREATED (no antihypertensive on record) or "
            "TREATED-BUT-UNCONTROLLED (on antihypertensive therapy, BP still at Stage 1 or Stage 2).\n"
            "2. If a WORSENING BP_TREND finding is present, note the trajectory explicitly.\n"
            "3. Name up to two comorbidities from the list above that most elevate cardiovascular risk.\n"
            "4. Return ONLY a concise 2-3 sentence clinician-facing summary. "
            "No bullet points. No headers. Clinical language only."
        )
