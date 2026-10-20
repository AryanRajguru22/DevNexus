# DevNexus

**AI-Assisted Software Development & Project Intelligence Platform** — academic project **ASDPIP** (*Autonomous Software Development & Project Intelligence Platform*), CSE3132 Software Engineering Lab.

Supervised AI agents (code generation → testing → deployment) work on tasks derived from requirements, every merge and deployment needs explicit human approval, and a project-intelligence layer shows progress, estimation and risk. The authoritative specification is the set of course documents (Lab Record, Phase 2 estimation, Lab 6, Phase 3 design; the Phase 3 design wins where it supersedes the earlier labs). They are not included in this repository; the team holds them privately.

> **Honest scope:** the LLM, Git host and CI/CD runner are **local mock adapters**, and test results/coverage are **simulated static checks**. Everything else (workflow, roles, audit trail, notifications, dashboard, estimation, risk) is real and persisted. See `docs/KNOWN_LIMITATIONS.md`.

## Quick start

Requires **Python 3.11** (3.12+ should work; the project was built and tested on 3.11.9) and Git.

### Windows (PowerShell)
```powershell
git clone https://github.com/AryanRajguru22/DevNexus.git
cd DevNexus
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest                      # 275 tests
python -m app               # http://127.0.0.1:8000
```

### macOS / Linux
```bash
git clone https://github.com/AryanRajguru22/DevNexus.git
cd DevNexus
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
python -m app
```

Open http://127.0.0.1:8000 · API docs at `/docs`. Use the **Acting as** menu (top right) to switch between the demo Project Manager and Developers (no passwords: deviation D-6).

Optional demo data (through the real API, server must be running, fresh database):
```
python scripts/demo_seed.py
```
To see the *Generating/Testing* states during a demo, slow the mock agents: set `DEVNEXUS_MOCK_AGENT_DELAY=1.5` before `python -m app`.

### Configuration (environment variables, all optional)
`DEVNEXUS_DATA_DIR` (default `./data`: SQLite file + mock Git workspace) · `DEVNEXUS_DATABASE_URL` · `DEVNEXUS_MOCK_AGENT_DELAY` · `DEVNEXUS_SEED_DEMO_USERS` (default `1`) · `DEVNEXUS_LLM_PROVIDER` (default and only built-in value: `mock`; an unknown name stops start-up) · `DEVNEXUS_RECOVER_ON_STARTUP` (default `1`; `0` disables re-running jobs interrupted by a restart) · `DEVNEXUS_HOST` · `DEVNEXUS_PORT`. No secrets are needed or stored. To reset everything, stop the server and delete `data/`.

### Verified on
| OS | Python | Result |
|---|---|---|
| Windows 11 | 3.11.9 | 275 passed in a clean venv from `requirements.txt` (2026-10-20, uncommitted working tree; 248 on the 2026-10-17 baseline) |
| macOS | — | not yet verified (proposed task PLAN-20) |
| Linux | — | not yet verified (proposed task PLAN-20) |

## Repository map
```
app/            FastAPI application (see docs/ARCHITECTURE.md)
  workflow.py   Task state chart: the only code that changes task.status
  agents/       Code Generation, Testing, Deployment agents
  adapters/     LLM, Git, CI/CD interfaces + mock/local implementations
  services/     orchestrator (agent jobs), analytics (dashboard, COCOMO, risk)
  routers/      REST API
  web/          Jinja2 page shells, CSS, vanilla JS
tests/          pytest suite (each test has its own temp DB)
scripts/        demo_seed.py
docs/           audit, contract, architecture, plans, test evidence, kickoff message
```

## Documentation index
`docs/PROJECT_AUDIT.md` · `REQUIREMENTS_TRACEABILITY.md` · `ARCHITECTURE.md` · `TEAM_CONTRACT.md` · `IMPLEMENTATION_PLAN.md` · `TEAM_WORK_DIVISION.md` · `GITHUB_ISSUES_PLAN.md` (+ `.csv`) · `TEST_PLAN.md` · `DEMO_SCRIPT.md` · `KNOWN_LIMITATIONS.md` · `TEAM_KICKOFF_MESSAGE.md`

## Contributing (team)
Short-lived branches from `main`, one PR per issue, `pytest` green before review, shared files (`models.py`, `schemas.py`, `main.py`, `workflow.py`, `TEAM_CONTRACT.md`) only through a coordinated PR. Details: `docs/TEAM_CONTRACT.md` §10–11.

## Team
Aryan (project lead) and two teammates (listed by role label until they consent to being named).
