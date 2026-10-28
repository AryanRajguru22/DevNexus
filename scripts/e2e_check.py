"""End-to-end check of a RUNNING DevNexus server through its real HTTP API (and page shells).

    python scripts/e2e_check.py [http://127.0.0.1:8000]

Use a FRESH database (it creates its own project "E2E check <timestamp>" and never touches existing ones, but
the dashboard assertions are scoped to that project only). Standard library only. Exit code 0 = every check passed.
Covers the journey of docs/DEMO_SCRIPT.md: project -> requirement -> edit/approve -> task -> generate -> review
(approve, reject) -> tests (pass, fail+rework) -> LLM outage + retry limit -> deployment (success, failure + rollback
visible, retry) -> audit, notifications, dashboard, estimation, risk -> role/state/input refusals.
Mock adapters are assumed (the [fail-*] markers in task titles are mock-only demo switches).
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
results: list[tuple[bool, str]] = []


def call(method: str, path: str, user: int | None = None, body: dict | None = None, expect: int | None = 200):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if user:
        req.add_header("X-User-Id", str(user))
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=60) as resp:
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    if expect is not None and status != expect:
        raise SystemExit(f"UNEXPECTED {method} {path} -> {status} (wanted {expect}): {raw[:300]!r}")
    try:
        return status, json.loads(raw or "null")
    except ValueError:
        return status, raw.decode("utf-8", "replace")


def check(name: str, condition: bool, extra: str = "") -> None:
    results.append((bool(condition), name))
    print(f"  [{'PASS' if condition else 'FAIL'}] {name}{'' if condition else '  -> ' + extra}")


def wait_for(task_id: int, wanted: set[str], user: int, timeout: float = 60.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        _, task = call("GET", f"/api/tasks/{task_id}", user)
        if task["status"] in wanted:
            return task
        time.sleep(0.3)
    raise SystemExit(f"task {task_id} never reached {wanted}; last status {task['status']}")


def main() -> None:
    print(f"DevNexus end-to-end check against {BASE}")
    _, health = call("GET", "/api/health")
    check("health endpoint reports ok", health == {"status": "ok"})
    users = {u["role"]: u["user_id"] for u in reversed(call("GET", "/api/users")[1])}
    pm, dev = users["project_manager"], users["developer"]
    for page in ("/", "/projects", "/reports", "/audit", "/notifications"):
        status, html = call("GET", page, expect=200)
        check(f"page {page} renders", status == 200 and "<html" in html.lower())

    # -- project, requirements, edit, approve ------------------------------------------------------------------
    name = f"E2E check {int(time.time())}"
    _, project = call("POST", "/api/projects", pm, {
        "name": name, "problem_statement": "p", "scope": "s", "objectives": "o"}, expect=201)
    pid = project["project_id"]
    check("project created and listed", any(p["project_id"] == pid for p in call("GET", "/api/projects", pm)[1]))
    call("PUT", f"/api/projects/{pid}/pipeline", pm, {
        "active_agents": ["code_generation", "testing", "deployment"], "retry_limit": 1,
        "constraints": {"max_loc": 200, "target_environment": "staging", "delay_threshold_hours": 72}})
    _, req = call("POST", f"/api/projects/{pid}/requirements", pm, {
        "description": "The system shall allow users to log in.", "type": "functional", "priority": "High"}, expect=201)
    rid = req["req_id"]
    _, edited = call("PATCH", f"/api/requirements/{rid}", pm, {"priority": "Medium"})
    check("PM can edit a Draft requirement", edited["priority"] == "Medium")
    call("PATCH", f"/api/requirements/{rid}", pm, {"status": "Approved"})
    status, locked = call("PATCH", f"/api/requirements/{rid}", pm, {"description": "changed after approval"}, expect=None)
    check("approved requirement is locked (422 requirement_locked)",
          status == 422 and locked["error"]["code"] == "requirement_locked")
    status, _ = call("PATCH", f"/api/requirements/{rid}", dev, {"priority": "Low"}, expect=None)
    check("developer cannot edit requirements (403)", status == 403)
    _, renamed = call("PATCH", f"/api/projects/{pid}", pm, {"name": name + " (edited)"})
    check("PM can edit project details", renamed["name"].endswith("(edited)"))

    def new_task(title: str, description: str = "") -> int:
        return call("POST", "/api/tasks", dev, {"project_id": pid, "req_id": rid, "title": title,
                                                "description": description}, expect=201)[1]["task_id"]

    # -- happy path + reject/rework + review diff isolation ---------------------------------------------------
    t1 = new_task("Build login API", "Return a token.")
    call("POST", f"/api/tasks/{t1}/assign", dev)
    task = wait_for(t1, {"In Review"}, dev)
    check("assign -> code generated -> In Review with one completed run",
          len(task["runs"]) == 1 and task["runs"][0]["status"] == "completed")
    _, diff = call("GET", f"/api/tasks/{t1}/diff", dev)
    check("review diff shows the generated file against main", diff["base"] == "main" and len(diff["files"]) == 1)
    status, _ = call("POST", f"/api/tasks/{t1}/reject", dev, {"comments": ""}, expect=None)
    check("reject without comments is refused (422)", status == 422)
    call("POST", f"/api/tasks/{t1}/reject", dev, {"comments": "Add input validation."})
    task = wait_for(t1, {"In Review"}, dev)
    check("reject -> regeneration -> back In Review (2 runs)", len(task["runs"]) == 2)
    call("POST", f"/api/tasks/{t1}/approve", dev, {"comments": "OK"})
    task = wait_for(t1, {"Ready for Deployment"}, dev)
    check("approve -> tests pass -> Ready for Deployment", task["status"] == "Ready for Deployment")
    status, err = call("POST", f"/api/tasks/{t1}/approve", dev, expect=None)
    check("approving twice is a 409 invalid_transition", status == 409 and err["error"]["code"] == "invalid_transition")
    status, _ = call("POST", f"/api/tasks/{t1}/deploy", users["developer"] + 99, expect=None)
    check("unknown user is refused", status in (401, 403))
    call("POST", f"/api/tasks/{t1}/deploy", pm, {"environment": "staging"})
    _, task = call("GET", f"/api/tasks/{t1}", pm)
    check("PM authorises deployment -> Deployed", task["status"] == "Deployed")

    t2 = new_task("Export grades")
    call("POST", f"/api/tasks/{t2}/assign", dev)
    wait_for(t2, {"In Review"}, dev)
    _, diff2 = call("GET", f"/api/tasks/{t2}/diff", dev)
    paths = [f["path"] for f in diff2["files"]]
    deleted = [line for f in diff2["files"] for line in f["diff"].splitlines() if line.startswith("-") and not line.startswith("---")]
    check("issue #3: second task's diff has only its own file and no deletions",
          len(paths) == 1 and "export_grades" in paths[0] and not deleted, str(paths))

    # -- failed tests -> automatic rework ------------------------------------------------------------------
    t3 = new_task("Send receipts [fail-tests]")
    call("POST", f"/api/tasks/{t3}/assign", dev)
    wait_for(t3, {"In Review"}, dev)
    call("POST", f"/api/tasks/{t3}/approve", dev)
    task = wait_for(t3, {"In Review", "Ready for Deployment"}, dev)
    check("failing tests send the task back for rework (2 runs, In Review)",
          task["status"] == "In Review" and len(task["runs"]) == 2, task["status"])

    # -- LLM outage and retry limit ---------------------------------------------------------------------
    t4 = new_task("Notify students [fail-llm-always]")
    call("POST", f"/api/tasks/{t4}/assign", dev)
    wait_for(t4, {"Failed"}, dev)
    call("POST", f"/api/tasks/{t4}/retry", dev)
    time.sleep(0.5)
    task = wait_for(t4, {"Failed"}, dev)
    check("LLM outage -> Failed; retry fails again", task["status"] == "Failed" and len(task["runs"]) == 2)
    status, err = call("POST", f"/api/tasks/{t4}/retry", dev, expect=None)
    check("retry limit reached: further retry refused (409 retry_limit_exceeded)",
          status == 409 and err["error"]["code"] == "retry_limit_exceeded")

    # -- deployment failure then success ----------------------------------------------------------------
    t5 = new_task("Archive results [fail-deploy]")
    call("POST", f"/api/tasks/{t5}/assign", dev)
    wait_for(t5, {"In Review"}, dev)
    call("POST", f"/api/tasks/{t5}/approve", dev)
    wait_for(t5, {"Ready for Deployment"}, dev)
    _, out = call("POST", f"/api/tasks/{t5}/deploy", dev)
    check("failed deployment is reported and the task stays Ready for Deployment",
          out["outcome"] == "failed" and out["task"]["status"] == "Ready for Deployment")
    _, out = call("POST", f"/api/tasks/{t5}/deploy", dev)
    check("deployment retry succeeds -> Deployed", out["outcome"] == "succeeded" and out["task"]["status"] == "Deployed")

    # -- audit, notifications, reports -------------------------------------------------------------------
    _, audit = call("GET", f"/api/audit?target_ref=task:{t1}&limit=100", pm)
    actions = {a["action"] for a in audit}
    check("audit trail has human and agent rows for task 1",
          {"task.assign", "task.reject", "task.approve", "task.deploy_authorise", "agent.generate", "agent.test"} <= actions,
          str(sorted(actions)))
    _, denied = call("GET", "/api/audit?action=access.denied", pm)
    check("refused calls are audited (access.denied)", any(d["action"] == "access.denied" for d in denied))
    kinds = {n["kind"] for n in call("GET", "/api/notifications", dev)[1] if n["project_id"] == pid}
    check("developer notified of the key events", {"task_failed", "deployment_failed", "deployment_completed"} <= kinds, str(kinds))
    pm_kinds = {n["kind"] for n in call("GET", "/api/notifications", pm)[1] if n["project_id"] == pid}
    check("PM receives the risk-threshold notification", "risk_threshold" in pm_kinds, str(pm_kinds))
    _, dash = call("GET", f"/api/dashboard?project_id={pid}", pm)
    check("dashboard counts match the five tasks", dash["totals"]["tasks"] == 5 and dash["totals"]["by_status"]["Deployed"] == 2,
          json.dumps(dash["totals"]))
    _, est = call("GET", f"/api/reports/estimation?project_id={pid}", pm)
    check("COCOMO estimation is computed", est["effort_person_months"] > 0 and est["cost_inr"] > 0)
    _, risk = call("POST", f"/api/reports/risk?project_id={pid}", pm, expect=201)
    check("risk report is generated and persisted", risk["risk_level"] in ("Low", "Medium", "High") and risk["report_id"] > 0)
    status, _ = call("POST", f"/api/reports/risk?project_id={pid}", dev, expect=None)
    check("developer cannot generate risk reports (403)", status == 403)
    status, _ = call("GET", "/api/tasks/999999", dev, expect=None)
    check("unknown task -> 404", status == 404)

    failed = [name for ok, name in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("FAILED:", *failed, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()
