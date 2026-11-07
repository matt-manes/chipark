from dataclasses import replace

import pytest

from backend.models.conditions import Conditions
from backend.models.park import Park
from backend.repositories.conditions_repository import ConditionsRepository
from backend.repositories.park_repository import ParkRepository


def test_add_and_get_conditions_for_park(
    conditions_repository: ConditionsRepository,
    park_repository: ParkRepository,
    sample_park: Park,
    sample_conditions: Conditions,
) -> None:
    saved_park: Park = park_repository.add(sample_park)

    saved_conditions: Conditions = conditions_repository.add(
        saved_park.park_id, sample_conditions
    )
    retrieved_conditions: Conditions | None = conditions_repository.get_for_park(
        saved_park.park_id
    )

    assert saved_conditions == sample_conditions
    assert retrieved_conditions == sample_conditions


def test_get_conditions_returns_none_for_missing_park_entry(
    conditions_repository: ConditionsRepository,
) -> None:
    conditions: Conditions | None = conditions_repository.get_for_park(42)

    assert conditions is None


def test_update_replaces_conditions_for_park(
    conditions_repository: ConditionsRepository,
    park_repository: ParkRepository,
    sample_park: Park,
    sample_conditions: Conditions,
) -> None:
    saved_park: Park = park_repository.add(sample_park)
    conditions_repository.add(saved_park.park_id, sample_conditions)
    refreshed_conditions: Conditions = replace(
        sample_conditions, temp_f=80.0, condition="Cloudy"
    )

    result: Conditions = conditions_repository.update(
        saved_park.park_id, refreshed_conditions
    )

    assert result == refreshed_conditions
    assert (
        conditions_repository.get_for_park(saved_park.park_id) == refreshed_conditions
    )


def test_update_raises_when_park_has_no_cached_conditions(
    conditions_repository: ConditionsRepository,
    sample_conditions: Conditions,
) -> None:
    with pytest.raises(LookupError, match="Conditions for park 42 were not found"):
        conditions_repository.update(42, sample_conditions)
