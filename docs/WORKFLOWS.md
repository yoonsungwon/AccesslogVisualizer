# 일반적인 워크플로우

액세스 로그 분석을 위한 일반적인 워크플로우와 사용 패턴을 설명합니다.

**관련 문서:**
- [USAGE_EXAMPLES.md](./USAGE_EXAMPLES.md) - Python API 사용 예제
- [MAIN_USAGE_EXAMPLES.md](./MAIN_USAGE_EXAMPLES.md) - CLI (main.py) 사용 예제
- [CONFIGURATION.md](./CONFIGURATION.md) - 설정 가이드

## 빠른 시작 (Quick Start)

### 기본 분석 파이프라인 (Basic Analysis Pipeline)

```python
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

## ALB 로그 분석 (Analyzing ALB Logs)

### 설정 (Setup)

1. 로그 파일과 동일한 디렉토리에 `config.yaml` 배치
2. config.yaml에 `log_format_type: 'ALB'` 설정

### 워크플로우 (Workflow)

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
# 출력: patterns_access.json (통합 패턴 파일)

# 3. 시각화 생성
viz_result = generateRequestPerURI(
    "access.log.gz",
    format_result['logFormatFile'],
    'html',
    topN=20,
    interval='10s',
    patternsFile='patterns_access.json'
)
# 출력: requestcnt_*.html

# 참고: patternsFile 파라미터는 선택 사항입니다.
# 지정하지 않으면 함수가 자동으로 패턴을 생성합니다.
viz_result = generateRequestPerURI(
    "access.log.gz",
    format_result['logFormatFile'],
    'html',
    topN=20,
    interval='10s'
)
```

## Apache/Nginx 액세스 로그 분석 (Analyzing Apache/Nginx Access Logs)

### 설정 (Setup)

`config.yaml` 생성 또는 수정:

```yaml
log_format_type: 'HTTPD'  # 또는 'NGINX'

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
    - "request_time"  # 선택 사항: 응답 시간 필드
  field_map:
    timestamp: "time"
    method: "request_method"
    url: "request_url"
    status: "status"
    clientIp: "client_ip"
    responseTime: "request_time"  # 응답 시간이 존재하는 경우
```

### 워크플로우 (Workflow)

```python
# 1. 포맷 감지 실행 (config.yaml 설정 사용)
format_result = recommendAccessLogFormat("access.log")

# 2. 모든 MCP 도구로 평소와 같이 파싱 및 분석
stats_result = calculateStats(
    "access.log",
    format_result['logFormatFile'],
    'statsType=url'
)
```

## JSON 로그 분석 (Analyzing JSON Logs)

### 설정 (Setup)

`config.yaml` 생성 또는 수정:

```yaml
log_format_type: 'JSON'

json:
  input_path: 'access.log'
  field_map:
    timestamp: "timestamp"  # JSON 필드 이름에 맞게 조정
    method: "method"
    url: "url"
    status: "status"
    responseTime: "response_time"
    clientIp: "client_ip"
```

### 워크플로우 (Workflow)

```python
# 포맷 감지 실행 및 평소와 같이 파싱
format_result = recommendAccessLogFormat("access.log")
```

## 사용자 정의 로그 포맷 (GROK) 분석 (Analyzing Custom Log Formats (GROK))

### 설정 (Setup)

`config.yaml`에 사용자 정의 패턴 정의:

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

### 워크플로우 (Workflow)

```python
# 모든 MCP 도구로 파싱 및 분석
format_result = recommendAccessLogFormat("custom.log")
```

## 사용자 정의 시간 범위 분석 (Custom Time Range Analysis)

### 시간 범위로 필터링 (Filter by Time Range)

```python
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

## Top N 느린 URL 분석 (Top N Slow URLs Analysis)

### 방법 1: calculateStats 사용 (권장)

단일 명령으로 특정 처리 시간 메트릭 기준 상위 URL 가져오기:

```python
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

출력 포함 내용:
- 지정된 모든 처리 시간 필드에 대한 URL 통계
- 각 필드 표시 항목: avg, sum, median, std, min, max, p90, p95, p99
- 결과는 자동으로 정렬되고 상위 N개로 제한됨
- 처리 시간 세부 정보가 포함된 요약 텍스트

### 방법 2: 레거시 접근 방식

```python
# 1. 통계 계산
stats_result = calculateStats(
    "access.log.gz",
    "logformat_access.json",
    'statsType=url'
)

# 2. stats_*.json을 파싱하여 평균 응답 시간 기준 상위 URL 찾기
# (수동 단계: 상위 5개 느린 URL 식별)

# 3. URL 목록 생성 및 필터링
filter_result = filterByCondition(
    "access.log.gz",
    "logformat_access.json",
    'urls',
    'urlsFile=top5.json'
)

# 4. 느린 URL에 대해서만 XLog 생성
xlog_result = generateXlog(
    filter_result['filePath'],
    "logformat_access.json",
    'html'
)
```

