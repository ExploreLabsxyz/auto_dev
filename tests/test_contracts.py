"""Test the contracts module."""

import json
import shutil
from pathlib import Path

import pytest
import responses

from auto_dev.constants import DEFAULT_ENCODING
from auto_dev.commands.scaffold import BlockExplorer, ContractScaffolder


KNOWN_ADDRESS = "0xc939df369C0Fc240C975A6dEEEE77d87bCFaC259"
KNOWN_NETWORK = "arbitrum"
DUMMY_ABI = json.loads((Path() / "tests" / "data" / "dummy_abi.json").read_text(DEFAULT_ENCODING))


@pytest.fixture
def block_explorer():
    """Block explorer fixture."""
    return BlockExplorer()


@responses.activate
def test_block_explorer(block_explorer):
    """Test the block explorer."""
    # Test mainnet (default network)
    responses.add(
        responses.GET,
        f"https://abidata.net/{KNOWN_ADDRESS}",
        json=DUMMY_ABI,
    )
    abi = block_explorer.get_abi(KNOWN_ADDRESS)
    assert abi == DUMMY_ABI

    # Test with specific network
    responses.add(
        responses.GET,
        f"https://abidata.net/{KNOWN_NETWORK}/{KNOWN_ADDRESS}",
        json=DUMMY_ABI,
    )
    abi = block_explorer.get_abi(KNOWN_ADDRESS, network=KNOWN_NETWORK)
    assert abi == DUMMY_ABI


# we now test the scaffolder
@pytest.fixture
def scaffolder(block_explorer):
    """Scaffolder fixture."""
    return ContractScaffolder(block_explorer, "eightballer")


@responses.activate
def test_scaffolder_generate(scaffolder):
    """Test the scaffolder."""
    test_abi = {"abi": "some_abi"}

    # Test mainnet scaffolding
    responses.add(
        responses.GET,
        f"https://abidata.net/{KNOWN_ADDRESS}",
        json=test_abi,
    )
    new_contract = scaffolder.from_block_explorer(KNOWN_ADDRESS, "new_contract")
    assert new_contract
    assert new_contract.abi == test_abi
    assert new_contract.address == KNOWN_ADDRESS
    assert new_contract.name == "new_contract"
    assert new_contract.author == "eightballer"

    # Test network-specific scaffolding
    responses.add(
        responses.GET,
        f"https://abidata.net/{KNOWN_NETWORK}/{KNOWN_ADDRESS}",
        json=test_abi,
    )
    new_contract = scaffolder.from_block_explorer(KNOWN_ADDRESS, "new_contract", network=KNOWN_NETWORK)
    assert new_contract
    assert new_contract.abi == test_abi
    assert new_contract.address == KNOWN_ADDRESS
    assert new_contract.name == "new_contract"
    assert new_contract.author == "eightballer"


@responses.activate
def test_scaffolder_generate_openaea_contract(scaffolder, test_filesystem):
    """Test the scaffolder."""
    del test_filesystem
    test_abi = {"abi": "some_abi"}

    # Test contract generation with mainnet ABI
    responses.add(
        responses.GET,
        f"https://abidata.net/{KNOWN_ADDRESS}",
        json=test_abi,
    )
    new_contract = scaffolder.from_block_explorer(KNOWN_ADDRESS, "new_contract")
    contract_path = scaffolder.generate_openaea_contract(new_contract)
    assert contract_path
    assert contract_path.exists()
    assert contract_path.name == "new_contract"
    assert contract_path.parent.name == "contracts"
    shutil.rmtree(contract_path.parent)
    assert not contract_path.exists()

    # Test contract generation with network-specific ABI
    responses.add(
        responses.GET,
        f"https://abidata.net/{KNOWN_NETWORK}/{KNOWN_ADDRESS}",
        json=test_abi,
    )
    new_contract = scaffolder.from_block_explorer(KNOWN_ADDRESS, "new_contract", network=KNOWN_NETWORK)
    contract_path = scaffolder.generate_openaea_contract(new_contract)
    assert contract_path
    assert contract_path.exists()
    assert contract_path.name == "new_contract"
    assert contract_path.parent.name == "contracts"
    shutil.rmtree(contract_path.parent)
    assert not contract_path.exists()


def test_scaffolder_from_abi(scaffolder, test_filesystem):
    """Test the scaffolder using an ABI file."""
    assert test_filesystem
    path = Path() / "tests" / "data" / "dummy_abi.json"
    new_contract = scaffolder.from_abi(str(path), KNOWN_ADDRESS, "new_contract")
    assert new_contract
    assert new_contract.abi
    assert new_contract.address == KNOWN_ADDRESS
    assert new_contract.name == "new_contract"
    assert new_contract.author == "eightballer"


def test_scaffolder_extracts_events(scaffolder, test_filesystem):
    """Test the scaffolder extracts events."""
    assert test_filesystem
    path = Path() / "tests" / "data" / "dummy_abi.json"
    new_contract = scaffolder.from_abi(str(path), KNOWN_ADDRESS, "new_contract")
    new_contract.parse_events()
