import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ..models.park import Park

DEFAULT_PATH: Path = (
    Path(__file__).parent.parent / "data" / "CPD_Parks_20261019.geojson"
)


def flatten_multipolygon(
    geojson_multipolygon: list[list[list[list[float]]]],
) -> list[tuple[float, float]]:
    return [(k[0], k[1]) for i in geojson_multipolygon for j in i for k in j]


def get_centroid(
    coordinates: Sequence[tuple[float, float]],
) -> tuple[float, float]:
    x_sum: float = 0
    y_sum: float = 0
    count: int = len(coordinates)
    for c in coordinates:
        x_sum += c[0]
        y_sum += c[1]
    return x_sum / count, y_sum / count


def to_park(feature: dict[str, Any]) -> Park:
    x, y = get_centroid(flatten_multipolygon(feature["geometry"]["coordinates"]))
    properties: dict[str, str] = feature["properties"]
    return Park(
        properties["park_no"],
        properties["park"],
        properties["location"],
        properties["zip"],
        properties["acres"],
        properties["ward"].removesuffix(".0"),
        properties["park_class"],
        properties["label"],
        y,
        x,
    )


def load_from_geojson(path: Path = DEFAULT_PATH) -> list[Park]:
    data: dict[str, Any] = json.loads(path.read_text())
    return [to_park(feature) for feature in data["features"]]
