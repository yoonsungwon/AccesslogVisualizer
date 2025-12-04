# 설정 가이드 (Configuration Guide)

## config.yaml 구조

config.yaml 파일은 포맷별 섹션을 통해 여러 로그 포맷 유형을 지원합니다.

### 전역 설정 (Global Settings)

```yaml
# Global settings
version: '1.0'
```

## 멀티프로세싱 구성 (Multiprocessing Configuration)

시스템은 대용량 로그 파일의 빠른 분석을 위해 병렬 처리를 지원합니다.

### 구성 옵션

```yaml
multiprocessing:
  enabled: true              # 멀티프로세싱 전역 활성화 또는 비활성화
  num_workers: null          # null = 자동 감지, 또는 숫자 지정 (예: 4, 8)
  chunk_size: 10000          # 청크 당 처리되는 라인/항목 수
  min_lines_for_parallel: 10000  # 병렬 처리를 트리거할 최소 라인 수
```

### 파라미터 설명

- **enabled**: 멀티프로세싱 전역 활성화 또는 비활성화 (기본값: `true`)
- **num_workers**: 작업자 프로세스 수
  - `null` (기본값): CPU 코어 및 워크로드에 따라 자동 감지
  - 특정 숫자: 고정된 수의 작업자 사용 (예: `4`, `8`)
- **chunk_size**: 청크 당 처리되는 라인/항목 수 (기본값: `10000`)
  - 더 큰 청크 = 오버헤드 감소, 병렬성 감소
  - 더 작은 청크 = 오버헤드 증가, 부하 분산 개선
- **min_lines_for_parallel**: 병렬 처리를 트리거할 최소 라인 수 (기본값: `10000`)
  - 이보다 작은 파일은 순차 처리를 사용합니다.

### 멀티프로세싱 사용 시점

1. **로그 파싱** (`parse_log_file_with_format`):
   - 파일 라인 수가 `>= min_lines_for_parallel`일 때 트리거됨 (기본값: 10,000)
   - 전체 파일을 읽고 청크로 분할하여 병렬로 파싱
   - 성능 향상: 8코어 시스템에서 약 3-4배

2. **통계 계산** (`calculateStats`):
   - **URL 통계**: 고유 URL이 100개 이상일 때 트리거됨
   - **시계열 통계**: 시간 간격이 100개 이상일 때 트리거됨
   - **IP 통계**: 고유 IP가 100개 이상일 때 트리거됨
   - 성능 향상: 대규모 데이터셋의 경우 약 2-3배

### 성능 팁

- **CPU 바운드 워크로드**: `num_workers`를 CPU 코어 수로 설정
- **I/O 바운드 워크로드**: 코어 수보다 많은 작업자를 사용할 수 있음
- **메모리 제약**: 메모리가 부족한 경우 `chunk_size` 또는 `num_workers` 줄이기
- **작은 파일**: 멀티프로세싱 오버헤드로 인해 처리가 느려질 수 있음; `min_lines_for_parallel` 조정

### 멀티프로세싱 비활성화

#### 설정 파일을 통해:
```yaml
multiprocessing:
  enabled: false  # 모든 병렬 처리 비활성화
```

#### 함수 파라미터를 통해:
```python
# 특정 호출에 대해 비활성화
parse_log_file_with_format(file, format, use_multiprocessing=False)
calculateStats(file, format, params, use_multiprocessing=False)
```

## 로그 포맷 구성 (Log Format Configuration)

### 로그 포맷 유형 지정

```yaml
# 사용할 로그 포맷 지정
log_format_type: 'HTTPD'     # 옵션: ALB, HTTPD, NGINX, JSON, GROK
```

### 지원되는 로그 포맷 유형

1. **ALB** - AWS Application Load Balancer 로그 (34개 이상의 필드)
2. **HTTPD** - Apache/Nginx Combined Log Format
3. **HTTPD_WITH_TIME** - 응답 시간이 포함된 Apache 로그 (%D 또는 %T)
4. **NGINX** - 사용자 정의 포맷의 Nginx 액세스 로그
5. **JSON** - JSON 형식 로그 (줄당 하나의 JSON 객체)
6. **GROK** - 정규식 패턴을 사용한 사용자 정의 로그 포맷

## 포맷별 구성 (Format-Specific Configurations)

### ALB (AWS Application Load Balancer)

