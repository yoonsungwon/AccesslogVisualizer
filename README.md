# Access Log Analyzer

AccessLog Analyzer는 대용량 웹 서버 접근 로그를 분석하기 위한 MCP(Model Context Protocol) 기반 도구입니다.

## 주요 기능

- **자동 로그 포맷 감지**: ALB, Apache/Nginx, JSON 등 다양한 로그 포맷 자동 인식
- **필터링**: 시간, 상태코드, 응답시간, IP, URL 패턴 등 다양한 조건으로 필터링
- **URI 패턴 추출**: URL에서 자동으로 패턴 추출 (path variable을 * 처리)
- **통계 분석**: 전체/URL별/시간별/IP별 통계 계산
- **인터랙티브 시각화**: XLog, Request Count, Dashboard 등 HTML 기반 시각화
  - 체크박스 필터링, 드래그 확대, y축 조정 등 고급 상호작용 기능

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
```

## MCP 도구 목록

이 도구는 MCP(Model Context Protocol) 기반으로 설계되어 있으며, 다음과 같은 주요 도구들을 제공합니다:

- **로그 포맷 추천** (`recommendAccessLogFormat`): 로그 포맷 자동 감지
- **필터링** (`filterByCondition`): 시간, 상태코드, 응답시간, IP, URL 등으로 필터링
- **URI 패턴 추출** (`extractUriPatterns`): URL 추출 및 패턴 추출
- **통계 계산** (`calculateStats`): 전체/URL별/시간별/IP별 통계
- **시각화** (`generateXlog`, `generateRequestPerURI`, `generateMultiMetricDashboard`): 인터랙티브 HTML 차트 생성

자세한 사용 예제는 `USAGE_EXAMPLES.md`를 참조하세요.

## 지원 로그 포맷

- **AWS ALB**: Application Load Balancer access logs
- **Apache/Nginx**: Combined/Common log format
- **JSON**: JSON Lines format
- **GROK**: Custom patterns (fallback)

## 출력 파일

모든 도구는 파일 기반으로 데이터를 전달합니다:

- `logformat_*.json`: 로그 포맷 정보
- `filtered_*.log`: 필터링된 로그 (JSON Lines)
- `urls_*.json`: URL 목록
- `uris_*.json`: URI 패턴 목록
- `stats_*.json`: 통계 데이터
- `xlog_*.html`: XLog 그래프
- `requestcnt_*.html`: Request Count 그래프
- `dashboard_*.html`: 종합 대시보드

## 설정 파일 (선택사항)

`config.yaml` 파일을 사용하여 기본 설정을 지정할 수 있습니다:

```yaml
# 입력 파일 (glob 패턴 지원)
input_path: '*.gz'

# 로그 패턴 (자동 감지를 사용하는 경우 불필요)
# log_pattern: '...'

# 필드 이름
# columns: [...]
```

## 개발자 가이드

### 새로운 MCP 도구 추가

1. `data_processor.py` 또는 `data_visualizer.py`에 함수 추가
2. 입력: `inputFile`, `logFormatFile`, `params`
3. 출력: `dict` with `filePath` and metadata
4. `main.py`에 메뉴 항목 추가

### 파일 명명 규칙

- `logformat_`: 로그 포맷 파일
- `filtered_`: 필터링된 로그
- `urls_`: URL 목록
- `uris_`: URI 패턴
- `stats_`: 통계
- `xlog_`: XLog 그래프
- `requestcnt_`: Request Count 그래프
- `dashboard_`: 대시보드

## 라이선스

MIT License

## 작성자

- Technical Architecture Team
- Contact: user.sungwon

## 참고 문서

- **사용 예제**: `USAGE_EXAMPLES.md` - 상세한 Python API 사용 예제 및 고급 시나리오
- **설계 문서**: `AccessLogAnalyzer.md` - 아키텍처 및 MCP 도구 상세 설명

