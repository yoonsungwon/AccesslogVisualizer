# CLI (main.py) 사용 예제

대화형 CLI를 통한 로그 분석 예제를 제공합니다.

**관련 문서:**
- [USAGE_EXAMPLES.md](./USAGE_EXAMPLES.md) - Python API 사용 예제
- [PROCESSING_TIME_USAGE.md](./PROCESSING_TIME_USAGE.md) - 처리 시간 통계 가이드
- [WORKFLOWS.md](./WORKFLOWS.md) - 일반적인 워크플로우

## 기본 사용법

```bash
# 대화형 메뉴 모드
python main.py

# 파일별 모드
python main.py access.log.gz

# 예제 파이프라인
python main.py --example access.log.gz
```

## 처리 시간 분석을 포함한 통계 계산 (Calculate Statistics with Processing Time Analysis)

메뉴에서 옵션 6 "Calculate statistics"를 선택하면 이제 추가 옵션이 표시됩니다:

### 예제 세션

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

## 사용 사례 (Use Cases)

### 사용 사례 1: 평균 백엔드 처리 시간 기준 상위 10개 URL 찾기

**입력:**
- Statistics type: `url`
- Analyze processing time fields: `y`
- Processing time fields: `target_processing_time` (이것 하나만)
- Sort by field: `target_processing_time`
- Sort metric: `avg`
- Top N: `10`

**결과:** 평균 백엔드 처리 시간이 가장 높은 10개 URL을 가져옵니다.

### 사용 사례 2: 총 처리 시간을 가장 많이 소비하는 URL 찾기

**입력:**
- Statistics type: `url`
- Analyze processing time fields: `y`
- Processing time fields: `request_processing_time,target_processing_time,response_processing_time`
- Sort by field: `target_processing_time`
- Sort metric: `sum`
- Top N: `20`

**결과:** 총 백엔드 처리 시간을 가장 많이 소비하는 20개 URL을 가져옵니다 (트래픽이 많은 느린 엔드포인트를 찾는 데 유용함).

### 사용 사례 3: 최악의 응답 시간 (P95) 찾기

**입력:**
- Statistics type: `url`
- Analyze processing time fields: `y`
- Processing time fields: `target_processing_time`
- Sort by field: `target_processing_time`
- Sort metric: `p95`
- Top N: `15`

**결과:** 95번째 백분위수 응답 시간이 가장 나쁜 15개 URL을 가져옵니다.

### 사용 사례 4: 처리 시간 없는 간단한 통계

**입력:**
- Statistics type: `all`
- Analyze processing time fields: `n`

**결과:** 상세한 처리 시간 분석 없이 표준 통계(요청 수, 상태 코드, 기본 응답 시간 통계)를 가져옵니다.

## 예제 파이프라인 (옵션 12) (Example Pipeline (Option 12))

예제 파이프라인은 이제 새로운 처리 시간 분석 기능을 보여줍니다:

```bash
python main.py --example access.log.gz
```

**수행 작업:**
1. 처리 시간 분석을 포함하여 URL 통계 계산
2. 평균 `target_processing_time` 기준 상위 5개 URL 가져오기
3. 해당 URL만 표시하도록 로그 필터링
4. XLog 시각화 생성

**출력:**
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

## 빠른 참조 (Quick Reference)

### 처리 시간 필드 (Processing Time Fields)
- `request_processing_time` - 클라이언트로부터 요청을 받는 데 걸린 시간
- `target_processing_time` - 백엔드 처리 시간
- `response_processing_time` - 클라이언트로 응답을 보내는 데 걸린 시간

### 정렬 메트릭 (Sort Metrics)
- `avg` - 평균값
- `sum` - 총합 (총 시간 소비자를 찾는 데 유용)
- `median` - 50번째 백분위수 (중앙값)
- `p95` - 95번째 백분위수
- `p99` - 99번째 백분위수

### 메뉴 옵션 (Menu Options)
- **6** - 통계 계산 (새로운 처리 시간 분석 포함)
- **12** - URI별 처리 시간 생성 (신규 - 시계열 시각화)
- **13** - 예제 파이프라인 실행 (새로운 기능 시연)

## 처리 시간 시각화 (옵션 12) (Processing Time Visualization (Option 12))

### 대화형 시계열 차트 (Interactive Time-Series Chart)

옵션 12는 URI 패턴별 처리 시간의 시계열 시각화를 제공합니다.

#### 예제 세션

```
--- Generate Processing Time per URI ---

Select processing time field:
  1. request_processing_time
  2. target_processing_time (default)
  3. response_processing_time
Field number (1-3, default: 2): 2
  ✓ Selected field: target_processing_time

Select metric:
  1. avg - Average (default)
  2. median - Median
  3. p95 - 95th Percentile
  4. p99 - 99th Percentile
  5. max - Maximum
Metric number (1-5, default: 1): 3
  ✓ Selected metric: p95

  Found 2 pattern file(s) in the directory:
    1. patterns_250111_143000.json (20 pattern rules, 2048 bytes)
    2. patterns_250111_120000.json (15 pattern rules, 1536 bytes)

  Use existing pattern file? (y/n, default: n): y
  Select file number (1-2): 1
  ✓ Using pattern file: patterns_250111_143000.json

Number of top URI patterns to display (default: use all from file): 10

Time interval for aggregation (default: 1min, examples: 1s, 10s, 1min, 5min, 1h): 1min

✓ Processing Time chart generated:
  Total transactions: 1500000
  Processing time field: target_processing_time
  Metric: p95
  Top N patterns: 10
  Interval: 1min
  Patterns file: /path/to/patterns_250111_143000.json
  Patterns displayed: 10
  Output file: /path/to/proctime_target_processing_time_p95_250111_150000.html

  Open the HTML file in your browser to view the interactive chart.
  Features:
    - Time series visualization of processing time per URI pattern
    - Interactive legend to show/hide patterns
    - Drag to zoom, use toolbar for pan, reset, etc.
    - Range slider for time navigation
```

