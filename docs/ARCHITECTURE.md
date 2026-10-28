# DevNexus — Architecture

Source of truth: Phase 3 design (Fig 3.10 component diagram, Fig 3.11 deployment diagram, §14). This file records **how that design is realised for a one-laptop, zero-budget, 1–2 week delivery**, and every deviation.

## 1. Style

Layered and service-based (Phase 3 §14.2) — kept, but the services are **modules of one FastAPI process** instead of separate containers.

```
Browser (Jinja2 page shells + vanilla JS)            Web Dashboard UI           app/web/
        │  REST/JSON, header X-User-Id                      │
FastAPI app  ── security.py (role check, audit of denials) ── API Gateway       app/security.py, app/errors.py
  routers/projects  routers/tasks  routers/reports  routers/system
        │                │                │
  Project & Req.   Agent Orchestrator   Analytics & Risk     Notification & Audit
  routers/projects services/orchestrator services/analytics  notifications.py, audit.py
        │                │ (workflow.py = Task state chart, the only place that changes task.status)
        │      ┌─────────┼───────────┐
        │  CodeGenerationAgent  TestingAgent  DeploymentAgent       app/agents/
        │      │ LLMProvider   │ (static AST)   │ GitAdapter + CICDAdapter   app/adapters/
        ▼
SQLite (SQLAlchemy models = Phase 3 E-R + NOTIFICATION)   app/models.py, app/db.py
Workspace directory (mock Git host)                       data/workspace/<project>/{main,branches/}
```

Principles carried over from the design: low coupling (routers → services → agents → adapters; agents never touch the database), one responsibility per module, **human in the loop before any merge or deployment**, agents write only to feature branches, audit trail append-only.

## 2. Component mapping (Phase 3 §14.4 → code)

| Phase 3 component | Code |
|---|---|
| Web Dashboard UI | `app/web/templates/*.html`, `static/js/app.js`, `static/css/app.css` |
| API Gateway (auth, RBAC, routing) | `app/security.py`, `app/main.py`, `app/routers/*` |
| Project & Requirement Service | `app/routers/projects.py`, `app/validation.py` |
| Agent Orchestrator | `app/services/orchestrator.py`, `app/workflow.py`, `app/services/tasks.py` |
| Code Generation / Testing / Deployment Agent | `app/agents/codegen.py`, `testing.py`, `deployment.py` |
| Analytics & Risk Service | `app/services/analytics.py` |
| Notification & Audit Service | `app/notifications.py`, `app/audit.py`, `routers/system.py` |
| Project Database | `app/models.py`, `app/db.py` (SQLite) |
| LLM Provider / Git Hosting / CI/CD Runner (external) | `app/adapters/llm.py`, `git_local.py`, `cicd.py` — mocks behind interfaces |

## 3. Deviations from the documented design (all intentional, none hidden)

| ID | Documented | Implemented | Why | Impact |
|---|---|---|---|---|
| D-1 | PostgreSQL | SQLite file (`data/devnexus.db`) | zero setup/cost; SQLAlchemy keeps the code portable | none on features; NFR-8 headroom lower |
| D-2 | Separate services, gRPC, message queue, containers | One FastAPI process; services are modules; "queue" = FastAPI background tasks | 1–2 weeks, one laptop | NFR-5/8/9 partial; a job lost when the process dies is re-run at the next start (PLAN-13), but there is no durable queue |
| D-3 | TLS 1.2+ on every external link | Plain HTTP on 127.0.0.1 | local demo; TLS belongs to the reverse proxy in a real deployment | NFR-4 deferred |
| D-4 | Real LLM, GitHub/GitLab, CI/CD runner | Deterministic **mock** LLM, local directory "Git host", mock CI/CD; all behind interfaces | no paid services; no network dependency in a viva | FR-5/8/9 partial; clearly labelled in UI banner, code and tests |
| D-5 | Testing Agent "generates and executes" tests | Generated code is only **parsed** (AST) and statically checked; generated tests are committed but never run | never execute arbitrary generated code on the host | results/coverage flagged `simulated` |
| D-6 | Login handled by the Gateway (A-5, O-3: no login FR) | Role-based "acting user" via `X-User-Id`, user switcher in the UI, no passwords | no login requirement exists; avoids storing credentials | authorisation is real, authentication is not (NFR-3 partial) |
| D-7 | 10 E-R entities | + `NOTIFICATION`; extra columns (contract §3 E-1…E-3) | FR-1, FR-5, FR-11, FR-13 need data the E-R lacks | additive only; no documented column removed or renamed |
| D-8 | §14.5 endpoint list | + list/detail/diff/retry/read endpoints (E-4) | UI and the state chart's `retry` need them | additive only |

