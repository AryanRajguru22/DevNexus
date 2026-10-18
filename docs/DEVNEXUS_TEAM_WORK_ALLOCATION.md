<!-- page:portrait cover -->

<div class="cover">
<p class="brand">DevNexus</p>
<p class="subtitle">Team Work Allocation</p>
<p class="academic">Academic project: <b>ASDPIP &mdash; Autonomous Software Development &amp; Project Intelligence Platform</b><br>CSE3132 Software Engineering Lab</p>
<p class="kv"><b>Team:</b> Aryan (project lead) and two teammates, shown as Member B and Member C (role labels; names are kept out of public material until each person consents)</p>
<p class="kv"><b>Final deadline:</b> <b>Friday 23 October 2026</b></p>
<p class="kv"><b>Document version:</b> 1.0</p>
<p class="kv"><b>Prepared:</b> 18 October 2026</p>
<p class="kv"><b>Document status:</b> <b>Issued by Aryan for team review.</b> Clock times, C-2 and C-3 stay proposals until the team agrees them.</p>
<p class="kv"><b>Logo:</b> The official DevNexus logo file is not in the repository (only a labelled placeholder), so a text header is used here.</p>
<p class="note">Task IDs <b>PLAN-01 &hellip; PLAN-24</b> are <b>planning IDs</b> from <code>docs/GITHUB_ISSUES_PLAN.md</code>, not GitHub issue numbers. No feature branches or pull requests exist yet; IDs, branch names and every clock time in this document are <b>proposed</b> until the team agrees them.</p>
</div>

<!-- page:portrait contents -->

## Contents

<!-- toc-start -->
- 1. Document control and sources
- 2. Project overview and final deliverables
- 3. Responsibilities by team member
- 4. Task-by-task assignment matrix
- 5. Milestones and daily schedule, 18-23 October 2026
- 6. Shared development rules
- 7. Communication and accountability
- 8. Definition of done and final handover
- 9. Open decisions and risks
<!-- toc-end -->

<!-- page:portrait -->

## 1. Document control and sources

| Item | Value |
|---|---|
| Document | DevNexus Team Work Allocation, version 1.0, prepared 18 October 2026 |
| Editable source | `docs/DEVNEXUS_TEAM_WORK_ALLOCATION.md`. The PDF is rendered from it by a local script that is **not in the repository** (decision D13). After any edit the PDF must be re-rendered; the version and status line are fixed in both files |
| Generated from | `docs/TEAM_WORK_DIVISION.md`, `docs/GITHUB_ISSUES_PLAN.md` / `.csv` (task data), `docs/TEAM_CONTRACT.md`, `docs/PROJECT_AUDIT.md`, `docs/REQUIREMENTS_TRACEABILITY.md`, `docs/KNOWN_LIMITATIONS.md` and the original course requirement documents (not included in the repository) |
| Authority | The submitted documents; the Phase 3 design PDF wins where it supersedes the earlier labs (its section 15). Nothing in this document adds a requirement. |
| Baseline verified | 18 Oct 2026, Windows 11, Python 3.11.9: **248 tests passed** (about 26 s); coverage of `app/` **98%** (`orchestrator.py` 81%). macOS and Linux: **not yet verified**. |
| What does not exist yet | Feature branches and pull requests. The baseline is the initial commit on `main`; GitHub issues are created from `docs/GITHUB_ISSUES_PLAN.md` separately. |

Status vocabulary used in the decision register (section 9): **Confirmed** = supported by a source document or by verified code and tests; **Pending verification** = plausible but not yet checked; **Awaiting approval** = a team or instructor choice nobody with authority has confirmed.

## 2. Project overview and final deliverables

**What DevNexus is.** DevNexus is the application name; ASDPIP is the academic project name. It is a web platform in which supervised AI agents (code generation, then testing, then deployment) carry out well-scoped development tasks, while a project-intelligence layer gives the Project Manager a dashboard of progress, estimation and risk. Every merge and deployment needs explicit human approval, and every agent action and human approval is written to an append-only audit trail. Actors: Project Manager and Developer (users) and the AI agent subsystem (system actor).

**Current state (verified).** A working baseline covers FR-1 to FR-14 end to end with **mock** LLM, Git and CI/CD adapters, a web UI, and 248 passing tests. FR-5, FR-8 and FR-9 are only *partially* implemented (mock LLM, static simulated tests, mock CI/CD). There is **no real authentication**: the acting user is chosen with a demo user switcher (`X-User-Id` header). These limits are listed in `docs/KNOWN_LIMITATIONS.md` and must never be presented as more than they are.

### Required, optional and stretch work (proposed classification)

| Class | Items | Basis |
|---|---|---|
| **Required: source functionality** | FR-1 to FR-14 and NFR-1 to NFR-11 as traced in `docs/REQUIREMENTS_TRACEABILITY.md`; the 8-state task workflow with a retry limit; role-based approvals; audit trail; notifications; dashboard, COCOMO estimation, risk report | Lab Record Lab 2 (requirements), Phase 2, Phase 3 |
| **Required: close gaps in source NFRs and prove them** | PLAN-13 startup recovery (NFR-5), PLAN-10 getting-started checklist and PLAN-19 timed usability check (NFR-7), PLAN-18/20/21 regression, install check and honest traceability | NFR-5, NFR-7; traceability marks these *partially implemented* |
| **Required: delivery** | PLAN-01 publication, PLAN-17 feature freeze, PLAN-22 rehearsals, PLAN-23 final docs and release tag, PLAN-24 submission | Deadline 23 Oct 2026. What exactly must be submitted is **not defined in any source document**: confirm with the instructor |
| **Extensions needing approval** | C-2 quality gates (PLAN-05, PLAN-06); C-3 edit endpoints (PLAN-08) and their UI (PLAN-09) | No FR, use case or Phase 3 endpoint requires them; basis FR-7/FR-9/UC-07 for C-2 and FR-2 for C-3. Their P0/P1 priority is a team choice |
| **Optional enhancements** | PLAN-07 orchestrator edge tests, PLAN-12 UI structure tests, PLAN-14 duplicate-job guard and provider selection, PLAN-16 automated demo scenario | Quality and robustness; not required by a source |
| **Stretch (cut first)** | PLAN-11 task board and richer review screen (priority P2) | Explicitly marked stretch; drop first if behind |

