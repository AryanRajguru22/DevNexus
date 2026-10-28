# Requirements Traceability Matrix

Identifiers and wording are from the Lab Record (Lab 2) and Phase 3 §14.8. Status vocabulary: **implemented**, **partially implemented**, **planned**, **blocked**, **deferred**.
Evidence = automated tests in `tests/` (run `pytest`). Last verified: 2026-10-28 on the release candidate `release/rc1` — **387 passed**, app coverage 99% (fresh venv from `requirements.txt`); 34/34 live HTTP checks (`scripts/e2e_check.py`). Integrated: PR #11–#15 (edits, UI tokens/board/diff numbers, UI tests) and #17 (orchestrator edge tests). Fixes: #3 (review diff), #16 (rollback when the CI/CD runner raises). Not integrated: PLAN-03 conformance table (uncommitted on its owner's machine), PLAN-05/06 quality gates (not required by any source; see KNOWN_LIMITATIONS 9a).
Owner of this file: Member B (update the *Status* and *Evidence* columns whenever a PR changes them).

## Functional requirements

| ID | Requirement (short) | Module / use case | Source files | Verification | Status |
|---|---|---|---|---|---|
| FR-1 | PM creates project with problem statement, scope, objectives | Project & Requirement Service · UC-01 | `routers/projects.py`, `models.Project`, `schemas.ProjectCreate` | `test_api_projects.py` (create, validation ×7, role refusal) | implemented |
| FR-2 | Capture functional / non-functional requirements | same · UC-01 | `routers/projects.py`, `models.Requirement` | `test_api_projects.py` (add/list, validation ×6); editing (extension E-5, PLAN-08): `routers/edits.py`, `test_edits.py` | implemented (create/list); edit = extension pending confirmation |
| FR-3 | Configure agent pipeline (active agents, constraints, retry limit) | Agent Orchestrator · UC-02 | `validation.PipelineConfig`, `PUT /pipeline`, `workflow` gates | `test_api_projects.py` (pipeline ×8), `test_workflow.py` (inactive agent ×5), `test_task_flows.py` | implemented |
| FR-4 | Developer creates tasks from requirements and assigns to an agent | Project & Req. Service · UC-03 | `routers/tasks.py`, `workflow` (assign) | `test_task_flows.py` (creation rules, assignment, agent_inactive, agent_not_assignable) | implemented |
| FR-5 | Code Generation Agent produces code from task + requirement | Code Generation Agent · UC-03 | `agents/codegen.py`, `adapters/llm.py` (mock), `adapters/ollama.py` (optional local model) | `test_adapters_and_agents.py`, `test_task_flows.py` (happy path, rework, LOC limit), `test_ollama_provider.py` (28: request shape, fences, every failure mode) | partially implemented — mock LLM (D-4) |
| FR-6 | Monitor status (queued / in-progress / completed / failed) | Orchestrator · UC-04 | `enums.STATUS_GROUP`, `GET /tasks`, task page polling | `test_task_flows.py` (status_group, filters) | implemented |
| FR-7 | Explicit Developer approval before merge | Gateway/Audit · UC-05 | `workflow` (approve/reject), `GET /tasks/{id}/diff`, `LocalGitAdapter` | `test_task_flows.py` (nothing on main before approval/deploy, reject, comments required); `test_workflow.py` | implemented |
| FR-8 | Testing Agent generates and executes tests, reports pass/fail | Testing Agent · UC-06 | `agents/testing.py`, `orchestrator.run_tests` | `test_adapters_and_agents.py` (never executes code), `test_task_flows.py` (fail → rework → pass) | partially implemented — static, simulated (D-5) |
| FR-9 | Deployment only after explicit authorisation | Deployment Agent · UC-07 | `orchestrator.deploy_task`, `agents/deployment.py` | `test_task_flows.py` (success, failed deploy + rollback incl. a runner that raises - `test_orchestrator_edges.py`, PM may authorise, agent inactive, final state) | partially implemented — mock CI/CD (D-4) |
| FR-10 | Estimation metrics (effort, cost, schedule) from task data | Analytics · UC-08/09 | `services/analytics.estimation`, `GET /reports/estimation` | `test_analytics.py` (COCOMO reproduces Phase 2: 21.3 pm, 8.0 months) | implemented |
| FR-11 | Risk report: delayed tasks, repeated failures, slippage | Analytics · UC-09 | `analytics.assess_risk`, `generate_risk_report`, `/reports/risk` | `test_analytics.py` (thresholds, delayed, slippage, repeated failures, one-report-once) | implemented (rule A19 pending team confirmation) |
| FR-12 | Dashboard: status, coverage, velocity, risk | Analytics + UI · UC-08 | `analytics.dashboard`, `web/` | `test_analytics.py`, `test_ui_pages.py`; manual browser run 2026-10-17 | implemented (coverage simulated) |
| FR-13 | Notifications on failure, deployment completion, risk threshold | Notification & Audit · UC-10 | `notifications.py`, `GET /notifications` | `test_task_flows.py` (recipients, read), `test_analytics.py` | implemented (in-app only; no e-mail) |
| FR-14 | Audit trail of agent actions and human approvals | Notification & Audit | `audit.py`, `GET /audit` | `test_audit.py` (append-only, one actor), `test_task_flows.py` (history) | implemented |

