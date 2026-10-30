import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

COVERAGE_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("run", "-m", "pytest", "-s"),
    ("report", "--include=./*"),
    ("html", "--include=./*"),
)


def find_repository_root(start_directory: Path) -> Path:
    """
    Find the repository containing the backend project.

    Parameters
    ----------
    start_directory : Path
        Directory from which to search its parent directories.

    Returns
    -------
    Path
        Repository root containing ``backend/pyproject.toml``.

    Raises
    ------
    FileNotFoundError
        If no backend project is found in the directory ancestry.
    """
    directory: Path
    for directory in (start_directory, *start_directory.parents):
        backend_directory: Path = directory / "backend"
        if (backend_directory / "pyproject.toml").is_file():
            return directory
    raise FileNotFoundError(
        f"Could not find the repository root from '{start_directory}'."
    )


def run_coverage_command(arguments: Sequence[str], working_directory: Path) -> int:
    """
    Run a Coverage command from the repository root.

    Parameters
    ----------
    arguments : Sequence[str]
        Arguments passed to ``python -m coverage``.
    working_directory : Path
        Directory used as the command's working directory.

    Returns
    -------
    int
        Exit status returned by Coverage.
    """
    command: list[str] = [sys.executable, "-m", "coverage", *arguments]
    result: subprocess.CompletedProcess[bytes] = subprocess.run(
        command,
        cwd=working_directory,
        check=False,
    )
    return result.returncode


def main() -> int:
    """
    Run pytest under Coverage, then print and export coverage reports.

    Returns
    -------
    int
        The pytest exit status when tests fail, otherwise the first report
        command's non-zero exit status, or zero when every command succeeds.
    """
    repository_root: Path = find_repository_root(Path.cwd())
    exit_codes: list[int] = [
        run_coverage_command(arguments, repository_root)
        for arguments in COVERAGE_COMMANDS
    ]

    if exit_codes[0] != 0:
        return exit_codes[0]
    if exit_codes[1] != 0:
        return exit_codes[1]
    return exit_codes[2]