**Slippage rule (from the plan):** drop P2 (PLAN-11) first, then simplify PLAN-14; never drop PLAN-18, PLAN-21, PLAN-22 or PLAN-23.

### Academic and project deliverables

- The DevNexus repository with a clean install and a working demo from the README alone (PLAN-23).
- Automated test evidence: real `pytest` and coverage output (PLAN-17, PLAN-18, PLAN-21).
- `docs/REQUIREMENTS_TRACEABILITY.md` with no row claiming more than the code and tests support (PLAN-21).
- `docs/KNOWN_LIMITATIONS.md`, `docs/ARCHITECTURE.md`, `docs/TEAM_CONTRACT.md` and `docs/TEST_PLAN.md` matching the final code.
- Two demo rehearsals (PLAN-22) following `docs/DEMO_SCRIPT.md`; each member can explain their modules and the state chart without notes (viva).
- Submission package: **contents and format to be confirmed with the instructor**.

## 3. Responsibilities by team member

Review path (contract section 11): Member B's PRs are reviewed by Aryan; Member C's PRs by Aryan, with Member B checking the flow in the browser for UI PRs; Aryan's PRs by Member B (Member C may spot-check). **Aryan is the final integrator** for every pull request (squash merge) and for the feature freeze, release candidate and tag.

### Aryan: Core implementation and integration

**Primary ownership**

- Foundation and architecture: `app/models.py`, `schemas.py`, `db.py`, `config.py`, `errors.py`, `security.py`, `main.py`.
- AI provider / mock generation and agent-run handling: `app/agents/`, `app/adapters/`, `app/services/orchestrator.py`, `app/services/runtime.py`, `app/services/tasks.py`.
- Analytics, estimation and risk: `app/services/analytics.py`; REST routers `app/routers/projects.py`, `tasks.py`, `reports.py`, `system.py`.
- Shared documents: `docs/TEAM_CONTRACT.md`, `docs/ARCHITECTURE.md`, `README.md`.

**Secondary responsibilities**

- Reviews and squash-merges every pull request within the agreed turnaround (PLAN-15); keeps `main` green.
- Confirms or changes the proposed contracts C-2 and C-3 and resolves the decision register (PLAN-02).
- Supplies the real DevNexus logo file for PLAN-10 (the repository only has a placeholder).
- Feature freeze, release candidate, tag `v1.0` (only after approval), demo and submission.

**Can start independently:** PLAN-13 (startup recovery) and PLAN-15 (review queue). PLAN-01 (publication) is done: it is the initial commit on `main`.

**Dependencies / blocked until:** PLAN-02 after PLAN-01; PLAN-14 after PLAN-13; PLAN-17 after PLAN-06, 08, 10, 13 (and 14); PLAN-20 after PLAN-18; PLAN-22 after PLAN-17; PLAN-23 after PLAN-21 and PLAN-22; PLAN-24 after PLAN-23.

**Required tests:** `tests/test_recovery.py` (>= 4 tests), `tests/test_orchestrator_guard.py` (>= 4 tests); full `pytest` on `main` after every merge; coverage at freeze; manual install check on each available OS.

**Required evidence:** Real `pytest` summary line in every PR; coverage output (PLAN-17); README 'Verified on' rows filled only from PLAN-18 results; demo-run notes (PLAN-22).

**Reviewer:** Member B (Member C may spot-check). **Final integration:** Aryan.

**Branch convention (proposed):** `feat/<area>-<name>`, `fix/<name>`, `test/<name>`, `docs/<name>`; short-lived, rebased on `main`, one PR per task, PR title `[#issue] summary` once real issues exist. Suggested names are in the table below; no branch exists yet.

**Planned tasks (10):** PLAN-01, PLAN-02, PLAN-13, PLAN-14, PLAN-15, PLAN-17, PLAN-20, PLAN-22, PLAN-23, PLAN-24. (Planning IDs, not GitHub issue numbers.)

### Member B: Workflow implementation and independent verification

**Primary ownership**

- Workflow / state transitions: `app/workflow.py` (transition table frozen except through a contract change) and `app/validation.py`.
- New quality-gates module `app/quality_gates.py` (proposed contract C-2) enforcing approval and deployment gates; retry/rework validation tests.
- Test suite ownership: `tests/test_quality_gates.py`, `tests/test_orchestrator_edges.py`, `tests/test_e2e_demo.py` (new), additions to `tests/test_workflow.py`; additive changes only to `tests/conftest.py`.
- Verification documents: `docs/REQUIREMENTS_TRACEABILITY.md` and the evidence tables of `docs/TEST_PLAN.md`.

**Secondary responsibilities**

