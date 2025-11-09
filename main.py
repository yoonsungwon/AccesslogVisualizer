#!/usr/bin/python3
# -*- coding: utf-8 -*-
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
    generateMultiMetricDashboard,
    generateReceivedBytesPerURI,
    generateSentBytesPerURI
)


def print_banner():
    """Print application banner"""
    print("="*70)
    print(" Access Log Analyzer - MCP Tool Pipeline")
    print(" Version 1.0")
    print("="*70)
    print()


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
        print("  12. Run example pipeline")
        print("  0. Exit")
        print("="*70)

        choice = input("\nSelect operation (0-12): ").strip()

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

    try:
        result = generateXlog(log_file, log_format_file, 'html')
        print(f"\n✓ XLog generated:")
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

    try:
        result = generateRequestPerURI(
            log_file, 
            log_format_file, 
            'html', 
            topN=top_n, 
            interval=interval,
            patternsFile=patterns_file
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

    try:
        result = generateMultiMetricDashboard(log_file, log_format_file, 'html')
        print(f"\n✓ Dashboard generated:")
        print(f"  Total transactions: {result['totalTransactions']}")
        print(f"  Output file: {result['filePath']}")
        print(f"\n  Open the HTML file in your browser to view the dashboard.")
    except Exception as e:
        print(f"✗ Error: {e}")


def generate_received_bytes(log_file, log_format_file):
    """Generate Received Bytes per URI visualization"""
    print("\n--- Generate Received Bytes per URI ---")

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

    try:
        result = generateReceivedBytesPerURI(
            log_file,
            log_format_file,
            'html',
            topN=top_n,
            interval=interval,
            patternsFile=patterns_file
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

    try:
        result = generateSentBytesPerURI(
            log_file,
            log_format_file,
            'html',
            topN=top_n,
            interval=interval,
            patternsFile=patterns_file
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


def run_example_pipeline(log_file, log_format_file):
    """
    Run example pipeline demonstrating tool chaining.

    Example: "Extract top 5 URLs by average response time and generate XLog"

    Pipeline:
    1. Calculate URL statistics
    2. Extract top 5 URLs by avg response time
    3. Filter log by those URLs
    4. Generate XLog for filtered data
    """
    print("\n" + "="*70)
    print("Example Pipeline: Top 5 URLs by Response Time → XLog")
    print("="*70)

    try:
        # Step 1: Calculate statistics
        print("\n[1/4] Calculating statistics...")
        stats_result = calculateStats(log_file, log_format_file, 'statsType=url')
        print(f"  ✓ Stats file: {stats_result['filePath']}")

        # Step 2: Read statistics and extract top 5 URLs
        print("\n[2/4] Extracting top 5 URLs by avg response time...")
        import json
        with open(stats_result['filePath'], 'r', encoding='utf-8') as f:
            stats = json.load(f)

        url_stats = stats.get('urlStats', [])
        # Sort by avg response time (descending)
        url_stats_sorted = sorted(
            [s for s in url_stats if 'responseTime' in s],
            key=lambda x: x['responseTime']['avg'],
            reverse=True
        )[:5]

        top_urls = [s['url'] for s in url_stats_sorted]

        if not top_urls:
            print("  ✗ No URLs with response time data found.")
            return

        print(f"  ✓ Top 5 URLs:")
        for i, url in enumerate(top_urls, 1):
            avg_rt = next(s['responseTime']['avg'] for s in url_stats_sorted if s['url'] == url)
            print(f"    {i}. {url} (avg: {avg_rt:.2f})")

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