```yaml
alb:
  input_path: '*.gz'
  log_pattern: '([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) "([^"]*)" "([^"]*)" ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) "([^"]*)" "([^"]*)" "([^"]*)" ([^ ]*) ([^ ]*) "([^"]*)" "([^"]*)" "([^"]*)" "([^"]*)" "([^"]*)" "([^"]*)"'
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
    - "request_method"
    - "request_url"
    - "request_proto"
    - "user_agent"
    - "ssl_cipher"
    - "ssl_protocol"
    - "target_group_arn"
    - "trace_id"
    - "domain_name"
    - "chosen_cert_arn"
    - "matched_rule_priority"
    - "request_creation_time"
    - "actions_executed"
    - "redirect_url"
    - "error_reason"
    - "target_port_list"
    - "target_status_code_list"
    - "classification"
    - "classification_reason"
  column_types:
    time: "datetime"
    elb_status_code: "int"
    target_status_code: "int"
    request_processing_time: "float"
    target_processing_time: "float"
    response_processing_time: "float"
    received_bytes: "int"
    sent_bytes: "int"
```

### HTTPD (Apache/Nginx Combined Log Format)

```yaml
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
  column_types:
    time: "datetime"
    status: "int"
    bytes_sent: "int"
    request_time: "float"
  field_map:
    timestamp: "time"
    method: "request_method"
    url: "request_url"
    status: "status"
    clientIp: "client_ip"
    responseTime: "request_time"
```

**참고**: "request" 필드(존재하는 경우)는 자동으로 `request_method`, `request_url`, `request_proto`로 분할됩니다.

### HTTPD with Response Time

%D (마이크로초) 또는 %T (초) 응답 시간이 포함된 Apache 로그의 경우:

```yaml
httpd_with_time:
  input_path: 'access.log'
  log_pattern: '([^ ]*) [^ ]* ([^ ]*) \[([^\]]*)\] "([^ ]*) ([^ ]*) ([^"]*)" ([0-9]*) ([0-9\-]*) "([^"]*)" "([^"]*)" ([0-9]+)'
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
    - "response_time_us"  # 마이크로초 단위 응답 시간 (%D)
  column_types:
    time: "datetime"
    status: "int"
    bytes_sent: "int"
    response_time_us: "int"
```

### Nginx

```yaml
nginx:
  input_path: 'access.log'
  log_pattern: '([^ ]*) - ([^ ]*) \[([^\]]*)\] "([^ ]*) ([^ ]*) ([^"]*)" ([0-9]*) ([0-9\-]*) "([^"]*)" "([^"]*)" ([0-9.]+)'
  columns:
    - "client_ip"
    - "remote_user"
    - "time"
    - "request_method"
    - "request_url"
    - "request_proto"
    - "status"
    - "bytes_sent"
    - "referer"
    - "user_agent"
    - "request_time"  # 초 단위 응답 시간
  column_types:
    time: "datetime"
    status: "int"
    bytes_sent: "int"
    request_time: "float"
  field_map:
    timestamp: "time"
    method: "request_method"
    url: "request_url"
    status: "status"
    clientIp: "client_ip"
    responseTime: "request_time"
```

### JSON

JSON 형식 로그(줄당 하나의 JSON 객체)의 경우:

```yaml
json:
  input_path: 'access.log'
  field_map:
    timestamp: "timestamp"
    method: "method"
    url: "url"
    status: "status"
    responseTime: "response_time"
    clientIp: "client_ip"
```

### GROK/사용자 정의 패턴 (Custom Pattern)

정규식 패턴을 사용하는 사용자 정의 로그 포맷의 경우:

```yaml
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
  column_types:
    timestamp: "datetime"
    status: "int"
  field_map:
    timestamp: "timestamp"
    url: "request_url"
    status: "status"
    clientIp: "client_ip"
```

## 필드 매핑 (Field Mapping)

### 필드 매핑 작동 방식

1. **config의 명시적 `field_map`이 우선순위를 가짐**
2. **제공되지 않은 경우, 일반적인 필드 이름 변형을 기반으로 스마트 매칭이 사용됨**

### 일반적인 필드 이름 변형

- **Time**: `time`, `timestamp`, `@timestamp`, `datetime`
- **URL**: `url`, `request_url`, `uri`, `request_uri`, `path`
- **Status**: `status`, `status_code`, `elb_status_code`, `http_status`
- **Client IP**: `client_ip`, `remote_addr`, `client`, `ip`
- **Response Time**: `request_time`, `request_processing_time`, `response_time`, `duration`
- **Sent Bytes**: `sent_bytes`, `bytes_sent`, `size`, `response_size`, `body_bytes_sent`
- **Received Bytes**: `received_bytes`, `bytes`, `request_size`
- **Target IP**: `target_ip`, `backend_ip`, `upstream_addr`

### 필드 맵 예시