- Reviews Aryan's pull requests (tests and workflow focus) and checks UI flows in the browser for Member C's UI PRs.
- Runs the independent regression on a fresh clone of the frozen `main` (PLAN-18) and files defects with reproduction steps.
- May fix at most 10 lines in `orchestrator.py` (PLAN-07) with Aryan's review.

**Can start independently:** PLAN-05, PLAN-07 and PLAN-16 can start as soon as the project is cloned. The conformance table of PLAN-03 can start from the Phase 3 PDF now.

**Dependencies / blocked until:** PLAN-03 setup and PLAN-05/07/16 need the repository (PLAN-01); PLAN-06 after PLAN-05; PLAN-18 after PLAN-17 (freeze); PLAN-21 after PLAN-19 and PLAN-20.

**Required tests:** `tests/test_quality_gates.py` (>= 12 tests, pass and fail for every gate reason), >= 12 new workflow matrix cases (retry_limit 0-3 x reject / tests_failed / retry, inactive agents), `tests/test_orchestrator_edges.py` (>= 8 tests, orchestrator coverage >= 92%), `tests/test_e2e_demo.py` (all demo scenarios). Wiring C-2 requires updating 4 fixture-seeded tests in `tests/test_workflow.py` without weakening any assertion.

**Required evidence:** `pytest` summary line and coverage line pasted in PRs; conformance table in `docs/TEST_PLAN.md` section 5; regression report with real numbers and OS list; final pytest/coverage output in `docs/TEST_PLAN.md`.

**Reviewer:** Aryan. **Final integration:** Aryan.

**Branch convention (proposed):** `feat/<area>-<name>`, `fix/<name>`, `test/<name>`, `docs/<name>`; short-lived, rebased on `main`, one PR per task, PR title `[#issue] summary` once real issues exist. Suggested names are in the table below; no branch exists yet.

**Planned tasks (7):** PLAN-03, PLAN-05, PLAN-06, PLAN-07, PLAN-16, PLAN-18, PLAN-21. (Planning IDs, not GitHub issue numbers.)

### Member C: UI and connected application features

**Primary ownership**

- The visual system, templates and every user-facing screen: `app/web/templates/*.html`, `app/web/static/css/app.css`, `app/web/static/js/app.js`, `app/web/static/img/`.
- Backend edit endpoints (proposed contract C-3, an extension): new `app/routers/edits.py` and `tests/test_edits.py`; the only shared-file change is adding `edits` to the import and router tuple in `app/main.py`.
- Connecting UI actions to the real endpoints and persisted data; UI validation and `tests/test_ui_pages.py`.

**Secondary responsibilities**

- UI walkthrough as Project Manager and Developer at desktop and phone width (PLAN-04).
- Browser smoke checklist in `docs/TEST_PLAN.md` section 3 and the NFR-7 usability row (PLAN-12, PLAN-19).
- Spot-checks Aryan's pull requests when asked (PLAN-15).

**Can start independently:** PLAN-08, PLAN-10 and PLAN-12 can start as soon as the project is cloned; PLAN-09 can be developed against the proposed C-3 text immediately.

**Dependencies / blocked until:** PLAN-04 needs the repository (PLAN-01); PLAN-09 cannot merge before PLAN-08 (`tests/test_ui_pages.py` reads `/openapi.json`); PLAN-11 after PLAN-10 (same JS file, one UI PR open at a time); PLAN-19 after PLAN-18.

**Required tests:** `tests/test_edits.py` (>= 12 tests; success and failure for each rule); >= 4 new tests in `tests/test_ui_pages.py` (templates extend base, labelled inputs, unique titles, referenced ids exist); existing UI tests stay green; manual 10-line browser smoke checklist executed once.

**Required evidence:** Screenshots (before/after, three widths: 360, 768, 1280 px) in the PR; `pytest` summary line; timed NFR-7 result recorded honestly, pass or fail.

**Reviewer:** Aryan (Member B checks the flow for UI PRs). **Final integration:** Aryan.

**Branch convention (proposed):** `feat/<area>-<name>`, `fix/<name>`, `test/<name>`, `docs/<name>`; short-lived, rebased on `main`, one PR per task, PR title `[#issue] summary` once real issues exist. Suggested names are in the table below; no branch exists yet.

**Planned tasks (7):** PLAN-04, PLAN-08, PLAN-09, PLAN-10, PLAN-11, PLAN-12, PLAN-19. (Planning IDs, not GitHub issue numbers.)

<!-- page:landscape matrix -->

## 4. Task-by-task assignment matrix

All 24 proposed tasks, taken from `docs/GITHUB_ISSUES_PLAN.csv`. **PLAN-xx are planning IDs until real GitHub issues are created.** Every clock time is a proposal. Status shows no progress because none is claimed.

### 4.1 Overview

