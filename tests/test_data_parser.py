"""
Tests for data_parser module
"""

import pytest
from pathlib import Path
from core.exceptions import FileNotFoundError, InvalidFormatError
from data_parser import recommendAccessLogFormat, parse_log_file_with_format


def test_recommend_format_file_not_found():
    """Test recommendAccessLogFormat with non-existent file"""
    with pytest.raises(FileNotFoundError):
        recommendAccessLogFormat("/nonexistent/file.log")


def test_recommend_format_alb_log(sample_alb_log):
    """Test format detection for ALB log"""
    result = recommendAccessLogFormat(str(sample_alb_log))

    assert 'logFormatFile' in result
    assert 'logPattern' in result
    assert 'patternType' in result
    assert 'fieldMap' in result
    assert 'successRate' in result
    assert 'confidence' in result

    # Verify it's detected as ALB
    assert result['patternType'] == 'ALB'
    assert result['confidence'] > 0.5


def test_recommend_format_creates_file(sample_alb_log, temp_dir):
    """Test that recommendAccessLogFormat creates logformat file"""
    result = recommendAccessLogFormat(str(sample_alb_log))

    log_format_file = Path(result['logFormatFile'])
    assert log_format_file.exists()
    assert log_format_file.parent == sample_alb_log.parent
    assert log_format_file.name.startswith('logformat_')


def test_recommend_format_uses_existing(sample_alb_log, temp_dir):
    """Test that existing logformat file is reused"""
    # First call creates the file
    result1 = recommendAccessLogFormat(str(sample_alb_log))
    log_format_file1 = result1['logFormatFile']

    # Second call should reuse the same file
    result2 = recommendAccessLogFormat(str(sample_alb_log))
    log_format_file2 = result2['logFormatFile']

    assert log_format_file1 == log_format_file2


def test_log_regex_override_recommend_and_parse(sample_apache_log):
    """Test log_regex override uses GROK and named groups for parsing"""
    log_regex = r'(?P<client_ip>\d+\.\d+\.\d+\.\d+) [^ ]+ [^ ]+ \[[^\]]+\] "(?P<request_method>[A-Z]+) (?P<request_url>[^ ]+) (?P<request_proto>[^"]+)" (?P<status>\d{3}) (?P<bytes_sent>[^ ]+)'
    config_path = sample_apache_log.parent / "config.yaml"
    config_path.write_text(
        f"log_regex: '{log_regex}'\n"
        "apache_log_format: ''\n",
        encoding="utf-8",
    )

    result = recommendAccessLogFormat(str(sample_apache_log))

    assert result["patternType"] == "GROK"
    assert result["logPattern"] == log_regex

    df = parse_log_file_with_format(
        str(sample_apache_log),
        result["logFormatFile"],
        use_multiprocessing=False,
    )

    required_columns = {
        "client_ip",
        "request_method",
        "request_url",
        "request_proto",
        "status",
        "bytes_sent",
    }
    assert required_columns.issubset(set(df.columns))
    assert len(df) >= 1
    first_row = df.iloc[0]
    assert first_row["request_method"] == "GET"
    assert first_row["request_url"] == "/api/test"
    assert str(first_row["status"]) == "200"


def test_apache_log_format_override_recommend_and_parse(sample_apache_log):
    """Test apache_log_format override uses HTTPD converter output"""
    config_path = sample_apache_log.parent / "config.yaml"
    config_path.write_text(
        "log_regex: ''\n"
        "apache_log_format: '%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"'\n",
        encoding="utf-8",
    )

    result = recommendAccessLogFormat(str(sample_apache_log))

    assert result["patternType"] == "HTTPD"
    assert result.get("columns")
    assert "request" in result["columns"]

    df = parse_log_file_with_format(
        str(sample_apache_log),
        result["logFormatFile"],
        use_multiprocessing=False,
    )

    required_columns = {"request_method", "request_url", "request_proto", "status", "client_ip"}
    assert required_columns.issubset(set(df.columns))
    assert len(df) >= 1
    first_row = df.iloc[0]
    assert first_row["request_method"] == "GET"
    assert first_row["request_url"] == "/api/test"
    assert first_row["request_proto"] == "HTTP/1.1"


def test_log_regex_takes_precedence_over_apache_log_format(sample_apache_log):
    """Test precedence: log_regex override wins when both are set"""
    log_regex = r'(?P<client_ip>\d+\.\d+\.\d+\.\d+) [^ ]+ [^ ]+ \[[^\]]+\] "(?P<request>[^"]+)" (?P<status>\d{3}) (?P<bytes_sent>[^ ]+)'
    config_path = sample_apache_log.parent / "config.yaml"
    config_path.write_text(
        f"log_regex: '{log_regex}'\n"
        "apache_log_format: '%h %l %u %t \"%r\" %>s %b'\n",
        encoding="utf-8",
    )

    result = recommendAccessLogFormat(str(sample_apache_log))

    assert result["patternType"] == "GROK"
    assert result["logPattern"] == log_regex


def test_invalid_log_regex_raises_invalid_format_error(sample_apache_log):
    """Test invalid config log_regex raises InvalidFormatError"""
    config_path = sample_apache_log.parent / "config.yaml"
    config_path.write_text(
        "log_regex: '('\n"
        "apache_log_format: ''\n",
        encoding="utf-8",
    )

    with pytest.raises(InvalidFormatError):
        recommendAccessLogFormat(str(sample_apache_log))
