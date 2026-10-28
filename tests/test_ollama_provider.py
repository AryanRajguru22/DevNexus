"""Ollama LLM provider (optional adapter): request shape, answer handling and every failure mode.

The HTTP layer is replaced by a stub: no test needs a running Ollama server, so the suite stays offline.
"""
from __future__ import annotations

import io
import socket
import urllib.error
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.adapters import ollama as ollama_module
from app.adapters.llm import CodeRequest, LLMUnavailable, PROVIDERS, UnknownProviderError, create_provider
from app.adapters.ollama import OllamaLLMProvider, extract_code
from app.config import Settings
from app.main import create_app
from tests.conftest import DEV, Api

REQUEST = CodeRequest("Build login API", "Return a token", "The system shall log users in.", None, 1, 200)
CODE = 'def login(user: str) -> dict:\n    """Log a user in."""\n    return {"user": user}\n'


def answer(text: str) -> dict:
    return {"message": {"role": "assistant", "content": text}, "done": True}


def provider_with(result=None, exc: Exception | None = None, **kw):
    calls: list[tuple] = []

    def post(url, payload, timeout):
        calls.append((url, payload, timeout))
        if exc is not None:
            raise exc
        return result

    return OllamaLLMProvider(post=post, **kw), calls


# -- request and answer handling ----------------------------------------------------------------------------------
def test_generate_posts_a_non_streaming_chat_request_and_returns_the_module():
    provider, calls = provider_with(answer(f"Here you go:\n```python\n{CODE}```\nDone."), model="m:1b", timeout=7)
    out = provider.generate(REQUEST)
    url, payload, timeout = calls[0]
    assert url == "http://127.0.0.1:11434/api/chat" and timeout == 7
    assert payload["model"] == "m:1b" and payload["stream"] is False
    assert [m["role"] for m in payload["messages"]] == ["system", "user"]
    assert "Build login API" in payload["messages"][1]["content"] and "attempt" not in payload["messages"][1]["content"]
    assert list(out.files) == ["generated/build_login_api.py"] and out.files["generated/build_login_api.py"] == CODE
    assert "m:1b" in out.summary and "ollama" in provider.name


def test_rework_feedback_is_part_of_the_prompt():
    provider, calls = provider_with(answer(CODE))
    provider.generate(replace(REQUEST, feedback="add input validation", attempt=2))
    assert "add input validation" in calls[0][1]["messages"][1]["content"]


@pytest.mark.parametrize(
    "text,expected",
    [
        (f"```python\n{CODE}```", CODE),
        (f"```py\n{CODE}```\ntrailing prose", CODE),
        (f"text\n```\n{CODE}```", CODE),
        (f"```python\n{CODE}", CODE),  # truncated answer: the block was never closed
        (CODE, CODE),  # no fence at all
        ("   \n", ""),
    ],
)
def test_extract_code_strips_fences(text, expected):
    assert extract_code(text) == expected


# -- failure modes: all become LLMUnavailable, never an unhandled exception ---------------------------------------
def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://x/api/chat", code, "Reason", {}, io.BytesIO(b""))


@pytest.mark.parametrize(
    "exc,message",
    [
        (urllib.error.URLError(ConnectionRefusedError("refused")), "Cannot reach Ollama.*ollama serve"),
        (urllib.error.URLError(socket.timeout("timed out")), "did not answer within 5 s"),
        (socket.timeout("timed out"), "did not answer within 5 s"),
        (TimeoutError(), "did not answer within 5 s"),
        (http_error(404), "model 'm:1b' is not installed.*ollama pull m:1b"),
        (http_error(500), "HTTP 500"),
        (ConnectionResetError("reset"), "Unusable answer"),
        (ValueError("Expecting value"), "Unusable answer"),
    ],
)
def test_transport_problems_become_llm_unavailable(exc, message):
    provider, _ = provider_with(exc=exc, model="m:1b", timeout=5)
    with pytest.raises(LLMUnavailable, match=message):
        provider.generate(REQUEST)


@pytest.mark.parametrize(
    "result,message",
    [
        ({"error": "model requires more memory"}, "Ollama error: model requires more memory"),
        ({"message": {"content": None}}, "Malformed"),
        ({"unexpected": True}, "Malformed"),
        (["not", "a", "dict"], "Malformed"),
        (answer("I cannot help with that."), "no Python code"),
        (answer("```python\n\n```"), "no Python code"),
    ],
)
def test_malformed_or_empty_answers_become_llm_unavailable(result, message):
    provider, _ = provider_with(result)
    with pytest.raises(LLMUnavailable, match=message):
        provider.generate(REQUEST)


