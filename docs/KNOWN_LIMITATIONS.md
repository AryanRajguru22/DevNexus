# Known Limitations (honest list)

These are deliberate scope decisions for a laptop demo built in 1–2 weeks with no budget. Each is also visible in the UI banner, ARCHITECTURE.md §3 or the traceability matrix.

## Simulated or mock parts
1. **The "AI" is a mock.** `MockLLMProvider` returns a deterministic template (about 25 lines of Python per task), not output from a language model. FR-5 is therefore *partially* implemented. A real provider can be added behind `LLMProvider` (no code outside `adapters/` changes).
2. **Tests are static checks, not executed tests.** The Testing Agent parses generated code with `ast` and checks docstrings/return types; it never runs generated code (safety decision D-5). Pass/fail counts and "coverage" are labelled *simulated*; coverage is the share of functions whose checks pass, not line coverage.
3. **Git host and CI/CD are mocks.** Branches and `main` are directories under `data/workspace/`; "deployment" merges files into the `main` directory and returns a simulated CI result. No GitHub/GitLab/CI integration (NFR-10 partial).

## Security and operations
4. **No real authentication.** The acting user is chosen in the UI (header `X-User-Id`). Role-based *authorisation* is enforced and audited; anyone who can reach the server can impersonate anyone. Do not expose it beyond localhost.
5. **No TLS** (NFR-4 deferred); plain HTTP on 127.0.0.1.
6. **Background jobs are in-process.** If the server stops mid-run, a task can be left in *Assigned/Generating/Testing* until recovery (proposed task PLAN-13) is implemented. No durable queue, no uptime target (NFR-5 partial).
7. **SQLite, one process.** The 50-task test is sequential; true concurrent load was not measured (NFR-8 partial). No backups (R8).
8. Two near-simultaneous test jobs for the same task are not prevented from starting; the workflow rejects the later state change and rolls it back, but this race has no dedicated test yet (proposed tasks PLAN-14 and PLAN-07).

## Functional gaps
9. Requirements and projects cannot be edited after creation (proposed task PLAN-08).
10. Notifications are in-app only (no e-mail/push); polled every 10 s.
11. No user administration, no QA or System Administrator actors (explicitly out of scope per Phase 3 §2), no issue-tracker integration, no pipeline-constraint enforcement beyond `max_loc`, retry limit, agent activation and delay threshold.
12. Estimation is Basic COCOMO over task sizes (actual generated LOC, else half of `max_loc` as a planning figure). With a handful of tiny tasks it returns tiny numbers; it is a faithful application of the Phase 2 formula, not a prediction.
13. The project-level risk rule (probability/impact per category) is our interpretation of Phase 2's scoring scale (A19) pending team confirmation.
14. The usability target (NFR-7, < 10 minutes for a first-time PM) has not yet been measured (proposed task PLAN-19).

## Documents
15. Figures 3.3–3.5 and 3.8–3.11 of the Phase 3 PDF and all images in Lab 4–6 records were read through their captions and tables, not visually (PROJECT_AUDIT §1).
16. The official DevNexus logo file was not available; a labelled placeholder SVG is used (proposed task PLAN-10).
