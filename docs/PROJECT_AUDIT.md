# DevNexus / ASDPIP — Project Audit

Product name: **DevNexus**. Academic project: **ASDPIP — Autonomous Software Development & Project Intelligence Platform** (CSE3132 Software Engineering Lab).
Audit date: 2026-10-17. Auditor: Claude Code (for Aryan). Source documents were **not modified**.

## 1. Files inspected

| Course document (not included in the repository) | Size | How it was read | Not verified |
|---|---|---|---|
| Phase 3 design document (PDF) | 28 pages, 3.5 MB | All text extracted and read in full. Rendered and viewed: Fig 3.1 use case (p3), Fig 3.2 class diagram (p7), Fig 3.6 E-R (p12), Fig 3.7 state chart (p14). | Figs 3.3–3.5, 3.8–3.11 (sequence, DFD, activity, object, component, deployment) were read through their captions and the tables beside them, not visually. |
| Lab Record (Labs 1–5) | 775 KB | All paragraphs and tables extracted and read in full (Labs 1–5). | Embedded image 1 was viewed: it is the **university crest**, not a DevNexus logo. Images 2–4 (use case, class, sequence diagrams) were not viewed; their content is described in the text and in Phase 3. |
| Phase 2 estimation document | 18 KB | Read in full (text and tables). | — |
| Lab 6 record | 1.3 MB | All paragraphs and tables extracted and read in full. | The 8 embedded diagram images were not viewed. Phase 3 §15 says it supersedes them. |

Also inspected: the project working directory, Git state, Python/Git versions, installed packages, and the public GitHub remote (read-only `git ls-remote`).

## 2. Project purpose and required modules

ASDPIP is a web platform that combines (a) supervised AI agents (code generation, testing, deployment) that carry out well-scoped tasks and (b) a project-intelligence dashboard (progress, estimation, risk). Every agent action is gated by human review/authorisation and recorded in an audit trail.

Seven modules (Phase 2 §3, 8,000 LOC), mapped to design components in Phase 3 §14.4:

| Phase 2 module | LOC | Phase 3 component |
|---|---|---|
| Requirement & Project Management | 1,200 | Project & Requirement Service |
| Agent Orchestration Engine | 2,500 | Agent Orchestrator (+ message queue) |
| Code Generation Agent Interface | 1,000 | Code Generation Agent |
| Testing Agent Interface | 900 | Testing Agent |
| Deployment Agent Interface | 800 | Deployment Agent |
| Dashboard & Reporting | 1,200 | Analytics & Risk Service, Web Dashboard UI |
| Notification & Audit | 400 | Notification & Audit Service |

Actors: Project Manager (PM), Developer (primary users); AI Agent subsystem (system actor). QA Team and System Administrator are explicitly **out of scope** for Phase 3 (Phase 3 §2 scope note, A-5).

## 3. Requirements discovered

Full list with status: [REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md). Summary:

- **14 functional requirements** FR-1…FR-14 (Lab Record Lab 2): FR-1…FR-9, FR-12 High; FR-10, 11, 13, 14 Medium.
- **11 non-functional requirements** NFR-1…NFR-11: performance (1,2), security (3,4), reliability (5,6), usability (7), scalability (8), maintainability (9), portability (10), auditability (11).
- **10 use cases** UC-01…UC-10 (Phase 3 §4); detailed scenarios for UC-03, 05, 06, 07.
- **10 risks** R1…R10 with mitigations (Phase 2 §11; Phase 3 §14.9).
- **Estimation formulas** (Phase 2): Basic COCOMO organic `E = 2.4·KLOC^1.05`, `D = 2.5·E^0.38`, cost ₹60,000/person-month; risk score = probability × impact (1–5), High ≥ 15, Medium 9–14, Low < 9.

## 4. Design and technology constraints

- Layered, service-based architecture; low coupling; **human in the loop before any merge or deployment** (Phase 3 §14.2).
- Agent commits **only to isolated feature branches**; never to protected branches (NFR-6, SRS design constraints).
- Every agent action attributable and reversible; `AUDIT_LOG` is **append-only** (insert + select only), exactly one of `user_id` / `agent_id` set per row (Phase 3 §8, §14.3).
- Specified stack: PostgreSQL, API Gateway, gRPC + message queue, Docker agent sandbox node, TLS 1.2+, GitHub/GitLab adapters (Phase 3 §13, §14).
- Phase 3 §15 **supersedes** Labs 4–6 where they differ (14 corrections C-01…C-14). Phase 3 is the design authority in this project.

