from __future__ import annotations

import json
import os
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class DeepSeekClient:
    def __init__(self, api_key: str | None = None, api_url: str | None = None, model: str = "deepseek-chat"):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.api_url = api_url or os.getenv("DEEPSEEK_API_URL")
        self.model = model
        if not self.api_key or not self.api_url:
            raise ValueError("DeepSeekClient requires DEEPSEEK_API_KEY and DEEPSEEK_API_URL")

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.0) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        data = json.dumps(payload).encode("utf-8")
        req = Request(
            self.api_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                parsed = json.loads(body)
        except HTTPError as e:
            raise RuntimeError(f"DeepSeek API HTTPError: {e.code} {e.reason}") from e
        except URLError as e:
            raise RuntimeError(f"DeepSeek API connection error: {e.reason}") from e

        try:
            return parsed["choices"][0]["message"]["content"].strip()
        except Exception as e:  # noqa: B902
            raise RuntimeError("Unexpected DeepSeek response format") from e
