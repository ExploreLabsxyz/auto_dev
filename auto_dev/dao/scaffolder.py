import json
from typing import Any, Dict, List
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from openapi_spec_validator import validate_spec

from auto_dev.enums import FileType
from auto_dev.utils import write_to_file, read_from_file
from auto_dev.constants import JINJA_TEST_DAO_FOLDER
from auto_dev.dao.generator import DAOGenerator
from auto_dev.dao.dummy_data import generate_dummy_data


class DAOScaffolder:
    """DAOScaffolder class is responsible for scaffolding DAO classes and test scripts."""
    def __init__(self, logger: Any, verbose: bool):
        self.logger = logger
        self.verbose = verbose
        self.env = Environment(
            loader=FileSystemLoader(JINJA_TEST_DAO_FOLDER),
            autoescape=True,
            lstrip_blocks=True,
            trim_blocks=True
        )
        self.component_yaml = Path.cwd() / "component.yaml"

    def scaffold(self) -> None:
        """Scaffold DAO classes and test scripts."""
        try:
            self.logger.info("Starting DAO scaffolding process")
            component_data = self._load_component_yaml()
            api_spec_path = self._get_api_spec_path(component_data)
            api_spec = self._load_and_validate_api_spec(api_spec_path)

            models = api_spec.get("components", {}).get("schemas", {})
            paths = api_spec.get("paths", {})

            json_dummy_data = self._generate_dummy_data(models)
            test_dummy_data = self._generate_dummy_data(models)

            dao_classes = self._generate_dao_classes(models, paths)

            self._generate_and_save_test_script(dao_classes, test_dummy_data)

            self._save_dao_classes(dao_classes, json_dummy_data)

            self.logger.info("DAO scaffolding and test script generation completed successfully.")
        except Exception as e:
            self.logger.exception(f"DAO scaffolding failed: {e!s}")
            raise

    def _load_component_yaml(self) -> Dict[str, Any]:
        try:
            if not self.component_yaml.exists():
                msg = f"component.yaml not found in the current directory: {self.component_yaml}"
                raise FileNotFoundError(msg)
            return read_from_file(self.component_yaml, FileType.YAML)
        except yaml.YAMLError as e:
            self.logger.exception(f"Error parsing component YAML: {e!s}")
            raise
        except OSError as e:
            self.logger.exception(f"Error reading component YAML file: {e!s}")
            raise

    def _get_api_spec_path(self, component_data: Dict[str, Any]) -> str:
        api_spec_path = component_data.get("api_spec")
        if not api_spec_path:
            msg = "No 'api_spec' key found in the component.yaml file."
            raise ValueError(msg)
        return api_spec_path

    def _load_and_validate_api_spec(self, api_spec_path: str) -> Dict[str, Any]:
        try:
            api_spec_path = Path(api_spec_path)
            self.logger.info(f"Attempting to load API spec from: {api_spec_path}")

            if not api_spec_path.exists():
                msg = f"API spec file not found: {api_spec_path}"
                raise FileNotFoundError(msg)

            with api_spec_path.open("r") as f:
                if api_spec_path.suffix.lower() in {".yaml", ".yml"}:
                    self.logger.info("Detected YAML file, parsing as YAML")
                    api_spec = yaml.safe_load(f)
                else:
                    self.logger.info("Attempting to parse as JSON")
                    api_spec = json.load(f)

            self.logger.info("Successfully loaded API spec, validating...")
            validate_spec(api_spec)
            self.logger.info("API spec validation successful")

            if "components" not in api_spec or "schemas" not in api_spec["components"]:
                msg = "OpenAPI spec does not contain explicit models in 'components/schemas'."
                self.logger.error(msg)
                raise ValueError(msg)

            return api_spec

        except yaml.YAMLError as e:
            self.logger.exception(f"Error parsing API spec YAML: {e!s}")
            raise
        except json.JSONDecodeError as e:
            self.logger.exception(f"Error parsing API spec JSON: {e!s}")
            raise
        except FileNotFoundError as e:
            self.logger.exception(str(e))
            raise
        except Exception as e:
            self.logger.exception(f"Unexpected error loading or validating API spec: {e!s}")
            raise

    def _generate_dao_classes(self, models: Dict[str, Any], paths: Dict[str, Any]) -> Dict[str, str]:
        try:
            dao_generator = DAOGenerator(models, paths)
            return dao_generator.generate_dao_classes()
        except Exception as e:
            self.logger.exception(f"Error generating DAO classes: {e!s}")
            raise

    def _generate_dummy_data(self, models: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return generate_dummy_data(models)
        except Exception as e:
            self.logger.exception(f"Error generating dummy data: {e!s}")
            raise

    def _output_results(self, dao_classes: Dict[str, str], dummy_data: Dict[str, Any]) -> None:
        if self.verbose:
            self.logger.info("Generated DAO classes:")
            for class_name, class_code in dao_classes.items():
                self.logger.info(f"\n{class_name}:\n{class_code}")

            self.logger.info("\nGenerated dummy data for tests:")
            self.logger.info(json.dumps(dummy_data, indent=2))

    def _save_dao_classes(self, dao_classes: Dict[str, str], json_dummy_data: Dict[str, Any]) -> None:
        try:
            dao_dir = Path("generated/dao")
            dao_dir.mkdir(parents=True, exist_ok=True)
            for class_name, class_code in dao_classes.items():
                file_path = dao_dir / f"{class_name.lower()}.py"
                write_to_file(file_path, class_code, FileType.PYTHON)
                self.logger.info(f"Saved DAO class: {file_path}")

                model_name = class_name.replace("DAO", "")
                json_file_path = dao_dir / f"{model_name.lower()}.json"
                if not json_file_path.exists(): 
                    write_to_file(json_file_path, [json_dummy_data[model_name]], FileType.JSON, indent=2)
                    self.logger.info(f"Saved initial dummy data JSON: {json_file_path}")

        except OSError as e:
            self.logger.exception(f"Error saving generated files: {e!s}")
            raise

    def _generate_and_save_test_script(self, dao_classes: Dict[str, str], test_dummy_data: Dict[str, Any]) -> None:
        dao_class_names = list(dao_classes.keys())
        test_script = self._generate_test_script(dao_class_names, test_dummy_data)
        self._save_test_script(test_script)

    def _generate_test_script(self, dao_classes: List[str], test_dummy_data: Dict[str, Any]) -> str:
        template = self.env.get_template("test_dao.jinja")
        return template.render(
            dao_classes=dao_classes,
            dummy_data=test_dummy_data
        )

    def _save_test_script(self, test_script: str) -> None:
        test_script_path = Path("generated/test_dao.py")
        test_script_path.parent.mkdir(parents=True, exist_ok=True)
        write_to_file(test_script_path, test_script, FileType.PYTHON)
        self.logger.info(f"Test script saved to: {test_script_path}")
