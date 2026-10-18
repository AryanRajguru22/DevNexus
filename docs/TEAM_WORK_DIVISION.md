# Team Work Division (final)

Deadline **Fri 23 Oct 2026**. Based on the actual code (248 passing tests), the contract and the source documents. Task IDs `PLAN-xx` are *proposed* identifiers (see GITHUB_ISSUES_PLAN.md); GitHub issues are created from that file separately; no feature branches exist yet. **All clock times in this file (20:00, 21:00, noon, 18:00 …) are *proposed* by Aryan and have not been agreed by the team.**

## 1. Principle

The baseline already runs end to end, so nobody waits for anybody. Each member owns **a module with its own files and tests** and works against interfaces that already exist in `docs/TEAM_CONTRACT.md` (REST API §5, workflow §4) or that are **proposed** below (§12 of the contract, to be confirmed by Aryan by Sun 18 Oct 20:00). Aryan is *not* the sole implementer: Member B and Member C each deliver new code modules, not just documentation.

## 2. Responsibilities

**Aryan — core implementation and integration.** Foundation and architecture (`models`, `schemas`, `db`, `main`, `security`), AI provider/mock generation and agent-run handling (`agents/`, `adapters/`, `services/orchestrator.py`), analytics, estimation and risk (`services/analytics.py`), integration, release readiness and the demo. Reviews every PR.

**Member C — UI and connected application features.** The visual system, templates and all user-facing screens (`app/web/`); **backend CRUD** for editing requirements and projects (new `app/routers/edits.py`, PLAN-08); connecting UI actions to the real endpoints and persisted data; UI validation and tests.

**Member B — workflow implementation and independent verification.** The workflow/state-transition module (`app/workflow.py`) and a new **quality-gates module** (`app/quality_gates.py`) enforcing approval and deployment gates (FR-7, FR-9, UC-05/07); retry/rework validation; positive and negative tests; independent regression on a fresh clone with reproducible evidence. Work is cut into small independent units (0.25–1 day) doable with ordinary Python, pytest and manual testing; Claude Code is optional.

## 3. Minimum shared interfaces

| # | Interface | Status | Owner | Used by |
|---|---|---|---|---|
| I-1 | REST API and error envelope — TEAM_CONTRACT §5 | **implemented, frozen** | Aryan | Member C (UI), Member B (tests) |
| I-2 | Workflow: `workflow.check_event/apply_event/available_actions`, `Actor`, transition table — §4 | **implemented, frozen** | Member B | Aryan (orchestrator, routers) |
| C-2 | Quality gates: `quality_gates.check_approval_gate/check_deployment_gate(db, task)`, error `409 quality_gate_failed` — contract §12 | **proposed** | Member B | nobody directly: the gates are called from `workflow.check_event`, which Member B owns |
| C-3 | Edit endpoints: `PATCH /api/requirements/{id}`, `PATCH /api/projects/{id}` — contract §12. **An extension, not a source requirement** (no FR or Phase 3 §14.5 endpoint requires editing) | **proposed** | Member C (backend), Aryan (confirms; also decides whether it stays P0) | Member C (UI) |
| I-3 | UI uses only documented `/api/...` endpoints; buttons come from `allowed_actions` (enforced by `tests/test_ui_pages.py`) | **implemented** | Member C | all |

**Deadline to agree C-2 and C-3: Sun 18 Oct 20:00** (PLAN-02). Work on them may start earlier against the proposed text; if Aryan changes them, the owner adapts in the same PR.

## 4. What can start immediately and what depends on whom

- **Right now (no dependency):** Member B — conformance table from the Phase 3 PDF (PLAN-03 part), PLAN-05, PLAN-07, PLAN-16 skeleton. Member C — PLAN-10, PLAN-12, PLAN-08. Aryan — PLAN-01, PLAN-13.
- **Needs the repository pushed (PLAN-01):** cloning. Until then Aryan can hand over a copy of the project folder. **If the push slips, PLAN-03/04 onboarding and the PLAN-02 20:00 contract deadline slip with it.**
- **Depends on another member:** PLAN-06 ← PLAN-05 (Member B, same owner); PLAN-09 ← PLAN-08 to *merge* (Member C, same owner: `tests/test_ui_pages.py::test_js_only_calls_documented_api_endpoints` reads `/openapi.json`, so JS that calls the new PATCH endpoints fails that test until PLAN-08 is merged); PLAN-11 ← PLAN-10 (same JS file); PLAN-14 ← PLAN-13 (same files); PLAN-17 ← all P0/P1; PLAN-18 ← freeze.

## 5. Schedule

