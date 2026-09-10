"""Tests for the interactive backend (spec sections 13, 14, 64)."""

import pytest


@pytest.fixture(scope="module")
def session(config, environment):
    from mathesis.validation import InteractiveSession

    s = InteractiveSession(config, environment, imports=("Mathesis.Basic",))
    yield s
    s.close()


def test_session_ready(session):
    assert session.get_proof_state().status in ("ready", "success")


def test_valid_action(session):
    result = session.submit_action("theorem it_good : 1 = 1 := rfl")
    assert result.status.value == "SUCCESS"
    assert result.execution_time < 5.0
    assert result.source_hash


def test_invalid_action(session):
    result = session.submit_action("theorem it_bad : 1 = 2 := rfl")
    assert result.status.value != "SUCCESS"
    assert result.failure_class.value == "MODEL_FAILURE"
    assert len(result.errors) > 0
    assert result.errors[0].message


def test_action_record_fields(session):
    result = session.submit_action("theorem it_fields : True := trivial")
    d = result.to_dict()
    assert set(d) >= {"previous_state", "action", "next_state", "errors",
                      "execution_time", "status", "source_hash"}


def test_env_persists_across_actions(session):
    # declaration from a previous action is visible in the next one
    session.submit_action("theorem it_pers : 2 = 2 := rfl", update_env=True)
    result = session.submit_action("#print axioms it_pers")
    assert result.status.value == "SUCCESS"
    assert any("it_pers" in i for i in result.next_state.infos)


def test_get_errors(session):
    session.submit_action("theorem it_err : 1 = 2 := rfl")
    errors = session.get_errors()
    assert errors and errors[0].severity == "error"


def test_reset(session, config, environment):
    from mathesis.validation import InteractiveSession

    s = InteractiveSession(config, environment, imports=("Mathesis.Basic",))
    s.submit_action("theorem it_before_reset : 3 = 3 := rfl")
    s.reset()
    result = s.submit_action("theorem it_after_reset : 4 = 4 := rfl")
    assert result.status.value == "SUCCESS"
    s.close()


def test_close_then_reopen(config, environment):
    from mathesis.validation import InteractiveSession

    s = InteractiveSession(config, environment, imports=("Mathesis.Basic",))
    s.close()
    s.close()  # idempotent
    s.create_session()
    result = s.submit_action("theorem it_reopen : 5 = 5 := rfl")
    assert result.status.value == "SUCCESS"
    s.close()


def test_infrastructure_failure_not_math(session):
    """Lean crash must be attributed as LEAN/INFRASTRUCTURE failure, not
    mathematical FAIL (section 64)."""
    from mathesis.validation import FailureClass, ProofStatus

    if session._proc is not None:
        session._proc.kill()
        session._proc.wait(timeout=10)
    result = session.submit_action("theorem it_x : 1 = 1 := rfl")
    assert result.failure_class is not None
    assert result.failure_class.value in ("LEAN_FAILURE", "INFRASTRUCTURE_FAILURE")
    assert result.status.value not in ("FAIL_TYPECHECK", "FAIL_PARSE", "FAIL_KERNEL")
    # session recovers
    session.create_session()
    result = session.submit_action("theorem it_y : 1 = 1 := rfl")
    assert result.status.value == "SUCCESS"
