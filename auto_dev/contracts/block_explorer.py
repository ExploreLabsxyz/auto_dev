"""Module to interact with the blockchain explorer."""

import json
from typing import Any, Dict, Optional
from dataclasses import dataclass

import requests
from web3 import Web3

from auto_dev.constants import DEFAULT_TIMEOUT


@dataclass
class BlockExplorer:
    """Class to interact with the blockchain explorer.

    A class that provides methods to interact with blockchain explorers
    for retrieving contract information without requiring API keys.
    """

    base_url: str = "https://abidata.net"

    def get_abi(self, address: str, network: str) -> Dict[str, Any]:
        """Get the ABI for the contract at the address.

        Retrieves the ABI (Application Binary Interface) for a smart contract
        from abidata.net, which provides a simple API that doesn't require
        authentication. The method validates the contract address format and
        handles network-specific ABI retrieval.

        Args:
            address: The contract address to fetch the ABI for. Must be a valid
                    Ethereum address that can be converted to checksum format.
            network: Network name (e.g., 'arbitrum', 'polygon', 'base').
                    Required to specify which network to fetch the ABI from.

        Returns:
            Dict[str, Any]: The contract ABI as a dictionary containing the
                           interface specification with function signatures,
                           event definitions, and other contract details.

        Raises:
            ValueError: If the ABI cannot be retrieved from the explorer due to
                       invalid response, network issues, or malformed JSON.
        """
        web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
        check_address = web3.to_checksum_address(address)
        url = f"{self.base_url}/{check_address}?network={network}"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        if response.status_code != 200:
            msg = f"Failed to get ABI from {url} with status code {response.status_code}"
            raise ValueError(msg)
        try:
            result = response.json()
            return result["abi"]
        except (json.JSONDecodeError, KeyError) as e:
            msg = f"Failed to decode JSON response from {url}: {str(e)}"
            raise ValueError(msg) from e
