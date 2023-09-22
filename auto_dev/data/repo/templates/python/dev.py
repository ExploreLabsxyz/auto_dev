"""
Template file for the the workflows/dev.yml file

"""
EXTENSION = ".yml"
TEMPLATE = """
# This is a basic workflow to help you get started with Actions

name: Dependency Workflows
# Controls when the action will run.
on:
  # Triggers the workflow on push or pull request events but only for the master branch
  pull_request_target:
    types:
      - opened
    branches:
      - 'main'
      - 'master'
    paths:
      - 'pyproject.toml'

  # Allows you to run this workflow manually from the Actions tab
  workflow_dispatch:

# A workflow run is made up of one or more jobs that can run sequentially or in parallel
jobs:
  check_deps:
    strategy:
      matrix:
        python-versions:
        - {python_versions}
        os:
        - ubuntu-20.04
    env:
      PYTHONPATH: .
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: ${{ matrix.python-versions }}

      - name: Install ci dependencies
        run: |
          make are_deps_dirty && exit 0
          python -m pip install --upgrade pip
          pip install poetry tox-gh-actions tox-poetry

      - name: Install application deps
        run: |
          make are_deps_dirty && exit 0
          poetry install

      - name: Lock application deps
        run: |
          make are_deps_dirty || poetry lock
          echo "No change in dependencies not locking."
"""
DIR = "./.github/workflows/"