## Non-functional requirements

| ID | Requirement (short) | How realised | Verification | Status |
|---|---|---|---|---|
| NFR-1 | ≤ 60 s for a < 200 LOC task | mock provider returns in milliseconds; `max_loc` pipeline limit | `test_nfr.py::test_nfr1…` (mock only; real LLM latency not measured) | partially implemented |
| NFR-2 | Dashboard refresh ≤ 5 s | computed live per request; UI polls every 5 s | `test_analytics.py::test_dashboard_is_fast_with_50_tasks` | implemented |
| NFR-3 | Role-based authorisation before code/infra-changing actions | `security.require_roles` + `workflow` actor rules; denials audited | `test_api_projects.py`, `test_workflow.py` (wrong actor ×9), `test_task_flows.py` | partially implemented — roles enforced, authentication is a demo switcher (D-6) |
| NFR-4 | TLS 1.2+ | — | — | deferred (D-3) |
| NFR-5 | 99.5% uptime, queue during downtime | data persists in SQLite; start-up recovery re-runs interrupted jobs (PLAN-13); no durable queue, no uptime measured | `test_nfr.py::test_nfr5…`, `test_recovery.py` (13 tests), manual kill-and-restart of a real server 2026-10-20 | partially implemented |
| NFR-6 | Failed task cannot corrupt repo; agent commits on isolated branches | `LocalGitAdapter` refuses `main`/`master`, path traversal; merge snapshot + rollback | `test_adapters_and_agents.py` | implemented |
| NFR-7 | First-time PM creates project + sees dashboard < 10 min unaided | guided forms, empty states, role notes | not yet timed with a first-time user (proposed PLAN-19) | partially implemented |
| NFR-8 | ≥ 50 concurrent agent tasks per project | background jobs; 50 tasks created and assigned; duplicate-job guard (PLAN-14) | `test_nfr.py::test_nfr8…` (sequential smoke); `test_orchestrator_guard.py` (14 tests, threads on one task — not 50 parallel tasks) | partially implemented |
| NFR-9 | Agents independently deployable/upgradable | each agent is a module behind an interface | structural only | partially implemented (D-2) |
| NFR-10 | Any cloud; GitHub and GitLab integration | adapter interfaces; pure Python, runs on Windows/macOS/Linux | — | partially implemented — no real GitHub/GitLab adapter |
| NFR-11 | Every human approval/rejection/override logged with timestamp + user ID | `audit_log` rows with `user_id`, `timestamp`; DB triggers | `test_audit.py`, `test_task_flows.py` (approve/reject/deploy rows) | implemented |

## Use cases and design rules

| Item | Where verified |
|---|---|
| UC-01…UC-10 | FR rows above (UC-04 → FR-6, UC-08 → FR-12) |
| Fig 3.7 state chart (8 states, 10 transitions) | `test_workflow.py` (transition table equals the chart; every other (state, event) pair rejected: 70 cases) |
| Retry limit bounds rework/retry (A-2); no extra state | `test_workflow.py`, `test_task_flows.py` |
| Review → test → deploy order via pre-conditions (C-03) | `test_task_flows.py` (409 on wrong state for every action) |
| R1–R10 mitigations | ARCHITECTURE.md §6 |

## Not implemented (deliberately, see KNOWN_LIMITATIONS.md)
Real LLM / second provider · GitHub/GitLab/CI integrations · TLS · PostgreSQL, gRPC, queue, containers · user administration, QA and Admin actors (out of scope per Phase 3) · e-mail notifications · issue-tracker integration · backups.
