import json
import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path.cwd()))
from backend.models.park import Park

DEFAULT_PATH: Path = (
    Path(__file__).parent.parent / "data" / "CPD_Parks_20261019.geojson"
)


def get_approx_centroid(
    geojson_multipolygon: list[list[list[list[float]]]],
) -> tuple[float, float]:
    x_sum: float = 0
    y_sum: float = 0
    count: int = 0
    for i in geojson_multipolygon:
        for j in i:
            for k in j:
                x_sum += k[0]
                y_sum += k[1]
                count += 1
    return x_sum / count, y_sum / count


def to_park(feature: dict[str, Any]) -> Park:
    x, y = get_approx_centroid(feature["geometry"]["coordinates"])
    properties: dict[str, str] = feature["properties"]
    return Park(
        properties["park_no"],
        properties["park"],
        properties["location"],
        properties["zip"],
        properties["acres"],
        properties["ward"],
        properties["park_class"],
        properties["park_class"],
        y,
        x,
    )


def load_from_geojson(path: Path = DEFAULT_PATH) -> list[Park]:
    data: dict[str, Any] = json.loads(path.read_text())
    return [to_park(feature) for feature in data["features"]]
