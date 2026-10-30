from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path
from threading import Lock
from typing import ClassVar, Self, get_type_hints

CONFIG_PATH: Path = Path(__file__).resolve().parent.parent / "config.toml"


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
    Load application settings once from TOML and matching environment variables.

    Each annotated dataclass field is loaded from the matching TOML key and may
    be overridden by an environment variable with the same name.

    Notes
    -----
    Configuration is loaded when the singleton is first accessed. Fields are
    immutable after initialization.
    """

    _instance: ClassVar[Self | None] = None
    _lock: ClassVar[Lock] = Lock()

    database: str

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
        Load declared fields from TOML and matching environment variables.

        Raises
        ------
        ConfigError
            If a declared field is missing from both configuration sources.
        """
        settings: dict[str, object] = tomllib.loads(
            CONFIG_PATH.read_text(encoding="utf-8")
        )
        field_types: dict[str, object] = get_type_hints(type(self))

        for config_field in fields(self):
            field_name: str = config_field.name
            if field_name in os.environ:
                field_type: object = field_types[field_name]
                value: object = self._parse_environment_value(
                    field_name, os.environ[field_name], field_type
                )
            elif field_name in settings:
                value = settings[field_name]
            else:
                raise ConfigError(
                    f"Configuration field '{field_name}' is missing from "
                    f"{CONFIG_PATH} and the environment."
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
