#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Test script for log.gz file
Tests generateSentBytesPerURI and generateProcessingTimePerURI
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_parser import recommendAccessLogFormat
from data_visualizer import generateSentBytesPerURI, generateProcessingTimePerURI


def test_sent_bytes_per_uri():
    """Test Generate Sent Bytes per URI"""
    print("\n" + "="*70)
    print("Test 1: Generate Sent Bytes per URI (Sum & Average)")
    print("="*70)

    log_file = os.path.join(os.path.dirname(__file__), 'accesslog_example', 'log.gz')

    try:
        # Step 1: Detect log format
        print(f"\n[1/2] Detecting log format for {log_file}...")
        format_result = recommendAccessLogFormat(log_file)
        print(f"  [OK] Pattern Type: {format_result['patternType']}")
        print(f"  [OK] Format File: {format_result['logFormatFile']}")
        log_format_file = format_result['logFormatFile']

        # Step 2: Generate Sent Bytes per URI
        print("\n[2/2] Generating Sent Bytes per URI visualization...")
        result = generateSentBytesPerURI(
            inputFile=log_file,
            logFormatFile=log_format_file,
            outputFormat='html',
            topN=10,
            interval='10s',
            patternsFile=None,
            timeField='time'
        )

        print(f"\n[OK] Sent Bytes chart generated:")
        print(f"  Total transactions: {result['totalTransactions']}")
        print(f"  Top N patterns: {result.get('topN', 10)}")
        print(f"  Interval: {result.get('interval', '10s')}")
        print(f"  Top Sum URIs: {len(result.get('topNSum', []))}")
        print(f"  Top Avg URIs: {len(result.get('topNAvg', []))}")
        print(f"  Output file: {result['filePath']}")

        return True

    except Exception as e:
        print(f"\n[ERROR] Error in test_sent_bytes_per_uri: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_processing_time_per_uri():
    """Test Generate Processing Time per URI"""
    print("\n" + "="*70)
    print("Test 2: Generate Processing Time per URI (NEW)")
    print("="*70)

    log_file = os.path.join(os.path.dirname(__file__), 'accesslog_example', 'log.gz')

    try:
        # Step 1: Detect log format
        print(f"\n[1/2] Detecting log format for {log_file}...")
        format_result = recommendAccessLogFormat(log_file)
        print(f"  [OK] Pattern Type: {format_result['patternType']}")
        print(f"  [OK] Format File: {format_result['logFormatFile']}")
        log_format_file = format_result['logFormatFile']

        # Step 2: Generate Processing Time per URI
        print("\n[2/2] Generating Processing Time per URI visualization...")
        result = generateProcessingTimePerURI(
            inputFile=log_file,
            logFormatFile=log_format_file,
            outputFormat='html',
            processingTimeField='target_processing_time',
            metric='avg',
            topN=10,
            interval='1min',
            patternsFile=None,
            timeField='time'
        )

        print(f"\n[OK] Processing Time chart generated:")
        print(f"  Total transactions: {result['totalTransactions']}")
        print(f"  Processing time field: {result['processingTimeField']}")
        print(f"  Metric: {result['metric']}")
        print(f"  Top N patterns: {result.get('topN', 10)}")
        print(f"  Interval: {result.get('interval', '1min')}")
        print(f"  Patterns displayed: {result.get('patternsDisplayed', 10)}")
        print(f"  Output file: {result['filePath']}")

        return True

    except Exception as e:
        print(f"\n[ERROR] Error in test_processing_time_per_uri: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("="*70)
    print(" Test Suite for log.gz - Sent Bytes & Processing Time")
    print("="*70)

    results = {
        'sent_bytes': test_sent_bytes_per_uri(),
        'processing_time': test_processing_time_per_uri()
    }

    print("\n" + "="*70)
    print(" Test Results Summary")
    print("="*70)
    print(f"  Sent Bytes per URI: {'[PASS]' if results['sent_bytes'] else '[FAIL]'}")
    print(f"  Processing Time per URI: {'[PASS]' if results['processing_time'] else '[FAIL]'}")
    print("="*70)

    if all(results.values()):
        print("\n[OK] All tests passed!")
        return 0
    else:
        print("\n[ERROR] Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
