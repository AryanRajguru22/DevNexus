# Test Plan and Evidence

Run everything: `pytest` (venv active). With coverage: `pytest --cov=app --cov-report=term`. Each test uses its own temporary SQLite file and workspace (`tests/conftest.py`), so tests are independent and can run in any order.

## 1. Strategy

| Level | What | Where |
|---|---|---|
| Unit | Workflow table, guards, actors, retry bound; COCOMO/risk formulas; Git/LLM/CI adapters; agents (incl. "never executes generated code") | `test_workflow.py`, `test_analytics.py`, `test_adapters_and_agents.py` |
| Database | Append-only audit (triggers), exactly-one-actor CHECK, restart persistence | `test_audit.py`, `test_nfr.py` |
| API / integration | Whole task pipeline through HTTP incl. background agent jobs; roles; validation; notifications; error envelope | `test_api_projects.py`, `test_task_flows.py` |
| UI (no browser) | Pages render, assets served, JS only calls real endpoints, all element ids exist, no `innerHTML` | `test_ui_pages.py` |
| Non-functional | NFR-1/2/5/8 measurable parts | `test_nfr.py`, `test_analytics.py` |
| Manual / browser | Full lifecycle clicked through the real UI | DEMO_SCRIPT.md; run on 2026-10-17 (see §3) |

## 2. Latest automated results (real, 2026-10-17, Windows 11, Python 3.11.9)

```
248 passed        (pytest, ~50 s)
TOTAL coverage    98% of app/  (orchestrator 81%, others 97–100%)
```

| File | Tests |
|---|---|
| test_workflow.py | 102 (all 10 transitions; 70 invalid state/event pairs; 9 wrong-actor; 5 inactive-agent; 3 retry-limit; actions) |
| test_api_projects.py | 35 |
| test_adapters_and_agents.py | 33 |
| test_task_flows.py | 32 |
| test_analytics.py | 19 |
| test_ui_pages.py | 15 |
| test_audit.py | 9 |
| test_nfr.py | 3 |

Bugs found by testing during construction (all fixed, regression tests added): timestamps serialised as `…+00:00Z` (UI showed "Invalid Date"); `[hidden]` overridden by CSS `display:grid`; `ev.currentTarget` null after `await` in form handlers (found by driving the real UI in a browser).

## 3. Manual browser run (2026-10-17)
Real server with `DEVNEXUS_MOCK_AGENT_DELAY=1.5`: created a project and requirement through the forms, switched to a Developer, created a task, assigned → watched Generating → In Review, viewed the diff, approved → Testing → Ready for Deployment, authorised deployment → Deployed; dashboard showed 100% progress, 1 task, simulated 100% coverage, velocity bar in the current sprint; reports page showed the COCOMO figures and the Phase 2 baseline. No console errors on the projects page. `scripts/demo_seed.py` populated a second database through the API (5 tasks in 5 different states).

## 4. Requirement → test map
See REQUIREMENTS_TRACEABILITY.md (Verification column). Member B keeps the *Evidence* cells current (proposed task PLAN-21).

## 5. Workflow conformance (to be completed in proposed task PLAN-03)

| Transition (Fig 3.7) | PDF ref | Code | Test |
|---|---|---|---|
| assignTask: Created → Assigned | §9 table | `TRANSITIONS["assign"]` | `test_valid_transition…[assign]` |
| agent starts: Assigned → Generating | §9 | `agent_start` | … |
| codeReady: Generating → In Review | §9 | `code_ready` | … |
| agent error: Generating → Failed | §9 | `agent_error` | … |
| [approved]: In Review → Testing | §9, UC-05 | `approve` | … |
| [rejected]: In Review → Generating | §9, UC-05 3a | `reject` | … |
| [tests passed]: Testing → Ready for Deployment | §9, UC-06 | `tests_passed` | … |
| [tests failed]: Testing → Generating | §9, UC-06 5a | `tests_failed` | … |
| authoriseDeployment(): Ready → Deployed | §9, UC-07 | `authorise_deployment` | … |
| retry: Failed → Assigned | §9 | `retry` | … |

(PLAN-03: fill the PDF-reference and test-name cells and add any gap tests.)

## 6. Non-functional evidence

| NFR | Check | Result |
|---|---|---|
| NFR-1 | assign → In Review time with mock provider | < 1 s (real LLM not measured) |
| NFR-2 | dashboard request with 50 tasks | < 5 s asserted; typically tens of ms |
| NFR-5 | restart keeps tasks, history, users | passes |
| NFR-6 | commit to main/master, `..` paths, bad branch names refused; failed deploy restores main | passes |
| NFR-7 | first-time PM < 10 min | **not yet measured** (PLAN-19) |
| NFR-8 | 50 tasks created + assigned in one project | passes (sequential) |
| NFR-4, 9, 10 | — | deferred/partial, see KNOWN_LIMITATIONS.md |

## 7. Exit criteria for release v1.0
All P0/P1 issues merged · `pytest` green with coverage ≥ 90% · traceability has no status the tests do not support · two clean demo rehearsals from a fresh clone.
