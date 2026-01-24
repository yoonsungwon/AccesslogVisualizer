# 로그 포맷별 설정 예제

다양한 로그 포맷을 분석하기 위한 config.yaml 설정 예제를 제공합니다.

**관련 문서:**
- [CONFIGURATION.md](./CONFIGURATION.md) - 설정 가이드
- [APACHE_LOGFORMAT_GUIDE.md](./APACHE_LOGFORMAT_GUIDE.md) - Apache LogFormat 변환 가이드
- [USAGE_EXAMPLES.md](./USAGE_EXAMPLES.md) - Python API 사용 예제

## 목차
1. [ALB 로그](#alb-로그)
2. [Apache 액세스 로그](#apache-액세스-로그)
3. [Nginx 액세스 로그](#nginx-액세스-로그)
4. [JSON 로그](#json-로그)
5. [사용자 정의 로그 포맷 (GROK)](#사용자-정의-로그-포맷-grok)

---

## ALB 로그

### 설정 (config.yaml)
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

### 사용법
```python
from data_parser import recommendAccessLogFormat, parse_log_file_with_format
from data_visualizer import generateXlog, generateRequestPerURI

# 1. 포맷 감지
result = recommendAccessLogFormat("access.log.gz")
format_file = result['logFormatFile']

# 2. 로그 파일 파싱
df = parse_log_file_with_format("access.log.gz", format_file)
print(f"파싱된 항목: {len(df)}개")

# 3. 시각화 생성
generateXlog("access.log.gz", format_file, 'html')
generateRequestPerURI("access.log.gz", format_file, 'html', topN=20, interval='10s')
```

---

## Apache 액세스 로그

### 샘플 로그 포맷
```
192.168.1.100 - frank [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326 "http://www.example.com/start.html" "Mozilla/4.08 [en] (Win98; I ;Nav)"
```

### 설정 (config.yaml)
```yaml
log_format_type: 'HTTPD'

httpd:
  input_path: 'access.log'
  # Apache Combined Log Format
  # 참고: 전체 "request" 필드를 캡처하며, 파싱 중 method/url/proto로 분할됩니다
  log_pattern: '([^ ]*) ([^ ]*) ([^ ]*) \[([^\]]*)] "([^"]*)" ([0-9]*) ([0-9\-]*)(?: "([^"]*)" "([^"]*)")?'
  columns:
    - "client_ip"
    - "identity"
    - "user"
    - "time"
    - "request"      # 전체 요청 라인 (예: "GET /path HTTP/1.1")
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
    method: "request_method"      # request에서 파생
    url: "request_url"            # request에서 파생
    status: "status"
    clientIp: "client_ip"
```

**참고**: `request` 필드는 파싱 중 자동으로 `request_method`, `request_url`, `request_proto`로 분할됩니다.

### 응답 시간 포함 (Apache %D 지시자)
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

### 사용법
```python
# ALB와 동일 - config.yaml만 변경
from data_parser import recommendAccessLogFormat
from data_processor import calculateStats, extractUriPatterns
from data_visualizer import generateRequestPerURI

# 1. 포맷 감지 (config.yaml의 HTTPD 설정 사용)
result = recommendAccessLogFormat("access.log")
format_file = result['logFormatFile']

# 2. URI 패턴 추출
extractUriPatterns("access.log", format_file, 'patterns', 'maxPatterns=20')

# 3. 통계 계산
stats = calculateStats("access.log", format_file, 'statsType=url')

# 4. 시각화
generateRequestPerURI("access.log", format_file, 'html', topN=20, interval='1m')
```

---

## Nginx 액세스 로그

### 샘플 로그 포맷
```
192.168.1.100 - - [10/Oct/2000:13:55:36 -0700] "GET /index.html HTTP/1.1" 200 1024 "http://www.example.com/" "Mozilla/5.0" 0.123
```

### 설정 (config.yaml)
```yaml
log_format_type: 'NGINX'

nginx:
  input_path: 'access.log'
  # request_time이 포함된 Nginx 로그 포맷
  log_pattern: '([^ ]*) - ([^ ]*) \[([^\]]*)\] "([^"]*)" ([0-9]*) ([0-9\-]*) "([^"]*)" "([^"]*)" ([0-9.]+)'
  columns:
    - "client_ip"
    - "remote_user"
    - "time"
    - "request"           # 전체 요청 라인
    - "status"
    - "bytes_sent"
    - "referer"
    - "user_agent"
    - "request_time"      # 초 단위 응답 시간
  column_types:
    time: "datetime"
    status: "int"
    bytes_sent: "int"
    request_time: "float"
  field_map:
    timestamp: "time"
    method: "request_method"      # request에서 파생
    url: "request_url"            # request에서 파생
    status: "status"
    responseTime: "request_time"
    clientIp: "client_ip"
```

**참고**: HTTPD와 마찬가지로, `request` 필드는 자동으로 `request_method`, `request_url`, `request_proto`로 분할됩니다.

### Nginx 사용자 정의 로그 포맷 설정
사용자 정의 Nginx 로그 포맷의 경우, nginx.conf에 패턴을 정의하세요:
```nginx
log_format custom '$remote_addr - $remote_user [$time_local] '
                  '"$request" $status $body_bytes_sent '
                  '"$http_referer" "$http_user_agent" '
                  '$request_time $upstream_response_time';
```

그런 다음 config.yaml 패턴을 그에 맞게 업데이트하세요.

---

## JSON 로그

### 샘플 로그 포맷
```json
{"timestamp":"2024-01-15T10:30:00Z","method":"GET","url":"/api/users","status":200,"response_time":0.123,"client_ip":"192.168.1.100"}
```

### 설정 (config.yaml)
```yaml
log_format_type: 'JSON'

json:
  input_path: 'access.log'
  # JSON에는 패턴이 필요 없음 - 필드 매핑만 필요
  field_map:
    timestamp: "timestamp"  # JSON 필드 이름에 맞게 조정
    method: "method"
    url: "url"
    status: "status"
    responseTime: "response_time"
    clientIp: "client_ip"
```

### 대체 JSON 필드 이름
JSON이 다른 필드 이름을 사용하는 경우:
```yaml
json:
  field_map:
    timestamp: "@timestamp"      # Elasticsearch 스타일
    method: "request_method"
    url: "request_uri"
    status: "status_code"
    responseTime: "duration"
    clientIp: "remote_addr"
```

---

## 사용자 정의 로그 포맷 (GROK)

### 예제 1: 사용자 정의 애플리케이션 로그
```
2024-01-15 10:30:00 [INFO] 192.168.1.100 /api/users 200 GET 0.123s
```

#### 설정
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

### 예제 2: 로드 밸런서 사용자 정의 포맷
```
[2024-01-15T10:30:00+00:00] client=192.168.1.100 method=GET path=/api/users status=200 time=123ms
```

#### 설정
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

## 전체 워크플로우 예제

### 시나리오: 느린 URL에 대한 Apache 액세스 로그 분석

```python
# 1. config.yaml 설정
# (적절한 패턴과 컬럼으로 log_format_type을 'HTTPD'로 설정)

# 2. 필요한 모듈 임포트
from data_parser import recommendAccessLogFormat, parse_log_file_with_format
from data_processor import calculateStats, filterByCondition, extractUriPatterns
from data_visualizer import generateXlog, generateRequestPerURI, generateProcessingTimePerURI

# 3. 로그 포맷 감지 및 파싱
result = recommendAccessLogFormat("access.log")
format_file = result['logFormatFile']
print(f"감지된 포맷: {result['patternType']}")

# 4. 로그 파일 파싱
df = parse_log_file_with_format("access.log", format_file)
print(f"파싱된 항목: {len(df)}개")

# 5. URI 패턴 추출
patterns_result = extractUriPatterns(
    "access.log",
    format_file,
    'patterns',
    'maxPatterns=30'
)
patterns_file = patterns_result['filePath']

# 6. 통계 계산
stats_result = calculateStats(
    "access.log",
    format_file,
    params='statsType=url;sortBy=status;sortMetric=count;topN=20'
)

# 7. 시간 범위로 필터링
filtered = filterByCondition(
    "access.log",
    format_file,
    'time',
    'startTime=2024-01-15T10:00:00;endTime=2024-01-15T11:00:00'
)

# 8. 시각화 생성
# XLog 산점도
generateXlog(filtered['filePath'], format_file, 'html')

# URI별 요청 수
generateRequestPerURI(
    "access.log",
    format_file,
    'html',
    topN=20,
    interval='5m',
    patternsFile=patterns_file
)

print("분석 완료! 생성된 HTML 파일을 확인하세요.")
```

---

## 팁 및 모범 사례

### 1. 패턴 테스트
대용량 파일을 처리하기 전에 몇 개의 샘플 라인으로 정규식 패턴을 테스트하세요:
```python
import re
sample = '192.168.1.100 - - [10/Oct/2000:13:55:36 -0700] "GET /index.html HTTP/1.1" 200 1024'
pattern = r'([^ ]*) - ([^ ]*) \[([^\]]*)\] "([^ ]*) ([^ ]*) ([^"]*)" ([0-9]*) ([0-9\-]*)'
match = re.match(pattern, sample)
if match:
    print(f"{len(match.groups())}개 그룹 매칭됨: {match.groups()}")
else:
    print("패턴이 일치하지 않습니다!")
```

### 2. 컬럼 수와 그룹 수 일치
config.yaml의 컬럼 수가 정규식 그룹 수와 일치하는지 확인하세요:
```python
import re
pattern = r'...'  # 패턴
test_line = '...'  # 샘플 로그 라인
groups = len(re.match(pattern, test_line).groups())
columns = [...]   # 컬럼 목록
assert len(columns) == groups, f"불일치: {len(columns)} 컬럼 vs {groups} 그룹"
```

### 3. 응답 시간 단위
로그 포맷마다 다른 시간 단위를 사용합니다:
- **Apache %D**: 마이크로초 (µs)
- **Apache %T**: 초
- **Nginx $request_time**: 소수점 포함 초
- **ALB**: 소수점 포함 초

포맷에 따라 `responseTimeUnit`을 적절히 설정하세요.

### 4. 타임존 처리
Apache/Nginx 로그의 경우 타임스탬프가 타임존 오프셋과 함께 로컬 시간으로 기록됩니다. 타임스탬프 자체에서 파싱하려면 `timezone: 'fromLog'`로 설정하세요.

ALB 로그의 경우 타임스탬프가 항상 UTC이므로 `timezone: 'UTC'`로 설정하세요.

---

## 문제 해결

### 문제: "라인 파싱 실패"
**해결책**: 정규식 패턴이 로그 포맷과 정확히 일치하는지 확인하세요. 온라인 정규식 테스터나 Python의 `re.match()`로 디버깅하세요.

### 문제: "필수 필드 누락"
**해결책**: `field_map`에 최소한 `timestamp`, `url`, `status` 매핑이 포함되어 있는지 확인하세요.

### 문제: "컬럼 수 불일치"
**해결책**: 패턴의 정규식 그룹 `()` 수를 세고 컬럼 목록의 길이가 같은지 확인하세요.

### 문제: "파싱 후 데이터 없음"
**해결책**: `pattern_type`이 올바른지 확인하세요 (HTTPD vs ALB vs JSON). 로그 파일 인코딩이 UTF-8인지 확인하세요.

---

## 추가 리소스

- [ARCHITECTURE.md](./ARCHITECTURE.md) - 아키텍처 및 설계 문서
- [API_REFERENCE.md](./API_REFERENCE.md) - API 레퍼런스
- [CONFIGURATION.md](./CONFIGURATION.md) - 설정 가이드
