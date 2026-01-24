# API 참조

모든 MCP 도구 및 유틸리티 함수에 대한 전체 참조입니다.

**관련 문서:**
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 기술적 아키텍처
- [USAGE_EXAMPLES.md](./USAGE_EXAMPLES.md) - Python API 사용 예제
- [MCP_TOOL_REGISTRATION.md](./MCP_TOOL_REGISTRATION.md) - MCP 서버 등록 가이드

## data_parser 모듈

### recommendAccessLogFormat

로그 형식을 자동 감지하고 형식 파일을 생성합니다.

```python
def recommendAccessLogFormat(inputFile: str) -> Dict[str, Any]
```

**매개변수:**
- `inputFile` (str): 로그 파일 경로 (.gz 압축 지원)

**반환값:**
- 다음 키를 포함하는 딕셔너리:
  - `logFormatFile` (str): 생성된 `logformat_*.json`의 절대 경로
  - `patternType` (str): 감지된 형식 유형 ('ALB', 'HTTPD', 'NGINX', 'JSON', 'GROK')
  - `confidence` (float): 신뢰도 점수 (0.0-1.0)
  - `successRate` (float): 파싱 성공률 (0.0-1.0)
  - `fieldMap` (dict): 필드 매핑 딕셔너리

**예시:**
```python
result = recommendAccessLogFormat("access.log.gz")
# 반환값: {
#   'logFormatFile': '/path/to/logformat_access.json',
#   'patternType': 'ALB',
#   'confidence': 0.95,
#   'successRate': 1.0,
#   'fieldMap': {...}
# }
```

### parse_log_file_with_format

선택적 병렬 처리 및 메모리 최적화를 사용하여 로그 파일을 파싱합니다.

```python
def parse_log_file_with_format(
    inputFile: str,
    logFormatFile: str,
    use_multiprocessing: bool = None,
    num_workers: int = None,
    chunk_size: int = None,
    columns_to_load: List[str] = None
) -> pd.DataFrame
```

**매개변수:**
- `inputFile` (str): 로그 파일 경로
- `logFormatFile` (str): 형식 파일 경로
- `use_multiprocessing` (bool, 선택): 병렬 처리 활성화 (기본값: config.yaml 설정)
- `num_workers` (int, 선택): 작업자 프로세스 수 (기본값: 자동 감지)
- `chunk_size` (int, 선택): 청크 당 라인 수 (기본값: config.yaml 설정)
- `columns_to_load` (List[str], 선택): 지정된 컬럼만 로드 (메모리 사용량 감소)

**반환값:**
- `pd.DataFrame`: 파싱된 로그 데이터

**예시:**
```python
# 기본 파싱
df = parse_log_file_with_format("access.log.gz", "logformat_access.json")

# 메모리 최적화 사용
df = parse_log_file_with_format(
    "access.log.gz",
    "logformat_access.json",
    columns_to_load=['time', 'request_url', 'status']
)

# 병렬 처리 사용
df = parse_log_file_with_format(
    "large_access.log.gz",
    "logformat_access.json",
    use_multiprocessing=True,
    num_workers=8
)
```

## data_processor 모듈

### filterByCondition

다양한 조건으로 로그 데이터를 필터링합니다.

```python
def filterByCondition(
    inputFile: str,
    logFormatFile: str,
    condition: str,
    params: str = ''
) -> Dict[str, Any]
```

**매개변수:**
- `inputFile` (str): 로그 파일 경로
- `logFormatFile` (str): 형식 파일 경로
- `condition` (str): 필터 유형 - `'time'`, `'statusCode'`, `'responseTime'`, `'client'`, `'urls'`, `'uriPatterns'`
- `params` (str): 세미콜론으로 구분된 매개변수

**조건별 매개변수:**

**time (시간):**
- `startTime` (str): 시작 시간 (ISO 8601 형식)
- `endTime` (str): 종료 시간 (ISO 8601 형식)

**statusCode (상태 코드):**
- `statusCodes` (str): 상태 코드 그룹 (예: `'4xx,5xx'`, `'200,201'`, `'500'`)

