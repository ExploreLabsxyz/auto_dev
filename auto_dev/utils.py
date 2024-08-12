"""
Utilities for auto_dev.
"""
import json
import logging
import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from functools import reduce
from glob import glob
from pathlib import Path
from typing import Any, Callable, Optional, Union

import rich_click as click
import yaml
from aea.cli.utils.config import get_registry_path_from_cli_config
from aea.cli.utils.context import Context
from aea.configurations.base import AgentConfig
from rich.logging import RichHandler

from auto_dev.enums import FileOperation
from auto_dev.exceptions import NotFound, OperationError

from .constants import AUTONOMY_PACKAGES_FILE, DEFAULT_ENCODING, FileType


def get_logger(name: str = __name__, log_level: str = "INFO") -> logging.Logger:
    """
    Get the configured logger.

    Args:
        name (str): The name of the logger.
        log_level (str): The logging level.

    Returns:
        logging.Logger: Configured logger instance.
    """
    handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
    )
    datefmt = "%H:%M:%S"
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), "INFO"),
        datefmt=datefmt,
        format="%(levelname)s - %(message)s",
        handlers=[handler],
    )
    log = logging.getLogger(name)
    log.setLevel(getattr(logging, log_level.upper(), "INFO"))
    return log


def get_packages():
    """Get the packages file."""
    with open(AUTONOMY_PACKAGES_FILE, "r", encoding=DEFAULT_ENCODING) as file:
        packages = json.load(file)
    dev_packages = packages["dev"]
    results = []
    for package in dev_packages:
        component_type, author, component_name, _ = package.split("/")
        package_path = Path(f"packages/{author}/{component_type}s/{component_name}")
        if not package_path.exists():
            raise FileNotFoundError(f"Package {package} not found at: {package_path} does not exist")
        results.append(package_path)
    return results


def has_package_code_changed(package_path: Path):
    """
    We use git to effectively check if the code has changed.
    We filter out any files that are ;
    - not tracked by git
    - have no changes to the code in;
      - the package itself
      - the tests for the package

    """
    if not package_path.exists():
        raise FileNotFoundError(f"Package {package_path} does not exist")
    command = f"git status --short {package_path}"
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    changed_files = [f for f in result.stdout.decode().split("\n") if f != '']
    changed_files = [f.replace(" M ", "") for f in changed_files]
    changed_files = [f.replace("?? ", "") for f in changed_files]
    return changed_files


def get_paths(path: Optional[str] = None, changed_only: bool = False):
    """Get the paths."""
    if not path and not Path(AUTONOMY_PACKAGES_FILE).exists():
        raise FileNotFoundError("No path was provided and no default packages file found")
    packages = get_packages() if not path else [Path(path)]

    if path and Path(path).is_file():
        return [path]

    if changed_only:
        all_changed_files = []
        for package in packages:
            changed_files = has_package_code_changed(package)
            if changed_files:
                all_changed_files += changed_files
        packages = all_changed_files
    else:
        python_files = [glob(f"{package}/**/*py", recursive=True) for package in packages]
        if not python_files:
            return []
        packages = reduce(lambda x, y: x + y, python_files)
    if not packages:
        return []

    def filter_git_interferace_files(file_path: str):
        regexs = [
            'M  ',
        ]
        for regex in regexs:
            if regex in file_path:
                return file_path.replace(regex, "")
        return file_path

    def filter_protobuf_files(file_path: str):
        regexs = [
            '_pb2.py',
        ]
        for regex in regexs:
            if regex in file_path:
                return True
        return False

    python_files = [f for f in packages if "__pycache__" not in f and f.endswith(".py")]
    python_files = [filter_git_interferace_files(f) for f in python_files]
    python_files = [f for f in python_files if not filter_protobuf_files(f)]
    return python_files


