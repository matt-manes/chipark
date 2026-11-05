from backend.models.user import UserCredentials
from backend.repositories.auth_repository import AuthRepository
from backend.repositories.database import Database


def test_get_credentials_by_email_returns_none_for_unknown_email(
    database: Database,
) -> None:
    repository: AuthRepository = AuthRepository(database.session_factory)

    credentials: UserCredentials | None = repository.get_credentials_by_email(
        "missing@example.com"
    )

    assert credentials is None
