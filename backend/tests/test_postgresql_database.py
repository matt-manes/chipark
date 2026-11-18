from types import SimpleNamespace

import pytest
from sqlalchemy import URL
from sqlalchemy import create_engine as sqlalchemy_create_engine
from sqlalchemy.engine import Engine

from backend.repositories import postgresql_database
from backend.repositories.postgresql_database import PostgresqlDatabase


def test_database_uses_configured_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_urls: list[URL] = []

    def create_engine_stub(url: URL) -> Engine:
        captured_urls.append(url)
        return sqlalchemy_create_engine("sqlite:///:memory:")

    monkeypatch.setattr(postgresql_database, "create_engine", create_engine_stub)
    monkeypatch.setattr(
        postgresql_database,
        "Config",
        lambda: SimpleNamespace(
            CHIPARK_PG_USER="chipark_user", CHIPARK_PG_PASS="p@ssword"
        ),
    )

    database: PostgresqlDatabase = PostgresqlDatabase(
        "postgresql+psycopg2://localhost:5432/chipark"
    )

    assert captured_urls[0].username == "chipark_user"
    assert captured_urls[0].password == "p@ssword"
    assert captured_urls[0].database == "chipark"
    database.close()


def test_database_uses_explicit_credentials_over_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_urls: list[URL] = []

    def create_engine_stub(url: URL) -> Engine:
        captured_urls.append(url)
        return sqlalchemy_create_engine("sqlite:///:memory:")

    monkeypatch.setattr(postgresql_database, "create_engine", create_engine_stub)
    monkeypatch.setattr(
        postgresql_database,
        "Config",
        lambda: SimpleNamespace(
            CHIPARK_PG_USER="application-user",
            CHIPARK_PG_PASS="application-password",
        ),
    )

    database: PostgresqlDatabase = PostgresqlDatabase(
        "postgresql+psycopg2://localhost:5432/chipark_test",
        username="test-user",
        password="test-password",
    )

    assert captured_urls[0].username == "test-user"
    assert captured_urls[0].password == "test-password"
    database.close()


def test_database_requires_configured_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        postgresql_database,
        "Config",
        lambda: SimpleNamespace(CHIPARK_PG_USER=None, CHIPARK_PG_PASS=None),
    )

    with pytest.raises(ValueError, match="CHIPARK_PG_USER"):
        PostgresqlDatabase("postgresql+psycopg2://localhost:5432/chipark")


def test_database_rejects_non_postgresql_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        postgresql_database,
        "Config",
        lambda: SimpleNamespace(
            CHIPARK_PG_USER="chipark_user", CHIPARK_PG_PASS="password"
        ),
    )

    with pytest.raises(ValueError, match="CHIPARK_PG_URL"):
        PostgresqlDatabase("sqlite:///chipark.sqlite3")
