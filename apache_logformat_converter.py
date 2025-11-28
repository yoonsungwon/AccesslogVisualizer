#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apache LogFormat to Config Converter

Converts Apache LogFormat directives to config.yaml or logformat_*.json format.

Reference: https://httpd.apache.org/docs/2.4/en/mod/mod_log_config.html

Usage:
    python apache_logformat_converter.py 'LogFormat "%h %l %u %t \"%r\" %>s %b"'
    python apache_logformat_converter.py --format 'combined' --output config
"""

import re
import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


# Apache LogFormat directive mappings
# Format: directive -> (regex_pattern, column_name, column_type)
APACHE_DIRECTIVE_MAP = {
    # Client/Remote information
    '%h': (r'([^ ]+)', 'client_ip', 'str'),
    '%a': (r'([^ ]+)', 'client_ip', 'str'),
    '%l': (r'([^ ]+)', 'identity', 'str'),
    '%u': (r'([^ ]+)', 'user', 'str'),

    # Time
    '%t': (r'\[([^\]]+)\]', 'time', 'datetime'),

    # Request line (quotes are usually in LogFormat string, not in directive)
    '%r': (r'([^"]*)', 'request', 'str'),
    '%m': (r'([^ ]+)', 'request_method', 'str'),
    '%U': (r'([^ ]+)', 'request_url', 'str'),
    '%q': (r'([^ ]*)', 'query_string', 'str'),
    '%H': (r'([^ ]+)', 'request_proto', 'str'),

    # Status code
    '%s': (r'([-0-9]+)', 'status', 'int'),
    '%>s': (r'([-0-9]+)', 'status', 'int'),

    # Bytes sent
    '%b': (r'([-0-9]+)', 'bytes_sent', 'int'),
    '%B': (r'([0-9]+)', 'bytes_sent', 'int'),

    # Timing
    '%D': (r'([0-9]+)', 'response_time_us', 'int'),
    '%T': (r'([0-9.]+)', 'response_time_s', 'float'),

    # Server information
    '%v': (r'([^ ]+)', 'server_name', 'str'),
    '%V': (r'([^ ]+)', 'server_name', 'str'),
    '%p': (r'([0-9]+)', 'server_port', 'int'),
    '%A': (r'([^ ]+)', 'server_ip', 'str'),

    # Process information
    '%P': (r'([0-9]+)', 'process_id', 'int'),
    '%I': (r'([0-9]+)', 'bytes_received', 'int'),
    '%O': (r'([0-9]+)', 'bytes_sent_including_headers', 'int'),
}


# Common Apache LogFormat presets
APACHE_LOGFORMAT_PRESETS = {
    'common': '%h %l %u %t "%r" %>s %b',
    'combined': '%h %l %u %t "%r" %>s %b "%{Referer}i" "%{User-agent}i"',
    'combined_with_time': '%h %l %u %t "%r" %>s %b "%{Referer}i" "%{User-agent}i" %D',
    'vhost_combined': '%v:%p %h %l %u %t "%r" %>s %b "%{Referer}i" "%{User-agent}i"',
    'referer': '%{Referer}i -> %U',
    'agent': '%{User-agent}i',
}


def parse_apache_logformat(format_string: str) -> Tuple[str, List[str], Dict[str, str]]:
    """
    Parse Apache LogFormat string and generate regex pattern, columns, and column types.

    Args:
        format_string: Apache LogFormat string (e.g., '%h %l %u %t "%r" %>s %b')

    Returns:
        Tuple of (regex_pattern, columns, column_types)

    Examples:
        >>> parse_apache_logformat('%h %l %u %t "%r" %>s %b')
        ('([^ ]+) ([^ ]+) ([^ ]+) \\[([^\\]]+)\\] "([^"]*)" ([-0-9]+) ([-0-9]+)',
         ['client_ip', 'identity', 'user', 'time', 'request', 'status', 'bytes_sent'],
         {'time': 'datetime', 'status': 'int', 'bytes_sent': 'int'})
    """
    pattern_parts = []
    columns = []
    column_types = {}

    # Track position in format string
    i = 0
    while i < len(format_string):
        char = format_string[i]

        if char == '%':
            # Check for header/environment variable format: %{NAME}i, %{NAME}o, %{NAME}e
            if i + 1 < len(format_string) and format_string[i + 1] == '{':
                # Find closing }
                close_idx = format_string.find('}', i + 2)
                if close_idx != -1 and close_idx + 1 < len(format_string):
                    var_name = format_string[i + 2:close_idx]
                    var_type = format_string[close_idx + 1]

                    # Generate column name from variable name
                    column_name = var_name.lower().replace('-', '_')

                    if var_type == 'i':  # Request header
                        # Common headers (quotes are usually in LogFormat string)
                        if var_name.lower() in ('referer', 'referrer'):
                            pattern_parts.append(r'([^"]*)')
                            columns.append('referer')
                            column_types['referer'] = 'str'
                        elif var_name.lower() in ('user-agent', 'user_agent'):
                            pattern_parts.append(r'([^"]*)')
                            columns.append('user_agent')
                            column_types['user_agent'] = 'str'
                        else:
                            pattern_parts.append(r'([^"]*)')
                            columns.append(column_name)
                            column_types[column_name] = 'str'
                    elif var_type == 'o':  # Response header
                        pattern_parts.append(r'([^"]*)')
                        columns.append(f'resp_{column_name}')
                        column_types[f'resp_{column_name}'] = 'str'
                    elif var_type == 'e':  # Environment variable
                        pattern_parts.append(r'([^ ]+)')
                        columns.append(f'env_{column_name}')
                        column_types[f'env_{column_name}'] = 'str'

                    i = close_idx + 2
                    continue

            # Check for status code with condition: %>s, %<s, etc.
            elif i + 2 < len(format_string) and format_string[i + 1] in ('>', '<', '!'):
                directive = '%' + format_string[i + 1] + format_string[i + 2]
                if directive in APACHE_DIRECTIVE_MAP:
                    regex, col_name, col_type = APACHE_DIRECTIVE_MAP[directive]
                    pattern_parts.append(regex)
                    columns.append(col_name)
                    if col_type != 'str':
                        column_types[col_name] = col_type
                    i += 3
                    continue

            # Standard directive (e.g., %h, %t, %r)
            # Try to match the longest directive first
            matched = False
            for length in (3, 2):  # Try %xx then %x
                if i + length <= len(format_string):
                    directive = format_string[i:i + length]
                    if directive in APACHE_DIRECTIVE_MAP:
                        regex, col_name, col_type = APACHE_DIRECTIVE_MAP[directive]
                        pattern_parts.append(regex)
                        columns.append(col_name)
                        if col_type != 'str':
                            column_types[col_name] = col_type
                        i += length
                        matched = True
                        break

            if matched:
                continue

            # Unknown directive, skip it
            logger.warning(f"Unknown Apache directive at position {i}: {format_string[i:i+5]}")
            i += 1

        elif char == '"':
            # Literal quote in format
            pattern_parts.append(r'"')
            i += 1
        elif char == ' ':
            # Space separator
            pattern_parts.append(r' ')
            i += 1
        elif char == '[':
            # Literal bracket (for time format)
            pattern_parts.append(r'\[')
            i += 1
        elif char == ']':
            pattern_parts.append(r'\]')
            i += 1
        else:
            # Other literal characters
            pattern_parts.append(re.escape(char))
            i += 1

    regex_pattern = ''.join(pattern_parts)

    return regex_pattern, columns, column_types


def generate_config_yaml(format_string: str, output_path: Optional[str] = None,
                        format_name: str = 'httpd') -> Dict:
    """
    Generate config.yaml content from Apache LogFormat string.

    Args:
        format_string: Apache LogFormat string
        output_path: Optional output file path. If None, returns dict only.
        format_name: Format name (default: 'httpd')

    Returns:
        Dictionary with config.yaml structure
    """
    regex_pattern, columns, column_types = parse_apache_logformat(format_string)

    config = {
        'log_format_type': 'HTTPD',
        format_name: {
            'input_path': 'access.log',
            'log_pattern': regex_pattern,
            'columns': columns,
            'column_types': column_types,
            'field_map': {
                'timestamp': 'time',
                'clientIp': 'client_ip',
                'status': 'status',
            }
        }
    }

    # Add method/url mapping if request field exists
    if 'request' in columns:
        config[format_name]['field_map']['method'] = 'request_method'
        config[format_name]['field_map']['url'] = 'request_url'
    elif 'request_url' in columns:
        config[format_name]['field_map']['url'] = 'request_url'

    if 'request_method' in columns:
        config[format_name]['field_map']['method'] = 'request_method'

    # Add response time mapping
    if 'response_time_us' in columns:
        config[format_name]['field_map']['responseTime'] = 'response_time_us'
    elif 'response_time_s' in columns:
        config[format_name]['field_map']['responseTime'] = 'response_time_s'

    # Write to file if path provided
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        logger.info(f"Config file written to: {output_path}")

    return config


def generate_logformat_json(format_string: str, output_path: Optional[str] = None) -> Dict:
    """
    Generate logformat_*.json content from Apache LogFormat string.

    Args:
        format_string: Apache LogFormat string
        output_path: Optional output file path. If None, uses timestamp.

    Returns:
        Dictionary with logformat_*.json structure
    """
    regex_pattern, columns, column_types = parse_apache_logformat(format_string)

    format_info = {
        'logFormatFile': output_path or f"logformat_{datetime.now().strftime('%y%m%d_%H%M%S')}.json",
        'logPattern': regex_pattern,
        'patternType': 'HTTPD',
        'columns': columns,
        'columnTypes': column_types,
        'fieldMap': {
            'timestamp': 'time',
            'clientIp': 'client_ip',
            'status': 'status',
        },
        'responseTimeUnit': 'microseconds' if 'response_time_us' in columns else 'seconds',
        'timezone': 'fromLog'
    }

    # Add method/url mapping
    if 'request' in columns:
        format_info['fieldMap']['method'] = 'request_method'
        format_info['fieldMap']['url'] = 'request_url'
    elif 'request_url' in columns:
        format_info['fieldMap']['url'] = 'request_url'

    if 'request_method' in columns:
        format_info['fieldMap']['method'] = 'request_method'

    # Add response time mapping
    if 'response_time_us' in columns:
        format_info['fieldMap']['responseTime'] = 'response_time_us'
    elif 'response_time_s' in columns:
        format_info['fieldMap']['responseTime'] = 'response_time_s'

    # Write to file
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(format_info, f, indent=2, ensure_ascii=False)
        logger.info(f"Format file written to: {output_path}")

    return format_info


def main():
    """CLI interface for Apache LogFormat conversion."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert Apache LogFormat to config.yaml or logformat_*.json',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Convert common format
  python apache_logformat_converter.py --preset common --output config

  # Convert custom format to config.yaml
  python apache_logformat_converter.py '%%h %%l %%u %%t "%%r" %%>s %%b' --output config

  # Convert to logformat_*.json
  python apache_logformat_converter.py --preset combined --output json

  # Just show the parsed result
  python apache_logformat_converter.py --preset combined_with_time

