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
        return (
            f"Patient context JSON:\n{json.dumps(context, default=str)}\n\n"
            f"Monitoring findings JSON:\n{json.dumps(findings, default=str)}\n\n"
            "You are a clinical reasoning assistant. Return only a concise 1-2 sentence clinician-facing summary."
        )
