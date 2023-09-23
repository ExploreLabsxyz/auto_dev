"""
Implement scaffolding tooling
"""

from copy import deepcopy
from pathlib import Path
from typing import List, Tuple

import rich_click as click
import yaml

from auto_dev.base import build_cli
from auto_dev.constants import DEFAULT_ENCODING
from auto_dev.utils import get_logger

logger = get_logger()

cli = build_cli(plugins=False)

# we have a scaffold command group

BASE_LOGGING_CONFIG = yaml.safe_load(
    """
logging_config:
    disable_existing_loggers: true
    version: 1
    formatters:
        standard:
            format: '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    handlers:
        {handlers_config}
    loggers:
        aea:
            handlers: {handlers_list}
            level: INFO
            propagate: false
"""
)

LEDGER_CONNECTION_CONFIG = yaml.safe_load(
    """
public_id: valory/ledger:0.19.0
type: connection
config:
  ledger_apis:
    ethereum:
      address: ${str}
      chain_id: ${int}
      poa_chain: ${bool:false}
      default_gas_price_strategy: ${str:eip1559}
"""
)

ABCI_CONNECTION_CONFIG = yaml.safe_load(
    """
public_id: valory/abci:0.1.0
type: connection
config:
  host: ${str:localhost}
  port: ${int:26658}
  use_tendermint: ${bool:false}
  target_skill_id: ${str}
"""
)

CONSOLE_HANDLER = yaml.safe_load(
    """
class: rich.logging.RichHandler
level: INFO
"""
)

HTTP_HANDLER = yaml.safe_load(
    """
class: logging.handlers.HTTPHandler
formatter: standard
level: INFO
host: ${LOG_SERVER:str:localhost:8000}
url: /log/
method: POST
"""
)

LOGFILE_HANDLER = yaml.safe_load(
    """
class: logging.FileHandler
formatter: standard
filename: ${LOG_FILE:str:log.txt}
level: INFO
"""
)


HANDLERS = {
    "console": CONSOLE_HANDLER,
    "http": HTTP_HANDLER,
    "logfile": LOGFILE_HANDLER,
}

CONNECTIONS = {
    "ledger": (
        "valory/ledger:0.19.0:bafybeicgfupeudtmvehbwziqfxiz6ztsxr5rxzvalzvsdsspzz73o5fzfi",
        LEDGER_CONNECTION_CONFIG,
    ),
    "abci": ("valory/abci:0.1.0:bafybeigtjiag4a2h6msnlojahtc5pae7jrphjegjb3mlk2l54igc4jwnxe", ABCI_CONNECTION_CONFIG),
}

AEA_CONFIG = "aea-config.yaml"


class BaseScaffolder:
    """BaseScaffolder"""

    def load(self):
        """Load"""
        if not Path(AEA_CONFIG).exists():
            raise FileNotFoundError(f"File {AEA_CONFIG} not found")
        content = Path(AEA_CONFIG).read_text(encoding=DEFAULT_ENCODING)
        self.aea_config = list(yaml.safe_load_all(content))

    def __init__(self):
        """Init scaffolder."""
        self.logger = get_logger()
        self.load()

    def write(self):
        """Write"""
        with open(AEA_CONFIG, "w", encoding=DEFAULT_ENCODING) as file:
            yaml.dump_all(self.aea_config, file, default_flow_style=False, sort_keys=False)
        self.load()


class LoggingScaffolder(BaseScaffolder):
    """Logging scaffolder."""

    def generate(self, handlers: list):
        """Scaffold logging."""
        self.logger.info(f"Generating logging config with handlers: {handlers}")
        if not handlers:
            raise ValueError("No handlers provided")
        if handlers == ["all"]:
            handlers = HANDLERS
        for handler in handlers:
            if handler not in HANDLERS:
                raise ValueError(f"Handler '{handler}' not found")
            handlers = {handler: HANDLERS[handler] for handler in handlers}
        logging_config = deepcopy(BASE_LOGGING_CONFIG)
        logging_config["logging_config"]["handlers"] = handlers
        logging_config["logging_config"]["loggers"]["aea"]["handlers"] = list(handlers.keys())
        return logging_config

    def scaffold(self, handlers: list):
        """Scaffold logging."""

        logging_config = self.generate(handlers)
        self.aea_config[0].update(logging_config)
        self.write()
        return logging_config


@cli.group()
def augment():
    """Scaffold commands."""


@augment.command()
@click.argument("handlers", nargs=-1, type=click.Choice(HANDLERS.keys()), required=True)
def logging(handlers):
    """Augment an aeas logging configuration."""
    logger.info(f"Augmenting logging with handlers: {handlers}")
    logging_scaffolder = LoggingScaffolder()
    logging_scaffolder.scaffold(handlers)
    logger.info("Logging scaffolded.")


class ConnectionScaffolder(BaseScaffolder):
    """ConnectionScaffolder"""

    def generate(self, connections: list) -> List[Tuple[str, str]]:
        """Generate connections."""
        self.logger.info(f"Generating connection config for: {connections}")
        if not connections:
            raise ValueError("No connections provided")
        if connections == ["all"]:
            connections = CONNECTIONS
        for connection in connections:
            if connection not in CONNECTIONS:
                raise ValueError(f"Connection '{connection}' not found")
        connections = [CONNECTIONS[c] for c in connections]
        return connections

    def scaffold(self, connections: list) -> None:
        """Scaffold connection."""

        connections = self.generate(connections)
        for connection, config in connections:
            self.aea_config[0]["connections"].append(connection)
            self.aea_config.append(config)

        self.write()


@augment.command()
@click.argument("connections", nargs=-1, type=click.Choice(CONNECTIONS), required=True)
def connection(connections):
    """Augment an AEA configuration with connections."""
    logger.info(f"Augmenting agent connections: {connections}")
    connection_scaffolder = ConnectionScaffolder()
    connection_scaffolder.scaffold(connections)
    logger.info("Connections scaffolded.")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