## 5. Important diagrams and workflow rules

- **Task state chart (Fig 3.7)** — 8 states, no others: `Created → Assigned → Generating → In Review → Testing → Ready for Deployment → Deployed`, plus `Failed`.
  Transitions: `assignTask()` Created→Assigned; agent starts Assigned→Generating; `codeReady` Generating→In Review; agent error Generating→Failed; `[approved]` In Review→Testing; `[rejected]` In Review→Generating; `[tests passed]` Testing→Ready for Deployment; `[tests failed]` Testing→Generating; `authoriseDeployment()` Ready for Deployment→Deployed; `retry` Failed→Assigned.
  Rework loops and retry are bounded by a **retry limit in the pipeline configuration**; when exceeded the task is reported as a risk (FR-11) instead of looping.
- **Endpoints (§14.5)**: `POST /projects`, `POST /projects/{id}/requirements`, `PUT /projects/{id}/pipeline`, `POST /tasks`, `POST /tasks/{id}/assign`, `GET /tasks/{id}`, `POST /tasks/{id}/approve|reject|tests|deploy`, `GET /dashboard`, `GET /reports/estimation`, `GET /reports/risk`, `GET /notifications`, `GET /audit`.
- **E-R (Fig 3.6)**: 10 entities, 12 one-to-many relationships (USER, PROJECT, REQUIREMENT, TASK, AGENT, AGENT_RUN, TEST_RESULT, DEPLOYMENT, RISK_REPORT, AUDIT_LOG). Column lists in Phase 3 §14.3.
- **Pre-conditions order the pipeline** (UC-05/06/07), not `«include»` (correction C-03).

## 6. Conflicts, ambiguities and missing information

Each item has a resolution; those that change the documented design are recorded as deviations in [ARCHITECTURE.md](ARCHITECTURE.md) and [TEAM_CONTRACT.md](TEAM_CONTRACT.md). **Items marked ▲ need the team's or instructor's confirmation.**

