import subprocess
from collections.abc import Sequence
from pathlib import Path

from .run_coverage import find_repository_root

QUALITY_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("isort", "."),
    ("black", "."),
    ("ruff", "check"),
)


def run_quality_command(arguments: Sequence[str], working_directory: Path) -> int:
    """
    Run a project command through uv.

    Parameters
    ----------
    arguments : Sequence[str]
        Command and arguments passed after ``uv run``.
    working_directory : Path
        Backend project directory used as the command's working directory.

    Returns
    -------
    int
        Exit status returned by the command.
    """
    command: list[str] = ["uv", "run", *arguments]
    result: subprocess.CompletedProcess[bytes] = subprocess.run(
        command,
        cwd=working_directory,
        check=False,
    )
    return result.returncode


def main() -> int:
    """
    Run isort, Black, and Ruff sequentially.

    Returns
    -------
    int
        The first non-zero command exit status, or zero when all succeed.
    """
    repository_root: Path = find_repository_root(Path.cwd())
    backend_directory: Path = repository_root / "backend"

    for arguments in QUALITY_COMMANDS:
        exit_code: int = run_quality_command(arguments, backend_directory)
        if exit_code != 0:
            return exit_code
    return 0
