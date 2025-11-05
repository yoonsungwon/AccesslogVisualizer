"""
Core module for Access Log Analyzer

This module provides common utilities and infrastructure:
- Custom exceptions
- Configuration management
- Logging setup
- Utility classes (FieldMapper, ParamParser)
"""

from .exceptions import (
    LogAnalyzerError,
    FileNotFoundError,
    InvalidFormatError,
    ParseError,
    ValidationError,
    ConfigurationError
)
from .config import ConfigManager
from .logging_config import setup_logger, get_logger
from .utils import FieldMapper, ParamParser

__all__ = [
    'LogAnalyzerError',
    'FileNotFoundError',
    'InvalidFormatError',
    'ParseError',
    'ValidationError',
    'ConfigurationError',
    'ConfigManager',
    'setup_logger',
    'get_logger',
    'FieldMapper',
    'ParamParser',
]
