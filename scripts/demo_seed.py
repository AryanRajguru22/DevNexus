"""Populate a RUNNING DevNexus server with a realistic demo project by calling the real REST API.

    python scripts/demo_seed.py [http://127.0.0.1:8000]

Nothing is inserted behind the application's back: every row is created through the same endpoints and workflow
rules the UI uses, so the dashboard numbers are genuine (agents are still mock adapters). Run it once on a fresh
database; it refuses to run if a project already exists. Uses only the standard library.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")


def call(method: str, path: str, user: int | None = None, body: dict | None = None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if user:
        req.add_header("X-User-Id", str(user))
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=30) as resp:
            return json.loads(resp.read() or "null")
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"{method} {path} -> {exc.code}: {exc.read().decode()}")


def wait_for(task_id: int, wanted: set[str], user: int) -> dict:
    for _ in range(120):
        task = call("GET", f"/api/tasks/{task_id}", user)
        if task["status"] in wanted:
            return task
        time.sleep(0.5)
    raise SystemExit(f"task {task_id} never reached {wanted}")


def main() -> None:
    users = {u["role"]: u["user_id"] for u in reversed(call("GET", "/api/users"))}  # first PM, first developer
    pm, dev = users["project_manager"], users["developer"]
    if call("GET", "/api/projects", pm):
        raise SystemExit("A project already exists; demo_seed.py is meant for a fresh database.")

    project = call("POST", "/api/projects", pm, {
        "name": "Student Portal",
        "problem_statement": "Students cannot see their results online and staff compile them by hand.",
        "scope": "Login API, results page, grade export and e-mail alerts.",
        "objectives": "Deliver a supervised, AI-assisted first release within the sprint.",
        "start_date": time.strftime("%Y-%m-%d", time.gmtime(time.time() - 7 * 86400)),
        "end_date": time.strftime("%Y-%m-%d", time.gmtime(time.time() + 14 * 86400)),
    })
    pid = project["project_id"]
    call("PUT", f"/api/projects/{pid}/pipeline", pm, {
        "active_agents": ["code_generation", "testing", "deployment"], "retry_limit": 1,
        "constraints": {"max_loc": 200, "target_environment": "staging", "delay_threshold_hours": 72},
    })
    reqs = [
        ("The system shall allow a registered student to log in with e-mail and password.", "functional", "High"),
        ("The system shall show a student their published results.", "functional", "High"),
        ("Pages shall load within two seconds on a campus network.", "non-functional", "Medium"),
    ]
    req_ids = [call("POST", f"/api/projects/{pid}/requirements", pm,
                    {"description": d, "type": t, "priority": p, "status": "Approved"})["req_id"] for d, t, p in reqs]

    def new_task(title: str, req: int, description: str = "") -> int:
        return call("POST", "/api/tasks", dev, {"project_id": pid, "req_id": req, "title": title, "description": description})["task_id"]

    # 1. the happy path, all the way to Deployed
    t1 = new_task("Build login API", req_ids[0], "Return a token for valid credentials.")
    call("POST", f"/api/tasks/{t1}/assign", dev)
    wait_for(t1, {"In Review"}, dev)
    call("POST", f"/api/tasks/{t1}/approve", dev, {"comments": "Reviewed: matches the requirement."})
    wait_for(t1, {"Ready for Deployment"}, dev)
    call("POST", f"/api/tasks/{t1}/deploy", dev, {"environment": "staging"})

    # 2. waiting for a human review
    t2 = new_task("Build results page", req_ids[1])
    call("POST", f"/api/tasks/{t2}/assign", dev)
    wait_for(t2, {"In Review"}, dev)

    # 3. a failing first test run -> automatic rework -> back in review
    t3 = new_task("Export grades to CSV [fail-tests]", req_ids[1])
    call("POST", f"/api/tasks/{t3}/assign", dev)
    wait_for(t3, {"In Review"}, dev)
    call("POST", f"/api/tasks/{t3}/approve", dev)
    time.sleep(1)
    wait_for(t3, {"In Review"}, dev)

    # 4. an LLM outage: fails, retried once, fails again, retry limit reached -> reported as a risk
    t4 = new_task("Send e-mail alerts [fail-llm-always]", req_ids[2])
    call("POST", f"/api/tasks/{t4}/assign", dev)
    wait_for(t4, {"Failed"}, dev)
    call("POST", f"/api/tasks/{t4}/retry", dev)
    time.sleep(1)
    wait_for(t4, {"Failed"}, dev)

    # 5. not started
    new_task("Archive old results", req_ids[1])
    call("POST", f"/api/reports/risk?project_id={pid}", pm)
    print(f"Demo project #{pid} ready: open {BASE}/projects/{pid}")


if __name__ == "__main__":
    main()
