import pytest

from backend.tools.accent_normalizer import AccentNormalizer


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("HONORÉ", "HONORE"),
        ("Crème brûlée", "Creme brulee"),
        ("No accents", "No accents"),
        ("", ""),
        ("東京", ""),
    ],
)
def test_remove_accents(value: str, expected: str) -> None:
    normalized_value: str = AccentNormalizer.remove_accents(value)

    assert normalized_value == expected
