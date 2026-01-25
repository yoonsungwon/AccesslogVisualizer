# 사용 예제 (Usage Examples)

Access Log Analyzer의 Python API, CLI, 워크플로우 예제를 제공합니다.

**관련 문서:**
- [CONFIGURATION.md](./CONFIGURATION.md) - 설정 가이드
- [API_REFERENCE.md](./API_REFERENCE.md) - API 참조
- [PROCESSING_TIME_USAGE.md](./PROCESSING_TIME_USAGE.md) - 처리 시간 통계 가이드

## 목차

1. [빠른 시작 워크플로우](#빠른-시작-워크플로우-quick-start-workflows)
2. [CLI (main.py) 사용 예제](#cli-mainpy-사용-예제)
3. [Python API 사용 예제](#python-api-사용-예제)
4. [고급 워크플로우](#고급-워크플로우-advanced-workflows)

---

## 빠른 시작 워크플로우 (Quick Start Workflows)

### 기본 분석 파이프라인

```python
from data_parser import recommendAccessLogFormat
from data_processor import extractUriPatterns
from data_visualizer import generateRequestPerURI

# 1. 로그 포맷 감지
format_result = recommendAccessLogFormat("access.log.gz")

# 2. URI 패턴 추출
patterns_result = extractUriPatterns(
    "access.log.gz",
    format_result['logFormatFile'],
    'patterns',
    'maxPatterns=20'
)

# 3. 시각화 생성
viz_result = generateRequestPerURI(
    "access.log.gz",
    format_result['logFormatFile'],
    'html',
    topN=20,
    interval='10s',
    patternsFile=patterns_result['filePath']
)
```

### ALB 로그 분석 워크플로우

1. 로그 파일과 동일한 디렉토리에 `config.yaml` 배치
2. config.yaml에 `log_format_type: 'ALB'` 설정

```python
# 1. 포맷 감지 실행
format_result = recommendAccessLogFormat("access.log.gz")
# 출력: logformat_access.json

# 2. 패턴 추출 (patterns_access.json 생성/업데이트)
patterns_result = extractUriPatterns(
    "access.log.gz",
    format_result['logFormatFile'],
    'patterns',
    'maxPatterns=20'
)

# 3. 시각화 생성
viz_result = generateRequestPerURI(
    "access.log.gz",
    format_result['logFormatFile'],
    'html',
    topN=20,
    interval='10s',
    patternsFile='patterns_access.json'
)
```

### Apache/Nginx 로그 분석 워크플로우

config.yaml 설정:
```yaml
log_format_type: 'HTTPD'  # 또는 'NGINX'

httpd:
  input_path: 'access.log'
  log_pattern: '...'  # 로그 패턴
  columns: [...]      # 컬럼 목록
  field_map:
    timestamp: "time"
    method: "request_method"
    url: "request_url"
    status: "status"
```

```python
# 포맷 감지 실행 (config.yaml 설정 사용)
format_result = recommendAccessLogFormat("access.log")

# 모든 MCP 도구로 평소와 같이 분석
stats_result = calculateStats(
    "access.log",
    format_result['logFormatFile'],
    'statsType=url'
)
```

---

## CLI (main.py) 사용 예제

### 기본 사용법

```bash
# 대화형 메뉴 모드
python main.py

# 파일별 모드
python main.py access.log.gz

# 예제 파이프라인
python main.py --example access.log.gz
```

### 처리 시간 분석을 포함한 통계 계산

메뉴에서 옵션 6 "Calculate statistics"를 선택하면 추가 옵션이 표시됩니다:

#### 예제 세션

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

Processing time fields (default: all three above): request_processing_time,target_processing_time,response_processing_time

--- Sorting & Top N (Optional) ---
Sort by field: target_processing_time
Sort metric (default: avg): avg
Top N URLs to return: 20

✓ Statistics calculated:
  Output file: /path/to/stats_250111_143000.json
```

### CLI 사용 사례

#### 사용 사례 1: 평균 백엔드 처리 시간 기준 상위 10개 URL 찾기

**입력:**
- Statistics type: `url`
- Analyze processing time fields: `y`
- Processing time fields: `target_processing_time`
- Sort by field: `target_processing_time`
- Sort metric: `avg`
- Top N: `10`

#### 사용 사례 2: 총 처리 시간을 가장 많이 소비하는 URL 찾기

**입력:**
- Statistics type: `url`
- Sort by field: `target_processing_time`
- Sort metric: `sum`
- Top N: `20`

#### 사용 사례 3: 최악의 응답 시간 (P95) 찾기

**입력:**
- Sort by field: `target_processing_time`
- Sort metric: `p95`
- Top N: `15`

### 처리 시간 시각화 (옵션 12)

옵션 12는 URI 패턴별 처리 시간의 시계열 시각화를 제공합니다.

```
--- Generate Processing Time per URI ---

Select processing time field:
  1. request_processing_time
  2. target_processing_time (default)
  3. response_processing_time
Field number (1-3, default: 2): 2

Select metric:
  1. avg - Average (default)
  2. median - Median
  3. p95 - 95th Percentile
  4. p99 - 99th Percentile
  5. max - Maximum
Metric number (1-5, default: 1): 3

✓ Processing Time chart generated
```

### 필드 가용성 확인

CLI는 분석을 시작하기 **전**에 로그 포맷에서 사용 가능한 필드를 표시합니다:

```
--- Generate Processing Time per URI ---

Select processing time field:
  1. request_processing_time - ✗ Not available
  2. target_processing_time (default) - ✗ Not available
  3. response_processing_time - ✗ Not available

  ✗ Field Not Found: target_processing_time
  Available columns in log format: client_ip, identity, user, time, request, status, bytes_sent
```

### 빠른 참조

#### 처리 시간 필드
- `request_processing_time` - 클라이언트로부터 요청을 받는 데 걸린 시간
- `target_processing_time` - 백엔드 처리 시간
- `response_processing_time` - 클라이언트로 응답을 보내는 데 걸린 시간

#### 정렬 메트릭
- `avg` - 평균값
- `sum` - 총합
- `median` - 중앙값
- `p95` - 95번째 백분위수
- `p99` - 99번째 백분위수

---

## Python API 사용 예제

### 예제 1: 로그 포맷 자동 감지

```python
from data_parser import recommendAccessLogFormat

result = recommendAccessLogFormat('access.log.gz')

print(f"Pattern Type: {result['patternType']}")
print(f"Confidence: {result['confidence']:.1%}")
print(f"Format File: {result['logFormatFile']}")
```

### 예제 2: 시간 범위 필터링

```python
from data_parser import recommendAccessLogFormat
from data_processor import filterByCondition

# 1. 로그 포맷 감지
format_result = recommendAccessLogFormat('access.log.gz')
log_format_file = format_result['logFormatFile']

# 2. 시간 필터링
result = filterByCondition(
    'access.log.gz',
    log_format_file,
    'time',
    'startTime=2024-10-23T09:00:00;endTime=2024-10-23T10:00:00'
)

print(f"Filtered: {result['filteredLines']} / {result['totalLines']} lines")
print(f"Output: {result['filePath']}")
```

### 예제 3: 에러 로그만 추출

```python
from data_parser import recommendAccessLogFormat
from data_processor import filterByCondition

format_result = recommendAccessLogFormat('access.log.gz')
log_format_file = format_result['logFormatFile']

# 4xx, 5xx 에러만 필터링
result = filterByCondition(
    'access.log.gz',
    log_format_file,
    'statusCode',
    'statusCodes=4xx,5xx'
)

print(f"Errors found: {result['filteredLines']}")
```

### 예제 4: 느린 요청 찾기

```python
from data_parser import recommendAccessLogFormat
from data_processor import filterByCondition

format_result = recommendAccessLogFormat('access.log.gz')
log_format_file = format_result['logFormatFile']

# 2초 이상 걸린 요청만 필터링
result = filterByCondition(
    'access.log.gz',
    log_format_file,
    'responseTime',
    'min=2s'
)

print(f"Slow requests: {result['filteredLines']}")
```

### 예제 5: URI 패턴 추출 및 통계

```python
from data_parser import recommendAccessLogFormat
from data_processor import extractUriPatterns, calculateStats

format_result = recommendAccessLogFormat('access.log.gz')
log_format_file = format_result['logFormatFile']

# URI 패턴 추출 (최소 1000건 이상)
patterns = extractUriPatterns(
    'access.log.gz',
    log_format_file,
    'patterns',
    'minCount=1000;maxPatterns=100'
)

print(f"Found {patterns['patternsFound']} patterns")

# 통계 계산
stats = calculateStats(
    'access.log.gz',
    log_format_file,
    'statsType=url;timeInterval=10m'
)

print(f"\nStatistics saved to: {stats['filePath']}")
```

### 예제 6: XLog 생성

```python
from data_parser import recommendAccessLogFormat
from data_visualizer import generateXlog

format_result = recommendAccessLogFormat('access.log.gz')
log_format_file = format_result['logFormatFile']

# XLog 생성
result = generateXlog(
    'access.log.gz',
    log_format_file,
    'html'
)

print(f"XLog generated: {result['filePath']}")
print(f"Total transactions: {result['totalTransactions']}")
```

### 예제 7: 복합 파이프라인

```python
from data_parser import recommendAccessLogFormat
from data_processor import filterByCondition, calculateStats
from data_visualizer import generateXlog

# 1. 로그 포맷 감지
print("Step 1: Detecting log format...")
format_result = recommendAccessLogFormat('access.log.gz')
log_format_file = format_result['logFormatFile']

# 2. 특정 시간대 필터링
print("Step 2: Filtering by time...")
time_filtered = filterByCondition(
    'access.log.gz',
    log_format_file,
    'time',
    'startTime=2024-10-23T09:00:00;endTime=2024-10-23T10:00:00'
)

# 3. 에러만 필터링
print("Step 3: Filtering errors...")
error_filtered = filterByCondition(
    time_filtered['filePath'],
    log_format_file,
    'statusCode',
    'statusCodes=5xx'
)

# 4. 통계 계산
print("Step 4: Calculating statistics...")
stats = calculateStats(
    error_filtered['filePath'],
    log_format_file,
    'statsType=url'
)

# 5. XLog 생성
print("Step 5: Generating XLog...")
xlog = generateXlog(
    error_filtered['filePath'],
    log_format_file,
    'html'
)

print(f"\nPipeline completed!")
print(f"- Errors in time range: {error_filtered['filteredLines']}")
print(f"- Statistics: {stats['filePath']}")
print(f"- XLog: {xlog['filePath']}")
```

### 예제 8: 특정 IP 대역 분석

```python
from data_parser import recommendAccessLogFormat
from data_processor import filterByCondition, calculateStats

format_result = recommendAccessLogFormat('access.log.gz')
log_format_file = format_result['logFormatFile']

# 특정 IP 대역 필터링 (CIDR 표기법 지원)
result = filterByCondition(
    'access.log.gz',
    log_format_file,
    'client',
    'clientIps=10.0.0.0/8,172.16.0.0/12'
)

print(f"Requests from internal networks: {result['filteredLines']}")

# 통계 계산
stats = calculateStats(
    result['filePath'],
    log_format_file,
    'statsType=ip'
)
```

### 예제 9: Dashboard 생성

```python
from data_parser import recommendAccessLogFormat
from data_visualizer import generateMultiMetricDashboard

format_result = recommendAccessLogFormat('access.log.gz')
log_format_file = format_result['logFormatFile']

# 종합 대시보드 생성
result = generateMultiMetricDashboard(
    'access.log.gz',
    log_format_file,
    'html'
)

print(f"Dashboard generated: {result['filePath']}")
print(f"Total transactions: {result['totalTransactions']}")
print("\nThe dashboard includes:")
print("- Request count per minute")
print("- Average response time")
print("- Error rate")
```

---

## 고급 워크플로우 (Advanced Workflows)

### Top N 느린 URL 분석

#### 방법 1: calculateStats 사용 (권장)

단일 명령으로 특정 처리 시간 메트릭 기준 상위 URL 가져오기:

```python
from data_processor import calculateStats

# 평균 request_processing_time 기준 상위 20개 URL
result = calculateStats(
    'access.log.gz',
    'logformat_access.json',
    params='statsType=url;processingTimeFields=request_processing_time,target_processing_time,response_processing_time;sortBy=request_processing_time;sortMetric=avg;topN=20'
)

# target_processing_time 합계 기준 상위 10개 URL
result = calculateStats(
    'access.log.gz',
    'logformat_access.json',
    params='statsType=url;processingTimeFields=target_processing_time;sortBy=target_processing_time;sortMetric=sum;topN=10'
)

# p95 response_processing_time 기준 상위 15개 URL
result = calculateStats(
    'access.log.gz',
    'logformat_access.json',
    params='statsType=url;processingTimeFields=response_processing_time;sortBy=response_processing_time;sortMetric=p95;topN=15'
)
```

### 사용자 정의 시간 범위 분석

```python
from data_parser import recommendAccessLogFormat
from data_processor import filterByCondition, calculateStats
from data_visualizer import generateXlog

# 1. 포맷 감지
format_result = recommendAccessLogFormat("access.log.gz")

# 2. 시간으로 필터링
filter_result = filterByCondition(
    "access.log.gz",
    format_result['logFormatFile'],
    'time',
    'startTime=2024-08-08T09:00:00;endTime=2024-08-08T10:00:00'
)
# 출력: filtered_*.log (JSON Lines 포맷)

# 3. 필터링된 데이터에 대해 통계 계산
stats_result = calculateStats(
    filter_result['filePath'],
    format_result['logFormatFile'],
    'statsType=url'
)

# 4. 필터링된 시간대에 대해 XLog 생성
xlog_result = generateXlog(
    filter_result['filePath'],
    format_result['logFormatFile'],
    'html'
)
```

### 처리 시간 분석

```python
from data_visualizer import generateProcessingTimePerURI

# request_processing_time에 대한 처리 시간 시각화 생성
result = generateProcessingTimePerURI(
    'access.log.gz',
    'logformat_access.json',
    'html',
    processingTimeField='request_processing_time',
    metric='avg',
    topN=20,
    interval='10min',
    patternsFile='patterns_access.json'
)

# target_processing_time에 대해 생성
result = generateProcessingTimePerURI(
    'access.log.gz',
    'logformat_access.json',
    'html',
    processingTimeField='target_processing_time',
    metric='p95',
    topN=20,
    interval='10min',
    patternsFile='patterns_access.json'
)
```

### 바이트 전송 분석

```python
from data_visualizer import generateSentBytesPerURI, generateReceivedBytesPerURI

# 전송 바이트 분석
result = generateSentBytesPerURI(
    'access.log.gz',
    'logformat_access.json',
    'html',
    topN=20,
    interval='10min',
    patternsFile='patterns_access.json'
)

# 수신 바이트 분석
result = generateReceivedBytesPerURI(
    'access.log.gz',
    'logformat_access.json',
    'html',
    topN=20,
    interval='10min',
    patternsFile='patterns_access.json'
)
```

### 타겟 및 클라이언트 IP 분석

```python
from data_visualizer import generateRequestPerTarget, generateRequestPerClientIP

# 백엔드 서버별 요청 분포 시각화
result = generateRequestPerTarget(
    'access.log.gz',
    'logformat_access.json',
    'html',
    topN=10,
    interval='5min'
)

# 클라이언트 소스 IP별 요청 분포 시각화
result = generateRequestPerClientIP(
    'access.log.gz',
    'logformat_access.json',
    'html',
    topN=20,
    interval='5min'
)
```

### 상태 코드/응답 시간 필터링

```python
from data_processor import filterByCondition

# 4xx 에러 필터링
filter_result = filterByCondition(
    'access.log.gz',
    'logformat_access.json',
    'statusCode',
    'statusCodes=4xx'
)

# 1초보다 느린 요청 필터링
filter_result = filterByCondition(
    'access.log.gz',
    'logformat_access.json',
    'responseTime',
    'minTime=1.0'
)

# 범위 내 요청 필터링
filter_result = filterByCondition(
    'access.log.gz',
    'logformat_access.json',
    'responseTime',
    'minTime=0.5;maxTime=2.0'
)
```

### 대용량 파일을 위한 메모리 최적화

```python
from data_parser import parse_log_file_with_format

# 필요한 컬럼만 로드하여 메모리 사용량 80-90% 감소
df = parse_log_file_with_format(
    'large_access.log.gz',
    'logformat_access.json',
    columns_to_load=['time', 'request_url', 'status', 'target_processing_time']
)

# 멀티프로세싱으로 빠른 파싱
df = parse_log_file_with_format(
    'large_access.log.gz',
    'logformat_access.json',
    use_multiprocessing=True,
    num_workers=8,
    chunk_size=10000
)
```

### 전체 분석 예제

```python
from data_parser import recommendAccessLogFormat
from data_processor import extractUriPatterns, calculateStats
from data_visualizer import (
    generateRequestPerURI,
    generateProcessingTimePerURI,
    generateXlog,
    generateMultiMetricDashboard
)

# 1. 포맷 감지
print("Step 1: Detecting log format...")
format_result = recommendAccessLogFormat("access.log.gz")

# 2. URI 패턴 추출
print("\nStep 2: Extracting URI patterns...")
patterns_result = extractUriPatterns(
    "access.log.gz",
    format_result['logFormatFile'],
    'patterns',
    'maxPatterns=30'
)

# 3. 포괄적인 통계 계산
print("\nStep 3: Calculating statistics...")
stats_result = calculateStats(
    "access.log.gz",
    format_result['logFormatFile'],
    'statsType=url;processingTimeFields=request_processing_time,target_processing_time;sortBy=target_processing_time;sortMetric=p95;topN=20'
)

# 4. 요청 수 시각화 생성
print("\nStep 4: Generating request count visualization...")
request_viz = generateRequestPerURI(
    "access.log.gz",
    format_result['logFormatFile'],
    'html',
    topN=20,
    interval='10min',
    patternsFile=patterns_result['filePath']
)

# 5. 처리 시간 시각화 생성
print("\nStep 5: Generating processing time visualization...")
proctime_viz = generateProcessingTimePerURI(
    "access.log.gz",
    format_result['logFormatFile'],
    'html',
    processingTimeField='target_processing_time',
    metric='p95',
    topN=20,
    interval='10min',
    patternsFile=patterns_result['filePath']
)

# 6. XLog 산점도 생성
print("\nStep 6: Generating XLog scatter plot...")
xlog_viz = generateXlog(
    "access.log.gz",
    format_result['logFormatFile'],
    'html'
)

# 7. 다중 메트릭 대시보드 생성
print("\nStep 7: Generating dashboard...")
dashboard = generateMultiMetricDashboard(
    "access.log.gz",
    format_result['logFormatFile'],
    'html'
)

print("\nAnalysis complete!")
```

---

## 패턴 파일 작업

### 패턴 파일 포맷

패턴 파일은 정규식 기반 규칙을 사용합니다:

```json
{
  "patternRules": [
    {
      "pattern": "^/api/users/.*$",
      "replacement": "/api/users/*"
    },
    {
      "pattern": "^/products/[0-9]+$",
      "replacement": "/products/*"
    }
  ],
  "metadata": {
    "created": "2024-11-11T12:00:00",
    "maxPatterns": 20
  }
}
```

### 통합 패턴 파일 관리

- 파일 이름 포맷: `patterns_{log_name}.json`
- 다른 함수가 패턴을 추출할 때 패턴 규칙이 자동으로 병합됩니다.

---

## 팁과 트릭

### Tip 1: 결과 파일 재사용
필터링이나 처리 결과 파일(`filtered_*.log`)은 다음 단계의 입력으로 바로 사용할 수 있습니다.

### Tip 2: JSON 출력 파일 분석
통계나 URL 목록은 JSON 형식으로 저장되므로, 다른 도구나 스크립트에서 쉽게 읽어서 추가 처리할 수 있습니다.

### Tip 3: 시간 범위 형식
시간 범위는 ISO 8601 형식을 사용합니다:
- `2024-10-23T09:00:00`
- `2024-10-23T09:00:00+09:00` (타임존 지정)

### Tip 4: 응답시간 단위
응답시간은 다양한 단위를 지원합니다:
- `500ms` (밀리초)
- `0.5s` (초)
- `500000us` (마이크로초)

### Tip 5: 시간 간격 포맷
시간 간격은 유연한 포맷을 지원합니다:
- 초: `'10s'`, `'30s'`, `'30sec'`
- 분: `'1m'`, `'5min'`, `'10m'`
- 시간: `'1h'`, `'2hr'`, `'3hour'`
- 일: `'1d'`, `'7day'`

---

## 문제 해결

### 문제: "No valid lines found in file"
**원인**: 로그 파일이 비어있거나 압축 형식이 잘못되었습니다.
**해결**: `zcat access.log.gz | head -10`으로 파일 내용을 확인하세요.

### 문제: "Pattern Type: GROK, Confidence: 10%"
**원인**: 로그 포맷을 자동 감지하지 못했습니다.
**해결**: 로그 포맷을 수동으로 지정하거나 config.yaml을 확인하세요.

### 문제: "No data to visualize"
**원인**: 필터링 결과가 비어있거나, 필수 필드가 누락되었습니다.
**해결**: 필터링 조건을 완화하거나 필드 매핑을 확인하세요.

---

## 추가 리소스

- **기본 문서**: `README.md` - 프로젝트 개요 및 빠른 시작
- **설계 문서**: [DESIGN.md](./DESIGN.md) - 아키텍처 및 MCP 도구 상세 설명
- **API 참조**: [API_REFERENCE.md](./API_REFERENCE.md) - 함수 시그니처 및 매개변수
