# 아키텍처 문서

이 문서는 Access Log Analyzer의 기술적 아키텍처를 설명합니다.

**관련 문서:**
- [DESIGN.md](./DESIGN.md) - 설계 철학 및 MCP 도구 상세 사양
- [API_REFERENCE.md](./API_REFERENCE.md) - 함수 시그니처 및 매개변수
- [CONFIGURATION.md](./CONFIGURATION.md) - 설정 가이드
- [DEVELOPMENT.md](./DEVELOPMENT.md) - 개발 가이드

## 프로젝트 구조

```
AccesslogVisualizer/
├── core/                      # 핵심 인프라
│   ├── __init__.py
│   ├── exceptions.py          # 커스텀 예외 클래스
│   ├── config.py             # 중앙화된 설정을 위한 ConfigManager
│   ├── logging_config.py     # 로깅 설정
│   └── utils.py              # 유틸리티 클래스 (FieldMapper, ParamParser, MultiprocessingConfig)
├── data_parser.py            # 로그 포맷 감지 및 파싱
├── data_processor.py         # 필터링, 패턴, 통계
├── data_visualizer.py        # 인터랙티브 시각화
├── main.py                   # CLI 인터페이스
├── mcp_server.py            # MCP 서버
├── config.yaml              # 선택적 설정 파일
└── docs/                    # 문서
    ├── ARCHITECTURE.md      # 기술적 아키텍처 (이 파일)
    ├── DESIGN.md            # 설계 문서 및 MCP 도구 사양
    ├── API_REFERENCE.md     # 함수 시그니처 및 파라미터
    ├── CONFIGURATION.md     # 설정 가이드
    ├── DEVELOPMENT.md       # 개발 가이드
    ├── WORKFLOWS.md         # 일반적인 워크플로우
    ├── EXAMPLES.md          # 로그 포맷별 설정 예제
    ├── USAGE_EXAMPLES.md    # Python API 사용 예제
    ├── MAIN_USAGE_EXAMPLES.md # CLI (main.py) 사용 예제
    └── CHANGELOG.md         # 최근 변경사항
```

## 핵심 인프라

### core/exceptions.py - 커스텀 예외 클래스

- `LogAnalyzerError` - 모든 에러의 기본 예외
- `FileNotFoundError` - 파일 찾기 실패 에러
- `InvalidFormatError` - 잘못된 로그 포맷 에러
- `ParseError` - 라인 컨텍스트를 포함한 로그 파싱 에러
- `ValidationError` - 입력 검증 에러
- `ConfigurationError` - 설정 에러

### core/config.py - 설정 관리

- `ConfigManager` - 중앙화된 설정 관리를 위한 싱글톤 클래스
- 여러 표준 위치에서 `config.yaml` 검색
- 성능을 위한 설정 캐싱
- 중첩된 키에 대한 점 표기법 지원 (예: `config.get('server.port')`)

### core/logging_config.py - 로깅 시스템

- 콘솔 및 파일 핸들러를 사용한 중앙화된 로깅 설정
- 로그 레벨: DEBUG, INFO, WARNING, ERROR, CRITICAL
- 디버깅을 위한 파일명과 라인 번호를 포함한 상세 포맷
- 모든 `print()` 문을 적절한 로깅으로 대체
- `logs/` 디렉토리에 일일 로테이션 로그 파일

### core/utils.py - 유틸리티 클래스

#### FieldMapper - 스마트 필드 매핑
- `find_field()` - 다양한 로그 포맷에서 필드 찾기
- `map_fields()` - 검증을 포함한 대량 필드 매핑
- `validate_required_fields()` - 명확한 에러 메시지와 함께 검증

#### ParamParser - 타입 안전 파라미터 파싱
- `parse()` - "key=value;key2=value2" 포맷 파싱
- `get_bool/int/float/list()` - 타입 안전 값 추출
- 커스텀 예외를 사용한 내장 검증

#### MultiprocessingConfig - 멀티프로세싱 설정
- `get_config()` - config.yaml에서 멀티프로세싱 설정 로드
- `get_optimal_workers()` - 최적 워커 수 계산
- `should_use_multiprocessing()` - 병렬 처리 사용 여부 결정
- `get_processing_params()` - 오버라이드를 포함한 완전한 처리 파라미터 가져오기

## 핵심 모듈

