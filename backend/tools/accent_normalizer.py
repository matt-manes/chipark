import unicodedata


class AccentNormalizer:
    """Normalize accented Latin characters to unaccented ASCII equivalents."""

    @staticmethod
    def remove_accents(value: str) -> str:
        """Remove accents from characters with ASCII base-letter equivalents.

        Parameters
        ----------
        value : str
            Text to normalize.

        Returns
        -------
        str
            Text with decomposable accents removed. Characters without an
            ASCII equivalent are omitted.
        """
        decomposed_value: str = unicodedata.normalize("NFKD", value)
        return decomposed_value.encode("ascii", "ignore").decode("ascii")
