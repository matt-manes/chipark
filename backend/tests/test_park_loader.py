import json
from pathlib import Path
from typing import Any

from backend.models.park import Park
from backend.tools.park_loader import (
    flatten_multipolygon,
    get_centroid,
    load_from_geojson,
    to_park,
)


def test_flatten_multipolygon_returns_all_coordinates() -> None:
    coordinates: list[list[list[list[float]]]] = [
        [[[0.0, 0.0], [1.0, 0.0]]],
        [[[2.0, 2.0], [3.0, 2.0]]],
    ]

    flattened_coordinates: list[tuple[float, float]] = flatten_multipolygon(
        coordinates
    )

    assert flattened_coordinates == [
        (0.0, 0.0),
        (1.0, 0.0),
        (2.0, 2.0),
        (3.0, 2.0),
    ]


def test_get_centroid_averages_coordinates() -> None:
    coordinates: list[tuple[float, float]] = [
        (0.0, 0.0),
        (2.0, 0.0),
        (2.0, 2.0),
        (0.0, 2.0),
    ]

    centroid: tuple[float, float] = get_centroid(coordinates)

    assert centroid == (1.0, 1.0)


def test_to_park_maps_properties_and_centroid() -> None:
    feature: dict[str, Any] = {
        "geometry": {
            "coordinates": [
                [[[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0]]]
            ]
        },
        "properties": {
            "park_no": "P001",
            "park": "Sample Park",
            "location": "123 Main Street",
            "zip": "60601",
            "acres": "10",
            "ward": "1.0",
            "park_class": "NEIGHBORHOOD PARK",
            "label": "Sample Park",
        },
    }

    park: Park = to_park(feature)

    assert park == Park(
        park_no="P001",
        name="Sample Park",
        street="123 Main Street",
        zip_code="60601",
        acres="10",
        ward="1",
        park_class="NEIGHBORHOOD PARK",
        label="Sample Park",
        lat=1.0,
        lon=1.0,
    )


def test_load_from_geojson_reads_features(tmp_path: Path) -> None:
    feature: dict[str, Any] = {
        "geometry": {
            "coordinates": [
                [[[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0]]]
            ]
        },
        "properties": {
            "park_no": "P001",
            "park": "Sample Park",
            "location": "123 Main Street",
            "zip": "60601",
            "acres": "10",
            "ward": "1",
            "park_class": "NEIGHBORHOOD PARK",
            "label": "Sample Park",
        },
    }
    geojson: dict[str, Any] = {"features": [feature]}
    geojson_path: Path = tmp_path / "parks.geojson"
    geojson_path.write_text(json.dumps(geojson))

    parks: list[Park] = load_from_geojson(geojson_path)

    assert len(parks) == 1
    assert parks[0].name == "Sample Park"
