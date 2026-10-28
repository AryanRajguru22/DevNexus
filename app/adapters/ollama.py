"""Local LLM provider backed by an Ollama server (optional; the deterministic mock stays the default).

Select it with DEVNEXUS_LLM_PROVIDER=ollama. Settings (environment variables, all optional):
  DEVNEXUS_OLLAMA_URL      base URL of the Ollama server           (default http://127.0.0.1:11434)
  DEVNEXUS_OLLAMA_MODEL    model tag that has been pulled           (default qwen2.5-coder:1.5b)
  DEVNEXUS_OLLAMA_TIMEOUT  seconds to wait for one generation       (default 120)

Everything that can go wrong at run time (server not running, model not pulled, timeout, malformed answer) is
reported as LLMUnavailable, which the Code Generation Agent turns into a Failed task with a clear message - the
application never crashes because a local model is missing. The generated text is only ever parsed by the Testing
Agent (ast); it is never executed.
"""
from __future__ import annotations

import json
import os
import re
import socket
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from .llm import CodeRequest, GeneratedCode, LLMUnavailable, slugify

DEFAULT_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5-coder:1.5b"
DEFAULT_TIMEOUT = 120.0

# (url, json payload, timeout seconds) -> decoded JSON document. Replaceable in tests.
PostJson = Callable[[str, dict[str, Any], float], dict[str, Any]]

_FENCE = re.compile(r"```[A-Za-z0-9_+-]*[ \t]*\r?\n(.*?)```", re.DOTALL)
_OPEN_FENCE = re.compile(r"```[A-Za-z0-9_+-]*[ \t]*\r?\n(.*)", re.DOTALL)

SYSTEM_PROMPT = (
    "You are the Code Generation Agent of a supervised software-development platform. "
    "Write ONE self-contained Python 3.11 module that implements the task. Rules: standard library only; "
    "every function has a docstring and a return-type annotation; no input(), no network, no file or "
    "subprocess access; no code that runs at import time. Reply with the module in a single ```python code "
    "block and nothing else."
)


def post_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    """POST a JSON document and decode the JSON answer (standard library only: no extra dependency)."""
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - URL comes from operator configuration
        return json.loads(resp.read().decode("utf-8"))


def extract_code(text: str) -> str:
    """The Python source from a model answer: the first fenced block, else the whole text, fences stripped."""
    match = _FENCE.search(text) or _OPEN_FENCE.search(text)  # the second form tolerates a truncated, unclosed block
    code = match.group(1) if match else text
    return code.strip("\n").rstrip() + "\n" if code.strip() else ""


class OllamaLLMProvider:
    def __init__(
        self,
        base_url: str = DEFAULT_URL,
        model: str = DEFAULT_MODEL,
        timeout: float = DEFAULT_TIMEOUT,
        post: PostJson = post_json,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._post = post
        self.name = f"ollama:{model} (local model at {self.base_url})"

    @classmethod
    def from_environment(cls) -> "OllamaLLMProvider":
        raw_timeout = os.environ.get("DEVNEXUS_OLLAMA_TIMEOUT", str(DEFAULT_TIMEOUT))
        try:
            timeout = float(raw_timeout)
            if timeout <= 0:
                raise ValueError
        except ValueError:
            raise ValueError(f"DEVNEXUS_OLLAMA_TIMEOUT must be a positive number of seconds, got {raw_timeout!r}") from None
        return cls(
            base_url=os.environ.get("DEVNEXUS_OLLAMA_URL", DEFAULT_URL),
            model=os.environ.get("DEVNEXUS_OLLAMA_MODEL", DEFAULT_MODEL),
            timeout=timeout,
        )

    @staticmethod
    def _prompt(request: CodeRequest) -> str:
        parts = [
            f"Task title: {request.title}",
            f"Task description: {request.description or '(none)'}",
            f"Requirement: {request.requirement}",
            f"Keep the module under {max(request.max_loc - 5, 10)} non-blank lines.",
        ]
        if request.feedback:
            parts.append(f"This is attempt {request.attempt}. Fix the problems the reviewer or tests reported:\n{request.feedback}")
        return "\n".join(parts)

    def _chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        """One request to /api/chat; every transport problem becomes LLMUnavailable with an actionable message."""
        timed_out = f"Ollama did not answer within {self.timeout:g} s (model '{self.model}')"
        try:
            return self._post(f"{self.base_url}/api/chat", payload, self.timeout)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise LLMUnavailable(f"Ollama model '{self.model}' is not installed. Run: ollama pull {self.model}") from exc
            raise LLMUnavailable(f"Ollama returned HTTP {exc.code}: {exc.reason}") from exc
        except (socket.timeout, TimeoutError) as exc:
            raise LLMUnavailable(timed_out) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (socket.timeout, TimeoutError)):
                raise LLMUnavailable(timed_out) from exc
            raise LLMUnavailable(f"Cannot reach Ollama at {self.base_url} ({exc.reason}). Start it with 'ollama serve'") from exc
        except (OSError, ValueError) as exc:  # connection reset, undecodable JSON, ...
            raise LLMUnavailable(f"Unusable answer from Ollama: {exc}") from exc

    def generate(self, request: CodeRequest) -> GeneratedCode:
        answer = self._chat({
            "model": self.model,
            "stream": False,
            "options": {"temperature": 0.2},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._prompt(request)},
            ],
        })
        message = answer.get("message") if isinstance(answer, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            error = answer.get("error") if isinstance(answer, dict) else None
            raise LLMUnavailable(f"Ollama error: {error}" if error else "Malformed Ollama response: no message content")
        code = extract_code(content)
        if "def " not in code and "class " not in code:
            raise LLMUnavailable("Ollama returned no Python code for this task")
        slug = slugify(request.title)
        loc = sum(1 for line in code.splitlines() if line.strip())
        return GeneratedCode(
            files={f"generated/{slug}.py": code},
            summary=f"Generated generated/{slug}.py ({loc} lines) with local model {self.model}",
        )
