from backend.models.park import Park
from backend.repositories.park_repository import ParkRepository


def test_add_assigns_generated_id(
    park_repository: ParkRepository, sample_park: Park, sample_park2: Park
) -> None:
    saved_park: Park = park_repository.add(sample_park)
    assert saved_park.park_id > 0

    saved_second_park: Park = park_repository.add(sample_park2)
    assert saved_second_park.park_id > saved_park.park_id


def test_add_preserves_park_fields(
    park_repository: ParkRepository, sample_park: Park
) -> None:
    saved_park: Park = park_repository.add(sample_park)

    assert saved_park == Park(
        park_no=sample_park.park_no,
        name=sample_park.name,
        street=sample_park.street,
        zip_code=sample_park.zip_code,
        acres=sample_park.acres,
        ward=sample_park.ward,
        park_class=sample_park.park_class,
        label=sample_park.label,
        lat=sample_park.lat,
        lon=sample_park.lon,
        park_id=saved_park.park_id,
    )


def test_add_removes_accents_from_selected_text_fields(
    park_repository: ParkRepository,
) -> None:
    park: Park = Park(
        park_no="P003",
        name="HONORÉ Park",
        street="Rue HONORÉ",
        zip_code="60601",
        acres="10",
        ward="1",
        park_class="NEIGHBORHOOD PARK",
        label="HONORÉ",
        lat=41.88,
        lon=-87.63,
    )

    saved_park: Park = park_repository.add(park)

    assert saved_park.name == "HONORE Park"
    assert saved_park.street == "Rue HONORE"
    assert saved_park.label == "HONORE"


def test_get_all_returns_parks_in_id_order(
    park_repository: ParkRepository, sample_park: Park, sample_park2: Park
) -> None:
    first_park: Park = park_repository.add(sample_park)
    second_park: Park = park_repository.add(sample_park2)

    assert park_repository.get_all() == [first_park, second_park]


def test_get_all_returns_empty_list_when_no_parks(
    park_repository: ParkRepository,
) -> None:
    assert park_repository.get_all() == []
