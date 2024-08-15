"""reads in 2 github repos.

One is the parent repo, the other is the child repo.

The child repo is dependent on the parent repo.

When there is a change in the parent repo, we want to update the child repo.

The dependencies are depfined in a file called packages/packages.json

this is structures as follows:

{
    "dev": {
        "aea_dep1": "ipfshash",
        "aea_dep2": "ipfshash",
        },
    "third_party": {
        "aea_dep3": "ipfshash",
        "aea_dep4": "ipfshash",
        },
}

The ipfshash is the hash of the package.

We want to be able to update the hash of the package.

"""

import os
import sys
import shutil
import logging
import traceback
from enum import Enum
from typing import Dict, List
from pathlib import Path
from dataclasses import dataclass

import toml
import yaml
import requests
import rich_click as click
from rich import print_json
from rich.progress import track

from auto_dev.base import build_cli
from auto_dev.utils import write_to_file
from auto_dev.constants import DEFAULT_TIMEOUT, DEFAULT_ENCODING, FileType
from auto_dev.exceptions import AuthenticationError, NetworkTimeoutError


PARENT = Path("repo_1")
CHILD = Path("repo_2")


def get_package_json(repo: Path) -> dict[str, dict[str, str]]:
    """We get the package json."""
    package_json = repo / "packages" / "packages.json"
    with open(package_json, encoding=DEFAULT_ENCODING) as file_pointer:
        return yaml.safe_load(file_pointer)


def write_package_json(repo: Path, package_dict: dict[str, dict[str, str]]) -> None:
    """We write the package json."""
    package_json = repo / "packages" / "packages.json"
    write_to_file(str(package_json), package_dict, FileType.JSON)


def get_package_hashes(repo: Path) -> dict[str, str]:
    """We get the package hashes."""
    package_dict = get_package_json(repo)
    package_hashes = {}
    for package_type_dict in package_dict.values():
        for package_name, package_hash in package_type_dict.items():
            package_hashes[package_name] = package_hash
    return package_hashes


def get_proposed_dependency_updates(parent_repo: Path, child_repo: Path) -> dict[str, str]:
    """We get the proposed dependency updates."""
    parent_package_hashes = get_package_hashes(parent_repo)
    child_package_hashes = get_package_hashes(child_repo)
    proposed_dependency_updates = {}
    for package_name, package_hash in parent_package_hashes.items():
        if package_name in child_package_hashes and package_hash != child_package_hashes[package_name]:
            proposed_dependency_updates[package_name] = package_hash
    return proposed_dependency_updates


def update_package_json(repo: Path, proposed_dependency_updates: dict[str, str]) -> None:
    """We update the package json."""
    package_dict = get_package_json(repo)
    for package_type, package_type_dict in package_dict.items():
        for package_name in package_type_dict:
            if package_name in proposed_dependency_updates:
                package_dict[package_type][package_name] = proposed_dependency_updates[package_name]
    write_package_json(repo, package_dict)


def from_key_to_path(key: str) -> Path:
    """We get the path from the key string some examples of the keys are;
    agent/eightballer/custom_balance_poller/0.1.0
    where the folder to be removed is;
    packages/eightballer/agents/custom_balance_poller.
    """
    parts = key.split("/")

    path_list = [
        "packages",
        parts[1],
        parts[0] + "s",
        parts[2],
    ]
    return Path(*path_list)


def remove_old_package(repo: Path, proposed_dependency_updates: dict[str, str]) -> None:
    """We remove the old package directories."""
    for package_name in proposed_dependency_updates:
        path = from_key_to_path(package_name)
        path = repo / path
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)


def main(
    parent_repo: Path,
    child_repo: Path,
    logger: logging.Logger,
    auto_confirm: bool = False,
) -> None:
    """We run the main function."""
    try:
        proposed = get_proposed_dependency_updates(parent_repo=parent_repo, child_repo=child_repo)
    except FileNotFoundError:
        logger.debug(traceback.format_exc())
        logger.exception("The packages.json file does not exist. Exiting. 😢")
        return False
    if not proposed:
        logger.info("No changes required. 😎")
        return False
    for package_name, package_hash in proposed.items():
        logger.info(f"Updating {package_name} to {package_hash}")
    if not auto_confirm:
        click.confirm("Do you want to update the package?", abort=True)
    logger.info("Updating the packages json... 📝")
    update_package_json(repo=child_repo, proposed_dependency_updates=proposed)
    logger.info("Removing the old packages directories... 🗑")
    remove_old_package(repo=child_repo, proposed_dependency_updates=proposed)
    # we now copy the new packages over.
    logger.info("Copying the new packages over... 📝")
    for package_name in proposed:
        path = from_key_to_path(package_name)
        parent_path = parent_repo / path
        child_path = child_repo / path
        shutil.copytree(parent_path, child_path)
    logger.info("Done. 😎")
    return True


