# Access Log Analyzer - Usage Examples

This document provides practical examples for analyzing different log formats.

## Table of Contents
1. [ALB Logs](#alb-logs)
2. [Apache Access Logs](#apache-access-logs)
3. [Nginx Access Logs](#nginx-access-logs)
4. [JSON Logs](#json-logs)
5. [Custom Log Formats (GROK)](#custom-log-formats-grok)

---

## ALB Logs

### Configuration (config.yaml)
```yaml
log_format_type: 'ALB'

alb:
  input_path: '*.gz'
  log_pattern: '([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*):([0-9]*) ([^ ]*)[:-]([0-9]*) ([-.0-9]*) ([-.0-9]*) ([-.0-9]*) (|[-0-9]*) (-|[-0-9]*) ([-0-9]*) ([-0-9]*) "([^ ]*) (.*) (- |[^ ]*)" "([^"]*)" ([A-Z0-9-_]+) ([A-Za-z0-9.-]*) ([^ ]*) "([^"]*)" "([^"]*)" "([^"]*)" ([-.0-9]*) ([^ ]*) "([^"]*)" "([^"]*)" "([^ ]*)" "([^\s]+?)" "([^\s]+)" "([^ ]*)" "([^ ]*)" ?([^ ]*)?'
  columns:
    - "type"
    - "time"
    - "elb"
    - "client_ip"
    - "client_port"
    - "target_ip"
    - "target_port"
    - "request_processing_time"
    - "target_processing_time"
    - "response_processing_time"
    - "elb_status_code"
    - "target_status_code"
    - "received_bytes"
    - "sent_bytes"
    - "request_verb"
    - "request_url"
    - "request_proto"
    - "user_agent"
    # ... (remaining columns)
```

### Usage
```python
from data_parser import recommendAccessLogFormat, parse_log_file_with_format
from data_visualizer import generateXlog, generateRequestPerURI

# 1. Detect format
result = recommendAccessLogFormat("access.log.gz")
format_file = result['logFormatFile']

# 2. Parse log file
df = parse_log_file_with_format("access.log.gz", format_file)
print(f"Parsed {len(df)} log entries")

# 3. Generate visualizations
generateXlog("access.log.gz", format_file, 'html')
generateRequestPerURI("access.log.gz", format_file, 'html', topN=20, interval='10s')
```

---

## Apache Access Logs

### Sample Log Format
```
192.168.1.100 - frank [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326 "http://www.example.com/start.html" "Mozilla/4.08 [en] (Win98; I ;Nav)"
```

### Configuration (config.yaml)
```yaml
log_format_type: 'HTTPD'

httpd:
  input_path: 'access.log'
  # Apache Combined Log Format
  # Note: Captures full "request" field, which is split into method/url/proto during parsing
  log_pattern: '([^ ]*) ([^ ]*) ([^ ]*) \[([^\]]*)] "([^"]*)" ([0-9]*) ([0-9\-]*)(?: "([^"]*)" "([^"]*)")?'
  columns:
    - "client_ip"
    - "identity"
    - "user"
    - "time"
    - "request"      # Full request line (e.g., "GET /path HTTP/1.1")
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
    method: "request_method"      # Derived from request
    url: "request_url"            # Derived from request
    status: "status"
    clientIp: "client_ip"
```

**Note**: The `request` field is automatically split into `request_method`, `request_url`, and `request_proto` during parsing.

### With Response Time (Apache %D directive)
```yaml
httpd_with_time:
  input_path: 'access.log'
  # Pattern with response time in microseconds at the end
  log_pattern: '([^ ]*) [^ ]* ([^ ]*) \[([^\]]*)\] "([^"]*)" ([0-9]*) ([0-9\-]*) "([^"]*)" "([^"]*)" ([0-9]+)'
  columns:
    - "client_ip"
    - "user"
    - "time"
    - "request"
    - "status"
    - "bytes_sent"
    - "referer"
    - "user_agent"
    - "response_time_us"
  column_types:
    time: "datetime"
    status: "int"
    bytes_sent: "int"
    response_time_us: "int"
  field_map:
    timestamp: "time"
    method: "request_method"
    url: "request_url"
    status: "status"
    clientIp: "client_ip"
    responseTime: "response_time_us"
```

### Usage
```python
# Same as ALB - just change config.yaml
from data_parser import recommendAccessLogFormat
from data_processor import calculateStats, extractUriPatterns
from data_visualizer import generateRequestPerURI

# 1. Detect format (will use HTTPD config from config.yaml)
result = recommendAccessLogFormat("access.log")
format_file = result['logFormatFile']

# 2. Extract URI patterns
extractUriPatterns("access.log", format_file, 'patterns', 'maxPatterns=20')

# 3. Calculate statistics
stats = calculateStats("access.log", format_file, 'statsType=url')

# 4. Visualize
generateRequestPerURI("access.log", format_file, 'html', topN=20, interval='1m')
```

---

## Nginx Access Logs

### Sample Log Format
```
192.168.1.100 - - [10/Oct/2000:13:55:36 -0700] "GET /index.html HTTP/1.1" 200 1024 "http://www.example.com/" "Mozilla/5.0" 0.123
```

### Configuration (config.yaml)
```yaml
log_format_type: 'NGINX'

nginx:
  input_path: 'access.log'
  # Nginx log format with request_time
  log_pattern: '([^ ]*) - ([^ ]*) \[([^\]]*)\] "([^"]*)" ([0-9]*) ([0-9\-]*) "([^"]*)" "([^"]*)" ([0-9.]+)'
  columns:
    - "client_ip"
    - "remote_user"
    - "time"
    - "request"           # Full request line
    - "status"
    - "bytes_sent"
    - "referer"
    - "user_agent"
    - "request_time"      # Response time in seconds
  column_types:
    time: "datetime"
    status: "int"
    bytes_sent: "int"
    request_time: "float"
  field_map:
    timestamp: "time"
    method: "request_method"      # Derived from request
    url: "request_url"            # Derived from request
    status: "status"
    responseTime: "request_time"
    clientIp: "client_ip"
```

**Note**: Like HTTPD, the `request` field is automatically split into `request_method`, `request_url`, and `request_proto`.

### Nginx Custom Log Format Configuration
For custom Nginx log formats, define your pattern in nginx.conf:
```nginx
log_format custom '$remote_addr - $remote_user [$time_local] '
                  '"$request" $status $body_bytes_sent '
                  '"$http_referer" "$http_user_agent" '
                  '$request_time $upstream_response_time';
```

Then update config.yaml pattern accordingly.

---

## JSON Logs

### Sample Log Format
```json
{"timestamp":"2024-01-15T10:30:00Z","method":"GET","url":"/api/users","status":200,"response_time":0.123,"client_ip":"192.168.1.100"}
```

### Configuration (config.yaml)
```yaml
log_format_type: 'JSON'

json:
  input_path: 'access.log'
  # No pattern needed for JSON - just field mapping
  field_map:
    timestamp: "timestamp"  # Adjust to match your JSON field names
    method: "method"
    url: "url"
    status: "status"
    responseTime: "response_time"
    clientIp: "client_ip"
```

### Alternative JSON Field Names
If your JSON uses different field names:
```yaml
json:
  field_map:
    timestamp: "@timestamp"      # Elasticsearch-style
    method: "request_method"
    url: "request_uri"
    status: "status_code"
    responseTime: "duration"
    clientIp: "remote_addr"
```

---

## Custom Log Formats (GROK)

### Example 1: Custom Application Log
```
2024-01-15 10:30:00 [INFO] 192.168.1.100 /api/users 200 GET 0.123s
```

#### Configuration
```yaml
log_format_type: 'GROK'

grok:
  input_path: 'app.log'
  log_pattern: '(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[([^\]]+)\] (\S+) (\S+) (\d+) (\S+) ([0-9.]+)s'
  columns:
    - "timestamp"
    - "level"
    - "client_ip"
    - "request_url"
    - "status"
    - "request_method"
    - "response_time"
  column_types:
    timestamp: "datetime"
    status: "int"
    response_time: "float"
  field_map:
    timestamp: "timestamp"
    method: "request_method"
    url: "request_url"
    status: "status"
    responseTime: "response_time"
    clientIp: "client_ip"
```

### Example 2: Load Balancer Custom Format
```
[2024-01-15T10:30:00+00:00] client=192.168.1.100 method=GET path=/api/users status=200 time=123ms
```

#### Configuration
```yaml
grok:
  log_pattern: '\[([^\]]+)\] client=(\S+) method=(\S+) path=(\S+) status=(\d+) time=(\d+)ms'
  columns:
    - "timestamp"
    - "client_ip"
    - "request_method"
    - "request_url"
    - "status"
    - "response_time_ms"
  column_types:
    timestamp: "datetime"
    status: "int"
    response_time_ms: "int"
  field_map:
    timestamp: "timestamp"
    clientIp: "client_ip"
    method: "request_method"
    url: "request_url"
    status: "status"
    responseTime: "response_time_ms"
```

---

## Complete Workflow Example

### Scenario: Analyze Apache Access Logs for Slow URLs

```python
# 1. Set up config.yaml
# (Set log_format_type to 'HTTPD' with appropriate pattern and columns)

# 2. Import required modules
from data_parser import recommendAccessLogFormat, parse_log_file_with_format
from data_processor import calculateStats, filterByCondition, extractUriPatterns
from data_visualizer import generateXlog, generateRequestPerURI, generateProcessingTimePerURI

# 3. Detect and parse log format
result = recommendAccessLogFormat("access.log")
format_file = result['logFormatFile']
print(f"Detected format: {result['patternType']}")

# 4. Parse the log file
df = parse_log_file_with_format("access.log", format_file)
print(f"Parsed {len(df)} entries")

# 5. Extract URI patterns
patterns_result = extractUriPatterns(
    "access.log",
    format_file,
    'patterns',
    'maxPatterns=30'
)
patterns_file = patterns_result['filePath']

# 6. Calculate statistics
stats_result = calculateStats(
    "access.log",
    format_file,
    params='statsType=url;sortBy=status;sortMetric=count;topN=20'
)

# 7. Filter by time range
filtered = filterByCondition(
    "access.log",
    format_file,
    'time',
    'startTime=2024-01-15T10:00:00;endTime=2024-01-15T11:00:00'
)

# 8. Generate visualizations
# XLog scatter plot
generateXlog(filtered['filePath'], format_file, 'html')

# Request count per URI
generateRequestPerURI(
    "access.log",
    format_file,
    'html',
    topN=20,
    interval='5m',
    patternsFile=patterns_file
)

print("Analysis complete! Check generated HTML files.")
```

---

## Tips and Best Practices

### 1. Testing Your Pattern
Before processing large files, test your regex pattern on a few sample lines:
```python
import re
sample = '192.168.1.100 - - [10/Oct/2000:13:55:36 -0700] "GET /index.html HTTP/1.1" 200 1024'
pattern = r'([^ ]*) - ([^ ]*) \[([^\]]*)\] "([^ ]*) ([^ ]*) ([^"]*)" ([0-9]*) ([0-9\-]*)'
match = re.match(pattern, sample)
if match:
    print(f"Matched {len(match.groups())} groups: {match.groups()}")
else:
    print("Pattern did not match!")
```

### 2. Column Count Must Match Groups
Ensure the number of columns in config.yaml matches the number of regex groups:
```python
import re
pattern = r'...'  # Your pattern
test_line = '...'  # Sample log line
groups = len(re.match(pattern, test_line).groups())
columns = [...]   # Your columns list
assert len(columns) == groups, f"Mismatch: {len(columns)} columns vs {groups} groups"
```

### 3. Response Time Units
Different log formats use different time units:
- **Apache %D**: Microseconds (µs)
- **Apache %T**: Seconds
- **Nginx $request_time**: Seconds with decimals
- **ALB**: Seconds with decimals

Configure `responseTimeUnit` in your format accordingly.

### 4. Timezone Handling
For Apache/Nginx logs, timestamps are in local time with timezone offset. Set `timezone: 'fromLog'` to parse from the timestamp itself.

For ALB logs, timestamps are always UTC, so set `timezone: 'UTC'`.

---

## Troubleshooting

### Issue: "Failed to parse line"
**Solution**: Check if your regex pattern matches the log format exactly. Use online regex testers or Python's `re.match()` to debug.

### Issue: "Missing required fields"
**Solution**: Ensure `field_map` contains at least `timestamp`, `url`, and `status` mappings.

### Issue: "Column count mismatch"
**Solution**: Count regex groups `()` in your pattern and ensure columns list has the same length.

### Issue: "No data after parsing"
**Solution**: Check if `pattern_type` is correct (HTTPD vs ALB vs JSON). Verify log file encoding is UTF-8.

---

## Additional Resources

- [AI_GUIDE.md](./AI_GUIDE.md) - Complete technical documentation
- [CLAUDE.md](./CLAUDE.md) - Claude Code integration guide
- [config.yaml](./config.yaml) - Full configuration file with all format examples