### data_parser.py - 로그 포맷 감지 및 파싱

#### `recommendAccessLogFormat(inputFile)`
로그 포맷(ALB, Apache/Nginx, JSON)을 자동 감지하고 `logformat_*.json` 파일을 생성합니다.

**우선순위:**
1. 동일 디렉토리에서 기존 `logformat_*.json` 확인
2. 입력 파일에서 100줄 샘플링
3. 포맷 타입 자동 감지 (ALB, JSON, Apache/Nginx, 또는 GROK 폴백)
4. 여러 위치에서 `config.yaml` 검색
5. 절대 경로로 `logformat_*.json` 생성 및 저장

#### `parse_log_file_with_format(inputFile, logFormatFile, use_multiprocessing, num_workers, chunk_size, columns_to_load)`
선택적 병렬 처리 및 메모리 최적화를 사용하여 로그 파일을 파싱합니다.

**기능:**
- **멀티프로세싱 지원**: 대용량 파일(기본값 10,000줄 이상)에 대해 자동으로 병렬 처리 사용
- **Config.yaml 자동 로드**: 파라미터가 `None`일 때 `config.yaml`에서 설정 자동 로드
- **설정 가능한 워커**: CPU 코어와 파일 크기에 따라 최적 워커 수 자동 감지
- **청크 기반 처리**: 효율적인 병렬 파싱을 위해 대용량 파일을 청크로 분할
- **메모리 최적화**: `columns_to_load` 파라미터로 필요한 컬럼만 로드
  - 대용량 파일의 메모리 사용량 80-90% 감소
  - 최대 효율성을 위해 DataFrame 생성 전에 컬럼 필터링
  - 예시: `columns_to_load=['time', 'request_url']`
- 성능: 멀티코어 시스템에서 대용량 파일의 경우 약 3-4배 빠름
- gzip 압축 파일 자동 지원
- ALB 로그를 위한 설정 가능한 `config.yaml`을 사용한 패턴 매칭
- 메타데이터 반환: 패턴 타입, 신뢰도 점수, 성공률, 필드 매핑

**HTTPD 요청 필드 처리:**
HTTPD 로그의 경우, 단일 "request" 필드가 자동으로 다음과 같이 분할됩니다:
- `request_method` - HTTP 메서드 (GET, POST 등)
- `request_url` - URL 경로
- `request_proto` - 프로토콜 버전 (HTTP/1.1 등)

**컬럼 타입 변환:**
포맷 파일의 `columnTypes`에 따라 컬럼 타입 변환을 적용합니다:
- `datetime` - pandas datetime으로 변환 (HTTPD 전용 포맷: `%d/%b/%Y:%H:%M:%S %z`)
- `int/integer` - 에러 처리를 포함하여 Int64로 변환
- `float/double` - 에러 처리를 포함하여 float으로 변환

### data_processor.py - 필터링 및 통계

#### `filterByCondition(inputFile, logFormatFile, condition, params)`
시간, 상태 코드, 응답 시간, 클라이언트 IP, URL 또는 URI 패턴으로 필터링합니다.

모든 필터링된 데이터는 유연성을 위해 JSON Lines 포맷으로 저장됩니다.

#### `extractUriPatterns(inputFile, logFormatFile, extractionType, params)`
고유 URL 또는 일반화된 URI 패턴을 추출합니다 (ID/UUID를 `*`로 대체).

**기능:**
- **통합 패턴 파일**: 표준화된 패턴 파일 경로 사용 (`patterns_{log_name}.json`)
- 표준화된 경로를 위해 `data_visualizer` 모듈의 `_get_patterns_file_path()` 호출
- 수동으로 추가된 규칙을 보존하면서 기존 패턴과 병합하기 위해 `_save_or_merge_patterns()` 사용

#### `calculateStats(inputFile, logFormatFile, params, use_multiprocessing, num_workers)`
병렬 처리 지원과 함께 포괄적인 통계를 계산합니다.

