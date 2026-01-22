# Access Log Analyzer

AccessLog Analyzer는 대용량 웹 서버 접근 로그를 분석하기 위한 MCP(Model Context Protocol) 기반 도구입니다.

## 주요 기능

- **자동 로그 포맷 감지**: ALB, HTTPD (Apache/Nginx), JSON, GROK 등 다양한 로그 포맷 자동 인식
- **멀티포맷 지원**: config.yaml을 통해 다양한 로그 포맷 설정 가능
- **필터링**: 시간, 상태코드, 응답시간, IP, URL 패턴 등 다양한 조건으로 필터링
- **URI 패턴 추출**: URL에서 자동으로 패턴 추출 (path variable을 * 처리)
- **통계 분석**: 전체/URL별/시간별/IP별 통계 계산
- **인터랙티브 시각화**: XLog, Request Count, Bytes, Processing Time 등 HTML 기반 시각화
  - 체크박스 필터링, 드래그 확대, y축 조정 등 고급 상호작용 기능
- **필드 가용성 체크**: 로그 포맷에 없는 필드 선택 시 사전 경고

## 설치

```bash
pip install -r requirements.txt
```

## 빠른 시작

```bash
# 인터랙티브 모드
python main.py

# 파일 지정 모드
python main.py access.log.gz

# 예제 파이프라인 실행
python main.py --example access.log.gz

# Apache LogFormat에서 설정 파일 생성
python apache_logformat_converter.py --preset combined --output config
```

## MCP 도구 목록

이 도구는 MCP(Model Context Protocol) 기반으로 설계되어 있으며, 다음과 같은 주요 도구들을 제공합니다:

### 파싱 및 포맷 감지
- **`recommendAccessLogFormat`**: 로그 포맷 자동 감지 및 format 파일 생성
- **`parse_log_file_with_format`**: 로그 파일 파싱 (멀티프로세싱 지원)

### 필터링 및 데이터 처리
- **`filterByCondition`**: 시간, 상태코드, 응답시간, IP, URL 등으로 필터링
- **`extractUriPatterns`**: URL 추출 및 패턴 생성
- **`filterUriPatterns`**: 패턴 기반 필터링
- **`calculateStats`**: 전체/URL별/시간별/IP별 통계 계산

### 시각화
- **`generateXlog`**: XLog 산점도 (응답시간 scatter plot)
- **`generateRequestPerURI`**: URI별 요청 수 시계열 차트
- **`generateRequestPerTarget`**: Target IP별 요청 수 시계열 차트 (ALB 전용)
- **`generateRequestPerClientIP`**: Client IP별 요청 수 시계열 차트
- **`generateReceivedBytesPerURI`**: URI별 수신 바이트 (Sum/Average) (ALB 전용)
- **`generateSentBytesPerURI`**: URI별 전송 바이트 (Sum/Average)
- **`generateProcessingTimePerURI`**: URI별 처리 시간 (avg/sum/median/p95/p99/max) (ALB 전용)
- **`generateMultiMetricDashboard`**: 종합 대시보드

자세한 사용 예제는 `EXAMPLES.md`를 참조하세요.

## 지원 로그 포맷

config.yaml에서 다음 로그 포맷을 설정할 수 있습니다:

- **ALB**: AWS Application Load Balancer access logs
  - 모든 필드 지원 (target_ip, received_bytes, processing times 등)
- **HTTPD**: Apache Combined Log Format
  - client_ip, time, request (method/url/proto), status, bytes_sent, referer, user_agent
- **HTTPD_WITH_TIME**: Apache with response time (%D directive)
  - HTTPD + response_time_us 필드
- **NGINX**: Nginx access log with request_time
  - client_ip, time, request, status, bytes_sent, request_time 등
- **JSON**: JSON Lines format
  - 필드 이름 매핑 지원
- **GROK**: Custom patterns
  - 정규표현식 기반 커스텀 패턴
- **Custom**: 사용자 정의 포맷
  - `config.yaml`에 임의의 섹션 이름(예: `httpd_custom`)으로 정의하여 사용 가능

### 로그 포맷별 필드 가용성

| 기능 | ALB | HTTPD | HTTPD_WITH_TIME | NGINX | JSON |
|------|-----|-------|-----------------|-------|------|
| Request Count per URI | ✓ | ✓ | ✓ | ✓ | ✓ |
| Request Count per Client IP | ✓ | ✓ | ✓ | ✓ | ✓ |
| Request Count per Target | ✓ | ✗ | ✗ | ✗ | * |
| Sent Bytes | ✓ | ✓ | ✓ | ✓ | * |
| Received Bytes | ✓ | ✗ | ✗ | ✗ | * |
| Processing Time | ✓ | ✗ | ✓ | ✓ | * |
| XLog (Response Time) | ✓ | ✗ | ✓ | ✓ | * |

