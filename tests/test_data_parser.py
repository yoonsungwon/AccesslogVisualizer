"""
Tests for data_parser module
"""

import pytest
from pathlib import Path
from core.exceptions import FileNotFoundError
from data_parser import recommendAccessLogFormat


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