| ID | Task | Pri | Owner | Depends on | Target (proposed) | Reviewer | Status |
|---|---|---|---|---|---|---|---|
| PLAN-01 | Review the baseline, then commit and push it to GitHub main | P0 | Aryan | none | Sun 18 Oct | Member B (verifies the clone) | Done (initial commit on `main`) |
| PLAN-02 | Confirm the proposed contracts and open decisions; create the GitHub issues | P0 | Aryan | PLAN-01 | Sun 18 Oct 20:00 | Member B and Member C read and acknowledge | Not started (proposed) |
| PLAN-03 | Onboarding and independent baseline verification | P0 | Member B | PLAN-01 | Sun 18 Oct | Aryan | Not started (proposed) |
| PLAN-04 | Onboarding and UI walkthrough | P0 | Member C | PLAN-01 | Sun 18 Oct | Aryan | Not started (proposed) |
| PLAN-05 | Quality gates module (approval and deployment gates), standalone and unit-tested | P0 | Member B | PLAN-03 (setup only) | Mon 19 Oct | Aryan | Not started (proposed) |
| PLAN-06 | Wire the quality gates into the workflow and add rework/retry validation matrix tests | P0 | Member B | PLAN-05 | Tue 20 Oct 12:00 | Aryan | Not started (proposed) |
| PLAN-07 | Orchestrator edge-case and crash-path tests | P1 | Member B | PLAN-03 (setup only) | Tue 20 Oct | Aryan | Not started (proposed) |
| PLAN-08 | Backend CRUD: edit requirements and projects (proposed contract C-3) | P0 | Member C | PLAN-04 (setup only) | Tue 20 Oct 12:00 | Aryan | Not started (proposed) |
| PLAN-09 | UI: edit and approve requirements, edit project details | P1 | Member C | PLAN-08 (must merge first) | Tue 20 Oct 18:00 | Aryan (Member B checks the flow) | Not started (proposed) |
| PLAN-10 | UI: real logo, design tokens, responsive check, getting-started checklist (NFR-7) | P1 | Member C | PLAN-04 (setup only) | Mon 19 Oct | Aryan | Not started (proposed) |
| PLAN-11 | UI stretch: task board and richer review screen (cut first if behind) | P2 | Member C | PLAN-10 | Tue 20 Oct 18:00 | Aryan | Not started (proposed) |
| PLAN-12 | UI regression tests and browser smoke checklist | P1 | Member C | PLAN-04 (setup only) | Tue 20 Oct | Member B | Not started (proposed) |

<!-- page:landscape matrix2 -->

### 4.1 Overview (continued)