## 처리 시간 분석 (Processing Time Analysis)

### 다중 처리 시간 필드 분석

```python
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

### 사용 가능한 메트릭

- `avg` - 평균 처리 시간
- `sum` - 총 처리 시간
- `median` - 처리 시간 중앙값
- `p95` - 95번째 백분위수
- `p99` - 99번째 백분위수
- `max` - 최대 처리 시간

## 다중 메트릭 대시보드 (Multi-Metric Dashboard)

### 종합 대시보드 생성

```python
# 다중 메트릭이 포함된 3패널 대시보드 생성
result = generateMultiMetricDashboard(
    'access.log.gz',
    'logformat_access.json',
    'html',
    timeField='time'
)
```

대시보드 포함 내용:
- 시간 경과에 따른 요청 수
- 응답 시간 분포
- 상태 코드 내역

## 타겟 및 클라이언트 IP 분석 (Target and Client IP Analysis)

### 백엔드 타겟별 요청 분석

```python
# 백엔드 서버별 요청 분포 시각화
result = generateRequestPerTarget(
    'access.log.gz',
    'logformat_access.json',
    'html',
    topN=10,
    interval='5min',
    timeField='time'
)
```

기능:
- 백엔드 타겟 서버별 요청 그룹화 (target_ip:target_port)
- 대화형 체크박스 필터링
- 상태 코드 색상 코딩이 적용된 IP 그룹화

### 클라이언트 IP별 요청 분석

```python
# 클라이언트 소스 IP별 요청 분포 시각화
result = generateRequestPerClientIP(
    'access.log.gz',
    'logformat_access.json',
    'html',
    topN=20,
    interval='5min',
    timeField='time'
)
```

기능:
- 클라이언트 소스 IP별 요청 그룹화
- 대화형 체크박스 필터링
- 상태 코드 색상 코딩

## 바이트 전송 분석 (Byte Transfer Analysis)

### 전송 바이트 (Sent Bytes) 분석

```python
result = generateSentBytesPerURI(
    'access.log.gz',
    'logformat_access.json',
    'html',
    topN=20,
    interval='10min',
    patternsFile='patterns_access.json',
    timeField='time'
)
```

### 수신 바이트 (Received Bytes) 분석

```python
result = generateReceivedBytesPerURI(
    'access.log.gz',
    'logformat_access.json',
    'html',
    topN=20,
    interval='10min',
    patternsFile='patterns_access.json',
    timeField='time'
)
```

## 상태 코드 필터링 (Status Code Filtering)

### 상태 코드 범위로 필터링

```python
# 4xx 에러 필터링
filter_result = filterByCondition(
    'access.log.gz',
    'logformat_access.json',
    'statusCode',
    'statusCodes=4xx'
)

# 5xx 에러 필터링
filter_result = filterByCondition(
    'access.log.gz',
    'logformat_access.json',
    'statusCode',
    'statusCodes=5xx'
)
```

## 응답 시간 필터링 (Response Time Filtering)

### 응답 시간 임계값으로 필터링

```python
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

## 클라이언트 IP 필터링 (Client IP Filtering)

### 특정 클라이언트 IP로 필터링

```python
filter_result = filterByCondition(
    'access.log.gz',
    'logformat_access.json',
    'client',
    'clientIps=192.168.1.100,192.168.1.101,192.168.1.102'
)
```

## URI 패턴 필터링 (URI Pattern Filtering)

### URI 패턴으로 필터링

```python
# 특정 URI 패턴으로 필터링
filter_result = filterByCondition(
    'access.log.gz',
    'logformat_access.json',
    'uriPatterns',
    'patternsFile=patterns_access.json'
)
```

## 시간 필드 선택 (Time Field Selection)

대부분의 시각화 함수는 `timeField` 파라미터를 지원하여 다른 시간 필드 간에 선택할 수 있습니다:

```python
# 'time' 필드 사용 (기본값)
result = generateRequestPerURI(
    'access.log.gz',
    'logformat_access.json',
    'html',
    topN=20,
    interval='10min',
    timeField='time'
)

# 'request_creation_time' 필드 사용 (ALB 전용)
result = generateRequestPerURI(
    'access.log.gz',
    'logformat_access.json',
    'html',
    topN=20,
    interval='10min',
    timeField='request_creation_time'
)
```

## 패턴 파일 작업 (Working with Pattern Files)

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

