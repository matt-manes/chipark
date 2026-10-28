from pathlib import Path

import pytest

from backend.tools import config as config_module
from backend.tools.config import Config, ConfigError


@pytest.fixture(autouse=True)
def reset_config_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Config, "_instance", None)
    monkeypatch.delenv("database", raising=False)


def test_loads_database_from_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path: Path = tmp_path / "config.toml"
    config_path.write_text('database = "sqlite"\n', encoding="utf-8")
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    config: Config = Config()

    assert config.database == "sqlite"


def test_environment_value_overrides_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path: Path = tmp_path / "config.toml"
    config_path.write_text('database = "sqlite"\n', encoding="utf-8")
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)
    monkeypatch.setenv("database", "postgresql")

    config: Config = Config()

    assert config.database == "postgresql"


def test_reuses_singleton_without_reloading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path: Path = tmp_path / "config.toml"
    config_path.write_text('database = "sqlite"\n', encoding="utf-8")
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    first_config: Config = Config()
    config_path.write_text('database = "postgresql"\n', encoding="utf-8")
    second_config: Config = Config()

    assert second_config is first_config
    assert second_config.database == "sqlite"


def test_raises_when_field_is_missing_from_toml_and_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path: Path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    with pytest.raises(ConfigError, match="database.*missing"):
        Config()


def test_rejects_invalid_environment_value_for_boolean_field() -> None:
    with pytest.raises(ConfigError, match="invalid value"):
        Config._parse_environment_value("enabled", "yes", bool)  # type: ignore


def test_rejects_unsupported_environment_field_type() -> None:
    with pytest.raises(ConfigError, match="unsupported type"):
        Config._parse_environment_value("options", "value", list)  # type: ignore
