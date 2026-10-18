# GitHub Issues Plan (PROPOSED)

**None of these issues exist on GitHub yet.** IDs `PLAN-xx` are *proposed* plan identifiers, not GitHub issue numbers; Aryan creates the issues after review and may then add the real numbers. Branch names are *suggested*; no branch exists yet. The same data is in `GITHUB_ISSUES_PLAN.csv`.

**All clock times below are proposed by Aryan and not yet agreed by the team.** What is due on 23 Oct (submission contents) is not defined in any source document; confirm it with the instructor.

Deadline: **Fri 23 Oct 2026**. Feature freeze **Tue 20 Oct 21:00**. Priorities: P0 must, P1 should, P2 cut first.

| ID | Phase | Title | Owner | Pri | Starts | Target | Reviewer |
|---|---|---|---|---|---|---|---|
| PLAN-01 | 1 | Review the baseline, then commit and push it to GitHub main | Aryan | P0 | Immediately | Sun 18 Oct (done) | Member B (verifies the clone) |
| PLAN-02 | 1 | Confirm the proposed contracts and open decisions; create the GitHub issues | Aryan | P0 | After PLAN-01 | Sun 18 Oct 20:00 | Member B and Member C read and acknowledge |
| PLAN-03 | 1 | Onboarding and independent baseline verification | Member B | P0 | After PLAN-01 (setup); conformance table can start from the Phase 3 PDF now | Sun 18 Oct | Aryan |
| PLAN-04 | 1 | Onboarding and UI walkthrough | Member C | P0 | After PLAN-01 | Sun 18 Oct | Aryan |
| PLAN-05 | 2 | Quality gates module (approval and deployment gates), standalone and unit-tested | Member B | P0 | Immediately after cloning | Mon 19 Oct | Aryan |
| PLAN-06 | 2 | Wire the quality gates into the workflow and add rework/retry validation matrix tests | Member B | P0 | After PLAN-05 | Tue 20 Oct 12:00 | Aryan |
| PLAN-07 | 2 | Orchestrator edge-case and crash-path tests | Member B | P1 | Immediately after cloning | Tue 20 Oct | Aryan |
| PLAN-08 | 2 | Backend CRUD: edit requirements and projects (proposed contract C-3) | Member C | P0 | Immediately after cloning | Tue 20 Oct 12:00 | Aryan |
| PLAN-09 | 2 | UI: edit and approve requirements, edit project details | Member C | P1 | Immediately (against the proposed contract) | Tue 20 Oct 18:00 | Aryan (Member B checks the flow) |
| PLAN-10 | 2 | UI: real logo, design tokens, responsive check, getting-started checklist (NFR-7) | Member C | P1 | Immediately after cloning | Mon 19 Oct | Aryan |
| PLAN-11 | 2 | UI stretch: task board and richer review screen (cut first if behind) | Member C | P2 | After PLAN-10 | Tue 20 Oct 18:00 | Aryan |
| PLAN-12 | 2 | UI regression tests and browser smoke checklist | Member C | P1 | Immediately after cloning | Tue 20 Oct | Member B |
| PLAN-13 | 2 | Startup recovery for interrupted agent jobs (NFR-5) | Aryan | P1 | Immediately | Mon 19 Oct | Member B |
| PLAN-14 | 2 | Agent-run hardening: duplicate-job guard and selectable LLM provider | Aryan | P1 | After PLAN-13 | Tue 20 Oct 12:00 | Member B |
| PLAN-15 | 2 | Daily review and merge queue | Aryan | P0 | Immediately | Daily Sun 18 – Thu 22 Oct | Member B or Member C spot-check |
| PLAN-16 | 3 | End-to-end demo scenario as an automated test | Member B | P1 | Immediately after cloning | Tue 20 Oct 18:00 | Aryan |
| PLAN-17 | 3 | Integration #2 and FEATURE FREEZE | Aryan | P0 | Tue 20 Oct 18:00 | Tue 20 Oct 21:00 (FREEZE) | Member B runs the regression |
| PLAN-18 | 4 | Independent regression and manual QA on a fresh clone | Member B | P0 | Wed 21 Oct 08:30 | Wed 21 Oct 13:00 | Aryan |
| PLAN-19 | 4 | UI bug fixes and the timed usability check (NFR-7) | Member C | P0 | Wed 21 Oct 10:00 | Wed 21 Oct 18:00 | Aryan |
| PLAN-20 | 4 | Backend bug fixes and cross-platform install check | Aryan | P0 | Wed 21 Oct 10:00 | Wed 21 Oct 18:00 | Member B |
| PLAN-21 | 4 | Traceability and test-evidence finalisation | Member B | P0 | Wed 21 Oct 18:00 | Wed 21 Oct 21:00 | Aryan |
| PLAN-22 | 5 | Demo rehearsals (all three) | Aryan | P0 | After PLAN-21 (Wed 21 Oct 21:00) | Thu 22 Oct 10:00 (#1) and 16:00 (#2) | all |
| PLAN-23 | 5 | Final documentation, release tag and submission package | Aryan | P0 | Thu 22 Oct | Thu 22 Oct 21:00 | Member B |
| PLAN-24 | 5 | Deadline day: contingency only | Aryan | P0 | Fri 23 Oct | Fri 23 Oct | — |

## Dependency chain

```
PLAN-01 (push) ─► PLAN-03 / PLAN-04 (setup, Sun) ─► all Phase 2 work
PLAN-02 (contracts C-2, C-3 confirmed by Sun 20:00)
PLAN-05 ─► PLAN-06 ─┐
PLAN-08 ─► PLAN-09 ─┤
PLAN-10 ─► PLAN-11 ─┼─► PLAN-17 (freeze Tue 21:00) ─► PLAN-18 ─► PLAN-19 / PLAN-20 ─► PLAN-21 ─► PLAN-22 ─► PLAN-23 ─► PLAN-24
PLAN-13 ─► PLAN-14 ─┘   (PLAN-07, PLAN-12, PLAN-16 are independent and feed PLAN-17/18)
```

## File ownership (no file has two writers at the same time)

| Area | Owner | Rule |
|---|---|---|
| `app/models.py`, `schemas.py`, `db.py`, `config.py`, `errors.py`, `security.py`, `main.py` | Aryan | Only exception: Member C adds `edits` to the import and router tuple in `main.py` in PLAN-08 |
| `app/agents/`, `app/adapters/`, `app/services/`, the projects, tasks, reports and system routers | Aryan | Member B may fix ≤ 10 lines in `orchestrator.py` (PLAN-07) with Aryan's review |
| `app/workflow.py`, `app/quality_gates.py` (new), `app/validation.py` | Member B | Transition table frozen; gates added in PLAN-06 |
| `app/routers/edits.py` (new), `tests/test_edits.py` | Member C | new files, no conflicts |
| `app/web/**`, `tests/test_ui_pages.py` | Member C | one UI PR open at a time (single JS file) |
| `tests/test_quality_gates.py`, `test_orchestrator_edges.py`, `test_e2e_demo.py`, `test_workflow.py` (additions) | Member B | `tests/conftest.py`: additive changes only, Member B |
| `docs/TEAM_CONTRACT.md`, `ARCHITECTURE.md`, `README.md` | Aryan | PRs that change an interface add their own contract row |
| `docs/REQUIREMENTS_TRACEABILITY.md`, `TEST_PLAN.md` | Member B | Member C edits only TEST_PLAN §3 and the NFR-7 row |

## Phase 1 — Baseline and shared contracts

### PLAN-01 — Review the baseline, then commit and push it to GitHub main  *(proposed)*

- **Owner:** Aryan · **Priority:** P0 · **Reviewer:** Member B (verifies the clone) · **Effort:** 1 h
- **Suggested branch:** (direct push to main — one-time exception) · **Target:** Sun 18 Oct (done: initial commit on `main`)
- **Can start:** Immediately
- **Description:** Aryan reviews the local baseline, decides the open publication questions (see the decision register in section 9 of docs/DEVNEXUS_TEAM_WORK_ALLOCATION.md), then creates the first commit and pushes `main`. The first push went straight to `main` (an empty `main` cannot be a PR target): a one-time exception to 'no direct pushes'.
- **Expected files/modules:** whole repository (the publication file list approved by Aryan)
- **Prerequisites:** none (approved by Aryan)
- **Dependencies:** none
- **Acceptance criteria:** `main` exists on GitHub; a fresh clone installs from README and `pytest` shows 248 passed; no .venv, data/, *.db, caches, .env in the commit; the coursework source documents are not in the commit (the Lab Record holds personal data; the others are not cleared for redistribution).
- **Tests and evidence:** `git status` clean; `pytest` on a fresh clone (done by Member B in PLAN-03)

### PLAN-02 — Confirm the proposed contracts and open decisions; create the GitHub issues  *(proposed)*

- **Owner:** Aryan · **Priority:** P0 · **Reviewer:** Member B and Member C read and acknowledge · **Effort:** 1 h
- **Suggested branch:** `docs/contracts-confirmed` · **Target:** Sun 18 Oct 20:00
- **Can start:** After PLAN-01
- **Description:** Review the two PROPOSED interfaces in TEAM_CONTRACT §12 (C-2 quality gates, C-3 edit endpoints) and the ▲ decisions (retry limit default, risk rule, NOTIFICATION table, header-based user switcher, PM may authorise deployment). Mark each confirmed/changed in the docs. Then create the issues from this plan.
- **Expected files/modules:** docs/TEAM_CONTRACT.md §12, docs/PROJECT_AUDIT.md §6
- **Prerequisites:** PLAN-01
- **Dependencies:** PLAN-01
- **Acceptance criteria:** C-2 and C-3 marked confirmed (or edited) by Sun 18 Oct 20:00 so Member B and Member C can rely on them; issues created; each ▲ row resolved.
- **Tests and evidence:** none (documents)

### PLAN-03 — Onboarding and independent baseline verification  *(proposed)*

- **Owner:** Member B · **Priority:** P0 · **Reviewer:** Aryan · **Effort:** 2 h
- **Suggested branch:** `test/conformance-table` · **Target:** Sun 18 Oct
- **Can start:** After PLAN-01 (setup); conformance table can start from the Phase 3 PDF now
- **Description:** Fresh clone, venv, `pip install -r requirements.txt`, `pytest`, start the server, walk through DEMO_SCRIPT.md. Compare `app/workflow.py` with the state chart (Phase 3 Fig 3.7, §9 table, UC-03/05/06/07 alternative flows) and fill the conformance table in TEST_PLAN §5 (one row per transition: PDF reference, code reference, test name). Report any mismatch as an issue.
- **Expected files/modules:** docs/TEST_PLAN.md §5 (table only)
- **Prerequisites:** PLAN-01 (repository cloned)
- **Dependencies:** PLAN-01
- **Acceptance criteria:** Comment with OS, Python version, the real pytest summary line; conformance table complete for all 10 transitions and the 4 alternative flows; mismatches listed.
- **Tests and evidence:** pytest output pasted; table in TEST_PLAN §5

### PLAN-04 — Onboarding and UI walkthrough  *(proposed)*

- **Owner:** Member C · **Priority:** P0 · **Reviewer:** Aryan · **Effort:** 2 h
- **Suggested branch:** `(no branch)` · **Target:** Sun 18 Oct
- **Can start:** After PLAN-01
- **Description:** Same setup as PLAN-03, then use every page as PM and as Developer at desktop and phone width. File at least five concrete defects/improvements (page, steps, screenshot), labelled `ui`.
- **Expected files/modules:** none (issues only)
- **Prerequisites:** PLAN-01 (repository cloned)
- **Dependencies:** PLAN-01
- **Acceptance criteria:** Comment with OS, Python version, real pytest summary; ≥ 5 defect reports with screenshots.
- **Tests and evidence:** pytest output pasted; screenshots


## Phase 2 — Parallel feature development

### PLAN-05 — Quality gates module (approval and deployment gates), standalone and unit-tested  *(proposed)*

- **Owner:** Member B · **Priority:** P0 · **Reviewer:** Aryan · **Effort:** 0.5 d
- **Suggested branch:** `feat/quality-gates` · **Target:** Mon 19 Oct
- **Can start:** Immediately after cloning
- **Description:** Create `app/quality_gates.py` with `check_approval_gate(db, task)` and `check_deployment_gate(db, task)` per proposed contract C-2 (TEAM_CONTRACT §12): approval needs a completed newest agent run; deployment needs the newest completed run to have a latest test result with failed_count = 0 and no newer run than the tested one. Violations raise `ApiError(409, 'quality_gate_failed', ..., details={'gate':..., 'reasons':[...]})`. Pure functions over the existing models; not yet called by the application, so existing behaviour does not change.
- **Expected files/modules:** app/quality_gates.py (new), tests/test_quality_gates.py (new)
- **Prerequisites:** PLAN-03 setup; C-2 as proposed (may start before PLAN-02 confirms)
- **Dependencies:** PLAN-03 (setup only)
- **Acceptance criteria:** Each gate has passing and failing cases for every reason (≥ 12 tests); module imports only `sqlalchemy`, `app.models`, `app.errors` (no routers, services or workflow); full suite still 248+ green.
- **Tests and evidence:** pytest tests/test_quality_gates.py; summary line in the PR

### PLAN-06 — Wire the quality gates into the workflow and add rework/retry validation matrix tests  *(proposed)*

- **Owner:** Member B · **Priority:** P0 · **Reviewer:** Aryan · **Effort:** 0.5 d
- **Suggested branch:** `feat/workflow-gates` · **Target:** Tue 20 Oct 12:00
- **Can start:** After PLAN-05
- **Description:** In `app/workflow.py::check_event`, call the gates for the `approve` and `authorise_deployment` events (after the existing checks), so `available_actions` hides the buttons automatically. Add the error code row to TEAM_CONTRACT §5. Extend workflow tests with a matrix over retry_limit 0–3 × the three rework events (reject, tests_failed, retry) and inactive-agent combinations.
- **Expected files/modules:** app/workflow.py, tests/test_workflow.py (additions), tests/test_quality_gates.py, docs/TEAM_CONTRACT.md (one table row)
- **Prerequisites:** PLAN-05 merged
- **Dependencies:** PLAN-05
- **Acceptance criteria:** A task whose newest run is not tested cannot be deployed (409 `quality_gate_failed`); demonstrated at workflow/unit level, because through the API the gates are defence in depth (see contract C-2). The 244 API-driven existing tests stay unchanged and green; the 4 fixture-seeded tests in tests/test_workflow.py (approve, two authorise_deployment cases, test_available_actions_follow_state_and_role) get fixtures that seed a completed run and a passing test result, with no assertion weakened (found by a local probe that emulated the gates). Matrix tests added (≥ 12 new cases).
- **Tests and evidence:** pytest (full) summary line; new test names listed in the PR

### PLAN-07 — Orchestrator edge-case and crash-path tests  *(proposed)*

- **Owner:** Member B · **Priority:** P1 · **Reviewer:** Aryan · **Effort:** 0.75 d
- **Suggested branch:** `test/orchestrator-edges` · **Target:** Tue 20 Oct
- **Can start:** Immediately after cloning
- **Description:** Raise coverage of `app/services/orchestrator.py` from 81% to ≥ 92% using monkeypatch: testing agent raising, deployment agent raising, generation/test job invoked for a task in the wrong state (stale job), double approve and double assign (second is 409), unexpected exception type from the LLM ends in Failed, no run left `running`. Report any defect as an issue for Aryan; fixes of ≤ 10 lines in `orchestrator.py` are allowed with Aryan's review.
- **Expected files/modules:** tests/test_orchestrator_edges.py (new)
- **Prerequisites:** PLAN-03 setup
- **Dependencies:** PLAN-03 (setup only)
- **Acceptance criteria:** ≥ 8 tests; `pytest --cov=app.services.orchestrator` ≥ 92%; defects found are filed.
- **Tests and evidence:** coverage line pasted in the PR

### PLAN-08 — Backend CRUD: edit requirements and projects (proposed contract C-3)  *(proposed)*

- **Owner:** Member C · **Priority:** P0 · **Reviewer:** Aryan · **Effort:** 1 d
- **Suggested branch:** `feat/edit-endpoints` · **Target:** Tue 20 Oct 12:00
- **Can start:** Immediately after cloning
- **Description:** New router `app/routers/edits.py` with `PATCH /api/requirements/{req_id}` and `PATCH /api/projects/{project_id}` as specified in TEAM_CONTRACT §12 (C-3), role project_manager, audited (`requirement.update`, `project.update`). Pydantic models live inside the new file so no shared schema file is touched. The only shared-file change is in `app/main.py`: add `edits` to the import and to the `for module in (system, projects, tasks, reports)` router tuple (agreed exception: Aryan does not edit main.py between Mon 19 and Tue 20 Oct). C-3 is an extension: no FR or Phase 3 section 14.5 endpoint requires editing, and the P0 priority is a team choice Aryan may revisit.
- **Expected files/modules:** app/routers/edits.py (new), tests/test_edits.py (new), app/main.py (import + router tuple)
- **Prerequisites:** PLAN-04 setup; C-3 as proposed
- **Dependencies:** PLAN-04 (setup only)
- **Acceptance criteria:** Approved requirement content is locked (422 `requirement_locked`); status moves Draft → Approved only; Developer gets 403 and the denial is audited; unknown ids 404; end date before start date 422; contract rows added to §5; ≥ 12 tests.
- **Tests and evidence:** pytest tests/test_edits.py; full-suite summary line

### PLAN-09 — UI: edit and approve requirements, edit project details  *(proposed)*

- **Owner:** Member C · **Priority:** P1 · **Reviewer:** Aryan (Member B checks the flow) · **Effort:** 0.5 d
- **Suggested branch:** `feat/ui-edit-controls` · **Target:** Tue 20 Oct 18:00
- **Can start:** Immediately (against the proposed contract)
- **Description:** Add edit/approve controls on the project page wired to the C-3 endpoints; hidden for non-PM; locked state shown for Approved requirements; errors shown as toasts. May be developed against the proposed contract and verified once PLAN-08 is merged.
- **Expected files/modules:** app/web/static/js/app.js, app/web/templates/project.html
- **Prerequisites:** C-3 as proposed; PLAN-08 must merge before this PR can (tests/test_ui_pages.py reads /openapi.json)
- **Dependencies:** PLAN-08 (must merge first)
- **Acceptance criteria:** Edit and Approve work end to end in the browser; no button without a handler; `tests/test_ui_pages.py` still passes (it checks every endpoint the JS calls exists).
- **Tests and evidence:** screenshots of before/after; pytest summary

### PLAN-10 — UI: real logo, design tokens, responsive check, getting-started checklist (NFR-7)  *(proposed)*

- **Owner:** Member C · **Priority:** P1 · **Reviewer:** Aryan · **Effort:** 1 d
- **Suggested branch:** `feat/ui-branding-onboarding` · **Target:** Mon 19 Oct
- **Can start:** Immediately after cloning
- **Description:** Use the real DevNexus logo file once Aryan supplies it (do not redraw it); consolidate colours/spacing in the CSS variables; verify 360/768/1280 px (no horizontal scroll). Add a 'Getting started' checklist on the dashboard derived from API data (hidden once done).
- **Expected files/modules:** app/web/static/img/, app/web/templates/base.html, dashboard.html, app/web/static/js/app.js (dashboard section only), app/web/static/css/app.css
- **Prerequisites:** PLAN-04 setup; logo file from Aryan (placeholder stays if it does not arrive)
- **Dependencies:** PLAN-04 (setup only)
- **Acceptance criteria:** Logo shown on every page (or placeholder still clearly labelled); screenshots at three widths in the PR; checklist appears and disappears from real data.
- **Tests and evidence:** screenshots; tests/test_ui_pages.py updated for the logo

### PLAN-11 — UI stretch: task board and richer review screen (cut first if behind)  *(proposed)*

- **Owner:** Member C · **Priority:** P2 · **Reviewer:** Aryan · **Effort:** 1 d
- **Suggested branch:** `feat/ui-board-review` · **Target:** Tue 20 Oct 18:00
- **Can start:** After PLAN-10
- **Description:** Board view of tasks by status group on the project page; diff viewer with line numbers and one-click rejection comment templates. Text nodes only, no innerHTML.
- **Expected files/modules:** app/web/static/js/app.js (task and project sections), app/web/static/css/app.css
- **Prerequisites:** PLAN-10 merged (same JS file; one UI PR open at a time)
- **Dependencies:** PLAN-10
- **Acceptance criteria:** Board counts equal the task table counts; existing UI tests pass.
- **Tests and evidence:** screenshots; pytest

### PLAN-12 — UI regression tests and browser smoke checklist  *(proposed)*

- **Owner:** Member C · **Priority:** P1 · **Reviewer:** Member B · **Effort:** 0.5 d
- **Suggested branch:** `test/ui-structure` · **Target:** Tue 20 Oct
- **Can start:** Immediately after cloning
- **Description:** Extend `tests/test_ui_pages.py`: every template extends base, every form input has a label, page titles unique, every `data-` or id referenced by JS exists. Write a 10-line browser smoke checklist in TEST_PLAN §3.
- **Expected files/modules:** tests/test_ui_pages.py, docs/TEST_PLAN.md §3
- **Prerequisites:** PLAN-04 setup
- **Dependencies:** PLAN-04 (setup only)
- **Acceptance criteria:** ≥ 4 new tests; checklist executed once with the result recorded.
- **Tests and evidence:** pytest summary

### PLAN-13 — Startup recovery for interrupted agent jobs (NFR-5)  *(proposed)*

- **Owner:** Aryan · **Priority:** P1 · **Reviewer:** Member B · **Effort:** 1 d
- **Suggested branch:** `feat/startup-recovery` · **Target:** Mon 19 Oct
- **Can start:** Immediately
- **Description:** On application start, re-dispatch tasks left in Assigned/Generating (generation) or Testing (tests), and close orphaned `running` agent runs as failed with a clear message; write the audit entry as the responsible agent.
- **Expected files/modules:** app/services/orchestrator.py, app/services/runtime.py, tests/test_recovery.py
- **Prerequisites:** none
- **Dependencies:** none
- **Acceptance criteria:** After a simulated crash (rows left in Generating/Testing) a new app instance brings the task to In Review/Failed/Ready without manual action; healthy tasks get no duplicate runs.
- **Tests and evidence:** tests/test_recovery.py (≥ 4 tests)

### PLAN-14 — Agent-run hardening: duplicate-job guard and selectable LLM provider  *(proposed)*

- **Owner:** Aryan · **Priority:** P1 · **Reviewer:** Member B · **Effort:** 0.75 d
- **Suggested branch:** `feat/job-guard-provider` · **Target:** Tue 20 Oct 12:00
- **Can start:** After PLAN-13
- **Description:** Prevent two simultaneous generation/test jobs for the same task (known limitation 8); select the LLM provider by `DEVNEXUS_LLM_PROVIDER` with `mock` as the only built-in value and a documented extension point for a real provider.
- **Expected files/modules:** app/services/orchestrator.py, app/services/runtime.py, app/config.py, tests/test_orchestrator_guard.py
- **Prerequisites:** PLAN-13 (same files)
- **Dependencies:** PLAN-13
- **Acceptance criteria:** Concurrent duplicate dispatch produces exactly one run; unknown provider name fails fast with a clear message; docs updated.
- **Tests and evidence:** tests (≥ 4)

### PLAN-15 — Daily review and merge queue  *(proposed)*

- **Owner:** Aryan · **Priority:** P0 · **Reviewer:** Member B or Member C spot-check · **Effort:** ongoing
- **Suggested branch:** `(n/a)` · **Target:** Daily Sun 18 – Thu 22 Oct
- **Can start:** Immediately
- **Description:** Review and squash-merge each PR within a few hours; keep `main` green; own all changes to shared files; 10-minute daily status check.
- **Expected files/modules:** shared files
- **Prerequisites:** none
- **Dependencies:** none
- **Acceptance criteria:** Every merged PR shows a green pytest line; no PR waits more than 6 h.
- **Tests and evidence:** pytest on main after each merge


## Phase 3 — Integration and end-to-end workflows

### PLAN-16 — End-to-end demo scenario as an automated test  *(proposed)*

- **Owner:** Member B · **Priority:** P1 · **Reviewer:** Aryan · **Effort:** 0.5 d
- **Suggested branch:** `test/e2e-demo` · **Target:** Tue 20 Oct 18:00
- **Can start:** Immediately after cloning
- **Description:** Convert DEMO_SCRIPT part B into `tests/test_e2e_demo.py` with the existing `Api` helper: happy path; reject then approve; `[fail-tests]` rework; `[fail-llm-always]` to the retry limit and risk notification; failed deployment then success; role refusals; final dashboard numbers. Prove it detects regressions by temporarily breaking one rule locally (do not commit the break).
- **Expected files/modules:** tests/test_e2e_demo.py (new)
- **Prerequisites:** PLAN-03 setup (can start immediately; extend after PLAN-06/08 merge)
- **Dependencies:** PLAN-03 (setup only)
- **Acceptance criteria:** All scenarios pass on `main`; each asserts final status, audit actions and notifications.
- **Tests and evidence:** pytest summary

### PLAN-17 — Integration #2 and FEATURE FREEZE  *(proposed)*

- **Owner:** Aryan · **Priority:** P0 · **Reviewer:** Member B runs the regression · **Effort:** 3 h
- **Suggested branch:** `(on main)` · **Target:** Tue 20 Oct 21:00 (FREEZE)
- **Can start:** Tue 20 Oct 18:00
- **Description:** Merge all P0/P1 work, resolve conflicts, update TEAM_CONTRACT §5 for everything merged (promote C-2/C-3 from 'proposed'), final README, run the full suite and the demo. Freeze at Tue 20 Oct 21:00.
- **Expected files/modules:** TEAM_CONTRACT.md, README.md, shared files
- **Prerequisites:** PLAN-06, PLAN-08, PLAN-10, PLAN-13 merged (P2 items dropped if not done)
- **Dependencies:** PLAN-06, PLAN-08, PLAN-10, PLAN-13, PLAN-14
- **Acceptance criteria:** main green; contract matches the code; frozen commit identified for the regression run.
- **Tests and evidence:** pytest + coverage on main


## Phase 4 — Regression testing and bug fixes

### PLAN-18 — Independent regression and manual QA on a fresh clone  *(proposed)*

- **Owner:** Member B · **Priority:** P0 · **Reviewer:** Aryan · **Effort:** 0.5 d
- **Suggested branch:** `test/regression-report` · **Target:** Wed 21 Oct 13:00
- **Can start:** Wed 21 Oct 08:30
- **Description:** Fresh clone of the frozen `main`, clean venv, full `pytest --cov`, then the manual checklist (DEMO_SCRIPT parts A–C) on Windows and on any other OS available (macOS/Linux/WSL). Record real results in TEST_PLAN §2–§3; file every defect with steps.
- **Expected files/modules:** docs/TEST_PLAN.md (results), issues
- **Prerequisites:** PLAN-17 freeze
- **Dependencies:** PLAN-17
- **Acceptance criteria:** Test report with real numbers and OS list; every defect filed with reproduction steps and severity.
- **Tests and evidence:** pytest output; checklist ticked

### PLAN-19 — UI bug fixes and the timed usability check (NFR-7)  *(proposed)*

- **Owner:** Member C · **Priority:** P0 · **Reviewer:** Aryan · **Effort:** 0.75 d
- **Suggested branch:** `fix/ui-regression` · **Target:** Wed 21 Oct 18:00
- **Can start:** Wed 21 Oct 10:00
- **Description:** Fix `ui`-labelled defects from PLAN-18. Time one first-time user (not on the team) creating a project and reading the dashboard without help; record the result.
- **Expected files/modules:** app/web/*, docs/TEST_PLAN.md §6 (NFR-7 row)
- **Prerequisites:** PLAN-18 defect list
- **Dependencies:** PLAN-18
- **Acceptance criteria:** No open P0/P1 UI defects; NFR-7 row filled with the measured time (pass/fail is stated honestly).
- **Tests and evidence:** re-run of the failing checks; pytest

### PLAN-20 — Backend bug fixes and cross-platform install check  *(proposed)*

- **Owner:** Aryan · **Priority:** P0 · **Reviewer:** Member B · **Effort:** 0.75 d
- **Suggested branch:** `fix/backend-regression` · **Target:** Wed 21 Oct 18:00
- **Can start:** Wed 21 Oct 10:00
- **Description:** Fix backend defects from PLAN-18; update README 'Verified on' table with real results from PLAN-18 for each OS.
- **Expected files/modules:** backend files, README.md
- **Prerequisites:** PLAN-18 defect list
- **Dependencies:** PLAN-18
- **Acceptance criteria:** No open P0/P1 backend defects; README table contains only verified results.
- **Tests and evidence:** pytest

### PLAN-21 — Traceability and test-evidence finalisation  *(proposed)*

- **Owner:** Member B · **Priority:** P0 · **Reviewer:** Aryan · **Effort:** 0.25 d
- **Suggested branch:** `docs/traceability-final` · **Target:** Wed 21 Oct 21:00
- **Can start:** Wed 21 Oct 18:00
- **Description:** Update every Status/Evidence cell of REQUIREMENTS_TRACEABILITY.md to match merged code and real test results; paste the final pytest and coverage output into TEST_PLAN; list unimplemented items.
- **Expected files/modules:** docs/REQUIREMENTS_TRACEABILITY.md, docs/TEST_PLAN.md
- **Prerequisites:** PLAN-19 and PLAN-20 merged
- **Dependencies:** PLAN-19, PLAN-20
- **Acceptance criteria:** No row claims a status the code or tests do not support; Aryan signs off.
- **Tests and evidence:** final pytest/coverage output


## Phase 5 — Feature freeze, documentation and demo rehearsal

### PLAN-22 — Demo rehearsals (all three)  *(proposed)*

- **Owner:** Aryan · **Priority:** P0 · **Reviewer:** all · **Effort:** 2 h each
- **Suggested branch:** `(n/a)` · **Target:** Thu 22 Oct 10:00 (#1) and 16:00 (#2)
- **Can start:** After PLAN-21 (Wed 21 Oct 21:00)
- **Description:** Rehearsal #1 Thu 22 Oct 10:00 and #2 Thu 22 Oct 16:00 (not Wednesday evening: PLAN-21 runs 18:00-21:00) on the actual demo laptop, from a fresh clone, following DEMO_SCRIPT.md. Member B and Member C ask viva-style questions about their modules; Aryan covers the architecture and state chart. Weak answers become doc or code fixes.
- **Expected files/modules:** docs/DEMO_SCRIPT.md
- **Prerequisites:** PLAN-17, PLAN-21
- **Dependencies:** PLAN-17, PLAN-21
- **Acceptance criteria:** Each member explains their modules, the state chart and the deviations without notes; demo runs end to end twice.
- **Tests and evidence:** demo run notes

### PLAN-23 — Final documentation, release tag and submission package  *(proposed)*

- **Owner:** Aryan · **Priority:** P0 · **Reviewer:** Member B · **Effort:** 2 h
- **Suggested branch:** `docs/release` · **Target:** Thu 22 Oct 21:00
- **Can start:** Thu 22 Oct
- **Description:** Final KNOWN_LIMITATIONS, README, kickoff-to-submission docs; tag `v1.0` on `main` after the final regression (only with Aryan's explicit approval).
- **Expected files/modules:** docs/*, README.md
- **Prerequisites:** PLAN-21, PLAN-22
- **Dependencies:** PLAN-21
- **Acceptance criteria:** Fresh clone → install → demo works from the README alone; tag created; submission files prepared.
- **Tests and evidence:** final pytest run

### PLAN-24 — Deadline day: contingency only  *(proposed)*

- **Owner:** Aryan · **Priority:** P0 · **Reviewer:** — · **Effort:** —
- **Suggested branch:** `(hotfix/*)` · **Target:** Fri 23 Oct
- **Can start:** Fri 23 Oct
- **Description:** No planned work. Reserved for urgent fixes and submission on Fri 23 Oct 2026.
- **Expected files/modules:** —
- **Prerequisites:** —
- **Dependencies:** PLAN-23
- **Acceptance criteria:** Submission made.
- **Tests and evidence:** —
