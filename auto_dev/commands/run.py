"""Command to run an agent."""

import os
import sys
import subprocess
from typing import Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

import docker
import rich_click as click
from aea.skills.base import PublicId

from auto_dev.base import build_cli
from auto_dev.cli_executor import CommandExecutor
from auto_dev.utils import map_os_to_env_vars


cli = build_cli()


@dataclass
class AgentRunner:
    """Class to manage running an agent."""

    agent_name: str
    verbose: bool
    force: bool
    logger: Any

    def run(self) -> None:
        """Run the agent."""
        self.log_operating_system()
        self.logger.info(f"Fetching agent {self.agent_name} from the local package registry...")
        self.check_tendermint()
        if self.check_agent_exists():
            sys.exit(1)
        self.fetch_agent()
        self.setup_agent()
        self.execute_agent()

    def check_tendermint(self) -> None:
        """Check if Tendermint is running."""
        docker_engine = docker.from_env()
        container_name = "tm_0"
        try:
            res = docker_engine.containers.get(container_name)
        except (subprocess.CalledProcessError, RuntimeError) as e:
            self.logger.error("Tendermint is not running. Please install and run Tendermint using Docker.")
            self.logger.error("You can start Tendermint with the following command:")
            sys.exit(1)
        if res.status != "running":
            self.logger.error("Tendermint is not healthy. Please check the logs.")
            sys.exit(1)

    def check_agent_exists(self) -> None:
        """Check if the agent already exists."""
        if Path(self.agent_name.name).exists() and not self.force:
            self.logger.error(f"Agent `{self.agent_name}` already exists. Use --force to overwrite.")
            return True
        if Path(self.agent_name.name).exists() and self.force:
            self.logger.info(f"Removing existing agent `{self.agent_name}` due to --force option.")
            self.execute_command(f"rm -rf {self.agent_name.name}")
        return False

    def fetch_agent(self) -> None:
        """Fetch the agent."""

        if not self.check_agent_exists():
            command = f"aea -s fetch {self.agent_name} --local"
            if not self.execute_command(command):
                self.logger.error(f"Failed to fetch agent {self.agent_name}.")
                sys.exit(1)
        return True

    def setup_agent(self) -> None:
        """Setup the agent."""

        self.logger.info(f"Agent author: {self.agent_name.author}")
        self.logger.info(f"Agent name: {self.agent_name.author}")

        self.change_directory(self.agent_name.name)
        self.manage_keys()
        self.install_dependencies()
        self.issue_certificates()
        self.logger.info("Agent setup complete. 🎉")

    def manage_keys(self) -> None:
        """Manage Ethereum keys."""
        if not Path("../ethereum_private_key.txt").exists():
            self.execute_command("aea generate-key ethereum")
            self.execute_command("aea -s add-key ethereum")
        else:
            self.execute_command("cp ../ethereum_private_key.txt ./ethereum_private_key.txt")
            self.execute_command("aea -s add-key ethereum")

    def install_dependencies(self) -> None:
        """Install agent dependencies."""
        self.execute_command("aea -s install")

    def issue_certificates(self) -> None:
        """Issue certificates for agent."""
        if not Path("../certs").exists():
            self.execute_command("aea -s issue-certificates")
        else:
            self.execute_command("cp -r ../certs ./")
    
    def start_tendermint(self) -> None:
        """Start Tendermint."""
        self.execute_command("docker compose up -d --force-recreate")

    def execute_agent(self) -> None:
        """Execute the agent."""
        # we run the agent in the os such that we can get the sterr and stdout
        # without having to use the subprocess module.
        os.system("aea -s run")  # noqa

    def execute_command(self, command: str, verbose=None) -> None:
        """Execute a shell command."""
        cli_executor = CommandExecutor(command=command.split(" "))
        result = cli_executor.execute(stream=True, verbose=verbose)
        if not result:
            self.logger.error(f"Command failed: {command}")
            self.logger.error(f"Error: {cli_executor.stderr}")
            sys.exit(1)
        return result

    def change_directory(self, directory: str) -> None:
        """Change the current working directory."""
        os.chdir(directory)


@cli.command()
@click.argument(
    "agent_public_id",
    type=PublicId.from_str,
    required=True,
)
@click.option("-v", "--verbose", is_flag=True, help="Verbose mode.", default=False)
@click.option("--force", is_flag=True, help="Force overwrite of existing agent", default=False)
@click.pass_context
def run(ctx, agent_public_id: str, verbose: bool, force: bool) -> None:
    """
    Run an agent from the local packages registry.

    Example usage:
        adev run eightballer/my_agent
    """
    logger = ctx.obj["LOGGER"]
    logger.info(f"Running agent {agent_public_id}... 🚀")
    runner = AgentRunner(agent_name=agent_public_id, verbose=verbose, force=force, logger=logger)
    runner.run()
    logger.info("Agent run complete. 😎")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
