# Access Log Analyzer - 사용 예제

이 문서는 Access Log Analyzer의 Python API 사용 예제를 제공합니다. 기본 사용법은 `README.md`를 참조하세요.

## Python API 사용 예제

### 예제 1: 로그 포맷 자동 감지

```python
from data_parser import recommendAccessLogFormat

# 로그 포맷 자동 감지
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
print(f"Output: {result['filePath']}")
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
print(f"Output: {result['filePath']}")
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
print(stats['summary'])
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
print("\nOpen the HTML file in your browser to view the interactive chart.")
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

print(f"Statistics: {stats['filePath']}")
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

## 고급 사용 시나리오

### 시나리오 1: 응답시간 평균 Top 5 URL 분석

```python
from data_parser import recommendAccessLogFormat
from data_processor import filterByCondition, calculateStats
from data_visualizer import generateXlog
import json
from pathlib import Path

# 1. 포맷 감지
format_result = recommendAccessLogFormat('access.log.gz')
log_format_file = format_result['logFormatFile']

# 2. URL별 통계 계산
stats_result = calculateStats('access.log.gz', log_format_file, 'statsType=url')

# 3. Top 5 URL 추출
with open(stats_result['filePath'], 'r') as f:
    stats = json.load(f)

url_stats_sorted = sorted(
    [s for s in stats.get('urlStats', []) if 'responseTime' in s],
    key=lambda x: x['responseTime']['avg'],
    reverse=True
)[:5]

top_urls = [s['url'] for s in url_stats_sorted]

print("Top 5 slowest URLs:")
for i, url in enumerate(top_urls, 1):
    avg_rt = next(s['responseTime']['avg'] for s in url_stats_sorted if s['url'] == url)
    print(f"  {i}. {url} (avg: {avg_rt:.2f})")

# 4. Top 5 URL로 필터링
urls_file = Path('access.log.gz').parent / 'top5_urls.json'
with open(urls_file, 'w') as f:
    json.dump({'urls': top_urls}, f)

filter_result = filterByCondition(
    'access.log.gz',
    log_format_file,
    'urls',
    f'urlsFile={urls_file}'
)

# 5. XLog 생성
xlog_result = generateXlog(filter_result['filePath'], log_format_file, 'html')

print(f"\nXLog for top 5 slowest URLs: {xlog_result['filePath']}")
```

### 시나리오 2: 특정 시간대 에러 분석

```python
from data_parser import recommendAccessLogFormat
from data_processor import filterByCondition, extractUriPatterns, calculateStats
from data_visualizer import generateRequestPerURI

# 1. 포맷 감지
format_result = recommendAccessLogFormat('access.log.gz')
log_format_file = format_result['logFormatFile']

# 2. 시간 필터링
time_filtered = filterByCondition(
    'access.log.gz',
    log_format_file,
    'time',
    'startTime=2024-10-23T09:00:00;endTime=2024-10-23T10:00:00'
)

# 3. 에러만 필터링
error_filtered = filterByCondition(
    time_filtered['filePath'],
    log_format_file,
    'statusCode',
    'statusCodes=5xx'
)

# 4. URI 패턴 추출
patterns = extractUriPatterns(
    error_filtered['filePath'],
    log_format_file,
    'patterns',
    'maxPatterns=20'
)

print(f"Error patterns found: {patterns['patternsFound']}")

# 5. 통계 계산
stats = calculateStats(
    error_filtered['filePath'],
    log_format_file,
    'statsType=all;timeInterval=5m'
)

print(f"\nDetailed statistics: {stats['filePath']}")
print(stats['summary'])

# 6. Request Count 그래프 생성
chart = generateRequestPerURI(
    error_filtered['filePath'],
    log_format_file,
    'html'
)

print(f"\nRequest count chart: {chart['filePath']}")
```

## 팁과 트릭

### Tip 1: Glob 패턴으로 여러 파일 처리

여러 로그 파일을 한 번에 처리하려면 먼저 파일을 병합하거나, 각 파일을 순차적으로 처리하세요.

### Tip 2: 결과 파일 재사용

필터링이나 처리 결과 파일(`filtered_*.log`)은 다음 단계의 입력으로 바로 사용할 수 있습니다.

### Tip 3: JSON 출력 파일 분석

통계나 URL 목록은 JSON 형식으로 저장되므로, 다른 도구나 스크립트에서 쉽게 읽어서 추가 처리할 수 있습니다.

### Tip 4: 시간 범위 형식

시간 범위는 ISO 8601 형식을 사용합니다:
- `2024-10-23T09:00:00`
- `2024-10-23T09:00:00+09:00` (타임존 지정)

### Tip 5: 응답시간 단위

응답시간은 다양한 단위를 지원합니다:
- `500ms` (밀리초)
- `0.5s` (초)
- `500000us` (마이크로초)

## 문제 해결

### 문제: "No valid lines found in file"

**원인**: 로그 파일이 비어있거나 압축 형식이 잘못되었습니다.

**해결**: 
```bash
# 파일 내용 확인
zcat access.log.gz | head -10
```

### 문제: "Pattern Type: GROK, Confidence: 10%"

**원인**: 로그 포맷을 자동 감지하지 못했습니다.

**해결**: 로그 포맷을 수동으로 지정하거나, 로그 샘플을 확인하여 지원 여부를 검토하세요.

### 문제: "No data to visualize"

**원인**: 필터링 결과가 비어있거나, 필수 필드(time, responseTime 등)가 누락되었습니다.

**해결**: 
1. 필터링 조건을 완화하세요.
2. 로그 포맷 파일을 확인하여 필드 매핑이 올바른지 검토하세요.

## 추가 리소스

- **기본 문서**: `README.md` - 프로젝트 개요 및 빠른 시작
- **설계 문서**: `AccessLogAnalyzer.md` - 아키텍처 및 MCP 도구 상세 설명
- **API 문서**: 각 Python 파일의 docstring 참조

