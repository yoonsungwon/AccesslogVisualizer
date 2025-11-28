# AI Agent Guide

This file provides guidance to AI coding assistants (Claude Code, Gemini, etc.) when working with code in this repository.

## Project Overview

Access Log Analyzer는 대용량 웹 서버 접근 로그를 분석하기 위한 MCP(Model Context Protocol) 기반 도구입니다. The tool provides automatic log format detection, filtering, URI pattern extraction, statistical analysis, and interactive HTML visualizations.

## Development Commands

### Setup and Installation
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
# Interactive menu mode
python main.py

# File-specific mode
python main.py access.log.gz

# Example pipeline execution
python main.py --example access.log.gz
```

### Testing Individual MCP Tools
```bash
# Test log format detection
python data_parser.py <log_file>

# Test MCP server
python mcp_server.py
```

## Architecture

### MCP Tool-Based Architecture

The codebase follows a **Model Context Protocol (MCP)** architecture, which means:
- Each major operation is implemented as a standalone MCP tool
- Tools take file inputs and produce file outputs (JSON, HTML, etc.)
- Tools are chainable - output files from one tool serve as input to another
- All tools can be invoked via the MCP server (`mcp_server.py`) or directly via Python API

### Project Structure

```
AccesslogAnalyzer/
├── core/                      # Core infrastructure (NEW)
│   ├── __init__.py
│   ├── exceptions.py          # Custom exception classes
│   ├── config.py             # ConfigManager for centralized config
│   └── logging_config.py     # Logging setup and configuration
├── data_parser.py            # Log format detection and parsing
├── data_processor.py         # Filtering, patterns, statistics
├── data_visualizer.py        # Interactive visualizations
├── main.py                   # CLI interface
├── mcp_server.py            # MCP server
└── config.yaml              # Optional configuration file
```

### Core Infrastructure

**core/exceptions.py** - Custom Exception Classes
- `LogAnalyzerError` - Base exception for all errors
- `FileNotFoundError` - File not found errors
- `InvalidFormatError` - Invalid log format errors
- `ParseError` - Log parsing errors with line context
- `ValidationError` - Input validation errors
- `ConfigurationError` - Configuration errors

**core/config.py** - Configuration Management
- `ConfigManager` - Singleton class for centralized config management
- Searches for `config.yaml` in multiple standard locations
- Caches configuration for performance
- Supports dot notation for nested keys (e.g., `config.get('server.port')`)

**core/logging_config.py** - Logging System
- Centralized logging setup with console and file handlers
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Detailed format with filename and line numbers for debugging
- All `print()` statements replaced with proper logging
- Daily rotating log files in `logs/` directory

**core/utils.py** - Utility Classes (NEW)
- `FieldMapper` - Smart field mapping with fallback alternatives
  - `find_field()` - Find fields across different log formats
  - `map_fields()` - Bulk field mapping with validation
  - `validate_required_fields()` - Validation with clear errors
- `ParamParser` - Type-safe parameter parsing
  - `parse()` - Parse "key=value;key2=value2" format
  - `get_bool/int/float/list()` - Type-safe value extraction
  - Built-in validation with custom exceptions
- `MultiprocessingConfig` - Multiprocessing configuration management (NEW)
  - `get_config()` - Load multiprocessing settings from config.yaml
  - `get_optimal_workers()` - Calculate optimal number of workers
  - `should_use_multiprocessing()` - Determine if parallel processing should be used
  - `get_processing_params()` - Get complete processing parameters with overrides

### Core Modules

**data_parser.py** - Log Format Detection and Parsing
- `recommendAccessLogFormat(inputFile)`: Auto-detects log format (ALB, Apache/Nginx, JSON) and generates a `logformat_*.json` file
- `parse_log_file_with_format(inputFile, logFormatFile, use_multiprocessing, num_workers, chunk_size, columns_to_load)`: Parse log files with optional parallel processing and memory optimization
  - **Multiprocessing support**: Automatically uses parallel processing for large files (>= 10,000 lines by default)
  - **Config.yaml auto-load**: When parameters are `None`, automatically loads settings from `config.yaml` (NEW)
  - **Configurable workers**: Auto-detects optimal worker count based on CPU cores and file size
  - **Chunk-based processing**: Splits large files into chunks for efficient parallel parsing
  - **Memory optimization** (NEW): `columns_to_load` parameter allows loading only required columns
    - Reduces memory usage by 80-90% for large files (e.g., loading 2 columns instead of 34)
    - Filters columns BEFORE DataFrame creation for maximum efficiency
    - Example: `columns_to_load=['time', 'request_url']` loads only these columns
  - Performance: ~3-4x faster for large files on multi-core systems
- Supports gzip-compressed files automatically
- Pattern matching with configurable `config.yaml` for ALB logs
- Returns metadata: pattern type, confidence score, success rate, field mappings

**data_processor.py** - Filtering and Statistics
- `filterByCondition(inputFile, logFormatFile, condition, params)`: Filters by time, status code, response time, client IP, URLs, or URI patterns
- `extractUriPatterns(inputFile, logFormatFile, extractionType, params)`: Extracts unique URLs or generalized URI patterns (replaces IDs/UUIDs with `*`)
  - **Unified patterns file** (NEW): Uses standardized patterns file path (`patterns_{log_name}.json`)
  - The function calls `_get_patterns_file_path()` from `data_visualizer` module to get standardized path
  - Uses `_save_or_merge_patterns()` from `data_visualizer` to merge with existing patterns, preserving manually added rules
- `calculateStats(inputFile, logFormatFile, params, use_multiprocessing, num_workers)`: Computes comprehensive statistics with parallel processing support
  - **Config.yaml auto-load** (NEW): When parameters are `None`, automatically loads multiprocessing settings from `config.yaml`
  - **Parallel URL statistics**: Process multiple URL groups concurrently (>= 100 URLs)
  - **Parallel time-series stats**: Calculate time interval statistics in parallel (>= 100 intervals)
  - **Parallel IP statistics**: Process IP groups concurrently (>= 100 IPs)
  - **timeInterval parameter**: Supports flexible time interval formats (e.g., '1m', '10s', '1h')
  - **processingTimeFields parameter**: Analyze multiple processing time fields simultaneously
    - Supports: `request_processing_time`, `target_processing_time`, `response_processing_time`, etc.
    - Calculates: avg, sum, median, std, min, max, p90, p95, p99 for each field
  - **sortBy/sortMetric/topN parameters**: Get Top N URLs by specific metrics
    - `sortBy`: Field to sort by (e.g., 'request_processing_time', 'target_processing_time')
    - `sortMetric`: Metric to use ('avg', 'sum', 'median', 'p95', 'p99')
    - `topN`: Return only top N results
    - Example: Top 20 URLs by average request_processing_time
  - Automatically normalizes common abbreviations: '1m' → '1min', '30sec' → '30s'
  - Performance: ~2-3x faster for large datasets with many unique URLs/IPs
- `PatternRulesManager` - Pattern caching class for efficient pattern rule loading (replaces global variables)
  - `load_rules(patterns_file)` - Load and cache pattern rules from file
  - `clear_cache(patterns_file)` - Clear cached patterns
  - `get_cached_files()` - Get list of cached pattern files
- All filtered data is saved as JSON Lines format for flexibility

**data_visualizer.py** - Interactive Visualizations
- **All visualization functions support `timeField` parameter** (NEW): Select between 'time' and 'request_creation_time' for analysis
- `generateXlog(inputFile, logFormatFile, outputFormat, timeField)`: Creates response time scatter plot with WebGL rendering
  - **Memory optimization**: Loads only required columns (time, URL, status, response time) instead of all 34+ fields
- `generateRequestPerURI(inputFile, logFormatFile, outputFormat, topN, interval, patternsFile, timeField)`: Generates time-series chart with interactive checkbox filtering and hover-text clipboard copy
  - **interval parameter**: Supports flexible time interval formats (e.g., '1m', '10s', '1h')
  - Automatically normalizes common abbreviations: '1m' → '1min', '30sec' → '30s'
  - Supported units: s (seconds), min (minutes), h (hours), d (days)
  - **Memory optimization**: Column filtering + dtype optimization + explicit memory cleanup
- `generateRequestPerTarget(inputFile, logFormatFile, outputFormat, topN, interval, timeField)`: Time-series visualization of request count per target (target_ip:target_port)
  - Groups requests by backend target servers
  - Interactive checkbox filtering and IP grouping with status color coding
- `generateRequestPerClientIP(inputFile, logFormatFile, outputFormat, topN, interval, timeField)`: Time-series visualization of request count per client IP
  - Groups requests by client source IP
  - Interactive checkbox filtering with status color coding
- `generateReceivedBytesPerURI()` and `generateSentBytesPerURI()`: Byte transfer analysis with memory optimization
- `generateProcessingTimePerURI(inputFile, logFormatFile, outputFormat, processingTimeField, metric, topN, interval, patternsFile, timeField)`: Time-series visualization of processing time per URI pattern
  - **processingTimeField**: Field to analyze (request_processing_time, target_processing_time, response_processing_time)
  - **metric**: Metric to calculate (avg, sum, median, p95, p99, max)
  - Extracts top N patterns by total processing time
  - Interactive time-series chart with zoom, pan, and range slider
- `generateMultiMetricDashboard(inputFile, logFormatFile, outputFormat, timeField)`: Creates comprehensive 3-panel dashboard
- **Pattern File Management**:
  - `_get_patterns_file_path(inputFile)`: Returns standardized patterns file path based on input log file (e.g., `patterns_access.log.json`)
  - `_save_or_merge_patterns(patterns_file_path, pattern_rules, metadata)`: Saves or merges pattern rules into a single patterns file, removing duplicates
  - All visualization functions now share a single patterns file per log file, eliminating multiple timestamped pattern files
  - Pattern rules are automatically merged when different visualization functions are called on the same log file
- **Memory Optimization Functions** (NEW):
  - `_optimize_dataframe_dtypes(df)`: Reduces memory usage by 50-70% through dtype optimization
    - int64 → int32/int16 (50% savings)
    - float64 → float32 (50% savings)
    - object → category (70-90% savings for low-cardinality strings)
  - Column filtering: Loads only required columns before DataFrame creation (80-90% memory reduction)
  - Explicit memory cleanup: Uses `gc.collect()` after pivot operations
- `_normalize_interval(interval)`: Helper function to normalize time interval strings to pandas-compatible format
- All visualizations use Plotly with CDN for interactivity

**main.py** - Interactive CLI
- Menu-driven interface for all MCP tools
- Example pipeline demonstrates tool chaining: stats → filter → visualization

**mcp_server.py** - MCP Server
- Exposes all MCP tools via stdio-based MCP protocol
- Enables integration with LLM-based agents

### File Naming Conventions

Output files follow strict naming patterns for easy identification:
- `logformat_*.json` - Log format detection results
- `filtered_*.log` - Filtered log data (JSON Lines format)
- `urls_*.json` - URL extraction results
- `uris_*.json` or `patterns_*.json` - URI pattern extraction with `patternRules`
- `patterns_{log_name}.json` - **Single unified patterns file per log file** (NEW)
  - All visualization functions now share the same patterns file for a given log file
  - Format: `patterns_access.json` for input file `access.log.gz` (`.log` extension is removed from stem)
  - Pattern rules are automatically merged when different functions extract patterns
  - Replaces previous timestamped files: `patterns_241111_120000.json`, `patterns_proctime_241111_120000.json`
- `stats_*.json` - Statistical analysis results
- `xlog_*.html` - Response time scatter plots
- `requestcnt_*.html` - Request count per URI visualizations
- `requestcnt_target_*.html` - Request count per target visualizations
- `requestcnt_clientip_*.html` - Request count per client IP visualizations
- `dashboard_*.html` - Multi-metric dashboards

### Key Design Patterns

**Tool Chaining Pattern**: Tools are designed to chain together:
```python
# 1. Detect format
format_result = recommendAccessLogFormat("access.log.gz")

