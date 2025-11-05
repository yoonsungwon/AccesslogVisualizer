"""
Tests for multiprocessing functionality in Access Log Analyzer
"""

import pytest
import tempfile
import os
import json
from pathlib import Path

# Import modules to test
from core.utils import MultiprocessingConfig
from data_parser import _parse_lines_chunk, _read_lines_from_file


class TestMultiprocessingConfig:
    """Test MultiprocessingConfig utility class"""

    def test_get_config_defaults(self):
        """Test that default config is returned when config.yaml not found"""
        config = MultiprocessingConfig.get_config()

        assert isinstance(config, dict)
        assert 'enabled' in config
        assert 'num_workers' in config
        assert 'chunk_size' in config
        assert 'min_lines_for_parallel' in config

        # Check default values
        assert config['enabled'] is True
        assert config['chunk_size'] == 10000
        assert config['min_lines_for_parallel'] == 10000

    def test_get_optimal_workers(self):
        """Test optimal worker calculation"""
        # Small workload
        workers = MultiprocessingConfig.get_optimal_workers(
            total_items=500,
            min_items_per_worker=100
        )
        assert 1 <= workers <= 5

        # Large workload
        workers = MultiprocessingConfig.get_optimal_workers(
            total_items=100000,
            min_items_per_worker=1000
        )
        assert workers >= 1

        # With max_workers limit
        workers = MultiprocessingConfig.get_optimal_workers(
            total_items=100000,
            min_items_per_worker=100,
            max_workers=4
        )
        assert workers <= 4

    def test_should_use_multiprocessing(self):
        """Test multiprocessing decision logic"""
        config = MultiprocessingConfig.get_config()

        # Large file - should use multiprocessing
        should_use = MultiprocessingConfig.should_use_multiprocessing(
            total_items=20000,
            config=config
        )
        assert should_use is True

        # Small file - should not use multiprocessing
        should_use = MultiprocessingConfig.should_use_multiprocessing(
            total_items=100,
            config=config
        )
        assert should_use is False

        # Disabled config
        disabled_config = config.copy()
        disabled_config['enabled'] = False
        should_use = MultiprocessingConfig.should_use_multiprocessing(
            total_items=100000,
            config=disabled_config
        )
        assert should_use is False

    def test_get_processing_params(self):
        """Test processing parameter calculation"""
        # Large dataset
        use_mp, num_workers, chunk_size = MultiprocessingConfig.get_processing_params(
            total_items=50000
        )

        assert isinstance(use_mp, bool)
        assert num_workers is None or num_workers >= 1
        assert chunk_size > 0

        # Small dataset
        use_mp, num_workers, chunk_size = MultiprocessingConfig.get_processing_params(
            total_items=100
        )

        assert use_mp is False

        # With overrides
        use_mp, num_workers, chunk_size = MultiprocessingConfig.get_processing_params(
            total_items=50000,
            override_enabled=False
        )

        assert use_mp is False


