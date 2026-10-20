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

## 2. Latest automated results (real, 2026-10-20, Windows 11, Python 3.11.9)

```
275 passed        (pytest, ~50 s; also 275 passed in a clean venv built from requirements.txt)
TOTAL coverage    98% of app/  (orchestrator 91%, others 97–100%)
```
Working tree with PLAN-13/PLAN-14 applied (uncommitted). Baseline commit `37ab6aa` (2026-10-17): 248 passed, orchestrator 81%. The new tests were mutation-checked: disabling the compare-and-set, the running-run check, the Testing-discriminator or the retry-limit check each makes the intended tests fail.

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
| test_recovery.py | 13 (start-up recovery: interrupted/assigned/testing jobs, feedback restore, retry-limit bound, idempotency, left-alone cases) |
| test_orchestrator_guard.py | 14 (duplicate generation/test/deploy/approve requests with real threads, stale-session lost update, provider selection) |

Bugs found by testing during construction (all fixed, regression tests added): timestamps serialised as `…+00:00Z` (UI showed "Invalid Date"); `[hidden]` overridden by CSS `display:grid`; `ev.currentTarget` null after `await` in form handlers (found by driving the real UI in a browser).

## 3. Manual browser run (2026-10-17)
Real server with `DEVNEXUS_MOCK_AGENT_DELAY=1.5`: created a project and requirement through the forms, switched to a Developer, created a task, assigned → watched Generating → In Review, viewed the diff, approved → Testing → Ready for Deployment, authorised deployment → Deployed; dashboard showed 100% progress, 1 task, simulated 100% coverage, velocity bar in the current sprint; reports page showed the COCOMO figures and the Phase 2 baseline. No console errors on the projects page. `scripts/demo_seed.py` populated a second database through the API (5 tasks in 5 different states).

### 3.1 Browser smoke checklist (PLAN-12)
Run before every demo and after any UI change. Start the server, run `scripts/demo_seed.py` once, then:

| # | Check | Pass when |
|---|---|---|
| 1 | Open all 7 pages as PM and as Developer | data loads, no error toast, no console error |
| 2 | Resize to 1280, 768 and 360 px | no sideways scroll on any page; nav collapses to ☰ below 860 px |
| 3 | As PM, create a project through the form | redirected to the new project page |
| 4 | As PM, add a Draft requirement, Edit it, then Approve it | row shows "Approved · locked" with no buttons; Edit details saves the project; an end date before the start date shows an error toast |
| 5 | Switch to a Developer | no project form, pipeline read-only, no requirement buttons; task form visible |
| 6 | Create a task and assign it | page refreshes on its own to *In Review*; diff has line numbers |
| 7 | Reject using a quick comment, then Approve, then Authorise deployment | 2 agent runs; comment in History; status ends *Deployed* |
| 8 | Toggle Table / Board on the project page | board column counts equal the table's status-group counts |
| 9 | Notifications: Mark read | row loses its marker; bell count drops by 1 |
| 10 | Dashboard on a fresh database | Getting started shows 0/7 and ticks as steps 3–7 happen; Hide keeps it hidden after reload |

**Executed 2026-10-20 (Member C, branch `test/ui-structure`, Linux / CachyOS, Python 3.14.7, Chromium headless via Playwright 1.64.0).** These checks were *scripted in a headless browser against a running server*, not clicked by a person. All 10 passed:
1–2: 10 URLs × 2 roles × 3 widths = 60 views, no console/page errors, no horizontal scroll (before PLAN-10: 22 of 60 views overflowed). 3, 5–7, 9: forms-only run on an empty database (no API shortcuts) passed; bell 4 → 3. 4: edit, approve, lock, date-error toast and Developer view verified, with API state checked after each step. 8: board = table = API counts (queued 1, in progress 2, completed 1, failed 1). 10: 0/7 → 7/7 through real actions; Hide survives reload.
Not covered: Windows/macOS browsers, real touch devices, screen readers, and a first-time human user (NFR-7 timing remains PLAN-19).

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
| NFR-5 | restart keeps tasks, history, users; interrupted jobs are re-run | passes; real server killed mid-generation (`taskkill /F`) → on restart the run is closed as failed, a new run completes, task reaches In Review; a second restart changes nothing (2026-10-20) |
| End-to-end (HTTP) | 69 checks against a real server: project/requirement/pipeline → task → assign → diff → reject/rework → approve → tests → deploy; role refusals; invalid transitions; `[fail-tests]`, `[fail-llm]`, `[fail-llm-always]` retry limit, `[fail-deploy]`; dashboard/estimation on empty and populated projects; hard restart persistence | 69/69 passed (2026-10-20). Script not committed. Browser (visual) pass **not done** on 2026-10-20: the Chrome extension was not connected |
| NFR-6 | commit to main/master, `..` paths, bad branch names refused; failed deploy restores main | passes |
| NFR-7 | first-time PM < 10 min | **not yet measured** (PLAN-19) |
| NFR-8 | 50 tasks created + assigned in one project | passes (sequential) |
| NFR-4, 9, 10 | — | deferred/partial, see KNOWN_LIMITATIONS.md |

## 7. Exit criteria for release v1.0
All P0/P1 issues merged · `pytest` green with coverage ≥ 90% · traceability has no status the tests do not support · two clean demo rehearsals from a fresh clone.
