# Implementation Plan

**Deadline: Fri 23 Oct 2026.** The baseline already runs end to end (248 passing tests at commit `37ab6aa`; 275 with PLAN-13/14 applied locally, 2026-10-20), so the remaining six days are parallel hardening, UI completion, evidence and rehearsal.

The authoritative day-by-day schedule, task list, owners, dependencies, acceptance criteria and file ownership are in:
- `TEAM_WORK_DIVISION.md` (schedule, interfaces, per-person task tables)
- `GITHUB_ISSUES_PLAN.md` / `.csv` (24 proposed tasks PLAN-01..PLAN-24; GitHub issues are created from them separately)

Key dates: contracts confirmed Sun 18 Oct 20:00 - **feature freeze Tue 20 Oct 21:00** - regression and evidence Wed 21 Oct - rehearsals #1 (10:00) and #2 (16:00) and release candidate Thu 22 Oct - deadline Fri 23 Oct. P2 work is cut first if anything slips.

Build order (steps 1-9 are done; step 10 is in progress): audit, contract, skeleton, workflow/audit/notifications, agents/adapters, API, UI, analytics, tests, then docs/demo/release.
