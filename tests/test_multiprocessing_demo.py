#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Demo script to test multiprocessing functionality
Creates a test log file and compares sequential vs parallel processing performance
"""

import time
import tempfile
import json
from pathlib import Path

from core.utils import MultiprocessingConfig
from core.logging_config import get_logger, enable_file_logging

# Enable logging
enable_file_logging()
logger = get_logger(__name__)


def create_test_log_file(num_lines=50000):
    """Create a test log file with specified number of lines"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log')

    logger.info(f"Creating test log file with {num_lines} lines...")

    for i in range(num_lines):
        # Generate JSON log line
        log_line = {
            "time": f"2024-01-01T{i % 24:02d}:{i % 60:02d}:{i % 60:02d}Z",
            "request_url": f"/api/endpoint{i % 100}",
            "elb_status_code": 200 if i % 10 != 0 else 500,
            "target_processing_time": 0.001 + (i % 1000) / 100000,
            "client_ip": f"192.168.{i % 256}.{(i // 256) % 256}"
        }
        temp_file.write(json.dumps(log_line) + '\n')

    temp_file.close()
    logger.info(f"Test log file created: {temp_file.name}")

    return temp_file.name


def create_format_file():
    """Create a log format file for JSON logs"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')

    format_info = {
        'logPattern': 'JSON',
        'patternType': 'JSON',
        'fieldMap': {
            'timestamp': 'time',
            'url': 'request_url',
            'status': 'elb_status_code',
            'responseTime': 'target_processing_time',
            'clientIp': 'client_ip'
        },
        'responseTimeUnit': 's',
        'timezone': 'UTC'
    }

    json.dump(format_info, temp_file, indent=2)
    temp_file.close()

    logger.info(f"Format file created: {temp_file.name}")

    return temp_file.name


def test_parsing_performance():
    """Test parsing performance with and without multiprocessing"""
    from data_parser import parse_log_file_with_format

    logger.info("\n" + "="*60)
    logger.info("Testing Parsing Performance")
    logger.info("="*60)

    # Create test files
    log_file = create_test_log_file(num_lines=50000)
    format_file = create_format_file()

    try:
        # Test sequential parsing
        logger.info("\n1. Sequential Parsing (use_multiprocessing=False):")
        start_time = time.time()

        df_sequential = parse_log_file_with_format(
            log_file,
            format_file,
            use_multiprocessing=False
        )

        sequential_time = time.time() - start_time
        logger.info(f"   Parsed {len(df_sequential)} lines in {sequential_time:.2f} seconds")

        # Test parallel parsing
        logger.info("\n2. Parallel Parsing (use_multiprocessing=True):")
        start_time = time.time()

        df_parallel = parse_log_file_with_format(
            log_file,
            format_file,
            use_multiprocessing=True,
            chunk_size=5000
        )

        parallel_time = time.time() - start_time
        logger.info(f"   Parsed {len(df_parallel)} lines in {parallel_time:.2f} seconds")

        # Calculate speedup
        if sequential_time > 0:
            speedup = sequential_time / parallel_time
            logger.info(f"\n✓ Speedup: {speedup:.2f}x faster with multiprocessing")

        # Verify results are the same
        if len(df_sequential) == len(df_parallel):
            logger.info("✓ Both methods parsed the same number of lines")
        else:
            logger.warning(f"⚠ Line count mismatch: {len(df_sequential)} vs {len(df_parallel)}")

    finally:
        # Cleanup
        import os
        os.unlink(log_file)
        os.unlink(format_file)


def test_stats_performance():
    """Test statistics calculation performance"""
    from data_parser import parse_log_file_with_format
    from data_processor import calculateStats

    logger.info("\n" + "="*60)
    logger.info("Testing Statistics Calculation Performance")
    logger.info("="*60)

    # Create test files with diverse URLs and IPs
    log_file = create_test_log_file(num_lines=20000)
    format_file = create_format_file()

    try:
        # Parse the file first
        logger.info("\nParsing test file...")
        df = parse_log_file_with_format(
            log_file,
            format_file,
            use_multiprocessing=True
        )
        logger.info(f"Parsed {len(df)} lines")

        # Test sequential stats
        logger.info("\n1. Sequential Statistics (use_multiprocessing=False):")
        start_time = time.time()

        result_sequential = calculateStats(
            log_file,
            format_file,
            params='statsType=all',
            use_multiprocessing=False
        )

        sequential_time = time.time() - start_time
        logger.info(f"   Calculated stats in {sequential_time:.2f} seconds")

        # Test parallel stats
        logger.info("\n2. Parallel Statistics (use_multiprocessing=True):")
        start_time = time.time()

        result_parallel = calculateStats(
            log_file,
            format_file,
            params='statsType=all',
            use_multiprocessing=True
        )

        parallel_time = time.time() - start_time
        logger.info(f"   Calculated stats in {parallel_time:.2f} seconds")

        # Calculate speedup
        if sequential_time > 0:
            speedup = sequential_time / parallel_time
            logger.info(f"\n✓ Speedup: {speedup:.2f}x faster with multiprocessing")

    finally:
        # Cleanup
        import os
        os.unlink(log_file)
        os.unlink(format_file)

        # Remove generated stats files
        if 'filePath' in result_sequential:
            try:
                os.unlink(result_sequential['filePath'])
            except:
                pass

        if 'filePath' in result_parallel:
            try:
                os.unlink(result_parallel['filePath'])
            except:
                pass


def test_config():
    """Test multiprocessing configuration"""
    logger.info("\n" + "="*60)
    logger.info("Testing Multiprocessing Configuration")
    logger.info("="*60)

    config = MultiprocessingConfig.get_config()

    logger.info("\nConfiguration from config.yaml:")
    logger.info(f"  Enabled: {config['enabled']}")
    logger.info(f"  Num Workers: {config['num_workers']} (auto-detect)")
    logger.info(f"  Chunk Size: {config['chunk_size']}")
    logger.info(f"  Min Lines for Parallel: {config['min_lines_for_parallel']}")

    # Test decision logic
    logger.info("\nDecision Logic:")

    test_cases = [
        (100, "Small file"),
        (5000, "Medium file"),
        (50000, "Large file")
    ]

    for num_lines, description in test_cases:
        should_use = MultiprocessingConfig.should_use_multiprocessing(num_lines)
        logger.info(f"  {description} ({num_lines} lines): {'PARALLEL' if should_use else 'SEQUENTIAL'}")


def main():
    """Run all tests"""
    logger.info("\n" + "="*60)
    logger.info("Multiprocessing Demo and Performance Tests")
    logger.info("="*60)

    try:
        # Test configuration
        test_config()

        # Test parsing performance
        test_parsing_performance()

        # Test statistics performance
        test_stats_performance()

        logger.info("\n" + "="*60)
        logger.info("All tests completed successfully!")
        logger.info("="*60 + "\n")

    except Exception as e:
        logger.error(f"Error during testing: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
