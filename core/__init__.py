"""
Core module for Access Log Analyzer

This module provides common utilities and infrastructure:
- Custom exceptions
- Configuration management
- Logging setup
"""

from .exceptions import (
    LogAnalyzerError,
    FileNotFoundError,
    InvalidFormatError,
    ParseError,
    ValidationError
)
from .config import ConfigManager
from .logging_config import setup_logger, get_logger

__all__ = [
    'LogAnalyzerError',
    'FileNotFoundError',
    'InvalidFormatError',
    'ParseError',
    'ValidationError',
    'ConfigManager',
    'setup_logger',
    'get_logger',
]
