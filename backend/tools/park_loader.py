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
    """
    Convert the triple nested multipolygon into a flat list of coordinate pairs.

    Parameters
    ----------
    geojson_multipolygon : list[list[list[list[float]]]]
        The multipolygon structure used in a geojson file.

    Returns
    -------
    list[tuple[float, float]]
        The flattened list of coordinate pairs.
    """
    return [(k[0], k[1]) for i in geojson_multipolygon for j in i for k in j]


def get_centroid(
    coordinates: Sequence[tuple[float, float]],
) -> tuple[float, float]:
    """
    Calculate the arithmetic mean of a sequence of coordinate pairs.

    Parameters
    ----------
    coordinates : Sequence[tuple[float, float]]
        Non-empty coordinate pairs, with each pair containing an x and y value.

    Returns
    -------
    tuple[float, float]
        The mean x and y values.
    """
    x_sum: float = 0
    y_sum: float = 0
    count: int = len(coordinates)
    for c in coordinates:
        x_sum += c[0]
        y_sum += c[1]
    return x_sum / count, y_sum / count


def to_park(feature: dict[str, Any]) -> Park:
    """
    Convert a GeoJSON feature into a park model.

    Parameters
    ----------
    feature : dict[str, Any]
        A GeoJSON feature containing park properties and multipolygon geometry.

    Returns
    -------
    Park
        A park model populated from the feature.
    """
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
    """
    Load park models from a GeoJSON file.

    Parameters
    ----------
    path : Path, default=DEFAULT_PATH
        Path to the GeoJSON file.

    Returns
    -------
    list[Park]
        Parks converted from the file's features.
    """
    data: dict[str, Any] = json.loads(path.read_text("utf-8"))
    return [to_park(feature) for feature in data["features"]]