# 2. Filter by time
filter_result = filterByCondition(
    "access.log.gz",
    format_result['logFormatFile'],
    'time',
    'startTime=2024-08-08T09:00:00;endTime=2024-08-08T10:00:00'
)

# 3. Visualize filtered data
xlog_result = generateXlog(
    filter_result['filePath'],
    format_result['logFormatFile'],
    'html'
)
```

**Pattern Rules System**: URI patterns use regex-based pattern rules stored in JSON:
```json
{
  "patternRules": [
    {
      "pattern": "^/api/users/.*$",
      "replacement": "/api/users/*"
    }
  ]
}
```

**Field Mapping Abstraction**: All tools use `fieldMap` from log format files to work with different log types:
```json
{
  "fieldMap": {
    "timestamp": "time",
    "url": "request_url",
    "status": "elb_status_code",
    "responseTime": "target_processing_time",
    "clientIp": "client_ip"
  }
}
```

## Important Implementation Details

### Log Format Detection Priority
When `recommendAccessLogFormat()` is called, it follows this search order:
1. Check for existing `logformat_*.json` in same directory (최우선)
2. Sample 100 lines from input file
3. Auto-detect format type (ALB, JSON, Apache/Nginx, or GROK fallback)
4. Search for `config.yaml` in multiple locations (input file dir, parent dir, CWD, script dir)
5. Generate and save `logformat_*.json` with absolute path

### Multi-Format Log Parsing with config.yaml (NEW)

The system now supports multiple log format types through `config.yaml`:

**Supported Log Format Types:**
1. **ALB** - AWS Application Load Balancer logs (34+ fields)
2. **HTTPD** - Apache/Nginx Combined Log Format
3. **HTTPD_WITH_TIME** - Apache logs with response time (%D or %T)
4. **NGINX** - Nginx access logs with custom format
5. **JSON** - JSON-formatted logs (one JSON object per line)
6. **GROK** - Custom log formats using regex patterns

**Configuration Structure:**
```yaml
# Specify log format type
log_format_type: 'HTTPD'  # Options: ALB, HTTPD, NGINX, JSON, GROK

