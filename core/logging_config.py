"""
Logging configuration for Access Log Analyzer

Provides centralized logging setup with both console and file handlers.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


# Default log format
DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DETAILED_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'

# Log levels mapping
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# Global logger registry
_loggers = {}


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: str = 'INFO',
    console_output: bool = True,
    file_output: bool = False,
    detailed: bool = False
) -> logging.Logger:
    """
    Setup a logger with console and/or file handlers.

    Args:
        name: Logger name (usually __name__)
        log_file: Log file path (if None, uses default: logs/access_log_analyzer.log)
        level: Log level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        console_output: Enable console output
        file_output: Enable file output
        detailed: Use detailed format with filename and line number

    Returns:
        Configured logger instance
    """
    # Check if logger already exists
    if name in _loggers:
        return _loggers[name]

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVELS.get(level.upper(), logging.INFO))
    logger.handlers.clear()  # Clear any existing handlers

    # Choose format
    fmt = DETAILED_FORMAT if detailed else DEFAULT_FORMAT
    formatter = logging.Formatter(fmt)

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(LOG_LEVELS.get(level.upper(), logging.INFO))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if file_output:
        if log_file is None:
            # Create logs directory if it doesn't exist
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d')
            log_file = log_dir / f"access_log_analyzer_{timestamp}.log"

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Always log DEBUG to file
        file_handler.setFormatter(logging.Formatter(DETAILED_FORMAT))
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    # Register logger
    _loggers[name] = logger

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with default settings.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    if name in _loggers:
        return _loggers[name]

    return setup_logger(name)


def set_log_level(level: str):
    """
    Set log level for all registered loggers.

    Args:
        level: Log level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    """
    log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
    for logger in _loggers.values():
        logger.setLevel(log_level)
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(log_level)


def enable_file_logging(log_file: Optional[str] = None):
    """
    Enable file logging for all registered loggers.

    Args:
        log_file: Log file path
    """
    if log_file is None:
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d')
        log_file = log_dir / f"access_log_analyzer_{timestamp}.log"

    formatter = logging.Formatter(DETAILED_FORMAT)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    for logger in _loggers.values():
        # Check if file handler already exists
        has_file_handler = any(
            isinstance(h, logging.FileHandler) for h in logger.handlers
        )
        if not has_file_handler:
            logger.addHandler(file_handler)


def disable_file_logging():
    """Disable file logging for all registered loggers."""
    for logger in _loggers.values():
        logger.handlers = [
            h for h in logger.handlers
            if not isinstance(h, logging.FileHandler)
        ]


# Setup default root logger
_root_logger = setup_logger('access_log_analyzer', level='INFO')
