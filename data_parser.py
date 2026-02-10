#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Log Parser Module for Access Log Analyzer
Supports ALB, Apache/Nginx (HTTPD), JSON, and GROK patterns
Implements MCP tool: recommendAccessLogFormat, parseAccessLog
"""
import gzip
import pandas as pd
import re
import yaml
import json
import os
import glob
from datetime import datetime
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from multiprocessing import Pool, cpu_count
from functools import partial
import itertools

# Import core modules
from core.exceptions import (
    FileNotFoundError as CustomFileNotFoundError,
    InvalidFormatError,
    ParseError
)
from core.config import ConfigManager
from core.logging_config import get_logger

# Setup logger
logger = get_logger(__name__)


# ============================================================================
# MCP Tool: recommendAccessLogFormat
# ============================================================================

def recommendAccessLogFormat(inputFile: str) -> Dict[str, Any]:
    """
    Automatically detect and recommend access log format.
    Returns a logFormatFile (JSON) with pattern, field mappings, and metadata.
    
    If a log format file exists in the same directory, it will be used preferentially.
    
    Args:
        inputFile (str): Input log file path
        
    Returns:
        dict: {
            'logFormatFile': str (path to generated JSON file),
            'logPattern': str,
            'patternType': str (HTTPD|GROK|JSON|ALB),
            'fieldMap': dict,
            'responseTimeUnit': str (s|ms|us|ns),
            'timezone': str,
            'successRate': float (0~1),
            'confidence': float (0~1)
        }
    """
    # Validate input first
    if not inputFile or not os.path.exists(inputFile):
        raise CustomFileNotFoundError(inputFile)

    config, _ = _load_config_near_input(inputFile)
    configured_log_regex = config.get('log_regex', '') if config else ''
    if isinstance(configured_log_regex, str):
        configured_log_regex = configured_log_regex.strip()
    else:
        configured_log_regex = ''

    configured_apache_log_format = config.get('apache_log_format', '') if config else ''
    if isinstance(configured_apache_log_format, str):
        configured_apache_log_format = configured_apache_log_format.strip()
    else:
        configured_apache_log_format = ''
    
    input_path = Path(inputFile)
    
    # Check if log format file exists in the same directory (우선 탐색)
    # Look for existing logformat_*.json files
    log_format_files = list(input_path.parent.glob("logformat_*.json"))
    if log_format_files and not configured_log_regex and not configured_apache_log_format:
        # Use the most recent log format file
        latest_format_file = max(log_format_files, key=lambda p: p.stat().st_mtime)
        logger.info(f"Found existing log format file: {latest_format_file}")
        logger.info("Using existing format file (우선 탐색)")
        
        # Load and return existing format
        with open(latest_format_file, 'r', encoding='utf-8') as f:
            existing_format = json.load(f)
        
        # Validate that it's a valid format file
        if all(key in existing_format for key in ['logPattern', 'patternType', 'fieldMap']):
            # Return absolute path for logFormatFile
            existing_format['logFormatFile'] = str(Path(latest_format_file).resolve())
            return existing_format
    
    # Sample lines from input file
    sample_lines = _sample_log_lines(inputFile, n=100)
    
    if not sample_lines:
        raise ValueError(f"No valid lines found in {inputFile}")
    
    if configured_log_regex:
        try:
            compiled_regex = re.compile(configured_log_regex)
        except re.error as e:
            raise InvalidFormatError(f"Invalid log_regex in config.yaml: {e}", format_type='GROK')

        columns = [
            group_name for group_name, _ in sorted(compiled_regex.groupindex.items(), key=lambda item: item[1])
        ]
        format_info = {
            'logPattern': configured_log_regex,
            'patternType': 'GROK',
            'fieldMap': _build_field_map_from_columns(columns, {}),
            'columns': columns,
            'responseTimeUnit': 'ms',
            'timezone': 'fromLog'
        }
        confidence = 1.0
    elif configured_apache_log_format:
        try:
            from apache_logformat_converter import parse_apache_logformat
            regex_pattern, columns, column_types = parse_apache_logformat(configured_apache_log_format)
        except Exception as e:
            raise InvalidFormatError(f"Invalid apache_log_format in config.yaml: {e}", format_type='HTTPD')

        if (
            not isinstance(regex_pattern, str) or
            not regex_pattern.strip() or
            not isinstance(columns, list) or
            not all(isinstance(col, str) and col for col in columns) or
            not isinstance(column_types, dict)
        ):
            raise InvalidFormatError(
                "Invalid apache_log_format in config.yaml: converter returned invalid output",
                format_type='HTTPD'
            )

        try:
            re.compile(regex_pattern)
        except re.error as e:
            raise InvalidFormatError(f"Invalid apache_log_format in config.yaml: {e}", format_type='HTTPD')

        response_time_unit = 'ms'
        if 'response_time_us' in columns:
            response_time_unit = 'us'
        elif 'response_time_s' in columns:
            response_time_unit = 's'

        format_info = {
            'logPattern': regex_pattern,
            'patternType': 'HTTPD',
            'fieldMap': _build_field_map_from_columns(columns, {}),
            'columns': columns,
            'columnTypes': column_types,
            'responseTimeUnit': response_time_unit,
            'timezone': 'fromLog'
        }
        confidence = 1.0
    else:
        # Detect log type
        log_type, confidence = _detect_log_type(sample_lines)

        # Generate format candidates based on type
        if log_type == 'ALB':
            format_info = _generate_alb_format(inputFile)
        elif log_type == 'JSON':
            format_info = _generate_json_format(sample_lines)
        elif log_type == 'APACHE':
            format_info = _generate_apache_format(sample_lines)
        else:
            format_info = _generate_grok_format(sample_lines)
    
    # Test pattern on sample lines
    success_count = 0
    failed_sample_lines = []  # Collect failed lines for output
    
    for line_num, line in enumerate(sample_lines[:50], 1):  # Test on first 50 lines
        if _test_pattern(line, format_info['logPattern'], format_info['patternType']):
            success_count += 1
        else:
            # Collect failed lines (파싱에 실패한 라인은 화면에 출력함)
            if line.strip():
                failed_sample_lines.append((line_num, line))
    
    success_rate = success_count / min(50, len(sample_lines))
    
    # Output failed lines during format recommendation (파싱에 실패한 라인은 화면에 출력함)
    if failed_sample_lines:
        logger.warning(f"포맷 추천 단계에서 파싱에 실패한 샘플 라인 ({len(failed_sample_lines)}건):")
        for line_num, failed_line in failed_sample_lines[:10]:
            logger.warning(f"Sample Line {line_num}: {failed_line[:100]}...")  # Truncate long lines
        if len(failed_sample_lines) > 10:
            logger.warning(f"... and {len(failed_sample_lines) - 10} more failed sample lines")
    
    # Generate logFormatFile path (same directory as input)
    input_path = Path(inputFile)
    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
    log_format_file = input_path.parent / f"logformat_{timestamp}.json"
    
    # Prepare result
    result = {
        'logFormatFile': str(log_format_file.resolve()),  # Return absolute path
        'logPattern': format_info['logPattern'],
        'patternType': format_info['patternType'],
        'fieldMap': format_info['fieldMap'],
        'responseTimeUnit': format_info['responseTimeUnit'],
        'timezone': format_info['timezone'],
        'successRate': success_rate,
        'confidence': confidence * success_rate
    }
    
    # Include columns if available (for ALB parsing with config.yaml)
    if 'columns' in format_info:
        result['columns'] = format_info['columns']

    # Include columnTypes if available
    if 'columnTypes' in format_info:
        result['columnTypes'] = format_info['columnTypes']

    # Save to JSON file
    with open(log_format_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    return result


def _sample_log_lines(file_path: str, n: int = 100) -> List[str]:
    """Sample n lines from log file (supports gzip)"""
    lines = []
    try:
        # Try gzip first
        try:
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i >= n:
                        break
                    line = line.strip()
                    if line:
                        lines.append(line)
        except:
            # Try plain text
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f):
                    if i >= n:
                        break
                    line = line.strip()
                    if line:
                        lines.append(line)
    except Exception as e:
        logger.error(f"Error sampling file {file_path}: {e}")
    
    return lines


def _load_config_near_input(input_file: Optional[str] = None) -> Tuple[Dict[str, Any], Optional[Path]]:
    """Load config.yaml near the input file using legacy search order."""
    config_paths: List[Path] = []

    if input_file:
        input_path = Path(input_file)
        # 1. Same directory as input file
        config_paths.append(input_path.parent / 'config.yaml')
        # 2. Parent directory
        config_paths.append(input_path.parent.parent / 'config.yaml')

    # 3. Current working directory
    config_paths.append(Path.cwd() / 'config.yaml')
    # 4. Script directory (where data_parser.py is located)
    script_dir = Path(__file__).parent
    config_paths.append(script_dir / 'config.yaml')

    for config_path in config_paths:
        if config_path.exists():
            try:
                return load_config_legacy(str(config_path)) or {}, config_path
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
                continue

    return {}, None


def _detect_log_type(sample_lines: List[str]) -> Tuple[str, float]:
    """Detect log type from sample lines"""
    scores = {'ALB': 0, 'JSON': 0, 'APACHE': 0, 'GROK': 0}
    
    for line in sample_lines[:20]:
        # ALB detection
        if line.startswith(('http ', 'https ', 'h2 ', 'ws ', 'wss ')):
            tokens = line.split()
            if len(tokens) > 10 and 'app/' in line:
                scores['ALB'] += 1
        
        # JSON detection
        stripped = line.strip()
        if stripped.startswith(('{', '[')):
            try:
                json.loads(stripped)
                scores['JSON'] += 1
            except:
                pass
        
        # Apache/Nginx detection (Combined/Common log format)
        if '"' in line and '[' in line:
            # Pattern: IP [timestamp] "METHOD URL PROTO" status bytes
            if re.search(r'\d+\.\d+\.\d+\.\d+.*\[.*\].*"[A-Z]+.*".*\d{3}', line):
                scores['APACHE'] += 1
    
    # Determine type with highest score
    max_score = max(scores.values())
    if max_score == 0:
        return 'GROK', 0.1
    
    detected_type = max(scores.items(), key=lambda item: item[1])[0]
    confidence = max_score / len(sample_lines[:20])
    
    return detected_type, confidence


def _generate_alb_format(input_file=None):
    """Generate log format specification using config.yaml if available

    Supports multiple log format types: ALB, HTTPD, JSON, GROK, Nginx

    Args:
        input_file (str, optional): Input log file path to find config.yaml in same directory

    Returns:
        dict: Format specification with pattern, columns, field_map, etc.
    """
    # Try to load config.yaml
    config, config_path = _load_config_near_input(input_file)
    if config_path:
        logger.info(f"Loaded config from: {config_path}")

    if not config:
        # No config found - return default ALB format
        logger.info("No config.yaml found, using default ALB format")
        return _get_default_alb_format()

    # Determine log format type
    log_format_type = config.get('log_format_type', 'ALB').upper()
    logger.info(f"Log format type from config: {log_format_type}")

    # Handle different log format types
    if log_format_type == 'HTTPD' or log_format_type == 'APACHE':
        return _load_httpd_format_from_config(config)
    elif log_format_type == 'NGINX':
        return _load_nginx_format_from_config(config)
    elif log_format_type == 'JSON':
        return _load_json_format_from_config(config)
    elif log_format_type == 'GROK':
        return _load_grok_format_from_config(config)
    elif log_format_type == 'ALB':
        return _load_alb_format_from_config(config)
    else:
        # Unknown type - return default ALB
        logger.warning(f"Unknown log_format_type: {log_format_type}, using default ALB format")
        return _get_default_alb_format()


def _get_default_alb_format():
    """Return default ALB format specification"""
    pattern = r'([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*):([0-9]*) ([^ ]*)[:-]([0-9]*) ([-.0-9]*) ([-.0-9]*) ([-.0-9]*) (|[-0-9]*) (-|[-0-9]*) ([-0-9]*) ([-0-9]*) "([^ ]*) (.*?) (- |[^ ]*)" "([^"]*)" ([A-Z0-9-_]+) ([A-Za-z0-9.-]*) ([^ ]*) "([^"]*)" "([^"]*)" "([^"]*)" ([-.0-9]*) ([^ ]*) "([^"]*)"'

    return {
        'logPattern': pattern,
        'patternType': 'ALB',
        'fieldMap': {
            'timestamp': 'time',
            'method': 'request_verb',
            'url': 'request_url',
            'status': 'elb_status_code',
            'responseTime': 'target_processing_time',
            'clientIp': 'client_ip'
        },
        'responseTimeUnit': 's',
        'timezone': 'UTC'
    }


def _load_alb_format_from_config(config):
    """Load ALB format from config.yaml"""
    # Try format-specific section first
    alb_config = config.get('alb', {})

    # Check if ALB config is valid
    if not alb_config or 'log_pattern' not in alb_config:
        logger.warning("ALB config incomplete, using default")
        return _get_default_alb_format()

    pattern = alb_config.get('log_pattern')
    columns = alb_config.get('columns', [])

    if not pattern or not columns:
        logger.warning("ALB pattern or columns missing, using default")
        return _get_default_alb_format()

    # Build field map from config columns
    field_map = _build_field_map_from_columns(columns, alb_config.get('field_map', {}))

    return {
        'logPattern': pattern,
        'patternType': 'ALB',
        'fieldMap': field_map,
        'columns': columns,
        'responseTimeUnit': 's',
        'timezone': 'UTC'
    }


def _load_httpd_format_from_config(config):
    """Load Apache/HTTPD format from config.yaml"""
    # Try httpd_with_time first (more detailed format)
    httpd_config = config.get('httpd_with_time', {})
    pattern_type = 'HTTPD'

    if not httpd_config or 'log_pattern' not in httpd_config:
        # Fall back to basic httpd config
        httpd_config = config.get('httpd', {})

    if not httpd_config or 'log_pattern' not in httpd_config:
        logger.warning("HTTPD config not found in config.yaml, using default Apache Combined format")
        return _generate_apache_format([])

    pattern = httpd_config.get('log_pattern')
    columns = httpd_config.get('columns', [])
    field_map = httpd_config.get('field_map', {})

    # If no explicit field_map, build from columns
    if not field_map:
        field_map = _build_field_map_from_columns(columns, {})

    return {
        'logPattern': pattern,
        'patternType': pattern_type,
        'fieldMap': field_map,
        'columns': columns,
        'responseTimeUnit': 'ms',
        'timezone': 'fromLog'
    }


def _load_nginx_format_from_config(config):
    """Load Nginx format from config.yaml"""
    nginx_config = config.get('nginx', {})

    if not nginx_config or 'log_pattern' not in nginx_config:
        logger.warning("Nginx config not found, using default")
        # Return default Nginx format
        pattern = r'([^ ]*) - ([^ ]*) \[([^\]]*)\] "([^ ]*) ([^ ]*) ([^"]*)" ([0-9]*) ([0-9\-]*) "([^"]*)" "([^"]*)" ([0-9.]+)'
        columns = ['client_ip', 'remote_user', 'time', 'request_method', 'request_url',
                   'request_proto', 'status', 'bytes_sent', 'referer', 'user_agent', 'request_time']
        field_map = {
            'timestamp': 'time',
            'method': 'request_method',
            'url': 'request_url',
            'status': 'status',
            'responseTime': 'request_time',
            'clientIp': 'client_ip'
        }
    else:
        pattern = nginx_config.get('log_pattern')
        columns = nginx_config.get('columns', [])
        field_map = nginx_config.get('field_map', {})

        if not field_map:
            field_map = _build_field_map_from_columns(columns, {})

    return {
        'logPattern': pattern,
        'patternType': 'HTTPD',
        'fieldMap': field_map,
        'columns': columns,
        'responseTimeUnit': 's',
        'timezone': 'fromLog'
    }


def _load_json_format_from_config(config):
    """Load JSON format from config.yaml"""
    json_config = config.get('json', {})
    field_map = json_config.get('field_map', {})

    if not field_map:
        # Default JSON field mapping
        field_map = {
            'timestamp': 'timestamp',
            'method': 'method',
            'url': 'url',
            'status': 'status',
            'responseTime': 'response_time',
            'clientIp': 'client_ip'
        }

    return {
        'logPattern': 'JSON',
        'patternType': 'JSON',
        'fieldMap': field_map,
        'responseTimeUnit': 'ms',
        'timezone': 'fromLog'
    }


def _load_grok_format_from_config(config):
    """Load GROK/custom format from config.yaml"""
    grok_config = config.get('grok', {})

    if not grok_config or 'log_pattern' not in grok_config:
        logger.warning("GROK config incomplete, using default")
        return {
            'logPattern': r'.*',
            'patternType': 'GROK',
            'fieldMap': {},
            'responseTimeUnit': 'ms',
            'timezone': 'fromLog'
        }

    pattern = grok_config.get('log_pattern')
    columns = grok_config.get('columns', [])
    field_map = grok_config.get('field_map', {})

    if not field_map:
        field_map = _build_field_map_from_columns(columns, {})

    return {
        'logPattern': pattern,
        'patternType': 'GROK',
        'fieldMap': field_map,
        'columns': columns,
        'responseTimeUnit': 'ms',
        'timezone': 'fromLog'
    }


def _build_field_map_from_columns(columns, explicit_field_map=None):
    """Build field map from column names with smart matching

    Args:
        columns: List of column names from config
        explicit_field_map: Explicit field mapping from config (takes priority)

    Returns:
        dict: Field mapping for MCP tools
    """
    if explicit_field_map:
        return explicit_field_map

    field_map = {}

    # Common field name variations
    time_variants = ['time', 'timestamp', '@timestamp', 'datetime', 'request_time']
    method_variants = ['method', 'request_method', 'request_verb', 'verb', 'http_method']
    url_variants = ['url', 'request_url', 'uri', 'request_uri', 'path']
    status_variants = ['status', 'status_code', 'elb_status_code', 'http_status', 'response_code']
    response_time_variants = ['response_time', 'request_time', 'response_time_us',
                              'target_processing_time', 'request_processing_time', 'duration', 'elapsed']
    client_ip_variants = ['client_ip', 'remote_addr', 'client', 'ip', 'clientip', 'remote_ip']

    # Find matches
    for col in columns:
        col_lower = col.lower()

        if not field_map.get('timestamp') and col_lower in time_variants:
            field_map['timestamp'] = col
        elif not field_map.get('method') and col_lower in method_variants:
            field_map['method'] = col
        elif not field_map.get('url') and col_lower in url_variants:
            field_map['url'] = col
        elif not field_map.get('status') and col_lower in status_variants:
            field_map['status'] = col
        elif not field_map.get('responseTime') and col_lower in response_time_variants:
            field_map['responseTime'] = col
        elif not field_map.get('clientIp') and col_lower in client_ip_variants:
            field_map['clientIp'] = col

    return field_map


def _generate_json_format(sample_lines):
    """Generate JSON format specification"""
    # Try to parse first valid JSON to get field names
    field_map = {}
    for line in sample_lines[:10]:
        try:
            obj = json.loads(line.strip())
            # Common field mappings
            field_map = {
                'timestamp': _find_field(obj, ['timestamp', 'time', '@timestamp', 'datetime']),
                'method': _find_field(obj, ['method', 'request_method', 'verb']),
                'url': _find_field(obj, ['url', 'uri', 'path', 'request_uri']),
                'status': _find_field(obj, ['status', 'status_code', 'response_status']),
                'responseTime': _find_field(obj, ['response_time', 'duration', 'elapsed']),
                'clientIp': _find_field(obj, ['client_ip', 'remote_addr', 'ip'])
            }
            break
        except:
            continue
    
    return {
        'logPattern': 'JSON',
        'patternType': 'JSON',
        'fieldMap': field_map,
        'responseTimeUnit': 'ms',
        'timezone': 'fromLog'
    }


def _generate_apache_format(sample_lines):
    """Generate Apache/Nginx format specification

    Apache Combined Log Format: %h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"
    Example: 116.33.12.98 - - [12/Dec/2021:03:13:02 +0900] "POST /path HTTP/1.1" 200 117 "http://..." "Mozilla/..."
    Also handles malformed requests: 10.118.5.174 - - [12/Dec/2021:03:13:43 +0900] "-" 408 - "-" "-"
    """
    # Apache Combined Log Format pattern with support for:
    # 1. Normal requests: "POST /path HTTP/1.1"
    # 2. Malformed requests: "-"
    # 3. Optional referer and user agent (without trailing quote)
    pattern = r'([^ ]*) ([^ ]*) ([^ ]*) \[([^\]]*)\] "([^"]*)" ([0-9]*) ([0-9\-]*)(?: "([^"]*)" "([^"]*)")?'

    return {
        'logPattern': pattern,
        'patternType': 'HTTPD',
        'columns': [
            'client_ip',
            'identity',
            'user',
            'time',
            'request',  # Full request line (will be split later)
            'status',
            'bytes_sent',
            'referer',
            'user_agent'
        ],
        'columnTypes': {
            'client_ip': 'str',
            'identity': 'str',
            'user': 'str',
            'time': 'datetime',
            'request': 'str',
            'status': 'int',
            'bytes_sent': 'int',
            'referer': 'str',
            'user_agent': 'str'
        },
        'fieldMap': {
            'timestamp': 'time',
            'method': 'request_method',
            'url': 'request_url',
            'status': 'status',
            'clientIp': 'client_ip'
        },
        'responseTimeUnit': 'ms',
        'timezone': 'fromLog'
    }


def _generate_grok_format(sample_lines):
    """Generate GROK format specification (fallback)"""
    return {
        'logPattern': r'.*',
        'patternType': 'GROK',
        'fieldMap': {},
        'responseTimeUnit': 'ms',
        'timezone': 'fromLog'
    }


def _find_field(obj, candidates):
    """Find field in JSON object by candidate names"""
    for key in candidates:
        if key in obj:
            return key
    return None


def _test_pattern(line, pattern, pattern_type):
    """Test if pattern matches the line"""
    if pattern_type == 'JSON':
        try:
            json.loads(line.strip())
            return True
        except:
            return False
    else:
        try:
            return re.match(pattern, line) is not None
        except:
            return False


# ============================================================================
# MCP Tool: parseAccessLog
# ============================================================================

def parseAccessLog(logLine, logPattern):
    """
    Parse a single access log line using specified pattern.
    For debugging and testing purposes.
    
    Args:
        logLine (str): Log line to parse
        logPattern (str): Log pattern (regex or 'JSON')
        
    Returns:
        dict: Parsed log entry
    """
    if logPattern == 'JSON':
        try:
            return json.loads(logLine.strip())
        except Exception as e:
            return {'error': str(e)}
    else:
        try:
            match = re.match(logPattern, logLine.strip())
            if match:
                return {'groups': match.groups(), 'matched': True}
            else:
                return {'matched': False}
        except Exception as e:
            return {'error': str(e)}


# ============================================================================
# Helper Functions for File Parsing
# ============================================================================

def _parse_lines_chunk(lines_chunk, pattern, pattern_type, format_info):
    """
    Parse a chunk of lines in parallel worker process.

    Args:
        lines_chunk: List of (line_num, line) tuples
        pattern: Regex pattern
        pattern_type: Pattern type (ALB, JSON, HTTPD, GROK)
        format_info: Format information dict

    Returns:
        Tuple of (parsed_data, failed_lines)
    """
    parsed_data = []
    failed_lines = []

    for line_num, line in lines_chunk:
        original_line = line.rstrip('\n\r')
        parsed = _parse_line(line, pattern, pattern_type, format_info)
        if parsed:
            parsed_data.append(parsed)
        else:
            if original_line.strip():
                failed_lines.append((line_num, original_line))

    return parsed_data, failed_lines


def _read_lines_from_file(input_file, max_lines=None):
    """
    Read lines from file (gzip or plain text) with line numbers.

    Args:
        input_file: Path to input file
        max_lines: Maximum number of lines to read (None for all)

    Returns:
        List of (line_num, line) tuples
    """
    lines = []

    try:
        # Try gzip first
        try:
            with gzip.open(input_file, 'rt', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    lines.append((line_num, line))
                    if max_lines and line_num >= max_lines:
                        break
        except (gzip.BadGzipFile, OSError):
            # Try plain text
            with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    lines.append((line_num, line))
                    if max_lines and line_num >= max_lines:
                        break
    except Exception as e:
        logger.error(f"Error reading file {input_file}: {e}")
        raise

    return lines


def parse_log_file_with_format(input_file, log_format_file, use_multiprocessing=None, num_workers=None, chunk_size=None, columns_to_load=None):
    """
    Parse log file using a log format file (from recommendAccessLogFormat).
    Supports both original log files and JSON Lines files (filtered results).

    Args:
        input_file (str): Input log file path
        log_format_file (str): Log format JSON file path
        use_multiprocessing (bool, optional): Enable multiprocessing for large files.
            If None, reads from config.yaml (default: None, will use config or True)
        num_workers (int, optional): Number of worker processes.
            If None, reads from config.yaml or auto-detects based on CPU cores
        chunk_size (int, optional): Number of lines per chunk for parallel processing.
            If None, reads from config.yaml (default: None, will use config or 10000)
        columns_to_load (list, optional): List of column names to load. If None, loads all columns.
            This significantly reduces memory usage for large files (80-90% reduction).
            Example: ['time', 'request_url'] will only load these 2 columns instead of all 34.

    Returns:
        pandas.DataFrame: Parsed log data (with selected columns if columns_to_load specified)
    """
    # Load multiprocessing configuration from config.yaml if not explicitly provided
    from core.utils import MultiprocessingConfig
    mp_config = MultiprocessingConfig.get_config()

    # Apply config values if parameters are None
    if use_multiprocessing is None:
        use_multiprocessing = mp_config['enabled']
    if num_workers is None:
        num_workers = mp_config['num_workers']  # Can still be None (auto-detect)
    if chunk_size is None:
        chunk_size = mp_config['chunk_size']

    logger.info(f"parse_log_file_with_format: use_multiprocessing={use_multiprocessing}, "
               f"num_workers={num_workers}, chunk_size={chunk_size}")

    # Check if input file is JSON Lines (filtered result)
    # Filtered files from filterByCondition are saved as JSON Lines
    # Check by filename pattern first (filtered_*.log) or try to detect JSON Lines format
    input_path = Path(input_file)
    is_filtered_file = 'filtered_' in input_path.name
    
    if is_filtered_file:
        # Try to read as JSON Lines (filtered files are JSON Lines)
        try:
            log_data = []
            # Try gzip first
            try:
                with gzip.open(input_file, 'rt', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            log_data.append(obj)
                        except json.JSONDecodeError:
                            # If first few lines fail to parse as JSON, probably not JSON Lines
                            if line_num <= 3:
                                raise ValueError("Not a JSON Lines file")
                            continue
                        if line_num % 10000 == 0:
                            logger.debug(f"Processed {line_num} lines...")
            except (gzip.BadGzipFile, OSError):
                # Try plain text JSON Lines
                with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            log_data.append(obj)
                        except json.JSONDecodeError:
                            # If first few lines fail to parse as JSON, probably not JSON Lines
                            if line_num <= 3:
                                raise ValueError("Not a JSON Lines file")
                            continue
                        if line_num % 10000 == 0:
                            logger.debug(f"Processed {line_num} lines...")
            
            # If we successfully parsed JSON Lines, return it
            if log_data:
                df = pd.DataFrame(log_data)
                logger.info(f"Total parsed entries (JSON Lines): {len(df)}")
                return df
        except (ValueError, Exception) as e:
            # If JSON Lines parsing fails, fall through to original log parsing
            if is_filtered_file:
                logger.warning(f"Failed to parse as JSON Lines, trying original log format: {e}")
            pass
    
    # Load log format for original log parsing
    with open(log_format_file, 'r', encoding='utf-8') as f:
        format_info = json.load(f)
    
    pattern = format_info['logPattern']
    pattern_type = format_info['patternType']
    field_map = format_info['fieldMap']
    
    # For ALB, if columns are missing, try to load from config.yaml
    if pattern_type == 'ALB' and 'columns' not in format_info:
        logger.warning("columns not found in logFormatFile, trying to load from config.yaml")
        try:
            # Try to find config.yaml and load columns
            config_paths = [
                Path(input_file).parent / 'config.yaml',
                Path(input_file).parent.parent / 'config.yaml',
                Path.cwd() / 'config.yaml',
                Path(__file__).parent / 'config.yaml'
            ]
            
            for config_path in config_paths:
                if config_path.exists():
                    try:
                        config = load_config_legacy(str(config_path))
                        if 'columns' in config:
                            format_info['columns'] = config['columns']
                            logger.info(f"Loaded columns from config.yaml: {config_path}")
                            break
                    except Exception as e:
                        continue
        except Exception as e:
            logger.warning(f"Failed to load columns from config.yaml: {e}")
    
    # Parse file as original log format
    log_data = []
    failed_lines = []  # Collect failed lines for output

    # Determine if we should use multiprocessing
    # Get total line count estimate for decision
    try:
        lines_with_nums = _read_lines_from_file(input_file)
        total_lines = len(lines_with_nums)
        logger.info(f"Read {total_lines} lines from {input_file}")

        # Use multiprocessing for large files (>= 10000 lines)
        if use_multiprocessing and total_lines >= chunk_size:
            # Determine number of workers
            if num_workers is None:
                num_workers = min(cpu_count(), max(1, total_lines // chunk_size))

            logger.info(f"Using multiprocessing with {num_workers} workers, chunk_size={chunk_size}")

            # Split lines into chunks
            chunks = [lines_with_nums[i:i + chunk_size] for i in range(0, len(lines_with_nums), chunk_size)]

            # Create worker function with fixed parameters
            worker_fn = partial(_parse_lines_chunk, pattern=pattern, pattern_type=pattern_type, format_info=format_info)

            # Process chunks in parallel
            with Pool(processes=num_workers) as pool:
                results = pool.map(worker_fn, chunks)

            # Combine results
            for parsed_chunk, failed_chunk in results:
                log_data.extend(parsed_chunk)
                failed_lines.extend(failed_chunk)

            logger.info(f"Parallel parsing completed: {len(log_data)} entries parsed, {len(failed_lines)} failed")

        else:
            # Sequential processing for small files
            logger.info("Using sequential processing (file too small or multiprocessing disabled)")

            for line_num, line in lines_with_nums:
                original_line = line.rstrip('\n\r')
                parsed = _parse_line(line, pattern, pattern_type, format_info)
                if parsed:
                    log_data.append(parsed)
                else:
                    if original_line.strip():
                        failed_lines.append((line_num, original_line))
                if line_num % 10000 == 0:
                    logger.debug(f"Processed {line_num} lines...")

    except Exception as e:
        logger.error(f"Error parsing file {input_file}: {e}")
        raise

    # Output failed lines (파싱에 실패한 라인은 화면에 출력함)
    if failed_lines:
        logger.warning(f"파싱에 실패한 라인 ({len(failed_lines)}건):")
        # Show first 10 failed lines
        for line_num, failed_line in failed_lines[:10]:
            logger.warning(f"Line {line_num}: {failed_line[:100]}...")  # Truncate long lines
        if len(failed_lines) > 10:
            logger.warning(f"... and {len(failed_lines) - 10} more failed lines")
    
    if not log_data:
        logger.warning("No valid log entries parsed.")
        return pd.DataFrame()

    # OPTIMIZED: Filter columns BEFORE DataFrame creation to reduce memory usage
    if columns_to_load:
        # Get sample entry to check available columns
        sample_entry = log_data[0] if log_data else {}
        all_columns = list(sample_entry.keys())
        available_cols = [col for col in columns_to_load if col in all_columns]
        missing_cols = [col for col in columns_to_load if col not in all_columns]

        # For HTTPD logs: if derived columns (request_url, request_method, request_proto) are requested,
        # we need to include the source 'request' column for splitting
        if pattern_type == 'HTTPD' and 'request' in all_columns:
            httpd_derived_cols = ['request_url', 'request_method', 'request_proto']
            if any(col in columns_to_load for col in httpd_derived_cols):
                if 'request' not in available_cols:
                    available_cols.append('request')
                    logger.info("Added 'request' column for HTTPD request splitting")
                # Remove derived columns from missing_cols since they'll be generated
                missing_cols = [col for col in missing_cols if col not in httpd_derived_cols]

        if missing_cols:
            logger.warning(f"Requested columns not found in parsed data: {missing_cols}")

        if available_cols:
            # Filter each entry to only include requested columns
            # This happens BEFORE DataFrame creation, reducing memory by 80-90%
            filtered_log_data = []
            for entry in log_data:
                filtered_entry = {col: entry.get(col) for col in available_cols}
                filtered_log_data.append(filtered_entry)

            logger.info(f"Column filtering: Loading {len(available_cols)}/{len(columns_to_load)} requested columns (from {len(all_columns)} total)")
            logger.info(f"Pre-filtered {len(log_data)} entries before DataFrame creation (memory optimized)")
            log_data = filtered_log_data
        else:
            logger.warning("No requested columns found in parsed data, loading all columns")

    # Create DataFrame from pre-filtered data (much smaller memory footprint)
    df = pd.DataFrame(log_data)

    logger.info(f"Total parsed entries: {len(df)}")
    if failed_lines:
        logger.info(f"Total failed lines: {len(failed_lines)}")

    # For HTTPD logs, split 'request' field into method, url, protocol
    if pattern_type == 'HTTPD' and 'request' in df.columns and not df.empty:
        logger.info("Splitting HTTPD request field into method, url, protocol")

        def split_request(request_str):
            """Split request string like 'POST /path HTTP/1.1' into components"""
            if pd.isna(request_str) or request_str in ('', '-', ' '):
                return None, None, None

            parts = request_str.strip().split(' ', 2)
            if len(parts) == 3:
                return parts[0], parts[1], parts[2]
            elif len(parts) == 2:
                return parts[0], parts[1], None
            elif len(parts) == 1:
                return None, parts[0], None
            else:
                return None, None, None

        # Split request field
        split_results = df['request'].apply(split_request)
        df['request_method'] = split_results.apply(lambda x: x[0] if x else None)
        df['request_url'] = split_results.apply(lambda x: x[1] if x else None)
        df['request_proto'] = split_results.apply(lambda x: x[2] if x else None)

        logger.info(f"Created columns: request_method, request_url, request_proto")

        # Update fieldMap for compatibility
        if 'fieldMap' in format_info:
            format_info['fieldMap']['url'] = 'request_url'
            format_info['fieldMap']['method'] = 'request_method'

        # If columns_to_load was specified and doesn't include 'request', remove it to save memory
        if columns_to_load and 'request' not in columns_to_load:
            df = df.drop(columns=['request'])
            logger.info("Removed 'request' column (not in requested columns)")

        # Filter to only requested columns if specified
        if columns_to_load:
            # Keep only columns that were requested or generated from requested columns
            final_cols = [col for col in df.columns if col in columns_to_load or col in ['request_method', 'request_url', 'request_proto']]
            df = df[final_cols]
            logger.info(f"Final columns after filtering: {final_cols}")

    # Apply column type conversions from config
    if not df.empty and 'columnTypes' in format_info:
        column_types = format_info['columnTypes']
        logger.info(f"Applying column type conversions from format info")

        for col, dtype in column_types.items():
            if col in df.columns:
                try:
                    if dtype == 'datetime' or dtype == 'timestamp':
                        # For Apache/HTTPD logs: parse time format like "12/Dec/2021:03:13:02 +0900"
                        if pattern_type == 'HTTPD':
                            # Apache Common/Combined Log Format time
                            df[col] = pd.to_datetime(df[col], format='%d/%b/%Y:%H:%M:%S %z', errors='coerce')
                        else:
                            # ALB or other formats
                            df[col] = pd.to_datetime(df[col], errors='coerce')
                        logger.debug(f"Converted '{col}' to datetime")
                    elif dtype in ('int', 'integer', 'int64'):
                        numeric_series = pd.to_numeric(df[col], errors='coerce')
                        if isinstance(numeric_series, pd.Series):
                            df[col] = numeric_series.astype('Int64')
                        else:
                            df[col] = numeric_series
                        logger.debug(f"Converted '{col}' to int")
                    elif dtype in ('float', 'float64', 'double'):
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        logger.debug(f"Converted '{col}' to float")
                    elif dtype in ('str', 'string', 'object'):
                        df[col] = df[col].astype(str)
                        logger.debug(f"Converted '{col}' to string")
                except Exception as e:
                    logger.warning(f"Failed to convert column '{col}' to {dtype}: {e}")

        logger.info(f"Column type conversions completed")

    # Debug: For ALB, show column information
    if pattern_type == 'ALB' and not df.empty:
        logger.debug(f"ALB DataFrame columns: {list(df.columns)[:10]}...")  # Show first 10 columns
        if 'columns' in format_info:
            logger.debug(f"Expected columns from config.yaml: {len(format_info['columns'])} columns")
            logger.debug(f"Columns match: {set(df.columns) == set(format_info['columns'])}")
        else:
            logger.warning("No columns in format_info - columns may not be loaded from config.yaml")

    return df


def _parse_line(line, pattern, pattern_type, format_info=None):
    """Parse a single line based on pattern type

    Args:
        line: Log line to parse
        pattern: Regex pattern
        pattern_type: Pattern type (ALB, JSON, HTTPD, GROK)
        format_info: Format information dict (may contain 'columns')
    """
    line = line.strip()
    if not line:
        return None

    if pattern_type == 'JSON':
        try:
            return json.loads(line)
        except:
            return None
    else:
        try:
            match = re.match(pattern, line)
            if match:
                named_groups = match.groupdict()
                if named_groups:
                    return {
                        key: (None if value in ('', '-', ' ', None) else value)
                        for key, value in named_groups.items()
                    }

                groups = match.groups()

                # Use columns from format_info if available (works for ALB, HTTPD, GROK, Nginx)
                columns = format_info.get('columns', []) if format_info else []

                if columns:
                    # Map groups to column names from config
                    result = {}
                    for i, col in enumerate(columns):
                        if i < len(groups):
                            value = groups[i]
                            # Handle empty strings and special values
                            if value == '' or value == '-' or value == ' ' or value is None:
                                result[col] = None
                            else:
                                result[col] = value
                        else:
                            # If not enough groups, set remaining columns to None
                            result[col] = None

                    # Validate for ALB (strict validation)
                    if pattern_type == 'ALB':
                        # For ALB, validate that we have at least some key fields
                        if not any(result.get(col) for col in ['time', 'request_url', 'request_verb'] if col in result):
                            return None

                    # Validate for HTTPD/Nginx (less strict - just check for time or status)
                    elif pattern_type == 'HTTPD':
                        # For HTTPD, validate that we have at least time or status
                        time_exists = any(result.get(col) for col in ['time', 'timestamp'] if col in result)
                        status_exists = any(result.get(col) for col in ['status', 'status_code'] if col in result)
                        if not (time_exists or status_exists):
                            return None

                    return result
                else:
                    # No columns defined - use fallback mapping
                    if pattern_type == 'ALB':
                        # Fallback to default ALB mapping
                        min_fields = min(len(groups), 17)
                        result = {}
                        field_names = [
                            'type', 'time', 'elb', 'client_ip', 'client_port',
                            'target_ip', 'target_port', 'request_processing_time',
                            'target_processing_time', 'response_processing_time',
                            'elb_status_code', 'target_status_code',
                            'received_bytes', 'sent_bytes',
                            'request_verb', 'request_url', 'request_proto'
                        ]
                        for i in range(min_fields):
                            if i < len(field_names):
                                value = groups[i]
                                if value == '' or value == '-' or value == ' ':
                                    result[field_names[i]] = None
                                else:
                                    result[field_names[i]] = value
                        if len(groups) > min_fields:
                            result['_extra_groups'] = list(groups[min_fields:])
                        return result
                    elif pattern_type == 'HTTPD':
                        # Fallback for HTTPD (Apache Combined Log Format)
                        if len(groups) >= 10:
                            return {
                                'client_ip': groups[0] if groups[0] not in ('', '-') else None,
                                'user': groups[1] if groups[1] not in ('', '-') else None,
                                'time': groups[2] if groups[2] not in ('', '-') else None,
                                'request_method': groups[3] if groups[3] not in ('', '-') else None,
                                'request_url': groups[4] if groups[4] not in ('', '-') else None,
                                'request_proto': groups[5] if groups[5] not in ('', '-') else None,
                                'status': groups[6] if groups[6] not in ('', '-') else None,
                                'bytes_sent': groups[7] if groups[7] not in ('', '-') else None,
                                'referer': groups[8] if len(groups) > 8 and groups[8] not in ('', '-') else None,
                                'user_agent': groups[9] if len(groups) > 9 and groups[9] not in ('', '-') else None
                            }

                    # Generic fallback for other types
                    return {'raw_groups': groups}
            return None
        except Exception as e:
            return None


# ============================================================================
# Legacy Functions (for backward compatibility)
# ============================================================================

def load_config_legacy(config_path):
    """Load configuration from YAML file"""
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)


def parse_log_file(input_path, log_pattern, columns):
    """
    Parse log file using pattern and column names (legacy function for main.py).
    
    Args:
        input_path (str): Input log file path (can be glob pattern)
        log_pattern (str): Regex pattern for parsing
        columns (list): Column names
        
    Returns:
        pandas.DataFrame: Parsed log data
    """
    import glob
    
    log_data = []
    
    # Handle glob patterns
    if isinstance(input_path, str):
        file_paths = glob.glob(input_path) if ('*' in input_path or '?' in input_path) else [input_path]
    else:
        file_paths = input_path if isinstance(input_path, list) else [input_path]
    
    for file_path in file_paths:
        try:
            # Try gzip first
            try:
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        match = re.match(log_pattern, line.strip())
                        if match:
                            log_data.append(dict(zip(columns, match.groups())))
                        if line_num % 10000 == 0:
                            logger.debug(f"Processed {line_num} lines from {file_path}...")
            except:
                # Try plain text
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        match = re.match(log_pattern, line.strip())
                        if match:
                            log_data.append(dict(zip(columns, match.groups())))
                        if line_num % 10000 == 0:
                            logger.debug(f"Processed {line_num} lines from {file_path}...")
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
    
    if not log_data:
        logger.warning("No valid log entries parsed.")
        return pd.DataFrame()
    
    df = pd.DataFrame(log_data)
    logger.info(f"Total parsed entries: {len(df)}")
    
    return df


def apply_column_types(log_df, column_types):
    """
    Apply data types to DataFrame columns.
    
    Args:
        log_df (pandas.DataFrame): Input DataFrame
        column_types (dict): Mapping of column names to types
        
    Returns:
        pandas.DataFrame: DataFrame with applied types
    """
    for col, dtype in column_types.items():
        if col in log_df.columns:
            if dtype == 'datetime':
                log_df[col] = pd.to_datetime(log_df[col], errors='coerce')
            elif dtype == 'int':
                numeric_series = pd.to_numeric(log_df[col], errors='coerce')
                if isinstance(numeric_series, pd.Series):
                    log_df[col] = numeric_series.astype('Int64')
                else:
                    log_df[col] = numeric_series
            elif dtype == 'float':
                log_df[col] = pd.to_numeric(log_df[col], errors='coerce')
            elif dtype == 'str':
                log_df[col] = log_df[col].astype(str)
    
    return log_df


def save_as_pickle(log_df, pickle_path):
    """
    Save DataFrame to pickle file.
    
    Args:
        log_df (pandas.DataFrame): DataFrame to save
        pickle_path (str): Output pickle file path
    """
    import pickle
    with open(pickle_path, 'wb') as f:
        pickle.dump(log_df, f)
    print(f"Data saved to {pickle_path}")


def load_from_pickle(pickle_path):
    """
    Load DataFrame from pickle file.
    
    Args:
        pickle_path (str): Pickle file path
        
    Returns:
        pandas.DataFrame: Loaded DataFrame
    """
    import pickle
    with open(pickle_path, 'rb') as f:
        return pickle.load(f)


def save_to_sqlite(log_df, sqlite_path, table_name):
    """
    Save DataFrame to SQLite database.
    
    Args:
        log_df (pandas.DataFrame): DataFrame to save
        sqlite_path (str): SQLite database file path
        table_name (str): Table name
    """
    import sqlite3
    conn = sqlite3.connect(sqlite_path)
    log_df.to_sql(table_name, conn, if_exists='replace', index=False)
    conn.close()
    print(f"Data saved to SQLite database: {sqlite_path} (table: {table_name})")


def load_from_sqlite(sqlite_path, table_name):
    """
    Load DataFrame from SQLite database.
    
    Args:
        sqlite_path (str): SQLite database file path
        table_name (str): Table name
        
    Returns:
        pandas.DataFrame: Loaded DataFrame
    """
    import sqlite3
    conn = sqlite3.connect(sqlite_path)
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df


# Main function for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        print(f"Analyzing log format for: {input_file}")
        result = recommendAccessLogFormat(input_file)
        print("\n" + "="*60)
        print("Log Format Recommendation Result:")
        print("="*60)
        print(f"Pattern Type: {result['patternType']}")
        print(f"Success Rate: {result['successRate']:.1%}")
        print(f"Confidence: {result['confidence']:.1%}")
        print(f"Response Time Unit: {result['responseTimeUnit']}")
        print(f"Timezone: {result['timezone']}")
        print(f"Log Format File: {result['logFormatFile']}")
        print("\nField Mapping:")
        for key, value in result['fieldMap'].items():
            print(f"  {key}: {value}")
    else:
        print("Usage: python data_parser.py <log_file_path>")
        print("Example: python data_parser.py access.log")