모든 시각화 함수는 이제 로그 파일당 하나의 패턴 파일을 공유합니다:

- 파일 이름 포맷: `patterns_{log_name}.json`
  - 예: `access.log.gz`의 경우 `patterns_access.json`
- 다른 함수가 패턴을 추출할 때 패턴 규칙이 자동으로 병합됩니다.
- 수동으로 추가된 규칙은 병합 중에 보존됩니다.

### 패턴 추출 및 사용

```python
# 1. 패턴 추출 (patterns_access.json 생성)
patterns_result = extractUriPatterns(
    'access.log.gz',
    'logformat_access.json',
    'patterns',
    'maxPatterns=50'
)

# 2. 시각화에서 패턴 사용
viz_result = generateRequestPerURI(
    'access.log.gz',
    'logformat_access.json',
    'html',
    topN=20,
    interval='10s',
    patternsFile='patterns_access.json'
)

# 3. 또는 함수가 자동으로 패턴을 생성하도록 함
viz_result = generateRequestPerURI(
    'access.log.gz',
    'logformat_access.json',
    'html',
    topN=20,
    interval='10s'
    # patternsFile이 지정되지 않음 - 자동 생성됨
)
```

## 시간 간격 포맷팅 (Time Interval Formatting)

시간 간격은 자동 정규화와 함께 유연한 포맷을 지원합니다:

### 지원되는 포맷

- 초: `'10s'`, `'30s'`, `'30sec'` → `'30s'`
- 분: `'1m'`, `'5min'`, `'10m'` → `'1min'`, `'5min'`, `'10min'`
- 시간: `'1h'`, `'2hr'`, `'3hour'` → `'1h'`, `'2h'`, `'3h'`
- 일: `'1d'`, `'7day'` → `'1d'`, `'7d'`

### 예제

```python
# 이 모든 것이 작동합니다
generateRequestPerURI(..., interval='1m')
generateRequestPerURI(..., interval='10s')
generateRequestPerURI(..., interval='1h')
generateRequestPerURI(..., interval='30sec')  # '30s'로 정규화됨
```

## 대용량 파일을 위한 메모리 최적화 (Memory Optimization for Large Files)

### 컬럼 필터링 사용

```python
# 메모리 사용량을 줄이기 위해 필요한 컬럼만 로드
from data_parser import parse_log_file_with_format

df = parse_log_file_with_format(
    'large_access.log.gz',
    'logformat_access.json',
    columns_to_load=['time', 'request_url', 'status', 'target_processing_time']
)
# 메모리 사용량 80-90% 감소
```

### 대용량 파일을 위한 멀티프로세싱

```python
# 빠른 파싱을 위해 멀티프로세싱 활성화
df = parse_log_file_with_format(
    'large_access.log.gz',
    'logformat_access.json',
    use_multiprocessing=True,
    num_workers=8,  # 또는 자동 감지를 위해 None
    chunk_size=10000
)
# 멀티코어 시스템에서 3-4배 더 빠름
```

## 전체 분석 예제 (Complete Analysis Example)

```python
# ALB 로그 분석을 위한 전체 워크플로우

# 1. 포맷 감지
print("Step 1: Detecting log format...")
format_result = recommendAccessLogFormat("access.log.gz")
print(f"Format file: {format_result['logFormatFile']}")

# 2. URI 패턴 추출
print("\nStep 2: Extracting URI patterns...")
patterns_result = extractUriPatterns(
    "access.log.gz",
    format_result['logFormatFile'],
    'patterns',
    'maxPatterns=30'
)
print(f"Patterns file: {patterns_result['filePath']}")

# 3. 포괄적인 통계 계산
print("\nStep 3: Calculating statistics...")
stats_result = calculateStats(
    "access.log.gz",
    format_result['logFormatFile'],
    'statsType=url;processingTimeFields=request_processing_time,target_processing_time;sortBy=target_processing_time;sortMetric=p95;topN=20'
)
print(f"Stats file: {stats_result['filePath']}")

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
print(f"Visualization: {request_viz['filePath']}")

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
print(f"Processing time viz: {proctime_viz['filePath']}")

# 6. XLog 산점도 생성
print("\nStep 6: Generating XLog scatter plot...")
xlog_viz = generateXlog(
    "access.log.gz",
    format_result['logFormatFile'],
    'html'
)
print(f"XLog: {xlog_viz['filePath']}")

# 7. 다중 메트릭 대시보드 생성
print("\nStep 7: Generating dashboard...")
dashboard = generateMultiMetricDashboard(
    "access.log.gz",
    format_result['logFormatFile'],
    'html'
)
print(f"Dashboard: {dashboard['filePath']}")

print("\nAnalysis complete!")
```
