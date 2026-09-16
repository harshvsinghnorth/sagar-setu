"""The LLM behind one small interface. Provider is a config choice, not an architecture
choice: the model only plans and explains (CLAUDE.md rule 1), so swapping it changes nothing
about what the system decides.

Providers: Gemini (free tier — the default), Anthropic (optional), Ollama (local, offline),
and `none`, which raises `LLMUnavailable` so callers fall back to deterministic templates.
Structured output is done the portable way: schema in the prompt, `pydantic` validation on
the way out, one retry with the validation error. Works identically on every provider.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import AsyncIterator
from typing import Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from marine.config import settings

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LLMUnavailable(Exception):
    """No provider configured, or the provider failed. Callers degrade, never crash."""


class LLM(Protocol):
    name: str

    async def complete(
        self, system: str, user: str, *, json_mode: bool = False, max_tokens: int = 1024
    ) -> str: ...

    def stream(self, system: str, user: str, *, max_tokens: int = 1024) -> AsyncIterator[str]: ...


# -- Gemini (REST; no SDK dependency) -------------------------------------------------------


class GeminiLLM:
    name = "gemini"

    def __init__(self, api_key: str, model: str, *, thinking: bool = False):
        self.api_key, self.model, self.thinking = api_key, model, thinking
        self.base = f"https://generativelanguage.googleapis.com/v1beta/models/{model}"

    def _body(self, system: str, user: str, json_mode: bool, max_tokens: int) -> dict:
        cfg: dict = {"maxOutputTokens": max_tokens, "temperature": 0.2}
        if json_mode:
            cfg["responseMimeType"] = "application/json"
        if not self.thinking:
            cfg["thinkingConfig"] = {"thinkingBudget": 0}
        return {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": cfg,
        }

    async def complete(self, system, user, *, json_mode=False, max_tokens=1024) -> str:
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout_s) as c:
                r = await c.post(
                    f"{self.base}:generateContent",
                    headers={"x-goog-api-key": self.api_key},
                    json=self._body(system, user, json_mode, max_tokens),
                )
        except httpx.HTTPError as e:
            raise LLMUnavailable(f"gemini: {type(e).__name__}") from e
        if r.status_code != 200:
            raise LLMUnavailable(f"gemini: HTTP {r.status_code} {r.text[:200]}")
        try:
            text = "".join(p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"])
        except (KeyError, IndexError, ValueError) as e:
            raise LLMUnavailable(f"gemini: malformed response ({e})") from e
        log.info("gemini complete %d ms", (time.perf_counter() - t0) * 1000)
        return text

    async def stream(self, system, user, *, max_tokens=1024) -> AsyncIterator[str]:
        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout_s) as c:
                async with c.stream(
                    "POST",
                    f"{self.base}:streamGenerateContent?alt=sse",
                    headers={"x-goog-api-key": self.api_key},
                    json=self._body(system, user, False, max_tokens),
                ) as r:
                    if r.status_code != 200:
                        raise LLMUnavailable(f"gemini stream: HTTP {r.status_code}")
                    async for line in r.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        try:
                            chunk = json.loads(line[6:])
                            for p in chunk["candidates"][0]["content"]["parts"]:
                                if p.get("text"):
                                    yield p["text"]
                        except (KeyError, IndexError, ValueError):
                            continue
        except httpx.HTTPError as e:
            raise LLMUnavailable(f"gemini stream: {type(e).__name__}") from e


# -- Ollama (local, offline) ---------------------------------------------------------------


class OllamaLLM:
    name = "ollama"

    def __init__(self, url: str, model: str):
        self.url, self.model = url.rstrip("/"), model

    async def complete(self, system, user, *, json_mode=False, max_tokens=1024) -> str:
        body = {
            "model": self.model,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": max_tokens},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        if json_mode:
            body["format"] = "json"
        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout_s * 3) as c:
                r = await c.post(f"{self.url}/api/chat", json=body)
        except httpx.HTTPError as e:
            raise LLMUnavailable(f"ollama: {type(e).__name__} (is `ollama serve` running?)") from e
        if r.status_code != 200:
            raise LLMUnavailable(f"ollama: HTTP {r.status_code}")
        return r.json()["message"]["content"]

    async def stream(self, system, user, *, max_tokens=1024) -> AsyncIterator[str]:
        body = {
            "model": self.model,
            "stream": True,
            "options": {"temperature": 0.2, "num_predict": max_tokens},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout_s * 3) as c:
                async with c.stream("POST", f"{self.url}/api/chat", json=body) as r:
                    async for line in r.aiter_lines():
                        if line:
                            yield json.loads(line).get("message", {}).get("content", "")
        except httpx.HTTPError as e:
            raise LLMUnavailable(f"ollama stream: {type(e).__name__}") from e


# -- Anthropic (optional; paid) ------------------------------------------------------------


class AnthropicLLM:
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover
            raise LLMUnavailable("anthropic SDK not installed: uv sync --extra anthropic") from e
        self.client = anthropic.AsyncAnthropic(api_key=api_key, timeout=settings.llm_timeout_s)
        self.model = model

    async def complete(self, system, user, *, json_mode=False, max_tokens=1024) -> str:
        import anthropic

        if json_mode:
            system = system + "\n\nRespond with a single JSON object and nothing else."
        try:
            r = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.APIError as e:
            raise LLMUnavailable(f"anthropic: {type(e).__name__}") from e
        return "".join(b.text for b in r.content if b.type == "text")

    async def stream(self, system, user, *, max_tokens=1024) -> AsyncIterator[str]:
        import anthropic

        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            ) as s:
                async for text in s.text_stream:
                    yield text
        except anthropic.APIError as e:
            raise LLMUnavailable(f"anthropic stream: {type(e).__name__}") from e


# -- none ------------------------------------------------------------------------------------


class NoLLM:
    name = "none"

    async def complete(self, system, user, *, json_mode=False, max_tokens=1024) -> str:
        raise LLMUnavailable("no LLM provider configured (LLM_PROVIDER=none)")

    async def stream(self, system, user, *, max_tokens=1024) -> AsyncIterator[str]:
        raise LLMUnavailable("no LLM provider configured (LLM_PROVIDER=none)")
        yield ""  # pragma: no cover — makes this an async generator


# -- selection and structured output -------------------------------------------------------


def get_llm(provider: str | None = None, *, thinking: bool = False) -> LLM:
    p = (provider or settings.llm_provider).lower()
    if p == "auto":
        p = (
            "gemini"
            if settings.gemini_api_key
            else "anthropic"
            if settings.anthropic_api_key
            else "none"
        )
    if p == "gemini":
        if not settings.gemini_api_key:
            raise LLMUnavailable("GEMINI_API_KEY not set")
        return GeminiLLM(settings.gemini_api_key, settings.gemini_model, thinking=thinking)
    if p == "anthropic":
        if not settings.anthropic_api_key:
            raise LLMUnavailable("ANTHROPIC_API_KEY not set")
        return AnthropicLLM(settings.anthropic_api_key, settings.anthropic_model)
    if p == "ollama":
        return OllamaLLM(settings.ollama_url, settings.ollama_model)
    return NoLLM()


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def extract_json(text: str) -> dict:
    """Tolerate code fences and leading prose; find the first {...} object."""
    text = _FENCE.sub("", text.strip())
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in response")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("unterminated JSON object")


async def complete_structured(
    llm: LLM, system: str, user: str, model: type[T], *, max_tokens: int = 1024
) -> T:
    """Schema-in-prompt structured output with pydantic validation and one corrective retry.
    A malformed plan fails loudly here, at the boundary — never as a wrong number downstream."""
    schema = json.dumps(model.model_json_schema(), ensure_ascii=False)
    sys_full = f"{system}\n\nReturn ONLY a JSON object matching this JSON Schema:\n{schema}"
    text = await llm.complete(sys_full, user, json_mode=True, max_tokens=max_tokens)
    try:
        return model.model_validate(extract_json(text))
    except (ValidationError, ValueError) as first:
        log.warning("structured output invalid, retrying once: %s", str(first)[:200])
        fix = (
            f"{user}\n\nYour previous reply was invalid: {str(first)[:600]}\n"
            "Reply again with a corrected JSON object only."
        )
        text = await llm.complete(sys_full, fix, json_mode=True, max_tokens=max_tokens)
        try:
            return model.model_validate(extract_json(text))
        except (ValidationError, ValueError) as second:
            raise LLMUnavailable(
                f"{llm.name}: structured output failed twice: {second}"
            ) from second