**responseTime (응답 시간):**
- `minTime` (float): 최소 응답 시간 (초)
- `maxTime` (float): 최대 응답 시간 (초)

**client (클라이언트 IP):**
- `clientIps` (str): 쉼표로 구분된 IP 주소 목록 (CIDR 표기법 지원, 예: `'192.168.1.1,10.0.0.0/8'`)

**urls (URL):**
- `urlsFile` (str): URL 목록이 있는 JSON 파일 경로

**uriPatterns (URI 패턴):**
- `patternsFile` (str): 패턴 파일 경로

**반환값:**
- 다음 키를 포함하는 딕셔너리:
  - `filePath` (str): 필터링된 출력 파일의 절대 경로 (`filtered_*.log`)
  - `totalLines` (int): 필터링된 라인 수
  - `condition` (str): 사용된 필터 조건
  - `params` (dict): 필터 매개변수

**예시:**
```python
# 시간 범위로 필터링
result = filterByCondition(
    "access.log.gz",
    "logformat_access.json",
    "time",
    "startTime=2024-08-08T09:00:00;endTime=2024-08-08T10:00:00"
)

# 상태 코드로 필터링
result = filterByCondition(
    "access.log.gz",
    "logformat_access.json",
    "statusCode",
    "statusCodes=5xx"
)

# 응답 시간으로 필터링
result = filterByCondition(
    "access.log.gz",
    "logformat_access.json",
    "responseTime",
    "minTime=1.0"
)

# 클라이언트 IP로 필터링
result = filterByCondition(
    "access.log.gz",
    "logformat_access.json",
    "client",
    "clientIps=192.168.1.100,192.168.1.101"
)
```

### extractUriPatterns

고유 URL 또는 일반화된 URI 패턴을 추출합니다.

```python
def extractUriPatterns(
    inputFile: str,
    logFormatFile: str,
    extractionType: str,
    params: str = ''
) -> Dict[str, Any]
```

**매개변수:**
- `inputFile` (str): 로그 파일 경로
- `logFormatFile` (str): 형식 파일 경로
- `extractionType` (str): 고유 URL의 경우 `'urls'`, 일반화된 패턴의 경우 `'patterns'`
- `params` (str): 세미콜론으로 구분된 매개변수

**매개변수:**
- `maxPatterns` (int): 추출할 최대 패턴 수 (기본값: 20)

**반환값:**
- 다음 키를 포함하는 딕셔너리:
  - `filePath` (str): 출력 파일의 절대 경로 (`patterns_{log_name}.json`)
  - `extractionType` (str): 추출 유형
  - `totalPatterns` (int): 추출된 패턴 수
  - `patternRules` (list): 패턴 규칙 목록

**예시:**
```python
result = extractUriPatterns(
    "access.log.gz",
    "logformat_access.json",
    "patterns",
    "maxPatterns=30"
)
# 반환값: {
#   'filePath': '/path/to/patterns_access.json',
#   'extractionType': 'patterns',
#   'totalPatterns': 30,
#   'patternRules': [...]
# }
```

### calculateStats

선택적 병렬 처리를 사용하여 포괄적인 통계를 계산합니다.

```python
def calculateStats(
    inputFile: str,
    logFormatFile: str,
    params: str = '',
    use_multiprocessing: bool = None,
    num_workers: int = None
) -> Dict[str, Any]
```

**매개변수:**
- `inputFile` (str): 로그 파일 경로
- `logFormatFile` (str): 형식 파일 경로
- `params` (str): 세미콜론으로 구분된 매개변수
- `use_multiprocessing` (bool, 선택): 병렬 처리 활성화 (기본값: config.yaml 설정)
- `num_workers` (int, 선택): 작업자 프로세스 수 (기본값: 자동 감지)