**기능:**
- **Config.yaml 자동 로드**: 파라미터가 `None`일 때 멀티프로세싱 설정 자동 로드
- **병렬 URL 통계**: 여러 URL 그룹을 동시에 처리 (>= 100개 URL)
- **병렬 시계열 통계**: 시간 간격 통계를 병렬로 계산 (>= 100개 간격)
- **병렬 IP 통계**: IP 그룹을 동시에 처리 (>= 100개 IP)
- **timeInterval 파라미터**: 유연한 시간 간격 포맷 지원 (예: '1m', '10s', '1h')
- **processingTimeFields 파라미터**: 여러 처리 시간 필드를 동시에 분석
  - 지원: `request_processing_time`, `target_processing_time`, `response_processing_time` 등
  - 계산: 각 필드에 대한 avg, sum, median, std, min, max, p90, p95, p99
- **sortBy/sortMetric/topN 파라미터**: 특정 메트릭으로 상위 N개 URL 가져오기
  - `sortBy`: 정렬할 필드
  - `sortMetric`: 사용할 메트릭 ('avg', 'sum', 'median', 'p95', 'p99')
  - `topN`: 상위 N개 결과만 반환
- 일반적인 약어 자동 정규화: '1m' → '1min', '30sec' → '30s'
- 성능: 대규모 데이터셋의 경우 약 2-3배 빠름

#### `PatternRulesManager`
효율적인 패턴 규칙 로딩을 위한 패턴 캐싱 클래스 (전역 변수 대체).

- `load_rules(patterns_file)` - 파일에서 패턴 규칙 로드 및 캐싱
- `clear_cache(patterns_file)` - 캐시된 패턴 지우기
- `get_cached_files()` - 캐시된 패턴 파일 목록 가져오기

### data_visualizer.py - 인터랙티브 시각화

모든 시각화 함수는 분석을 위해 'time'과 'request_creation_time' 중 선택할 수 있는 `timeField` 파라미터를 지원합니다.

#### `generateXlog(inputFile, logFormatFile, outputFormat, timeField)`
WebGL 렌더링을 사용하여 응답 시간 산점도를 생성합니다.
- **메모리 최적화**: 모든 34개 이상의 필드 대신 필요한 컬럼만 로드 (시간, URL, 상태, 응답 시간)

#### `generateRequestPerURI(inputFile, logFormatFile, outputFormat, topN, interval, patternsFile, timeField)`
인터랙티브 체크박스 필터링 및 호버 텍스트 클립보드 복사 기능이 있는 시계열 차트를 생성합니다.
- **interval 파라미터**: 유연한 시간 간격 포맷 지원 (예: '1m', '10s', '1h')
- 일반적인 약어 자동 정규화
- **메모리 최적화**: 컬럼 필터링 + dtype 최적화 + 명시적 메모리 정리

#### `generateRequestPerTarget(inputFile, logFormatFile, outputFormat, topN, interval, timeField)`
타겟별 요청 수의 시계열 시각화 (target_ip:target_port).
- 백엔드 타겟 서버별로 요청 그룹화
- 상태 색상 코딩과 함께 인터랙티브 체크박스 필터링 및 IP 그룹화

#### `generateRequestPerClientIP(inputFile, logFormatFile, outputFormat, topN, interval, timeField)`
클라이언트 IP별 요청 수의 시계열 시각화.
- 클라이언트 소스 IP별로 요청 그룹화
- 상태 색상 코딩과 함께 인터랙티브 체크박스 필터링

#### `generateReceivedBytesPerURI()` 및 `generateSentBytesPerURI()`
메모리 최적화를 사용한 바이트 전송 분석.

#### `generateProcessingTimePerURI(inputFile, logFormatFile, outputFormat, processingTimeField, metric, topN, interval, patternsFile, timeField)`
URI 패턴별 처리 시간의 시계열 시각화.
- **processingTimeField**: 분석할 처리 시간 필드 (request_processing_time, target_processing_time, response_processing_time)
- **metric**: 계산할 메트릭 (avg, sum, median, p95, p99, max)
- 총 처리 시간으로 상위 N개 패턴 추출
- 줌, 팬 및 범위 슬라이더가 있는 인터랙티브 시계열 차트

#### `generateMultiMetricDashboard(inputFile, logFormatFile, outputFormat, timeField)`
포괄적인 3-패널 대시보드를 생성합니다.

#### 패턴 파일 관리

- `_get_patterns_file_path(inputFile)`: 표준화된 패턴 파일 경로 반환 (예: `patterns_access.log.json`)
- `_save_or_merge_patterns(patterns_file_path, pattern_rules, metadata)`: 중복을 제거하면서 패턴 규칙 저장 또는 병합
- 모든 시각화 함수는 로그 파일당 단일 패턴 파일을 공유
- 동일한 로그 파일에서 다른 함수를 호출할 때 패턴 규칙이 자동으로 병합됨

