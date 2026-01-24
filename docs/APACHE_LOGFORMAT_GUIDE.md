# Apache LogFormat 변환 가이드

Apache LogFormat 문자열을 자동으로 파싱하여 config.yaml 또는 logformat_*.json 파일을 생성하는 도구입니다.

**관련 문서:**
- [CONFIGURATION.md](./CONFIGURATION.md) - 설정 가이드
- [EXAMPLES.md](./EXAMPLES.md) - 로그 포맷별 설정 예제

## 사용법

### 기본 사용

```bash
# Preset 포맷 사용
python apache_logformat_converter.py --preset combined --output config

# 커스텀 LogFormat 문자열 사용
python apache_logformat_converter.py '%h %l %u %t "%r" %>s %b' --output json

# 결과만 확인 (파일 생성 없이)
python apache_logformat_converter.py --preset common
```

### 사용 가능한 Presets

| Preset | LogFormat | 설명 |
|--------|-----------|------|
| `common` | `%h %l %u %t "%r" %>s %b` | Common Log Format |
| `combined` | `%h %l %u %t "%r" %>s %b "%{Referer}i" "%{User-agent}i"` | Combined Log Format |
| `combined_with_time` | `%h %l %u %t "%r" %>s %b "%{Referer}i" "%{User-agent}i" %D` | Combined + Response Time |
| `vhost_combined` | `%v:%p %h %l %u %t "%r" %>s %b "%{Referer}i" "%{User-agent}i"` | Virtual Host Combined |

### 출력 옵션

- `--output config`: config.yaml 생성 (기본 파일명: `config_generated.yaml`)
- `--output json`: logformat_*.json 생성 (기본 파일명: `logformat_YYMMDD_HHMMSS.json`)
- `--output both`: 두 파일 모두 생성
- `--output-file <path>`: 출력 파일 경로 지정

## 지원하는 Apache 지시자

### 클라이언트/서버 정보

| 지시자 | 설명 | 컬럼 이름 |
|--------|------|-----------|
| `%h` | Client IP (hostname) | `client_ip` |
| `%a` | Client IP address | `client_ip` |
| `%l` | Remote logname (identd) | `identity` |
| `%u` | Remote user (auth) | `user` |
| `%v` | Server name | `server_name` |
| `%p` | Server port | `server_port` |
| `%A` | Server IP | `server_ip` |

### 요청 정보

| 지시자 | 설명 | 컬럼 이름 |
|--------|------|-----------|
| `%r` | First line of request | `request` |
| `%m` | Request method | `request_method` |
| `%U` | URL path | `request_url` |
| `%q` | Query string | `query_string` |
| `%H` | Request protocol | `request_proto` |

### 응답 정보

| 지시자 | 설명 | 컬럼 이름 |
|--------|------|-----------|
| `%s` | Status code | `status` |
| `%>s` | Final status code | `status` |
| `%b` | Bytes sent (CLF format) | `bytes_sent` |
| `%B` | Bytes sent | `bytes_sent` |
| `%I` | Bytes received | `bytes_received` |
| `%O` | Bytes sent including headers | `bytes_sent_including_headers` |

### 시간 정보

| 지시자 | 설명 | 컬럼 이름 | 타입 |
|--------|------|-----------|------|
| `%t` | Request time | `time` | `datetime` |
| `%D` | Response time (microseconds) | `response_time_us` | `int` |
| `%T` | Response time (seconds) | `response_time_s` | `float` |

### 헤더 및 환경 변수

| 지시자 | 설명 | 예시 |
|--------|------|------|
| `%{NAME}i` | Request header | `%{Referer}i` → `referer` |
| `%{NAME}o` | Response header | `%{Content-Type}o` → `resp_content_type` |
| `%{NAME}e` | Environment variable | `%{PATH}e` → `env_path` |

## 사용 예시

### 예시 1: Apache Combined 포맷

```bash
$ python apache_logformat_converter.py --preset combined --output config
```

