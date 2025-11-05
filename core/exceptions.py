"""
Custom exceptions for Access Log Analyzer

This module defines all custom exceptions used throughout the application.
"""


class LogAnalyzerError(Exception):
    """Base exception for all Access Log Analyzer errors"""
    pass


class FileNotFoundError(LogAnalyzerError):
    """Raised when an input file is not found"""

    def __init__(self, file_path: str, message: str = None):
        self.file_path = file_path
        if message is None:
            message = f"File not found: {file_path}"
        super().__init__(message)


class InvalidFormatError(LogAnalyzerError):
    """Raised when log format is invalid or cannot be detected"""

    def __init__(self, message: str, format_type: str = None):
        self.format_type = format_type
        super().__init__(message)


class ParseError(LogAnalyzerError):
    """Raised when log parsing fails"""

    def __init__(self, message: str, line_number: int = None, line_content: str = None):
        self.line_number = line_number
        self.line_content = line_content
        if line_number:
            message = f"Parse error at line {line_number}: {message}"
        super().__init__(message)


class ValidationError(LogAnalyzerError):
    """Raised when input validation fails"""

    def __init__(self, parameter: str, message: str):
        self.parameter = parameter
        super().__init__(f"Validation error for '{parameter}': {message}")


class ConfigurationError(LogAnalyzerError):
    """Raised when configuration is invalid or missing"""

    def __init__(self, message: str, config_file: str = None):
        self.config_file = config_file
        if config_file:
            message = f"Configuration error in {config_file}: {message}"
        super().__init__(message)