| Day | Aryan | Member B | Member C | Gate |
|---|---|---|---|---|
| Sat 17 Oct (past) | Baseline built and verified locally; nothing pushed | — | — | — |
| Sun 18 Oct | PLAN-01 push as soon as approved; PLAN-02 contracts confirmed by 20:00 (slips if the push slips) | PLAN-03 (setup after the push; conformance table from the PDF now), start PLAN-05 | PLAN-04, start PLAN-08/10/12 | Everyone has `pytest` green on their own machine |
| Mon 19 Oct | PLAN-13, reviews | PLAN-05 PR, PLAN-07 | PLAN-10 PR, PLAN-08 | |
| Tue 20 Oct | PLAN-14, reviews, PLAN-17 from 18:00 | PLAN-06 PR (noon), PLAN-07 PR, PLAN-16 | PLAN-08 PR (noon), PLAN-09, PLAN-12, (PLAN-11 stretch) | **FEATURE FREEZE 21:00** |
| Wed 21 Oct | PLAN-20 | PLAN-18 (morning), PLAN-21 | PLAN-19 | Regression report 13:00; evidence final 21:00 (no rehearsal this evening) |
| Thu 22 Oct | PLAN-22 rehearsals, PLAN-23, tag `v1.0` (after approval) | rehearsals #1 10:00 and #2 16:00 | rehearsals #1 10:00 and #2 16:00 | Release candidate 21:00 |
| Fri 23 Oct | PLAN-24 contingency / submission | — | — | **Deadline** |

Rule of thumb for slipping: drop P2 (PLAN-11) first, then simplify PLAN-14; never drop PLAN-18/21/22/23.

## 6. Assignments in full

### Aryan

