#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Test script for processing time statistics feature

This script demonstrates how to use the new processing time fields analysis
in calculateStats function.
"""

import pandas as pd
import json
from datetime import datetime
from pathlib import Path


def create_sample_data():
    """Create sample log data with processing time fields"""
    data = {
        'time': pd.date_range('2024-01-01 10:00:00', periods=100, freq='1min'),
        'request_url': [
            '/api/users',
            '/api/orders',
            '/api/products',
            '/static/css/main.css',
            '/static/js/app.js'
        ] * 20,
        'elb_status_code': [200] * 80 + [404] * 10 + [500] * 10,
        'client_ip': ['192.168.1.1'] * 50 + ['192.168.1.2'] * 50,
        'request_processing_time': [0.001, 0.002, 0.003, 0.001, 0.001] * 20,
        'target_processing_time': [0.050, 0.100, 0.200, 0.010, 0.015] * 20,
        'response_processing_time': [0.001, 0.002, 0.001, 0.001, 0.001] * 20
    }

    df = pd.DataFrame(data)
    return df


def create_sample_format_info():
    """Create sample log format info"""
    return {
        'fieldMap': {
            'timestamp': 'time',
            'url': 'request_url',
            'status': 'elb_status_code',
            'clientIp': 'client_ip',
            'responseTime': 'target_processing_time'
        },
        'timezone': 'UTC',
        'patternType': 'alb'
    }


def test_processing_time_stats():
    """Test processing time statistics calculation"""
    print("=" * 80)
    print("Testing Processing Time Statistics Feature")
    print("=" * 80)

    # Create sample data
    log_df = create_sample_data()
    format_info = create_sample_format_info()

    print(f"\nSample data created: {len(log_df)} records")
    print(f"Unique URLs: {log_df['request_url'].nunique()}")
    print("\nProcessing time fields:")
    print("  - request_processing_time")
    print("  - target_processing_time")
    print("  - response_processing_time")

    # Import the function
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from data_processor import _calculate_url_stats_chunk

    # Prepare data for testing
    url_field = 'request_url'
    status_field = 'elb_status_code'
    rt_field = 'target_processing_time'
    processing_time_fields = [
        'request_processing_time',
        'target_processing_time',
        'response_processing_time'
    ]

    # Group by URL
    url_groups = log_df.groupby(url_field)
    url_group_data = [(url, group) for url, group in url_groups]

    print("\n" + "=" * 80)
    print("Calculating Statistics...")
    print("=" * 80)

    # Calculate statistics
    url_stats = _calculate_url_stats_chunk(
        url_group_data,
        status_field,
        rt_field,
        processing_time_fields
    )

    # Display results
    print(f"\nResults for {len(url_stats)} URLs:\n")

    for i, stat in enumerate(url_stats, 1):
        print(f"{i}. URL: {stat['url']}")
        print(f"   Count: {stat['count']} requests")

        # Show processing time statistics
        for field in processing_time_fields:
            if field in stat:
                field_stats = stat[field]
                print(f"   {field}:")
                print(f"     - avg: {field_stats['avg']:.6f}")
                print(f"     - sum: {field_stats['sum']:.6f}")
                print(f"     - median: {field_stats['median']:.6f}")
                print(f"     - p95: {field_stats['p95']:.6f}")
                print(f"     - p99: {field_stats['p99']:.6f}")
        print()

    # Test sorting by different metrics
    print("=" * 80)
    print("Testing Sorting by Different Metrics")
    print("=" * 80)

    # Sort by average target_processing_time
    sorted_by_avg = sorted(
        url_stats,
        key=lambda x: x.get('target_processing_time', {}).get('avg', 0),
        reverse=True
    )

    print("\nTop 3 URLs by average target_processing_time:")
    for i, stat in enumerate(sorted_by_avg[:3], 1):
        avg_time = stat.get('target_processing_time', {}).get('avg', 0)
        print(f"  {i}. {stat['url']}: {avg_time:.6f}s")

    # Sort by sum of request_processing_time
    sorted_by_sum = sorted(
        url_stats,
        key=lambda x: x.get('request_processing_time', {}).get('sum', 0),
        reverse=True
    )

    print("\nTop 3 URLs by sum of request_processing_time:")
    for i, stat in enumerate(sorted_by_sum[:3], 1):
        sum_time = stat.get('request_processing_time', {}).get('sum', 0)
        print(f"  {i}. {stat['url']}: {sum_time:.6f}s")

    # Sort by p95 response_processing_time
    sorted_by_p95 = sorted(
        url_stats,
        key=lambda x: x.get('response_processing_time', {}).get('p95', 0),
        reverse=True
    )

    print("\nTop 3 URLs by p95 response_processing_time:")
    for i, stat in enumerate(sorted_by_p95[:3], 1):
        p95_time = stat.get('response_processing_time', {}).get('p95', 0)
        print(f"  {i}. {stat['url']}: {p95_time:.6f}s")

    print("\n" + "=" * 80)
    print("Test completed successfully!")
    print("=" * 80)


if __name__ == '__main__':
    test_processing_time_stats()
