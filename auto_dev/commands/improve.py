"""Group to implement improvements."""

import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import rich_click as click

from auto_dev.base import build_cli
from auto_dev.constants import CheckResult
from auto_dev.commands.repo import TEMPLATES, RepoScaffolder


cli = build_cli()


def get_remote_owner():
    """Get the remote owner of the repo."""
    try:
        remote_url = subprocess.check_output(["git", "config", "--get", "remote.origin.url"]).decode().strip()
        parsed_url = urlparse(remote_url)
        path_parts = parsed_url.path.strip("/").split("/")
        return path_parts[-2]
    except subprocess.CalledProcessError:
        return None


@cli.command()
@click.option(
    "-p",
    "--path",
    help="Path to repo to verify format. Default is current directory.",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
    default=None,
)
@click.option(
    "-t",
    "--type-of-repo",
    help="Type of repo to scaffold",
    type=click.Choice(TEMPLATES),
    required=True,
    default="autonomy",
)
@click.option(
    "--author",
    help="Author of the repo",
    type=str,
    required=True,
)
@click.option(
    "--name",
    help="Name of the repo",
    type=str,
    required=True,
)
@click.option(
    "-y",
    "--yes",
    help="Automatically answer yes to all questions.",
    is_flag=True,
)
@click.pass_context
def improve(ctx, path, type_of_repo, author, name, yes) -> None:
    """Improves downstream repos by verifying the context of scaffolded files."""
    if path is None:
        path = Path.cwd()
    os.chdir(path)
    verbose = ctx.obj["VERBOSE"]
    logger = ctx.obj["LOGGER"]
    remote = ctx.obj["REMOTE"]
    logger.info(f"Remote: {remote}")

    remote_owner = get_remote_owner()
    if remote_owner:
        logger.info(f"Repo owner found: {remote_owner}")
    else:
        logger.warning("Could not determine remote owner. Using provided author.")
        remote_owner = author

    scaffolder = RepoScaffolder(
        type_of_repo=type_of_repo,
        logger=logger,
        verbose=verbose,
        render_overrides={
            "author": author,
            "project_name": name,
            "git_owner": remote_owner
        },
    )
    results = scaffolder.verify(True, yes=yes)
    failed = results.count(CheckResult.FAIL)
    modified = results.count(CheckResult.MODIFIED)
    logger.info(f"""Verification completed with results:
        Passed:   - {results.count(CheckResult.PASS)}
        Failed:   - {failed}
        Modified: - {modified}
        Skipped:  - {results.count(CheckResult.SKIPPED)}
        """)

    if modified:
        msg = f"Verification completed with {modified} modified."
        raise click.ClickException(msg)
    if failed:
        msg = f"Verification failed with {failed} failed."
        raise click.ClickException(msg)
    logger.info("Verification completed successfully. All files are formatted correctly.")
