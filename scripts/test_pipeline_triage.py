"""Standalone self-test for pipeline_triage.py -- run directly, not part of
the app's DB-backed suite: `python -m pytest scripts/test_pipeline_triage.py -q`
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pipeline_triage import classify


def test_high_risk_always_escalates():
    result = classify("high", ["tests/conftest.py"])
    assert result["decision"] == "full_pipeline"


def test_medium_risk_always_escalates():
    result = classify("medium", ["tests/conftest.py"])
    assert result["decision"] == "full_pipeline"


def test_low_risk_multi_file_escalates():
    result = classify("low", ["a.py", "b.py"])
    assert result["decision"] == "full_pipeline"


def test_low_risk_sensitive_path_escalates():
    result = classify("low", ["server/app/routers/auth_router.py"])
    assert result["decision"] == "full_pipeline"


def test_low_risk_payment_path_escalates():
    result = classify("low", ["server/app/services/pay_order.py"])
    assert result["decision"] == "full_pipeline"


def test_low_risk_single_nonsensitive_file_is_fast_path():
    # This is the actual rate-limiter fix from the L1/L2/L3 pilot
    # (fix/test-ratelimiter-leak) -- a real case that should have taken
    # the fast path instead of the full pipeline.
    result = classify("low", ["tests/conftest.py"])
    assert result["decision"] == "fast_path"


def test_no_files_never_fast_path():
    result = classify("low", [])
    assert result["decision"] == "full_pipeline"