#### 메모리 최적화 함수

- `_optimize_dataframe_dtypes(df)`: dtype 최적화를 통해 메모리 사용량 50-70% 감소
  - int64 → int32/int16 (50% 절감)
  - float64 → float32 (50% 절감)
  - object → category (낮은 카디널리티 문자열의 경우 70-90% 절감)
- 컬럼 필터링: DataFrame 생성 전에 필요한 컬럼만 로드 (80-90% 메모리 감소)
- 명시적 메모리 정리: 피벗 작업 후 `gc.collect()` 사용

- `_normalize_interval(interval)`: 시간 간격 문자열을 pandas 호환 포맷으로 정규화하는 헬퍼 함수

모든 시각화는 인터랙티비티를 위해 CDN과 함께 Plotly를 사용합니다.

## 파일 명명 규칙

출력 파일은 쉬운 식별을 위해 엄격한 명명 패턴을 따릅니다:

- `logformat_*.json` - 로그 포맷 감지 결과
- `filtered_*.log` - 필터링된 로그 데이터 (JSON Lines 포맷)
- `urls_*.json` - URL 추출 결과
- `uris_*.json` 또는 `patterns_*.json` - `patternRules`를 포함한 URI 패턴 추출
- `patterns_{log_name}.json` - **로그 파일당 단일 통합 패턴 파일**
  - 모든 시각화 함수가 주어진 로그 파일에 대해 동일한 패턴 파일 공유
  - 포맷: 입력 파일 `access.log.gz`에 대한 `patterns_access.json`
  - 다른 함수가 패턴을 추출할 때 패턴 규칙이 자동으로 병합됨
- `stats_*.json` - 통계 분석 결과
- `xlog_*.html` - 응답 시간 산점도
- `requestcnt_*.html` - URI별 요청 수 시각화
- `requestcnt_target_*.html` - 타겟별 요청 수 시각화
- `requestcnt_clientip_*.html` - 클라이언트 IP별 요청 수 시각화
- `dashboard_*.html` - 멀티 메트릭 대시보드

## 주요 디자인 패턴

### MCP 도구 기반 아키텍처

코드베이스는 **Model Context Protocol (MCP)** 아키텍처를 따릅니다:
- 각 주요 작업은 독립형 MCP 도구로 구현됨
- 도구는 파일 입력을 받고 파일 출력을 생성 (JSON, HTML 등)
- 도구는 체인 가능 - 한 도구의 출력 파일이 다른 도구의 입력으로 사용됨
- 모든 도구는 MCP 서버(`mcp_server.py`) 또는 Python API를 통해 직접 호출 가능

### 도구 체인 패턴

도구는 함께 체인하도록 설계되었습니다:

```python
# 1. 포맷 감지
format_result = recommendAccessLogFormat("access.log.gz")

# 2. 시간별 필터링
filter_result = filterByCondition(
    "access.log.gz",
    format_result['logFormatFile'],
    'time',
    'startTime=2024-08-08T09:00:00;endTime=2024-08-08T10:00:00'
)

# 3. 필터링된 데이터 시각화
xlog_result = generateXlog(
    filter_result['filePath'],
    format_result['logFormatFile'],
    'html'
)
```

### 패턴 규칙 시스템

URI 패턴은 JSON에 저장된 정규식 기반 패턴 규칙을 사용합니다:

```json
{
  "patternRules": [
    {
      "pattern": "^/api/users/.*$",
      "replacement": "/api/users/*"
    }
  ]
}
```

### 필드 매핑 추상화

모든 도구는 로그 포맷 파일의 `fieldMap`을 사용하여 다양한 로그 타입과 작동합니다:

```json
{
  "fieldMap": {
    "timestamp": "time",
    "url": "request_url",
    "status": "elb_status_code",
    "responseTime": "target_processing_time",
    "clientIp": "client_ip"
  }
}
```

## URI 패턴 일반화

시스템은 두 가지 URL 일반화 함수를 제공합니다:

1. **`_generalize_url(url, patterns_file=None)`** - 각 호출마다 파일에서 패턴 규칙 로드
2. **`_generalize_url_with_rules(url, pattern_rules=None)`** - 미리 로드된 패턴 규칙 받기 (DataFrame 작업에 권장)

