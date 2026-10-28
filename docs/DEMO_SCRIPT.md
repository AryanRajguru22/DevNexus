# Demo Script (8-10 minutes)

**Setup (before the audience arrives)** — from the repo root with the venv active:
```
set DEVNEXUS_MOCK_AGENT_DELAY=1.5        (PowerShell: $env:DEVNEXUS_MOCK_AGENT_DELAY="1.5")
python -m app                             # http://127.0.0.1:8000
python scripts/demo_seed.py               # optional: a ready-made project through the real API
```
**Before you start (2 minutes, once):** `pytest -q` (387 passed) and, with the server running on a fresh `data/`, `python scripts/e2e_check.py` (34/34) - keep the output on screen as evidence for the closing slide. Always demo with the **mock** provider (`DEVNEXUS_LLM_PROVIDER` unset): it is deterministic, offline and the only one that supports the `[fail-*]` markers. Show Ollama (README) only as a bonus *after* the main demo and only if you verified it on this laptop that day.

**Timing guide:** problem + architecture 2 min · steps 1-10 below 4 min · failure paths B.1 and B.4 1 min · intelligence 1 min · recovery + duplicate-job note 30 s (say it; the kill-restart demo is optional: start with `DEVNEXUS_MOCK_AGENT_DELAY=20`, assign a task, stop the server window, start it again, open the task: *interrupted run failed, new run completed*) · evidence + limitations 1 min.

Open the app. Say up front: *the agents, Git host and CI are local mock adapters; test results are simulated static checks; everything else is real and persisted.*

## A. Story (follow the Phase 3 pipeline)

| Step | Do | Say / show | Requirement |
|---|---|---|---|
| 1 | Acting as **Aryan (PM)** → Projects → New project | problem statement, scope, objectives | FR-1 |
| 2 | Add 2–3 requirements (one non-functional) | | FR-2 |
| 3 | Pipeline card: tick agents, retry limit 1 | "retry limit bounds rework" | FR-3 |
| 4 | Switch to **Member C (Developer)** → Create task from a requirement | creation is Developer-only (the form is hidden for the PM; the API refuses and audits it) | FR-4, NFR-3 |
| 5 | Open task → *Assign to Code Generation Agent* | stepper moves Assigned → Generating → In Review; bell shows a notification | FR-5, FR-6, FR-13 |
| 6 | Review the diff | "only on a feature branch; nothing in main yet" | FR-7, NFR-6 |
| 7 | **Reject** with a comment | task returns to Generating, new run, comment appears in the code and in History | FR-7, UC-05 3a |
| 8 | **Approve** | Testing → Ready for Deployment; test result flagged *simulated* | FR-8 |
| 9 | **Authorise deployment** (staging) | Deployed; main now contains the code | FR-9 |
| 10 | History table | each action with actor, timestamp; audit page search | FR-14, NFR-11 |

## B. Failure paths (type the marker into the task title)
1. `Export grades [fail-tests]` → approve → tests fail → automatic rework → back In Review → approve → passes.
2. `Send alerts [fail-llm]` → assign → **Failed** (notification to Developer and PM) → Retry → In Review.
3. `Send alerts [fail-llm-always]` with retry limit 1 → Failed → Retry → Failed → Retry refused (`retry_limit_exceeded`): "no infinite loop; reported as a risk".
4. `Publish [fail-deploy]` → authorise → deployment failed, main restored, task stays Ready for Deployment → authorise again → succeeds.

## C. Intelligence
Dashboard (status bars, velocity, coverage *simulated*, risk) → switch project filter → Reports: COCOMO estimate from task sizes next to the Phase 2 baseline (21.3 person-months, 8 months, ₹12,78,000) → *Generate risk report* as PM.

## D. Likely viva questions (answers live in the docs)
- Why 8 states and where is the retry limit? → ARCHITECTURE §4, `workflow.py`.
- How do you guarantee the audit log is append-only? → DB triggers, `test_audit.py`.
- Why a mock LLM and static tests? → D-4/D-5, never execute generated code.
- Which requirements are not fully met? → KNOWN_LIMITATIONS.md, traceability "partially implemented".
- Why SQLite/one process vs PostgreSQL/microservices? → D-1/D-2 (deadline, budget, laptop).

## E. If something breaks
Stop the server (Ctrl+C), delete the `data/` folder, restart: the schema and demo users are re-created (demo data only - this is a reset, not part of normal start-up). If a page looks empty, check `/api/health` and the server console. If Ollama was selected and misbehaves, restart with `DEVNEXUS_LLM_PROVIDER` unset. API docs at `/docs` are a fallback to show endpoints. Honest limitations to state: mocked AI/Git/CI, simulated tests, no real authentication, single-process SQLite.
