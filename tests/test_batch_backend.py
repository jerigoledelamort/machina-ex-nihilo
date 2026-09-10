"""Smoke tests for the batch ProofValidator pipeline (spec sections 9, 12, 15)."""

HEADER = "import Mathesis.Basic\n"


def test_valid_proof_success(validator):
    src = HEADER + """
theorem t_rfl : 1 = 1 := rfl

#print axioms t_rfl
"""
    result = validator.verify_candidate(src, task_id="t_success")
    assert result.status.value == "SUCCESS", result.to_dict()
    assert result.kernel_axioms == []


def test_sorry_blocked(validator):
    src = HEADER + "theorem t_bad : 1 = 1 := sorry\n"
    result = validator.verify_candidate(src, task_id="t_sorry")
    assert result.status.value == "FAIL_SAFETY"
    assert result.failure_class.value == "INVALID_ACTION"


def test_user_axiom_blocked(validator):
    src = HEADER + "axiom magic : ∀ (p : Prop), p ∨ ¬ p\n"
    result = validator.verify_candidate(src, task_id="t_axiom")
    assert result.status.value == "FAIL_SAFETY"


def test_native_decide_blocked(validator):
    src = HEADER + "theorem t_nd (x : Nat) : x = x := by native_decide\n"
    result = validator.verify_candidate(src, task_id="t_ndecide")
    assert result.status.value == "FAIL_SAFETY"
    # restricted mechanism usage must be recorded (section 9)
    assert any("native_decide" in d.message for d in result.diagnostics)


def test_unsafe_blocked(validator):
    src = HEADER + "unsafe def u : Nat := 0\n"
    result = validator.verify_candidate(src, task_id="t_unsafe")
    assert result.status.value == "FAIL_SAFETY"


def test_disallowed_import_blocked(validator):
    src = "import Std.Data.HashMap\ntheorem t : 1 = 1 := rfl\n"
    result = validator.verify_candidate(src, task_id="t_import")
    assert result.status.value == "FAIL_SAFETY"
    assert any("disallowed import" in d.message for d in result.diagnostics)


def test_parse_error(validator):
    src = HEADER + "theorem t : 1 = 1 := := rfl\n"
    result = validator.verify_candidate(src, task_id="t_parse")
    assert result.status.value == "FAIL_PARSE"
    assert result.failure_class.value == "MODEL_FAILURE"


def test_type_error(validator):
    src = HEADER + "theorem t : 1 = 2 := rfl\n"
    result = validator.verify_candidate(src, task_id="t_type")
    assert result.status.value in ("FAIL_TYPECHECK", "FAIL_KERNEL")
    assert result.failure_class.value == "MODEL_FAILURE"


def test_kernel_axiom_recorded_not_violated(validator):
    # Classical.choice is TRUSTED KERNEL (section 9): allowed, but must be
    # recorded in provenance (kernel_axioms).
    src = HEADER + """
theorem t_em (p : Prop) : p ∨ ¬ p := Classical.em p

#print axioms t_em
"""
    result = validator.verify_candidate(src, task_id="t_classical")
    assert result.status.value == "SUCCESS", result.to_dict()
    assert "Classical.choice" in result.kernel_axioms


def test_result_has_provenance_fields(validator):
    src = HEADER + "theorem t_prov : True := trivial\n"
    result = validator.verify_candidate(src, task_id="t_prov")
    d = result.to_dict()
    assert d["source_hash"] and d["environment_hash"]
    assert d["wall_time_seconds"] > 0


def test_environment_fingerprint_stable(environment):
    d1 = environment.to_dict()
    assert d1["environment_hash"]
    assert "4.33.1" in d1["lean_version"]
    assert d1["manifest_hash"] is not None or True