@contextmanager
def isolated_filesystem(copy_cwd: bool = False):
    """
    Context manager to create an isolated file system.
    And to navigate to it and then to clean it up.
    """
    original_path = Path.cwd()
    with tempfile.TemporaryDirectory(dir=tempfile.gettempdir()) as temp_dir:
        temp_dir_path = Path(temp_dir).resolve()
        os.chdir(temp_dir_path)
        if copy_cwd:
            # we copy the content of the original directory into the temporary one
            for file_name in os.listdir(original_path):
                if file_name == "__pycache__":
                    continue
                file_path = Path(original_path, file_name)
                if file_path.is_file():
                    shutil.copy(file_path, temp_dir_path)
                elif file_path.is_dir():
                    shutil.copytree(file_path, Path(temp_dir, file_name))
        yield str(Path(temp_dir_path))
    os.chdir(original_path)


@contextmanager
def change_dir(target_path):
    """
    Temporarily change the working directory.
    """
    original_path = str(Path.cwd())
    try:
        os.chdir(target_path)
        yield
    finally:
        os.chdir(original_path)


@contextmanager
def restore_directory():
    """
    Ensure working directory is restored.
    """
    original_dir = os.getcwd()
    try:
        yield
    finally:
        os.chdir(original_dir)


@contextmanager
def folder_swapper(dir_a: Union[str, Path], dir_b: Union[str, Path]):
    """
    A custom context manager that swaps the contents of two folders, allows the execution of logic
    within the context, and ensures the original folder contents are restored on exit, whether due
    to success or failure.
    """

    dir_a = Path(dir_a)
    dir_b = Path(dir_b)

    if not dir_a.exists() or not dir_b.exists():
        raise FileNotFoundError("One or both of the provided directories do not exist.")

    dir_a_backup = Path(tempfile.mkdtemp()) / "backup_a"
    dir_b_backup = Path(tempfile.mkdtemp()) / "backup_b"
    shutil.copytree(dir_a, dir_a_backup)
    shutil.copytree(dir_b, dir_b_backup)

    def overwrite(source_dir: Path, target_dir: Path) -> None:
        shutil.rmtree(dir_a)
        shutil.rmtree(dir_b)
        shutil.copytree(source_dir, dir_a)
        shutil.copytree(target_dir, dir_b)

    try:
        overwrite(dir_b_backup, dir_a_backup)
        yield
    finally:
        overwrite(dir_a_backup, dir_b_backup)
        shutil.rmtree(dir_a_backup.parent)
        shutil.rmtree(dir_b_backup.parent)


def snake_to_camel(string: str):
    """
    Convert a string from snake case to camel case.
    """
    return "".join(word.capitalize() for word in string.split("_"))


def camel_to_snake(string: str):
    """
    Convert a string from camel case to snake case.
    Note: If the string is all uppercase, it will be converted to lowercase.
    """
    if string.isupper():
        return string.lower()
    return "".join("_" + c.lower() if c.isupper() else c for c in string).lstrip("_")


def remove_prefix(text: str, prefix: str) -> str:
    """str.removeprefix"""

    return text[len(prefix) :] if prefix and text.startswith(prefix) else text


def remove_suffix(text: str, suffix: str) -> str:
    """str.removesuffix"""

    return text[: -len(suffix)] if suffix and text.endswith(suffix) else text


def load_aea_ctx(func: Callable[[click.Context, Any, Any], Any]) -> Callable[[click.Context, Any, Any], Any]:
    """Load aea Context and AgentConfig if aea-config.yaml exists"""

    def wrapper(ctx: click.Context, *args, **kwargs):
        aea_config = Path("aea-config.yaml")
        if not aea_config.exists():
            raise FileNotFoundError(f"Could not find {aea_config}")

        registry_path = get_registry_path_from_cli_config()
        ctx.aea_ctx = Context(cwd=".", verbosity="INFO", registry_path=registry_path)

        agent_config_yaml = yaml.safe_load(aea_config.read_text(encoding=DEFAULT_ENCODING))
        agent_config_json = json.loads(json.dumps(agent_config_yaml))
        ctx.aea_ctx.agent_config = AgentConfig.from_json(agent_config_json)

        return func(ctx, *args, **kwargs)

    wrapper.__name__ = func.__name__

    return wrapper


