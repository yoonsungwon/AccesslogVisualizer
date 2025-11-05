"""
Tests for core.exceptions module
"""

import pytest
from core.exceptions import (
    LogAnalyzerError,
    FileNotFoundError,
    InvalidFormatError,
    ParseError,
    ValidationError,
    ConfigurationError
)


def test_base_exception():
    """Test LogAnalyzerError base exception"""
    with pytest.raises(LogAnalyzerError):
        raise LogAnalyzerError("Test error")


def test_file_not_found_error():
    """Test FileNotFoundError"""
    error = FileNotFoundError("/path/to/file.log")
    assert error.file_path == "/path/to/file.log"
    assert "file.log" in str(error)


def test_file_not_found_error_custom_message():
    """Test FileNotFoundError with custom message"""
    error = FileNotFoundError("/path/to/file.log", "Custom message")
    assert error.file_path == "/path/to/file.log"
    assert "Custom message" in str(error)


def test_invalid_format_error():
    """Test InvalidFormatError"""
    error = InvalidFormatError("Invalid log format", format_type="ALB")
    assert error.format_type == "ALB"
    assert "Invalid log format" in str(error)


def test_parse_error():
    """Test ParseError"""
    error = ParseError("Parsing failed", line_number=42, line_content="invalid line")
    assert error.line_number == 42
    assert error.line_content == "invalid line"
    assert "line 42" in str(error)


def test_parse_error_without_line():
    """Test ParseError without line number"""
    error = ParseError("Parsing failed")
    assert error.line_number is None
    assert "Parsing failed" in str(error)


def test_validation_error():
    """Test ValidationError"""
    error = ValidationError("param1", "Invalid value")
    assert error.parameter == "param1"
    assert "param1" in str(error)
    assert "Invalid value" in str(error)


def test_configuration_error():
    """Test ConfigurationError"""
    error = ConfigurationError("Missing key", config_file="config.yaml")
    assert error.config_file == "config.yaml"
    assert "config.yaml" in str(error)
    assert "Missing key" in str(error)


def test_exception_hierarchy():
    """Test exception hierarchy"""
    assert issubclass(FileNotFoundError, LogAnalyzerError)
    assert issubclass(InvalidFormatError, LogAnalyzerError)
    assert issubclass(ParseError, LogAnalyzerError)
    assert issubclass(ValidationError, LogAnalyzerError)
    assert issubclass(ConfigurationError, LogAnalyzerError)
