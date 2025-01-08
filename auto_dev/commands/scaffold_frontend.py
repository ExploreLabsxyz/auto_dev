"""Frontend component scaffolding for auto_dev."""

import os
from pathlib import Path
from typing import IO, Optional

import click
from click import Context

from auto_dev.commands.scaffold import scaffold


DEFAULT_OPENAPI_SPEC = """openapi: 3.0.0
info:
  title: Agent Frontend API
  description: API endpoints for agent interaction
  version: 0.1.0
servers:
  - url: http://0.0.0.0:5555
paths:
  /:
    get:
      summary: Returns the main HTML page
      responses:
        '200':
          description: HTML response
          content:
            text/html:
              schema:
                type: string
  /api/agent-info:
    get:
      summary: Returns the agent's state and info
      responses:
        '200':
          description: JSON response
          content:
            application/json:
              schema:
                type: object
                properties:
                  agent-status:
                    type: string"""


DEFAULT_COMPONENT_YAML = """name: {component_name}
author: {author}
version: 0.1.0
type: custom
description: Custom UI for interacting with an autonomous agent
license: Apache-2.0
aea_version: '>=1.0.0, <2.0.0'
api_spec: openapi3_spec.yaml
frontend_dir: build
behaviours:
  - class_name: ExampleBehaviour
    args: {}
handlers:
  - class_name: UserInterfaceHttpHandler
    args: {}"""


DEFAULT_INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Agent UI</title>
</head>
<body>
    <div id="root"></div>
    <script>
        // Example of API interaction
        fetch('http://localhost:5555/api/agent-info')
            .then(response => response.json())
            .then(data => {
                console.log('Agent status:', data['agent-status']);
            });
    </script>
</body>
</html>"""


@scaffold.command()
@click.argument("frontend_name")
@click.option(
    "--author",
    default=None,
    help="Author name for the component",
)
@click.pass_context
def frontend(ctx: Context, frontend_name: str, author: Optional[str] = None) -> None:
    """
    Scaffold a frontend component with the recommended folder structure.

    Creates a new frontend component with the following structure:
    packages/AUTHOR/customs/COMPONENT_NAME/
    ├── build
    │   └── index.html
    ├── component.yaml
    ├── __init__.py
    └── openapi3_spec.yaml
    """
    if author is None:
        author = os.getenv("USER", "default_author")

    # Create component directory structure
    base_path = Path(f"packages/{author}/customs/{frontend_name}")
    base_path.mkdir(parents=True, exist_ok=True)
    (base_path / "build").mkdir(exist_ok=True)

    # Create __init__.py
    (base_path / "__init__.py").touch()

    # Create component.yaml
    with open(base_path / "component.yaml", "w") as f_component:
        f_component.write(DEFAULT_COMPONENT_YAML.format(
            component_name=frontend_name,
            author=author
        ))

    # Create openapi3_spec.yaml
    with open(base_path / "openapi3_spec.yaml", "w") as f_openapi:
        f_openapi.write(DEFAULT_OPENAPI_SPEC)

    # Create index.html
    with open(base_path / "build" / "index.html", "w") as f_html:
        f_html.write(DEFAULT_INDEX_HTML)

    click.echo(f"Created frontend component at {base_path}")
    click.echo("Next steps:")
    click.echo("1. Customize the OpenAPI specification in openapi3_spec.yaml")
    click.echo("2. Update the frontend code in build/index.html")
    click.echo("3. Configure your agent to use this component")