**매개변수:**
- `statsType` (str): `'overall'`, `'url'`, `'timeseries'`, `'ip'`
- `timeInterval` (str): 시간 간격 (예: `'1m'`, `'10s'`, `'1h'`)
- `processingTimeFields` (str): 쉼표로 구분된 처리 시간 필드 목록
- `sortBy` (str): 정렬 기준 필드 (`topN`용)
- `sortMetric` (str): 정렬 기준 메트릭 - `'avg'`, `'sum'`, `'median'`, `'p95'`, `'p99'`
- `topN` (int): 상위 N개 결과만 반환

**반환값:**
- 다음 키를 포함하는 딕셔너리:
  - `filePath` (str): 통계 파일의 절대 경로 (`stats_*.json`)
  - `statsType` (str): 통계 유형
  - `summary` (str): 사람이 읽을 수 있는 요약
  - `statistics` (dict): 상세 통계

**예시:**
```python
# 전체 통계
result = calculateStats(
    "access.log.gz",
    "logformat_access.json",
    "statsType=overall"
)

# 처리 시간 분석을 포함한 URL 통계
result = calculateStats(
    "access.log.gz",
    "logformat_access.json",
    "statsType=url;processingTimeFields=request_processing_time,target_processing_time"
)

# p95 처리 시간 기준 상위 20개 URL
result = calculateStats(
    "access.log.gz",
    "logformat_access.json",
    "statsType=url;processingTimeFields=target_processing_time;sortBy=target_processing_time;sortMetric=p95;topN=20"
)

# 시계열 통계
result = calculateStats(
    "access.log.gz",
    "logformat_access.json",
    "statsType=timeseries;timeInterval=10min"
)

# IP 통계
result = calculateStats(
    "access.log.gz",
    "logformat_access.json",
    "statsType=ip"
)
```

## data_visualizer 모듈

### generateXlog

응답 시간 산점도(Xlog)를 생성합니다.

```python
def generateXlog(
    inputFile: str,
    logFormatFile: str,
    outputFormat: str = 'html',
    timeField: str = 'time'
) -> Dict[str, Any]
```

**매개변수:**
- `inputFile` (str): 로그 파일 경로
- `logFormatFile` (str): 형식 파일 경로
- `outputFormat` (str): 출력 형식 (`'html'`만 지원)
- `timeField` (str): 사용할 시간 필드 (`'time'` 또는 `'request_creation_time'`)

**반환값:**
- 다음 키를 포함하는 딕셔너리:
  - `filePath` (str): HTML 파일의 절대 경로 (`xlog_*.html`)
  - `totalTransactions` (int): 플롯된 트랜잭션 수

**예시:**
```python
result = generateXlog(
    "access.log.gz",
    "logformat_access.json",
    "html",
    timeField="time"
)
```

### generateRequestPerURI

URI별 요청 수 시계열 차트를 생성합니다.

```python
def generateRequestPerURI(
    inputFile: str,
    logFormatFile: str,
    outputFormat: str = 'html',
    topN: int = 20,
    interval: str = '10min',
    patternsFile: str = None,
    timeField: str = 'time'
) -> Dict[str, Any]
```

**매개변수:**
- `inputFile` (str): 로그 파일 경로
- `logFormatFile` (str): 형식 파일 경로
- `outputFormat` (str): 출력 형식 (`'html'`만 지원)
- `topN` (int): 표시할 상위 URI 수 (기본값: 20)
- `interval` (str): 시간 간격 (예: `'1m'`, `'10s'`, `'1h'`) (기본값: '10min')
- `patternsFile` (str, 선택): 패턴 파일 경로 (지정하지 않으면 자동 생성)
- `timeField` (str): 사용할 시간 필드 (기본값: 'time')

**반환값:**
- 다음 키를 포함하는 딕셔너리:
  - `filePath` (str): HTML 파일의 절대 경로 (`requestcnt_*.html`)
  - `totalTransactions` (int): 총 트랜잭션 수
  - `topN` (int): 표시된 URI 수

**예시:**
```python
result = generateRequestPerURI(
    "access.log.gz",
    "logformat_access.json",
    "html",
    topN=30,
    interval="5min",
    patternsFile="patterns_access.json",
    timeField="time"
)
```

### generateRequestPerTarget

타겟별 요청 수 시계열 차트를 생성합니다.

