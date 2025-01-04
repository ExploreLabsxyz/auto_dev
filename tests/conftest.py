"""Conftest for testing command-line interfaces."""
# pylint: disable=W0135

import os
import shutil
from pathlib import Path

import pytest
from aea.configurations.base import PublicId

from auto_dev.utils import isolated_filesystem
from auto_dev.constants import DEFAULT_ENCODING, SAMPLE_PACKAGE_FILE, SAMPLE_PACKAGES_JSON, AUTONOMY_PACKAGES_FILE
from auto_dev.cli_executor import CommandExecutor


OPENAPI_TEST_CASES = [
    ("uspto.yaml", ["handle_get_", "handle_get_dataset_version_fields", "handle_post_dataset_version_records"]),
    ("petstore.yaml", ["handle_get_pets", "handle_post_pets", "handle_get_pets_petId"]),
    ("petstore-expanded.yaml", ["handle_get_pets", "handle_post_pets", "handle_get_pets_id", "handle_delete_pets_id"]),
    ("dummy_openapi.yaml", ["handle_get_users", "handle_post_users", "handle_get_users_userId"]),
    (
        "innovation_station.yaml",
        [
            "handle_get_protocol",
            "handle_post_protocol",
            "handle_get_protocol_id",
            "handle_get_connection",
            "handle_post_connection",
            "handle_get_connection_id",
            "handle_get_contract",
            "handle_post_contract",
            "handle_get_contract_id",
            "handle_get_skill",
            "handle_post_skill",
            "handle_get_skill_id",
            "handle_get_agent",
            "handle_post_agent",
            "handle_get_agent_id",
            "handle_get_service",
            "handle_post_service",
            "handle_get_service_id",
            "handle_post_generate",
        ],
    ),
]


@pytest.fixture(params=OPENAPI_TEST_CASES)
def openapi_test_case(request):
    """Fixture for openapi test cases."""
    return request.param


@pytest.fixture
def test_filesystem():
    """Fixture for invoking command-line interfaces."""
    with isolated_filesystem(copy_cwd=True) as directory:
        yield directory


@pytest.fixture
def test_clean_filesystem():
    """Fixture for invoking command-line interfaces."""
    with isolated_filesystem() as directory:
        yield directory


@pytest.fixture
def test_packages_filesystem(test_filesystem):
    """Fixture for testing packages."""
    # Initialize packages using autonomy CLI
    try:
        command_executor = CommandExecutor(["autonomy", "packages", "init"])
        if not command_executor.execute(verbose=True):
            raise ValueError("Failed to initialize packages directory")
    except Exception as e:
        raise ValueError(f"Failed to initialize packages directory: {str(e)}")

    # Write packages configuration
    with open(AUTONOMY_PACKAGES_FILE, "w", encoding=DEFAULT_ENCODING) as file:
        file.write(SAMPLE_PACKAGES_JSON["packages/packages.json"])

    for file, data in SAMPLE_PACKAGE_FILE.items():
        (Path(test_filesystem) / Path(file).parent).mkdir(parents=True, exist_ok=True)
        with open(Path(test_filesystem) / Path(file), "w", encoding=DEFAULT_ENCODING) as path:
            path.write(data)

    return test_filesystem


@pytest.fixture
def cli_runner():
    """Fixture for invoking command-line interfaces."""
    return CommandExecutor


@pytest.fixture
def dummy_agent_tim(test_filesystem, monkeypatch) -> Path:
    """Fixture for dummy agent tim."""

    monkeypatch.syspath_prepend(test_filesystem)
    assert Path.cwd() == Path(test_filesystem)

    agent = PublicId.from_str("dummy_author/tim")
    # Create the agent directory
    agent_dir = Path.cwd() / agent.name
    if agent_dir.exists():
        shutil.rmtree(agent_dir)

    # Create the agent
    create_cmd = ["adev", "create", str(agent), "-t", "eightballer/base"]
    command_executor = CommandExecutor(create_cmd)
    result = command_executor.execute(verbose=True)
    if not result:
        msg = f"CLI command execution failed: {' '.join(create_cmd)}"
        raise ValueError(msg)

    # Verify agent directory was created
    if not agent_dir.exists():
        msg = f"Agent directory not created at {agent_dir}"
        raise ValueError(msg)

    agent_dir = Path.cwd() / agent.name
    if not agent_dir.exists():
        msg = f"Agent directory not created at {agent_dir}"
        raise ValueError(msg)

    os.chdir(str(agent_dir))

    commands = [
        ["aea", "generate-key", "ethereum"],
        ["aea", "add-key", "ethereum"],
    ]
    for cmd in commands:
        command_executor = CommandExecutor(cmd)
        result = command_executor.execute(verbose=True)
        if not result:
            msg = f"CLI command execution failed: {' '.join(cmd)}"
            raise ValueError(msg)

    return Path.cwd()