두 함수 모두 동적 세그먼트를 지능적으로 대체합니다:

### ID 유사 세그먼트 → `*`
- 순수 숫자 → `*`
- UUID (8-4-4-4-12 포맷) → `*`
- 긴 16진수 문자열 (16자 이상) → `*`
- 70% 이상 숫자인 혼합 영숫자 → `*`

### 정적 파일 → 확장자별 분류
- `.css`, `.scss`, `.sass`, `.less` → `*.css`
- `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs` → `*.js`
- `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.ico`, `.webp` → `*.image`
- `.woff`, `.woff2`, `.ttf`, `.otf`, `.eot` → `*.font`
- `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx` → `*.doc`
- `.mp4`, `.avi`, `.mov`, `.webm`, `.mkv` → `*.video`
- `.mp3`, `.wav`, `.ogg`, `.m4a` → `*.audio`
- `.html`, `.htm` → `*.html`
- `.json`, `.xml`, `.yaml`, `.yml`, `.csv`, `.txt` → `*.data`
- `.zip`, `.tar`, `.gz`, `.rar`, `.7z` → `*.archive`

### 커스텀 패턴
커스텀 매칭을 위해 파일의 패턴 규칙을 사용할 수 있습니다.

### 성능 팁

DataFrame에서 많은 URL을 처리할 때는 미리 로드된 패턴 규칙과 함께 `_generalize_url_with_rules()`를 사용하세요:

```python
# 좋음 - 패턴 규칙을 한 번만 로드
pattern_rules = _pattern_manager.load_rules(patterns_file)
df['url_pattern'] = df['url'].apply(lambda x: _generalize_url_with_rules(x, pattern_rules))

# 나쁨 - 모든 URL에 대해 패턴 규칙 로드
df['url_pattern'] = df['url'].apply(lambda x: _generalize_url(x, patterns_file))
```

변환 예시:
```
/assets/styles/main.css → /assets/styles/*.css
/static/js/app.12345.js → /static/js/*.js
/images/logo.png → /images/*.image
/fonts/Roboto-Regular.woff2 → /fonts/*.font
```

## 성능 최적화

### 대규모 데이터셋 샘플링
더 나은 렌더링 성능을 위해 시각화는 최대 50,000개 포인트로 샘플링합니다.

### WebGL 렌더링
대규모 데이터셋으로 더 나은 성능을 위해 `Scatter` 대신 `Scattergl`을 사용합니다.

### 효율적인 필터링
더 빠른 처리를 위해 패턴 매칭은 컴파일된 정규식을 사용합니다.

### 지연 로딩
재파싱을 피하기 위해 패턴 규칙이 전역적으로 캐시됩니다.

### 메모리 최적화 (다층 접근 방식)

1. **컬럼 필터링**: DataFrame 생성 전에 필요한 컬럼만 로드 (80-90% 메모리 감소)
   - 예시: ALB 로그의 경우 34개 대신 2개 컬럼 로드
   - 모든 시각화 함수에 적용

2. **Dtype 최적화**: 숫자 타입 다운캐스트 및 낮은 카디널리티 문자열을 category로 변환 (50-70% 감소)
   - int64 → int32/int16
   - float64 → float32
   - object → category (반복 값의 경우)

3. **명시적 메모리 정리**: 즉시 메모리를 해제하기 위해 대규모 작업 후 `gc.collect()` 사용

4. **결합 효과**: 시각화 작업의 총 메모리 공간을 90% 이상 줄일 수 있음

### Config.yaml 자동 로드
파라미터가 `None`일 때 config에서 멀티프로세싱 설정이 자동으로 로드됩니다.

## 타임존 처리

시간별 필터링은 순수 및 타임존 인식 타임스탬프를 모두 지원합니다:
- 로그 포맷 파일의 타임존 (`timezone` 필드)
- 필터 파라미터의 ISO 8601 포맷이 로그 타임존을 오버라이드
- 비교 호환성을 보장하기 위한 자동 변환

## JSON Lines 포맷

모든 필터링된 출력은 JSON Lines (줄당 하나의 JSON 객체)를 사용합니다:
- 중간 포맷으로 모든 로그 포맷 지원
- 다운스트림 도구를 위해 재파싱 용이
- 스트리밍 처리와 호환