def write_to_file(file_path: str, content: Any, file_type: FileType = FileType.TEXT) -> None:
    """
    Write content to a file.
    """
    try:
        with open(file_path, "w", encoding=DEFAULT_ENCODING) as f:
            if file_type == FileType.TEXT:
                f.write(content)
            elif file_type == FileType.YAML:
                if isinstance(content, list):
                    yaml.dump_all(content, f, default_flow_style=False, sort_keys=False)
                else:
                    yaml.dump(content, f, default_flow_style=False, sort_keys=False)
            elif file_type == FileType.JSON:
                json.dump(content, f, separators=(',', ':'))
            else:
                raise ValueError(f"Invalid file_type, must be one of {list(FileType)}.")
    except Exception as e:
        raise ValueError(f"Error writing to file {file_path}: {e}") from e


def read_from_file(file_path: str, file_type: FileType = FileType.TEXT) -> Any:
    """
    Read content from a file.
    """
    try:
        with open(file_path, "r", encoding=DEFAULT_ENCODING) as f:
            if file_type == FileType.TEXT:
                return f.read()
            if file_type == FileType.YAML:
                return yaml.safe_load(f)
            if file_type == FileType.JSON:
                return json.load(f)
            raise ValueError(f"Invalid file_type, must be one of {list(FileType)}.")
    except Exception as e:
        raise ValueError(f"Error reading from file {file_path}: {e}") from e


# We want to use emojis as much as possible in all output.
@dataclass
class FileLoader:
    """File loader class."""

    file_path: Path
    file_type: FileType
    parse_data: bool = False
    _file_type_to_loader = {
        FileType.YAML: (yaml.safe_load, {}),
        FileType.JSON: (json.loads, {}),
    }
    _file_type_to_dumper = {
        FileType.YAML: (yaml.dump, {"default_flow_style": False, "sort_keys": False}),
        FileType.JSON: (json.dumps, {"separators": (',', ':'), "sort_keys": False, "indent": 4}),
    }

    def __post_init__(self):
        """Post init."""
        self.file_path = Path(self.file_path)
        for operation in self.supported_operations:
            setattr(  # noqa
                self,  # noqa
                operation.value,  # noqa
                lambda *args, **kwargs: self._exec_function(operation, *args, **kwargs),  # noqa  # noqa
            )  # noqa

    @property
    def supported_operations(self):
        """Supported operations. aligns the operations with the file type."""
        return {
            FileOperation.READ: self._file_type_to_loader.get(self.file_type),
            FileOperation.WRITE: self._file_type_to_dumper.get(self.file_type),
        }

    def _exec_function(self, func: Callable, *args, **kwargs):
        """Execute a function."""
        if not self.file_path.exists() and FileOperation(func) is FileOperation.READ:
            raise NotFound(f"The file {self.file_path} was not found⁉") from FileNotFoundError
        try:
            func_type = FileOperation(func)
        except ValueError as exc:
            raise OperationError(
                f"Operation {func} not supported for file type {self.file_type}. "
                + f"Only {list(self.supported_operations.keys())} supported."
            ) from exc
        if func_type not in self.supported_operations:
            raise OperationError(
                f"Operation {func} not supported for file type {self.file_type}. "
                + "Only {list(self.supported_operations.keys())} supported."
            )
        if self.file_type not in self._file_type_to_loader:
            raise OperationError(
                f"File type {self.file_type} not supported. Only {list(self._file_type_to_loader.keys())} supported."
            )
        loader_func, kwargs = self.supported_operations.get(func_type)
        if func_type is FileOperation.READ:
            return (
                loader_func(self.file_path.read_text(encoding=DEFAULT_ENCODING), **kwargs)
                if self.parse_data
                else self.file_path.read_text(encoding=DEFAULT_ENCODING)
            )
        if func_type is FileOperation.WRITE:
            return self.file_path.write_text(loader_func(*args, **kwargs), encoding=DEFAULT_ENCODING)
        raise OperationError(f"Operation {func} not supported")