```yaml
field_map:
  timestamp: "time"          # 표준 필드를 실제 컬럼 이름에 매핑
  method: "request_method"
  url: "request_url"
  status: "elb_status_code"
  responseTime: "target_processing_time"
  clientIp: "client_ip"
  targetIp: "target_ip"
  sentBytes: "sent_bytes"
  receivedBytes: "received_bytes"
```

## 컬럼 타입 (Column Types)

파싱 중 자동 변환을 위한 데이터 타입을 지정합니다:

```yaml
column_types:
  time: "datetime"                    # pandas datetime으로 변환
  status: "int"                       # 정수로 변환
  bytes_sent: "int"
  request_time: "float"               # 실수로 변환
  request_processing_time: "float"
  target_processing_time: "float"
  response_processing_time: "float"
```

### 지원되는 타입

- `datetime` - 적절한 포맷의 pandas datetime으로 변환
  - HTTPD: `%d/%b/%Y:%H:%M:%S %z` 포맷 사용
  - 기타: 포맷 자동 감지
- `int` 또는 `integer` - Int64(nullable integer)로 변환
- `float` 또는 `double` - float64로 변환


## 구성 파일 검색 순서

시스템은 다음 위치(순서대로)에서 `config.yaml`을 검색합니다:

1. 입력 파일과 동일한 디렉토리
2. 입력 파일의 상위 디렉토리
3. 현재 작업 디렉토리
4. 스크립트 디렉토리 (Python 스크립트가 위치한 곳)

## 환경 설정 (Environment Settings)

### 필수 환경

- Python 3.7+
- 모든 파일에 대해 UTF-8 인코딩
- WSL2 또는 Unix 계열 환경 (파일 경로용)

### 작업 디렉토리

기본 작업 디렉토리는 `/mnt/c/bucket/AccesslogAnalyzer`입니다.

## 구성 예시 (Configuration Examples)

### 최소 구성 (모두 자동 감지)

```yaml
log_format_type: 'HTTPD'

httpd:
  input_path: 'access.log'
```

시스템은 로그 패턴을 자동 감지하고 필드 매핑을 자동으로 구축하려고 시도합니다.

### 전체 구성 (모두 명시적)

```yaml
version: '1.0'

multiprocessing:
  enabled: true
  num_workers: 8
  chunk_size: 10000
  min_lines_for_parallel: 10000

log_format_type: 'HTTPD'

httpd:
  input_path: 'access.log'
  log_pattern: '([^ ]*) [^ ]* ([^ ]*) \[([^\]]*)\] "([^ ]*) ([^ ]*) ([^"]*)" ([0-9]*) ([0-9\-]*) "([^"]*)" "([^"]*)" ([0-9.]+)'
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
    - "request_time"
  column_types:
    time: "datetime"
    status: "int"
    bytes_sent: "int"
    request_time: "float"
  field_map:
    timestamp: "time"
    method: "request_method"
    url: "request_url"
    status: "status"
    clientIp: "client_ip"
    responseTime: "request_time"
```

## 문제 해결 (Troubleshooting)

### 파싱 실패

로그 파싱이 실패하는 경우 다음을 확인하세요:
- `config.yaml`의 패턴/컬럼 불일치
- 예상치 못한 로그 포맷 변형
- 로그에 추가/누락된 필드
- 잘못된 datetime 포맷 지정

시스템 출력:
- 라인 번호와 잘린 내용이 포함된 `⚠️ 파싱에 실패한 라인`
- 포맷 추천 중 처음 10개의 실패 라인
- 실제 파싱 중 모든 실패 라인 (처음 10개까지 표시됨)

### 성능 문제

성능이 느린 경우:
- 멀티프로세싱 활성화: `multiprocessing.enabled: true`
- 작업자 수 증가: `num_workers: 8`
- 청크 크기 조정: `chunk_size: 5000` (더 작게) 또는 `chunk_size: 20000` (더 크게)

메모리 문제가 발생하는 경우:
- 작업자 수 감소: `num_workers: 2`
- 청크 크기 감소: `chunk_size: 5000`
- 파싱 함수 호출 시 컬럼 필터링 사용

### 필드를 찾을 수 없음 오류 (Field Not Found Errors)

"Field Not Found" 오류가 발생하는 경우:
- config.yaml의 필드 매핑 확인
- 명시적 `field_map` 항목 추가
- `_check_field_availability()` 헬퍼를 사용하여 사용 가능한 필드 확인
- 필드 이름 변형에 대해서는 [ARCHITECTURE.md](ARCHITECTURE.md#field-mapping-abstraction) 참조
