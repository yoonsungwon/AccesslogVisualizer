# AI Agent Guide

This file provides quick guidance to AI coding assistants (Claude Code, Gemini, etc.) when working with code in this repository.

## Project Overview

**Access Log Analyzer** - MCP(Model Context Protocol) 기반 대용량 웹 서버 접근 로그 분석 도구

The tool provides:
- Automatic log format detection (ALB, Apache/Nginx, JSON, GROK)
- Filtering and pattern extraction
- Statistical analysis with multiprocessing
- Interactive HTML visualizations with Plotly

## Quick Links

📚 **Detailed Documentation:**
- **[Architecture](docs/ARCHITECTURE.md)** - System design, modules, and patterns
- **[Configuration](docs/CONFIGURATION.md)** - config.yaml settings and log formats
- **[Usage Examples](docs/USAGE_EXAMPLES.md)** - Python API, CLI, and common workflows
- **[API Reference](docs/API_REFERENCE.md)** - Function signatures and parameters
- **[Development](docs/DEVELOPMENT.md)** - Setup, testing, and contributing
- **[Changelog](docs/CHANGELOG.md)** - Recent changes and improvements

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Interactive mode
python main.py

# Analyze specific file
python main.py access.log.gz

# Run tests
pytest tests/ -v
```

See [Development Guide](docs/DEVELOPMENT.md) for detailed setup and testing instructions.

## Architecture Overview

**MCP Tool-Based Architecture:**
- Each operation is a standalone MCP tool
- Tools chain together (output → input)
- Accessible via MCP server or Python API

**Project Structure:**
```
AccesslogAnalyzer/
├── core/                   # Infrastructure (exceptions, config, logging, utils)
├── data_parser.py         # Log format detection and parsing
├── data_processor.py      # Filtering, patterns, statistics
├── data_visualizer.py     # Interactive visualizations
├── main.py               # CLI interface
├── mcp_server.py         # MCP server
├── config.yaml           # Configuration
└── docs/                 # Documentation
```

See [Architecture Documentation](docs/ARCHITECTURE.md) for detailed design and patterns.

## Core Modules

### data_parser.py
- `recommendAccessLogFormat()` - Auto-detect log format
- `parse_log_file_with_format()` - Parse logs with multiprocessing and memory optimization

### data_processor.py
- `filterByCondition()` - Filter by time, status, response time, IP, URLs, patterns
- `extractUriPatterns()` - Extract URL patterns with generalization
- `calculateStats()` - Compute statistics with parallel processing

### data_visualizer.py
- `generateXlog()` - Response time scatter plot
- `generateRequestPerURI()` - Request count time-series
- `generateRequestPerTarget()` - Request count per backend
- `generateRequestPerClientIP()` - Request count per client
- `generateProcessingTimePerURI()` - Processing time analysis
- `generateSentBytesPerURI()` / `generateReceivedBytesPerURI()` - Byte transfer analysis
- `generateMultiMetricDashboard()` - Comprehensive dashboard

See [API Reference](docs/API_REFERENCE.md) for detailed function signatures.

## Key Features

### Multi-Format Log Support
- **ALB** - AWS Application Load Balancer logs (34+ fields)
- **HTTPD** - Apache/Nginx Combined Log Format
- **NGINX** - Nginx access logs with custom format
- **JSON** - JSON-formatted logs (one JSON object per line)
- **GROK** - Custom log formats using regex patterns

See [Configuration Guide](docs/CONFIGURATION.md) for format-specific setup.

### Memory Optimization
- Column filtering: Load only required columns (80-90% reduction)
- Dtype optimization: Downcast numeric types (50-70% reduction)
- Explicit memory cleanup: Use `gc.collect()` after large operations
- Combined effect: 90%+ memory footprint reduction

### Multiprocessing Support
- Log parsing: ~3-4x faster on multi-core systems
- Statistics: ~2-3x faster for large datasets
- Auto-detection of optimal worker count
- Configurable via config.yaml

See [Configuration Guide](docs/CONFIGURATION.md#multiprocessing-configuration) for settings.

### Pattern File Management
- Single unified patterns file per log file: `patterns_{log_name}.json`
- Automatic merging of pattern rules
- Preservation of manually added rules
- Smart ID/UUID replacement and file extension categorization

## Common Workflows

### Basic Analysis
```python
# 1. Detect format
format_result = recommendAccessLogFormat("access.log.gz")

# 2. Extract patterns
patterns_result = extractUriPatterns(
    "access.log.gz",
    format_result['logFormatFile'],
    'patterns',
    'maxPatterns=20'
)

# 3. Generate visualization
viz_result = generateRequestPerURI(
    "access.log.gz",
    format_result['logFormatFile'],
    'html',
    topN=20,
    interval='10s'
)
```

### Filter and Analyze
```python
# Filter by time range
filter_result = filterByCondition(
    "access.log.gz",
    "logformat_access.json",
    "time",
    "startTime=2024-08-08T09:00:00;endTime=2024-08-08T10:00:00"
)

# Analyze filtered data
stats_result = calculateStats(
    filter_result['filePath'],
    "logformat_access.json",
    "statsType=url"
)
```

See [Usage Examples](docs/USAGE_EXAMPLES.md) for more examples.

## Utility Classes

### FieldMapper - Smart Field Mapping
```python
from core.utils import FieldMapper

# Find field with fallback alternatives
time_field = FieldMapper.find_field(df, 'time', format_info)

# Map all common fields
field_map = FieldMapper.map_fields(df, format_info)

