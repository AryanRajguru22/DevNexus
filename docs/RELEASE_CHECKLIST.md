# Release Candidate Report, Checklist and Viva Notes (2026-10-28)

Branch `release/rc1` (local integration branch; see "Git / GitHub state"). Everything below was measured on this branch, not copied from earlier reports.

## 1. What changed since `main` (`f5364a0`)

| Change | Source | Evidence |
|---|---|---|
| Edit endpoints for requirements/projects (`PATCH`, PM only, approved requirements locked) | PR #11 (PLAN-08) | `tests/test_edits.py` (34) |
| Edit / approve UI | PR #12 (PLAN-09) | `tests/test_ui_pages.py` |
| Design tokens, responsive fixes, getting-started checklist; claims to fix UI issues #1, #2, #4-#9 | PR #13 (PLAN-10) | checked: no horizontal overflow and no console errors on 7 pages at 1280/768/360 px (CDP run); #4 wording confirmed in the diff |
| Task board, diff line numbers, reject templates (P2, text-node DOM only, no `innerHTML`) | PR #14 (PLAN-11) | kept: small, tested, and PR #15 sits on top of it |
| UI structure tests + smoke checklist | PR #15 (PLAN-12) | `tests/test_ui_pages.py` (52) |
| Orchestrator edge/crash tests | PR #17 (PLAN-07) | `tests/test_orchestrator_edges.py` (10) |
| **Fix #3** review diff showed other tasks' merged files as deleted | this branch | adapter + HTTP regression tests; both fail on the old code |
| **Fix #16** failed CI/CD runner that *raises* left merged code in `main` | this branch | PLAN-07's strict xfail is now a normal passing test |
| `reject` / `tests_failed` guard documented + tested (code_generation must be active) | this branch | contract §4, `test_inactive_agent_blocks_the_transition` |
| Optional **Ollama** provider (`DEVNEXUS_LLM_PROVIDER=ollama`) | this branch | `tests/test_ollama_provider.py` (28) |
| `scripts/e2e_check.py`: 34 live HTTP checks | this branch | run against a real server |

### Root causes
* **#3** - A feature branch is an *overlay* of the files its own task committed, and `merge_to_main` only adds/overwrites. `diff()` compared *all* of main with the branch, so every file merged by another task looked deleted. It now compares only the paths the branch holds against main's version of them. Nothing is hidden: a branch cannot delete a file by construction.
* **#16** - `DeploymentAgent.deploy` merged first and rolled back only when the runner *returned* a failure. A raising runner skipped the rollback while the orchestrator still recorded the failure. The agent now rolls back and re-raises. Scope: this restores the *mock workspace directory*; there is no real deployment.

## 2. Git / GitHub state (verify, do not assume)
* `main` and `origin/main` = `f5364a0`. No PR has been merged on GitHub by this work; `gh` is not installed and nothing was pushed.
* Open PRs on GitHub (as read from the API on 2026-10-28): #11 → #12 → #13 → #14 → #15 (stacked, each based on the previous branch) and #17 (based on `main`). All showed `mergeable: clean` for #11-#14; #15/#17 not re-queried (API rate limit).
* `release/rc1` = `main` + fast-forward of the whole #11-#15 stack + merge of #17 + fix commits. To publish: push `release/rc1`, open one PR to `main`, and close #11-#15/#17 as superseded **or** merge them in stack order first and then rebase the fix commits. This needs the owner's decision and was not done.
* Issue states on GitHub are unchanged. Fixed by this branch: #3, #16 and (per PR #13's own description and our checks) #1, #2, #4-#9.
* Not available to this work: Member B's uncommitted PLAN-03 conformance table; Member B's macOS evidence (reported only).

## 3. Decisions (and their impact)
1. **Workflow contract**: no change to `TRANSITIONS`; the PDF (§9 table, UC-03/05/06/07, A-2) agrees with it. The only inconsistency found was documentation (extra guard on `reject`/`tests_failed`), fixed in `TEAM_CONTRACT.md` §4. Table: `docs/TEST_PLAN.md` §5.
2. **Quality gates (C-2, PLAN-05/06)**: *not implemented*. No source requires them; unreachable through the API; would break fixture-seeded workflow tests for no user-visible gain. Recorded in KNOWN_LIMITATIONS 9a.
3. **PLAN-11 board** kept (small, text-node DOM, tested, PLAN-12 depends on it).
4. **Retry limit exhausted**: refuse + flag as risk + keep state (assumption A-2), not a ninth state.
5. **Ollama**: optional; mock stays the default and the demo does not depend on it.

