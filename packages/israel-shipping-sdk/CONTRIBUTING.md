# Contributing

## TDD is not optional here

This project exists because Israeli courier integration is usually done by
trial and error against undocumented APIs. The whole point is that this
SDK's behavior is *proven*, not guessed. Concretely:

1. **Tests first.** Write the failing test(s) before writing the
   implementation. Confirm they fail for the reason you expect (missing
   attribute, `ModuleNotFoundError` — not a typo in the test itself), then
   implement until green, then refactor with the suite still green.
2. **One fixture file per documented response shape.** Every fixture in
   `tests/fixtures/` must be traceable to one of:
   - the provider's own public API docs,
   - a captured real response (redact secrets, keep the shape),
   - or — as with HFD — the provider's own official plugin/integration
     source, cited by name, version, and file in a comment at the top of
     the adapter module.

   Do not invent a fixture shape "because it's probably like this." If you
   don't have a source, say so explicitly in the test (see the HFD
   `get_tracking_status` test's `xfail` marker for the pattern) rather than
   asserting invented behavior as fact.
3. **New provider = new file in `providers/`, satisfying
   `BaseShippingProvider`.** Add it to `REGISTERED_PROVIDERS` in
   `tests/test_base_contract.py` so the shared conformance suite runs
   against it. If an operation genuinely has no equivalent on that
   provider, raise `UnsupportedOperationError` and say why in a comment —
   don't fabricate a fallback that silently does the wrong thing.
4. **Uncertain findings are marked, not smoothed over.** If you reverse-
   engineer a provider and can't confirm a specific endpoint (no call site
   observed, only a configured URL, say), implement your best inference,
   but mark its test `@pytest.mark.xfail(strict=False, reason="...")`
   explaining exactly what's unconfirmed, add a fallback status like
   `ShipmentStatus.UNKNOWN` rather than crashing, and say so in a docstring.
   Silently presenting a guess as a confirmed fact is the one thing this
   project can't tolerate — see `providers/hfd.py`'s `get_tracking_status`.

## Local setup

```bash
python -m venv .venv
.venv/Scripts/activate    # or source .venv/bin/activate on macOS/Linux
pip install -e ".[dev]"
pytest
```

## Before opening a PR

```bash
pytest --cov=israel_shipping_sdk
ruff check src/ tests/
mypy src/
```

CI runs the same three commands on 3.10/3.11/3.12 — matching that locally
avoids surprises.