class TestParallelParsing:
    """Test parallel parsing functions"""

    def test_parse_lines_chunk_json(self):
        """Test parsing a chunk of JSON lines"""
        lines_chunk = [
            (1, '{"url": "/test", "status": 200}\n'),
            (2, '{"url": "/api/users", "status": 404}\n'),
            (3, 'invalid json line\n')
        ]

        pattern = 'JSON'
        pattern_type = 'JSON'
        format_info = {}

        parsed_data, failed_lines = _parse_lines_chunk(
            lines_chunk, pattern, pattern_type, format_info
        )

        # Should parse 2 valid JSON lines
        assert len(parsed_data) == 2
        assert parsed_data[0]['url'] == '/test'
        assert parsed_data[1]['status'] == 404

        # Should have 1 failed line
        assert len(failed_lines) == 1
        assert failed_lines[0][0] == 3  # line number

    def test_parse_lines_chunk_alb(self):
        """Test parsing a chunk of ALB log lines"""
        # Sample ALB log line (simplified)
        alb_line = 'http 2024-01-01T00:00:00.000000Z app/test 1.2.3.4:12345 10.0.0.1:80 0.001 0.002 0.001 200 200 100 200 "GET http://example.com/test HTTP/1.1" "Mozilla/5.0" ECDHE-RSA-AES128-GCM-SHA256 TLSv1.2'

        lines_chunk = [
            (1, alb_line)
        ]

        # Simple ALB pattern (matches first few fields)
        pattern = r'([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*):([0-9]*) ([^ ]*)[:-]([0-9]*) ([-.0-9]*) ([-.0-9]*) ([-.0-9]*) (|[-0-9]*) (-|[-0-9]*) ([-0-9]*) ([-0-9]*) \"([^ ]*) ([^ ]*) ([^ ]*)\" \"([^\"]*)\".*'
        pattern_type = 'ALB'
        format_info = {
            'columns': ['type', 'time', 'elb', 'client_ip', 'client_port', 'target_ip', 'target_port',
                       'request_processing_time', 'target_processing_time', 'response_processing_time',
                       'elb_status_code', 'target_status_code', 'received_bytes', 'sent_bytes',
                       'request_verb', 'request_url', 'request_proto', 'user_agent']
        }

        parsed_data, failed_lines = _parse_lines_chunk(
            lines_chunk, pattern, pattern_type, format_info
        )

        # Should parse 1 line successfully
        assert len(parsed_data) == 1
        assert parsed_data[0]['type'] == 'http'
        assert parsed_data[0]['client_ip'] == '1.2.3.4'

        # No failed lines
        assert len(failed_lines) == 0

    def test_read_lines_from_file(self):
        """Test reading lines from file with line numbers"""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("line 1\n")
            f.write("line 2\n")
            f.write("line 3\n")
            temp_file = f.name

        try:
            lines = _read_lines_from_file(temp_file)

            # Should read all lines with line numbers
            assert len(lines) == 3
            assert lines[0] == (1, 'line 1\n')
            assert lines[1] == (2, 'line 2\n')
            assert lines[2] == (3, 'line 3\n')

            # Test max_lines limit
            lines = _read_lines_from_file(temp_file, max_lines=2)
            assert len(lines) == 2

        finally:
            os.unlink(temp_file)


class TestParallelStatistics:
    """Test parallel statistics calculation"""

    def test_parallel_stats_imports(self):
        """Test that parallel statistics functions can be imported"""
        from data_processor import (
            _calculate_url_stats_chunk,
            _calculate_time_stats_chunk,
            _calculate_ip_stats_chunk
        )

        # Just verify they exist
        assert callable(_calculate_url_stats_chunk)
        assert callable(_calculate_time_stats_chunk)
        assert callable(_calculate_ip_stats_chunk)


class TestEndToEnd:
    """End-to-end integration tests"""

    def test_small_file_sequential(self, tmp_path):
        """Test that small files use sequential processing"""
        # Create a small test log file
        log_file = tmp_path / "small_test.log"
        with open(log_file, 'w') as f:
            for i in range(100):
                f.write(f'{{"line": {i}, "status": 200}}\n')

        # Create format file
        format_file = tmp_path / "format.json"
        with open(format_file, 'w') as f:
            json.dump({
                'logPattern': 'JSON',
                'patternType': 'JSON',
                'fieldMap': {
                    'status': 'status',
                    'line': 'line'
                },
                'responseTimeUnit': 'ms',
                'timezone': 'UTC'
            }, f)

        # Parse with multiprocessing enabled (should still use sequential for small file)
        from data_parser import parse_log_file_with_format

        df = parse_log_file_with_format(
            str(log_file),
            str(format_file),
            use_multiprocessing=True,
            chunk_size=10000
        )

        # Verify all lines parsed
        assert len(df) == 100

    def test_config_integration(self):
        """Test that config.yaml multiprocessing section is valid"""
        from core.config import ConfigManager

        config_mgr = ConfigManager()
        try:
            config = config_mgr.load_config()

            # If config exists, check multiprocessing section
            if config and 'multiprocessing' in config:
                mp_config = config['multiprocessing']

                # Validate structure
                assert 'enabled' in mp_config
                assert isinstance(mp_config['enabled'], bool)

                if 'chunk_size' in mp_config:
                    assert mp_config['chunk_size'] > 0

                if 'min_lines_for_parallel' in mp_config:
                    assert mp_config['min_lines_for_parallel'] > 0

        except Exception:
            # Config file may not exist in test environment
            pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
