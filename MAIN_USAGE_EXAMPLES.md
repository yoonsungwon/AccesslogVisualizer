# main.py Usage Examples

This document provides examples of using the interactive CLI with the new Processing Time analysis feature.

## Basic Usage

```bash
# Interactive menu mode
python main.py

# File-specific mode
python main.py access.log.gz

# Example pipeline
python main.py --example access.log.gz
```

## Calculate Statistics with Processing Time Analysis

When you select option 6 "Calculate statistics" from the menu, you'll now see additional options:

### Example Session

```
--- Calculate Statistics ---
Available types: all, summary, url, time, ip
Statistics type (comma-separated, default: all): url
Time interval (1h, 30m, 10m, 5m, 1m, default: 10m): 10m

--- Processing Time Analysis (Optional) ---
Analyze processing time fields? (y/n, default: n): y

Available fields (comma-separated):
  - request_processing_time
  - target_processing_time
  - response_processing_time
  - Or any custom processing time field in your logs

Processing time fields (default: all three above): request_processing_time,target_processing_time,response_processing_time

--- Sorting & Top N (Optional) ---
Sort by field (e.g., request_processing_time, target_processing_time, or empty to skip): target_processing_time

Available metrics: avg, sum, median, p95, p99
Sort metric (default: avg): avg

Top N URLs to return (e.g., 20, 50, or empty for all): 20

✓ Statistics calculated:
  Output file: /path/to/stats_250111_143000.json

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

## Use Cases

### Use Case 1: Find Top 10 URLs by Average Backend Processing Time

**Input:**
- Statistics type: `url`
- Analyze processing time fields: `y`
- Processing time fields: `target_processing_time` (just this one)
- Sort by field: `target_processing_time`
- Sort metric: `avg`
- Top N: `10`

**Result:** Get the 10 URLs with the highest average backend processing time.

### Use Case 2: Find URLs Consuming Most Total Processing Time

**Input:**
- Statistics type: `url`
- Analyze processing time fields: `y`
- Processing time fields: `request_processing_time,target_processing_time,response_processing_time`
- Sort by field: `target_processing_time`
- Sort metric: `sum`
- Top N: `20`

**Result:** Get the 20 URLs that consume the most total backend processing time (useful for finding high-traffic slow endpoints).

### Use Case 3: Find Worst-Case Response Times (P95)

**Input:**
- Statistics type: `url`
- Analyze processing time fields: `y`
- Processing time fields: `target_processing_time`
- Sort by field: `target_processing_time`
- Sort metric: `p95`
- Top N: `15`

**Result:** Get the 15 URLs with the worst 95th percentile response times.

### Use Case 4: Simple Statistics Without Processing Time

**Input:**
- Statistics type: `all`
- Analyze processing time fields: `n`

**Result:** Get standard statistics (request counts, status codes, basic response time stats) without detailed processing time breakdown.

## Example Pipeline (Option 12)

The example pipeline now demonstrates the new Processing Time analysis feature:

```bash
python main.py --example access.log.gz
```

**What it does:**
1. Calculates URL statistics with processing time analysis
2. Gets Top 5 URLs by average `target_processing_time`
3. Filters the log to show only those URLs
4. Generates an XLog visualization

**Output:**
```
======================================================================
Example Pipeline: Top 5 URLs by Processing Time → XLog
======================================================================

[1/4] Calculating statistics with processing time analysis...
  Using new processingTimeFields feature!
  ✓ Stats file: /path/to/stats_250111_143000.json

[2/4] Extracting top 5 URLs by avg target_processing_time...
  ✓ Top 5 URLs by avg target_processing_time:
    1. /api/heavy-endpoint (count: 1500)
       target_processing_time: avg=0.3500s, p95=0.6000s
    2. /api/slow-query (count: 800)
       target_processing_time: avg=0.2800s, p95=0.5500s
    ...

[3/4] Filtering log by top 5 URLs...
  ✓ Filtered: 5000 / 1500000 lines
  ✓ Filtered file: /path/to/filtered_250111_143000.log

[4/4] Generating XLog...
  ✓ XLog generated: /path/to/xlog_250111_143000.html

======================================================================
Pipeline completed successfully!
======================================================================

Results:
  - Statistics: /path/to/stats_250111_143000.json
  - Filtered log: /path/to/filtered_250111_143000.log
  - XLog: /path/to/xlog_250111_143000.html

Open the XLog HTML file to view the visualization.

Note: This pipeline used the NEW processing time analysis feature
      to get Top 5 URLs by target_processing_time in a single command!
```

## Quick Reference

### Processing Time Fields
- `request_processing_time` - Time to receive request from client
- `target_processing_time` - Backend processing time
- `response_processing_time` - Time to send response to client

### Sort Metrics
- `avg` - Average value
- `sum` - Total sum (useful for finding total time consumers)
- `median` - 50th percentile
- `p95` - 95th percentile
- `p99` - 99th percentile

### Menu Options
- **6** - Calculate statistics (includes new Processing Time analysis)
- **12** - Run example pipeline (demonstrates new feature)

## Tips

1. **Start Simple**: Try without Processing Time analysis first to understand the data
2. **Use Top N**: For large datasets, use Top N to get only the most relevant URLs
3. **Choose Right Metric**:
   - `avg` - Find consistently slow endpoints
   - `sum` - Find endpoints consuming most total time
   - `p95`/`p99` - Find endpoints with worst-case performance
4. **Multiple Fields**: Analyze all three processing time fields to understand where time is spent (client, backend, response)
