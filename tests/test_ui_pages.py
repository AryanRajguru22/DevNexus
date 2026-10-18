"""UI checks that need no browser: pages render, assets load, and the JS only calls endpoints that really exist."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "app" / "web"
PAGES = ["/", "/projects", "/projects/1", "/tasks/1", "/reports", "/audit", "/notifications"]


@pytest.mark.parametrize("path", PAGES)
def test_every_page_renders_with_shell_and_brand(client, path):
    r = client.get(path)
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert "DevNexus" in r.text and "ASDPIP" in r.text and "js/app.js" in r.text
    assert "local mock adapters" in r.text  # honest demo-mode banner is always visible


@pytest.mark.parametrize("asset", ["css/app.css", "js/app.js", "img/devnexus-logo-placeholder.svg"])
def test_static_assets_are_served(client, asset):
    assert client.get(f"/static/{asset}").status_code == 200


def test_logo_is_labelled_as_a_placeholder():
    svg = (WEB / "static/img/devnexus-logo-placeholder.svg").read_text(encoding="utf-8")
    assert "PLACEHOLDER" in svg and "NOT THE OFFICIAL" in svg


def test_non_numeric_ids_in_page_urls_are_rejected(client):
    assert client.get("/tasks/abc").status_code == 422


def test_js_only_calls_documented_api_endpoints(client):
    """No dead buttons: every /api/... path used by app.js must exist in the OpenAPI schema."""
    js = (WEB / "static/js/app.js").read_text(encoding="utf-8")
    used = set(re.findall(r"""['"`](/api/[^'"`?]*)""", js))
    assert used, "app.js should call the API"
    known = set(client.get("/openapi.json").json()["paths"])
    # task actions go through post('<action>', ...) -> /api/tasks/{id}/<action>: expand them explicitly
    actions = set(re.findall(r"post\('([a-z_]+)'", js))
    assert actions == {"assign", "approve", "retry", "tests", "deploy"}
    used = {p for p in used if p != "/api/tasks/${tid}/${path}"} | {f"/api/tasks/${{tid}}/{a}" for a in actions}
    normalised = {re.sub(r"\$\{[^}]+\}", "{}", p) for p in used}
    known_norm = {re.sub(r"\{[^}]+\}", "{}", p) for p in known}
    unknown = {p.rstrip("/") for p in normalised if p.rstrip("/") not in known_norm and p.rstrip("/") + "/" not in known_norm}
    assert not unknown, f"app.js calls undocumented endpoints: {unknown}"


def test_every_element_id_used_by_js_exists_in_a_template():
    js = (WEB / "static/js/app.js").read_text(encoding="utf-8")
    html = "".join(p.read_text(encoding="utf-8") for p in (WEB / "templates").glob("*.html"))
    ids_in_html = set(re.findall(r'id="([^"]+)"', html))
    used = set(re.findall(r"\$\('#([A-Za-z0-9_-]+)'\)", js))
    dynamic = {"deploy-env"}  # created by the script itself
    assert used - ids_in_html - dynamic == set()


def test_js_never_uses_innerhtml():
    js = (WEB / "static/js/app.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js and "insertAdjacentHTML" not in js and "document.write" not in js
