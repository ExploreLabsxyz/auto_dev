"""
Test the contracts module.
"""
import shutil

import pytest
import responses

from auto_dev.commands.scaffold import BlockExplorer, ContractScaffolder

KNOWN_ADDRESS = "0xc939df369C0Fc240C975A6dEEEE77d87bCFaC259"
BLOCK_EXPLORER_URL = "https://api.etherscan.io"
BLOCK_EXPLORER_API_KEY = None


@pytest.fixture
def block_explorer():
    """
    Block explorer fixture.
    """
    return BlockExplorer(BLOCK_EXPLORER_URL, BLOCK_EXPLORER_API_KEY)


@responses.activate
def test_block_explorer(block_explorer):
    """
    Test the block explorer.
    """
    responses.add(
        responses.GET,
        f"{BLOCK_EXPLORER_URL}/api?module=contract&action=getabi&address={KNOWN_ADDRESS}",
        json={"status": "1", "message": "OK", "result": '{"abi": "some_abi"}'},
    )
    block_explorer = BlockExplorer(BLOCK_EXPLORER_URL, BLOCK_EXPLORER_API_KEY)
    abi = block_explorer.get_abi(KNOWN_ADDRESS)
    assert abi


# we now test the scaffolder
@pytest.fixture
def scaffolder(block_explorer):
    """
    Scaffolder fixture.
    """
    return ContractScaffolder(block_explorer, "eightballer")


@responses.activate
def test_scaffolder_generate(scaffolder):
    """Test the scaffolder."""
    responses.add(
        responses.GET,
        f"{BLOCK_EXPLORER_URL}/api?module=contract&action=getabi&address={KNOWN_ADDRESS}",
        json={"status": "1", "message": "OK", "result": '{"abi": "some_abi"}'},
    )
    new_contract = scaffolder.from_block_explorer(KNOWN_ADDRESS, "new_contract")
    assert new_contract
    assert new_contract.abi
    assert new_contract.address == KNOWN_ADDRESS
    assert new_contract.name == "new_contract"
    assert new_contract.author == "eightballer"


@responses.activate
def test_scaffolder_generate_openaea_contract(scaffolder, test_filesystem):
    """
    Test the scaffolder.
    """
    del test_filesystem
    responses.add(
        responses.GET,
        f"{BLOCK_EXPLORER_URL}/api?module=contract&action=getabi&address={KNOWN_ADDRESS}",
        json={"status": "1", "message": "OK", "result": '{"abi": "some_abi"}'},
    )
    new_contract = scaffolder.from_block_explorer(KNOWN_ADDRESS, "new_contract")
    contract_path = scaffolder.generate_openaea_contract(new_contract)
    assert contract_path
    assert contract_path.exists()
    assert contract_path.name == "new_contract"
    assert contract_path.parent.name == "contracts"
    shutil.rmtree(contract_path.parent)
    assert not contract_path.exists()