```python
def generateRequestPerTarget(
    inputFile: str,
    logFormatFile: str,
    outputFormat: str = 'html',
    topN: int = 10,
    interval: str = '10min',
    timeField: str = 'time'
) -> Dict[str, Any]
```

**매개변수:**
- `inputFile` (str): 로그 파일 경로
- `logFormatFile` (str): 형식 파일 경로
- `outputFormat` (str): 출력 형식 (`'html'`만 지원)
- `topN` (int): 표시할 상위 타겟 수 (기본값: 10)
- `interval` (str): 시간 간격 (기본값: '10min')
- `timeField` (str): 사용할 시간 필드 (기본값: 'time')

**반환값:**
- 다음 키를 포함하는 딕셔너리:
  - `filePath` (str): HTML 파일의 절대 경로 (`requestcnt_target_*.html`)
  - `totalTransactions` (int): 총 트랜잭션 수
  - `topN` (int): 표시된 타겟 수

**예시:**
```python
result = generateRequestPerTarget(
    "access.log.gz",
    "logformat_access.json",
    "html",
    topN=10,
    interval="5min"
)
```

### generateRequestPerClientIP

클라이언트 IP별 요청 수 시계열 차트를 생성합니다.

```python
def generateRequestPerClientIP(
    inputFile: str,
    logFormatFile: str,
    outputFormat: str = 'html',
    topN: int = 20,
    interval: str = '10min',
    timeField: str = 'time'
) -> Dict[str, Any]
```

**매개변수:**
- `inputFile` (str): 로그 파일 경로
- `logFormatFile` (str): 형식 파일 경로
- `outputFormat` (str): 출력 형식 (`'html'`만 지원)
- `topN` (int): 표시할 상위 클라이언트 IP 수 (기본값: 20)
- `interval` (str): 시간 간격 (기본값: '10min')
- `timeField` (str): 사용할 시간 필드 (기본값: 'time')

**반환값:**
- 다음 키를 포함하는 딕셔너리:
  - `filePath` (str): HTML 파일의 절대 경로 (`requestcnt_clientip_*.html`)
  - `totalTransactions` (int): 총 트랜잭션 수
  - `topN` (int): 표시된 클라이언트 IP 수

**예시:**
```python
result = generateRequestPerClientIP(
    "access.log.gz",
    "logformat_access.json",
    "html",
    topN=20,
    interval="5min"
)
```

### generateProcessingTimePerURI

URI별 처리 시간 시계열 차트를 생성합니다.

```python
def generateProcessingTimePerURI(
    inputFile: str,
    logFormatFile: str,
    outputFormat: str = 'html',
    processingTimeField: str = 'target_processing_time',
    metric: str = 'avg',
    topN: int = 20,
    interval: str = '10min',
    patternsFile: str = None,
    timeField: str = 'time'
) -> Dict[str, Any]
```

**매개변수:**
- `inputFile` (str): 로그 파일 경로
- `logFormatFile` (str): 형식 파일 경로
- `outputFormat` (str): 출력 형식 (`'html'`만 지원)
- `processingTimeField` (str): 분석할 처리 시간 필드 (기본값: 'target_processing_time')
  - 옵션: `'request_processing_time'`, `'target_processing_time'`, `'response_processing_time'`
- `metric` (str): 계산할 메트릭 (기본값: 'avg')
  - 옵션: `'avg'`, `'sum'`, `'median'`, `'p95'`, `'p99'`, `'max'`
- `topN` (int): 표시할 상위 URI 수 (기본값: 20)
- `interval` (str): 시간 간격 (기본값: '10min')
- `patternsFile` (str, 선택): 패턴 파일 경로
- `timeField` (str): 사용할 시간 필드 (기본값: 'time')

**반환값:**
- 다음 키를 포함하는 딕셔너리:
  - `filePath` (str): HTML 파일의 절대 경로
  - `totalTransactions` (int): 총 트랜잭션 수
  - `topN` (int): 표시된 URI 수
  - `metric` (str): 사용된 메트릭

