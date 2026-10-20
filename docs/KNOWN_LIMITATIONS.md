# Known Limitations (honest list)

These are deliberate scope decisions for a laptop demo built in 1–2 weeks with no budget. Each is also visible in the UI banner, ARCHITECTURE.md §3 or the traceability matrix.

## Simulated or mock parts
1. **The "AI" is a mock.** `MockLLMProvider` returns a deterministic template (about 25 lines of Python per task), not output from a language model. FR-5 is therefore *partially* implemented. A real provider can be added behind `LLMProvider` (no code outside `adapters/` changes).
2. **Tests are static checks, not executed tests.** The Testing Agent parses generated code with `ast` and checks docstrings/return types; it never runs generated code (safety decision D-5). Pass/fail counts and "coverage" are labelled *simulated*; coverage is the share of functions whose checks pass, not line coverage.
3. **Git host and CI/CD are mocks.** Branches and `main` are directories under `data/workspace/`; "deployment" merges files into the `main` directory and returns a simulated CI result. No GitHub/GitLab/CI integration (NFR-10 partial).

## Security and operations
4. **No real authentication.** The acting user is chosen in the UI (header `X-User-Id`). Role-based *authorisation* is enforced and audited; anyone who can reach the server can impersonate anyone. Do not expose it beyond localhost.
5. **No TLS** (NFR-4 deferred); plain HTTP on 127.0.0.1.
6. **Background jobs are in-process; recovery is best-effort.** If the server stops mid-run, the next start repairs the database and re-runs the lost job (PLAN-13): a `running` run is closed as `failed` ("Interrupted…", audit `agent.error`), and Assigned / Generating / un-tested Testing tasks are re-dispatched on a background thread. The interrupted run **counts as an attempt** toward the retry limit and toward the "repeated failures" risk. If the retry limit leaves no run, the task goes to *Failed* instead. Recovery assumes **one application process per database** and has no durable queue, so there is no uptime target (NFR-5 partial). Verified by killing a real server process mid-generation and restarting it (2026-10-20, Windows); not verified on macOS/Linux.
7. **SQLite, one process.** The 50-task test is sequential; true concurrent load beyond the small thread tests below was not measured (NFR-8 partial). No backups (R8).
8. **Duplicate protection (PLAN-14) is a database compare-and-set, not a queue.** A transition is applied only if the stored status still matches, and a generation job will not start while a run of that task is `running`; concurrent approvals, deploys and generation/test jobs for one task therefore yield one run / one test result / one deployment (tests use real threads on a SQLite file and a deterministic stale-session case). Limits: two *explicit* re-run requests for a task parked in Testing (retry limit reached) are two requests and run one after the other; a deployment holds the database write lock for its duration, so other writes wait (mock deploy only); behaviour on PostgreSQL or several processes was not tested.
8a. The LLM provider is chosen with `DEVNEXUS_LLM_PROVIDER`; only `mock` exists. An unknown name stops start-up with a clear message. A real provider has to be written and registered in `adapters/llm.PROVIDERS`; none is included or tested.

## Functional gaps
9. Requirements and projects can be edited only by a PM, through `PATCH` endpoints that are an extension (E-5, contract C-3) awaiting team confirmation. An Approved requirement is locked; it cannot be moved back to Draft.
10. Notifications are in-app only (no e-mail/push); polled every 10 s.
11. No user administration, no QA or System Administrator actors (explicitly out of scope per Phase 3 §2), no issue-tracker integration, no pipeline-constraint enforcement beyond `max_loc`, retry limit, agent activation and delay threshold.
12. Estimation is Basic COCOMO over task sizes (actual generated LOC, else half of `max_loc` as a planning figure). With a handful of tiny tasks it returns tiny numbers; it is a faithful application of the Phase 2 formula, not a prediction.
13. The project-level risk rule (probability/impact per category) is our interpretation of Phase 2's scoring scale (A19) pending team confirmation.
14. The usability target (NFR-7, < 10 minutes for a first-time PM) has not yet been measured (proposed task PLAN-19).

## Documents
15. Figures 3.3–3.5 and 3.8–3.11 of the Phase 3 PDF and all images in Lab 4–6 records were read through their captions and tables, not visually (PROJECT_AUDIT §1).
16. The official DevNexus logo file was not available; a labelled placeholder SVG is used (proposed task PLAN-10).