# Format-specific configuration sections
httpd:
  input_path: 'access.log'
  log_pattern: '([^ ]*) [^ ]* ([^ ]*) \[([^\]]*)\] ...'
  columns:
    - "client_ip"
    - "user"
    - "time"
    ...
  field_map:
    timestamp: "time"
    method: "request_method"
    url: "request_url"
    status: "status"
    clientIp: "client_ip"
```

**How it Works:**
1. `_generate_alb_format()` reads `log_format_type` from config.yaml
2. Based on the type, it calls the appropriate loader:
   - `_load_alb_format_from_config()` - for ALB logs
   - `_load_httpd_format_from_config()` - for Apache/HTTPD logs
   - `_load_nginx_format_from_config()` - for Nginx logs
   - `_load_json_format_from_config()` - for JSON logs
   - `_load_grok_format_from_config()` - for custom patterns
3. `_parse_line()` uses columns from config to map regex groups to field names
4. Field mapping is automatically built with `_build_field_map_from_columns()`

**Field Mapping:**
- Explicit `field_map` in config takes priority
- If not provided, smart matching is used based on common field name variants
- Example variants:
  - Time: `time`, `timestamp`, `@timestamp`, `datetime`
  - URL: `url`, `request_url`, `uri`, `request_uri`, `path`
  - Status: `status`, `status_code`, `elb_status_code`, `http_status`
  - Client IP: `client_ip`, `remote_addr`, `client`, `ip`

**Legacy Compatibility:**
- Top-level `log_pattern` and `columns` still work for ALB logs
- If `log_format_type` is not specified, defaults to ALB
- Missing fields are set to `None` rather than failing parse

### JSON Lines Format for Filtered Data
All filtered output uses JSON Lines (one JSON object per line):
- Supports any log format as intermediate format
- Easy to re-parse for downstream tools
- Compatible with streaming processing

### URI Pattern Generalization

The system provides two URL generalization functions:
1. **`_generalize_url(url, patterns_file=None)`** - Loads pattern rules from file on each call
2. **`_generalize_url_with_rules(url, pattern_rules=None)`** - Accepts pre-loaded pattern rules (recommended for DataFrame operations)

Both functions intelligently replace dynamic segments:
- **ID-like segments** → `*`
  - Pure numbers → `*`
  - UUIDs (8-4-4-4-12 format) → `*`
  - Long hex strings (16+ chars) → `*`
  - Mixed alphanumeric with >70% digits → `*`
- **Static files** → categorized by extension
  - `.css`, `.scss`, `.sass`, `.less` → `*.css`
  - `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs` → `*.js`
  - `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.ico`, `.webp` → `*.image`
  - `.woff`, `.woff2`, `.ttf`, `.otf`, `.eot` → `*.font`
  - `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx` → `*.doc`
  - `.mp4`, `.avi`, `.mov`, `.webm`, `.mkv` → `*.video`
  - `.mp3`, `.wav`, `.ogg`, `.m4a` → `*.audio`
  - `.html`, `.htm` → `*.html`
  - `.json`, `.xml`, `.yaml`, `.yml`, `.csv`, `.txt` → `*.data`
  - `.zip`, `.tar`, `.gz`, `.rar`, `.7z` → `*.archive`
- **Custom patterns** → can use pattern rules from file for custom matching

**Performance Tip**: When processing many URLs in a DataFrame, use `_generalize_url_with_rules()` with pre-loaded pattern rules:
```python
# Good - loads pattern rules once
pattern_rules = _pattern_manager.load_rules(patterns_file)
df['url_pattern'] = df['url'].apply(lambda x: _generalize_url_with_rules(x, pattern_rules))