## 4. Database (derived from the source)
SQLite, SQLAlchemy 2.x, **11 model classes / 11 tables**: `User`(user), `Agent`(agent), `Project`(project), `Requirement`(requirement), `Task`(task), `AgentRun`(agent_run), `TestResult`(test_result), `Deployment`(deployment), `RiskReport`(risk_report), `Notification`(notification), `AuditLog`(audit_log). Details and responsibilities: `docs/ARCHITECTURE.md` §4a. No migrations; reset = stop server, delete `data/` (demo data only).

## 5. Release checklist
- [x] Fresh venv + `pip install -r requirements.txt` + `pytest`: 387 passed, 99% (2026-10-28)
- [x] `python -m app` starts; `/api/health` ok; all 7 pages render
- [x] `python scripts/e2e_check.py` 34/34
- [x] Kill the server mid-generation, restart: run closed as failed, task recovered, data persisted
- [x] 1280 / 768 / 360 px: no horizontal overflow, no console errors (7 pages)
- [x] Mock provider path verified separately from Ollama (all 387 tests and `e2e_check.py` use the mock)
- [x] Ollama installed (E:\Ollama, models in E:\ollama-models), `qwen2.5-coder:1.5b` pulled, real inference + app smoke + provider-down path verified (details: KNOWN_LIMITATIONS 8a)
- [ ] First-time-user usability timing (NFR-7) - not measured
- [ ] Linux / macOS re-run on the release candidate - not done
- [ ] Push `release/rc1`, open/merge the PR, tag `v1.0` - **owner action**
- [ ] Rehearse `docs/DEMO_SCRIPT.md` twice on the demo laptop

## 6. Troubleshooting
| Symptom | Cause / fix |
|---|---|
| `Unknown LLM provider '...'` at start | `DEVNEXUS_LLM_PROVIDER` must be `mock` or `ollama` |
| Task goes to **Failed** with "Cannot reach Ollama" | start Ollama (`ollama serve` or the tray app) or `set DEVNEXUS_LLM_PROVIDER=mock` and restart |
| Failed with "model ... is not installed" | `ollama pull <model>` (default `qwen2.5-coder:1.5b`) |
| Failed with "did not answer within N s" | first request loads the model; raise `DEVNEXUS_OLLAMA_TIMEOUT` or warm it with `ollama run <model> hi` |
| Page shows no data / "Invalid Date" | hard-refresh; check the server console; confirm `/api/health` |
| `sqlite3.OperationalError: no such column` after pulling new code | schema changed; stop the server and delete `data/` (demo data only) |
| Port 8000 busy | `set DEVNEXUS_PORT=8001` |
| Everything odd | stop the server, delete `data/`, restart (schema + demo users are re-created) |

## 7. Viva questions (short answers)
* **Modules?** `workflow.py` (only code that changes `task.status`), `agents/` (codegen, testing, deployment), `adapters/` (LLM, Git, CI/CD interfaces + local implementations), `services/` (orchestrator for jobs/recovery, analytics for dashboard/COCOMO/risk), `routers/` (REST), `web/` (Jinja2 shells + vanilla JS).
* **How many models/tables?** 11 (list in §4). Models = persisted SQLAlchemy tables; schemas = Pydantic API documents.
* **Agents vs adapters?** An agent decides and orchestrates one step (generate / test / deploy); an adapter is the interface to something external (LLM, Git host, CI runner) - mocks today, replaceable.
* **Workflow?** 8 states, 10 transitions in one table (`TEST_PLAN` §5); anything else is 409; humans gate approve/reject/deploy; rework bounded by the pipeline's retry limit.
* **Why SQLite/SQLAlchemy?** zero setup/cost for a laptop demo (D-1); ORM keeps PostgreSQL possible; WAL + 30 s timeout; limits in KNOWN_LIMITATIONS 7.
* **COCOMO / risk?** Basic COCOMO organic E = 2.4·KLOC^1.05, D = 2.5·E^0.38, ₹60,000 per person-month (Phase 2); risk = probability × impact per category with bands (our reading of Phase 2, assumption A19).
* **Start-up recovery?** At start: `running` runs are closed as failed ("Interrupted…"), Assigned/Generating/untested-Testing tasks are re-dispatched, retry limit respected (interrupted run counts as an attempt), tasks waiting for a human are untouched, repeat restarts change nothing.
* **Atomic task claiming?** A compare-and-set `UPDATE task SET status=status WHERE id=? AND status=?` takes the row's write lock; the loser gets 409 and nothing is created. It is a database mechanism, not a Python lock (single process assumed).
* **Coverage vs correctness?** 99% line coverage shows the lines ran, not that they are right; "coverage" in the app is simulated static checks, not line coverage.
* **Human approval / mocks?** Merge needs an authorised human; AI, Git host and CI/CD are mocks; no real authentication (demo user switcher).
* **Team?** Aryan: backend, workflow, recovery, integration; Member B: QA, orchestrator tests, conformance; Member C: edit endpoints and UI. Individual contributions are in `git log`.