**예시:**
```python
result = generateProcessingTimePerURI(
    "access.log.gz",
    "logformat_access.json",
    "html",
    processingTimeField="target_processing_time",
    metric="p95",
    topN=20,
    interval="10min",
    patternsFile="patterns_access.json"
)
```

### generateSentBytesPerURI

URI별 전송 바이트(Sent Bytes) 시계열 차트를 생성합니다.

```python
def generateSentBytesPerURI(
    inputFile: str,
    logFormatFile: str,
    outputFormat: str = 'html',
    topN: int = 20,
    interval: str = '10min',
    patternsFile: str = None,
    timeField: str = 'time'
) -> Dict[str, Any]
```

**매개변수:**
- `generateRequestPerURI`와 동일

**반환값:**
- `generateRequestPerURI`와 동일한 구조

### generateReceivedBytesPerURI

URI별 수신 바이트(Received Bytes) 시계열 차트를 생성합니다.

```python
def generateReceivedBytesPerURI(
    inputFile: str,
    logFormatFile: str,
    outputFormat: str = 'html',
    topN: int = 20,
    interval: str = '10min',
    patternsFile: str = None,
    timeField: str = 'time'
) -> Dict[str, Any]
```

**매개변수:**
- `generateRequestPerURI`와 동일

**반환값:**
- `generateRequestPerURI`와 동일한 구조

### generateMultiMetricDashboard

포괄적인 다중 지표 대시보드를 생성합니다.

```python
def generateMultiMetricDashboard(
    inputFile: str,
    logFormatFile: str,
    outputFormat: str = 'html',
    timeField: str = 'time'
) -> Dict[str, Any]
```

**매개변수:**
- `inputFile` (str): 로그 파일 경로
- `logFormatFile` (str): 형식 파일 경로
- `outputFormat` (str): 출력 형식 (`'html'`만 지원)
- `timeField` (str): 사용할 시간 필드 (기본값: 'time')

**반환값:**
- 다음 키를 포함하는 딕셔너리:
  - `filePath` (str): HTML 파일의 절대 경로 (`dashboard_*.html`)
  - `totalTransactions` (int): 총 트랜잭션 수

**예시:**
```python
result = generateMultiMetricDashboard(
    "access.log.gz",
    "logformat_access.json",
    "html"
)
```

## core.utils 모듈

### FieldMapper

대체 대안을 포함한 스마트 필드 매핑.

#### find_field

```python
@staticmethod
def find_field(df: pd.DataFrame, field_name: str, format_info: Dict) -> str
```

**매개변수:**
- `df` (pd.DataFrame): 검색할 DataFrame
- `field_name` (str): 찾을 표준 필드 이름
- `format_info` (Dict): `fieldMap`을 포함한 형식 정보

**반환값:**
- `str`: DataFrame의 실제 컬럼 이름

**예외:**
- `ValidationError`: 필드를 찾을 수 없는 경우

**예시:**
```python
from core.utils import FieldMapper

time_field = FieldMapper.find_field(df, 'time', format_info)
# 반환값: 'time'을 찾을 수 없지만 'timestamp'가 존재하는 경우 'timestamp'
```

#### map_fields

```python
@staticmethod
def map_fields(df: pd.DataFrame, format_info: Dict) -> Dict[str, str]
```

**매개변수:**
- `df` (pd.DataFrame): 매핑할 DataFrame
- `format_info` (Dict): 형식 정보

**반환값:**
- `Dict[str, str]`: 표준 필드 이름에서 실제 컬럼 이름으로의 매핑

**예시:**
```python
field_map = FieldMapper.map_fields(df, format_info)
# 반환값: {'timestamp': 'time', 'url': 'request_url', ...}
```

#### validate_required_fields

```python
@staticmethod
def validate_required_fields(
    df: pd.DataFrame,
    format_info: Dict,
    required_fields: List[str]
) -> None
```

**매개변수:**
- `df` (pd.DataFrame): 검증할 DataFrame
- `format_info` (Dict): 형식 정보
- `required_fields` (List[str]): 필수 필드 이름 목록