| ID | Pri | Deliverable and files | Prerequisites / can start | Acceptance criteria | Tests and evidence | Branch (suggested) | Target | Reviewer |
|---|---|---|---|---|---|---|---|---|
| PLAN-01 | P0 | **Review the baseline, then commit and push it to GitHub main** — files: whole repository (the publication file list approved by Aryan) | none (approved by Aryan); done | `main` exists on GitHub; a fresh clone installs from README and `pytest` shows 248 passed; no .venv, data/, *.db, caches, .env in the commit; the coursework source documents are not in the commit (the Lab Record holds personal data; the others are not cleared for redistribution). | `git status` clean; `pytest` on a fresh clone (done by Member B in PLAN-03) | `(direct push to main — one-time exception, an empty main cannot be a PR target)` | Sun 18 Oct (done) | Member B (verifies the clone) |
| PLAN-02 | P0 | **Confirm the proposed contracts and open decisions; create the GitHub issues** — files: docs/TEAM_CONTRACT.md §12, docs/PROJECT_AUDIT.md §6 | PLAN-01; After PLAN-01 | C-2 and C-3 marked confirmed (or edited) by Sun 18 Oct 20:00 so Member B and Member C can rely on them; issues created; each ▲ row resolved. | none (documents) | `docs/contracts-confirmed` | Sun 18 Oct 20:00 | Member B and Member C read and acknowledge |
| PLAN-13 | P1 | **Startup recovery for interrupted agent jobs (NFR-5)** — files: app/services/orchestrator.py, app/services/runtime.py, tests/test_recovery.py | none; Immediately | After a simulated crash (rows left in Generating/Testing) a new app instance brings the task to In Review/Failed/Ready without manual action; healthy tasks get no duplicate runs. | tests/test_recovery.py (≥ 4 tests) | `feat/startup-recovery` | Mon 19 Oct | Member B |
| PLAN-14 | P1 | **Agent-run hardening: duplicate-job guard and selectable LLM provider** — files: app/services/orchestrator.py, app/services/runtime.py, app/config.py, tests/test_orchestrator_guard.py | PLAN-13 (same files); After PLAN-13 | Concurrent duplicate dispatch produces exactly one run; unknown provider name fails fast with a clear message; docs updated. | tests (≥ 4) | `feat/job-guard-provider` | Tue 20 Oct 12:00 | Member B |
| PLAN-15 | P0 | **Daily review and merge queue** — files: shared files | none; Immediately | Every merged PR shows a green pytest line; no PR waits more than 6 h. | pytest on main after each merge | `(n/a)` | Daily Sun 18 – Thu 22 Oct | Member B or Member C spot-check |
| PLAN-17 | P0 | **Integration #2 and FEATURE FREEZE** — files: TEAM_CONTRACT.md, README.md, shared files | PLAN-06, PLAN-08, PLAN-10, PLAN-13 merged (P2 items dropped if not done); Tue 20 Oct 18:00 | main green; contract matches the code; frozen commit identified for the regression run. | pytest + coverage on main | `(on main)` | Tue 20 Oct 21:00 (FREEZE) | Member B runs the regression |
| PLAN-20 | P0 | **Backend bug fixes and cross-platform install check** — files: backend files, README.md | PLAN-18 defect list; Wed 21 Oct 10:00 | No open P0/P1 backend defects; README table contains only verified results. | pytest | `fix/backend-regression` | Wed 21 Oct 18:00 | Member B |
| PLAN-22 | P0 | **Demo rehearsals (all three)** — files: docs/DEMO_SCRIPT.md | PLAN-17, PLAN-21; Thu 22 Oct 10:00 | Each member explains their modules, the state chart and the deviations without notes; demo runs end to end twice. | demo run notes | `(n/a)` | Thu 22 Oct 10:00 (#1) and 16:00 (#2) | all |
| PLAN-23 | P0 | **Final documentation, release tag and submission package** — files: docs/*, README.md | PLAN-21, PLAN-22; Thu 22 Oct | Fresh clone → install → demo works from the README alone; tag created; submission files prepared. | final pytest run | `docs/release` | Thu 22 Oct 21:00 | Member B |
| PLAN-24 | P0 | **Deadline day: contingency only** — files: — | —; Fri 23 Oct | Submission made. | — | `(hotfix/*)` | Fri 23 Oct | — |

### Member C

| ID | Pri | Deliverable and files | Prerequisites / can start | Acceptance criteria | Tests and evidence | Branch (suggested) | Target | Reviewer |
|---|---|---|---|---|---|---|---|---|
| PLAN-04 | P0 | **Onboarding and UI walkthrough** — files: none (issues only) | PLAN-01 (repository cloned); After PLAN-01 | Comment with OS, Python version, real pytest summary; ≥ 5 defect reports with screenshots. | pytest output pasted; screenshots | `(no branch)` | Sun 18 Oct | Aryan |
| PLAN-08 | P0 | **Backend CRUD: edit requirements and projects (proposed contract C-3)** — files: app/routers/edits.py (new), tests/test_edits.py (new), app/main.py (import + router tuple) | PLAN-04 setup; C-3 as proposed (extension; priority P0 is a team choice Aryan may revisit); Immediately after cloning. `main.py` change = add `edits` to the import and to the `for module in (system, projects, tasks, reports)` tuple | Approved requirement content is locked (422 `requirement_locked`); status moves Draft → Approved only; Developer gets 403 and the denial is audited; unknown ids 404; end date before start date 422; contract rows added to §5; ≥ 12 tests. | pytest tests/test_edits.py; full-suite summary line | `feat/edit-endpoints` | Tue 20 Oct 12:00 | Aryan |
| PLAN-09 | P1 | **UI: edit and approve requirements, edit project details** — files: app/web/static/js/app.js, app/web/templates/project.html | C-3 as proposed; develop against the proposed contract immediately, but the PR can only merge after PLAN-08 (the UI test checks `/openapi.json`) | Edit and Approve work end to end in the browser; no button without a handler; `tests/test_ui_pages.py` still passes (it checks every endpoint the JS calls exists). | screenshots of before/after; pytest summary | `feat/ui-edit-controls` | Tue 20 Oct 18:00 | Aryan (Member B checks the flow) |
| PLAN-10 | P1 | **UI: real logo, design tokens, responsive check, getting-started checklist (NFR-7)** — files: app/web/static/img/, app/web/templates/base.html, dashboard.html, app/web/static/js/app.js (dashboard section only), app/web/static/css/app.css | PLAN-04 setup; logo file from Aryan (placeholder stays if it does not arrive); Immediately after cloning | Logo shown on every page (or placeholder still clearly labelled); screenshots at three widths in the PR; checklist appears and disappears from real data. | screenshots; tests/test_ui_pages.py updated for the logo | `feat/ui-branding-onboarding` | Mon 19 Oct | Aryan |
| PLAN-11 | P2 | **UI stretch: task board and richer review screen (cut first if behind)** — files: app/web/static/js/app.js (task and project sections), app/web/static/css/app.css | PLAN-10 merged (same JS file; one UI PR open at a time); After PLAN-10 | Board counts equal the task table counts; existing UI tests pass. | screenshots; pytest | `feat/ui-board-review` | Tue 20 Oct 18:00 | Aryan |
| PLAN-12 | P1 | **UI regression tests and browser smoke checklist** — files: tests/test_ui_pages.py, docs/TEST_PLAN.md §3 | PLAN-04 setup; Immediately after cloning | ≥ 4 new tests; checklist executed once with the result recorded. | pytest summary | `test/ui-structure` | Tue 20 Oct | Member B |
| PLAN-19 | P0 | **UI bug fixes and the timed usability check (NFR-7)** — files: app/web/*, docs/TEST_PLAN.md §6 (NFR-7 row) | PLAN-18 defect list; Wed 21 Oct 10:00 | No open P0/P1 UI defects; NFR-7 row filled with the measured time (pass/fail is stated honestly). | re-run of the failing checks; pytest | `fix/ui-regression` | Wed 21 Oct 18:00 | Aryan |

### Member B

| ID | Pri | Deliverable and files | Prerequisites / can start | Acceptance criteria | Tests and evidence | Branch (suggested) | Target | Reviewer |
|---|---|---|---|---|---|---|---|---|
| PLAN-03 | P0 | **Onboarding and independent baseline verification** — files: docs/TEST_PLAN.md §5 (table only) | PLAN-01 (repository cloned); After PLAN-01 (setup); conformance table can start from the Phase 3 PDF now | Comment with OS, Python version, the real pytest summary line; conformance table complete for all 10 transitions and the 4 alternative flows; mismatches listed. | pytest output pasted; table in TEST_PLAN §5 | `test/conformance-table` | Sun 18 Oct | Aryan |
| PLAN-05 | P0 | **Quality gates module (approval and deployment gates), standalone and unit-tested** — files: app/quality_gates.py (new), tests/test_quality_gates.py (new) | PLAN-03 setup; C-2 as proposed (may start before PLAN-02 confirms); Immediately after cloning | Each gate has passing and failing cases for every reason (≥ 12 tests); module imports only `sqlalchemy`, `app.models`, `app.errors` (no routers, services or workflow); full suite still 248+ green. | pytest tests/test_quality_gates.py; summary line in the PR | `feat/quality-gates` | Mon 19 Oct | Aryan |
| PLAN-06 | P0 | **Wire the quality gates into the workflow and add rework/retry validation matrix tests** — files: app/workflow.py, tests/test_workflow.py (additions), tests/test_quality_gates.py, docs/TEAM_CONTRACT.md (one table row) | PLAN-05 merged; After PLAN-05 | A task whose newest run is not tested cannot be deployed (409 `quality_gate_failed`); demonstrated at workflow/unit level, because through the API the gates are defence in depth (see contract C-2). The 244 API-driven existing tests stay unchanged and green; the 4 fixture-seeded tests in `tests/test_workflow.py` (`approve`, two `authorise_deployment` cases, `test_available_actions_follow_state_and_role`) get fixtures that seed a completed run and a passing test result, with no assertion weakened (found by a local probe that emulated the gates). Matrix tests added (≥ 12 new cases). | pytest (full) summary line; new test names listed in the PR | `feat/workflow-gates` | Tue 20 Oct 12:00 | Aryan |
| PLAN-07 | P1 | **Orchestrator edge-case and crash-path tests** — files: tests/test_orchestrator_edges.py (new) | PLAN-03 setup; Immediately after cloning | ≥ 8 tests; `pytest --cov=app.services.orchestrator` ≥ 92%; defects found are filed. | coverage line pasted in the PR | `test/orchestrator-edges` | Tue 20 Oct | Aryan |
| PLAN-16 | P1 | **End-to-end demo scenario as an automated test** — files: tests/test_e2e_demo.py (new) | PLAN-03 setup (can start immediately; extend after PLAN-06/08 merge); Immediately after cloning | All scenarios pass on `main`; each asserts final status, audit actions and notifications. | pytest summary | `test/e2e-demo` | Tue 20 Oct 18:00 | Aryan |
| PLAN-18 | P0 | **Independent regression and manual QA on a fresh clone** — files: docs/TEST_PLAN.md (results), issues | PLAN-17 freeze; Wed 21 Oct 08:30 | Test report with real numbers and OS list; every defect filed with reproduction steps and severity. | pytest output; checklist ticked | `test/regression-report` | Wed 21 Oct 13:00 | Aryan |
| PLAN-21 | P0 | **Traceability and test-evidence finalisation** — files: docs/REQUIREMENTS_TRACEABILITY.md, docs/TEST_PLAN.md | PLAN-19 and PLAN-20 merged; Wed 21 Oct 18:00 | No row claims a status the code or tests do not support; Aryan signs off. | final pytest/coverage output | `docs/traceability-final` | Wed 21 Oct 21:00 | Aryan |

## 7. Review and integration rules

- Reviews: Member B → Aryan; Member C → Aryan (Member B checks the flow in the browser for UI PRs); Aryan → Member B.
- One PR per task; squash merge by Aryan; `main` must pass `pytest` at all times. **Exception:** the very first push (PLAN-01) goes straight to `main` because an empty `main` cannot be a PR target; after that, no direct pushes.
- Every PR states: task ID, acceptance criteria ticked, the real `pytest` summary line, screenshots for UI.
- Anyone blocked > 3 hours posts the task ID and the blocker in the group chat; Aryan re-plans or pairs the same day.
- Daily status message by 21:00: done / next / blocked.