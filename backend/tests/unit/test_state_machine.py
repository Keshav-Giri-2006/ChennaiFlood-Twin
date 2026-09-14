import pytest

from app.models.simulation import STATUS_PROGRESS, InvalidTransitionError, SimulationStatus as S, ensure_transition

HAPPY_PATH = [S.CREATED, S.VALIDATING, S.PREPARING, S.RUNNING, S.PROCESSING, S.COMPLETED]


def test_happy_path_transitions_are_allowed():
    for current, target in zip(HAPPY_PATH, HAPPY_PATH[1:]):
        ensure_transition(current, target)


@pytest.mark.parametrize("status", HAPPY_PATH[:-1])
def test_any_active_state_can_fail(status):
    ensure_transition(status, S.FAILED)


@pytest.mark.parametrize(
    "current,target",
    [(S.CREATED, S.RUNNING), (S.RUNNING, S.COMPLETED), (S.COMPLETED, S.FAILED), (S.FAILED, S.COMPLETED), (S.PROCESSING, S.RUNNING)],
)
def test_illegal_transitions_are_rejected(current, target):
    with pytest.raises(InvalidTransitionError):
        ensure_transition(current, target)


def test_stage_progress_is_monotonic():
    values = [STATUS_PROGRESS[s] for s in HAPPY_PATH]
    assert values == sorted(values)
    assert values[0] == 0 and values[-1] == 100
