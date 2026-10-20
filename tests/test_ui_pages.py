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


def test_css_colours_come_from_design_tokens():
    """PLAN-10: hex colours are defined once in :root; components use var(--...) only."""
    css = (WEB / "static/css/app.css").read_text(encoding="utf-8")
    root_end = css.index("}", css.index(":root"))
    stray = re.findall(r"#[0-9a-fA-F]{3,8}\b", css[root_end:])
    assert stray == [], f"hard-coded colours outside :root: {stray}"


def test_grid_columns_can_shrink_below_content_width():
    """PLAN-04 defect 2: `1fr` columns grow to fit wide tables and cause sideways scrolling; use minmax(0, 1fr)."""
    css = (WEB / "static/css/app.css").read_text(encoding="utf-8")
    assert not re.search(r"repeat\(\d, 1fr\)", css)


def test_dashboard_has_getting_started_checklist(client):
    html = client.get("/").text
    assert 'id="getting-started"' in html and 'id="gs-steps"' in html and 'id="gs-hide"' in html


# ---------- PLAN-12: template structure checks (no browser needed) ----------
from html.parser import HTMLParser  # noqa: E402

TEMPLATES = sorted((WEB / "templates").glob("*.html"))
JS = (WEB / "static/js/app.js").read_text(encoding="utf-8")
FIELD_TAGS = {"input", "select", "textarea"}


class _Collector(HTMLParser):
    """Collects ids, form-field names, unlabelled fields and buttons, tracking <label> and <form> nesting."""

    def __init__(self):
        super().__init__()
        self.ids, self.names, self.label_for = [], set(), set()
        self.fields, self.buttons = [], []
        self._label_depth, self._forms = 0, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "label":
            self._label_depth += 1
            if "for" in a:
                self.label_for.add(a["for"])
        elif tag == "form":
            self._forms.append(a.get("id"))
        elif tag in FIELD_TAGS:
            if "name" in a:
                self.names.add(a["name"])
            self.fields.append((tag, a, self._label_depth > 0))
        elif tag == "button":
            self.buttons.append((a, self._forms[-1] if self._forms else None))

    def handle_endtag(self, tag):
        if tag == "label":
            self._label_depth -= 1
        elif tag == "form" and self._forms:
            self._forms.pop()


def _parse(path: Path) -> _Collector:
    c = _Collector()
    c.feed(path.read_text(encoding="utf-8"))
    return c


@pytest.mark.parametrize("template", [t for t in TEMPLATES if t.name != "base.html"], ids=lambda t: t.name)
def test_every_page_template_extends_base(template):
    assert template.read_text(encoding="utf-8").lstrip().startswith('{% extends "base.html" %}')


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t.name)
def test_every_form_field_has_a_label(template):
    c = _parse(template)
    unlabelled = [
        a.get("name") or a.get("id") or tag
        for tag, a, inside_label in c.fields
        if not inside_label and "aria-label" not in a and a.get("id") not in c.label_for
    ]
    assert unlabelled == [], f"{template.name}: fields without a label: {unlabelled}"


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t.name)
def test_element_ids_are_unique_within_a_page(template):
    ids = _parse(template).ids + (_parse(WEB / "templates/base.html").ids if template.name != "base.html" else [])
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    assert dupes == [], f"{template.name}: duplicate ids {dupes}"


def test_page_titles_are_unique(client):
    titles = [re.search(r"<title>(.*?)</title>", client.get(p).text).group(1) for p in PAGES]
    assert len(set(titles)) == len(titles), titles


def test_every_form_field_name_used_by_js_exists():
    """`f.retry_limit.value`, `form.comments...`, `[name=agent]` must match a real field name in a template."""
    names = set().union(*(_parse(t).names for t in TEMPLATES))
    # a named field is read as <form>.<name>.value / .focus() / .checked, or through [name=...] selectors
    used = set(re.findall(r"\b(?:f|form)\.([a-z_]+)\.(?:value|focus|checked)\b", JS))
    used |= set(re.findall(r"\$\('#[\w-]+-form'\)\.([a-z_]+)\b", JS))
    used |= set(re.findall(r"\[name=([a-z_]+)\]", JS))
    assert {"retry_limit", "comments", "description", "agent"} <= used  # the patterns still find real reads
    missing = used - {"hidden"} - names  # .hidden is the DOM property, not a field
    assert missing == set(), f"app.js reads form fields that no template defines: {missing}"


def test_every_data_attribute_read_by_js_is_set_by_a_template():
    used = set(re.findall(r"dataset\.([A-Za-z]+)", JS)) - {"d"}
    html = "".join(t.read_text(encoding="utf-8") for t in TEMPLATES)
    to_attr = lambda camel: "data-" + re.sub(r"([A-Z])", lambda m: "-" + m.group(1).lower(), camel)  # noqa: E731
    missing = {u for u in used if to_attr(u) not in html}
    assert used and missing == set(), f"data attributes read by JS but never set: {missing}"


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t.name)
def test_no_button_without_a_handler(template):
    """Every template button is wired by app.js: by its own id, or as the submit button of a form the JS handles."""
    handled_ids = set(re.findall(r"\$\('#([\w-]+)'\)\.addEventListener", JS))
    # also `const gen = $('#gen-risk'); ... gen.addEventListener(...)`
    for var, el_id in re.findall(r"const (\w+) = \$\('#([\w-]+)'\);", JS):
        if re.search(rf"\b{var}\.addEventListener\(", JS):
            handled_ids.add(el_id)
    dead = []
    for a, form_id in _parse(template).buttons:
        if a.get("id") in handled_ids:
            continue
        if a.get("type", "submit") == "submit" and form_id in handled_ids:
            continue
        if a.get("type") == "reset" and form_id:
            continue  # native form reset
        dead.append(a.get("id") or a.get("class") or "button")
    assert dead == [], f"{template.name}: buttons with no handler: {dead}"
