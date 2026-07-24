from __future__ import annotations

import pytest

from cleandrop.domain.errors import InvalidTransitionError
from cleandrop.domain.models import (
    JobState,
    NormalizedRect,
    ResourceLimits,
    SanitizationPlan,
    SanitizationProfile,
)
from cleandrop.domain.state_machine import JobStateMachine


@pytest.mark.parametrize(
    ("values", "valid"),
    [
        ((0.0, 0.0, 1.0, 1.0), True),
        ((0.1, 0.2, 0.3, 0.4), True),
        ((-0.1, 0.0, 0.2, 0.2), False),
        ((0.9, 0.0, 0.2, 0.2), False),
        ((0.0, 0.0, 0.0, 0.2), False),
    ],
)
def test_normalized_rect_validation(values: tuple[float, ...], valid: bool) -> None:
    if valid:
        rect = NormalizedRect(*values)
        assert rect.to_pixels(100, 50)[0] >= 0
    else:
        with pytest.raises(ValueError):
            NormalizedRect(*values)


def test_resource_limits_must_be_positive() -> None:
    with pytest.raises(ValueError):
        ResourceLimits(max_pdf_pages=0)


def test_plan_dpi_is_restricted() -> None:
    with pytest.raises(ValueError):
        SanitizationPlan(SanitizationProfile.SECURE_FLATTEN, "out.pdf", [], 144)


def test_state_machine_requires_order_and_verification() -> None:
    machine = JobStateMachine()
    with pytest.raises(InvalidTransitionError):
        machine.transition(JobState.COMPLETED)
    for state in (
        JobState.VALIDATING,
        JobState.INSPECTING,
        JobState.REVIEW_REQUIRED,
        JobState.PLAN_READY,
        JobState.SANITIZING,
        JobState.VERIFYING,
        JobState.COMPLETED,
    ):
        machine.transition(state)
    assert machine.state is JobState.COMPLETED


def test_state_machine_allows_error_states() -> None:
    machine = JobStateMachine()
    machine.transition(JobState.VALIDATING)
    machine.transition(JobState.REJECTED)
    with pytest.raises(InvalidTransitionError):
        machine.transition(JobState.INSPECTING)


def test_state_machine_rejects_completion_if_verification_flag_is_missing() -> None:
    machine = JobStateMachine(
        state=JobState.VERIFYING,
        verification_entered=False,
    )
    with pytest.raises(InvalidTransitionError, match="without verification"):
        machine.transition(JobState.COMPLETED)
