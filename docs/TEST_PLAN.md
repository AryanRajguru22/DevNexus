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

## 2. Latest automated results (real, 2026-10-28, Windows 11, Python 3.11.9, release candidate `release/rc1`)

Command (fresh venv `python -m venv <dir>`; `pip install -r requirements.txt`):
```
pytest -q -p no:cacheprovider --cov=app --cov-report=term-missing:skip-covered
387 passed in 89 s          (0 failed, 0 skipped, 0 xfail)
TOTAL coverage 99% of app/  (1848 statements, 17 missed; app/__main__.py is the uvicorn launcher, 0%)
```
History: baseline `37ab6aa` 248 → `f5364a0` (PLAN-13/14) 275 → + PR #11–#17 355 (+1 xfail for #16) → + fixes/tests for #3, #16, `tests_failed` guard, Ollama provider 387. Earlier macOS result (275 passed, 98%, Python 3.11.15) belongs to `f5364a0` and was not repeated.

Live checks (real server, `python scripts/e2e_check.py`): **34/34 passed** - pages, project/requirement create+edit+lock, role refusals, assign→generate→review diff, reject→rework, approve→tests, fail-tests rework, LLM outage + retry limit, failed deploy → retry → success, audit rows, notifications, dashboard, COCOMO, risk report, invalid-state/input/404.
Kill-and-restart (real server, mock agent delay 20 s, process killed while *Generating*): after restart the interrupted run is `failed` ("Interrupted: …", audit `agent.error`), a new run completes and the task is In Review; projects created before the restart are still listed.

| File | Tests |
|---|---|
| test_workflow.py | 103 |
| test_edits.py | 34 |
| test_ui_pages.py | 52 |
| test_ollama_provider.py | 28 |
| test_api_projects.py | 35 |
| test_adapters_and_agents.py | 34 |
| test_task_flows.py | 33 |
| test_orchestrator_edges.py | 10 |
| test_analytics.py | 19 |
| test_recovery.py | 13 |
| test_orchestrator_guard.py | 14 |
| test_audit.py / test_nfr.py | 9 / 3 |

(Per-file counts from `pytest --collect-only -q`; they sum to 387.) Mutation checks done by the authors of PLAN-13/14 (disabling the compare-and-set, running-run check, Testing-discriminator, retry-limit check) and, for this release, the #3 and #16 regression tests were confirmed to **fail on the unfixed code** and pass on the fixed code.

Bugs found by testing during construction (all fixed, regression tests added): timestamps serialised as `…+00:00Z` (UI showed "Invalid Date"); `[hidden]` overridden by CSS `display:grid`; `ev.currentTarget` null after `await` in form handlers (found by driving the real UI in a browser).

## 3. Browser / UI evidence

