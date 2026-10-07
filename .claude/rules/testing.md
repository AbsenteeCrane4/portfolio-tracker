---
paths:
  - "tests/**"
---

# Testing rules

- **No network.** Unit tests never make a network call. Feature tests run
  against the fake `AppContext` helper, containing only the attributes the
  feature uses.
- **Recorded fixtures for providers.** Credentials and account identifiers are
  scrubbed. No secrets go in any fixture, including fake ones that look real.
- **DB-backed tests** take the `db_session` fixture from `tests/conftest.py`.
  It wraps each test in a transaction that is rolled back afterwards, and it
  reads `TEST_DATABASE_URL`. These tests skip when it is unset, which is fine
  locally, but CI always sets it and must never skip them silently.
- **Property tests (`hypothesis`)** cover cost basis, IRR and return
  attribution, and tax matching. Prefer invariants such as conservation of
  quantity and cost, reversal of a correction restoring the prior state, and
  order-independence where it applies.
- **Golden cases** use HMRC worked examples for CGT and hand-checked
  spreadsheets for return attribution. Each case carries a comment citing its
  source.
- **Valuation rebuild equivalence:** apply changes incrementally, then compare
  against a from-scratch rebuild. The results must be equal exactly, as
  `Decimal`s, with no tolerance.
- **Use `Decimal` for money in tests too.** Compare exactly. Never use
  `pytest.approx` on money.
- **Datetimes are UTC-aware.** ruff's `DTZ` rules apply to tests as well.
- **`tests/test_layout.py` is the boundary guard.** Don't loosen it to make a
  change pass. If a rule there blocks legitimate work, raise it.
