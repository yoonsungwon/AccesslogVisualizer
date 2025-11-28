#!/mnt/c/bucket/AccesslogAnalyzer/venv/bin/python3
# -*- coding: utf-8 -*-
###!/usr/bin/python3
"""
Main script for Access Log Analyzer - MCP Tool-based Architecture

This script demonstrates the MCP (Model Context Protocol) tool pipeline approach.
It provides both interactive mode and example pipeline execution.

Usage:
    python main.py                          # Interactive menu
    python main.py <log_file>              # Auto-detect format and show options
    python main.py --example <log_file>    # Run example pipeline
"""

import sys
import os
from pathlib import Path

# Import MCP tools
from data_parser import recommendAccessLogFormat, parseAccessLog
from data_processor import (
    filterByCondition,
    extractUriPatterns,
    filterUriPatterns,
    calculateStats
)
from data_visualizer import (
    generateXlog,
    generateRequestPerURI,
    generateRequestPerTarget,
    generateRequestPerClientIP,
    generateMultiMetricDashboard,
    generateReceivedBytesPerURI,
    generateSentBytesPerURI,
    generateProcessingTimePerURI
)


def print_banner():
    """Print application banner"""
    print("="*70)
    print(" Access Log Analyzer - MCP Tool Pipeline")
    print(" Version 1.0")
    print("="*70)
    print()


def _get_available_columns(log_format_file):
    """
    Get available columns from log format file.

    Args:
        log_format_file: Path to log format JSON file

    Returns:
        list: List of available column names
    """
    import json
    try:
        with open(log_format_file, 'r', encoding='utf-8') as f:
            format_data = json.load(f)

        # Get columns from format file
        if 'columns' in format_data:
            columns = format_data['columns']
        else:
            # Fallback: try to parse from fieldMap
            columns = list(format_data.get('fieldMap', {}).values())

        # For HTTPD logs, add derived columns
        if format_data.get('patternType') == 'HTTPD' and 'request' in columns:
            columns.extend(['request_method', 'request_url', 'request_proto'])

        return columns
    except Exception as e:
        print(f"Warning: Could not read columns from format file: {e}")
        return []


def _check_field_availability(field_name, available_columns):
    """
    Check if a field is available in the log format.

    Args:
        field_name: Field name to check
        available_columns: List of available columns

    Returns:
        bool: True if field is available
    """
    # Check direct match
    if field_name in available_columns:
        return True

    # Check common field name variants
    variants = {
        'sent_bytes': ['sent_bytes', 'bytes_sent', 'size', 'response_size', 'body_bytes_sent'],
        'received_bytes': ['received_bytes', 'bytes', 'request_size'],
        'target_ip': ['target_ip', 'backend_ip', 'upstream_addr'],
        'client_ip': ['client_ip', 'remote_addr', 'clientIp'],
        'request_processing_time': ['request_processing_time', 'request_time'],
        'target_processing_time': ['target_processing_time', 'upstream_response_time'],
        'response_processing_time': ['response_processing_time'],
    }

    # Check variants
    if field_name in variants:
        for variant in variants[field_name]:
            if variant in available_columns:
                return True

    return False


def select_time_field():
    """
    Prompt user to select time field for analysis.

    Returns:
        str: Selected time field ('time' or 'request_creation_time')
    """
    print("\nSelect time field for analysis:")
    print("  1. time (default)")
    print("  2. request_creation_time")
    time_choice = input("Time field (1-2, default: 1): ").strip()

    time_map = {
        '1': 'time',
        '2': 'request_creation_time',
        '': 'time'  # default
    }

    time_field = time_map.get(time_choice, 'time')
    print(f"  ✓ Selected time field: {time_field}")
    return time_field


def interactive_menu(log_file=None):
    """Interactive menu for tool selection"""
    print_banner()

    if not log_file:
        log_file = input("Enter log file path: ").strip()
        if not log_file:
            print("Error: Log file path is required.")
            return

    if not os.path.exists(log_file):
        print(f"Error: File not found: {log_file}")
        return

    print(f"\nAnalyzing: {log_file}\n")

    # Step 1: Recommend log format
    print("Step 1: Detecting log format...")
    try:
        format_result = recommendAccessLogFormat(log_file)
        print(f"  ✓ Pattern Type: {format_result['patternType']}")
        print(f"  ✓ Confidence: {format_result['confidence']:.1%}")
        print(f"  ✓ Success Rate: {format_result['successRate']:.1%}")
        print(f"  ✓ Format File: {format_result['logFormatFile']}")
        log_format_file = format_result['logFormatFile']
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return

    # Show menu
    while True:
        print("\n" + "="*70)
        print("Available Operations:")
        print("="*70)
        print("  1. Filter by time range")
        print("  2. Filter by status code")
        print("  3. Filter by response time")
        print("  4. Extract URLs")
        print("  5. Extract URI patterns")
        print("  6. Calculate statistics")
        print("  7. Generate XLog (response time scatter plot)")
        print("  8. Generate Request Count per URI")
        print("  9. Generate Dashboard")
        print("  10. Generate Received Bytes per URI (Sum & Average)")
        print("  11. Generate Sent Bytes per URI (Sum & Average)")
        print("  12. Generate Processing Time per URI (NEW)")
        print("  13. Generate Request Count per Target (NEW)")
        print("  14. Generate Request Count per Client IP (NEW)")
        print("  15. Run example pipeline")
        print("  0. Exit")
        print("="*70)

        choice = input("\nSelect operation (0-15): ").strip()

        if choice == '0':
            print("\nExiting. Goodbye!")
            break
        elif choice == '1':
            filter_by_time(log_file, log_format_file)
        elif choice == '2':
            filter_by_status(log_file, log_format_file)
        elif choice == '3':
            filter_by_response_time(log_file, log_format_file)
        elif choice == '4':
            extract_urls(log_file, log_format_file)
        elif choice == '5':
            extract_patterns(log_file, log_format_file)
        elif choice == '6':
            calculate_statistics(log_file, log_format_file)
        elif choice == '7':
            generate_xlog_viz(log_file, log_format_file)
        elif choice == '8':
            generate_request_cnt(log_file, log_format_file)
        elif choice == '9':
            generate_dashboard(log_file, log_format_file)
        elif choice == '10':
            generate_received_bytes(log_file, log_format_file)
        elif choice == '11':
            generate_sent_bytes(log_file, log_format_file)
        elif choice == '12':
            generate_processing_time(log_file, log_format_file)
        elif choice == '13':
            generate_request_per_target(log_file, log_format_file)
        elif choice == '14':
            generate_request_per_client_ip(log_file, log_format_file)
        elif choice == '15':
            run_example_pipeline(log_file, log_format_file)
        else:
            print("Invalid choice. Please try again.")


