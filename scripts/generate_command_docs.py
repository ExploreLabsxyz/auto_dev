"""Script to generate command documentation.

This module handles the automatic generation of documentation for all CLI commands
in the auto_dev project. It uses introspection to discover commands and their
subcommands, then generates markdown documentation with proper formatting.
"""

import logging
from pathlib import Path
from importlib import import_module
from dataclasses import dataclass

import click


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Command configuration
COMMANDS = [
    "run",
    "create",
    "lint",
    "publish",
    "test",
    "improve",
    "release",
    "metadata",
    "fmt",
    "scaffold",
    "deps",
    "convert",
    "repo",
    "fsm",
    "augment",
]


@dataclass
class DocTemplates:
    """Templates for documentation generation."""

    COMMAND = """## Description

::: auto_dev.commands.{command_name}.{command_name}
    options:
      show_root_heading: false
      show_source: false
      show_signature: true
      show_signature_annotations: true
      docstring_style: sphinx
      show_docstring_parameters: true
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_examples: true
      docstring_section_style: table
      heading_level: 2

## Usage

```bash
adev {command_name} [OPTIONS] [ARGS]
```

Additionally, you can view the parameters for the command using:
```bash
adev {command_name} --help
```

{subcommands}"""

    SUBCOMMAND = """
## {subcommand_title}

::: auto_dev.commands.{command_name}.{subcommand_func}
    options:
      show_root_heading: false
      show_source: false
      show_signature: true
      show_signature_annotations: true
      docstring_style: sphinx
      show_docstring_parameters: true
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_examples: true
      docstring_section_style: table
      heading_level: 2"""


class CommandDocGenerator:
    """Handles the generation of command documentation."""

    def __init__(self, docs_dir: Path):
        """Initialize the generator with output directory."""
        self.docs_dir = docs_dir
        self.templates = DocTemplates()

    def find_function_name(self, module, cmd_name: str) -> str | None:
        """Find the actual function name in the module for a given command name.

        Args:
        ----
            module: The imported module to search
            cmd_name: The command name to find

        Returns:
        -------
            The function name if found, None otherwise

        """
        for attr_name, attr_value in module.__dict__.items():
            if isinstance(attr_value, click.Command) and attr_value.name == cmd_name:
                return attr_name
        return None

    def get_subcommands(self, command_name: str) -> list[tuple[str, str]]:
        """Discover subcommands for a given command by inspecting its module.

        Args:
        ----
            command_name: Name of the command to inspect

        Returns:
        -------
            List of tuples containing (command_name, function_name)

        """
        try:
            module = import_module(f"auto_dev.commands.{command_name}")
        except ImportError as e:
            logger.warning(f"Could not import command module {command_name}: {e}")
            return []

        # Get the command group function
        group_func = getattr(module, command_name, None)
        if not group_func or not isinstance(group_func, click.Group):
            return []

        # Get commands directly from the Click group
        subcommands = []
        for cmd_name, cmd in group_func.commands.items():
            if not isinstance(cmd, click.Command) or isinstance(cmd, click.Group):
                continue

            func_name = self.find_function_name(module, cmd_name)
            if func_name:
                subcommands.append((cmd_name, func_name))

        return sorted(subcommands)

    def generate_command_doc(self, command: str) -> None:
        """Generate documentation for a single command.

        Args:
        ----
            command: Name of the command to document

        """
        doc_path = self.docs_dir / f"{command}.md"
        subcommands = self.get_subcommands(command)

        # Generate subcommand documentation
        subcommands_text = ""
        for cmd_name, func_name in subcommands:
            subcommands_text += self.templates.SUBCOMMAND.format(
                subcommand_title=cmd_name.replace("-", " ").title(), command_name=command, subcommand_func=func_name
            )

        try:
            doc_path.write_text(
                self.templates.COMMAND.format(command_name=command, subcommands=subcommands_text), encoding="utf-8"
            )
            logger.info(f"Generated documentation for {command}")
        except OSError as e:
            logger.exception(f"Failed to write documentation for {command}: {e}")


def main() -> None:
    """Generate documentation for all commands."""
    docs_dir = Path("docs/commands")
    assets_dir = Path("docs/assets")

    # Preserve assets directory if it exists
    if assets_dir.exists():
        logger.info("Preserving existing docs/assets directory")
    try:
        docs_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.exception(f"Failed to create docs directory: {e}")
        return

    generator = CommandDocGenerator(docs_dir)
    for command in COMMANDS:
        try:
            generator.generate_command_doc(command)
        except Exception as e:
            logger.exception(f"Failed to generate documentation for {command}: {e}")


if __name__ == "__main__":
    main()
