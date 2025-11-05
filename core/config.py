"""
Configuration management for Access Log Analyzer

Provides centralized configuration loading and caching.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
import os

from .exceptions import ConfigurationError, FileNotFoundError as CustomFileNotFoundError
from .logging_config import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """
    Centralized configuration management with caching.

    This class follows the Singleton pattern to ensure only one
    instance manages configuration across the application.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._config: Optional[Dict[str, Any]] = None
        self._config_path: Optional[Path] = None
        self._initialized = True

    def find_config(
        self,
        input_file: Optional[str] = None,
        custom_paths: Optional[List[Path]] = None
    ) -> Optional[Path]:
        """
        Search for config.yaml in multiple standard locations.

        Search order:
        1. Same directory as input file
        2. Parent directory of input file
        3. Current working directory
        4. Script directory
        5. Custom paths (if provided)

        Args:
            input_file: Input file path to use as reference
            custom_paths: Additional paths to search

        Returns:
            Path to config.yaml if found, None otherwise
        """
        search_paths = []

        # Add paths based on input file
        if input_file:
            input_path = Path(input_file)
            if input_path.exists():
                # Same directory as input file
                search_paths.append(input_path.parent / 'config.yaml')
                # Parent directory
                search_paths.append(input_path.parent.parent / 'config.yaml')

        # Current working directory
        search_paths.append(Path.cwd() / 'config.yaml')

        # Script directory (where this module is located)
        script_dir = Path(__file__).parent.parent
        search_paths.append(script_dir / 'config.yaml')

        # Custom paths
        if custom_paths:
            search_paths.extend(custom_paths)

        # Search for config file
        for path in search_paths:
            if path.exists():
                logger.debug(f"Found config file: {path}")
                return path

        logger.debug("No config.yaml found in standard locations")
        return None

    def load_config(
        self,
        config_path: Optional[Path] = None,
        force_reload: bool = False
    ) -> Dict[str, Any]:
        """
        Load and cache configuration from file.

        Args:
            config_path: Path to config file. If None, searches standard locations.
            force_reload: Force reload even if already cached

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file not found
            ConfigurationError: If config file is invalid
        """
        # Return cached config if available and not forcing reload
        if not force_reload and self._config is not None:
            if config_path is None or config_path == self._config_path:
                logger.debug("Using cached configuration")
                return self._config

        # Find config file if not provided
        if config_path is None:
            config_path = self.find_config()
            if config_path is None:
                logger.warning("No config.yaml found, using defaults")
                return {}

        # Validate config file exists
        if not config_path.exists():
            raise CustomFileNotFoundError(
                str(config_path),
                f"Configuration file not found: {config_path}"
            )

        # Load configuration
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if config is None:
                config = {}

            # Cache configuration
            self._config = config
            self._config_path = config_path

            logger.info(f"Loaded configuration from: {config_path}")
            return config

        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML format: {e}",
                str(config_path)
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration: {e}",
                str(config_path)
            )

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        if self._config is None:
            self.load_config()

        # Support dot notation (e.g., 'server.port')
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def reload(self):
        """Force reload configuration from file"""
        if self._config_path:
            self.load_config(self._config_path, force_reload=True)

    def clear_cache(self):
        """Clear cached configuration"""
        self._config = None
        self._config_path = None
        logger.debug("Configuration cache cleared")


# Global instance
_config_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    """Get the global ConfigManager instance"""
    return _config_manager


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Convenience function to load configuration.

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary
    """
    return _config_manager.load_config(config_path)