def filter_by_time(log_file, log_format_file):
    """Filter logs by time range"""
    print("\n--- Filter by Time Range ---")
    start_time = input("Start time (YYYY-MM-DDTHH:MM:SS): ").strip()
    end_time = input("End time (YYYY-MM-DDTHH:MM:SS): ").strip()

    if not start_time or not end_time:
        print("Error: Both start and end times are required.")
        return

    params = f"startTime={start_time};endTime={end_time}"

    try:
        result = filterByCondition(log_file, log_format_file, 'time', params)
        print(f"\n✓ Filter completed:")
        print(f"  Total lines: {result['totalLines']}")
        print(f"  Filtered lines: {result['filteredLines']}")
        print(f"  Output file: {result['filePath']}")
    except Exception as e:
        print(f"✗ Error: {e}")


def filter_by_status(log_file, log_format_file):
    """Filter logs by status code"""
    print("\n--- Filter by Status Code ---")
    status_codes = input("Status codes (comma-separated, e.g., 2xx,5xx or 200,404): ").strip()

    if not status_codes:
        print("Error: Status codes are required.")
        return

    params = f"statusCodes={status_codes}"

    try:
        result = filterByCondition(log_file, log_format_file, 'statusCode', params)
        print(f"\n✓ Filter completed:")
        print(f"  Total lines: {result['totalLines']}")
        print(f"  Filtered lines: {result['filteredLines']}")
        print(f"  Output file: {result['filePath']}")
    except Exception as e:
        print(f"✗ Error: {e}")


def filter_by_response_time(log_file, log_format_file):
    """Filter logs by response time"""
    print("\n--- Filter by Response Time ---")
    min_time = input("Minimum response time (e.g., 500ms, 0.5s): ").strip()
    max_time = input("Maximum response time (e.g., 2000ms, 2s): ").strip()

    params = []
    if min_time:
        params.append(f"min={min_time}")
    if max_time:
        params.append(f"max={max_time}")

    if not params:
        print("Error: At least one threshold is required.")
        return

    params_str = ';'.join(params)

    try:
        result = filterByCondition(log_file, log_format_file, 'responseTime', params_str)
        print(f"\n✓ Filter completed:")
        print(f"  Total lines: {result['totalLines']}")
        print(f"  Filtered lines: {result['filteredLines']}")
        print(f"  Output file: {result['filePath']}")
    except Exception as e:
        print(f"✗ Error: {e}")


def extract_urls(log_file, log_format_file):
    """Extract unique URLs"""
    print("\n--- Extract URLs ---")
    include_params = input("Include query parameters? (y/n): ").strip().lower() == 'y'

    params = f"includeParams={'true' if include_params else 'false'}"

    try:
        result = extractUriPatterns(log_file, log_format_file, 'urls', params)
        print(f"\n✓ Extraction completed:")
        print(f"  Unique URLs: {result['uniqueUrls']}")
        print(f"  Total requests: {result['totalRequests']}")
        print(f"  Output file: {result['filePath']}")
    except Exception as e:
        print(f"✗ Error: {e}")


def extract_patterns(log_file, log_format_file):
    """Extract URI patterns"""
    print("\n--- Extract URI Patterns ---")
    max_patterns = input("Maximum patterns to extract (default: 100): ").strip()
    min_count = input("Minimum request count (default: 1): ").strip()

    params = []
    if max_patterns:
        params.append(f"maxPatterns={max_patterns}")
    if min_count:
        params.append(f"minCount={min_count}")

    params_str = ';'.join(params) if params else ''

    try:
        result = extractUriPatterns(log_file, log_format_file, 'patterns', params_str)
        print(f"\n✓ Extraction completed:")
        print(f"  Patterns found: {result['patternsFound']}")
        print(f"  Total requests: {result['totalRequests']}")
        print(f"  Output file: {result['filePath']}")
    except Exception as e:
        print(f"✗ Error: {e}")