# Bad - loads pattern rules for every URL
df['url_pattern'] = df['url'].apply(lambda x: _generalize_url(x, patterns_file))
```

Example transformations:
```
/assets/styles/main.css → /assets/styles/*.css
/static/js/app.12345.js → /static/js/*.js
/images/logo.png → /images/*.image
/fonts/Roboto-Regular.woff2 → /fonts/*.font
```

### Timezone Handling
Filter by time supports both naive and timezone-aware timestamps:
- Timezone from log format file (`timezone` field)
- ISO 8601 format in filter parameters overrides log timezone
- Automatic conversion to ensure comparison compatibility

### Performance Optimizations
- **Sampling for large datasets**: Visualizations sample to 50,000 points max
- **WebGL rendering**: Uses `Scattergl` instead of `Scatter` for better performance
- **Efficient filtering**: Pattern matching uses compiled regex
- **Lazy loading**: Pattern rules cached globally to avoid re-parsing
- **Memory optimization** (NEW): Multi-layered approach for large log files
  - **Column filtering**: Load only required columns before DataFrame creation (80-90% memory reduction)
    - Example: Loading 2 columns instead of 34 for ALB logs
    - Applied in all visualization functions
  - **Dtype optimization**: Downcast numeric types and convert low-cardinality strings to category (50-70% reduction)
    - int64 → int32/int16
    - float64 → float32
    - object → category (for repetitive values)
  - **Explicit memory cleanup**: Use `gc.collect()` after large operations to free memory immediately
  - **Combined effect**: Can reduce total memory footprint by 90%+ for visualization tasks
- **Config.yaml auto-load**: Multiprocessing settings automatically loaded from config when parameters are `None`

## Error Handling

All modules use consistent error handling with custom exceptions:

```python
from core.exceptions import FileNotFoundError, ValidationError

# Validate file existence
if not os.path.exists(file_path):
    raise FileNotFoundError(file_path)

# Validate parameters
if value not in allowed_values:
    raise ValidationError('parameter_name', f"Invalid value: {value}")
```

Exceptions are properly caught and logged in `mcp_server.py`, returning structured error responses to clients.

## Logging

All modules use the centralized logging system:

```python
from core.logging_config import get_logger

logger = get_logger(__name__)

logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning messages")
logger.error("Error messages")
```

### Enabling File Logging

```python
from core.logging_config import enable_file_logging, set_log_level

# Enable file logging (creates logs/access_log_analyzer_YYYYMMDD.log)
enable_file_logging()

# Set log level for all loggers
set_log_level('DEBUG')
```

## Configuration Management

Use `ConfigManager` for centralized configuration:

```python
from core.config import ConfigManager

config_mgr = ConfigManager()

# Automatically search for config.yaml in standard locations
config = config_mgr.load_config()

# Get specific value with default
port = config_mgr.get('server.port', default=8080)

# Force reload configuration
config_mgr.reload()
```

## Using Utility Classes

### FieldMapper - Smart Field Mapping

```python
from core.utils import FieldMapper
import pandas as pd

# Find a field with fallback alternatives
df = pd.DataFrame({'timestamp': [...], 'request_url': [...]})
format_info = {'fieldMap': {...}}

time_field = FieldMapper.find_field(df, 'time', format_info)
# Returns 'timestamp' if exact match not found

# Map all common fields at once
field_map = FieldMapper.map_fields(df, format_info)
# Returns: {'timestamp': 'timestamp', 'url': 'request_url', ...}

# Validate required fields
FieldMapper.validate_required_fields(df, format_info, ['time', 'url'])
# Raises ValidationError if any field missing
```

### ParamParser - Type-Safe Parameter Parsing

```python
from core.utils import ParamParser

params = "startTime=2024-01-01;endTime=2024-12-31;topN=20;enabled=true"

# Parse all parameters
parsed = ParamParser.parse(params)
# Returns: {'startTime': '2024-01-01', 'endTime': '2024-12-31', ...}

# Get typed values
start_time = ParamParser.get(params, 'startTime', required=True)
top_n = ParamParser.get_int(params, 'topN', default=10)  # Returns int
enabled = ParamParser.get_bool(params, 'enabled')  # Returns bool
filters = ParamParser.get_list(params, 'filters', separator=',')  # Returns list
```

## Testing

### Running Tests

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_core_utils.py -v

# Run with coverage
pytest tests/ --cov=core --cov=data_parser --cov=data_processor
```

### Test Structure

```
tests/
├── conftest.py              # Pytest fixtures (sample logs)
├── test_core_exceptions.py  # Exception tests
├── test_core_utils.py       # FieldMapper, ParamParser tests
└── test_data_parser.py      # Parser tests
```

### Writing New Tests

```python
import pytest
from core.exceptions import ValidationError

def test_my_function():
    """Test description"""
    # Arrange
    input_data = "test"

    # Act
    result = my_function(input_data)

    # Assert
    assert result == expected_value

def test_error_handling():
    """Test error handling"""
    with pytest.raises(ValidationError):
        my_function_with_invalid_input()
```

## Working with the Codebase

### Adding a New MCP Tool

1. **Implement the function** in appropriate module (`data_processor.py` or `data_visualizer.py`)
   - Add type hints: `def myTool(inputFile: str, logFormatFile: str, params: str = '') -> Dict[str, Any]:`
   - Use custom exceptions: `raise CustomFileNotFoundError(inputFile)`
   - Use logger: `logger.info("Processing...")`
   - Use ParamParser for parameters: `topN = ParamParser.get_int(params, 'topN', default=20)`
   - Return a dict with `filePath` (absolute path) and metadata

2. **Add tool registration** in `mcp_server.py`:
   ```python
   Tool(
       name="myTool",
       description="한글 설명",
       inputSchema={...}
   )
   ```

3. **Add handler** in `mcp_server.py` `call_tool()` function

4. **Add menu item** in `main.py` interactive menu

5. **Write tests** in `tests/test_my_module.py`

### Debugging Parse Failures
When log parsing fails, the system outputs:
- `⚠️ 파싱에 실패한 라인` with line numbers and truncated content
- First 10 failed lines during format recommendation
- All failed lines during actual parsing (up to first 10 displayed)

Check for:
- Pattern/columns mismatch in `config.yaml`
- Unexpected log format variations
- Extra/missing fields in ALB logs

### Working with Patterns File
The `patterns_*.json` or `uris_*.json` file has evolved format:
- **New format** (preferred): `patternRules` array with `pattern` (regex) and `replacement`
- **Old format** (backward compatible): `patterns` array with match patterns
- When using in `generateRequestPerURI()`, new format enables precise matching

To convert old format to new:
```python
# extractUriPatterns now automatically generates patternRules
result = extractUriPatterns(log_file, format_file, 'patterns', 'maxPatterns=50')
# Output file will contain patternRules
```

## Configuration

### config.yaml Structure (NEW - Multi-Format Support)

The config.yaml file now supports multiple log format types with format-specific sections:

```yaml
# Global settings
version: '1.0'

# Multiprocessing Configuration
multiprocessing:
  enabled: true
  num_workers: null          # null = auto-detect
  chunk_size: 10000
  min_lines_for_parallel: 10000

# Specify which log format to use
log_format_type: 'HTTPD'     # Options: ALB, HTTPD, NGINX, JSON, GROK

# ============================================================================
# Format-Specific Configurations
# ============================================================================

# ALB (AWS Application Load Balancer) Configuration
alb:
  input_path: '*.gz'
  log_pattern: '([^ ]*) ([^ ]*) ...'
  columns:
    - "type"
    - "time"
    - "elb"
    - "client_ip"
    ...
  column_types:
    time: "datetime"
    elb_status_code: "int"
    target_processing_time: "float"

# HTTPD (Apache/Nginx Combined Log Format)
httpd:
  input_path: 'access.log'
  log_pattern: '([^ ]*) [^ ]* ([^ ]*) \[([^\]]*)\] ...'
  columns:
    - "client_ip"
    - "user"
    - "time"
    - "request_method"
    - "request_url"
    - "request_proto"
    - "status"
    - "bytes_sent"
    - "referer"
    - "user_agent"
  column_types:
    time: "datetime"
    status: "int"
    bytes_sent: "int"
  field_map:
    timestamp: "time"
    method: "request_method"
    url: "request_url"
    status: "status"
    clientIp: "client_ip"

# HTTPD with Response Time (Apache %D or %T)
httpd_with_time:
  input_path: 'access.log'
  log_pattern: '... ([0-9]+)'  # Last group is response time
  columns:
    - ...
    - "response_time_us"  # Response time in microseconds

# Nginx Configuration
nginx:
  input_path: 'access.log'
  log_pattern: '([^ ]*) - ([^ ]*) \[([^\]]*)\] "([^ ]*) ([^ ]*) ([^"]*)" ([0-9]*) ([0-9\-]*) "([^"]*)" "([^"]*)" ([0-9.]+)'
  columns:
    - "client_ip"
    - "remote_user"
    - "time"
    - "request_method"
    - "request_url"
    - "request_proto"
    - "status"
    - "bytes_sent"
    - "referer"
    - "user_agent"
    - "request_time"  # Response time in seconds

# JSON Configuration (field mapping only)
json:
  input_path: 'access.log'
  field_map:
    timestamp: "timestamp"
    method: "method"
    url: "url"
    status: "status"
    responseTime: "response_time"
    clientIp: "client_ip"

# GROK/Custom Pattern Configuration
grok:
  input_path: 'custom.log'
  log_pattern: '(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[([^\]]+)\] (.*)'
  columns:
    - "timestamp"
    - "level"
    - "message"

# ============================================================================
# Legacy Configuration (Backward Compatibility)
# ============================================================================
# Top-level fields for ALB (used if log_format_type not specified)
input_path: '*.gz'
log_pattern: '...'
columns: [...]
column_types: {...}
```

**Key Features:**
- **Format-specific sections**: Each log format has its own configuration section
- **Automatic field mapping**: Smart matching of common field names if `field_map` not provided
- **Flexible patterns**: Support for any regex pattern (HTTPD, GROK) or JSON
- **Column mapping**: Regex groups are mapped to column names automatically
- **Legacy support**: Old config structure still works for ALB logs

### Multiprocessing Configuration (NEW)

The system now supports parallel processing for faster analysis of large log files:

**Configuration Options:**
- `enabled`: Enable or disable multiprocessing globally (default: `true`)
- `num_workers`: Number of worker processes
  - `null` (default): Auto-detect based on CPU cores and workload
  - Specific number: Use fixed number of workers (e.g., `4`, `8`)
- `chunk_size`: Number of lines/items processed per chunk (default: `10000`)
  - Larger chunks = less overhead, but less parallelism
  - Smaller chunks = more overhead, but better load distribution
- `min_lines_for_parallel`: Minimum lines to trigger parallel processing (default: `10000`)
  - Files smaller than this will use sequential processing

**When Multiprocessing is Used:**
1. **Log Parsing** (`parse_log_file_with_format`):
   - Triggered when file has >= `min_lines_for_parallel` lines (default: 10,000)
   - Reads entire file, splits into chunks, parses in parallel
   - Performance gain: ~3-4x on 8-core systems

2. **Statistics Calculation** (`calculateStats`):
   - **URL stats**: Triggered when >= 100 unique URLs
   - **Time-series stats**: Triggered when >= 100 time intervals
   - **IP stats**: Triggered when >= 100 unique IPs
   - Performance gain: ~2-3x for large datasets

**Performance Tips:**
- **CPU-bound workloads**: Set `num_workers` to CPU core count
- **I/O-bound workloads**: Can use more workers than cores
- **Memory constraints**: Reduce `chunk_size` or `num_workers` if running out of memory
- **Small files**: Multiprocessing overhead may slow down processing; adjust `min_lines_for_parallel`

**Disabling Multiprocessing:**
```yaml
multiprocessing:
  enabled: false  # Disable all parallel processing
```

Or pass parameters directly to functions:
```python
# Disable for specific call
parse_log_file_with_format(file, format, use_multiprocessing=False)
calculateStats(file, format, params, use_multiprocessing=False)
```

### Environment Assumptions
- Python 3.7+
- UTF-8 encoding for all files
- WSL2 or Unix-like environment (for file paths)
- Working directory: `/mnt/c/bucket/AccesslogAnalyzer`

## Common Workflows

### Analyzing ALB Logs
1. Place `config.yaml` in same directory as log file
2. Set `log_format_type: 'ALB'` in config.yaml
3. Run format detection: `recommendAccessLogFormat("access.log.gz")`
4. Extract patterns: `extractUriPatterns(file, format, 'patterns', 'maxPatterns=20')`
   - This automatically creates/updates `patterns_access.json` (unified patterns file)
5. Generate visualization: `generateRequestPerURI(file, format, 'html', topN=20, interval='10s', patternsFile='patterns_access.json')`
   - Note: patternsFile parameter is optional - if not specified, the function will auto-generate patterns

### Analyzing Apache/Nginx Access Logs (NEW)
1. Create or modify `config.yaml`:
   ```yaml
   log_format_type: 'HTTPD'  # or 'NGINX'

   httpd:
     input_path: 'access.log'
     log_pattern: '([^ ]*) [^ ]* ([^ ]*) \[([^\]]*)\] "([^ ]*) ([^ ]*) ([^"]*)" ([0-9]*) ([0-9\-]*)(?: "([^"]*)" "([^"]*)")? ?([0-9.]+)?'
     columns:
       - "client_ip"
       - "user"
       - "time"
       - "request_method"
       - "request_url"
       - "request_proto"
       - "status"
       - "bytes_sent"
       - "referer"
       - "user_agent"
       - "request_time"  # Optional: response time field
     field_map:
       timestamp: "time"
       method: "request_method"
       url: "request_url"
       status: "status"
       clientIp: "client_ip"
       responseTime: "request_time"  # If response time exists
   ```
2. Run format detection: `recommendAccessLogFormat("access.log")`
   - System will use config.yaml settings
3. Parse and analyze as usual with all MCP tools

### Analyzing JSON Logs (NEW)
1. Create or modify `config.yaml`:
   ```yaml
   log_format_type: 'JSON'

   json:
     input_path: 'access.log'
     field_map:
       timestamp: "timestamp"  # Adjust to match your JSON field names
       method: "method"
       url: "url"
       status: "status"
       responseTime: "response_time"
       clientIp: "client_ip"
   ```
2. Run format detection and parse as usual

### Analyzing Custom Log Formats (GROK) (NEW)
1. Define custom pattern in `config.yaml`:
   ```yaml
   log_format_type: 'GROK'

   grok:
     input_path: 'custom.log'
     log_pattern: '(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[([^\]]+)\] (\S+) (\S+) (\d+) (.+)'
     columns:
       - "timestamp"
       - "level"
       - "client_ip"
       - "request_url"
       - "status"
       - "message"
     field_map:
       timestamp: "timestamp"
       url: "request_url"
       status: "status"
       clientIp: "client_ip"
   ```
2. Parse and analyze with all MCP tools

### Custom Time Range Analysis
1. Detect format
2. Filter by time: `filterByCondition(file, format, 'time', 'startTime=...;endTime=...')`
3. Calculate stats on filtered data
4. Generate XLog for filtered timeframe

### Top N Slow URLs (Legacy Method)
1. Calculate stats: `calculateStats(file, format, 'statsType=url')`
2. Parse `stats_*.json` to find top URLs by avg response time
3. Create URL list and filter: `filterByCondition(file, format, 'urls', 'urlsFile=top5.json')`
4. Generate XLog for slow URLs only

### Top N URLs by Processing Time (NEW)
Get top URLs by specific processing time metrics in a single command:

```python
# Top 20 URLs by average request_processing_time
result = calculateStats(
    'access.log.gz',
    'logformat_*.json',
    params='statsType=url;processingTimeFields=request_processing_time,target_processing_time,response_processing_time;sortBy=request_processing_time;sortMetric=avg;topN=20'
)

# Top 10 URLs by sum of target_processing_time
result = calculateStats(
    'access.log.gz',
    'logformat_*.json',
    params='statsType=url;processingTimeFields=target_processing_time;sortBy=target_processing_time;sortMetric=sum;topN=10'
)

# Top 15 URLs by p95 response_processing_time
result = calculateStats(
    'access.log.gz',
    'logformat_*.json',
    params='statsType=url;processingTimeFields=response_processing_time;sortBy=response_processing_time;sortMetric=p95;topN=15'
)
```

Output includes:
- URL statistics for all specified processing time fields
- Each field shows: avg, sum, median, std, min, max, p90, p95, p99
- Results automatically sorted and limited to top N
- Summary text with processing time details

---

## Recent Changes and Improvements

### Field Availability Check (2025-11-28)

**Problem**: Users could select visualization options that required fields not present in their log format (e.g., selecting "target_processing_time" for HTTPD logs which don't have this field), leading to confusing error messages after parsing.

**Solution**: Added field availability checking in `main.py`:

#### New Helper Functions

```python
def _get_available_columns(log_format_file):
    """
    Get available columns from log format file.
    Includes derived columns (e.g., request_method, request_url for HTTPD).
    """

def _check_field_availability(field_name, available_columns):
    """
    Check if a field is available in the log format.
    Supports field name variants across different log formats:
    - sent_bytes: ['sent_bytes', 'bytes_sent', 'size', 'response_size', 'body_bytes_sent']
    - received_bytes: ['received_bytes', 'bytes', 'request_size']
    - target_ip: ['target_ip', 'backend_ip', 'upstream_addr']
    - client_ip: ['client_ip', 'remote_addr', 'clientIp']
    - request_processing_time: ['request_processing_time', 'request_time']
    - target_processing_time: ['target_processing_time', 'upstream_response_time']
    - response_processing_time: ['response_processing_time']
    """
```

#### Updated Functions

All field-dependent visualization functions now show availability status:

1. **`generate_processing_time()`** - Shows availability for each processing time field:
   ```
   Select processing time field:
     1. request_processing_time - ✗ Not available
     2. target_processing_time (default) - ✗ Not available
     3. response_processing_time - ✗ Not available

     ✗ Field Not Found: target_processing_time
     Available columns in log format: client_ip, identity, user, time, request, status, bytes_sent, referer, user_agent, request_method
   ```

2. **`generate_sent_bytes()`** - Checks for sent_bytes field before execution
3. **`generate_received_bytes()`** - Checks for received_bytes field before execution
4. **`generate_request_per_target()`** - Checks for target_ip field before execution

**Benefits**:
- Users see immediately which fields are available in their log format
- Prevents wasted time parsing logs for unavailable features
- Clear error messages showing available alternatives
- Supports field name variants across different log formats

### Column Type Conversion for HTTPD Logs (2025-11-28)

**Problem**: HTTPD log time fields were stored as strings, causing "Total transactions: 0" in visualizations.

**Solution**:
1. Added `columnTypes` to format file generation (`recommendAccessLogFormat`)
2. Added column type conversion in `parse_log_file_with_format()`:
   ```python
   # Apply column type conversions
   for col, dtype in column_types.items():
       if dtype == 'datetime':
           if pattern_type == 'HTTPD':
               # Apache format: 12/Dec/2021:03:13:02 +0900
               df[col] = pd.to_datetime(df[col], format='%d/%b/%Y:%H:%M:%S %z', errors='coerce')
           else:
               df[col] = pd.to_datetime(df[col], errors='coerce')
       elif dtype in ('int', 'integer'):
           df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
       elif dtype in ('float', 'double'):
           df[col] = pd.to_numeric(df[col], errors='coerce')
   ```

**Result**: All 1,764,211 HTTPD log entries now parse correctly with proper datetime conversion.

### HTTPD Request Field Handling (2025-11-28)

**Problem**: HTTPD logs have a single "request" field containing "METHOD URL PROTOCOL", but visualizations need separate fields.

**Solution**: Implemented post-parse splitting in `parse_log_file_with_format()`:

```python
# For HTTPD logs: split request into method, url, protocol
if pattern_type == 'HTTPD' and 'request' in df.columns:
    def split_request(request_str):
        if pd.isna(request_str) or request_str in ('', '-', ' '):
            return None, None, None
        parts = request_str.strip().split(' ', 2)
        if len(parts) == 3:
            return parts[0], parts[1], parts[2]
        # Handle malformed requests
        return None, None, None

    split_results = df['request'].apply(split_request)
    df['request_method'] = split_results.apply(lambda x: x[0])
    df['request_url'] = split_results.apply(lambda x: x[1])
    df['request_proto'] = split_results.apply(lambda x: x[2])
```

**Smart Column Filtering**: If derived columns (request_url, request_method, request_proto) are requested, automatically includes source 'request' column, then removes it after splitting.

**Result**:
- 100% parsing success (1,764,211 entries, 0 failures)
- Handles malformed requests gracefully
- Memory efficient (removes source column after splitting)

### Key Lessons for AI Assistants

1. **Field Variants**: When checking field availability, always consider variants. Different log formats use different field names for the same concept (e.g., bytes_sent vs sent_bytes).

2. **Format-Specific Datetime**: Apache/HTTPD logs use format `%d/%b/%Y:%H:%M:%S %z`, while ALB uses ISO format. Always specify the correct format string.

3. **Derived Columns**: Some log formats (HTTPD) require post-parse processing to create commonly-used fields. Always check for derived column logic.

4. **User Experience**: Show field availability BEFORE the user starts a long parsing operation. This saves time and prevents frustration.

5. **Graceful Degradation**: When a field is not available, show alternatives rather than just an error. The `_check_field_availability()` function checks variants automatically.
