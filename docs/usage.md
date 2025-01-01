# Quick Start Guide

This guide will help you get started with auto_dev quickly.

## Basic Usage

1. Create a new agent:
   ```bash
   adev create -t eightballer/frontend_agent my_author/my_agent
   ```

2. Scaffold components:
   ```bash
   # Add a contract
   adev scaffold contract --from-abi contract.abi --name MyContract
   
   # Add an FSM
   adev scaffold fsm --spec fsm_spec.yaml
   ```

3. Format and lint code:
   ```bash
   # Format code
   adev fmt -p .
   
   # Lint code
   adev lint -p .
   ```

4. Run tests:
   ```bash
   adev test -p tests
   ```

## Common Workflows

### Creating a New Agent

1. Choose a template:
   ```bash
   # List available templates
   adev create --help
   
   # Create from template
   adev create -t eightballer/frontend_agent my_author/my_agent
   ```

### Managing Dependencies

1. Update dependencies:
   ```bash
   adev deps update -p parent_repo -c child_repo
   ```

### Development Workflow

1. Format code before committing:
   ```bash
   adev fmt -p . --changed-only
   ```


2. Run linting:
   ```bash
   adev lint -p . --changed-only
   ```

3. Run tests:
   ```bash
   adev test -p tests --coverage-report
   ```

## Next Steps

- Check the [CLI Reference](commands/index.md) for detailed command documentation
- Explore [FSM documentation](fsm.md) for state machine development
- Read [OpenAPI guide](openapi.md) for API integration
