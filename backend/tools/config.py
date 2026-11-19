from __future__ import annotations

import os
from dataclasses import MISSING, dataclass, fields
from pathlib import Path
from threading import Lock
from typing import ClassVar, Self, get_type_hints

from dotenv import dotenv_values

DOTENV_PATH: Path = Path(__file__).resolve().parent.parent / ".env"


class ConfigError(ValueError):
    """Error raised when application configuration is missing or invalid."""


class EnvValueParser:
    """Convert environment variable strings to declared configuration types."""

    @staticmethod
    def parse(value: str, field_type: object) -> object:
        """
        Parse an environment value as the requested field type.

        Parameters
        ----------
        value : str
            Raw environment variable value.
        field_type : object
            Declared type of the configuration field.

        Returns
        -------
        object
            Parsed value matching ``field_type``.

        Raises
        ------
        ValueError
            If ``value`` cannot be parsed as the requested type.
        TypeError
            If ``field_type`` is unsupported.
        """
        if field_type == str | None:
            return value or None
        if field_type is bool:
            normalized_value: str = value.casefold()
            if normalized_value == "true":
                return True
            if normalized_value == "false":
                return False
            raise ValueError("Expected 'true' or 'false'.")
        if field_type is str:
            return value
        if field_type is int:
            return int(value)
        if field_type is float:
            return float(value)
        raise TypeError(f"Unsupported environment field type: {field_type}.")


@dataclass(frozen=True, init=False)
class Config:
    """
    Load application settings once from the process environment and ``.env``.

    Process environment values are loaded first. Values from ``.env`` override
    them when present.

    Notes
    -----
    Configuration is loaded when the singleton is first accessed. Fields are
    immutable after initialization.
    """

    _instance: ClassVar[Self | None] = None
    _lock: ClassVar[Lock] = Lock()
    CHIPARK_DATABASE: str
    CHIPARK_CONDITIONS_TTL: int
    CHIPARK_CORS_ALLOW_LIST: str
    CHIPARK_GOOGLE_FRONTEND_REDIRECT_URL: str
    CHIPARK_PG_URL: str
    CHIPARK_ADMIN_EMAIL: str | None = None
    CHIPARK_ADMIN_PASSWORD: str | None = None
    CHIPARK_WEATHERAPI_KEY: str | None = None
    CHIPARK_PG_USER: str | None = None
    CHIPARK_PG_PASS: str | None = None
    CHIPARK_GOOGLE_CLIENT_ID: str | None = None
    CHIPARK_GOOGLE_CLIENT_SECRET: str | None = None
    CHIPARK_GOOGLE_REDIRECT_URI: str | None = None
    CHIPARK_TEST_PG_URL: str | None = None
    CHIPARK_TEST_PG_USER: str | None = None
    CHIPARK_TEST_PG_PASSWORD: str | None = None
    OTEL_SERVICE_NAME: str | None = None
    OTEL_RESOURCE_ATTRIBUTES: str | None = None
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    OTEL_EXPORTER_OTLP_HEADERS: str | None = None
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT: str | None = None
    OTEL_EXPORTER_OTLP_TRACES_HEADERS: str | None = None
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT: str | None = None
    OTEL_EXPORTER_OTLP_METRICS_HEADERS: str | None = None
    OTEL_EXPORTER_OTLP_LOGS_ENDPOINT: str | None = None
    OTEL_EXPORTER_OTLP_LOGS_HEADERS: str | None = None

    @property
    def cors_allow_origins(self) -> tuple[str, ...]:
        """Parse the comma-separated CORS origin allow-list.

        Returns
        -------
        tuple[str, ...]
            Non-empty, whitespace-trimmed origins.
        """
        return tuple(
            origin.strip()
            for origin in self.CHIPARK_CORS_ALLOW_LIST.replace(" ", "").split(",")
            if origin.strip()
        )

    def __new__(cls) -> Self:
        """
        Return the shared configuration instance.

        Returns
        -------
        Config
            The lazily initialized singleton configuration.
        """
        with cls._lock:
            if cls._instance is None:
                instance: Config = object.__new__(cls)
                instance._load()
                cls._instance = instance
            return cls._instance

    def _load(self) -> None:
        """
        Load declared fields from the process environment and ``.env``.

        Raises
        ------
        ConfigError
            If a required field is missing or a value is invalid.
        """
        field_types: dict[str, object] = get_type_hints(type(self))
        dotenv_settings: dict[str, str | None] = dotenv_values(DOTENV_PATH)
        for config_field in fields(self):
            field_name: str = config_field.name
            dotenv_value: str | None = dotenv_settings.get(field_name)
            if dotenv_value is not None:
                raw_value: str = dotenv_value
            elif field_name in os.environ:
                raw_value = os.environ[field_name]
            elif config_field.default is not MISSING:
                object.__setattr__(self, field_name, config_field.default)
                continue
            else:
                raise ConfigError(
                    f"Configuration field '{field_name}' is missing from "
                    "the process environment and .env file."
                )

            value: object = self._parse_environment_value(
                field_name, raw_value, field_types[field_name]
            )
            object.__setattr__(self, field_name, value)

    @staticmethod
    def _parse_environment_value(
        field_name: str, raw_value: str, field_type: object
    ) -> object:
        """
        Convert an environment value to a declared field type.

        Parameters
        ----------
        field_name : str
            Name of the configuration field being overridden.
        raw_value : str
            Environment variable value.
        field_type : object
            Declared type of the configuration field.

        Returns
        -------
        object
            Environment value converted to the declared type.

        Raises
        ------
        ConfigError
            If the value cannot be converted or the type is unsupported.
        """
        try:
            return EnvValueParser.parse(raw_value, field_type)
        except ValueError as error:
            raise ConfigError(
                f"Environment variable '{field_name}' has an invalid value."
            ) from error
        except TypeError as error:
            raise ConfigError(
                f"Environment overrides for '{field_name}' use an unsupported type."
            ) from error
