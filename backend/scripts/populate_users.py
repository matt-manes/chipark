import json
import secrets
from pathlib import Path

from rich.progress import track

from backend.models.user import AuthenticatedUser
from backend.repositories import Database, DatabaseFactory
from backend.services.auth_service import AuthService
from backend.tools.config import Config

DATA_PATH: Path = Path(__file__).resolve().parents[1] / "data"
SAMPLE_USERS_PATH: Path = DATA_PATH / "sample-users.json"
REGISTERED_USERS_PATH: Path = DATA_PATH / "registered-sample-users.json"


class SampleUserPopulator:
    """Register synthetic users and save their generated credentials."""

    def __init__(self) -> None:
        """Create the authentication service for the configured database."""
        self._database: Database = DatabaseFactory.get_database(
            Config().CHIPARK_DATABASE
        )
        self._auth_service: AuthService = AuthService(self._database.session_factory)

    def populate(self) -> int:
        """
        Register all sample users and save their credentials.

        Returns
        -------
        int
            Number of accounts registered.
        """
        self._auth_service.bootstrap_admin(
            Config().CHIPARK_ADMIN_EMAIL, Config().CHIPARK_ADMIN_PASSWORD
        )
        try:
            sample_users: list[dict[str, str]] = json.loads(
                SAMPLE_USERS_PATH.read_text(encoding="utf-8")
            )
            registered_users: list[dict[str, str | int]] = [
                self._register_user(sample_user["email"])
                for sample_user in track(sample_users, "Registering users...")
            ]
            REGISTERED_USERS_PATH.write_text(
                json.dumps(registered_users, indent=2),
                encoding="utf-8",
            )
            return len(registered_users)
        finally:
            self._database.close()

    def _register_user(self, email: str) -> dict[str, str | int]:
        """Register one account and preserve its generated credentials.

        Parameters
        ----------
        email : str
            Email address for the account to register.

        Returns
        -------
        dict of str to str or int
            Registered account's email, ID, and generated password.
        """
        password: str = secrets.token_urlsafe(18)
        authenticated_user: AuthenticatedUser = self._auth_service.register(
            email, password
        )
        self._auth_service.logout(authenticated_user.access_token)
        return {
            "email": authenticated_user.user.email,
            "user_id": authenticated_user.user.user_id,
            "password": password,
        }


def main() -> None:
    """Populate the database with the configured sample users."""
    if REGISTERED_USERS_PATH.exists():
        print("Error: Registered users data file exists.")
        print("Refusing to overwrite.")
        return
    count: int = SampleUserPopulator().populate()
    print(f"Registered {count} sample users.")
    print(f"Login data written to '{REGISTERED_USERS_PATH}'.")


if __name__ == "__main__":
    main()
