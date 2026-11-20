from dataclasses import fields
from pathlib import Path
from typing import Any

from rich import print
from rich.prompt import Confirm

from backend.tools.config import DOTENV_PATH, Config


class EnvironmentFileGenerator:
    """Create a dotenv file containing every declared application setting."""

    def __init__(self) -> None:
        """Initialize the generator with the configured dotenv path."""
        self._dotenv_path: Path = DOTENV_PATH
        self._defaults: dict[str, Any] = {
            "CHIPARK_DATABASE": "sqlite",
            "CHIPARK_CONDITIONS_TTL": 900,
            "CHIPARK_CORS_ALLOW_LIST": "http://localhost:5173",
            "CHIPARK_RATE_LIMIT_AUTH": "5/minute",
            "CHIPARK_RATE_LIMIT_GLOBAL": "60/minute",
        }

    def generate(self) -> bool:
        """
        Create the dotenv file, asking before replacing an existing file.

        Returns
        -------
        bool
            Whether the file was created or replaced.
        """
        if self._dotenv_path.exists() and not Confirm.ask(
            f"[yellow]{self._dotenv_path} already exists. Overwrite it?[/yellow]",
            default=False,
        ):
            print("[dim]Kept the existing .env file.[/dim]")
            return False

        self._dotenv_path.write_text(self._contents(), encoding="utf-8")
        print(f"[green]Created {self._dotenv_path}.[/green]")
        return True

    def _contents(self) -> str:
        """Build dotenv entries from the declared Config fields."""
        values: list[str] = []
        for config_field in fields(Config):
            # default: str = "sqlite" if config_field.name == "CHIPARK_DATABASE" else ""
            values.append(
                f"{config_field.name}={self._defaults.get(config_field.name, '')}"
            )
        return "\n".join(values) + "\n"


def main() -> None:
    """Run the dotenv file generator."""
    EnvironmentFileGenerator().generate()


if __name__ == "__main__":
    main()