**\*** JSON 포맷은 field_map 설정에 따라 다름

## 출력 파일

모든 도구는 파일 기반으로 데이터를 전달합니다:

- `logformat_*.json`: 로그 포맷 정보 (columns, columnTypes, pattern 등)
- `filtered_*.log`: 필터링된 로그 (JSON Lines)
- `urls_*.json`: URL 목록
- `patterns_*.json`: URI 패턴 규칙
- `stats_*.json`: 통계 데이터
- `xlog_*.html`: XLog 산점도
- `requestcnt_*.html`: Request Count per URI 시계열 차트
- `requestcnt_target_*.html`: Request Count per Target 시계열 차트
- `requestcnt_clientip_*.html`: Request Count per Client IP 시계열 차트
- `receivedbytes_*.html`: Received Bytes per URI 차트
- `sentbytes_*.html`: Sent Bytes per URI 차트
- `processingtime_*.html`: Processing Time per URI 차트
- `dashboard_*.html`: 종합 대시보드

## 설정 파일 (config.yaml)

`config.yaml` 파일을 사용하여 로그 포맷을 설정할 수 있습니다:

```yaml
# 사용할 로그 포맷 타입 지정
log_format_type: 'HTTPD'  # ALB, HTTPD, HTTPD_WITH_TIME, NGINX, JSON, GROK, 또는 사용자 정의 섹션 이름

# 사용자 정의 포맷 예시 (httpd_custom)
httpd_custom:
  log_pattern: '([^ ]*) ([^ ]*) ...'
  columns: ['client_ip', 'time', ...]
  field_map: {timestamp: 'time', ...}

# HTTPD (Apache Combined Log Format)
httpd:
  input_path: 'access.log'
  log_pattern: '([^ ]*) ([^ ]*) ([^ ]*) \[([^\]]*)] "([^"]*)" ([0-9]*) ([0-9\-]*)(?: "([^"]*)" "([^"]*)")?'
  columns:
    - "client_ip"
    - "identity"
    - "user"
    - "time"
    - "request"
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
    method: "request_method"
    url: "request_url"
    status: "status"
    clientIp: "client_ip"

# ALB (AWS Application Load Balancer)
alb:
  input_path: '*.gz'
  log_pattern: '...'  # ALB 전용 패턴
  columns: [...]      # ALB 전용 컬럼
  column_types: {...} # 컬럼 타입 지정

# Multiprocessing 설정
multiprocessing:
  enabled: true
  num_workers: null      # null = CPU 코어 수 자동 감지
  chunk_size: 10000
  min_lines_for_parallel: 10000
```

상세한 설정 예제는 `EXAMPLES.md`를 참조하세요.

## 개발자 가이드

### 새로운 MCP 도구 추가

1. `data_processor.py` 또는 `data_visualizer.py`에 함수 추가
2. 입력: `inputFile`, `logFormatFile`, `params`
3. 출력: `dict` with `filePath` and metadata
4. `main.py`에 메뉴 항목 추가
5. 필드 가용성 체크 로직 추가 (필요시)

### 파일 명명 규칙

- `logformat_`: 로그 포맷 파일
- `filtered_`: 필터링된 로그
- `urls_`: URL 목록
- `patterns_`: URI 패턴
- `stats_`: 통계
- `xlog_`: XLog 그래프
- `requestcnt_`: Request Count 그래프
- `receivedbytes_`: Received Bytes 그래프
- `sentbytes_`: Sent Bytes 그래프
- `processingtime_`: Processing Time 그래프
- `dashboard_`: 대시보드

## 라이선스

MIT License

## 작성자

- IT Optimization Team
- Contact: user.sungwon

## 참고 문서

- **AI 가이드**: `AI_GUIDE.md` - AI 어시스턴트용 상세 기술 문서
- **사용 예제**: `EXAMPLES.md` - 로그 포맷별 설정 및 사용 예제
- **Apache LogFormat 컨버터**: `APACHE_LOGFORMAT_GUIDE.md` - Apache LogFormat 문자열로부터 설정 파일 자동 생성
- **Claude 가이드**: `CLAUDE.md` - Claude Code 통합 가이드
- **Gemini 가이드**: `GEMINI.md` - Gemini CLI 통합 가이드