Available presets:
  common              - Common Log Format
  combined            - Combined Log Format
  combined_with_time  - Combined with response time (%D)
  vhost_combined      - Virtual Host Combined
        '''
    )

    parser.add_argument('format_string', nargs='?',
                       help='Apache LogFormat string (e.g., "%%h %%l %%u %%t \\"%%r\\" %%>s %%b")')
    parser.add_argument('--preset', choices=list(APACHE_LOGFORMAT_PRESETS.keys()),
                       help='Use a preset format')
    parser.add_argument('--output', choices=['config', 'json', 'both'],
                       help='Output format (config=config.yaml, json=logformat_*.json, both=both)')
    parser.add_argument('--output-file',
                       help='Output file path (default: auto-generated)')
    parser.add_argument('--format-name', default='httpd',
                       help='Format name for config.yaml (default: httpd)')

    args = parser.parse_args()

    # Get format string
    if args.preset:
        format_string = APACHE_LOGFORMAT_PRESETS[args.preset]
        print(f"Using preset '{args.preset}': {format_string}\n")
    elif args.format_string:
        format_string = args.format_string
    else:
        parser.error("Either format_string or --preset must be provided")

    # Parse format
    regex_pattern, columns, column_types = parse_apache_logformat(format_string)

    print("="*70)
    print("Apache LogFormat Conversion Result")
    print("="*70)
    print(f"\nOriginal Format:\n  {format_string}\n")
    print(f"Regex Pattern:\n  {regex_pattern}\n")
    print(f"Columns ({len(columns)}):\n  {', '.join(columns)}\n")
    print(f"Column Types:\n  {json.dumps(column_types, indent=2)}\n")

    # Generate output files
    if args.output:
        if args.output in ('config', 'both'):
            output_file = args.output_file or 'config_generated.yaml'
            config = generate_config_yaml(format_string, output_file, args.format_name)
            print(f"✓ Config file generated: {output_file}")

        if args.output in ('json', 'both'):
            timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
            output_file = args.output_file or f'logformat_{timestamp}.json'
            format_info = generate_logformat_json(format_string, output_file)
            print(f"✓ Format file generated: {output_file}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    main()