def calculate_statistics(log_file, log_format_file):
    """Calculate statistics"""
    print("\n--- Calculate Statistics ---")
    print("Available types: all, summary, url, time, ip")
    stats_type = input("Statistics type (comma-separated, default: all): ").strip()
    time_interval = input("Time interval (1h, 30m, 10m, 5m, 1m, default: 10m): ").strip()

    params = []
    if stats_type:
        params.append(f"statsType={stats_type}")
    if time_interval:
        params.append(f"timeInterval={time_interval}")

    # Ask if user wants to analyze processing time fields
    print("\n--- Processing Time Analysis (Optional) ---")
    analyze_processing = input("Analyze processing time fields? (y/n, default: n): ").strip().lower()

    if analyze_processing == 'y':
        print("\nAvailable fields (comma-separated):")
        print("  - request_processing_time")
        print("  - target_processing_time")
        print("  - response_processing_time")
        print("  - Or any custom processing time field in your logs")

        proc_fields = input("\nProcessing time fields (default: all three above): ").strip()
        if not proc_fields:
            proc_fields = "request_processing_time,target_processing_time,response_processing_time"
        params.append(f"processingTimeFields={proc_fields}")

        # Ask for sorting preferences
        print("\n--- Sorting & Top N (Optional) ---")
        sort_by = input("Sort by field (e.g., request_processing_time, target_processing_time, or empty to skip): ").strip()
        if sort_by:
            params.append(f"sortBy={sort_by}")

            print("\nAvailable metrics: avg, sum, median, p95, p99")
            sort_metric = input("Sort metric (default: avg): ").strip()
            if not sort_metric:
                sort_metric = "avg"
            params.append(f"sortMetric={sort_metric}")

            top_n = input("Top N URLs to return (e.g., 20, 50, or empty for all): ").strip()
            if top_n:
                params.append(f"topN={top_n}")

    params_str = ';'.join(params) if params else ''

    try:
        result = calculateStats(log_file, log_format_file, params_str)
        print(f"\n✓ Statistics calculated:")
        print(f"  Output file: {result['filePath']}")
        print(f"\n{result['summary']}")
    except Exception as e:
        print(f"✗ Error: {e}")