**생성된 config.yaml:**
```yaml
log_format_type: HTTPD
httpd:
  input_path: access.log
  log_pattern: ([^ ]+) ([^ ]+) ([^ ]+) \[([^\]]+)\] "([^"]*)" ([-0-9]+) ([-0-9]+) "([^"]*)" "([^"]*)"
  columns:
  - client_ip
  - identity
  - user
  - time
  - request
  - status
  - bytes_sent
  - referer
  - user_agent
  column_types:
    time: datetime
    status: int
    bytes_sent: int
  field_map:
    timestamp: time
    clientIp: client_ip
    status: status
    method: request_method
    url: request_url
```

### 예시 2: 커스텀 포맷 (응답 시간 포함)

```bash
$ python apache_logformat_converter.py '%h %l %u %t "%r" %>s %b %D' --output json
```

**생성된 logformat_*.json:**
```json
{
  "logPattern": "([^ ]+) ([^ ]+) ([^ ]+) \\[([^\\]]+)\\] \"([^\"]*)\" ([-0-9]+) ([-0-9]+) ([0-9]+)",
  "patternType": "HTTPD",
  "columns": [
    "client_ip",
    "identity",
    "user",
    "time",
    "request",
    "status",
    "bytes_sent",
    "response_time_us"
  ],
  "columnTypes": {
    "time": "datetime",
    "status": "int",
    "bytes_sent": "int",
    "response_time_us": "int"
  },
  "fieldMap": {
    "timestamp": "time",
    "clientIp": "client_ip",
    "status": "status",
    "method": "request_method",
    "url": "request_url",
    "responseTime": "response_time_us"
  },
  "responseTimeUnit": "microseconds",
  "timezone": "fromLog"
}
```

### 예시 3: 가상 호스트 로그

```bash
$ python apache_logformat_converter.py '%v:%p %h %l %u %t "%r" %>s %b' --output config
```

이 경우 `server_name`과 `server_port` 컬럼이 추가됩니다.

## Apache LogFormat 설정 확인

현재 Apache 서버의 LogFormat 설정을 확인하려면:

```bash
# Apache 설정 파일 확인
grep LogFormat /etc/httpd/conf/httpd.conf
# 또는
grep LogFormat /etc/apache2/apache2.conf

# 예시 출력:
# LogFormat "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-agent}i\"" combined
# LogFormat "%h %l %u %t \"%r\" %>s %b" common
```

## 생성된 파일 사용하기

### config.yaml 사용

1. 생성된 `config_generated.yaml`을 `config.yaml`로 복사하거나 내용을 병합
2. `main.py` 실행 시 자동으로 해당 포맷 사용

```bash
cp config_generated.yaml config.yaml
python main.py access.log
```

### logformat_*.json 사용

생성된 JSON 파일을 직접 지정하여 사용:

```python
from data_parser import parse_log_file_with_format
from data_visualizer import generateRequestPerURI

# 파싱
df = parse_log_file_with_format('access.log', 'logformat_251128_170217.json')

# 시각화
generateRequestPerURI('access.log', 'logformat_251128_170217.json', 'html')
```

## 트러블슈팅

### 패턴이 맞지 않는 경우

실제 로그 샘플과 생성된 정규표현식을 확인:

```python
import re

# 생성된 패턴
pattern = r'([^ ]+) ([^ ]+) ([^ ]+) \[([^\]]+)\] "([^"]*)" ([-0-9]+) ([-0-9]+)'

# 실제 로그 샘플
log_line = '192.168.1.1 - - [18/Sep/2011:19:18:28 -0400] "GET / HTTP/1.1" 200 1234'

# 매칭 테스트
match = re.match(pattern, log_line)
if match:
    print(f"✓ Matched: {match.groups()}")
else:
    print("✗ Pattern did not match")
```

### 커스텀 헤더 지원

특정 헤더가 필요한 경우 LogFormat에 추가:

```bash
# X-Forwarded-For 헤더 추가
python apache_logformat_converter.py '%h %l %u %t "%r" %>s %b "%{X-Forwarded-For}i"' --output config
```

이는 `x_forwarded_for` 컬럼으로 변환됩니다.

## 참고 자료

- [Apache mod_log_config 문서](https://httpd.apache.org/docs/2.4/en/mod/mod_log_config.html)
- [Apache Log Files 가이드](https://httpd.apache.org/docs/2.4/logs.html)
