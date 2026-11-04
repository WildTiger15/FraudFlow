# API smoke test (2026-11-04 23:51 UTC)

Run on a throwaway copy of the database; the real database was not changed. This replays the Power Automate flow's HTTP calls from Python. It is not a Power Automate run.

1. GET /cases?status=pending_review -> 20 cases waiting
2. GET /cases/C-A000011 -> alert A000011, flagged transaction T0000086, label 'LOW CONFIDENCE - check every fact - drafted WITHOUT AI (template)'
3. Alert A000011 status before decision: drafted
4. POST /cases/C-A000011/decision -> status rejected at 2026-11-04T23:51:18+00:00
5. GET /decisions -> 1 row(s); last reviewer 'smoke test (automated, not a real review)'
6. Second decision on the same case -> HTTP 409 (refused, as intended)
7. Request without API key -> HTTP 401