cli = build_cli()


class DependencyType(Enum):
    """Type of dependency."""

    AUTONOMY = "autonomy"
    PYTHON = "python"
    GIT = "git"


class DependencyLocation(Enum):
    """Location of the dependency."""

    LOCAL = "local"
    REMOTE = "remote"


@dataclass
class Dependency:
    """A dependency."""

    name: str
    version: str
    location: DependencyLocation


@dataclass
class PythonDependency(Dependency):
    """A python dependency."""

    type: DependencyType.PYTHON


@dataclass
class AutonomyDependency(Dependency):
    """An autonomy dependency."""

    type: DependencyType.AUTONOMY


@dataclass
class GitDependency(Dependency):
    """A git dependency."""

    type = DependencyType.GIT
    autonomy_dependencies: Dict[str, Dependency] = None
    url: str = None

    @property
    def headers(self) -> Dict[str, str]:
        """Get the headers."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
        }
        return headers

    def get_latest_version(self) -> str:
        """Get the latest version."""
        if self.location == DependencyLocation.LOCAL:
            return self.version
        return self._get_latest_remote_version()

    def _get_latest_remote_version(self) -> str:
        """Get the latest remote version."""
        tag_url = f"{self.url}/releases"
        res = requests.get(tag_url, headers=self.headers, timeout=DEFAULT_TIMEOUT)
        if res.status_code != 200:
            if res.status_code == 403:
                raise AuthenticationError("Error: Rate limit exceeded. Please add a github token.")
            raise NetworkTimeoutError(f"Error: {res.status_code} {res.text}")
        data = res.json()
        latest_version = data[0]["tag_name"]
        return latest_version

    def get_all_autonomy_packages(self):
        """Read in the autonomy packages. the are located in the remote url."""
        tag = self.get_latest_version()
        file_path = "packages/packages.json"
        remote_url = f"{self.url}/contents/{file_path}?ref={tag}"
        data = requests.get(remote_url, headers=self.headers, timeout=DEFAULT_TIMEOUT)

        if data.status_code != 200:
            raise NetworkTimeoutError(f"Error: {data.status_code} {data.text}")
        dl_url = data.json()["download_url"]
        data = requests.get(dl_url, headers=self.headers, timeout=DEFAULT_TIMEOUT).json()
        autonomy_packages = data["dev"]
        return autonomy_packages


@cli.group()
@click.pass_context
def deps(
    ctx: click.Context,  # noqa
) -> None:
    """Commands for managing dependencies.
    - update: Update both the packages.json from the parent repo and the packages in the child repo.
    - generate_gitignore: Generate the gitignore file from the packages.json file.
    """


@click.option(
    "-p",
    "--parent-repo",
    default=".",
    help="The parent repo.",
    type=Path,
    required=True,
)
@click.option(
    "-c",
    "--child-repo",
    help="The child repo.",
    type=Path,
    required=True,
    default=".",
)
@click.option(
    "--auto-confirm",
    default=False,
    help="Auto confirm the changes.",
)
@click.option(
    "--location",
    default=DependencyLocation.LOCAL,
    type=DependencyLocation,
    help="The location of the dependency.",
)
@deps.command()
@click.pass_context
def update(
    ctx: click.Context,
    parent_repo: Path,
    child_repo: Path,
    location: DependencyLocation = DependencyLocation.LOCAL,
    auto_confirm: bool = False,
) -> None:
    """We update aea packages.json dependencies from a parent repo.
    Example usage:
        adev deps update -p /path/to/parent/repo -c /path/to/child/repo.
    """
    logger = ctx.obj["LOGGER"]
    logger.info("Updating the dependencies... 📝")
    logger.info(f"Parent repo: {parent_repo}")
    logger.info(f"Child repo: {child_repo}")
    logger.info(f"Location: {location}")
    if parent_repo == DependencyLocation.REMOTE:
        parent_repo = Path("parent_repo")
    logger = ctx.obj["LOGGER"]
    logger.info("Updating the dependencies... 📝")

    result = main(parent_repo=parent_repo, child_repo=child_repo, auto_confirm=auto_confirm, logger=logger)
    if not result:
        sys.exit(1)
    logger.info("Done. 😎")


# We have a command to generate the gitignore file.
@deps.command()
@click.pass_context
def generate_gitignore(
    ctx: click.Context,
) -> None:
    """We generate the gitignore file from the packages.json file
    Example usage:
        adev deps generate_gitignore.
    """
    package_dict = get_package_json(repo=Path())
    third_party_packages = package_dict.get("third_party", {})
    third_party_paths = [from_key_to_path(key) for key in third_party_packages]
    current_gitignore = Path(".gitignore").read_text(encoding=DEFAULT_ENCODING)
    for path in third_party_paths:
        # we check if the path is in the gitignore file.
        if str(path) in current_gitignore:
            continue
        with open(".gitignore", "a", encoding=DEFAULT_ENCODING) as file_pointer:
            file_pointer.write(f"\n{path}")
    ctx.obj["LOGGER"].info("Done. 😎")


@dataclass
class AutonomyVersionSet:
    """A set of autonomy versions."""

    upstream_dependency: List[GitDependency]


open_autonomy_repo = GitDependency(
    name="open-autonomy",
    version="0.15.2",
    location=DependencyLocation.REMOTE,
    url="https://api.github.com/repos/valory-xyz/open-autonomy",
)

open_aea_repo = GitDependency(
    name="open-aea",
    version="1.55.0",
    location=DependencyLocation.REMOTE,
    url="https://api.github.com/repos/valory-xyz/open-aea",
)

auto_dev_repo = GitDependency(
    name="autonomy-dev",
    version="0.2.73",
    location=DependencyLocation.REMOTE,
    url="https://api.github.com/repos/8ball030/auto_dev",
)

autonomy_version_set = AutonomyVersionSet(
    upstream_dependency=[
        open_autonomy_repo,
        open_aea_repo,
    ]
)

poetry_dependencies = [
    auto_dev_repo,
]


def handle_output(issues, changes) -> None:
    """Handle the output."""
    if issues:
        for issue in issues:
            print(issue)
        sys.exit(1)

    if changes:
        for change in changes:
            print(f"Updated {change} successfully. ✅")
        print("Please verify the proposed changes and commit them! 📝")
        sys.exit(1)
    print("No changes required. 😎")


@deps.command()
@click.pass_context
def verify(
    ctx: click.Context,
) -> None:
    """
    We verify the packages.json file.
    Example usage:
        adev deps verify
    """
    ctx.obj["LOGGER"].info("Verifying the dependencies against the version set specified. 📝")
    issues = []
    changes = []
    click.echo("Verifying autonomy dependencies... 📝")
    for dependency in track(autonomy_version_set.upstream_dependency):
        click.echo(f"   Verifying:   {dependency.name}")
        remote_packages = dependency.get_all_autonomy_packages()
        local_packages = get_package_json(Path())["third_party"]
        diffs = {}
        for package_name, package_hash in remote_packages.items():
            if package_name in local_packages:
                if package_hash != local_packages[package_name]:
                    diffs[package_name] = package_hash

        if diffs:
            print_json(data=diffs)
            click.confirm("Do you want to update the package?\n", abort=True)
            update_package_json(repo=Path(), proposed_dependency_updates=diffs)
            remove_old_package(repo=Path(), proposed_dependency_updates=diffs)
            changes.append(dependency.name)

        pyproject = toml.load("pyproject.toml")["tool"]["poetry"]["dependencies"]
        if dependency.name in pyproject:
            current_version = pyproject[dependency.name]
            expected_version = f"=={dependency.get_latest_version()[1:]}"
            if current_version != expected_version:
                issues.append(
                    f"Please update the version of {dependency.name} from `{current_version}` to `{expected_version}`\n"
                )

    click.echo("Verifying poetry dependencies... 📝")
    for dependency in track(poetry_dependencies):
        click.echo(f"   Verifying:   {dependency.name}")
        raw = toml.load("pyproject.toml")["tool"]["poetry"]["dependencies"]
        current_version = str(raw[dependency.name])
        expected_version = f"{dependency.get_latest_version()[1:]}"
        if current_version.find(expected_version) == -1:
            issues.append(
                f"Update the poetry version of {dependency.name} from `{current_version}` to `{expected_version}`\n"
            )

    handle_output(issues, changes)


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
