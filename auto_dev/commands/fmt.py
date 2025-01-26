"""This module contains the logic for the fmt command."""

import rich_click as click

from auto_dev.fmt import multi_thread_fmt, single_thread_fmt
from auto_dev.base import build_cli
from auto_dev.utils import get_paths


cli = build_cli()


@cli.command()
@click.option(
    "-p",
    "--path",
    help="Path to code to format. If not provided will format all packages.",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
    default=None,
)
@click.option(
    "-co",
    "--changed-only",
    help="Only lint the files that have changed.",
    is_flag=True,
    default=False,
)
@click.pass_context
def fmt(ctx, path, changed_only) -> None:
    """Format code using the configured formatters.

    Optional Parameters:
        path: Path to code to format. Default: None
            - If not provided, formats all packages
            - Can be file or directory path
            - Must exist in workspace
        changed_only: Only format files that have changed. Default: False
            - Uses git to detect changes
            - Only formats files with uncommitted changes
            - Ignores untracked files

    Usage:
        Format all packages:
            adev fmt

        Format specific path:
            adev fmt -p ./my_package

        Format only changed files:
            adev fmt --changed-only

        Format specific path and only changed files:
            adev fmt -p ./my_package --changed-only

    Notes
    -----
        - Uses multiple formatters:
            - black: Python code formatting
            - isort: Import sorting
            - docformatter: Docstring formatting
        - Supports parallel processing for faster formatting
        - Shows formatting statistics on completion
        - Exits with error if any formatting fails
        - Can be integrated into pre-commit hooks
        - Respects .gitignore patterns
    """
    verbose = ctx.obj["VERBOSE"]
    num_processes = ctx.obj["NUM_PROCESSES"]
    logger = ctx.obj["LOGGER"]
    remote = ctx.obj["REMOTE"]
    logger.info("Formatting Open Autonomy Packages...")
    logger.info(f"Remote: {remote}")
    paths = get_paths(path, changed_only)
    logger.info(f"Formatting {len(paths)} files...")
    if num_processes > 1:
        results = multi_thread_fmt(paths, verbose, num_processes, remote=remote)
    else:
        results = single_thread_fmt(paths, verbose, logger, remote=remote)
    passed = sum(results.values())
    failed = len(results) - passed
    logger.info(f"Formatting completed with {passed} passed and {failed} failed")
    if failed > 0:
        msg = "Formatting failed!"
        raise click.ClickException(msg)
