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

from marine import net
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


# Free-tier quotas are per model per day. When one model is exhausted (429) or overloaded
# (503) it is parked until Google says it may be retried, and the next model in the list is
# used — so one spent quota cannot take the whole assistant down mid-demo. Process-wide, so
# the API server stops hitting a dead model on every request.
_PARKED: dict[str, float] = {}  # model -> time.monotonic() after which it may be tried again
# Models that reject thinkingConfig {thinkingBudget: 0} with 400 INVALID_ARGUMENT (the
# flash-lite family does). Learned on first refusal, then omitted for that model.
_NO_THINKING_CONFIG: set[str] = set()
_RETRY_DELAY = re.compile(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"')
_FALLBACK_STATUSES = (429, 503)


def _park(model: str, status: int, body: str) -> None:
    m = _RETRY_DELAY.search(body)
    secs = float(m.group(1)) if m else 60.0
    _PARKED[model] = time.monotonic() + secs
    log.warning("gemini %s returned %d; parked for %.0f s, falling back", model, status, secs)


class GeminiLLM:
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        thinking: bool = False,
        fallbacks: tuple[str, ...] | list[str] = (),
    ):
        self.api_key, self.model, self.thinking = api_key, model, thinking
        self.models = [model] + [f for f in fallbacks if f and f != model]
        self.transport: httpx.AsyncBaseTransport | None = None  # tests inject a mock here

    def _url(self, model: str, method: str) -> str:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:{method}"

    def _candidates(self) -> list[str]:
        now = time.monotonic()
        live = [m for m in self.models if _PARKED.get(m, 0.0) <= now]
        # Everything parked: still try the primary, so the caller gets the real error.
        return live or self.models[:1]

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=settings.llm_timeout_s, transport=self.transport)

    def _rejects_thinking_config(self, model: str, status: int, body: str) -> bool:
        """True (and remembered) if this 400 is the model refusing thinkingBudget=0."""
        if (
            status == 400
            and not self.thinking
            and model not in _NO_THINKING_CONFIG
            and "invalid argument" in body.lower()
        ):
            _NO_THINKING_CONFIG.add(model)
            log.warning("gemini %s rejects thinkingConfig; resending without it", model)
            return True
        return False

    def _body(self, model: str, system: str, user: str, json_mode: bool, max_tokens: int) -> dict:
        cfg: dict = {"maxOutputTokens": max_tokens, "temperature": 0.2}
        if json_mode:
            cfg["responseMimeType"] = "application/json"
        if not self.thinking and model not in _NO_THINKING_CONFIG:
            cfg["thinkingConfig"] = {"thinkingBudget": 0}
        return {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": cfg,
        }

    def _check_reachable(self) -> None:
        """Fail at once if the API host failed to connect moments ago (marine.net breaker)."""
        skipped = net.skip_reason(self._url(self.models[0], "generateContent"))
        if skipped:
            raise LLMUnavailable(f"gemini: host unreachable ({skipped})")

    async def complete(self, system, user, *, json_mode=False, max_tokens=1024) -> str:
        t0 = time.perf_counter()
        last = ""
        self._check_reachable()
        for model in self._candidates():
            url = self._url(model, "generateContent")
            try:
                async with self._client() as c:
                    for _attempt in range(2):
                        r = await c.post(
                            url,
                            headers={"x-goog-api-key": self.api_key},
                            json=self._body(model, system, user, json_mode, max_tokens),
                        )
                        if not self._rejects_thinking_config(model, r.status_code, r.text):
                            break
            except httpx.HTTPError as e:  # network trouble affects every model: fail fast
                net.record_failure(url, e)
                raise LLMUnavailable(f"gemini: {type(e).__name__}") from e
            net.record_success(url)
            if r.status_code in _FALLBACK_STATUSES:
                _park(model, r.status_code, r.text)
                last = f"{model}: HTTP {r.status_code} {r.text[:200]}"
                continue
            if r.status_code != 200:
                raise LLMUnavailable(f"gemini: HTTP {r.status_code} {r.text[:200]}")
            try:
                text = "".join(
                    p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"]
                )
            except (KeyError, IndexError, ValueError) as e:
                raise LLMUnavailable(f"gemini: malformed response ({e})") from e
            self.model = model
            log.info("gemini %s complete %d ms", model, (time.perf_counter() - t0) * 1000)
            return text
        raise LLMUnavailable(f"gemini: every model unavailable ({last})")

    async def stream(self, system, user, *, max_tokens=1024) -> AsyncIterator[str]:
        last = ""
        self._check_reachable()
        for model in self._candidates():
            url = self._url(model, "streamGenerateContent") + "?alt=sse"
            for _attempt in range(2):
                resend = False
                try:
                    async with self._client() as c:
                        async with c.stream(
                            "POST",
                            url,
                            headers={"x-goog-api-key": self.api_key},
                            json=self._body(model, system, user, False, max_tokens),
                        ) as r:
                            if r.status_code != 200:
                                body = (await r.aread()).decode(errors="ignore")
                                if self._rejects_thinking_config(model, r.status_code, body):
                                    resend = True
                                elif r.status_code in _FALLBACK_STATUSES:
                                    _park(model, r.status_code, body)
                                    last = f"{model}: HTTP {r.status_code}"
                                else:
                                    raise LLMUnavailable(f"gemini stream: HTTP {r.status_code}")
                            else:
                                self.model = model
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
                                return
                except httpx.HTTPError as e:
                    net.record_failure(url, e)
                    raise LLMUnavailable(f"gemini stream: {type(e).__name__}") from e
                if not resend:
                    break
        raise LLMUnavailable(f"gemini stream: every model unavailable ({last})")


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
        fallbacks = [m.strip() for m in settings.gemini_fallback_models.split(",") if m.strip()]
        return GeminiLLM(
            settings.gemini_api_key, settings.gemini_model, thinking=thinking, fallbacks=fallbacks
        )
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