| # | Finding | Resolution adopted |
|---|---|---|
| A1 | FR-6 lists statuses *queued / in-progress / completed / failed*; the state chart has 8 states. | Keep the 8 states as stored values; expose a derived `status_group` (queued = Created, Assigned; in_progress = Generating, In Review, Testing, Ready for Deployment; completed = Deployed; failed = Failed). |
| A2 | FR-1 needs *problem statement, scope, objectives*; `PROJECT` has no such columns. | Add three text columns (extension E-1). |
| A3 | FR-5 needs a *task description*; `TASK` has only `title`. | Add `TASK.description` (E-2). |
| A4 | FR-13 notifications; no notification entity; `GET /notifications` exists. | Add a `NOTIFICATION` table (E-3). ▲ |
| A5 | FR-11 asks for *delayed tasks*; `TASK` has no timestamps. | Add `created_at`, `status_changed_at` (E-2). |
| A6 | State chart has `retry` (Failed→Assigned); §14.5 has no retry endpoint. | Add `POST /tasks/{id}/retry` (E-4). |
| A7 | Retry limit value is not fixed (A-2); behaviour on exceeding it is "reported as a risk". | Default `retry_limit = 2` in `pipeline_config`. On exceeding, the transition is refused with `retry_limit_exceeded`, the task stays in its state, a risk is raised. **No new state is added.** ▲ default value |
| A8 | UC-05 step 5 says approval starts UC-06 automatically, but §14.5 has `POST /tasks/{id}/tests` ("trigger or re-run"). | Approval auto-starts tests; `POST /tests` is the re-run (valid in `Testing`). |
| A9 | UC-07 3a: failed deployment leaves the task in Ready for Deployment. | Implemented as written; a `DEPLOYMENT` row with `status=failed` is stored. |
| A10 | No login FR (O-3); Gateway handles login (A-5). | Role-based "current user" chosen with an `X-User-Id` header (UI user switcher). No passwords. Deviation D-6. ▲ |
| A11 | FR-9 says "Developer/PM authorisation"; UC-07 primary actor is the Developer. | Both roles may authorise deployment; all other role rules follow the use cases. |
| A12 | Class diagram `TestResult` shows `taskId`; the E-R shows `test_id` (PK) + `run_id`. | Use the E-R (the data design authority); treat `taskId` as a typo. |
| A13 | Class diagram has `Repository`, `Dashboard`; E-R has no table for either. | `Repository` realised by the Git adapter + workspace directory; `Dashboard` computed on request, never persisted. |
| A14 | FR-8 says the Testing Agent "generates and executes" tests; executing LLM-generated code on the host is unsafe. | The mock Testing Agent derives tests from the AST of the generated code and runs **static checks only**; generated code is never executed. Results are labelled *simulated* (D-5). |
| A15 | Lab 1 says "1-person team"; Phase 2 says three members (O-1). | Three members used (matches this project). |
| A16 | Phase 2 plans 8 months / 21.3 person-months; this delivery has ~1–2 weeks. | MVP scope (§7). Estimation formulas are still implemented and tested so that the numbers trace to Phase 2. |
| A17 | §14.5 lists only `GET /tasks/{id}`; the UI needs lists and a diff (UC-05 step 2). | Add `GET /projects`, `GET /projects/{id}`, `GET /tasks`, `GET /tasks/{id}/diff`, `GET /users`, `GET /me`, `GET /agents`, `POST /notifications/{id}/read` (E-4). |
| A18 | Phase 3 mandates PostgreSQL, gRPC, queue, containers, TLS; the demo runs on one laptop with zero budget. | Deviations D-1…D-4 in ARCHITECTURE.md. |
| A19 | Risk-level formula for a *project* is not defined; Phase 2 defines only a per-risk score. | Per-category probability × impact using Phase 2 thresholds; rule documented in TEAM_CONTRACT §9 (our interpretation). ▲ |
| A20 | The Lab 1 prose for roles ("Product Owner/Scrum Master = PM") has no software meaning. | No change. |

## 7. Recommended MVP scope and deferred features

**In MVP (end-to-end, tested):** FR-1…FR-14 with mock adapters — project/requirement/pipeline CRUD; task lifecycle exactly per Fig 3.7 with the retry limit; mock Code Generation / Testing / Deployment agents behind interfaces; feature-branch-only Git adapter; role checks; audit trail with DB-level append-only guarantee; notifications; dashboard, COCOMO estimation, risk report; responsive web UI over the real endpoints.

**Deferred / partial (stated honestly in KNOWN_LIMITATIONS.md):** real LLM provider and second provider (R3); real GitHub/GitLab/CI integrations (NFR-10); TLS (NFR-4); PostgreSQL, gRPC and message queue; container-isolated agents and independent deployment (NFR-9); 99.5% uptime/queueing across restarts (NFR-5); 50-concurrent-task load behaviour beyond a smoke test (NFR-8); formal usability test (NFR-7); user/account administration and QA/Admin actors (out of scope per Phase 3); issue-tracker integration; database backup (R8).

## 8. Environment and repository status (at audit time)

- OS: Windows 11 Home; shell PowerShell/Git Bash.
- Python: default `python` 3.11.9; `py` launcher also has 3.13. Project venv: `py -3.11 -m venv .venv`.
- Git 2.46.0. The project folder was **not** a Git repository. The remote `https://github.com/AryanRajguru22/DevNexus` was queried read-only (`git ls-remote`): it returned **no refs (empty repository)**. A local `git init -b main` with `origin` configured was therefore created; the baseline was later published as the initial commit.
- Pre-existing contents: only the 4 course documents (kept out of the repository, see D10 in the work allocation). No code, no image/logo files were present on disk (searched the project, Downloads, Desktop, Pictures).
- **Logo:** the selected green geometric DevNexus mark was not available as a file. A clearly-labelled **placeholder SVG** is used (`app/web/static/img/devnexus-logo-placeholder.svg`). ▲ Action for Aryan: drop the real asset at `app/web/static/img/devnexus-logo.svg` (or `.png`) and update one line in `base.html`.
- Existing libs in the global interpreter did not include the web stack; all dependencies are installed in `.venv` and pinned in `requirements.txt`.