def generate_xlog_viz(log_file, log_format_file):
    """Generate XLog visualization"""
    print("\n--- Generate XLog ---")

    # Ask for grouping method
    print("\n  Select grouping method:")
    print("    1. Group by Status Code (default)")
    print("    2. Group by URL Pattern")
    print("    3. Group by Target IP")
    group_choice = input("\n  Enter choice (1-3) [default: 1]: ").strip()

    group_by = "status"
    patterns_file = None

    if group_choice == "2":
        group_by = "url"

        # Check for existing pattern files
        log_file_path = Path(log_file)
        log_dir = log_file_path.parent
        pattern_files = []
        try:
            pattern_files = sorted(log_dir.glob('patterns_*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
        except Exception:
            pass

        if pattern_files:
            print(f"\n  Found {len(pattern_files)} pattern file(s):")
            for i, pf in enumerate(pattern_files[:5], 1):
                print(f"    {i}. {pf.name}")
            print(f"    {len(pattern_files[:5]) + 1}. Auto-detect")
            print(f"    {len(pattern_files[:5]) + 2}. Skip (use raw URLs)")

            choice = input(f"\n  Select pattern file (1-{len(pattern_files[:5]) + 2}) [default: auto-detect]: ").strip()
            if choice and choice.isdigit():
                choice_num = int(choice)
                if 1 <= choice_num <= len(pattern_files[:5]):
                    patterns_file = str(pattern_files[choice_num - 1])
                    print(f"  Using pattern file: {patterns_file}")
                elif choice_num == len(pattern_files[:5]) + 2:
                    print("  Skipping pattern file, using raw URLs")
                else:
                    print("  Auto-detecting pattern file")
            else:
                print("  Auto-detecting pattern file")
        else:
            print("  No pattern files found. Will use raw URLs for grouping.")
    elif group_choice == "3":
        group_by = "ip"
        print("  Grouping by Target IP address")

    # Ask for status code field
    print("\n  Select status code field:")
    print("    1. elb_status_code (default)")
    print("    2. target_status_code")
    status_choice = input("\n  Enter choice (1-2) [default: 1]: ").strip()

    status_field = "elb_status_code"
    if status_choice == "2":
        status_field = "target_status_code"

    print(f"  Using status code field: {status_field}")

    # Ask for URL pattern filtering (optional)
    print("\n  URL Pattern Filtering (optional):")
    print("    Enter comma-separated URL patterns to filter (e.g., '/api/*,/admin/*')")
    print("    Leave empty to show all URLs")
    url_patterns = input("\n  URL patterns: ").strip()

    # Select time field
    time_field = select_time_field()

    try:
        result = generateXlog(log_file, log_format_file, 'html', status_field, url_patterns, group_by, patterns_file, time_field)
        print(f"\n✓ XLog generated:")
        print(f"  Grouping method: {result['groupBy']}")
        if result['groupBy'] == 'url' and 'uniquePatterns' in result:
            print(f"  Unique URL patterns: {result['uniquePatterns']}")
        elif result['groupBy'] == 'ip' and 'uniqueIPs' in result:
            print(f"  Unique Target IPs: {result['uniqueIPs']}")
        print(f"  Status code field: {result['statusCodeField']}")
        if result['filteredUrls'] > 0:
            print(f"  URL filters applied: {result['filteredUrls']}")
            print(f"  Original transactions: {result['originalTransactions']}")
            print(f"  Filtered transactions: {result['totalTransactions']}")
        else:
            print(f"  Total transactions: {result['totalTransactions']}")
        print(f"  Output file: {result['filePath']}")
        print(f"\n  Open the HTML file in your browser to view the interactive chart.")
    except Exception as e:
        print(f"✗ Error: {e}")


def generate_request_cnt(log_file, log_format_file):
    """Generate Request Count visualization"""
    print("\n--- Generate Request Count per URI ---")
    
    # Check for existing pattern files in the same directory
    log_file_path = Path(log_file)
    log_dir = log_file_path.parent
    
    # Look for pattern files (patterns_*.json)
    pattern_files = []
    try:
        pattern_files = sorted(log_dir.glob('patterns_*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    except Exception:
        pass  # If directory doesn't exist or other error, continue without pattern files
    
    patterns_file = None
    if pattern_files:
        print(f"\n  Found {len(pattern_files)} pattern file(s) in the directory:")
        for i, pf in enumerate(pattern_files[:5], 1):  # Show up to 5 most recent
            try:
                # Try to read pattern count from file
                import json
                with open(pf, 'r', encoding='utf-8') as f:
                    pattern_data = json.load(f)
                    # Get pattern count from patternRules if available, otherwise from patterns (backward compatibility)
                    if isinstance(pattern_data, dict):
                        if 'patternRules' in pattern_data:
                            pattern_count = len(pattern_data['patternRules'])
                        else:
                            pattern_count = len(pattern_data.get('patterns', []))
                    else:
                        pattern_count = len(pattern_data) if isinstance(pattern_data, list) else 0
                    file_size = pf.stat().st_size
                    print(f"    {i}. {pf.name} ({pattern_count} pattern rules, {file_size} bytes)")
            except Exception:
                print(f"    {i}. {pf.name}")
        
        use_existing = input(f"\n  Use existing pattern file? (y/n, default: n): ").strip().lower()
        if use_existing == 'y':
            if len(pattern_files) == 1:
                patterns_file = str(pattern_files[0])
            else:
                file_choice = input(f"  Select file number (1-{min(len(pattern_files), 5)}): ").strip()
                try:
                    file_idx = int(file_choice) - 1
                    if 0 <= file_idx < len(pattern_files):
                        patterns_file = str(pattern_files[file_idx])
                    else:
                        print(f"  Invalid selection, using most recent file: {pattern_files[0].name}")
                        patterns_file = str(pattern_files[0])
                except ValueError:
                    print(f"  Invalid input, using most recent file: {pattern_files[0].name}")
                    patterns_file = str(pattern_files[0])
            
            if patterns_file:
                print(f"  ✓ Using pattern file: {Path(patterns_file).name}")
    
    # Get user preferences (only if not using existing pattern file)
    if not patterns_file:
        top_n_input = input("\nNumber of top URI patterns to display (default: 20): ").strip()
        top_n = int(top_n_input) if top_n_input else 20
    else:
        # Pattern file will be used, but still ask for topN as it might be needed
        top_n_input = input("\nNumber of top URI patterns to display (default: use all from file): ").strip()
        top_n = int(top_n_input) if top_n_input else 20
    
    interval_input = input("Time interval for aggregation (default: 10s, examples: 1s, 10s, 1min, 5min, 1h): ").strip()
    interval = interval_input if interval_input else '10s'

    # Select time field
    time_field = select_time_field()

    try:
        result = generateRequestPerURI(
            log_file,
            log_format_file,
            'html',
            topN=top_n,
            interval=interval,
            patternsFile=patterns_file,
            timeField=time_field
        )
        print(f"\n✓ Request Count chart generated:")
        print(f"  Total transactions: {result['totalTransactions']}")
        print(f"  Top N patterns: {result.get('topN', top_n)}")
        print(f"  Interval: {result.get('interval', interval)}")
        print(f"  Patterns displayed: {result.get('patternsDisplayed', top_n)}")
        if result.get('patternsFile'):
            print(f"  Patterns file: {result['patternsFile']}")
        print(f"  Output file: {result['filePath']}")
        print(f"\n  Open the HTML file in your browser to view the interactive chart.")
        print(f"  Features:")
        print(f"    - Click legend items to show/hide patterns")
        print(f"    - Use checkboxes on the right to filter patterns")
        print(f"    - Drag to zoom (box select)")
        print(f"    - Use toolbar buttons for pan, zoom, reset, etc.")
    except Exception as e:
        print(f"✗ Error: {e}")


def generate_dashboard(log_file, log_format_file):
    """Generate comprehensive dashboard"""
    print("\n--- Generate Dashboard ---")

    # Select time field
    time_field = select_time_field()

    try:
        result = generateMultiMetricDashboard(log_file, log_format_file, 'html', time_field)
        print(f"\n✓ Dashboard generated:")
        print(f"  Total transactions: {result['totalTransactions']}")
        print(f"  Output file: {result['filePath']}")
        print(f"\n  Open the HTML file in your browser to view the dashboard.")
    except Exception as e:
        print(f"✗ Error: {e}")


def generate_received_bytes(log_file, log_format_file):
    """Generate Received Bytes per URI visualization"""
    print("\n--- Generate Received Bytes per URI ---")

    # Check if received_bytes field is available
    available_columns = _get_available_columns(log_format_file)
    if not _check_field_availability('received_bytes', available_columns):
        print(f"  ✗ Field Not Found: received_bytes (or variants: bytes, request_size)")
        print(f"  Available columns in log format: {', '.join(available_columns[:10])}")
        if len(available_columns) > 10:
            print(f"  ... and {len(available_columns) - 10} more")
        return

    # Check for existing pattern files in the same directory
    log_file_path = Path(log_file)
    log_dir = log_file_path.parent

    # Look for pattern files (patterns_*.json)
    pattern_files = []
    try:
        pattern_files = sorted(log_dir.glob('patterns_*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    except Exception:
        pass  # If directory doesn't exist or other error, continue without pattern files

    patterns_file = None
    if pattern_files:
        print(f"\n  Found {len(pattern_files)} pattern file(s) in the directory:")
        for i, pf in enumerate(pattern_files[:5], 1):  # Show up to 5 most recent
            try:
                # Try to read pattern count from file
                import json
                with open(pf, 'r', encoding='utf-8') as f:
                    pattern_data = json.load(f)
                    # Get pattern count from patternRules if available, otherwise from patterns (backward compatibility)
                    if isinstance(pattern_data, dict):
                        if 'patternRules' in pattern_data:
                            pattern_count = len(pattern_data['patternRules'])
                        else:
                            pattern_count = len(pattern_data.get('patterns', []))
                    else:
                        pattern_count = len(pattern_data) if isinstance(pattern_data, list) else 0
                    file_size = pf.stat().st_size
                    print(f"    {i}. {pf.name} ({pattern_count} pattern rules, {file_size} bytes)")
            except Exception:
                print(f"    {i}. {pf.name}")

        use_existing = input(f"\n  Use existing pattern file? (y/n, default: n): ").strip().lower()
        if use_existing == 'y':
            if len(pattern_files) == 1:
                patterns_file = str(pattern_files[0])
            else:
                file_choice = input(f"  Select file number (1-{min(len(pattern_files), 5)}): ").strip()
                try:
                    file_idx = int(file_choice) - 1
                    if 0 <= file_idx < len(pattern_files):
                        patterns_file = str(pattern_files[file_idx])
                    else:
                        print(f"  Invalid selection, using most recent file: {pattern_files[0].name}")
                        patterns_file = str(pattern_files[0])
                except ValueError:
                    print(f"  Invalid input, using most recent file: {pattern_files[0].name}")
                    patterns_file = str(pattern_files[0])

            if patterns_file:
                print(f"  ✓ Using pattern file: {Path(patterns_file).name}")

    # Get user preferences (only if not using existing pattern file)
    if not patterns_file:
        top_n_input = input("\nNumber of top URI patterns to display (default: 10): ").strip()
        top_n = int(top_n_input) if top_n_input else 10
    else:
        # Pattern file will be used, but still ask for topN as it might be needed
        top_n_input = input("\nNumber of top URI patterns to display (default: use all from file): ").strip()
        top_n = int(top_n_input) if top_n_input else 10

    interval_input = input("Time interval for aggregation (default: 10s, examples: 1s, 10s, 1min, 5min, 1h): ").strip()
    interval = interval_input if interval_input else '10s'

    # Select time field
    time_field = select_time_field()

    try:
        result = generateReceivedBytesPerURI(
            log_file,
            log_format_file,
            'html',
            topN=top_n,
            interval=interval,
            patternsFile=patterns_file,
            timeField=time_field
        )
        print(f"\n✓ Received Bytes chart generated:")
        print(f"  Total transactions: {result['totalTransactions']}")
        print(f"  Top N patterns: {result.get('topN', top_n)}")
        print(f"  Interval: {result.get('interval', interval)}")
        if result.get('patternsFile'):
            print(f"  Patterns file: {result['patternsFile']}")
        print(f"  Top Sum URIs: {len(result.get('topNSum', []))}")
        print(f"  Top Avg URIs: {len(result.get('topNAvg', []))}")
        print(f"  Output file: {result['filePath']}")
        print(f"\n  Open the HTML file in your browser to view the interactive chart.")
        print(f"  Features:")
        print(f"    - Two charts: Sum Top N and Average Top N")
        print(f"    - Time series visualization with interactive controls")
        print(f"    - Use toolbar buttons for pan, zoom, reset, etc.")
    except Exception as e:
        print(f"✗ Error: {e}")


def generate_sent_bytes(log_file, log_format_file):
    """Generate Sent Bytes per URI visualization"""
    print("\n--- Generate Sent Bytes per URI ---")

    # Check if sent_bytes field is available
    available_columns = _get_available_columns(log_format_file)
    if not _check_field_availability('sent_bytes', available_columns):
        print(f"  ✗ Field Not Found: sent_bytes (or variants: bytes_sent, size, response_size, body_bytes_sent)")
        print(f"  Available columns in log format: {', '.join(available_columns[:10])}")
        if len(available_columns) > 10:
            print(f"  ... and {len(available_columns) - 10} more")
        return

    # Check for existing pattern files in the same directory
    log_file_path = Path(log_file)
    log_dir = log_file_path.parent

    # Look for pattern files (patterns_*.json)
    pattern_files = []
    try:
        pattern_files = sorted(log_dir.glob('patterns_*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    except Exception:
        pass  # If directory doesn't exist or other error, continue without pattern files

    patterns_file = None
    if pattern_files:
        print(f"\n  Found {len(pattern_files)} pattern file(s) in the directory:")
        for i, pf in enumerate(pattern_files[:5], 1):  # Show up to 5 most recent
            try:
                # Try to read pattern count from file
                import json
                with open(pf, 'r', encoding='utf-8') as f:
                    pattern_data = json.load(f)
                    # Get pattern count from patternRules if available, otherwise from patterns (backward compatibility)
                    if isinstance(pattern_data, dict):
                        if 'patternRules' in pattern_data:
                            pattern_count = len(pattern_data['patternRules'])
                        else:
                            pattern_count = len(pattern_data.get('patterns', []))
                    else:
                        pattern_count = len(pattern_data) if isinstance(pattern_data, list) else 0
                    file_size = pf.stat().st_size
                    print(f"    {i}. {pf.name} ({pattern_count} pattern rules, {file_size} bytes)")
            except Exception:
                print(f"    {i}. {pf.name}")

        use_existing = input(f"\n  Use existing pattern file? (y/n, default: n): ").strip().lower()
        if use_existing == 'y':
            if len(pattern_files) == 1:
                patterns_file = str(pattern_files[0])
            else:
                file_choice = input(f"  Select file number (1-{min(len(pattern_files), 5)}): ").strip()
                try:
                    file_idx = int(file_choice) - 1
                    if 0 <= file_idx < len(pattern_files):
                        patterns_file = str(pattern_files[file_idx])
                    else:
                        print(f"  Invalid selection, using most recent file: {pattern_files[0].name}")
                        patterns_file = str(pattern_files[0])
                except ValueError:
                    print(f"  Invalid input, using most recent file: {pattern_files[0].name}")
                    patterns_file = str(pattern_files[0])

            if patterns_file:
                print(f"  ✓ Using pattern file: {Path(patterns_file).name}")

    # Get user preferences (only if not using existing pattern file)
    if not patterns_file:
        top_n_input = input("\nNumber of top URI patterns to display (default: 10): ").strip()
        top_n = int(top_n_input) if top_n_input else 10
    else:
        # Pattern file will be used, but still ask for topN as it might be needed
        top_n_input = input("\nNumber of top URI patterns to display (default: use all from file): ").strip()
        top_n = int(top_n_input) if top_n_input else 10

    interval_input = input("Time interval for aggregation (default: 10s, examples: 1s, 10s, 1min, 5min, 1h): ").strip()
    interval = interval_input if interval_input else '10s'

    # Select time field
    time_field = select_time_field()

    try:
        result = generateSentBytesPerURI(
            log_file,
            log_format_file,
            'html',
            topN=top_n,
            interval=interval,
            patternsFile=patterns_file,
            timeField=time_field
        )
        print(f"\n✓ Sent Bytes chart generated:")
        print(f"  Total transactions: {result['totalTransactions']}")
        print(f"  Top N patterns: {result.get('topN', top_n)}")
        print(f"  Interval: {result.get('interval', interval)}")
        if result.get('patternsFile'):
            print(f"  Patterns file: {result['patternsFile']}")
        print(f"  Top Sum URIs: {len(result.get('topNSum', []))}")
        print(f"  Top Avg URIs: {len(result.get('topNAvg', []))}")
        print(f"  Output file: {result['filePath']}")
        print(f"\n  Open the HTML file in your browser to view the interactive chart.")
        print(f"  Features:")
        print(f"    - Two charts: Sum Top N and Average Top N")
        print(f"    - Time series visualization with interactive controls")
        print(f"    - Use toolbar buttons for pan, zoom, reset, etc.")
    except Exception as e:
        print(f"✗ Error: {e}")


def generate_processing_time(log_file, log_format_file):
    """Generate Processing Time per URI visualization"""
    print("\n--- Generate Processing Time per URI ---")

    # Get available columns
    available_columns = _get_available_columns(log_format_file)

    # Check field availability
    fields = {
        '1': ('request_processing_time', 'Request Processing Time'),
        '2': ('target_processing_time', 'Target Processing Time'),
        '3': ('response_processing_time', 'Response Processing Time')
    }

    field_availability = {}
    for key, (field_name, display_name) in fields.items():
        field_availability[key] = _check_field_availability(field_name, available_columns)

    # Select processing time field
    print("\nSelect processing time field:")
    for key, (field_name, display_name) in fields.items():
        status = "✓ Available" if field_availability[key] else "✗ Not available"
        default_marker = " (default)" if key == '2' else ""
        print(f"  {key}. {field_name}{default_marker} - {status}")

    field_choice = input("Field number (1-3, default: 2): ").strip()

    field_map = {
        '1': 'request_processing_time',
        '2': 'target_processing_time',
        '3': 'response_processing_time',
        '': 'target_processing_time'  # default
    }

    processing_time_field = field_map.get(field_choice, 'target_processing_time')

    # Check if selected field is available
    selected_key = field_choice if field_choice else '2'
    if not field_availability.get(selected_key, False):
        print(f"  ✗ Field Not Found: {processing_time_field}")
        print(f"  Available columns in log format: {', '.join(available_columns[:10])}")
        if len(available_columns) > 10:
            print(f"  ... and {len(available_columns) - 10} more")
        return

    print(f"  ✓ Selected field: {processing_time_field}")

    # Select metric
    print("\nSelect metric:")
    print("  1. avg - Average (default)")
    print("  2. sum - Sum")
    print("  3. median - Median")
    print("  4. p95 - 95th Percentile")
    print("  5. p99 - 99th Percentile")
    print("  6. max - Maximum")
    metric_choice = input("Metric number (1-6, default: 1): ").strip()

    metric_map = {
        '1': 'avg',
        '2': 'sum',
        '3': 'median',
        '4': 'p95',
        '5': 'p99',
        '6': 'max',
        '': 'avg'  # default
    }

    metric = metric_map.get(metric_choice, 'avg')
    print(f"  ✓ Selected metric: {metric}")

    # Check for existing pattern files
    log_file_path = Path(log_file)
    log_dir = log_file_path.parent

    pattern_files = []
    try:
        pattern_files = sorted(log_dir.glob('patterns_*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    except Exception:
        pass

    patterns_file = None
    if pattern_files:
        print(f"\n  Found {len(pattern_files)} pattern file(s) in the directory:")
        for i, pf in enumerate(pattern_files[:5], 1):
            try:
                import json
                with open(pf, 'r', encoding='utf-8') as f:
                    pattern_data = json.load(f)
                    if isinstance(pattern_data, dict):
                        if 'patternRules' in pattern_data:
                            pattern_count = len(pattern_data['patternRules'])
                        else:
                            pattern_count = len(pattern_data.get('patterns', []))
                    else:
                        pattern_count = len(pattern_data) if isinstance(pattern_data, list) else 0
                    file_size = pf.stat().st_size
                    print(f"    {i}. {pf.name} ({pattern_count} pattern rules, {file_size} bytes)")
            except Exception:
                print(f"    {i}. {pf.name}")

        use_existing = input(f"\n  Use existing pattern file? (y/n, default: n): ").strip().lower()
        if use_existing == 'y':
            if len(pattern_files) == 1:
                patterns_file = str(pattern_files[0])
            else:
                file_choice = input(f"  Select file number (1-{min(len(pattern_files), 5)}): ").strip()
                try:
                    file_idx = int(file_choice) - 1
                    if 0 <= file_idx < len(pattern_files):
                        patterns_file = str(pattern_files[file_idx])
                    else:
                        print(f"  Invalid selection, using most recent file: {pattern_files[0].name}")
                        patterns_file = str(pattern_files[0])
                except ValueError:
                    print(f"  Invalid input, using most recent file: {pattern_files[0].name}")
                    patterns_file = str(pattern_files[0])

            if patterns_file:
                print(f"  ✓ Using pattern file: {Path(patterns_file).name}")

    # Get user preferences
    if not patterns_file:
        top_n_input = input("\nNumber of top URI patterns to display (default: 10): ").strip()
        top_n = int(top_n_input) if top_n_input else 10
    else:
        top_n_input = input("\nNumber of top URI patterns to display (default: use all from file): ").strip()
        top_n = int(top_n_input) if top_n_input else 10

    interval_input = input("Time interval for aggregation (default: 1min, examples: 1s, 10s, 1min, 5min, 1h): ").strip()
    interval = interval_input if interval_input else '1min'

    # Select time field
    time_field = select_time_field()

    try:
        result = generateProcessingTimePerURI(
            log_file,
            log_format_file,
            'html',
            processingTimeField=processing_time_field,
            metric=metric,
            topN=top_n,
            interval=interval,
            patternsFile=patterns_file,
            timeField=time_field
        )
        print(f"\n✓ Processing Time chart generated:")
        print(f"  Total transactions: {result['totalTransactions']}")
        print(f"  Processing time field: {result['processingTimeField']}")
        print(f"  Metric: {result['metric']}")
        print(f"  Top N patterns: {result.get('topN', top_n)}")
        print(f"  Interval: {result.get('interval', interval)}")
        if result.get('patternsFile'):
            print(f"  Patterns file: {result['patternsFile']}")
        print(f"  Patterns displayed: {result.get('patternsDisplayed', top_n)}")
        print(f"  Output file: {result['filePath']}")
        print(f"\n  Open the HTML file in your browser to view the interactive chart.")
        print(f"  Features:")
        print(f"    - Time series visualization of processing time per URI pattern")
        print(f"    - Interactive legend to show/hide patterns")
        print(f"    - Drag to zoom, use toolbar for pan, reset, etc.")
        print(f"    - Range slider for time navigation")
    except Exception as e:
        print(f"✗ Error: {e}")


def generate_request_per_target(log_file, log_format_file):
    """Generate Request Count per Target visualization"""
    print("\n--- Generate Request Count per Target ---")

    # Check if target_ip field is available
    available_columns = _get_available_columns(log_format_file)
    if not _check_field_availability('target_ip', available_columns):
        print(f"  ✗ Field Not Found: target_ip (or variants: backend_ip, upstream_addr)")
        print(f"  Available columns in log format: {', '.join(available_columns[:10])}")
        if len(available_columns) > 10:
            print(f"  ... and {len(available_columns) - 10} more")
        return

    # Get user preferences
    top_n_input = input("\nNumber of top targets to display (default: 20): ").strip()
    top_n = int(top_n_input) if top_n_input else 20

    interval_input = input("Time interval for aggregation (default: 10s, examples: 1s, 10s, 1min, 5min, 1h): ").strip()
    interval = interval_input if interval_input else '10s'

    # Select time field
    time_field = select_time_field()

    try:
        result = generateRequestPerTarget(
            log_file,
            log_format_file,
            'html',
            topN=top_n,
            interval=interval,
            timeField=time_field
        )
        print(f"\n✓ Request Count per Target chart generated:")
        print(f"  Total transactions: {result['totalTransactions']}")
        print(f"  Targets displayed: {result['targetsDisplayed']}")
        print(f"  Interval: {result.get('interval', interval)}")
        print(f"  Output file: {result['filePath']}")
        print(f"\n  Open the HTML file in your browser to view the interactive chart.")
        print(f"  Features:")
        print(f"    - Time series visualization of request count per target (target_ip:target_port)")
        print(f"    - Interactive legend to show/hide targets")
        print(f"    - Checkbox filter panel for easy target selection")
        print(f"    - Drag to zoom, use toolbar for pan, reset, etc.")
        print(f"    - Range slider for time navigation")
        print(f"    - Hover text display with click-to-copy functionality")
    except Exception as e:
        print(f"✗ Error: {e}")


def generate_request_per_client_ip(log_file, log_format_file):
    """Generate Request Count per Client IP visualization"""
    print("\n--- Generate Request Count per Client IP ---")

    # Get user preferences
    top_n_input = input("\nNumber of top client IPs to display (default: 20): ").strip()
    top_n = int(top_n_input) if top_n_input else 20

    interval_input = input("Time interval for aggregation (default: 10s, examples: 1s, 10s, 1min, 5min, 1h): ").strip()
    interval = interval_input if interval_input else '10s'

    # Select time field
    time_field = select_time_field()

    try:
        result = generateRequestPerClientIP(
            log_file,
            log_format_file,
            'html',
            topN=top_n,
            interval=interval,
            timeField=time_field
        )
        print(f"\n✓ Request Count per Client IP chart generated:")
        print(f"  Total transactions: {result['totalTransactions']}")
        print(f"  Client IPs displayed: {result['clientIPsDisplayed']}")
        print(f"  Interval: {result.get('interval', interval)}")
        print(f"  Output file: {result['filePath']}")
        print(f"\n  Open the HTML file in your browser to view the interactive chart.")
        print(f"  Features:")
        print(f"    - Time series visualization of request count per client IP")
        print(f"    - Interactive legend to show/hide client IPs")
        print(f"    - Checkbox filter panel for easy client IP selection")
        print(f"    - Drag to zoom, use toolbar for pan, reset, etc.")
        print(f"    - Range slider for time navigation")
        print(f"    - Hover text display with click-to-copy functionality")
    except Exception as e:
        print(f"✗ Error: {e}")


def run_example_pipeline(log_file, log_format_file):
    """
    Run example pipeline demonstrating tool chaining.

    Example: "Extract top 5 URLs by processing time and generate XLog"

    Pipeline:
    1. Calculate URL statistics with processing time analysis
    2. Extract top 5 URLs by avg target_processing_time (using new feature)
    3. Filter log by those URLs
    4. Generate XLog for filtered data
    """
    print("\n" + "="*70)
    print("Example Pipeline: Top 5 URLs by Processing Time → XLog")
    print("="*70)

    try:
        # Step 1: Calculate statistics with processing time analysis (NEW)
        print("\n[1/4] Calculating statistics with processing time analysis...")
        print("  Using new processingTimeFields feature!")
        stats_result = calculateStats(
            log_file,
            log_format_file,
            'statsType=url;processingTimeFields=request_processing_time,target_processing_time,response_processing_time;sortBy=target_processing_time;sortMetric=avg;topN=5'
        )
        print(f"  ✓ Stats file: {stats_result['filePath']}")

        # Step 2: Read statistics and extract top 5 URLs
        print("\n[2/4] Extracting top 5 URLs by avg target_processing_time...")
        import json
        with open(stats_result['filePath'], 'r', encoding='utf-8') as f:
            stats = json.load(f)

        url_stats = stats.get('urlStats', [])

        if not url_stats:
            print("  ✗ No URL statistics found.")
            return

        # URLs are already sorted by target_processing_time avg (thanks to new feature)
        top_urls = [s['url'] for s in url_stats[:5]]

        print(f"  ✓ Top 5 URLs by avg target_processing_time:")
        for i, stat in enumerate(url_stats[:5], 1):
            url = stat['url']
            count = stat.get('count', 0)

            # Show processing time details if available
            if 'target_processing_time' in stat:
                tpt = stat['target_processing_time']
                print(f"    {i}. {url} (count: {count})")
                print(f"       target_processing_time: avg={tpt.get('avg', 0):.4f}s, p95={tpt.get('p95', 0):.4f}s")
            else:
                print(f"    {i}. {url} (count: {count})")

        # Step 3: Create URLs file and filter
        print("\n[3/4] Filtering log by top 5 URLs...")
        urls_file = Path(log_file).parent / "top5_urls.json"
        with open(urls_file, 'w', encoding='utf-8') as f:
            json.dump({'urls': top_urls}, f, indent=2)

        filter_result = filterByCondition(
            log_file,
            log_format_file,
            'urls',
            f'urlsFile={urls_file}'
        )
        print(f"  ✓ Filtered: {filter_result['filteredLines']} / {filter_result['totalLines']} lines")
        print(f"  ✓ Filtered file: {filter_result['filePath']}")

        # Step 4: Generate XLog
        print("\n[4/4] Generating XLog...")
        xlog_result = generateXlog(filter_result['filePath'], log_format_file, 'html')
        print(f"  ✓ XLog generated: {xlog_result['filePath']}")

        print("\n" + "="*70)
        print("Pipeline completed successfully!")
        print("="*70)
        print(f"\nResults:")
        print(f"  - Statistics: {stats_result['filePath']}")
        print(f"  - Filtered log: {filter_result['filePath']}")
        print(f"  - XLog: {xlog_result['filePath']}")
        print(f"\nOpen the XLog HTML file to view the visualization.")
        print(f"\nNote: This pipeline used the NEW processing time analysis feature")
        print(f"      to get Top 5 URLs by target_processing_time in a single command!")

    except Exception as e:
        print(f"\n✗ Pipeline error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--example' and len(sys.argv) > 2:
            # Run example pipeline
            log_file = sys.argv[2]
            if not os.path.exists(log_file):
                print(f"Error: File not found: {log_file}")
                return

            print_banner()
            print(f"Running example pipeline on: {log_file}\n")

            # Detect format first
            format_result = recommendAccessLogFormat(log_file)
            log_format_file = format_result['logFormatFile']

            run_example_pipeline(log_file, log_format_file)
        else:
            # Interactive mode with provided file
            log_file = sys.argv[1]
            interactive_menu(log_file)
    else:
        # Interactive mode without file
        interactive_menu()


if __name__ == "__main__":
    main()