**2026-10-28 (release candidate, headless Chrome driven over the DevTools protocol, device-metrics emulation):** 7 pages (`/`, `/projects`, `/projects/1`, `/tasks/N`, `/reports`, `/audit`, `/notifications`) as Project Manager at 1280, 768 and 360 px, and as Developer at 1280 and 360 px (dashboard, project page, an In Review, a Failed and a freshly generated task): **no horizontal page overflow, no console errors**. Screenshots read by eye: hamburger menu at 360 px; user switcher fits and does not repeat the role (#1, #7); Failed task shows the single true reason "retry limit is reached, so this task is reported as a risk" (#4); create-task form is separated from the task table (#8); wide tables scroll inside their own card (`.table-wrap`) instead of scrolling the page (#2, #9); review page shows Approve/Reject, line-numbered diff containing only the task's own file (#3 and PLAN-11). Not individually inspected: #5 (status badge at 360 px on the dashboard) and #6 (group badge) beyond the overflow measurement.
**Not covered:** keyboard-only navigation and screen readers (not tested), real touch devices, Firefox/Safari, a first-time human user (NFR-7). The Chrome extension was not connected, so the interactive click-through of 2026-10-17 was not repeated; the same journeys were driven through the real HTTP API by `scripts/e2e_check.py`.

Earlier manual run (2026-10-17, interactive browser): project and requirement created through the forms, task assigned → In Review → approved → Ready → deployed; dashboard 100%, velocity bar, COCOMO page; no console errors.

## 4. Requirement → test map
See REQUIREMENTS_TRACEABILITY.md (Verification column). Member B keeps the *Evidence* cells current .

## 5. Workflow conformance (checked against the Phase 3 PDF, 2026-10-28)

Sources: Phase 3 §9 state table + Fig 3.7, UC-03 (alt 3a/4a), UC-05 (3a), UC-06 (5a), UC-07 (2a/3a), A-2. Code: `app/workflow.py::TRANSITIONS`. Every row is exercised by `tests/test_workflow.py` (`test_valid_transition_changes_state_and_writes_audit[…]`) and, through HTTP, by `tests/test_task_flows.py`.

| Event | From → To | Actor | Guards (beyond state + actor) | Invalid-state result | Audit action | Notification / run |
|---|---|---|---|---|---|---|
| `assign` (assignTask) | Created → Assigned | Developer | code_generation active | 409 `invalid_transition` | `task.assign` | queues generation job |
| `agent_start` | Assigned → Generating | Code Gen. agent | - | same | `agent.start` | run `running` |
| `code_ready` (codeReady) | Generating → In Review | Code Gen. agent | - | same | `agent.generate` | run `completed`, "code ready" to Developer |
| `agent_error` | Generating → Failed | Code Gen. agent | - | same | `agent.error` | run `failed`, `task_failed` to Developer + PM |
| `approve` ([approved]) | In Review → Testing | Developer (human) | testing active | same | `task.approve` | starts test job |
| `reject` ([rejected]) | In Review → Generating | Developer (human) | comments required (API, 422); code_generation active; rework allowed | same; at the limit 409 `retry_limit_exceeded`, task stays In Review | `task.reject` | new run with the comments as feedback |
| `tests_passed` | Testing → Ready for Deployment | Testing agent | - | same | `agent.test` | `tests_passed` |
| `tests_failed` ([tests failed]) | Testing → Generating | Testing agent | code_generation active; rework allowed | at the limit / agent inactive: task stays in Testing, failed `TEST_RESULT` kept, `risk_threshold` to PM | `agent.test` | new run with the failure report |
| `authorise_deployment` | Ready for Deployment → Deployed | Developer or PM (human) | deployment active; completed run exists | same | `task.deploy_authorise` (before the agent acts) + `agent.deploy` | `deployment_completed`; on failure `deployment_failed`, task stays Ready for Deployment |
| `retry` | Failed → Assigned | Developer (human) | code_generation active; rework allowed | same | `task.retry` | queues generation job |

Any other (state, event) pair → 409 `invalid_transition` (tests: `test_every_other_state_event_pair_is_rejected`, 70 pairs); wrong actor → 403 (audited as `access.denied` at the API).

**Findings of this review**
1. *Doc/code mismatch, fixed in the docs:* `TEAM_CONTRACT §4` listed only "rework allowed" as guard for `reject` and `tests_failed`; the code also requires the Code Generation agent to be active (both return to Generating; UC-03 3a refuses work for an inactive agent). The code is the defensible reading; the contract now says so and `test_inactive_agent_blocks_the_transition` covers `tests_failed` too.
2. *Retry limit exceeded - interpretation (project-level assumption A-2):* the PDF says only that the task "is reported as a risk instead of looping indefinitely" and gives no destination state. We refuse the event, keep the task in its state, write `task.retry_limit_exceeded`, notify the PM and add the task to the risk report. No ninth state or extra transition is invented. Consequence: a task in *Testing* at the limit has no automatic way out (the Developer can re-run the tests); it is a documented limitation.
3. The state table in the PDF is garbled in text extraction for the `Deployed`/`Failed` rows; the reading `Failed --retry--> Assigned` and `Deployed` = final is confirmed by UC-03 4a and by the text "retry from Failed".

## 6. Non-functional evidence

| NFR | Check | Result |
|---|---|---|
| NFR-1 | assign → In Review time with mock provider | < 1 s (real LLM not measured) |
| NFR-2 | dashboard request with 50 tasks | < 5 s asserted; typically tens of ms |
| NFR-5 | restart keeps tasks, history, users; interrupted jobs are re-run | passes; real server killed mid-generation (`taskkill /F`) → on restart the run is closed as failed, a new run completes, task reaches In Review; a second restart changes nothing (2026-10-20) |
| End-to-end (HTTP) | `scripts/e2e_check.py` (committed): 34 checks against a real server - pages, project/requirement create + edit + lock, role refusals, assign → generate → diff (only own files) → reject/rework → approve → tests → deploy, `[fail-tests]`, `[fail-llm-always]` retry limit, `[fail-deploy]` then success, audit, notifications, dashboard, COCOMO, risk report, invalid state / input / 404 | 34/34 passed on 2026-10-28, both in the working tree and in a fresh `git clone` of `release/rc1` (commit `efcf1f3`) using a fresh venv |
| NFR-6 | commit to main/master, `..` paths, bad branch names refused; failed deploy restores main | passes |
| NFR-7 | first-time PM < 10 min | **not measured** |
| NFR-8 | 50 tasks created + assigned in one project | passes (sequential) |
| NFR-4, 9, 10 | — | deferred/partial, see KNOWN_LIMITATIONS.md |

## 7. Exit criteria for release v1.0
All P0/P1 issues merged · `pytest` green with coverage ≥ 90% · traceability has no status the tests do not support · two clean demo rehearsals from a fresh clone.
