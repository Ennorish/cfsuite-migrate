# Deferred Items — Phase 02-core-etl

## Out-of-scope issues discovered during plan 02-03 execution

### 1. test_request_flow.py — pre-existing RED test suite (no implementation)

- **Origin:** Commit `3b29ddb` (plan 02-02, test(02-02): add failing tests for request_flow migrator)
- **Status:** The RED tests were committed but migrate/objects/request_flow.py was never implemented
- **Failing test:** `TestMigrateRequestFlows::test_self_referential_resolution` — `update` not called because the module doesn't exist
- **Ruff issue:** `from unittest.mock import MagicMock, call, patch` — `call` unused (F401)
- **Action required:** Plan 02-02 execution needs to be completed (implement migrate/objects/request_flow.py)
- **Logged by:** Plan 02-03 execution on 2026-03-12
