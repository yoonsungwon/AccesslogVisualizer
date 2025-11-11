# Processing Time Statistics - Usage Guide

This document explains how to use the new processing time statistics feature in AccessLogAnalyzer.

## Overview

The `calculateStats` function has been enhanced to support multiple processing time field analysis with flexible sorting and Top N filtering.

## Key Features

### 1. Multiple Processing Time Fields
Analyze multiple timing fields simultaneously:
- `request_processing_time`: Time to receive request from client
- `target_processing_time`: Time for backend to process request
- `response_processing_time`: Time to send response back to client

### 2. Comprehensive Statistics
For each field, the following metrics are calculated:
- **avg**: Average value
- **sum**: Total sum
- **median**: 50th percentile
- **std**: Standard deviation
- **min**: Minimum value
- **max**: Maximum value
- **p90**: 90th percentile
- **p95**: 95th percentile
- **p99**: 99th percentile

### 3. Flexible Sorting
Sort results by any field and metric combination:
- Sort by field: Any processing time field or 'count'
- Sort by metric: 'avg', 'sum', 'median', 'p95', 'p99'

### 4. Top N Filtering
Get only the top N URLs based on your criteria.

## Usage Examples

### Example 1: Top 20 URLs by Average Request Processing Time

```python
from data_processor import calculateStats

result = calculateStats(
    inputFile='access.log.gz',
    logFormatFile='logformat_240101_120000.json',
    params='statsType=url;processingTimeFields=request_processing_time,target_processing_time,response_processing_time;sortBy=request_processing_time;sortMetric=avg;topN=20'
)

print(f"Results saved to: {result['filePath']}")
print(f"\nSummary:\n{result['summary']}")
```

**Parameters:**
- `statsType=url`: Calculate URL statistics
- `processingTimeFields=request_processing_time,target_processing_time,response_processing_time`: Analyze all three fields
- `sortBy=request_processing_time`: Sort by request processing time
- `sortMetric=avg`: Use average metric for sorting
- `topN=20`: Return only top 20 URLs

**Output JSON Structure:**
```json
{
  "urlStats": [
    {
      "url": "/api/heavy-endpoint",
      "count": 1500,
      "request_processing_time": {
        "avg": 0.025,
        "sum": 37.5,
        "median": 0.020,
        "std": 0.015,
        "min": 0.001,
        "max": 0.150,
        "p90": 0.045,
        "p95": 0.060,
        "p99": 0.100
      },
      "target_processing_time": {
        "avg": 0.350,
        "sum": 525.0,
        ...
      },
      "response_processing_time": {
        "avg": 0.005,
        "sum": 7.5,
        ...
      }
    },
    ...
  ]
}
```

### Example 2: Top 10 URLs by Sum of Target Processing Time

```python
result = calculateStats(
    inputFile='access.log.gz',
    logFormatFile='logformat_240101_120000.json',
    params='statsType=url;processingTimeFields=target_processing_time;sortBy=target_processing_time;sortMetric=sum;topN=10'
)
```

**Use Case:** Find URLs that consume the most total backend processing time.

### Example 3: Top 15 URLs by P95 Response Processing Time

```python
result = calculateStats(
    inputFile='access.log.gz',
    logFormatFile='logformat_240101_120000.json',
    params='statsType=url;processingTimeFields=response_processing_time;sortBy=response_processing_time;sortMetric=p95;topN=15'
)
```

**Use Case:** Find URLs with slowest response sending times (95th percentile).

### Example 4: All Processing Time Fields, Sorted by P99

```python
result = calculateStats(
    inputFile='access.log.gz',
    logFormatFile='logformat_240101_120000.json',
    params='statsType=url;processingTimeFields=request_processing_time,target_processing_time,response_processing_time;sortBy=target_processing_time;sortMetric=p99;topN=25'
)
```

**Use Case:** Find URLs with worst-case backend processing times.

## Parameter Reference

### statsType
- **Type**: String (comma-separated)
- **Options**: 'all', 'summary', 'url', 'time', 'ip'
- **Example**: `statsType=url`

### processingTimeFields
- **Type**: String (comma-separated field names)
- **Available Fields**:
  - `request_processing_time`
  - `target_processing_time`
  - `response_processing_time`
  - Any custom processing time field in your logs