| ID | Task | Pri | Owner | Depends on | Target (proposed) | Reviewer | Status |
|---|---|---|---|---|---|---|---|
| PLAN-13 | Startup recovery for interrupted agent jobs (NFR-5) | P1 | Aryan | none | Mon 19 Oct | Member B | Not started (proposed) |
| PLAN-14 | Agent-run hardening: duplicate-job guard and selectable LLM provider | P1 | Aryan | PLAN-13 | Tue 20 Oct 12:00 | Member B | Not started (proposed) |
| PLAN-15 | Daily review and merge queue | P0 | Aryan | none | Daily Sun 18 – Thu 22 Oct | Member B or Member C spot-check | Not started (proposed) |
| PLAN-16 | End-to-end demo scenario as an automated test | P1 | Member B | PLAN-03 (setup only) | Tue 20 Oct 18:00 | Aryan | Not started (proposed) |
| PLAN-17 | Integration #2 and FEATURE FREEZE | P0 | Aryan | PLAN-06, PLAN-08, PLAN-10, PLAN-13, PLAN-14 | Tue 20 Oct 21:00 (FREEZE) | Member B runs the regression | Not started (proposed) |
| PLAN-18 | Independent regression and manual QA on a fresh clone | P0 | Member B | PLAN-17 | Wed 21 Oct 13:00 | Aryan | Not started (proposed) |
| PLAN-19 | UI bug fixes and the timed usability check (NFR-7) | P0 | Member C | PLAN-18 | Wed 21 Oct 18:00 | Aryan | Not started (proposed) |
| PLAN-20 | Backend bug fixes and cross-platform install check | P0 | Aryan | PLAN-18 | Wed 21 Oct 18:00 | Member B | Not started (proposed) |
| PLAN-21 | Traceability and test-evidence finalisation | P0 | Member B | PLAN-19, PLAN-20 | Wed 21 Oct 21:00 | Aryan | Not started (proposed) |
| PLAN-22 | Demo rehearsals (all three) | P0 | Aryan | PLAN-17, PLAN-21 | Thu 22 Oct 10:00 (#1) and 16:00 (#2) | all | Not started (proposed) |
| PLAN-23 | Final documentation, release tag and submission package | P0 | Aryan | PLAN-21, PLAN-22 | Thu 22 Oct 21:00 | Member B | Not started (proposed) |
| PLAN-24 | Deadline day: contingency only | P0 | Aryan | PLAN-23 | Fri 23 Oct | — | Not started (proposed) |

<!-- page:landscape detail -->

### 4.2 Acceptance criteria, tests and evidence

Branch names are suggestions. 'Files' lists the expected files or modules.

#### Aryan

| ID | Acceptance criteria | Tests and evidence required | Files / modules | Branch (proposed) |
|---|---|---|---|---|
| PLAN-01 | `main` exists on GitHub; a fresh clone installs from README and `pytest` shows 248 passed; no .venv, data/, *.db, caches, .env in the commit; the coursework source documents are not in the commit (the Lab Record holds personal data; Lab 6, Phase 2 and Phase 3 are not cleared for redistribution). | `git status` clean; `pytest` on a fresh clone (done by Member B in PLAN-03) | whole repository (the publication file list approved by Aryan) | (direct push to main — one-time exception) |
| PLAN-02 | C-2 and C-3 marked confirmed (or edited) by Sun 18 Oct 20:00 so Member B and Member C can rely on them; issues created; each ▲ row resolved. | none (documents) | docs/TEAM_CONTRACT.md §12, docs/PROJECT_AUDIT.md §6 | docs/contracts-confirmed |
| PLAN-13 | After a simulated crash (rows left in Generating/Testing) a new app instance brings the task to In Review/Failed/Ready without manual action; healthy tasks get no duplicate runs. | tests/test_recovery.py (≥ 4 tests) | app/services/orchestrator.py, app/services/runtime.py, tests/test_recovery.py | feat/startup-recovery |
| PLAN-14 | Concurrent duplicate dispatch produces exactly one run; unknown provider name fails fast with a clear message; docs updated. | tests (≥ 4) | app/services/orchestrator.py, app/services/runtime.py, app/config.py, tests/test_orchestrator_guard.py | feat/job-guard-provider |
| PLAN-15 | Every merged PR shows a green pytest line; no PR waits more than 6 h. | pytest on main after each merge | shared files | (n/a) |
| PLAN-17 | main green; contract matches the code; frozen commit identified for the regression run. | pytest + coverage on main | TEAM_CONTRACT.md, README.md, shared files | (on main) |
| PLAN-20 | No open P0/P1 backend defects; README table contains only verified results. | pytest | backend files, README.md | fix/backend-regression |
| PLAN-22 | Each member explains their modules, the state chart and the deviations without notes; demo runs end to end twice. | demo run notes | docs/DEMO_SCRIPT.md | (n/a) |
| PLAN-23 | Fresh clone → install → demo works from the README alone; tag created; submission files prepared. | final pytest run | docs/*, README.md | docs/release |
| PLAN-24 | Submission made. | — | — | (hotfix/*) |

<!-- page:landscape detail_b -->

### 4.2 Acceptance criteria, tests and evidence (continued)

#### Member B

| ID | Acceptance criteria | Tests and evidence required | Files / modules | Branch (proposed) |
|---|---|---|---|---|
| PLAN-03 | Comment with OS, Python version, the real pytest summary line; conformance table complete for all 10 transitions and the 4 alternative flows; mismatches listed. | pytest output pasted; table in TEST_PLAN §5 | docs/TEST_PLAN.md §5 (table only) | test/conformance-table |
| PLAN-05 | Each gate has passing and failing cases for every reason (≥ 12 tests); module imports only `sqlalchemy`, `app.models`, `app.errors` (no routers, services or workflow); full suite still 248+ green. | pytest tests/test_quality_gates.py; summary line in the PR | app/quality_gates.py (new), tests/test_quality_gates.py (new) | feat/quality-gates |
| PLAN-06 | A task whose newest run is not tested cannot be deployed (409 `quality_gate_failed`); demonstrated at workflow/unit level, because through the API the gates are defence in depth (see contract C-2). The 244 API-driven existing tests stay unchanged and green; the 4 fixture-seeded tests in tests/test_workflow.py (approve, two authorise_deployment cases, test_available_actions_follow_state_and_role) get fixtures that seed a completed run and a passing test result, with no assertion weakened (found by a local probe that emulated the gates). Matrix tests added (≥ 12 new cases). | pytest (full) summary line; new test names listed in the PR | app/workflow.py, tests/test_workflow.py (additions), tests/test_quality_gates.py, docs/TEAM_CONTRACT.md (one table row) | feat/workflow-gates |
| PLAN-07 | ≥ 8 tests; `pytest --cov=app.services.orchestrator` ≥ 92%; defects found are filed. | coverage line pasted in the PR | tests/test_orchestrator_edges.py (new) | test/orchestrator-edges |
| PLAN-16 | All scenarios pass on `main`; each asserts final status, audit actions and notifications. | pytest summary | tests/test_e2e_demo.py (new) | test/e2e-demo |
| PLAN-18 | Test report with real numbers and OS list; every defect filed with reproduction steps and severity. | pytest output; checklist ticked | docs/TEST_PLAN.md (results), issues | test/regression-report |
| PLAN-21 | No row claims a status the code or tests do not support; Aryan signs off. | final pytest/coverage output | docs/REQUIREMENTS_TRACEABILITY.md, docs/TEST_PLAN.md | docs/traceability-final |

<!-- page:landscape detail_c -->

### 4.2 Acceptance criteria, tests and evidence (continued)

#### Member C

| ID | Acceptance criteria | Tests and evidence required | Files / modules | Branch (proposed) |
|---|---|---|---|---|
| PLAN-04 | Comment with OS, Python version, real pytest summary; ≥ 5 defect reports with screenshots. | pytest output pasted; screenshots | none (issues only) | (no branch) |
| PLAN-08 | Approved requirement content is locked (422 `requirement_locked`); status moves Draft → Approved only; Developer gets 403 and the denial is audited; unknown ids 404; end date before start date 422; contract rows added to §5; ≥ 12 tests. | pytest tests/test_edits.py; full-suite summary line | app/routers/edits.py (new), tests/test_edits.py (new), app/main.py (import + router tuple) | feat/edit-endpoints |
| PLAN-09 | Edit and Approve work end to end in the browser; no button without a handler; `tests/test_ui_pages.py` still passes (it checks every endpoint the JS calls exists). | screenshots of before/after; pytest summary | app/web/static/js/app.js, app/web/templates/project.html | feat/ui-edit-controls |
| PLAN-10 | Logo shown on every page (or placeholder still clearly labelled); screenshots at three widths in the PR; checklist appears and disappears from real data. | screenshots; tests/test_ui_pages.py updated for the logo | app/web/static/img/, app/web/templates/base.html, dashboard.html, app/web/static/js/app.js (dashboard section only), app/web/static/css/app.css | feat/ui-branding-onboarding |
| PLAN-11 | Board counts equal the task table counts; existing UI tests pass. | screenshots; pytest | app/web/static/js/app.js (task and project sections), app/web/static/css/app.css | feat/ui-board-review |
| PLAN-12 | ≥ 4 new tests; checklist executed once with the result recorded. | pytest summary | tests/test_ui_pages.py, docs/TEST_PLAN.md §3 | test/ui-structure |
| PLAN-19 | No open P0/P1 UI defects; NFR-7 row filled with the measured time (pass/fail is stated honestly). | re-run of the failing checks; pytest | app/web/*, docs/TEST_PLAN.md §6 (NFR-7 row) | fix/ui-regression |

<!-- page:portrait schedule -->

## 5. Milestones and daily schedule, 18-23 October 2026

Planned dates and times only. **Nothing here is reported as completed**, and the clock times are Aryan's proposals that the team has not yet agreed. Today (18 Oct) is the onboarding and interface-agreement day.

| Date | Milestone | Owner | Expected outcome |
|---|---|---|---|
| Sun 18 Oct | Onboarding and interface agreement | Aryan (PLAN-01, PLAN-02); Member B (PLAN-03); Member C (PLAN-04) | Repository published (initial commit on `main`); everyone has `pytest` green on their own machine; C-2 and C-3 confirmed or edited by 20:00 (slips if the push slips); onboarding comments with OS, Python version and real pytest summary |
| Mon 19 Oct | Parallel implementation | All | PLAN-05 quality-gates module and PLAN-10 UI branding/checklist delivered as PRs; PLAN-13 startup recovery delivered; PLAN-07, PLAN-08, PLAN-12, PLAN-16 in progress |
| Tue 20 Oct | Parallel implementation, integration, **feature freeze 21:00** | All; Aryan integrates (PLAN-17 from 18:00) | PLAN-06 and PLAN-08 PRs by noon, PLAN-14 by noon, PLAN-09/16/(11) by 18:00; `main` green; contract matches the code; frozen commit identified |
| Wed 21 Oct | Regression testing, bug fixes, evidence | Member B (PLAN-18 08:30-13:00); Member C (PLAN-19); Aryan (PLAN-20); Member B (PLAN-21) | Independent regression report by 13:00; no open P0/P1 defects by 18:00; traceability finalised by 21:00. No rehearsal on Wednesday: PLAN-21 runs 18:00-21:00 |
| Thu 22 Oct | Demo rehearsals #1 (10:00) and #2 (16:00), release-candidate verification | Aryan (PLAN-23); all (PLAN-22) | Final docs, release-candidate check by 21:00 on a fresh clone; tag `v1.0` only with Aryan's explicit approval |
| Fri 23 Oct | Final submission (contingency only) | Aryan (PLAN-24) | Submission made; hotfixes only. Contents/format to be confirmed with the instructor |

### Daily plan by person (from the work division; proposed)

| Day | Aryan | Member B | Member C | Gate |
|---|---|---|---|---|
| Sat 17 Oct (past) | Baseline built and verified locally; nothing pushed | - | - | - |
| Sun 18 | PLAN-01 push (done); PLAN-02 contracts by 20:00 | PLAN-03; start PLAN-05 | PLAN-04; start PLAN-08/10/12 | Everyone has `pytest` green |
| Mon 19 | PLAN-13; reviews | PLAN-05 PR; PLAN-07 | PLAN-10 PR; PLAN-08 | - |
| Tue 20 | PLAN-14 (noon); reviews; PLAN-17 from 18:00 | PLAN-06 PR (noon); PLAN-07 PR; PLAN-16 (18:00) | PLAN-08 PR (noon); PLAN-09 (18:00); PLAN-12; (PLAN-11 stretch) | **Feature freeze 21:00** |
| Wed 21 | PLAN-20 (10:00-18:00) | PLAN-18 (08:30-13:00); PLAN-21 (18:00-21:00) | PLAN-19 (10:00-18:00) | Regression report 13:00; no open P0/P1 by 18:00; evidence final 21:00 |
| Thu 22 | PLAN-23; tag `v1.0` after approval | Rehearsals #1 10:00 and #2 16:00 | Rehearsals #1 10:00 and #2 16:00 | Release candidate 21:00 |
| Fri 23 | PLAN-24 contingency / submission | - | - | **Deadline** |

## 6. Shared development rules

- **Contracts first.** Agree API and module contracts before parallel implementation: the REST API and workflow are implemented and frozen (`docs/TEAM_CONTRACT.md` sections 4-5); C-2 and C-3 are only proposals until Aryan confirms them. If a confirmed contract changes, the owner adapts in the same PR.
- **One writer per shared file.** Avoid simultaneous edits to shared files (`models.py`, `schemas.py`, `db.py`, `main.py`, `config.py`, `security.py`, `errors.py`, `workflow.py`, the contract, `app.js`) unless coordinated in the group first. Only one UI PR may be open at a time (single JS file). Agreed exceptions: Member C edits `main.py` for PLAN-08 (Aryan does not edit it Mon 19 - Tue 20 Oct); Member B may change at most 10 lines of `orchestrator.py` with Aryan's review.
- **Small branches, reviewed PRs.** After the repository is published: short-lived feature branches from `main`, one PR per task, rebased on `main`, squash-merged by Aryan. The very first push goes straight to `main` as a one-time exception, because an empty `main` cannot be a PR target.
- **Test before review.** Run the relevant tests, then the full `pytest`, before requesting review; every PR states the task ID, ticked acceptance criteria, the real `pytest` summary line, and screenshots for UI changes. New behaviour needs a success and a failure test. Never weaken a test to make it pass.
- **No failing or unverified merges.** `main` must always install, start and pass `pytest`.
- **Evidence travels with the code.** Update the traceability matrix, test plan and contract rows in the same PR as the implementation.
- **Never commit** secrets, `.env` files, local databases (`data/`, `*.db`), virtual environments, caches, or unauthorised personal data.
- **Honesty.** Do not claim authentication, AI capabilities, test coverage or features that are not genuinely implemented. The LLM, Git host and CI/CD are mocks, test results are simulated, and there is no real login. Be able to explain every line you submit, even if an AI assistant wrote it.

## 7. Communication and accountability

**Daily update** (one message per person; the plan proposes sending it by 21:00, **a time the team has not yet agreed**):

| Field | Content |
|---|---|
| Completed | Task IDs finished or advanced, with PR links |
| Next | What you will do next and its planned time |
| Blocked | Task ID and the exact blocker, or 'none' |
| Tests / evidence | The real `pytest` summary line; screenshots or coverage where required |
| Help needed | Specific request and who you need it from |

| Situation | Escalation (proposed) |
|---|---|
| Blocker | If blocked for more than 3 hours, post the task ID and blocker in the group chat; Aryan re-plans or pairs the same day |
| Interface change | Announce in the group before changing a shared file or contract; keep the PR small, update the contract row in the same PR; others rebase the same day |
| Review request | Open the PR with the checklist complete and tag the reviewer; the plan targets review within 6 hours |
| Deadline risk | Say so in the daily update as soon as a task may miss its target; Aryan applies the slippage rule (drop P2 first, then simplify PLAN-14; never drop PLAN-18, 21, 22, 23) |

No meeting times are fixed in this document. Any meeting or rehearsal time must be agreed by the team first.

## 8. Definition of done and final handover

**A task is done when:** its acceptance criteria are met and ticked in the PR; success and failure tests exist for new behaviour; the full `pytest` is green with the real summary line pasted; documentation, contract and traceability changes are in the same PR; the named reviewer approved; Aryan merged it; and the required evidence (screenshots, coverage, notes) is attached.

**A feature is integrated when:** it is merged to `main`; `pytest` on `main` is green after the merge; the contract matches the code; the traceability row states only what the tests support; and the feature appears in the demo script where relevant.

**The project is ready for demonstration and submission when:**

- The frozen `main` passes a fresh-clone install and the full `pytest` (PLAN-18), on Windows and on any other OS available; the README 'Verified on' table contains only those verified results.
- `docs/REQUIREMENTS_TRACEABILITY.md` and `docs/TEST_PLAN.md` are final (PLAN-21) and list unimplemented items honestly; `docs/KNOWN_LIMITATIONS.md` is final.
- Two rehearsals have been run from a fresh clone on the demo laptop, and each member can explain their modules, the state chart and the deviations without notes (PLAN-22).
- A release-candidate check on Thu 22 Oct, then tag `v1.0` only with Aryan's explicit approval (PLAN-23).
- The submission package contains whatever the instructor requires (**to be confirmed**).

### Installation instructions (from the README; Windows verified, macOS/Linux not yet)

```
git clone https://github.com/AryanRajguru22/DevNexus.git
cd DevNexus
py -3.11 -m venv .venv                      (macOS/Linux: python3.11 -m venv .venv)
.\.venv\Scripts\Activate.ps1                (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
pytest                                        # expect: 248 passed
python -m app                                 # http://127.0.0.1:8000
```

### Verified test results (18 Oct 2026)

| OS | Python | Result |
|---|---|---|
| Windows 11 | 3.11.9 | 248 passed in about 26 s; coverage of `app/` 98% (1560 statements, 39 missed); `orchestrator.py` 81% |
| macOS | - | not yet verified |
| Linux | - | not yet verified |

**Known limitations to state at handover:** mock LLM, Git and CI/CD; simulated static test results and coverage; no real authentication or TLS; SQLite instead of PostgreSQL; no gRPC or message queue; no container-isolated agents; in-app notifications only (no e-mail); no durable job queue across restarts until PLAN-13 is merged. Full list: `docs/KNOWN_LIMITATIONS.md`.

<!-- page:landscape decisions -->

## 9. Open decisions and risks

Status is based on evidence, not on assumption. **Confirmed** = source document or verified code/tests; **Awaiting approval** = nobody with authority has confirmed it; **Pending verification** = not yet checked. Nothing below is silently assumed to be approved.

### 9.1 Decision register

| # | Topic | What the evidence shows | Status | Who decides |
|---|---|---|---|---|
| D1 | Retry limit | Source: the limit is configurable in the pipeline and a task over the limit is 'reported as a risk' (Phase 3 section 9, UC-05 3a, A-2: no fixed value). Verified in code and tests: refusal with `409 retry_limit_exceeded`, audit row and risk notification. NOT in any source: default of 2, range 0-10, and the counting rule 'runs <= limit' (initial run is not a retry). | Configurable: **Confirmed**. Default 2, 0-10 range, counting rule, refuse-and-stay behaviour: **Awaiting approval** | Aryan (instructor if graded) |
| D2 | Risk calculation | Source (Phase 2 section 11): score = probability x impact, each 1-5; High >= 15, Medium 9-14, Low < 9; matches `analytics.py`. FR-11 names three categories: delayed tasks, repeated agent failures, schedule slippage. NOT in any source: impacts 3/4/4, the probability rules, the 20-point slippage gap, project level = highest category, auto-report on reaching High (our interpretation A19). | Formula and boundaries: **Confirmed**. Categories: **Confirmed**. Impacts, probability rules, gap, aggregation: **Awaiting approval** | Aryan (instructor if graded) |
| D3 | Notifications | FR-13 and UC-03/06/07 support notifications on failure, deployment completion and risk threshold; Phase 3 lists `GET /notifications`. The Phase 3 E-R has no notification entity: the NOTIFICATION table (E-3) is our extension. In-app only. | Notification kinds and endpoint: **Confirmed**. NOTIFICATION table: **Awaiting approval** | Aryan |
| D4 | Simulated demo-user switcher | No login requirement exists (Phase 3 O-3; login assumed at the API Gateway, A-5) but use-case pre-conditions assume a logged-in user. The `X-User-Id` header + UI switcher (deviation D-6) gives role-based authorisation but **no authentication**: anyone who can reach the server can impersonate anyone. NFR-3 is only partially met. | **Awaiting approval** (instructor). Must be presented as a demo switcher, never as login | Aryan / instructor |
| D5 | Deployment authorisation | FR-9: 'explicit Developer/PM authorisation'; UC-07: 'the user holds a role allowed to authorise deployment', refusal and audit for other roles. Code allows Developer or Project Manager (reading '/' as 'or'). Primary actor in UC-07 is the Developer. | **Confirmed** by FR-9 and UC-07 (reading noted) | - |
| D6 | C-2 quality gates | Not a source requirement (basis FR-7, FR-9, UC-07). Through the API the gates are defence in depth: `tests_passed` already fires only when `failed == 0`. A local probe emulating the gates broke 4 fixture-built tests in `tests/test_workflow.py` and left 244 API-driven tests green. | **Awaiting approval**; fixture update in PLAN-06 required | Aryan |
| D7 | C-3 edit endpoints and UI | Not a source requirement: no FR or Phase 3 section 14.5 endpoint covers editing. The requirement values Draft/Approved and project values Planning/Active/Completed are not defined in any source. Currently P0/P1 by team choice. | **Awaiting approval**, including the priority | Aryan |
| D8 | Submission contents (23 Oct) | No source document defines what must be submitted on 23 Oct or in what format. | **Pending verification** with the instructor | Aryan |
| D9 | Clock times | 20:00 contract deadline, 21:00 daily update and freeze, Thu 22 rehearsals at 10:00 and 16:00, noon/18:00 targets exist only in the plan. | **Awaiting approval** (team agreement) | All three |
| D10 | Publication of the baseline | The repository is public. The coursework source documents are not published: the Lab Record (contains a team member's name and registration number) is excluded and ignored locally; Lab 6, Phase 2 and Phase 3 are excluded because permission to redistribute is unconfirmed (`docs/source-requirements/` is git-ignored; teammates receive those files privately). Teammates appear as role labels (Member B, Member C) in documents and demo data until they consent. Commits use the GitHub noreply e-mail address. | **Resolved for the first commit** (Aryan); revisit if the instructor or teammates agree otherwise | Aryan (teammates consulted) |
| D11 | Real DevNexus logo | Not in the repository; only a labelled placeholder SVG exists. | **Awaiting** the file from Aryan (PLAN-10) | Aryan |
| D12 | macOS / Linux support | Pure Python and plausible, but not run. | **Pending verification** (PLAN-18 / PLAN-20) | Member B |
| D13 | PDF generator script | The Markdown-to-PDF renderer is a dev-only script that needs `pymupdf` and `markdown` (not in `requirements.txt`). Either publish it under `scripts/` as a dev tool, or state that the PDF was generated once and keep the script out of the repository. | **Awaiting approval**; before sending the PDF, re-render it with the approved status and version | Aryan |

<!-- page:landscape risks -->

### 9.2 Risks

| Risk | Why it matters | Proposed mitigation |
|---|---|---|
| Publication slips (resolved: baseline pushed) | PLAN-03, PLAN-04 and the 20:00 contract deadline depended on PLAN-01 | None needed now; teammates clone the repository |
| Single reviewer | Aryan reviews every PR while also building PLAN-13/14/17 | 6-hour review target; Member C may spot-check; shed P2 first |
| Member C's load | PLAN-04, 08, 09, 10, 12 (and 11) between Sun 18 and Tue 20 | Order: 08 and 10 first; cut PLAN-11; PLAN-09 can only merge after PLAN-08 |
| Wed 21 overlap (resolved) | Rehearsal #1 had been proposed for Wed 20:00 while PLAN-21 (18:00-21:00, needs PLAN-19 and PLAN-20 merged) runs | Both rehearsals moved to Thu 22 Oct (10:00 and 16:00); Wed evening is reserved for PLAN-21. Thursday is then busy (two rehearsals, PLAN-23, release candidate 21:00): keep rehearsal fixes small |
| C-2 changes existing tests | Wiring the gates breaks 4 fixture-seeded tests | Update only their fixtures; no assertion weakened; Aryan reviews |
| Late freeze | Freeze is Tue 20 21:00 and PLAN-17 starts only at 18:00 | Merge early; PLAN-06 and PLAN-08 by noon |
| Overclaiming | Mock AI, simulated tests and no authentication are easy to overstate in a viva | Honesty rule (section 6); `docs/KNOWN_LIMITATIONS.md` is read by all three before rehearsals |

*DevNexus Team Work Allocation, version 1.0, prepared 18 October 2026. Issued by Aryan for team review; clock times and C-2/C-3 are proposals until the team agrees them.*
