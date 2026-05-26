"""
YAML configuration loader for AetherTest.
"""
import yaml
import os
from typing import Dict, Any, Optional
from pathlib import Path


class YAMLConfigLoader:
    """Loads configuration from YAML files."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the YAML config loader.

        Args:
            config_path: Path to the YAML configuration file.
                        If None, looks for config.yaml in current directory.
        """
        if config_path is None:
            # Look for config.yaml in current directory
            self.config_path = Path("config.yaml")
        else:
            self.config_path = Path(config_path)

        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    self._config = yaml.safe_load(f) or {}
            except Exception as e:
                raise RuntimeError(f"Failed to load configuration from {self.config_path}: {e}")
        else:
            # Create default config if none exists
            self._config = self._get_default_config()
            self._save_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "api": {
                "base_url": "http://127.0.0.1:8000",
                "auth": {
                    "type": "none",
                    "username": "",
                    "password": "",
                    "token": "",
                    "key_name": "X-API-Key",
                    "key_value": ""
                },
                "endpoints": {
                    "auth_login": "/auth/login",
                    "resource_base": "/api/v1/resources",
                    "health_check": "/health",
                    "batch_submit": "/api/v1/batch",
                    "batch_status": "/api/v1/batch/{batch_id}",
                    "config_get": "/api/v1/config",
                    "config_update": "/api/v1/config",
                    "ingest": "/api/v1/ingest",
                    "process_status": "/api/v1/process/{ingest_id}",
                    "results_get": "/api/v1/results/{ingest_id}"
                }
            },
            "simulation": {
                "agents_per_persona": 5,
                "num_interactions": 8,
                "duration_minutes": 0,
                "save_to_db": true,
                "scenarios": ["basic_interaction"]
            },
            "agents": {
                "personas": {
                    "cautious_devops": true,
                    "aggressive_founder": true,
                    "sre_engineer": true,
                    "qa_engineer": true
                },
                "custom": {}
            },
            "output": {
                "level": "normal",
                "save_logs": false,
                "log_file": "aethertest.log",
                "generate_report": false,
                "report_file": "aethertest_report.html"
            }
        }

    def _save_default_config(self) -> None:
        """Save default configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self._config, f, default_flow_style=False, indent=2)
        except Exception as e:
            # Non-critical - just warn
            print(f"Warning: Could not save default config to {self.config_path}: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            key_path: Dot-separated path to the configuration value (e.g., "api.base_url")
            default: Default value to return if key is not found

        Returns:
            The configuration value or default if not found
        """
        keys = key_path.split('.')
        value = self._config

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def get_api_base_url(self) -> str:
        """Get the API base URL."""
        return self.get("api.base_url", "http://127.0.0.1:8000")

    def get_api_auth_config(self) -> Dict[str, Any]:
        """Get the API authentication configuration."""
        return self.get("api.auth", {
            "type": "none",
            "username": "",
            "password": "",
            "token": "",
            "key_name": "X-API-Key",
            "key_value": ""
        })

    def get_endpoint_config(self) -> Dict[str, str]:
        """Get the endpoint configuration with resolved placeholders."""
        endpoints = self.get("api.endpoints", {
            "auth_login": "/auth/login",
            "resource_base": "/api/v1/resources",
            "health_check": "/health",
            "batch_submit": "/api/v1/batch",
            "batch_status": "/api/v1/batch/{batch_id}",
            "config_get": "/api/v1/config",
            "config_update": "/api/v1/config",
            "ingest": "/api/v1/ingest",
            "process_status": "/api/v1/process/{ingest_id}",
            "results_get": "/api/v1/results/{ingest_id}"
        })

        # Resolve any placeholders in the endpoint values
        resolved_endpoints = {}
        for key, value in endpoints.items():
            # Replace placeholders like {auth_login} with their actual values
            resolved_value = value
            for placeholder_key, placeholder_value in endpoints.items():
                placeholder = "{" + placeholder_key + "}"
                if placeholder in resolved_value:
                    resolved_value = resolved_value.replace(placeholder, placeholder_value)
            resolved_endpoints[key] = resolved_value

        return resolved_endpoints

    def get_simulation_config(self) -> Dict[str, Any]:
        """Get the simulation configuration."""
        return self.get("simulation", {
            "agents_per_persona": 5,
            "num_interactions": 8,
            "duration_minutes": 0,
            "save_to_db": True,
            "scenarios": ["basic_interaction"]
        })

    def get_agents_config(self) -> Dict[str, Any]:
        """Get the agents configuration."""
        return self.get("agents", {
            "personas": {
                "cautious_devops": True,
                "aggressive_founder": True,
                "sre_engineer": True,
                "qa_engineer": True
            },
            "custom": {}
        })

    def get_output_config(self) -> Dict[str, Any]:
        """Get the output configuration."""
        return self.get("output", {
            "level": "normal",
            "save_logs": False,
            "log_file": "aethertest.log",
            "generate_report": False,
            "report_file": "aethertest_report.html"
        })

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()

    def update(self, updates: Dict[str, Any]) -> None:
        """
        Update configuration with new values.

        Args:
            updates: Dictionary of updates to apply
        """
        def _update_dict(d: Dict[str, Any], u: Dict[str, Any]) -> Dict[str, Any]:
            for k, v in u.items():
                if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                    d[k] = _update_dict(d[k], v)
                else:
                    d[k] = v
            return d

        self._config = _update_dict(self._config, updates)
        self._save_config()

    def _save_config(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self._config, f, default_flow_style=False, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to save configuration to {self.config_path}: {e}")