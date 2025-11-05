#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Data Processor Module for Access Log Analyzer
Implements MCP tools: filterByCondition, extractUriPatterns, filterUriPatterns, calculateStats
"""
import pandas as pd
import numpy as np
import json
import re
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter
from urllib.parse import urlparse, parse_qs
import ipaddress

# Import core modules
from core.exceptions import (
    FileNotFoundError as CustomFileNotFoundError,
    ValidationError
)
from core.logging_config import get_logger

# Setup logger
logger = get_logger(__name__)


# ============================================================================
# MCP Tool: filterByCondition
# ============================================================================

def filterByCondition(inputFile, logFormatFile, condition, params):
    """
    Filter access log by various conditions.
    
    Args:
        inputFile (str): Input log file path
        logFormatFile (str): Log format JSON file path
        condition (str): Filter condition ('time', 'statusCode', 'responseTime', 'client', 'urls', 'uriPatterns')
        params (str): Parameter string (e.g., 'startTime=2024-08-08T09:00:00;endTime=2024-08-08T10:00:00')
        
    Returns:
        dict: {
            'filePath': str (absolute path),
            'totalLines': int,
            'filteredLines': int,
            'fileSize': str
        }
    """
    # Validate inputs
    if not inputFile or not os.path.exists(inputFile):
        raise CustomFileNotFoundError(inputFile)
    if not logFormatFile or not os.path.exists(logFormatFile):
        raise CustomFileNotFoundError(logFormatFile)
    if condition not in ['time', 'statusCode', 'responseTime', 'client', 'urls', 'uriPatterns']:
        raise ValidationError('condition', f"Invalid condition: {condition}. Must be one of: time, statusCode, responseTime, client, urls, uriPatterns")
    
    # Parse parameters
    param_dict = _parse_params(params)
    
    # Load log format
    with open(logFormatFile, 'r', encoding='utf-8') as f:
        format_info = json.load(f)
    
    # Generate output file path
    input_path = Path(inputFile)
    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
    output_file = input_path.parent / f"filtered_{timestamp}.log"
    
    # Read and filter log file
    from data_parser import parse_log_file_with_format
    log_df = parse_log_file_with_format(inputFile, logFormatFile)
    
    total_lines = len(log_df)
    
    # Apply filter based on condition
    if condition == 'time':
        log_df = _filter_by_time(log_df, param_dict, format_info)
    elif condition == 'statusCode':
        log_df = _filter_by_status_code(log_df, param_dict, format_info)
    elif condition == 'responseTime':
        log_df = _filter_by_response_time(log_df, param_dict, format_info)
    elif condition == 'client':
        log_df = _filter_by_client(log_df, param_dict, format_info)
    elif condition == 'urls':
        log_df = _filter_by_urls(log_df, param_dict, format_info)
    elif condition == 'uriPatterns':
        log_df = _filter_by_uri_patterns(log_df, param_dict, format_info)
    else:
        raise ValueError(f"Unknown condition: {condition}")
    
    filtered_lines = len(log_df)
    
    # Save filtered data to file (as JSON Lines for flexibility)
    log_df.to_json(output_file, orient='records', lines=True)
    
    file_size = os.path.getsize(output_file)
    file_size_str = _format_size(file_size)
    
    # Return absolute path
    return {
        'filePath': str(output_file.resolve()),
        'totalLines': total_lines,
        'filteredLines': filtered_lines,
        'fileSize': file_size_str
    }


def _parse_params(params):
    """Parse parameter string into dict"""
    param_dict = {}
    if not params:
        return param_dict
    
    for pair in params.split(';'):
        if '=' in pair:
            key, value = pair.split('=', 1)
            param_dict[key.strip()] = value.strip()
    
    return param_dict


def _filter_by_time(log_df, params, format_info):
    """Filter by time range with timezone support
    
    If timezone is not specified in time parameters, uses the timezone from log lines.
    """
    time_field = format_info['fieldMap'].get('timestamp', 'time')
    
    if time_field not in log_df.columns:
        logger.warning(f"Time field '{time_field}' not found in log data")
        return log_df
    
    # Get timezone information from format
    timezone_from_log = format_info.get('timezone', 'fromLog')
    
    # Convert to datetime if not already
    if not pd.api.types.is_datetime64_any_dtype(log_df[time_field]):
        log_df[time_field] = pd.to_datetime(log_df[time_field], errors='coerce')
    
    # Check if log_df time field is timezone-aware
    # Handle empty dataframe
    if len(log_df) == 0:
        return log_df
    
    is_log_timezone_aware = pd.api.types.is_datetime64tz_dtype(log_df[time_field])
    
    # Helper function to check if a timestamp is timezone-aware
    def _is_timezone_aware(ts):
        """Check if timestamp is timezone-aware"""
        if isinstance(ts, pd.Timestamp):
            return ts.tz is not None
        return False
    
    # Parse time parameters with timezone support
    # If timezone is not specified in time parameter, use timezone from log format
    def _parse_time_with_timezone(time_str, log_timezone, target_timezone_aware):
        """Parse time string with timezone handling
        
        If timezone is already in time_str (ISO 8601 with timezone), use it.
        Otherwise, use log_timezone from format_info.
        Returns a datetime that matches target_timezone_aware (True/False).
        """
        parsed_time = pd.to_datetime(time_str)
        
        # Check if parsed_time is timezone-aware
        is_parsed_timezone_aware = _is_timezone_aware(parsed_time)
        
        # If target needs naive datetime but we have timezone-aware, convert
        if not target_timezone_aware and is_parsed_timezone_aware:
            return parsed_time.tz_localize(None)
        
        # If target needs timezone-aware but we have naive
        if target_timezone_aware and not is_parsed_timezone_aware:
            # Check if timezone is already specified in ISO 8601 format
            timezone_in_str = False
            if 'T' in time_str:
                # Check for timezone indicators: Z, +HH:MM, -HH:MM
                if time_str.endswith('Z') or time_str.endswith('z') or \
                   re.search(r'[+-]\d{2}:?\d{2}$', time_str):
                    # Timezone in string, but parse might have failed
                    # Try parsing again with utc=True
                    try:
                        parsed_time = pd.to_datetime(time_str, utc=True)
                        return parsed_time
                    except:
                        pass
            
            # No timezone in parameter - apply log timezone
            if log_timezone == 'fromLog':
                # For 'fromLog', return naive (assume same timezone as log)
                return parsed_time
            elif log_timezone and log_timezone != 'UTC' and log_timezone != 'fromLog':
                # Apply timezone from format info
                try:
                    return parsed_time.tz_localize(log_timezone)
                except (TypeError, ValueError):
                    # If timezone invalid, return naive
                    return parsed_time
            elif log_timezone == 'UTC':
                try:
                    return parsed_time.tz_localize('UTC')
                except (TypeError, ValueError):
                    return parsed_time
        
        return parsed_time
    
    # Apply time filters
    if 'startTime' in params:
        start_time = _parse_time_with_timezone(
            params['startTime'], 
            timezone_from_log,
            is_log_timezone_aware
        )
        # Ensure both are same type for comparison
        # Double-check and convert if needed
        if not is_log_timezone_aware and _is_timezone_aware(start_time):
            # Log is naive but start_time is timezone-aware - convert start_time to naive
            try:
                start_time = start_time.tz_localize(None) if start_time.tz is not None else start_time
            except (TypeError, AttributeError):
                # If conversion fails, convert to UTC then remove timezone
                start_time = start_time.tz_convert('UTC').tz_localize(None)
        elif is_log_timezone_aware and not _is_timezone_aware(start_time):
            # Log is timezone-aware but start_time is naive - convert log to naive for comparison
            # Convert timezone-aware to naive by converting to UTC first, then removing timezone
            try:
                log_df[time_field] = log_df[time_field].dt.tz_convert('UTC').dt.tz_localize(None)
            except (TypeError, AttributeError):
                # If conversion fails, try direct removal
                log_df[time_field] = log_df[time_field].dt.tz_localize(None)
            is_log_timezone_aware = False
        
        log_df = log_df[log_df[time_field] >= start_time]
    
    if 'endTime' in params:
        end_time = _parse_time_with_timezone(
            params['endTime'], 
            timezone_from_log,
            is_log_timezone_aware
        )
        # Ensure both are same type for comparison
        # Double-check and convert if needed
        if not is_log_timezone_aware and _is_timezone_aware(end_time):
            # Log is naive but end_time is timezone-aware - convert end_time to naive
            try:
                end_time = end_time.tz_localize(None) if end_time.tz is not None else end_time
            except (TypeError, AttributeError):
                # If conversion fails, convert to UTC then remove timezone
                end_time = end_time.tz_convert('UTC').tz_localize(None)
        elif is_log_timezone_aware and not _is_timezone_aware(end_time):
            # Log is timezone-aware but end_time is naive - convert log to naive for comparison
            # Convert timezone-aware to naive by converting to UTC first, then removing timezone
            try:
                log_df[time_field] = log_df[time_field].dt.tz_convert('UTC').dt.tz_localize(None)
            except (TypeError, AttributeError):
                # If conversion fails, try direct removal
                log_df[time_field] = log_df[time_field].dt.tz_localize(None)
            is_log_timezone_aware = False
        
        log_df = log_df[log_df[time_field] <= end_time]
    
    return log_df


def _filter_by_status_code(log_df, params, format_info):
    """Filter by status code"""
    status_field = format_info['fieldMap'].get('status', 'elb_status_code')
    
    if status_field not in log_df.columns:
        logger.warning(f"Status field '{status_field}' not found in log data")
        return log_df
    
    # Parse status codes (e.g., '2xx,5xx' or '200,404,500')
    status_codes = params.get('statusCodes', '').split(',')
    
    if not status_codes or status_codes == ['']:
        return log_df
    
    # Convert to numeric
    log_df[status_field] = pd.to_numeric(log_df[status_field], errors='coerce')
    
    # Build filter condition
    mask = pd.Series([False] * len(log_df), index=log_df.index)
    
    for code in status_codes:
        code = code.strip()
        if code.endswith('xx'):
            # Range filter (e.g., 2xx, 5xx)
            prefix = int(code[0])
            mask |= (log_df[status_field] >= prefix * 100) & (log_df[status_field] < (prefix + 1) * 100)
        else:
            # Exact match
            mask |= (log_df[status_field] == int(code))
    
    return log_df[mask]


def _filter_by_response_time(log_df, params, format_info):
    """Filter by response time"""
    rt_field = format_info['fieldMap'].get('responseTime', 'target_processing_time')
    
    if rt_field not in log_df.columns:
        logger.warning(f"Response time field '{rt_field}' not found in log data")
        return log_df
    
    # Convert to numeric
    log_df[rt_field] = pd.to_numeric(log_df[rt_field], errors='coerce')
    
    # Get response time unit from format info
    rt_unit = format_info.get('responseTimeUnit', 'ms')
    
    # Parse min/max (support both 'minMs'/'maxMs' and 'min'/'max' with units)
    min_val = None
    max_val = None
    
    if 'minMs' in params:
        min_val = float(params['minMs'])
    elif 'min' in params:
        min_val = _parse_time_value(params['min'], rt_unit)
    
    if 'maxMs' in params:
        max_val = float(params['maxMs'])
    elif 'max' in params:
        max_val = _parse_time_value(params['max'], rt_unit)
    
    # Apply filters
    if min_val is not None:
        log_df = log_df[log_df[rt_field] >= min_val]
    
    if max_val is not None:
        log_df = log_df[log_df[rt_field] <= max_val]
    
    return log_df


def _parse_time_value(value_str, target_unit):
    """Parse time value with unit (e.g., '0.5s', '500ms') to target unit"""
    value_str = value_str.strip()
    
    # Extract number and unit
    match = re.match(r'([\d.]+)\s*([a-z]*)', value_str, re.IGNORECASE)
    if not match:
        return float(value_str)
    
    number = float(match.group(1))
    unit = match.group(2).lower() if match.group(2) else target_unit
    
    # Convert to target unit
    conversions = {
        's': {'ms': 1000, 'us': 1000000, 'ns': 1000000000, 's': 1},
        'ms': {'ms': 1, 'us': 1000, 'ns': 1000000, 's': 0.001},
        'us': {'ms': 0.001, 'us': 1, 'ns': 1000, 's': 0.000001},
        'ns': {'ms': 0.000001, 'us': 0.001, 'ns': 1, 's': 0.000000001}
    }
    
    if unit in conversions and target_unit in conversions[unit]:
        return number * conversions[unit][target_unit]
    
    return number


def _filter_by_client(log_df, params, format_info):
    """Filter by client IP"""
    ip_field = format_info['fieldMap'].get('clientIp', 'client_ip')
    
    if ip_field not in log_df.columns:
        logger.warning(f"Client IP field '{ip_field}' not found in log data")
        return log_df
    
    # Parse client IPs (support CIDR notation)
    client_ips = params.get('clientIps', '').split(',')
    
    if not client_ips or client_ips == ['']:
        return log_df
    
    # Build filter mask
    mask = pd.Series([False] * len(log_df), index=log_df.index)
    
    for ip_pattern in client_ips:
        ip_pattern = ip_pattern.strip()
        
        if '/' in ip_pattern:
            # CIDR notation
            try:
                network = ipaddress.ip_network(ip_pattern, strict=False)
                mask |= log_df[ip_field].apply(lambda x: _ip_in_network(x, network))
            except:
                logger.warning(f"Invalid CIDR notation: {ip_pattern}")
        else:
            # Exact match
            mask |= (log_df[ip_field] == ip_pattern)
    
    return log_df[mask]


def _ip_in_network(ip_str, network):
    """Check if IP is in network"""
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip in network
    except:
        return False


def _filter_by_urls(log_df, params, format_info):
    """Filter by URL list from file"""
    urls_file = params.get('urlsFile')
    
    if not urls_file:
        return log_df
    
    # Load URLs from file
    with open(urls_file, 'r', encoding='utf-8') as f:
        if urls_file.endswith('.json'):
            urls_data = json.load(f)
            if isinstance(urls_data, list):
                urls = urls_data
            elif isinstance(urls_data, dict) and 'urls' in urls_data:
                urls = urls_data['urls']
            else:
                urls = []
        else:
            urls = [line.strip() for line in f if line.strip()]
    
    url_field = format_info['fieldMap'].get('url', 'request_url')
    
    if url_field not in log_df.columns:
        logger.warning(f"URL field '{url_field}' not found in log data")
        return log_df
    
    # Filter by URL set
    url_set = set(urls)
    return log_df[log_df[url_field].isin(url_set)]


def _filter_by_uri_patterns(log_df, params, format_info):
    """Filter by URI patterns from file"""
    uris_file = params.get('urisFile')
    
    if not uris_file:
        return log_df
    
    # Load URI patterns from file
    with open(uris_file, 'r', encoding='utf-8') as f:
        if uris_file.endswith('.json'):
            patterns_data = json.load(f)
            if isinstance(patterns_data, list):
                patterns = patterns_data
            elif isinstance(patterns_data, dict) and 'patterns' in patterns_data:
                patterns = patterns_data['patterns']
            else:
                patterns = []
        else:
            patterns = [line.strip() for line in f if line.strip()]
    
    url_field = format_info['fieldMap'].get('url', 'request_url')
    
    if url_field not in log_df.columns:
        logger.warning(f"URL field '{url_field}' not found in log data")
        return log_df
    
    # Match URLs against patterns
    mask = pd.Series([False] * len(log_df), index=log_df.index)
    
    for pattern in patterns:
        # Convert URI pattern to regex (replace * with .*)
        regex_pattern = pattern.replace('*', '.*')
        mask |= log_df[url_field].str.match(regex_pattern, na=False)
    
    return log_df[mask]


def _format_size(size_bytes):
    """Format file size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"