**예외:**
- `ValidationError`: 필수 필드가 누락된 경우

**예시:**
```python
FieldMapper.validate_required_fields(df, format_info, ['time', 'url', 'status'])
```

### ParamParser

타입 안전(Type-safe) 매개변수 파싱.

#### parse

```python
@staticmethod
def parse(params: str) -> Dict[str, str]
```

**매개변수:**
- `params` (str): 세미콜론으로 구분된 매개변수 (예: `'key1=value1;key2=value2'`)

**반환값:**
- `Dict[str, str]`: 파싱된 매개변수

**예시:**
```python
from core.utils import ParamParser

parsed = ParamParser.parse("startTime=2024-01-01;endTime=2024-12-31;topN=20")
# 반환값: {'startTime': '2024-01-01', 'endTime': '2024-12-31', 'topN': '20'}
```

#### get

```python
@staticmethod
def get(params: str, key: str, default: Any = None, required: bool = False) -> str
```

**매개변수:**
- `params` (str): 세미콜론으로 구분된 매개변수
- `key` (str): 검색할 매개변수 키
- `default` (Any, 선택): 키를 찾을 수 없는 경우의 기본값
- `required` (bool): 키를 찾을 수 없는 경우 오류 발생 여부 (기본값: False)

**반환값:**
- `str`: 매개변수 값

**예외:**
- `ValidationError`: 필수 매개변수가 누락된 경우

**예시:**
```python
start_time = ParamParser.get("startTime=2024-01-01", "startTime", required=True)
```

#### get_int

```python
@staticmethod
def get_int(params: str, key: str, default: int = None) -> int
```

**매개변수:**
- `params` (str): 세미콜론으로 구분된 매개변수
- `key` (str): 검색할 매개변수 키
- `default` (int, 선택): 키를 찾을 수 없는 경우의 기본값

**반환값:**
- `int`: 정수형 매개변수 값

**예시:**
```python
top_n = ParamParser.get_int("topN=20", "topN", default=10)
# 반환값: 20
```

#### get_float

```python
@staticmethod
def get_float(params: str, key: str, default: float = None) -> float
```

**매개변수:**
- `params` (str): 세미콜론으로 구분된 매개변수
- `key` (str): 검색할 매개변수 키
- `default` (float, 선택): 키를 찾을 수 없는 경우의 기본값

**반환값:**
- `float`: 실수형 매개변수 값

**예시:**
```python
min_time = ParamParser.get_float("minTime=1.5", "minTime", default=0.0)
# 반환값: 1.5
```

#### get_bool

```python
@staticmethod
def get_bool(params: str, key: str, default: bool = False) -> bool
```

**매개변수:**
- `params` (str): 세미콜론으로 구분된 매개변수
- `key` (str): 검색할 매개변수 키
- `default` (bool, 선택): 키를 찾을 수 없는 경우의 기본값

**반환값:**
- `bool`: 불리언형 매개변수 값

**예시:**
```python
enabled = ParamParser.get_bool("enabled=true", "enabled", default=False)
# 반환값: True
```

#### get_list

```python
@staticmethod
def get_list(params: str, key: str, separator: str = ',', default: List = None) -> List[str]
```

**매개변수:**
- `params` (str): 세미콜론으로 구분된 매개변수
- `key` (str): 검색할 매개변수 키
- `separator` (str): 리스트 항목 구분자 (기본값: ',')
- `default` (List, 선택): 키를 찾을 수 없는 경우의 기본값

**반환값:**
- `List[str]`: 리스트형 매개변수 값

**예시:**
```python
ips = ParamParser.get_list("ips=192.168.1.1,192.168.1.2", "ips", separator=',')
# 반환값: ['192.168.1.1', '192.168.1.2']
```

### MultiprocessingConfig

멀티프로세싱 구성 관리.

#### get_config

```python
@staticmethod
def get_config() -> Dict[str, Any]
```

**반환값:**
- `Dict[str, Any]`: config.yaml에서 가져온 멀티프로세싱 구성