### 사용 사례 (Use Cases)

#### 시간 경과에 따른 백엔드 성능 모니터링
```
Field: target_processing_time
Metric: avg or p95
Interval: 1min or 5min
```
상위 엔드포인트에 대해 백엔드 처리 시간이 시간 경과에 따라 어떻게 변하는지 확인합니다.

#### 성능 저하 식별
```
Field: target_processing_time
Metric: p95 or p99
Interval: 5min
```
엔드포인트가 더 나쁜 최악의 성능을 보이기 시작하는 시점을 포착합니다.

#### 요청/응답 시간 비교
시각화를 두 번 실행:
1. Field: request_processing_time, Metric: avg
2. Field: response_processing_time, Metric: avg

두 차트를 비교하여 시간이 요청 수신 또는 응답 전송에 소비되는지 확인합니다.

### 차트 기능 (Chart Features)

- **대화형 범례**: 패턴을 클릭하여 표시/숨김
- **줌**: 드래그하여 영역 선택, 또는 줌 버튼 사용
- **팬**: 팬 도구를 사용하여 탐색
- **범위 슬라이더**: 하단에서 시간 범위 선택
- **시간 범위 버튼**: 빠른 선택 (1h, 6h, 12h, 1d, all)
- **내보내기**: 카메라 버튼을 사용하여 PNG로 다운로드

## 필드 가용성 확인 (신규) (Field Availability Check (NEW))

CLI는 이제 분석을 시작하기 **전**에 로그 포맷에서 사용 가능한 필드를 표시하여, 사용할 수 없는 기능에 대해 로그를 파싱하는 시간 낭비를 방지합니다.

### 예시: 처리 시간 필드 선택

```
--- Generate Processing Time per URI ---

Select processing time field:
  1. request_processing_time - ✗ Not available
  2. target_processing_time (default) - ✗ Not available
  3. response_processing_time - ✗ Not available

  ✗ Field Not Found: target_processing_time
  Available columns in log format: client_ip, identity, user, time, request, status, bytes_sent, referer, user_agent, request_method
```

### 필드 의존적 기능

다음 기능은 필드 가용성을 확인합니다:

- **옵션 10 (Received Bytes)**: `received_bytes` 필드 필요 (ALB 전용)
- **옵션 11 (Sent Bytes)**: `sent_bytes` 또는 `bytes_sent` 필드 필요
- **옵션 12 (Processing Time)**: 처리 시간 필드 필요 (ALB, HTTPD_WITH_TIME, 또는 NGINX)
- **옵션 13 (Request per Target)**: `target_ip` 필드 필요 (ALB 전용)

### 지원되는 필드 변형

시스템은 다양한 로그 포맷에 걸쳐 필드 이름 변형을 자동으로 확인합니다:

| 기능 | 필드 변형 |
|---------|----------------|
| Sent Bytes | `sent_bytes`, `bytes_sent`, `size`, `response_size`, `body_bytes_sent` |
| Received Bytes | `received_bytes`, `bytes`, `request_size` |
| Client IP | `client_ip`, `remote_addr`, `clientIp` |
| Target IP | `target_ip`, `backend_ip`, `upstream_addr` |
| Request Processing Time | `request_processing_time`, `request_time` |
| Target Processing Time | `target_processing_time`, `upstream_response_time` |

## 팁 (Tips)

1. **간단하게 시작**: 데이터를 이해하기 위해 먼저 처리 시간 분석 없이 시도하세요.
2. **Top N 사용**: 대규모 데이터셋의 경우 Top N을 사용하여 가장 관련성 높은 URL만 가져오세요.
3. **올바른 메트릭 선택**:
   - `avg` - 지속적으로 느린 엔드포인트 찾기
   - `sum` - 총 시간을 가장 많이 소비하는 엔드포인트 찾기
   - `p95`/`p99` - 최악의 성능을 보이는 엔드포인트 찾기
4. **다중 필드**: 세 가지 처리 시간 필드를 모두 분석하여 시간이 어디서 소비되는지 이해하세요 (클라이언트, 백엔드, 응답).
5. **시계열 시각화**: 옵션 12를 사용하여 처리 시간이 시간 경과에 따라 어떻게 변하는지 확인하세요.
6. **도구 결합**: 옵션 6을 사용하여 느린 URL을 찾은 다음, 옵션 12를 사용하여 성능 추세를 시각화하세요.
7. **필드 가용성 확인**: 기능을 선택하기 전에 로그 포맷에 필수 필드가 포함되어 있는지 확인하세요 (위 표 참조).
