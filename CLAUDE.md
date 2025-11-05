# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

### Core Modules

**data_parser.py** - Log Format Detection and Parsing
- `recommendAccessLogFormat(inputFile)`: Auto-detects log format (ALB, Apache/Nginx, JSON) and generates a `logformat_*.json` file
- Supports gzip-compressed files automatically
- Pattern matching with configurable `config.yaml` for ALB logs
- Returns metadata: pattern type, confidence score, success rate, field mappings

**data_processor.py** - Filtering and Statistics
- `filterByCondition(inputFile, logFormatFile, condition, params)`: Filters by time, status code, response time, client IP, URLs, or URI patterns
- `extractUriPatterns(inputFile, logFormatFile, extractionType, params)`: Extracts unique URLs or generalized URI patterns (replaces IDs/UUIDs with `*`)
- `calculateStats(inputFile, logFormatFile, params)`: Computes comprehensive statistics (summary, per-URL, time-series, per-IP)
- All filtered data is saved as JSON Lines format for flexibility

**data_visualizer.py** - Interactive Visualizations
- `generateXlog(inputFile, logFormatFile, outputFormat)`: Creates response time scatter plot with WebGL rendering
- `generateRequestPerURI(inputFile, logFormatFile, outputFormat, topN, interval, patternsFile)`: Generates time-series chart with interactive checkbox filtering and hover-text clipboard copy
- `generateMultiMetricDashboard(inputFile, logFormatFile, outputFormat)`: Creates comprehensive 3-panel dashboard
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
- `stats_*.json` - Statistical analysis results
- `xlog_*.html` - Response time scatter plots
- `requestcnt_*.html` - Request count visualizations
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

### ALB Log Parsing with config.yaml
For ALB logs, the system can use `config.yaml` for column definitions:
- If `config.yaml` exists with `columns` and `log_pattern`, it takes precedence
- The pattern should match AWS ALB access log format (34+ fields)
- Missing fields are set to `None` rather than failing parse

### JSON Lines Format for Filtered Data
All filtered output uses JSON Lines (one JSON object per line):
- Supports any log format as intermediate format
- Easy to re-parse for downstream tools
- Compatible with streaming processing

### URI Pattern Generalization
The `_generalize_url()` function intelligently replaces dynamic segments:
- Pure numbers → `*`
- UUIDs (8-4-4-4-12 format) → `*`
- Long hex strings (16+ chars) → `*`
- Mixed alphanumeric with >70% digits → `*`
- Can use pattern rules from file for custom matching

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

## Working with the Codebase

### Adding a New MCP Tool

1. **Implement the function** in appropriate module (`data_processor.py` or `data_visualizer.py`)
   - Function signature: `def myTool(inputFile, logFormatFile, params='')`
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

### config.yaml Structure
```yaml
input_path: '*.gz'  # Glob pattern or file path
log_pattern: '...'  # Regex pattern for ALB logs (34+ groups)
columns: [...]      # Field names matching regex groups
column_types:       # Type conversions
  time: "datetime"
  elb_status_code: "int"
  target_processing_time: "float"
```

### Environment Assumptions
- Python 3.7+
- UTF-8 encoding for all files
- WSL2 or Unix-like environment (for file paths)
- Working directory: `/mnt/c/bucket/AccesslogAnalyzer`

## Common Workflows

### Analyzing ALB Logs
1. Place `config.yaml` in same directory as log file
2. Run format detection: `recommendAccessLogFormat("access.log.gz")`
3. Extract patterns: `extractUriPatterns(file, format, 'patterns', 'maxPatterns=20')`
4. Generate visualization: `generateRequestPerURI(file, format, 'html', topN=20, interval='10s', patternsFile='patterns_*.json')`

### Custom Time Range Analysis
1. Detect format
2. Filter by time: `filterByCondition(file, format, 'time', 'startTime=...;endTime=...')`
3. Calculate stats on filtered data
4. Generate XLog for filtered timeframe

### Top N Slow URLs
1. Calculate stats: `calculateStats(file, format, 'statsType=url')`
2. Parse `stats_*.json` to find top URLs by avg response time
3. Create URL list and filter: `filterByCondition(file, format, 'urls', 'urlsFile=top5.json')`
4. Generate XLog for slow URLs only
