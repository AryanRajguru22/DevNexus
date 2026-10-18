**DevNexus kickoff: deadline Fri 23 Oct 2026. Read this, then start your first task.**

Hi team,

> **Status:** the repository is live at https://github.com/AryanRajguru22/DevNexus (initial commit on `main`, the one-time exception to 'no direct pushes'; every change after that goes through a PR). Task IDs below (`PLAN-xx`) are the planning IDs in `docs/GITHUB_ISSUES_PLAN.md`; GitHub issues carry the same IDs in their titles once they exist. Clock times are *proposed*. In this repository copy the two teammates appear as role labels (Member B, Member C); in the message you receive, your name is next to your role.

**1. What we're building.** **DevNexus** is our app; **ASDPIP** (Autonomous Software Development & Project Intelligence Platform) is the academic project name. AI agents (code generation → testing → deployment) work on tasks under mandatory human review, and a dashboard shows progress, estimation and risk. The course documents (Lab Record, Phase 2, Lab 6, Phase 3) are the authority and are shared privately, not in the repository; the Phase 3 design wins where it supersedes the earlier labs. We don't invent requirements.

**2. Where we are.** A working baseline is on `main`: all of FR-1…FR-14 with **mock** AI/Git/CI adapters (clearly labelled), a web UI, and **248 passing tests** (verified on Windows 11 / Python 3.11.9, in the project venv and in a clean venv; 98% coverage of `app/`). Setup and tests: `py -3.11 -m venv .venv` → activate → `pip install -r requirements.txt` → `pytest` → `python -m app` (http://127.0.0.1:8000). It is **not yet verified on macOS/Linux**. Tell me your OS result. FR-5, FR-8 and FR-9 are only *partially* implemented (mock LLM, static simulated tests, mock CI/CD) and there is **no real authentication** (a demo user switcher, see `docs/KNOWN_LIMITATIONS.md`): we must not claim otherwise.

**3. Deadline plan (6 days).** Sun 18: onboarding + contracts confirmed 20:00 (proposed times: tell me if any clock time in this message does not work for you) · Mon 19–Tue 20: parallel work · **Tue 20 21:00 FEATURE FREEZE** · Wed 21: regression, bug fixes, evidence (no rehearsal that evening; PLAN-21 runs 18:00-21:00) · Thu 22: rehearsals #1 (10:00) and #2 (16:00), release candidate · Fri 23: deadline (contingency only). Full schedule: `docs/TEAM_WORK_DIVISION.md`.

**4. Who does what (nobody waits for anybody)**
- **Aryan — core and integration:** foundation/architecture, AI provider + agent-run handling (PLAN-13 startup recovery, PLAN-14 duplicate-job guard and provider selection), analytics/risk, merge queue, freeze, release, demo.
- **Member C — UI and connected features:** the UI (`app/web/`) **and backend CRUD**: PLAN-08 `PATCH` endpoints to edit requirements/projects in a new file `app/routers/edits.py`; PLAN-09 UI for them; PLAN-10 logo + design tokens + responsive + getting-started checklist; PLAN-12 UI tests; PLAN-11 task board (stretch, cut first); PLAN-19 UI fixes + timed usability test.
- **Member B — workflow and independent QA:** you own `app/workflow.py` and a new `app/quality_gates.py`: PLAN-05 approval/deployment quality gates (standalone, unit-tested), PLAN-06 wire them into the workflow + rework/retry validation matrix tests, PLAN-07 orchestrator edge-case tests, PLAN-16 end-to-end demo test, PLAN-18 independent regression on a fresh clone, PLAN-21 final test evidence. Each unit is 0.25–1 day, ordinary Python + pytest; Claude Code is optional.

**5. Shared interfaces (minimal).** Already implemented and frozen: the REST API/error format and the 8-state workflow (`docs/TEAM_CONTRACT.md` §4–5). **Proposed** (not yet in code, in contract §12): **C-2** quality gates (Member B; defence in depth, wiring it will need 4 test fixtures in `tests/test_workflow.py` updated) and **C-3** edit endpoints (Member C; an *extension*: no requirement in the source documents asks for editing). I confirm or change both by **Sun 18 Oct 20:00**; you may start earlier against the proposed text.

**6. Your first task, starting now**
- **Member B — PLAN-03:** set up and run `pytest`; walk `docs/DEMO_SCRIPT.md`; compare `app/workflow.py` with the state chart (Phase 3 Fig 3.7, §9, UC-03/05/06/07) and fill the table in `docs/TEST_PLAN.md` §5. You can start the table from the PDF immediately. Then start PLAN-05. Post OS, Python version, real pytest summary, mismatches.
- **Member C — PLAN-04:** same setup; use every page as PM and Developer at desktop and phone width; file ≥ 5 concrete defects with screenshots. Then start PLAN-08 (backend) and PLAN-10 (UI).
- **Aryan:** PLAN-01 is done (the push); confirm contracts (PLAN-02), PLAN-13.

**7. Can start immediately vs depends.** Immediately: PLAN-05, PLAN-07, PLAN-16 (Member B); PLAN-08, PLAN-10, PLAN-12 (Member C); PLAN-13 (Aryan). Depends: PLAN-06 ← PLAN-05; PLAN-09 can be built now but only merges after PLAN-08 (the UI test reads `/openapi.json`); PLAN-11 ← PLAN-10; PLAN-14 ← PLAN-13; everything on the cloned repo (PLAN-01, done).

**8. Deliverables and acceptance.** Each task in `docs/GITHUB_ISSUES_PLAN.md` lists files, acceptance criteria and tests. Every PR: task ID, acceptance criteria ticked, the real `pytest` summary line, screenshots for UI. New behaviour needs a success **and** a failure test. Don't weaken a test to pass it.

**9. Git rules.** `main` always installs and passes `pytest`; no direct pushes (the first push was the one exception). Short-lived branches from `main` (suggested names in the plan, e.g. `feat/quality-gates`, `feat/edit-endpoints`, `test/orchestrator-edges`). One PR per task, rebased on `main`, squash-merged by me. Reviews: Member B → Aryan; Member C → Aryan (Member B checks the flow); Aryan → Member B.

**10. Shared files — one writer at a time.** Aryan owns `models.py`, `schemas.py`, `db.py`, `main.py`, `config.py`, `security.py`, `errors.py`, agents/adapters/services and the existing routers. Member B owns `workflow.py`, `quality_gates.py`, `validation.py`, tests. Member C owns `app/web/**` (one UI PR at a time: it is a single JS file) and `routers/edits.py`. Two agreed exceptions: Member C adds `edits` to the import and the router tuple in `main.py` (I won't edit it Mon–Tue), and Member B may fix ≤ 10 lines in `orchestrator.py` with my review. Anything else: ask in the group first.

**11. Progress and blockers.** One message each day (proposed: by 21:00): done / next / blocked / tests-evidence / help needed. Blocked > 3 hours: post the task ID and the blocker; I re-plan or pair the same day. If a task slips, we drop P2 first.

**12. Honesty rule.** Partial is fine if documented. Mock parts are labelled; we never claim a requirement we can't demonstrate (`docs/KNOWN_LIMITATIONS.md`, traceability matrix). Be able to explain every line you submit, even if an AI wrote it: the viva will ask.

Aryan