## 4. Key design decisions (viva notes)

1. **One transition table** (`workflow.TRANSITIONS`) = Fig 3.7. Every mutating endpoint and every agent job calls `apply_event`, which checks state → actor → pipeline gate → retry limit, then changes the state and writes the audit row in the *same transaction*. There is no other code path that assigns `task.status`.
2. **Retry limit without a new state** (A-2): refused with `409 retry_limit_exceeded`, written to the audit log, raised as a `risk_threshold` notification and included in the risk report.
3. **Audit immutability at the database level**: SQLite triggers abort `UPDATE`/`DELETE` on `audit_log`; a CHECK constraint enforces exactly one of `user_id`/`agent_id`.
4. **Authorisation recorded before action**: deployment writes `task.deploy_authorise` *before* the Deployment Agent runs, so a failed deployment still shows who authorised it; main is restored (rollback) and the task stays *Ready for Deployment* (UC-07 alt 3a).
5. **NFR-6 enforced in code, not by convention**: `LocalGitAdapter.commit` refuses `main`/`master`; path traversal and invalid branch names are rejected; tested.
6. **Everything on screen is computed**: the dashboard/estimation/risk numbers are queries over persisted rows, with Phase 2 constants (COCOMO 2.4/1.05/2.5/0.38, ₹60,000, risk bands). Simulated values are labelled.
7. **Agents are replaceable** (NFR-9/10 partial): `LLMProvider`, `GitAdapter`, `CICDAdapter` are small interfaces; a provider is added by registering a factory in `adapters/llm.PROVIDERS` without touching routers or workflow. `mock` (default) and `ollama` (optional local model, `adapters/ollama.py`, stdlib HTTP, every failure mapped to a clean *Failed* task) exist today.

## 4a. Database (SQLite via SQLAlchemy 2.x; derived from `app/models.py`)

**11 model classes / 11 tables** (`Base.metadata.create_all` at start-up; there are *no migrations*: after a schema change, stop the server and delete `data/` - demo data only):

| Class | Table | Responsibility |
|---|---|---|
| `User` | `user` | demo identities with a role (Project Manager / Developer) |
| `Agent` | `agent` | the three AI agent types (code generation, testing, deployment) |
| `Project` | `project` | project definition + `pipeline_config` JSON (active agents, retry limit, constraints) |
| `Requirement` | `requirement` | functional / non-functional requirements of a project (Draft → Approved, then locked) |
| `Task` | `task` | unit of work and its 8-state status (the workflow table changes it) |
| `AgentRun` | `agent_run` | one execution of an agent on a task (branch, status, error, LOC) |
| `TestResult` | `test_result` | simulated pass/fail counts and coverage of a run |
| `Deployment` | `deployment` | one deployment attempt of a run (succeeded / failed) |
| `RiskReport` | `risk_report` | stored project risk assessment |
| `Notification` | `notification` | in-app notifications (extension D-7 to the Phase 3 E-R) |
| `AuditLog` | `audit_log` | append-only trail (DB triggers refuse UPDATE/DELETE; exactly one actor per row) |

*Models vs schemas*: `models.py` classes are the persisted tables (SQLAlchemy); `schemas.py` classes are the Pydantic request/response documents of the REST API - a model is never returned to a client directly.

## 5. Runtime & configuration

`python -m app` → http://127.0.0.1:8000 (API docs at `/docs`). Environment variables: `DEVNEXUS_DATA_DIR` (default `./data`), `DEVNEXUS_DATABASE_URL`, `DEVNEXUS_MOCK_AGENT_DELAY` (seconds; makes *Generating/Testing* visible in a demo), `DEVNEXUS_SEED_DEMO_USERS` (default 1), `DEVNEXUS_LLM_PROVIDER` (`mock` default | `ollama`), `DEVNEXUS_OLLAMA_URL` / `_MODEL` / `_TIMEOUT` (only for `ollama`), `DEVNEXUS_RECOVER_ON_STARTUP` (default 1), `DEVNEXUS_HOST`, `DEVNEXUS_PORT`. Nothing sensitive is stored; no secrets exist in the MVP.

## 6. Risk mapping (Phase 2 R1–R10)

R1 review + tests gate (workflow) · R2 role checks + audit · R3 retry/Failed state + provider interface (second provider deferred) · R4 feature-branch-only adapter · R5 dashboard/risk report · R6 adapter layer (real integrations deferred) · R7 background jobs, 50-task smoke test · R8 SQLite file (backup procedure deferred) · R9 guided UI (usability test pending) · R10 traceability matrix + this contract.
