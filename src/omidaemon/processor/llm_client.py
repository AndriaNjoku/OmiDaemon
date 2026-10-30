"""LLM client supporting Google Gemini, OpenAI, and Anthropic backends."""

import json
from typing import Optional, Dict, Any
import httpx
from ..config import LLMConfig


class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.provider = (config.provider or "gemini").lower()
        self.api_key = config.api_key
        self.model = config.model or "gemini-2.5-flash"
        self.temperature = config.temperature

    def complete(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Execute completion request and return the text content."""
        if self.provider == "mock":
            return self._mock_completion(prompt)
        elif self.provider == "gemini":
            return self._call_gemini(prompt, system_prompt)
        elif self.provider == "openai":
            return self._call_openai(prompt, system_prompt)
        elif self.provider == "anthropic":
            return self._call_anthropic(prompt, system_prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _call_gemini(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.api_key:
            raise ValueError("Gemini API key is required. Set OMIDAEMON_LLM_API_KEY or GEMINI_API_KEY.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"SYSTEM INSTRUCTIONS:\n{system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will follow these instructions."}]})

        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.temperature,
                "responseMimeType": "application/json",
            },
        }

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini API error ({resp.status_code}): {resp.text}")
            data = resp.json()

        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Unexpected Gemini response structure: {data}") from e

    def _call_openai(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OMIDAEMON_LLM_API_KEY or OPENAI_API_KEY.")

        url = "https://api.openai.com/v1/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"OpenAI API error ({resp.status_code}): {resp.text}")
            data = resp.json()

        return data["choices"][0]["message"]["content"]

    def _call_anthropic(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.api_key:
            raise ValueError("Anthropic API key is required. Set OMIDAEMON_LLM_API_KEY or ANTHROPIC_API_KEY.")

        url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "temperature": self.temperature,
            "system": system_prompt or "",
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Anthropic API error ({resp.status_code}): {resp.text}")
            data = resp.json()

        return data["content"][0]["text"]

    def _mock_completion(self, prompt: str) -> str:
        """Mock JSON output for test suites."""
        return json.dumps(
            {
                "title": "Executive Strategy & Roadmap Sync",
                "category": "executive_strategic",
                "summary": "Reviewed quarterly engineering velocity and agreed on partner updates.",
                "key_decisions": [
                    "Approved the new architectural milestone for Q1.",
                    "Agreed to schedule a briefing with the partner next Tuesday.",
                ],
                "action_items": [
                    {
                        "task": "Draft Q1 technical specs and share with team",
                        "assignee": "CTO",
                        "priority": "high",
                        "due_date": "2026-11-05",
                        "context": "Core architecture overhaul",
                    },
                    {
                        "task": "Send partnership update email",
                        "assignee": "CEO",
                        "priority": "medium",
                        "due_date": "2026-11-03",
                        "context": "Executive alignment",
                    },
                ],
                "routing": {
                    "save_obsidian": True,
                    "send_email": True,
                    "email_recipients": ["partner", "staff"],
                    "draft_slides": False,
                    "update_calendar": True,
                    "reasoning": "High-level strategic decisions require partner and staff notification.",
                },
                "email_draft": {
                    "subject": "Executive Update: Q1 Roadmap & Priorities",
                    "body_markdown": "Hi team,\n\nHere are the notes and key decisions from our executive sync...",
                    "recipients": ["partner", "staff"],
                },
                "slides_draft": None,
                "calendar_events": [
                    {
                        "title": "Partner Follow-up Review",
                        "description": "Discuss Q1 milestone progress",
                        "start_time": "2026-11-03T10:00:00",
                        "duration_minutes": 30,
                        "attendees": ["partner@company.com"],
                    }
                ],
                "tags": ["meeting/executive", "roadmap", "strategy"],
            }
        )
