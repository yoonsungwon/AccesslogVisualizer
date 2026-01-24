# 처리 시간 통계 사용 가이드

`calculateStats` 함수의 처리 시간 통계 기능을 사용하는 방법을 설명합니다.

**관련 문서:**
- [API_REFERENCE.md](./API_REFERENCE.md) - calculateStats 함수 참조
- [MAIN_USAGE_EXAMPLES.md](./MAIN_USAGE_EXAMPLES.md) - CLI 사용 예제
- [WORKFLOWS.md](./WORKFLOWS.md) - 일반적인 워크플로우

## 개요

`calculateStats` 함수는 유연한 정렬 및 Top N 필터링과 함께 다중 처리 시간 필드 분석을 지원하도록 향상되었습니다.

## 주요 기능 (Key Features)

### 1. 다중 처리 시간 필드 (Multiple Processing Time Fields)
여러 타이밍 필드를 동시에 분석합니다:
- `request_processing_time`: 클라이언트로부터 요청을 받는 데 걸린 시간
- `target_processing_time`: 백엔드가 요청을 처리하는 데 걸린 시간
- `response_processing_time`: 클라이언트로 응답을 보내는 데 걸린 시간

### 2. 포괄적인 통계 (Comprehensive Statistics)
각 필드에 대해 다음 메트릭이 계산됩니다:
- **avg**: 평균값
- **sum**: 총합
- **median**: 50번째 백분위수 (중앙값)
- **std**: 표준 편차
- **min**: 최소값
- **max**: 최대값
- **p90**: 90번째 백분위수
- **p95**: 95번째 백분위수
- **p99**: 99번째 백분위수

### 3. 유연한 정렬 (Flexible Sorting)
모든 필드 및 메트릭 조합으로 결과를 정렬합니다:
- 필드별 정렬: 모든 처리 시간 필드 또는 'count'
- 메트릭별 정렬: 'avg', 'sum', 'median', 'p95', 'p99'

### 4. Top N 필터링 (Top N Filtering)
기준에 따라 상위 N개 URL만 가져옵니다.

## 사용 예제 (Usage Examples)

### 예제 1: 평균 요청 처리 시간 기준 상위 20개 URL

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

**파라미터:**
- `statsType=url`: URL 통계 계산
- `processingTimeFields=request_processing_time,target_processing_time,response_processing_time`: 세 필드 모두 분석
- `sortBy=request_processing_time`: 요청 처리 시간으로 정렬
- `sortMetric=avg`: 정렬에 평균 메트릭 사용
- `topN=20`: 상위 20개 URL만 반환

**출력 JSON 구조:**
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

### 예제 2: 타겟 처리 시간 합계 기준 상위 10개 URL

```python
result = calculateStats(
    inputFile='access.log.gz',
    logFormatFile='logformat_240101_120000.json',
    params='statsType=url;processingTimeFields=target_processing_time;sortBy=target_processing_time;sortMetric=sum;topN=10'
)
```

**사용 사례:** 총 백엔드 처리 시간을 가장 많이 소비하는 URL 찾기.

### 예제 3: P95 응답 처리 시간 기준 상위 15개 URL

```python
result = calculateStats(
    inputFile='access.log.gz',
    logFormatFile='logformat_240101_120000.json',
    params='statsType=url;processingTimeFields=response_processing_time;sortBy=response_processing_time;sortMetric=p95;topN=15'
)
```

**사용 사례:** 응답 전송 시간이 가장 느린 URL 찾기 (95번째 백분위수).

### 예제 4: 모든 처리 시간 필드, P99 기준 정렬

```python
result = calculateStats(
    inputFile='access.log.gz',
    logFormatFile='logformat_240101_120000.json',
    params='statsType=url;processingTimeFields=request_processing_time,target_processing_time,response_processing_time;sortBy=target_processing_time;sortMetric=p99;topN=25'
)
```

**사용 사례:** 최악의 백엔드 처리 시간을 가진 URL 찾기.

## 파라미터 참조 (Parameter Reference)

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
  - 로그의 모든 사용자 정의 처리 시간 필드
- **Example**: `processingTimeFields=request_processing_time,target_processing_time`

### sortBy
- **Type**: String (field name)
- **Options**: 모든 처리 시간 필드 이름, 또는 'count'
- **Default**: 'count'
- **Example**: `sortBy=target_processing_time`