- **Example**: `processingTimeFields=request_processing_time,target_processing_time`

### sortBy
- **Type**: String (field name)
- **Options**: Any processing time field name, or 'count'
- **Default**: 'count'
- **Example**: `sortBy=target_processing_time`

### sortMetric
- **Type**: String
- **Options**: 'avg', 'sum', 'median', 'p90', 'p95', 'p99'
- **Default**: 'avg'
- **Example**: `sortMetric=p95`

### topN
- **Type**: Integer
- **Default**: None (returns all results)
- **Example**: `topN=20`

## Performance Considerations

### Multiprocessing
- Automatically enabled for 100+ unique URLs
- Significantly faster for large datasets
- Can be disabled with `use_multiprocessing=False`

### Example Performance
- Dataset: 1,000,000 requests, 500 unique URLs
- Without multiprocessing: ~30 seconds
- With multiprocessing (8 cores): ~10 seconds

## Output Interpretation

### Summary Text
The summary includes processing time details for top URLs:

```
Total Requests: 1500000
Unique URLs: 350
Unique IPs: 25000

Top URLs:
  1. /api/orders (45000 requests)
      request: avg=0.015, sum=675.000, target: avg=0.250, sum=11250.000, response: avg=0.003, sum=135.000
  2. /api/users (38000 requests)
      request: avg=0.012, sum=456.000, target: avg=0.180, sum=6840.000, response: avg=0.002, sum=76.000
  ...
```

### JSON Output
Full statistics are saved to `stats_YYMMDD_HHMMSS.json` with complete metrics for all URLs.

## Common Use Cases

### 1. Find Backend Bottlenecks
```python
# Top URLs by average backend processing time
params='statsType=url;processingTimeFields=target_processing_time;sortBy=target_processing_time;sortMetric=avg;topN=20'
```

### 2. Find Total Time Consumers
```python
# URLs consuming most total processing time
params='statsType=url;processingTimeFields=target_processing_time;sortBy=target_processing_time;sortMetric=sum;topN=10'
```

### 3. Find Worst-Case Scenarios
```python
# URLs with highest p99 processing times
params='statsType=url;processingTimeFields=request_processing_time,target_processing_time,response_processing_time;sortBy=target_processing_time;sortMetric=p99;topN=15'
```

### 4. Comprehensive Analysis
```python
# All fields, all metrics, sorted by average
params='statsType=url;processingTimeFields=request_processing_time,target_processing_time,response_processing_time;sortBy=target_processing_time;sortMetric=avg;topN=50'
```

## Integration with Other Tools

### Chain with Filtering
```python
# 1. Find top slow URLs
stats_result = calculateStats(
    'access.log.gz',
    'format.json',
    params='statsType=url;processingTimeFields=target_processing_time;sortBy=target_processing_time;sortMetric=avg;topN=10'
)

# 2. Extract top URL list from JSON
with open(stats_result['filePath'], 'r') as f:
    stats_data = json.load(f)
    top_urls = [stat['url'] for stat in stats_data['urlStats'][:10]]

# 3. Filter original log for these URLs
from data_processor import filterByCondition
# ... (create URL filter file)
filtered_result = filterByCondition(
    'access.log.gz',
    'format.json',
    'urls',
    f'urlsFile={url_list_file}'
)

# 4. Generate visualization for slow URLs only
from data_visualizer import generateXlog
generateXlog(filtered_result['filePath'], 'format.json', 'html')
```

## Troubleshooting

### Field Not Found
If a processing time field doesn't exist in your logs:
- The field is skipped silently
- Other fields are still processed
- Check field names in your log format file

### No Results
If no statistics are returned:
- Verify field names match log format
- Check that numeric conversion succeeded
- Review log format file fieldMap

### Sorting Not Working
If results aren't sorted as expected:
- Verify sortBy field exists in processingTimeFields
- Check sortMetric is valid ('avg', 'sum', etc.)
- Ensure field has data (not all NaN)

## Version Information
- **Feature Added**: Version 2.0 (2025-01-11)
- **Compatibility**: Requires pandas, numpy
- **Python Version**: 3.7+
