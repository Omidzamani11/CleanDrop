from __future__ import annotations

from dataclasses import dataclass

from cleandrop.domain.errors import InvalidTransitionError
from cleandrop.domain.models import JobState

_ALLOWED: dict[JobState, frozenset[JobState]] = {
    JobState.CREATED: frozenset({JobState.VALIDATING, JobState.CANCELLED}),
    JobState.VALIDATING: frozenset(
        {JobState.INSPECTING, JobState.REJECTED, JobState.FAILED, JobState.CANCELLED}
    ),
    JobState.INSPECTING: frozenset({JobState.REVIEW_REQUIRED, JobState.FAILED, JobState.CANCELLED}),
    JobState.REVIEW_REQUIRED: frozenset({JobState.PLAN_READY, JobState.CANCELLED, JobState.FAILED}),
    JobState.PLAN_READY: frozenset({JobState.SANITIZING, JobState.CANCELLED, JobState.FAILED}),
    JobState.SANITIZING: frozenset({JobState.VERIFYING, JobState.CANCELLED, JobState.FAILED}),
    JobState.VERIFYING: frozenset(
        {
            JobState.COMPLETED,
            JobState.COMPLETED_WITH_WARNINGS,
            JobState.FAILED,
            JobState.CANCELLED,
        }
    ),
    JobState.COMPLETED: frozenset(),
    JobState.COMPLETED_WITH_WARNINGS: frozenset(),
    JobState.REJECTED: frozenset(),
    JobState.FAILED: frozenset(),
    JobState.CANCELLED: frozenset(),
}


@dataclass(slots=True)
class JobStateMachine:
    state: JobState = JobState.CREATED
    verification_entered: bool = False

    def transition(self, target: JobState) -> JobState:
        if target not in _ALLOWED[self.state]:
            raise InvalidTransitionError(f"Cannot transition from {self.state} to {target}")
        if target is JobState.VERIFYING:
            self.verification_entered = True
        if target in {
            JobState.COMPLETED,
            JobState.COMPLETED_WITH_WARNINGS,
        } and (not self.verification_entered or self.state is not JobState.VERIFYING):
            raise InvalidTransitionError("A job cannot complete without verification")
        self.state = target
        return self.state