**예시:**
```python
from core.utils import MultiprocessingConfig

config = MultiprocessingConfig.get_config()
# 반환값: {'enabled': True, 'num_workers': None, 'chunk_size': 10000, ...}
```

#### get_optimal_workers

```python
@staticmethod
def get_optimal_workers(data_size: int = None) -> int
```

**매개변수:**
- `data_size` (int, 선택): 처리할 데이터 크기

**반환값:**
- `int`: 최적의 작업자 프로세스 수

**예시:**
```python
workers = MultiprocessingConfig.get_optimal_workers(data_size=100000)
# 반환값: 8 (8코어 시스템의 경우)
```

#### should_use_multiprocessing

```python
@staticmethod
def should_use_multiprocessing(data_size: int) -> bool
```

**매개변수:**
- `data_size` (int): 처리할 데이터 크기

**반환값:**
- `bool`: 멀티프로세싱 사용 여부

**예시:**
```python
use_mp = MultiprocessingConfig.should_use_multiprocessing(data_size=15000)
# 반환값: True (data_size >= min_lines_for_parallel 인 경우)
```

#### get_processing_params

```python
@staticmethod
def get_processing_params(
    use_multiprocessing: bool = None,
    num_workers: int = None,
    chunk_size: int = None,
    data_size: int = None
) -> Dict[str, Any]
```

**매개변수:**
- `use_multiprocessing` (bool, 선택): 구성 설정 재정의
- `num_workers` (int, 선택): 구성 설정 재정의
- `chunk_size` (int, 선택): 구성 설정 재정의
- `data_size` (int, 선택): 자동 구성을 위한 데이터 크기

**반환값:**
- `Dict[str, Any]`: 전체 처리 매개변수

**예시:**
```python
params = MultiprocessingConfig.get_processing_params(data_size=50000)
# 반환값: {'use_multiprocessing': True, 'num_workers': 8, 'chunk_size': 10000}
```

## core.exceptions 모듈

### 사용자 정의 예외 (Custom Exceptions)

모든 사용자 정의 예외는 `LogAnalyzerError`를 상속합니다.

```python
from core.exceptions import (
    LogAnalyzerError,        # 기본 예외
    FileNotFoundError,       # 파일을 찾을 수 없음
    InvalidFormatError,      # 잘못된 로그 형식
    ParseError,              # 라인 컨텍스트가 포함된 파싱 오류
    ValidationError,         # 검증 오류
    ConfigurationError       # 구성 오류
)

# 사용법
raise ValidationError('topN', 'Must be a positive integer')
raise FileNotFoundError('/path/to/file.log')
```

## core.logging_config 모듈

### get_logger

```python
def get_logger(name: str) -> logging.Logger
```

**매개변수:**
- `name` (str): 로거 이름 (보통 `__name__`)

**반환값:**
- `logging.Logger`: 구성된 로거 인스턴스

**예시:**
```python
from core.logging_config import get_logger

logger = get_logger(__name__)
logger.info("Processing log file...")
logger.warning("Large file detected")
logger.error("Parse failed")
```

### enable_file_logging

```python
def enable_file_logging() -> None
```

`logs/access_log_analyzer_YYYYMMDD.log`에 파일 로깅을 활성화합니다.

**예시:**
```python
from core.logging_config import enable_file_logging

enable_file_logging()
```

### set_log_level

```python
def set_log_level(level: str) -> None
```

**매개변수:**
- `level` (str): 로그 레벨 - `'DEBUG'`, `'INFO'`, `'WARNING'`, `'ERROR'`, `'CRITICAL'`

**예시:**
```python
from core.logging_config import set_log_level

set_log_level('DEBUG')
```

## core.config 모듈

### ConfigManager

중앙 집중식 구성 관리를 위한 싱글톤 클래스입니다.

```python
from core.config import ConfigManager

config_mgr = ConfigManager()

# 구성 로드
config = config_mgr.load_config()

# 기본값으로 값 가져오기
port = config_mgr.get('server.port', default=8080)

# 강제 다시 로드
config_mgr.reload()
```