### sortMetric
- **Type**: String
- **Options**: 'avg', 'sum', 'median', 'p90', 'p95', 'p99'
- **Default**: 'avg'
- **Example**: `sortMetric=p95`

### topN
- **Type**: Integer
- **Default**: None (모든 결과 반환)
- **Example**: `topN=20`

## 성능 고려 사항 (Performance Considerations)

### 멀티프로세싱 (Multiprocessing)
- 고유 URL이 100개 이상일 때 자동으로 활성화됨
- 대규모 데이터셋의 경우 훨씬 빠름
- `use_multiprocessing=False`로 비활성화 가능

### 예제 성능
- 데이터셋: 1,000,000 요청, 500 고유 URL
- 멀티프로세싱 미사용: ~30초
- 멀티프로세싱 사용 (8코어): ~10초

## 출력 해석 (Output Interpretation)

### 요약 텍스트 (Summary Text)
요약에는 상위 URL에 대한 처리 시간 세부 정보가 포함됩니다:

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

### JSON 출력
전체 통계는 모든 URL에 대한 전체 메트릭과 함께 `stats_YYMMDD_HHMMSS.json`에 저장됩니다.

## 일반적인 사용 사례 (Common Use Cases)

### 1. 백엔드 병목 현상 찾기
```python
# 평균 백엔드 처리 시간 기준 상위 URL
params='statsType=url;processingTimeFields=target_processing_time;sortBy=target_processing_time;sortMetric=avg;topN=20'
```

### 2. 총 시간 소비자 찾기
```python
# 총 처리 시간을 가장 많이 소비하는 URL
params='statsType=url;processingTimeFields=target_processing_time;sortBy=target_processing_time;sortMetric=sum;topN=10'
```

### 3. 최악의 시나리오 찾기
```python
# p99 처리 시간이 가장 높은 URL
params='statsType=url;processingTimeFields=request_processing_time,target_processing_time,response_processing_time;sortBy=target_processing_time;sortMetric=p99;topN=15'
```

### 4. 포괄적인 분석
```python
# 모든 필드, 모든 메트릭, 평균으로 정렬
params='statsType=url;processingTimeFields=request_processing_time,target_processing_time,response_processing_time;sortBy=target_processing_time;sortMetric=avg;topN=50'
```

## 다른 도구와의 통합 (Integration with Other Tools)

### 필터링과 체인 연결

```python
# 1. 상위 느린 URL 찾기
stats_result = calculateStats(
    'access.log.gz',
    'format.json',
    params='statsType=url;processingTimeFields=target_processing_time;sortBy=target_processing_time;sortMetric=avg;topN=10'
)

# 2. JSON에서 상위 URL 목록 추출
with open(stats_result['filePath'], 'r') as f:
    stats_data = json.load(f)
    top_urls = [stat['url'] for stat in stats_data['urlStats'][:10]]

# 3. 이 URL들에 대해 원본 로그 필터링
from data_processor import filterByCondition
# ... (URL 필터 파일 생성)
filtered_result = filterByCondition(
    'access.log.gz',
    'format.json',
    'urls',
    f'urlsFile={url_list_file}'
)

# 4. 느린 URL에 대해서만 시각화 생성
from data_visualizer import generateXlog
generateXlog(filtered_result['filePath'], 'format.json', 'html')
```

## 문제 해결 (Troubleshooting)

### 필드를 찾을 수 없음 (Field Not Found)
처리 시간 필드가 로그에 존재하지 않는 경우:
- 필드는 조용히 건너뜁니다.
- 다른 필드는 여전히 처리됩니다.
- 로그 포맷 파일의 필드 이름을 확인하세요.

### 결과 없음 (No Results)
통계가 반환되지 않는 경우:
- 필드 이름이 로그 포맷과 일치하는지 확인하세요.
- 숫자 변환이 성공했는지 확인하세요.
- 로그 포맷 파일 fieldMap을 검토하세요.

### 정렬이 작동하지 않음 (Sorting Not Working)
결과가 예상대로 정렬되지 않는 경우:
- sortBy 필드가 processingTimeFields에 존재하는지 확인하세요.
- sortMetric이 유효한지 확인하세요 ('avg', 'sum' 등).
- 필드에 데이터가 있는지 확인하세요 (모두 NaN이 아님).

## 버전 정보 (Version Information)
- **기능 추가**: 버전 2.0 (2025-01-11)
- **호환성**: pandas, numpy 필요
- **Python 버전**: 3.7+