# Validate required fields
FieldMapper.validate_required_fields(df, format_info, ['time', 'url'])
```

### ParamParser - Type-Safe Parameter Parsing
```python
from core.utils import ParamParser

# Parse parameters
params = "startTime=2024-01-01;topN=20;enabled=true"
top_n = ParamParser.get_int(params, 'topN', default=10)
enabled = ParamParser.get_bool(params, 'enabled')
```

### MultiprocessingConfig - Multiprocessing Settings
```python
from core.utils import MultiprocessingConfig

# Get optimal workers
workers = MultiprocessingConfig.get_optimal_workers(data_size=100000)

# Check if multiprocessing should be used
should_use = MultiprocessingConfig.should_use_multiprocessing(data_size=50000)
```

See [API Reference](docs/API_REFERENCE.md#coreutilsmodule) for complete API.

## Error Handling

Use custom exceptions from `core.exceptions`:

```python
from core.exceptions import (
    FileNotFoundError,
    ValidationError,
    ParseError,
    InvalidFormatError
)

# Validate file existence
if not os.path.exists(file_path):
    raise FileNotFoundError(file_path)

# Validate parameters
if value not in allowed_values:
    raise ValidationError('parameter_name', f"Invalid value: {value}")
```

## Logging

Use centralized logging system:

```python
from core.logging_config import get_logger

logger = get_logger(__name__)

logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning messages")
logger.error("Error messages")
```

See [Development Guide](docs/DEVELOPMENT.md#logging) for logging setup.

## File Naming Conventions

Output files follow strict naming patterns:
- `logformat_*.json` - Log format detection results
- `filtered_*.log` - Filtered log data (JSON Lines format)
- `patterns_{log_name}.json` - Unified patterns file per log
- `stats_*.json` - Statistical analysis results
- `xlog_*.html` - Response time scatter plots
- `requestcnt_*.html` - Request count visualizations
- `dashboard_*.html` - Multi-metric dashboards

## Adding a New MCP Tool

1. **Implement function** in appropriate module with type hints and docstring
2. **Add tool registration** in `mcp_server.py` `list_tools()`
3. **Add handler** in `mcp_server.py` `call_tool()`
4. **Add menu item** in `main.py` interactive menu
5. **Write tests** in `tests/test_*.py`
6. **Update documentation** in `docs/API_REFERENCE.md` and `docs/WORKFLOWS.md`

See [Development Guide](docs/DEVELOPMENT.md#adding-a-new-mcp-tool) for detailed steps.

## Important Implementation Details

### Log Format Detection Priority
1. Check for existing `logformat_*.json` in same directory
2. Sample 100 lines from input file
3. Auto-detect format type (ALB, JSON, Apache/Nginx, GROK)
4. Search for `config.yaml` in multiple locations
5. Generate and save `logformat_*.json` with absolute path

### Field Mapping
All tools use `fieldMap` from log format files to work with different log types. Smart matching is used for common field name variants:
- Time: `time`, `timestamp`, `@timestamp`, `datetime`
- URL: `url`, `request_url`, `uri`, `request_uri`, `path`
- Status: `status`, `status_code`, `elb_status_code`, `http_status`
- Client IP: `client_ip`, `remote_addr`, `client`, `ip`

### HTTPD Request Field Handling
For HTTPD logs, the single "request" field is automatically split into:
- `request_method` - HTTP method (GET, POST, etc.)
- `request_url` - URL path
- `request_proto` - Protocol version (HTTP/1.1, etc.)

### Column Type Conversion
Applies column type conversions based on `columnTypes` in format file:
- `datetime` - Converts to pandas datetime (HTTPD uses `%d/%b/%Y:%H:%M:%S %z`)
- `int/integer` - Converts to Int64 with error handling
- `float/double` - Converts to float with error handling

## Performance Tips

1. **Enable multiprocessing** for files >= 10,000 lines
2. **Use column filtering** to load only required columns
3. **Pre-load pattern rules** when processing many URLs
4. **Adjust chunk size** based on memory constraints
5. **Use config.yaml** for automatic settings

See [Configuration Guide](docs/CONFIGURATION.md#performance-tips) for optimization settings.

## Debugging

### Parse Failures
System outputs failed lines with line numbers and truncated content:
- First 10 failed lines during format recommendation
- All failed lines during actual parsing

Check for:
- Pattern/columns mismatch in `config.yaml`
- Unexpected log format variations
- Extra/missing fields

### Enable Debug Logging
```python
from core.logging_config import set_log_level, enable_file_logging

set_log_level('DEBUG')
enable_file_logging()
```

See [Development Guide](docs/DEVELOPMENT.md#debugging) for troubleshooting.

## Recent Changes

### Field Availability Check (2025-11-28)
- Pre-check field availability before parsing
- Show availability status in menu
- Support for field name variants across formats

### Multi-Format Log Support (2024-11-11)
- Support for ALB, HTTPD, NGINX, JSON, GROK formats
- Format-specific config sections
- Automatic field mapping

### Unified Pattern Files (2024-11-10)
- Single patterns file per log: `patterns_{log_name}.json`
- Automatic merging of pattern rules
- No more timestamped pattern files

See [Changelog](docs/CHANGELOG.md) for complete history.

## Environment

- Python 3.7+
- UTF-8 encoding for all files
- WSL2 or Unix-like environment (recommended)
- Working directory: `/mnt/c/bucket/AccesslogAnalyzer`

## License

[Project License Information]