# ============================================================================
# MCP Tool: extractUriPatterns
# ============================================================================

def extractUriPatterns(inputFile, logFormatFile, extractionType, params=''):
    """
    Extract URLs or URI patterns from access log.
    
    Args:
        inputFile (str): Input log file path
        logFormatFile (str): Log format JSON file path (required)
        extractionType (str): 'urls' or 'patterns'
        params (str): Parameters (includeParams, maxPatterns, minCount, etc.)
        
    Returns:
        dict: {
            'filePath': str (absolute path to urls_*.json or uris_*.json),
            'uniqueUrls': int (for urls type),
            'patternsFound': int (for patterns type),
            'totalRequests': int
        }
    """
    # Validate inputs
    if not inputFile or not os.path.exists(inputFile):
        raise ValueError(f"Input file not found: {inputFile}")
    if not logFormatFile or not os.path.exists(logFormatFile):
        raise ValueError(f"Log format file not found: {logFormatFile}")
    if extractionType not in ['urls', 'patterns']:
        raise ValueError(f"Invalid extractionType: {extractionType}. Must be 'urls' or 'patterns'")
    
    # Parse parameters
    param_dict = _parse_params(params)
    include_params = param_dict.get('includeParams', 'false').lower() == 'true'
    max_patterns = int(param_dict.get('maxPatterns', '100'))
    min_count = int(param_dict.get('minCount', '1'))
    max_count = int(param_dict.get('maxCount', '999999999'))
    
    # Load log format
    with open(logFormatFile, 'r', encoding='utf-8') as f:
        format_info = json.load(f)
    
    # Parse log file
    from data_parser import parse_log_file_with_format
    log_df = parse_log_file_with_format(inputFile, logFormatFile)
    
    url_field = format_info['fieldMap'].get('url', 'request_url')
    
    if url_field not in log_df.columns:
        raise ValueError(f"URL field '{url_field}' not found in log data")
    
    total_requests = len(log_df)
    
    # Generate output file
    input_path = Path(inputFile)
    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
    
    if extractionType == 'urls':
        # Extract unique URLs
        if include_params:
            urls = log_df[url_field].tolist()
        else:
            # Remove query parameters
            urls = log_df[url_field].apply(lambda x: x.split('?')[0] if x else x).tolist()
        
        url_counts = Counter(urls)
        
        # Filter by count range
        filtered_urls = {url: count for url, count in url_counts.items() 
                        if min_count <= count <= max_count}
        
        output_file = input_path.parent / f"urls_{timestamp}.json"
        
        # Save as JSON
        result_data = {
            'urls': list(filtered_urls.keys()),
            'counts': filtered_urls,
            'totalRequests': total_requests
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        
        # Return absolute path
        return {
            'filePath': str(output_file.resolve()),
            'uniqueUrls': len(filtered_urls),
            'totalRequests': total_requests
        }
    
    elif extractionType == 'patterns':
        # Extract URI patterns (replace path variables with *)
        if not include_params:
            urls = log_df[url_field].apply(lambda x: x.split('?')[0] if x else x).tolist()
        else:
            urls = log_df[url_field].tolist()
        
        patterns = _extract_uri_patterns(urls, max_patterns, min_count, max_count)
        pattern_list = list(patterns.keys())
        
        # Generate pattern rules from patterns
        pattern_rules = []
        for pattern in pattern_list:
            # Convert pattern with * wildcards to regex
            # First, replace * with a placeholder
            temp_pattern = pattern.replace('*', '__WILDCARD__')
            # Escape special regex characters
            escaped_pattern = re.escape(temp_pattern)
            # Replace placeholder with .* (regex wildcard)
            regex_pattern = escaped_pattern.replace('__WILDCARD__', '.*')
            
            pattern_rules.append({
                'pattern': f'^{regex_pattern}$',
                'replacement': pattern
            })
        
        output_file = input_path.parent / f"uris_{timestamp}.json"
        
        # Save as JSON with pattern rules only
        result_data = {
            'patternRules': pattern_rules,
            'counts': patterns,
            'totalRequests': total_requests
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        
        # Return absolute path
        return {
            'filePath': str(output_file.resolve()),
            'patternsFound': len(patterns),
            'totalRequests': total_requests
        }
    
    else:
        raise ValueError(f"Unknown extraction type: {extractionType}")


def _extract_uri_patterns(urls, max_patterns, min_count, max_count):
    """Extract URI patterns by replacing path variables with *"""
    # Count exact URLs first
    url_counts = Counter(urls)
    
    # Group similar URLs by replacing numbers with *
    pattern_groups = defaultdict(list)
    
    for url, count in url_counts.items():
        # Replace path segments that look like IDs/numbers with *
        pattern = _generalize_url(url)
        pattern_groups[pattern].append((url, count))
    
    # Calculate pattern counts
    pattern_counts = {}
    for pattern, url_list in pattern_groups.items():
        total_count = sum(count for _, count in url_list)
        if min_count <= total_count <= max_count:
            pattern_counts[pattern] = total_count
    
    # Sort by count and limit
    sorted_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)
    limited_patterns = dict(sorted_patterns[:max_patterns])
    
    return limited_patterns


# Global pattern rules cache (loaded from pattern file)
_pattern_rules_cache = None
_pattern_rules_file = None

def _load_pattern_rules(patterns_file=None):
    """Load pattern rules from file"""
    global _pattern_rules_cache, _pattern_rules_file
    
    # If no file specified or same file, return cached rules
    if patterns_file and patterns_file != _pattern_rules_file:
        _pattern_rules_cache = None
        _pattern_rules_file = None
    
    if _pattern_rules_cache is not None:
        return _pattern_rules_cache
    
    if not patterns_file or not os.path.exists(patterns_file):
        return None
    
    try:
        with open(patterns_file, 'r', encoding='utf-8') as f:
            pattern_data = json.load(f)
        
        # Check for patternRules (explicit regex rules)
        if 'patternRules' in pattern_data and isinstance(pattern_data['patternRules'], list):
            rules = []
            for rule in pattern_data['patternRules']:
                if isinstance(rule, dict) and 'pattern' in rule and 'replacement' in rule:
                    rules.append({
                        'pattern': re.compile(rule['pattern']),
                        'replacement': rule['replacement']
                    })
            if rules:
                _pattern_rules_cache = rules
                _pattern_rules_file = patterns_file
                return rules
        
        # Check for patterns list (match patterns)
        if 'patterns' in pattern_data:
            patterns = pattern_data['patterns']
            if isinstance(patterns, list) and patterns:
                # Convert patterns to regex rules
                rules = []
                for pattern in patterns:
                    if isinstance(pattern, str):
                        # Convert pattern with * wildcards to regex
                        # First, replace * with a placeholder
                        temp_pattern = pattern.replace('*', '__WILDCARD__')
                        # Escape special regex characters
                        escaped_pattern = re.escape(temp_pattern)
                        # Replace placeholder with .* (regex wildcard)
                        regex_pattern = escaped_pattern.replace('__WILDCARD__', '.*')
                        rules.append({
                            'pattern': re.compile(f'^{regex_pattern}$'),
                            'replacement': pattern
                        })
                if rules:
                    _pattern_rules_cache = rules
                    _pattern_rules_file = patterns_file
                    return rules
    
    except Exception as e:
        print(f"  Warning: Could not load pattern rules from {patterns_file}: {e}")
    
    return None


def _generalize_url(url, patterns_file=None):
    """
    Generalize URL by replacing path variables with * or using pattern rules from file.
    
    Args:
        url: URL string to generalize
        patterns_file: Optional path to pattern file with regex rules
    
    Returns:
        Generalized URL pattern
    """
    if not url:
        return url
    
    # Load pattern rules if file is provided
    pattern_rules = _load_pattern_rules(patterns_file) if patterns_file else None
    
    # Try pattern rules first
    if pattern_rules:
        for rule in pattern_rules:
            if rule['pattern'].match(url):
                return rule['replacement']
    
    # Fallback to default generalization
    # Split into path and query
    parts = url.split('?')
    path = parts[0]
    
    # Split path into segments
    segments = path.split('/')
    
    # Generalize each segment
    generalized = []
    for segment in segments:
        if not segment:
            generalized.append(segment)
            continue
        
        # Check if segment looks like an ID
        if _is_id_like(segment):
            generalized.append('*')
        else:
            generalized.append(segment)
    
    result = '/'.join(generalized)
    
    # Append query placeholder if present
    if len(parts) > 1:
        result += '?*'
    
    return result


def _is_id_like(segment):
    """Check if segment looks like an ID/UUID/number"""
    # Pure numbers
    if segment.isdigit():
        return True
    
    # UUID pattern
    if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', segment, re.I):
        return True
    
    # Long hex strings
    if re.match(r'^[0-9a-f]{16,}$', segment, re.I):
        return True
    
    # Mixed alphanumeric that's mostly numbers
    if len(segment) > 8 and sum(c.isdigit() for c in segment) / len(segment) > 0.7:
        return True
    
    return False


# ============================================================================
# MCP Tool: filterUriPatterns
# ============================================================================

def filterUriPatterns(urisFile, params=''):
    """
    Filter URI patterns file by include/exclude patterns.
    
    Args:
        urisFile (str): URI patterns file path
        params (str): Parameters (excludePatterns, includePatterns, caseSensitive, useRegex)
        
    Returns:
        dict: {
            'filePath': str,
            'originalCount': int,
            'filteredCount': int
        }
    """
    # Parse parameters
    param_dict = _parse_params(params)
    exclude_patterns = param_dict.get('excludePatterns', '').split(',')
    include_patterns = param_dict.get('includePatterns', '').split(',')
    case_sensitive = param_dict.get('caseSensitive', 'false').lower() == 'true'
    use_regex = param_dict.get('useRegex', 'false').lower() == 'true'
    
    # Load URI patterns
    with open(urisFile, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    patterns = data.get('patterns', [])
    counts = data.get('counts', {})
    original_count = len(patterns)
    
    # Apply filters
    filtered_patterns = []
    
    for pattern in patterns:
        # Check exclude patterns
        if exclude_patterns and exclude_patterns != ['']:
            excluded = False
            for ex_pattern in exclude_patterns:
                ex_pattern = ex_pattern.strip()
                if not ex_pattern:
                    continue
                
                if use_regex:
                    if re.search(ex_pattern, pattern, 0 if case_sensitive else re.IGNORECASE):
                        excluded = True
                        break
                else:
                    if case_sensitive:
                        if ex_pattern in pattern:
                            excluded = True
                            break
                    else:
                        if ex_pattern.lower() in pattern.lower():
                            excluded = True
                            break
            
            if excluded:
                continue
        
        # Check include patterns
        if include_patterns and include_patterns != ['']:
            included = False
            for in_pattern in include_patterns:
                in_pattern = in_pattern.strip()
                if not in_pattern:
                    continue
                
                if use_regex:
                    if re.search(in_pattern, pattern, 0 if case_sensitive else re.IGNORECASE):
                        included = True
                        break
                else:
                    if case_sensitive:
                        if in_pattern in pattern:
                            included = True
                            break
                    else:
                        if in_pattern.lower() in pattern.lower():
                            included = True
                            break
            
            if not included:
                continue
        
        filtered_patterns.append(pattern)
    
    # Generate output file
    input_path = Path(urisFile)
    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
    output_file = input_path.parent / f"uris_filtered_{timestamp}.json"
    
    # Save filtered patterns
    filtered_counts = {p: counts.get(p, 0) for p in filtered_patterns}
    result_data = {
        'patterns': filtered_patterns,
        'counts': filtered_counts,
        'totalRequests': data.get('totalRequests', 0)
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)
    
    return {
        'filePath': str(output_file),
        'originalCount': original_count,
        'filteredCount': len(filtered_patterns)
    }


# ============================================================================
# MCP Tool: calculateStats
# ============================================================================

def calculateStats(inputFile, logFormatFile, params=''):
    """
    Calculate statistics from access log.
    
    Args:
        inputFile (str): Input log file path
        logFormatFile (str): Log format JSON file path
        params (str): Parameters (statsType, timeInterval)
            - statsType: 'all', 'summary', 'url', 'time', 'ip' (comma-separated)
            - timeInterval: '1h', '30m', '10m', '5m', '1m'
        
    Returns:
        dict: {
            'filePath': str (absolute path to stats_*.json),
            'summary': str
        }
    """
    # Validate inputs
    if not inputFile or not os.path.exists(inputFile):
        raise ValueError(f"Input file not found: {inputFile}")
    if not logFormatFile or not os.path.exists(logFormatFile):
        raise ValueError(f"Log format file not found: {logFormatFile}")
    
    # Parse parameters
    param_dict = _parse_params(params)
    stats_types = param_dict.get('statsType', 'all').split(',')
    stats_types = [s.strip() for s in stats_types]
    time_interval = param_dict.get('timeInterval', '10m')
    
    # Expand 'all' to include everything
    if 'all' in stats_types:
        stats_types = ['summary', 'url', 'time', 'ip']
    
    # Load log format
    with open(logFormatFile, 'r', encoding='utf-8') as f:
        format_info = json.load(f)
    
    # Parse log file
    from data_parser import parse_log_file_with_format
    log_df = parse_log_file_with_format(inputFile, logFormatFile)
    
    if log_df.empty:
        raise ValueError("No data to analyze")
    
    # Get field mappings
    time_field = format_info['fieldMap'].get('timestamp', 'time')
    url_field = format_info['fieldMap'].get('url', 'request_url')
    status_field = format_info['fieldMap'].get('status', 'elb_status_code')
    rt_field = format_info['fieldMap'].get('responseTime', 'target_processing_time')
    ip_field = format_info['fieldMap'].get('clientIp', 'client_ip')
    
    # Convert types
    if time_field in log_df.columns:
        log_df[time_field] = pd.to_datetime(log_df[time_field], errors='coerce')
    if status_field in log_df.columns:
        log_df[status_field] = pd.to_numeric(log_df[status_field], errors='coerce')
    if rt_field in log_df.columns:
        log_df[rt_field] = pd.to_numeric(log_df[rt_field], errors='coerce')
    
    # Calculate statistics
    result = {}
    
    if 'summary' in stats_types:
        result['summary'] = _calculate_summary_stats(log_df, url_field, ip_field, status_field, rt_field)
    
    if 'url' in stats_types:
        result['urlStats'] = _calculate_url_stats(log_df, url_field, status_field, rt_field)
    
    if 'time' in stats_types:
        result['timeStats'] = _calculate_time_stats(log_df, time_field, status_field, rt_field, time_interval)
    
    if 'ip' in stats_types:
        result['ipStats'] = _calculate_ip_stats(log_df, ip_field, status_field, rt_field)
    
    # Generate output file
    input_path = Path(inputFile)
    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
    output_file = input_path.parent / f"stats_{timestamp}.json"
    
    # Save to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    # Generate summary text
    summary_text = _generate_summary_text(result, stats_types)
    
    # Return absolute path
    return {
        'filePath': str(output_file.resolve()),
        'summary': summary_text
    }


def _calculate_summary_stats(log_df, url_field, ip_field, status_field, rt_field):
    """Calculate overall summary statistics"""
    stats = {
        'totalRequests': len(log_df),
        'uniqueUrls': log_df[url_field].nunique() if url_field in log_df.columns else 0,
        'uniqueIps': log_df[ip_field].nunique() if ip_field in log_df.columns else 0
    }
    
    # Status code distribution
    if status_field in log_df.columns:
        status_counts = log_df[status_field].value_counts().to_dict()
        stats['statusCodeDistribution'] = {str(k): int(v) for k, v in status_counts.items() if pd.notna(k)}
    
    # Response time statistics
    if rt_field in log_df.columns:
        rt_data = log_df[rt_field].dropna()
        if not rt_data.empty:
            stats['responseTime'] = {
                'avg': float(rt_data.mean()),
                'median': float(rt_data.median()),
                'std': float(rt_data.std()),
                'min': float(rt_data.min()),
                'max': float(rt_data.max()),
                'p10': float(rt_data.quantile(0.1)),
                'p90': float(rt_data.quantile(0.9)),
                'p95': float(rt_data.quantile(0.95)),
                'p99': float(rt_data.quantile(0.99))
            }
    
    return stats


def _calculate_url_stats(log_df, url_field, status_field, rt_field):
    """Calculate per-URL statistics"""
    if url_field not in log_df.columns:
        return []
    
    # Group by URL
    url_groups = log_df.groupby(url_field)
    
    url_stats = []
    
    for url, group in url_groups:
        stat = {
            'url': url,
            'count': len(group)
        }
        
        # Status code distribution
        if status_field in group.columns:
            status_counts = group[status_field].value_counts().to_dict()
            stat['statusCodes'] = {str(k): int(v) for k, v in status_counts.items() if pd.notna(k)}
        
        # Response time statistics
        if rt_field in group.columns:
            rt_data = group[rt_field].dropna()
            if not rt_data.empty:
                stat['responseTime'] = {
                    'avg': float(rt_data.mean()),
                    'median': float(rt_data.median()),
                    'std': float(rt_data.std()),
                    'min': float(rt_data.min()),
                    'max': float(rt_data.max()),
                    'p90': float(rt_data.quantile(0.9)),
                    'p95': float(rt_data.quantile(0.95)),
                    'p99': float(rt_data.quantile(0.99))
                }
        
        url_stats.append(stat)
    
    # Sort by count (descending)
    url_stats.sort(key=lambda x: x['count'], reverse=True)
    
    return url_stats


def _calculate_time_stats(log_df, time_field, status_field, rt_field, interval):
    """Calculate time-series statistics"""
    if time_field not in log_df.columns:
        return []
    
    # Parse interval
    freq_map = {
        '1h': '1H',
        '30m': '30T',
        '10m': '10T',
        '5m': '5T',
        '1m': '1T'
    }
    
    freq = freq_map.get(interval, '10T')
    
    # Group by time interval
    log_df['time_bucket'] = log_df[time_field].dt.floor(freq)
    time_groups = log_df.groupby('time_bucket')
    
    time_stats = []
    
    for time_bucket, group in time_groups:
        stat = {
            'time': time_bucket.isoformat() if pd.notna(time_bucket) else None,
            'count': len(group)
        }
        
        # Status code distribution
        if status_field in group.columns:
            error_count = (group[status_field] >= 400).sum()
            stat['errorCount'] = int(error_count)
            stat['errorRate'] = float(error_count / len(group)) if len(group) > 0 else 0.0
        
        # Response time statistics
        if rt_field in group.columns:
            rt_data = group[rt_field].dropna()
            if not rt_data.empty:
                stat['avgResponseTime'] = float(rt_data.mean())
                stat['p95ResponseTime'] = float(rt_data.quantile(0.95))
        
        time_stats.append(stat)
    
    # Sort by time
    time_stats.sort(key=lambda x: x['time'] if x['time'] else '')
    
    return time_stats


def _calculate_ip_stats(log_df, ip_field, status_field, rt_field):
    """Calculate per-IP statistics"""
    if ip_field not in log_df.columns:
        return []
    
    # Group by IP
    ip_groups = log_df.groupby(ip_field)
    
    ip_stats = []
    
    for ip, group in ip_groups:
        stat = {
            'ip': ip,
            'count': len(group)
        }
        
        # Status code distribution
        if status_field in group.columns:
            error_count = (group[status_field] >= 400).sum()
            stat['errorCount'] = int(error_count)
        
        # Response time average
        if rt_field in group.columns:
            rt_data = group[rt_field].dropna()
            if not rt_data.empty:
                stat['avgResponseTime'] = float(rt_data.mean())
        
        ip_stats.append(stat)
    
    # Sort by count (descending)
    ip_stats.sort(key=lambda x: x['count'], reverse=True)
    
    # Limit to top 100 IPs
    return ip_stats[:100]


def _generate_summary_text(result, stats_types):
    """Generate summary text from statistics"""
    lines = []
    
    if 'summary' in result:
        summary = result['summary']
        lines.append(f"Total Requests: {summary['totalRequests']}")
        lines.append(f"Unique URLs: {summary['uniqueUrls']}")
        lines.append(f"Unique IPs: {summary['uniqueIps']}")
        
        if 'responseTime' in summary:
            rt = summary['responseTime']
            lines.append(f"Avg Response Time: {rt['avg']:.3f}")
            lines.append(f"P95 Response Time: {rt['p95']:.3f}")
            lines.append(f"P99 Response Time: {rt['p99']:.3f}")
    
    if 'urlStats' in result:
        lines.append(f"\nTotal URL Patterns: {len(result['urlStats'])}")
        if result['urlStats']:
            lines.append("\nTop 5 URLs by Request Count:")
            for i, stat in enumerate(result['urlStats'][:5], 1):
                lines.append(f"  {i}. {stat['url']} ({stat['count']} requests)")
    
    if 'timeStats' in result:
        lines.append(f"\nTime Intervals: {len(result['timeStats'])}")
    
    if 'ipStats' in result:
        lines.append(f"\nUnique IPs: {len(result['ipStats'])}")
    
    return '\n'.join(lines)


# ============================================================================
# Legacy Function: aggregate_data (for main.py)
# ============================================================================

def aggregate_data(log_df):
    """
    Aggregate parsed log data for time-series analysis (legacy function for main.py).
    
    Args:
        log_df (pandas.DataFrame): Parsed log DataFrame
        
    Returns:
        pandas.DataFrame: Aggregated time-series data
    """
    # Detect time field
    time_field = 'time' if 'time' in log_df.columns else None
    if time_field is None:
        # Try to find datetime column
        datetime_cols = [col for col in log_df.columns if pd.api.types.is_datetime64_any_dtype(log_df[col])]
        if datetime_cols:
            time_field = datetime_cols[0]
        else:
            raise ValueError("No time/datetime field found in log data")
    
    # Convert to datetime if not already
    if not pd.api.types.is_datetime64_any_dtype(log_df[time_field]):
        log_df[time_field] = pd.to_datetime(log_df[time_field], errors='coerce')
    
    # Remove invalid times
    log_df = log_df.dropna(subset=[time_field])
    
    # Create time buckets (1 minute intervals)
    log_df['time_bucket'] = log_df[time_field].dt.floor('1T')
    
    # Detect status and response time fields
    status_field = 'elb_status_code' if 'elb_status_code' in log_df.columns else None
    rt_field = 'target_processing_time' if 'target_processing_time' in log_df.columns else None
    
    # Aggregate by time bucket
    aggregated = []
    
    for time_bucket, group in log_df.groupby('time_bucket'):
        agg_row = {
            'time': time_bucket,
            'request_count': len(group)
        }
        
        if status_field and status_field in group.columns:
            agg_row['error_count'] = (pd.to_numeric(group[status_field], errors='coerce') >= 400).sum()
            agg_row['error_rate'] = agg_row['error_count'] / len(group) * 100
            
            status_counts = group[status_field].value_counts()
            agg_row['status_2xx'] = status_counts.get('2xx', 0) + status_counts.get(200, 0)
            agg_row['status_4xx'] = status_counts.get('4xx', 0) + status_counts.get(400, 0)
            agg_row['status_5xx'] = status_counts.get('5xx', 0) + status_counts.get(500, 0)
        
        if rt_field and rt_field in group.columns:
            rt_data = pd.to_numeric(group[rt_field], errors='coerce').dropna()
            if not rt_data.empty:
                agg_row['avg_response_time'] = float(rt_data.mean())
                agg_row['p95_response_time'] = float(rt_data.quantile(0.95))
                agg_row['p99_response_time'] = float(rt_data.quantile(0.99))
        
        aggregated.append(agg_row)
    
    result_df = pd.DataFrame(aggregated)
    
    if not result_df.empty:
        result_df = result_df.sort_values('time').reset_index(drop=True)
    
    return result_df


# Main function for testing
if __name__ == "__main__":
    logger.info("Data Processor Module - MCP Tools")
    logger.info("Available tools:")
    logger.info("  - filterByCondition(inputFile, logFormatFile, condition, params)")
    logger.info("  - extractUriPatterns(inputFile, logFormatFile, extractionType, params)")
    logger.info("  - filterUriPatterns(urisFile, params)")
    logger.info("  - calculateStats(inputFile, logFormatFile, params)")