def test_post_json_round_trip(monkeypatch):
    seen = {}

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout):
        seen.update(url=req.full_url, body=req.data, timeout=timeout, method=req.get_method())
        return Response(b'{"message": {"content": "ok"}}')

    monkeypatch.setattr(ollama_module.urllib.request, "urlopen", fake_urlopen)
    assert ollama_module.post_json("http://h/api/chat", {"a": 1}, 3.0) == {"message": {"content": "ok"}}
    assert seen == {"url": "http://h/api/chat", "body": b'{"a": 1}', "timeout": 3.0, "method": "POST"}


# -- configuration ------------------------------------------------------------------------------------------------
def test_ollama_is_registered_and_configured_from_the_environment(monkeypatch):
    assert "ollama" in PROVIDERS and "mock" in PROVIDERS
    monkeypatch.setenv("DEVNEXUS_OLLAMA_URL", "http://example:9999/")
    monkeypatch.setenv("DEVNEXUS_OLLAMA_MODEL", "tiny:1b")
    monkeypatch.setenv("DEVNEXUS_OLLAMA_TIMEOUT", "12.5")
    provider = create_provider("ollama")
    assert (provider.base_url, provider.model, provider.timeout) == ("http://example:9999", "tiny:1b", 12.5)


def test_defaults_and_bad_timeout(monkeypatch):
    for var in ("DEVNEXUS_OLLAMA_URL", "DEVNEXUS_OLLAMA_MODEL", "DEVNEXUS_OLLAMA_TIMEOUT"):
        monkeypatch.delenv(var, raising=False)
    p = OllamaLLMProvider.from_environment()
    assert (p.base_url, p.model, p.timeout) == (ollama_module.DEFAULT_URL, ollama_module.DEFAULT_MODEL, 120.0)
    for bad in ("abc", "0", "-3"):
        monkeypatch.setenv("DEVNEXUS_OLLAMA_TIMEOUT", bad)
        with pytest.raises(ValueError, match="DEVNEXUS_OLLAMA_TIMEOUT"):
            OllamaLLMProvider.from_environment()


def test_unknown_provider_message_lists_ollama(tmp_path):
    with pytest.raises(UnknownProviderError, match="mock, ollama"):
        create_provider("gpt-9")


# -- inside the application: a missing server fails the task cleanly ----------------------------------------------
def test_unreachable_ollama_fails_the_task_with_a_clear_reason_and_the_mock_still_works(tmp_path):
    settings = Settings(
        data_dir=tmp_path, database_url=f"sqlite:///{(tmp_path / 'o.db').as_posix()}", recover_on_startup=False
    )
    refused = OllamaLLMProvider(
        post=lambda url, payload, timeout: (_ for _ in ()).throw(urllib.error.URLError(ConnectionRefusedError("refused")))
    )
    app = create_app(settings, llm=refused)
    try:
        client = TestClient(app)
        api = Api(client)
        project = api.project()
        req = api.requirement(project["project_id"])
        tid = api.task(project["project_id"], req["req_id"])["task_id"]
        api.post(f"/api/tasks/{tid}/assign")
        task = api.get(tid)
        assert task["status"] == "Failed"
        assert task["runs"][0]["status"] == "failed" and "Cannot reach Ollama" in task["runs"][0]["error_message"]
        assert "retry" in client.get(f"/api/tasks/{tid}", headers=DEV).json()["allowed_actions"]
    finally:
        app.state.runtime.engine.dispose()


def test_ollama_output_flows_through_review_testing_and_deploy(tmp_path):
    """A well-formed local-model answer is committed to the feature branch, statically tested and deployable."""
    settings = Settings(
        data_dir=tmp_path, database_url=f"sqlite:///{(tmp_path / 'o2.db').as_posix()}", recover_on_startup=False
    )
    app = create_app(settings, llm=OllamaLLMProvider(post=lambda url, payload, timeout: answer(f"```python\n{CODE}```")))
    try:
        client = TestClient(app)
        api = Api(client)
        project = api.project()
        req = api.requirement(project["project_id"])
        tid = api.task(project["project_id"], req["req_id"])["task_id"]
        api.post(f"/api/tasks/{tid}/assign")
        assert api.get(tid)["status"] == "In Review"
        api.post(f"/api/tasks/{tid}/approve")
        assert api.get(tid)["status"] == "Ready for Deployment"
        api.post(f"/api/tasks/{tid}/deploy")
        assert api.get(tid)["status"] == "Deployed"
        assert app.state.runtime.git.read_main(project["project_id"])["generated/build_login_api.py"] == CODE
    finally:
        app.state.runtime.engine.dispose()
