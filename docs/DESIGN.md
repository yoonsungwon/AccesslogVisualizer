# 설계 문서

Access Log Analyzer의 설계 철학, MCP 도구 사양 및 상세 구현 가이드를 설명합니다.

**관련 문서:**
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 기술적 아키텍처 및 모듈 구조
- [API_REFERENCE.md](./API_REFERENCE.md) - 함수 시그니처 및 매개변수
- [USAGE_EXAMPLES.md](./USAGE_EXAMPLES.md) - Python API 사용 예제
- [WORKFLOWS.md](./WORKFLOWS.md) - 일반적인 워크플로우

## 개요

Access Log Analyzer는 대용량 웹 서버 접근 로그를 분석하기 위한 MCP(Model Context Protocol) 도구입니다. 이 도구는 LLM과의 자연어 상호작용을 통해 복잡한 로그 분석 작업을 파이프라인 형태로 구성하여 효율적으로 수행할 수 있도록 설계되었습니다.

### 핵심 개념

**파이프라인 기반 분석**: 리눅스 쉘의 파이프(|) 개념을 차용하여, 여러 분석 도구들을 순차적으로 연결하여 복잡한 분석 작업을 수행합니다. 예를 들어:

```
로그파일 → 시간필터링 → URL추출 → 패턴매칭 → 통계계산 → 그래프생성
```

**자연어 명령어 처리**: 사용자가 자연어로 분석 요구사항을 표현하면, LLM이 이를 적절한 도구 체인으로 변환하여 실행합니다.

예시 명령어:
> "8월 8일 9시부터 10시까지 URL들 중에 호출이 1000건 이상이었던 URL들 중 응답시간 평균 top 5의 xlog를 그려줘"

### 주요 특징

1. **대용량 로그 처리**: 1GB 이상의 대용량 접근 로그 파일을 효율적으로 처리
2. **유연한 파싱**: 다양한 로그 포맷에 대한 자동 감지 및 파싱
3. **실시간 통계**: 시계열 기반의 실시간 통계 및 이상 징후 탐지
4. **시각화**: xlog, 트래픽 그래프 등 다양한 형태의 시각화 제공
5. **패턴 기반 분석**: URI 패턴 추출 및 매칭을 통한 구조화된 분석

### 사용 시나리오

- **성능 모니터링**: 특정 시간대의 응답 시간 분석
- **트래픽 분석**: URL별, 클라이언트별 접근 패턴 분석
- **이상 징후 탐지**: 비정상적인 응답 시간이나 에러율 증가 탐지
- **용량 계획**: 시간대별 트래픽 패턴을 통한 리소스 계획 수립
- **보안 분석**: 의심스러운 IP나 패턴의 접근 로그 분석

### 아키텍처

```
[사용자 자연어 명령] 
    ↓
[LLM 명령 해석기]
    ↓
[도구 체인 구성기]
    ↓
[파이프라인 실행 엔진]
    ↓
[결과 시각화/리포트]
```

## 로그 포맷 추천/보정 설계

### 목표
- 다양한 접근 로그를 자동으로 인식/분석할 수 있도록 포맷을 추천하고, 지정 포맷으로 파싱 수행 후 실패한 라인에 대해 포맷 보정을 제안하는 폐루프 제공.
- 사용자가 타임존을 명시하지 않은 시간 파라미터는 기본적으로 "각 로그 라인의 타임존"을 따름.

### 처리 흐름(개요)
1. 샘플 수집: 입력 파일에서 n줄 샘플 추출(랜덤/헤드/구간별).
2. 타입 탐지: ALB/JSON/Apache(Nginx 포함)/미확정 후보 판정. 로그파일 타입이 정의된 파일이 존재할 경우, 지정한 파일 형식을 우선 탐색함
3. 포맷 후보 생성:
   - ALB: 전용 포맷(고정)
   - JSON: Jackson 토큰 기반(고정)
   - Apache/Nginx: Basjes httpd 포맷/대표 Combined/Custom, Grok 후보 함께 생성
4. 실행: 선택 포맷으로 파싱 → 성공/실패 요약
5. 실패 분석: 실패 라인의 공통 특성 분석 → 포맷 델타(추가/삭제/옵션) 제안
6. 재시도: 업데이트 포맷 재적용.

### 탐지 휴리스틱(요약)
- ALB: 라인 선두 토큰 패턴 `https 2024-...Z app/... client:port target:port ...` 탐지 → ALB 확정
- JSON: 트림 후 `{`/`[` 시작 + 유효 JSON 토큰 → JSON 확정
- Apache/유사: `IP [time] "METHOD URL PROTO" status bytes ...` 형태 혹은 `COMMON/COMBINED` 근사 → Apache 후보
- 기타: Grok 후보(ACCESSLOG 공용 패턴 조합) 생성

### 신뢰도(Confidence) 산출
- 특징 일치율(토큰/구문/타임스탬프/상태코드/따옴표/대괄호 등)
- 후보 포맷으로 샘플 파싱 성공률
- 분포 일관성(상태코드/시간 범위/응답시간/바이트 분포)

### 실패 분석 규칙(예)
- bytes가 `-`로 표기 → `%b` 대신 `%B` 또는 `-` 허용
- referer/agent 부재 → `"%{Referer}i" "%{User-Agent}i"` 제거/옵션화
- 응답시간 토큰 누락 → `%D`(마이크로초) 또는 `%{ms}T` 추가 후보
- 타임존 표기 차이 → `%t` 패턴/타임존 보정
- 파싱에 실패한 라인은 화면에 출력함함 

### 시간/타임존 정책
- 사용자가 시간 파라미터에 타임존을 명시하지 않으면, 해당 라인의 타임존(ISO-8601의 Zone 또는 Apache `[YYYY-MM-DD:hh:mm:ss Z]`의 `Z`)을 차용하여 비교.
- 문서 전역: "시간 파라미터의 타임존은 명시되지 않은 경우 access log 라인의 타임존을 따릅니다."

### MCP 도구: recommendAccessLogFormat

- **목적**: 접근 로그의 포맷을 자동 탐지해 최종 패턴을 반환
- **기본 정책**: 타임존 미지정 시 `fromLog`(각 라인의 타임존) 사용

#### 입력 파라미터(간소화)
```json
{
  "inputFile": "string"
}
```

#### 반환 값(필수 핵심만)
```json
{
  "logFormatFile": "string (생성된 로그 포맷 JSON 파일 경로)",
  "logPattern": "string",
  "patternType": "HTTPD|GROK|JSON|ALB",
  "fieldMap": {
    "type": "string",
    "timestamp": "string",
    "loadbalancer": "string",
    "clientIp": "string",
    "targetIp": "string",
    "request_processing_time": "float",
    "target_processing_time": "float",
    "response_processing_time": "float",
    "elb_status_code": "int",
    "target_status_code": "int",
    "received_bytes": "int",
    "sent_bytes": "int",
    "request_verb": "str",
    "url": "string",
    "request_proto": "str",
    "user_agent": "string",
    "request_creation_time": "string",
    "target_group_arn": "string",
    "actions_executed": "string",
    "redirect_url": "string"
  },
  "responseTimeUnit": "s|ms|us|ns",
  "timezone": "string",
  "successRate": "number (0~1)",
  "confidence": "number (0~1)"
}
```

#### MCP 도구 정의 예시
```json
{
  "name": "recommendAccessLogFormat",
  "description": "접근 로그 포맷을 자동 추천하여 최종 패턴을 반환합니다.",
  "parameters": {
    "type": "object",
    "required": ["inputFile"],
    "properties": {
      "inputFile": { "type": "string" }
    }
  },
  "returns": {
    "type": "object",
    "required": [
      "logFormatFile","logPattern","patternType","fieldMap",
      "responseTimeUnit","timezone","successRate","confidence"
    ]
  }
}
```

#### 권장 전달 방식
- 도구 간 데이터 전달은 파일 기반을 우선합니다.
- `recommendAccessLogFormat`는 `logFormatFile`(JSON) 아티팩트를 생성하고 경로를 반환합니다. 생성되는 파일은 입력 파일과 동일한 디렉토리에 저장됩니다.
- 이후 단계(`parseLogFile`, `filterByCondition` 등)는 `logFormatFile`을 우선 사용하고, 없을 경우 `logPattern` 문자열을 사용할 수 있습니다.
- 우선순위: `logFormatFile` > `logPattern` > 자동 감지

## MCP 도구 목록

### 1. 로그 파싱 및 기본 처리 도구

#### 1.1 parseAccessLog
- **기능**: 한 줄의 access log를 파싱 (지정된 패턴 사용)
- **파라미터**: 
  - `logLine` (String): 파싱할 로그 라인
  - `logPattern` (String, 필수): 로그 패턴
- **반환**: 파싱된 로그 객체 (ip, time, method, url, status, bytes, referer, agent, responseTimeMs 등)

#### 1.2 recommendAccessLogFormat
- **기능**: 접근 로그 포맷 자동 추천 (logFormatFile > logPattern > 자동 감지)
- **파라미터**:
  - `inputFile` (String): 입력 로그 파일 경로
- **반환**: logFormatFile(JSON) 경로, logPattern, patternType, fieldMap, responseTimeUnit, timezone, successRate, confidence

### 2. 필터링 도구

#### 2.1 filterByCondition
- **기능**: Access log를 다양한 조건으로 필터링
- **지원 조건**: time, statusCode, responseTime, client, urls, uriPatterns
- **파라미터**:
  - `inputFile` (String): 입력 로그 파일 경로 (절대 경로 또는 working directory 기준)
  - `logFormatFile` (String): 로그 포맷 파일 경로 (recommendAccessLogFormat 결과)
  - `condition` (String): 필터링 조건 ('time','statusCode','responseTime','client','urls','uriPatterns')
  - `params` (String): 조건별 파라미터 문자열
    - 시간 필터링: `'startTime=2024-08-08T09:00:00;endTime=2024-08-08T10:00:00'`
    - 상태코드 필터링: `'statusCodes=2xx,5xx'`
    - 응답시간 필터링: `'minMs=500;maxMs=2000'` 또는 `'min=0.5s;max=2s'`
    - 클라이언트 필터링: `'clientIps=172.168.0.0/16,10.0.0.5'`
    - URL 필터링: `'urlsFile=urls.txt'`
    - URI 패턴 필터링: `'urisFile=uris.txt'`
- **반환**: 필터링된 파일 경로와 메타데이터
- **참고**: time, responseTime는 초기 버전에서 통과 처리(메타 정보만 반환)

### 3. URL 및 URI 패턴 도구

#### 3.1 extractUriPatterns
- **기능**: URI 패턴/URL 추출 (extractionType: 'urls'|'patterns'). Path variable을 *로 처리하는 기능 포함.
- **파라미터**:
  - `inputFile` (String): 입력 로그 파일 경로 (절대 경로 또는 working directory 기준)
  - `logFormatFile` (String): 로그 포맷 파일 경로 (recommendAccessLogFormat 결과, 필수)
  - `extractionType` (String): 추출 타입 ('urls'|'patterns')
  - `params` (String): 파라미터 문자열
    - `includeParams=false`: 파라미터 포함 여부 (기본값: false)
    - `maxPatterns=100`: 최대 패턴 수
    - `minCount=1000`: 최소 건수
    - `maxCount=10000`: 최대 건수
    - `aggressivePathVariableDetection=true`: 적극적인 Path variable 탐지
    - `detectMixedIdPatterns=true`: 혼합 ID 패턴 탐지
    - `strategy=tailToken`: 패턴 추출 전략 (기본값: default)
- **반환**: 
  - urls 타입: URL 목록 JSON 파일 경로와 고유 URL 수
  - patterns 타입: URI 패턴 목록 JSON 파일 경로와 패턴 수
- **패턴 파일 형식**:
  - `extractionType='patterns'`일 때 생성되는 파일은 `patternRules` 배열을 포함합니다
  - 각 `patternRule`은 `pattern` (regex)과 `replacement` (패턴)로 구성됩니다
  - 예시:
    ```json
    {
      "patternRules": [
        {
          "pattern": "^api/user/getBadge/.*$",
          "replacement": "api/user/getBadge/*"
        },
        {
          "pattern": "^api/company/getDepartmentById\\?.*$",
          "replacement": "api/company/getDepartmentById?*"
        }
      ],
      "counts": {
        "api/user/getBadge/*": 1500,
        "api/company/getDepartmentById?*": 1200
      },
      "totalRequests": 10000
    }
    ```

#### 3.2 filterUriPatterns
- **기능**: URI 패턴 파일을 필터링 (포함/제외 패턴 기반)
- **파라미터**:
  - `urisFile` (String): URI 패턴 파일 경로 (extractUriPatterns의 결과 파일)
  - `params` (String): 필터링 파라미터 문자열
    - `excludePatterns`: 제외할 패턴들 (콤마로 구분, 예: '.js,.html,.svg,.png')
    - `includePatterns`: 포함할 패턴들 (콤마로 구분, 예: '.jsp,.do,.api')
    - `caseSensitive`: 대소문자 구분 여부 (기본값: false)
    - `useRegex`: 정규식 사용 여부 (기본값: false)
- **반환**: 필터링된 패턴 파일 경로와 필터링 결과 통계

### 4. 통계 분석 도구

#### 4.1 calculateStats
- **기능**: 접근 로그 통계 계산 (전체/패턴별/시간별/IP별 통계)
- **파라미터**:
  - `inputFile` (String): 입력 로그 파일 경로 (절대 경로 또는 working directory 기준)
  - `logFormatFile` (String): 로그 포맷 파일 경로 (필수)
  - `params` (String): 파라미터 문자열
    - `statsType`: 통계 종류 (콤마로 구분: 'all', 'summary', 'url', 'time', 'ip')
    - `timeInterval`: 시간 간격 ('1h', '30m', '10m', '5m', '1m')
- **반환**: 통계 결과 JSON 파일 경로와 요약 문자열

**사용 예시**:
```java
// 전체 통계 (모든 통계 포함)
calculateStats("access.log", "pattern.json", "statsType=all;timeInterval=10m")

// 요약 통계만
calculateStats("access.log", "pattern.json", "statsType=summary")

// URL 패턴별 통계만
calculateStats("access.log", "pattern.json", "statsType=url")

// 시간별 통계 (5분 간격)
calculateStats("access.log", "pattern.json", "statsType=time;timeInterval=5m")

// IP별 통계
calculateStats("access.log", "pattern.json", "statsType=ip")

// 시간별 + URL 패턴별 통계
calculateStats("access.log", "pattern.json", "statsType=time,url;timeInterval=1h")
```

**반환되는 통계 정보**:
- **전체 통계**: 전체 건수, 고유 URL/IP 수, 응답코드 분포, 응답시간 통계(avg/median/std/p10/p90/p95/p99), 바이트 통계(avg/std)
- **URL 패턴별 통계**: 각 URL 패턴별 건수, 응답코드 분포, 응답시간 통계, 바이트 통계
- **시간별 통계**: 지정된 시간 간격별 통계 (기본 10분, 1h/30m/10m/5m/1m 지원)
- **IP별 통계**: 각 IP별 통계 (IP 정보가 있는 경우)

### 5. 시각화 도구

#### 5.1 generateXlog
- **기능**: XLog(응답시간 산점도) 그래프 생성 (현재 HTML만 지원)
- **파라미터**:
  - `inputFile` (String): 입력 로그 파일 경로 (절대 경로 또는 working directory 기준)
  - `logFormatFile` (String): 로그 포맷 파일 경로 (recommendAccessLogFormat 결과, 필수)
  - `outputFormat` (String): 출력 형식 ('svg','png','html' 중 html만 지원)
- **반환**: XLog HTML 파일 경로와 트랜잭션 수
- **특징**:
  - 인터랙티브 HTML 차트
  - 드래그로 영역 선택하여 트랜잭션 테이블 팝업
  - Ctrl+마우스 휠로 줌 인/아웃
  - URL별 필터링 기능
  - 시간 범위는 로그 데이터에서 자동으로 계산

#### 5.2 generateRequestPerURI
- **기능**: Request Count per URI 시계열 그래프 생성 (현재 HTML만 지원)
- **파라미터**:
  - `inputFile` (String): 입력 로그 파일 경로 (절대 경로 또는 working directory 기준)
  - `logFormatFile` (String): 로그 포맷 파일 경로 (recommendAccessLogFormat 결과, 필수)
  - `outputFormat` (String): 출력 형식 ('svg','png','html' 중 html만 지원, 기본값: 'html')
  - `topN` (int, 선택): 표시할 Top URI 패턴 개수 (기본값: 20)
  - `interval` (String, 선택): 시간 집계 간격 (기본값: '10s')
    - 지원 형식: '1s', '10s', '1min', '5min', '1h' 등 pandas의 시간 간격 문자열
  - `patternsFile` (String, 선택): 패턴 파일 경로 (patterns_*.json 또는 uris_*.json)
    - 패턴 파일이 제공되면 해당 파일의 patternRules를 사용하여 URL을 generalize
    - 패턴 파일이 없으면 Top N 패턴을 자동 추출하여 새 패턴 파일 생성
- **반환**: 
  ```json
  {
    "filePath": "string (requestcnt_*.html)",
    "totalTransactions": "int",
    "topN": "int",
    "interval": "string",
    "patternsDisplayed": "int",
    "patternsFile": "string (사용된 또는 생성된 패턴 파일 경로)"
  }
  ```
- **특징**:
  - **인터랙티브 HTML 차트**: Plotly 기반의 고성능 WebGL 렌더링
  - **패턴 파일 기반 URL Generalization**:
    - 패턴 파일의 `patternRules`를 사용하여 URL을 generalize
    - 패턴 파일이 제공되면 해당 규칙을 우선 사용
    - 패턴 파일이 없으면 기본 generalization 로직 사용 (ID-like 세그먼트를 *로 치환)
    - 패턴에 포함되지 않는 URL은 "Others"로 그룹화
  - **y축 크기 조정**: 
    - 마우스 드래그로 박스 선택하여 확대 (zoom mode)
    - 마우스 휠로 y축 확대/축소
    - y축 수동 조정 가능 (fixedrange=False)
  - **URI Patterns 체크박스 필터링**:
    - 오른쪽 패널에 각 URI 패턴별 체크박스 제공
    - Regex 입력으로 체크박스 항목 필터링 가능
    - "All" 버튼 클릭 시 현재 필터링된 항목만 선택
    - "None" 토글 버튼으로 전체 해제
    - 실시간으로 선택한 패턴만 표시
    - Legend 클릭으로도 개별 패턴 표시/숨김 가능
  - **Hover 정보 표시**:
    - 마우스 위치의 모든 패턴 정보를 표시
    - Count와 Pattern 정보를 정렬하여 표시
    - 고정된 위치에 표시되어 항상 확인 가능
  - **Top N 개수 사용자 지정**: `topN` 파라미터로 원하는 개수만큼 표시 (기본값: 20)
  - **Interval 사용자 지정**: `interval` 파라미터로 시간 집계 간격 조정 (기본값: '10s')
  - **시간 범위 선택**: 
    - Range selector 버튼 (1h, 6h, 12h, 1d, All)
    - Range slider로 시간 범위 탐색
  - **확대/축소 기능**:
    - 드래그로 박스 선택하여 확대
    - Plotly 툴바 버튼 (pan, zoom, reset, select, lasso 등)
    - 더블 클릭으로 리셋
  - **시간 범위 자동 계산**: 로그 데이터에서 자동으로 시간 범위 계산
  - **Others 패턴 표시**: 패턴에 포함되지 않는 모든 URL을 "Others"로 그룹화하여 표시

#### 5.3 createPivotVisualization
- **기능**: Excel 피벗 테이블 스타일의 유연한 집계 및 시각화 (다양한 차원과 메트릭 조합 지원)
- **파라미터**:
  - `inputFile` (String): 입력 로그 파일 경로 (절대 경로 또는 working directory 기준)
  - `logFormatFile` (String): 로그 포맷 파일 경로 (recommendAccessLogFormat 결과, 필수)
  - `rowField` (String, 필수): 행 차원 필드 (예: 'url', 'client_ip', 'status', 'method')
  - `columnField` (String, 필수): 열 차원 필드 (예: 'time', 'status', 'method', 'elb_status_code')
  - `valueField` (String, 필수): 집계할 값 필드 (예: 'count', 'sent_bytes', 'target_processing_time', 'error_rate')
  - `valueAggFunc` (String, 선택): 집계 함수 (기본값: 'count')
    - 지원 함수: 'count', 'sum', 'avg', 'min', 'max', 'p50', 'p90', 'p95', 'p99', 'error_rate'
  - `rowFilter` (String, 선택): 행 필터링 조건
    - 형식: `'top:N:agg_func:field'` (예: 'top:20:sum:sent_bytes' - sent_bytes 합계 상위 20개)
    - 형식: `'threshold:field:operator:value'` (예: 'threshold:sent_bytes:>:1000000' - 1MB 이상)
  - `topN` (int, 선택): 표시할 상위 행 수 (기본값: 20)
  - `chartType` (String, 선택): 차트 타입 (기본값: 'line')
    - 지원 타입: 'line', 'bar', 'heatmap', 'area', 'stacked_bar', 'stacked_area', 'facet'
  - `outputFormat` (String, 선택): 출력 형식 ('html' 또는 'json', 기본값: 'html')
  - `params` (String, 선택): 추가 파라미터 문자열
    - `timeInterval`: 시간 집계 간격 (예: '1h', '30m', '10m', '5m', '1m')
    - `statusGroups`: Status code 그룹핑 (예: '2xx,4xx,5xx')
- **반환**:
  ```json
  {
    "filePath": "string (pivot_*.html 또는 pivot_*.json)",
    "chartType": "string",
    "rows": "int (피벗 테이블 행 수)",
    "columns": "int (피벗 테이블 열 수)",
    "totalRecords": "int (전체 레코드 수)",
    "outputFormat": "string"
  }
  ```
- **사용 예시**:
  ```python
  # 케이스 1: sent_bytes 상위 20개 URI의 시간대별 호출건수
  createPivotVisualization(
      inputFile="access.log.gz",
      logFormatFile="format.json",
      rowField="url",
      columnField="time",
      valueField="count",
      valueAggFunc="count",
      rowFilter="top:20:sum:sent_bytes",
      chartType="line",
      params="timeInterval=1h"
  )

  # 케이스 2: Status Code별 분석 (히트맵)
  createPivotVisualization(
      inputFile="access.log.gz",
      logFormatFile="format.json",
      rowField="url",
      columnField="elb_status_code",
      valueField="count",
      valueAggFunc="count",
      rowFilter="top:10:count",
      chartType="heatmap",
      params="statusGroups=2xx,4xx,5xx"
  )

  # 케이스 3: 응답시간 p95 분석
  createPivotVisualization(
      inputFile="access.log.gz",
      logFormatFile="format.json",
      rowField="url",
      columnField="time",
      valueField="target_processing_time",
      valueAggFunc="p95",
      rowFilter="top:15:avg:target_processing_time",
      chartType="heatmap",
      params="timeInterval=5m"
  )

  # 케이스 4: Client IP별 트래픽 분석
  createPivotVisualization(
      inputFile="access.log.gz",
      logFormatFile="format.json",
      rowField="client_ip",
      columnField="time",
      valueField="sent_bytes",
      valueAggFunc="sum",
      rowFilter="top:20:sum:sent_bytes",
      chartType="stacked_area",
      params="timeInterval=10m"
  )

  # 케이스 5: 에러율 분석 (다차원 facet)
  createPivotVisualization(
      inputFile="access.log.gz",
      logFormatFile="format.json",
      rowField="url",
      columnField="time",
      valueField="error_rate",
      valueAggFunc="error_rate",
      rowFilter="top:12:count",
      chartType="facet",
      params="timeInterval=30m"
  )
  ```
- **특징**:
  - **Excel 피벗 테이블 스타일**: 행, 열, 값을 자유롭게 조합하여 다차원 분석
  - **다양한 집계 함수**: count, sum, avg, percentile (p50, p90, p95, p99), error_rate
  - **유연한 필터링**:
    - 상위 N개 추출 (임의의 필드 기준 집계)
    - 임계값 기반 필터링
  - **다양한 차트 타입**:
    - **line**: 시계열 라인 차트 (트렌드 분석)
    - **bar**: 그룹 바 차트 (비교 분석)
    - **heatmap**: 히트맵 (패턴 발견)
    - **area**: 영역 차트 (누적 트렌드)
    - **stacked_bar**: 스택 바 차트 (구성 비율)
    - **stacked_area**: 스택 영역 차트 (누적 구성)
    - **facet**: 소형 다중 차트 (개별 트렌드 비교)
  - **자동 시간 버킷팅**: columnField='time'일 때 지정된 간격으로 자동 그룹핑
  - **Status Code 그룹핑**: 2xx, 3xx, 4xx, 5xx로 자동 그룹화 가능
  - **Plotly 인터랙티브 차트**: 줌, 팬, hover, 범례 필터링 등 지원
  - **JSON 출력**: 피벗 테이블을 JSON으로 저장하여 후처리 가능

### 도구 요약 표

| 진행 | 이름 | 설명 | 중요도 | 우선순위 | 난이도 | 비고 |
|:--:|---|---|---:|---:|---:|---|
| [v] | recommendAccessLogFormat | 로그 포맷 자동 추천(logFormatFile 생성, HTTPD/ALB/JSON/GROK) | 최상 | 1 | 중 | `logFormatFile` > `logPattern` > 자동 감지; responseTimeUnit/timezone 포함; 절대 경로 반환 |
| [v] | parseAccessLog | 한 줄의 access log 파싱 (지정된 패턴 사용) | 중 | 1 | 하 | 디버깅 및 테스트용 |
| [v] | filterByCondition | 통합 필터링(time/statusCode/responseTime/client/urls/uriPatterns) | 최상 | 1 | 중 | 파이프라인 허브; 입력 검증 및 절대 경로 반환 |
| [v] | calculateStats | 전체/패턴별/시간별/IP별 통계 | 상 | 1 | 중 | statsType/timeInterval 파라미터 지원; 절대 경로 반환 |
| [v] | generateXlog | 시계열 응답시간 산점도 (인터랙티브 HTML) | 상 | 1 | 중 | timeRange/outputFormat; 입력 검증 및 절대 경로 반환 |
| [v] | generateRequestPerURI | URI별 시계열 그래프  (인터랙티브 HTML) | 상 | 1 | 중 | topN/interval/patternsFile 파라미터 지원; 패턴 파일 기반 URL generalization; Others 패턴 처리; 체크박스 필터링(Regex 지원); Hover 정보 표시 |
| [v] | extractUriPatterns | URL/URI 패턴 추출 | 상 | 1 | 상 | patternRules 자동 생성; 절대 경로 반환; 입력 검증 |
| [v] | filterUriPatterns | URI 패턴 필터링(포함/제외 패턴) | 중 | 1 | 하 | excludePatterns/includePatterns 지원 |
| [v] | createPivotVisualization | Excel 피벗 스타일 유연한 집계/시각화 | 최상 | 1 | 상 | 7가지 차트 타입; 다양한 집계 함수(p50/p95/p99/error_rate); 유연한 행/열 필터링; 다차원 분석 지원 |

## 패턴 파일 및 URL Generalization 설계

### 개요

Access Log Analyzer는 패턴 파일 기반의 URL generalization을 지원합니다. 이를 통해 동일한 URI 패턴을 가진 URL들을 그룹화하여 분석할 수 있습니다.

### 패턴 파일 구조

#### 1. Pattern Rules 형식 (권장)

패턴 파일은 `patternRules` 배열을 포함하며, 각 규칙은 regex 패턴과 replacement 패턴으로 구성됩니다:

```json
{
  "patternRules": [
    {
      "pattern": "^api/user/getBadge/.*$",
      "replacement": "api/user/getBadge/*"
    },
    {
      "pattern": "^api/company/getDepartmentById\\?.*$",
      "replacement": "api/company/getDepartmentById?*"
    },
    {
      "pattern": "^web/environment\\?.*$",
      "replacement": "web/environment?*"
    }
  ],
  "totalPatterns": 20,
  "extractedAt": "2025-11-04T14:45:44.364584",
  "sourceFile": "issue.gz",
  "topN": 20
}
```

**특징**:
- `pattern`: 정규식 패턴 (URL 매칭용)
- `replacement`: 일반화된 패턴 (치환 결과)
- 패턴 파일 생성 시 자동으로 `patternRules` 생성
- `patterns` 필드는 더 이상 사용하지 않음 (하위 호환을 위해 로드 시 변환 지원)

#### 2. 패턴 파일 생성

`extractUriPatterns` 함수는 `extractionType='patterns'`일 때 패턴 파일을 생성합니다:

1. URL 리스트에서 패턴 추출 (ID-like 세그먼트를 *로 치환)
2. 각 패턴에 대해 regex 규칙 생성:
   - 패턴의 `*`를 `.*`로 변환
   - 특수 문자는 escape 처리
   - `^pattern$` 형식으로 전체 매칭
3. `patternRules` 배열에 저장
4. JSON 파일로 저장

**생성 위치**: 입력 파일과 동일한 디렉토리
**파일명 형식**: `uris_YYMMDD_HHMMSS.json` 또는 `patterns_YYMMDD_HHMMSS.json`

### URL Generalization 프로세스

#### 1. 패턴 파일 기반 Generalization

`_generalize_url` 함수는 패턴 파일이 제공되면 해당 규칙을 우선 사용합니다:

```python
def _generalize_url(url, patterns_file=None):
    """
    패턴 파일의 규칙을 사용하여 URL을 generalize합니다.
    
    프로세스:
    1. 패턴 파일 로드 (캐싱 지원)
    2. 각 patternRule의 regex로 URL 매칭 시도
    3. 첫 번째 매칭되는 규칙의 replacement 반환
    4. 매칭되지 않으면 기본 generalization 로직 사용
    """
```

**동작 순서**:
1. 패턴 파일 로드 (`_load_pattern_rules`)
   - 파일이 이미 로드되었으면 캐시 사용
   - `patternRules` 배열에서 regex 규칙 생성
   - 각 규칙을 `re.compile()`로 컴파일하여 저장
2. URL 매칭
   - 각 규칙의 `pattern`으로 URL 전체 매칭 시도
   - 첫 번째 매칭되는 규칙의 `replacement` 반환
3. Fallback
   - 모든 규칙과 매칭되지 않으면 기본 generalization 사용
   - ID-like 세그먼트를 *로 치환

#### 2. 기본 Generalization (Fallback)

패턴 파일이 없거나 매칭되지 않는 경우:

1. URL을 path와 query로 분리
2. Path를 세그먼트로 분할
3. 각 세그먼트가 ID-like인지 확인:
   - 숫자만 있는 경우
   - UUID 형식
   - 긴 hex 문자열
   - 대부분 숫자로 구성된 긴 문자열
4. ID-like 세그먼트를 *로 치환
5. Query 파라미터가 있으면 `?*` 추가

#### 3. 패턴 파일 사용 예시

```python
# 1. 패턴 파일 생성
result = extractUriPatterns(
    "access.log",
    "logformat.json",
    "patterns",
    "maxPatterns=50;minCount=100"
)
# 결과: uris_251104_144544.json 생성

# 2. 패턴 파일을 사용하여 시각화
result = generateRequestPerURI(
    "access.log",
    "logformat.json",
    "html",
    topN=20,
    interval="10s",
    patternsFile="uris_251104_144544.json"  # 패턴 파일 사용
)
# 패턴 파일의 규칙으로 URL generalize
# 패턴에 포함되지 않는 URL은 "Others"로 표시
```

### Others 패턴 처리

#### 1. Others 패턴 생성

`generateRequestPerURI` 함수는 다음과 같이 Others 패턴을 처리합니다:

1. **패턴 파일 사용 시**:
   - 패턴 파일의 `patternRules`로 URL generalize
   - 패턴 파일의 `replacement` 목록에 포함되지 않는 패턴을 "Others"로 마킹
   
2. **Top N 추출 시**:
   - Top N 패턴 선택
   - 나머지 패턴을 "Others"로 마킹

#### 2. Others 표시

- 시각화에서 "Others"는 회색으로 표시
- 체크박스 패널에 "Others" 항목 포함
- Others 패턴도 일반 패턴과 동일하게 필터링 및 표시/숨김 가능

#### 3. 구현 예시

```python
# 패턴 파일 로드 후
if top_patterns:
    # 패턴에 포함되지 않는 항목을 "Others"로 마킹
    log_df.loc[
        ~log_df['url_pattern'].isin(top_patterns) & 
        (log_df['url_pattern'] != 'Unknown'), 
        'url_pattern'
    ] = 'Others'
```

### 패턴 파일 재사용

#### 1. 자동 감지

`generateRequestPerURI` 함수는 입력 파일과 동일한 디렉토리에서 기존 패턴 파일을 자동으로 감지합니다:

1. `patterns_*.json` 파일 검색
2. 수정 시간 기준으로 최신순 정렬
3. 사용자에게 기존 파일 사용 여부 확인
4. 선택한 파일을 사용하거나 새로 생성

#### 2. 패턴 파일 정보 표시

패턴 파일 정보를 상세히 표시:

```
Found 3 pattern file(s) in the directory:
  1. patterns_251104_144544.json (20 pattern rules, 1234 bytes)
  2. patterns_251103_120000.json (15 pattern rules, 987 bytes)
  3. patterns_251102_090000.json (25 pattern rules, 1567 bytes)

Use existing pattern file? (y/n, default: n): y
Select file number (1-3): 1
✓ Using pattern file: patterns_251104_144544.json
```

### MCP Tool 통합

모든 MCP Tool은 다음과 같은 개선사항을 포함합니다:

#### 1. 입력 검증

- 파일 존재 여부 확인
- 필수 파라미터 검증
- 파라미터 값 유효성 검증 (예: condition, extractionType)

#### 2. 절대 경로 반환

- 모든 `filePath` 반환값은 절대 경로로 변환
- `Path.resolve()` 사용하여 상대 경로를 절대 경로로 변환

#### 3. 에러 처리

- 명확한 에러 메시지 제공
- 예외 발생 시 상세한 트레이스백 포함 (개발 모드)

#### 4. MCP 서버 등록

`mcp_server.py`를 통해 모든 도구를 MCP Tool로 등록:

- Claude Desktop과 통합 가능
- Python MCP 클라이언트로 호출 가능
- 자세한 내용은 `MCP_TOOL_REGISTRATION.md` 참조

## 시각화 고급 기능

### generateRequestPerURI 고급 기능

#### 1. 체크박스 패널

**위치**: 화면 오른쪽 고정 위치

**기능**:
- Regex 입력 필드로 패턴 필터링
- "All" 버튼: 현재 필터링된 항목만 선택
- "None" 버튼: 모든 항목 해제
- 각 패턴별 체크박스로 개별 표시/숨김 제어
- 패턴 색상 표시 (Plotly 기본 팔레트)

#### 2. Hover 정보 표시

**위치**: 화면 오른쪽 하단 고정 위치

**기능**:
- 마우스 위치의 모든 패턴 정보 표시
- Count와 Pattern 정보를 정렬하여 표시
- 여러 패턴이 같은 시간에 있을 경우 모두 표시
- Count 내림차순 정렬

#### 3. JavaScript 초기화

**DOM 준비 확인**:
- `waitForPlotly()` 함수로 DOM과 Plotly 로딩 확인
- 재시도 메커니즘으로 안정적인 초기화
- 콘솔 로그로 디버깅 지원

### 패턴 파일 통합 워크플로우

```
1. 로그 파일 분석
   ↓
2. extractUriPatterns로 패턴 추출
   → patterns_YYMMDD_HHMMSS.json 생성 (patternRules 포함)
   ↓
3. 패턴 파일 검토 및 수정 (선택사항)
   → patternRules 수정 가능
   ↓
4. generateRequestPerURI로 시각화
   → patternsFile 파라미터로 패턴 파일 지정
   → patternRules로 URL generalize
   → Others 패턴 자동 처리
   ↓
5. 시각화 결과 확인
   → 체크박스로 패턴 필터링
   → Hover로 상세 정보 확인
```

## 구현 세부사항

### 패턴 규칙 변환 알고리즘

패턴의 `*`를 regex `.*`로 변환하는 알고리즘:

```python
def convert_pattern_to_regex(pattern):
    """
    1. *를 임시 플레이스홀더로 치환 (__WILDCARD__)
    2. 특수 문자 escape 처리
    3. 플레이스홀더를 .*로 치환
    4. ^pattern$ 형식으로 감싸기
    """
    temp_pattern = pattern.replace('*', '__WILDCARD__')
    escaped_pattern = re.escape(temp_pattern)
    regex_pattern = escaped_pattern.replace('__WILDCARD__', '.*')
    return f'^{regex_pattern}$'
```

**예시**:
- 입력: `api/user/getBadge/*`
- 출력: `^api/user/getBadge/.*$`

### 캐싱 메커니즘

패턴 규칙은 전역 캐시로 관리됩니다:

```python
_pattern_rules_cache = None  # 컴파일된 규칙 리스트
_pattern_rules_file = None   # 현재 로드된 파일 경로

def _load_pattern_rules(patterns_file=None):
    """
    - 같은 파일이면 캐시 사용
    - 다른 파일이면 캐시 클리어 후 재로드
    - 파일이 없으면 None 반환
    """
```

이를 통해 동일한 패턴 파일을 여러 번 사용할 때 성능이 향상됩니다.

### Others 패턴 처리 로직

```python
# 1. 패턴 파일에서 패턴 추출
top_patterns = [rule['replacement'] for rule in pattern_rules]

# 2. URL generalize (패턴 규칙 사용)
log_df['url_pattern'] = log_df[url_field].apply(
    lambda x: _generalize_url(x, patterns_file)
)

# 3. 패턴에 포함되지 않는 항목을 Others로 마킹
log_df.loc[
    ~log_df['url_pattern'].isin(top_patterns) & 
    (log_df['url_pattern'] != 'Unknown'), 
    'url_pattern'
] = 'Others'
```

## 데이터 전달 설계

### 파이프라인 데이터 전달 방식

모든 데이터 전달은 **파일 기반**으로 통일하여 단순하고 일관된 인터페이스를 제공합니다.

#### 파일 기반 전달
- **입력**: 파일 경로 + 파라미터들
- **출력**: JSON 형태로 파일 경로와 의미있는 정보 반환
- **Prefix 구분**: 파일 형식과 내용을 prefix로 구분
  - `original_`: 원본 로그 파일
  - `filtered_`: 필터링된 로그 (JSON Lines)
  - `urls_`: URL 추출 결과 (URL 목록)
  - `stats_`: 통계 데이터 (JSON)
  - `uris_`: URI 패턴 목록 (JSON)
  - `xlog_`: XLog 그래프 (HTML)
  - `requestcnt_`: Request Count per URI 그래프 (HTML)
  - `csv_`: 구조화된 데이터
  - `json_`: JSON 형태의 데이터

#### 파라미터 기반 조건 설정
- **시간 범위**: `startTime`, `endTime` 파라미터
- **필터 조건**: `statusCode`, `minMs`, `maxMs` (또는 `min`, `max`로 초/밀리초 단위 지정) 등
- **통계 옵션**: `metrics` 배열, `topN` 값 등
- **처리 옵션**: `includeParams`, `groupBy` 등

**장점**: 
- 메모리 효율적, 대용량 데이터 처리 가능
- 확장자로 파일 형식 명확히 구분
- 단순하고 일관된 인터페이스
- LLM이 이해하기 쉬운 구조

### 도구 간 인터페이스 설계

#### 단계별 도구 호출 설계

**LLM 호출 방식**: LLM은 한 번에 하나의 도구만 호출하고, JSON 결과를 받아서 다음 단계를 결정합니다.

**사용자 요청 예시**: "8월 8일 9시부터 10시까지 URL들 중에 호출이 1000건 이상이었던 URL들 중 응답시간 평균 top 5의 xlog를 그려줘"

**LLM이 단계별로 해석하여 실행**:
1. 시간 필터링: "8월 8일 9시부터 10시까지" → `filterByCondition(condition: "time", startTime: "09:00", endTime: "10:00")`
2. URL 추출: "URL들" → `extractUriPatterns(extractionType: "urls")`
3. 패턴 매칭: "호출이 1000건 이상" → `extractUriPatterns(extractionType: "patterns", minCount: 1000)`
4. 통계 계산: "응답시간 평균" → `calculateStats(statsType: "url")`
5. 정렬: "응답시간 평균 기준" → (통계 결과에서 정렬)
6. Top 5 추출: "top 5" → (통계 결과에서 상위 5개)
7. 재필터링: Top 5 URL로 다시 필터링 → `filterByCondition(condition: "urls", urlsFile: top5Urls)`
8. XLog 생성: "xlog를 그려줘" → `generateXlog()`

**기본 도구 호출 패턴**:
```java
// 1단계: 시간 필터링
// 호출: filterByCondition("access.log", "pattern.json", "time", "startTime=2024-08-08T09:00:00;endTime=2024-08-08T10:00:00")
// 리턴:
{
  "filePath": "./filtered_1703123456789.log",
  "recordCount": 15000,
  "fileSize": "45MB"
}

// 2단계: URL 추출  
// 호출: extractUriPatterns("filtered_1703123456789.log", "pattern.json", "urls", "includeParams=false")
// 리턴:
{
  "filePath": "./urls_1703123456790.json",
  "uniqueUrls": 1250,
  "totalRequests": 15000
}

// 3단계: URI 패턴 추출 (1000건 이상)
// 호출: extractUriPatterns("filtered_1703123456789.log", "pattern.json", "patterns", "minCount=1000;maxPatterns=100")
// 리턴:
{
  "filePath": "./uris_1703123456791.json",
  "patternsFound": 15
}

// 4단계: 통계 계산
// 호출: calculateStats("filtered_1703123456789.log", "pattern.json", "statsType=url;timeInterval=10m")
// 리턴:
{
  "filePath": "./stats_1703123456792.json",
  "top5Urls": [
    {"url": "/api/users/*", "avgResponseTime": 1200, "count": 5000},
    {"url": "/api/products/*", "avgResponseTime": 800, "count": 3000}
  ]
}

// 5단계: Top 5 URL로 재필터링
// 호출: filterByCondition("filtered_1703123456789.log", "pattern.json", "urls", "urlsFile=stats_1703123456792.json")
// 리턴:
{
  "filePath": "./filtered_1703123456795.log",
  "filteredCount": 8000
}

// 6단계: XLog 생성
// 호출: generateXlog("filtered_1703123456795.log", "pattern.json", "html")
// 리턴:
{
  "filePath": "./xlog_1703123456796.html",
  "totalTransactions": 8000
}
```

**JSON 반환의 장점**: 
- LLM이 파일 경로뿐만 아니라 의미있는 정보도 함께 이해 가능
- 다음 단계에서 필요한 정보를 쉽게 추출 가능
- 결과의 품질과 의미를 즉시 파악 가능
- Prefix 기반 파일명으로 파일 형식과 내용을 명확히 구분

#### 단순한 도구 인터페이스

**각 도구는 독립적으로 동작**: 복잡한 파이프라인 관리 없이, 각 도구가 입력 파일을 받아서 출력 파일을 생성합니다.

```java
// 각 도구는 독립적인 함수로 구현
public class AccessLogTools {
    
    // 통합 필터링 도구
    public String filterByCondition(String inputFile, String logFormatFile, String condition, String params) {
        String outputFile = generateOutputFile("filtered");
        
        switch (condition) {
            case "time":
                // 시간 필터링 로직
                return "Access log 필터링 결과\n\n" +
                       "입력 파일: " + inputFile + "\n" +
                       "필터 조건: " + condition + "\n" +
                       "총 라인 수: 15000\n" +
                       "필터링된 라인 수: 12000\n" +
                       "출력 파일: " + outputFile + "\n";
                
            case "urls":
                // URL 목록 기반 필터링 로직
                return "Access log 필터링 결과\n\n" +
                       "입력 파일: " + inputFile + "\n" +
                       "필터 조건: " + condition + "\n" +
                       "총 라인 수: 15000\n" +
                       "필터링된 라인 수: 8000\n" +
                       "출력 파일: " + outputFile + "\n";
                
            case "uriPatterns":
                // URI 패턴 기반 필터링 로직
                return "Access log 필터링 결과\n\n" +
                       "입력 파일: " + inputFile + "\n" +
                       "필터 조건: " + condition + "\n" +
                       "총 라인 수: 15000\n" +
                       "필터링된 라인 수: 8000\n" +
                       "출력 파일: " + outputFile + "\n";
                
            default:
                throw new IllegalArgumentException("Unknown condition: " + condition);
        }
    }
    
    // URI 패턴 추출 (URL 추출 포함)
    public String extractUriPatterns(String inputFile, String logFormatFile, String extractionType, String params) {
        String outputFile = generateOutputFile(extractionType.equals("urls") ? "urls" : "patterns");
        
        if (extractionType.equals("urls")) {
            // URL 추출 로직 실행
            return "URL 추출 결과\n\n" +
                   "입력 파일: " + inputFile + "\n" +
                   "추출 타입: urls\n" +
                   "총 라인 수: 15000\n" +
                   "고유 URL 수: 1250\n" +
                   "출력 파일: " + outputFile + "\n";
        } else if (extractionType.equals("patterns")) {
            // URI 패턴 추출 로직 실행
            return "URI 패턴 추출 결과\n\n" +
                   "입력 파일: " + inputFile + "\n" +
                   "추출 타입: patterns\n" +
                   "총 라인 수: 15000\n" +
                   "패턴 수: 15\n" +
                   "출력 파일: " + outputFile + "\n";
        } else {
            throw new IllegalArgumentException("Unknown extraction type: " + extractionType);
        }
    }
    
    // 통계 계산
    public String calculateStats(String inputFile, String logFormatFile, String params) {
        String outputFile = generateOutputFile("stats");
        // 통계 계산 로직 실행
        return "통계 계산 결과\n\n" +
               "입력 파일: " + inputFile + "\n" +
               "로그 포맷 파일: " + logFormatFile + "\n" +
               "전체 건수: 15000\n" +
               "고유 URL 수: 1250\n" +
               "고유 IP 수: 500\n" +
               "출력 파일: " + outputFile + "\n";
    }
    
    // XLog 생성
    public String generateXlog(String inputFile, String logFormatFile, String outputFormat) {
        String outputFile = generateOutputFile("xlog");
        // XLog 생성 로직 실행
        return "XLog 생성 결과\n\n" +
               "입력 파일: " + inputFile + "\n" +
               "로그 포맷 파일: " + logFormatFile + "\n" +
               "총 레코드 수: 8000\n" +
               "시간 범위: 1시간\n" +
               "응답시간 최대값(ms): 5000.00\n" +
               "출력 파일: " + outputFile + "\n" +
               "출력 형식: html (인터랙티브)\n";
    }
    
    private String generateOutputFile(String prefix) {
        return String.format("./%s_%d.log", 
            prefix, System.currentTimeMillis());
    }
}
```

**LLM 사용 예시**:
```java
// LLM이 단계별로 호출
AccessLogTools tools = new AccessLogTools();

// 각 단계를 순차적으로 실행
String filtered = tools.filterByCondition("access.log", "pattern.json", "time", "startTime=2024-08-08T09:00:00;endTime=2024-08-08T10:00:00");
String urls = tools.extractUriPatterns("filtered_1703123456789.log", "pattern.json", "urls", "includeParams=false");
String patterns = tools.extractUriPatterns("filtered_1703123456789.log", "pattern.json", "patterns", "minCount=1000;maxPatterns=100");
String stats = tools.calculateStats("filtered_1703123456789.log", "pattern.json", "statsType=url;timeInterval=10m");
String xlog = tools.generateXlog("filtered_1703123456795.log", "pattern.json", "html");

System.out.println("분석 완료! XLog 파일: " + xlog);
```

### 최적화 전략

#### 1. 메모리 관리
- **스트리밍 처리**: 대용량 파일을 청크 단위로 처리
- **지연 로딩**: 필요할 때만 파일을 메모리에 로드
- **자동 정리**: 중간 파일들의 자동 삭제 (선택적)

#### 2. 파일 관리
- **Prefix 기반 분류**: 파일 형식과 내용을 prefix로 명확히 구분
- **타임스탬프 파일명**: 중복 방지를 위한 타임스탬프 기반 파일명 생성
- **출력 위치**: 모든 출력 파일은 입력 파일과 동일한 디렉토리에 저장

### 구현 예시

**사용자 요청**: "8월 8일 9시부터 10시까지 URL들 중에 호출이 1000건 이상이었던 URL들 중 응답시간 평균 top 5의 xlog를 그려줘"

**LLM이 단계별로 실행**:

```java
// 1단계: 시간 필터링
// 호출: filterByCondition("access.log", "pattern.json", "time", "startTime=2024-08-08T09:00:00;endTime=2024-08-08T10:00:00")
String filtered = filterByCondition("access.log", "pattern.json", "time", "startTime=2024-08-08T09:00:00;endTime=2024-08-08T10:00:00");
// 리턴: "Access log 필터링 결과\n\n입력 파일: access.log\n필터 조건: time\n총 라인 수: 15000\n필터링된 라인 수: 12000\n출력 파일: ./filtered_1703123456789.log\n"

// 2단계: URL 추출
// 호출: extractUriPatterns("filtered_1703123456789.log", "pattern.json", "urls", "includeParams=false")
String urls = extractUriPatterns("filtered_1703123456789.log", "pattern.json", "urls", "includeParams=false");
// 리턴: "URL 추출 결과\n\n입력 파일: filtered_1703123456789.log\n추출 타입: urls\n총 라인 수: 12000\n고유 URL 수: 1250\n출력 파일: ./urls_1703123456790.json\n"

// 3단계: URI 패턴 추출 (1000건 이상)
// 호출: extractUriPatterns("filtered_1703123456789.log", "pattern.json", "patterns", "minCount=1000;maxPatterns=100")
String patterns = extractUriPatterns("filtered_1703123456789.log", "pattern.json", "patterns", "minCount=1000;maxPatterns=100");
// 리턴: "URI 패턴 추출 결과\n\n입력 파일: filtered_1703123456789.log\n추출 타입: patterns\n총 라인 수: 12000\n패턴 수: 15\n출력 파일: ./uris_1703123456791.json\n"

// 4단계: 통계 계산 (평균 응답시간)
// 호출: calculateStats("filtered_1703123456789.log", "pattern.json", "statsType=url;timeInterval=10m")
String stats = calculateStats("filtered_1703123456789.log", "pattern.json", "statsType=url;timeInterval=10m");
// 리턴: "통계 계산 결과\n\n입력 파일: filtered_1703123456789.log\n패턴 파일: pattern.json\n전체 건수: 12000\n고유 URL 수: 1250\n고유 IP 수: 500\n출력 파일: ./stats_1703123456792.json\n"

// 5단계: Top 5 URL로 재필터링
// 호출: filterByCondition("filtered_1703123456789.log", "pattern.json", "urls", "urlsFile=stats_1703123456792.json")
String top5Filtered = filterByCondition("filtered_1703123456789.log", "pattern.json", "urls", "urlsFile=stats_1703123456792.json");
// 리턴: "Access log 필터링 결과\n\n입력 파일: filtered_1703123456789.log\n필터 조건: urls\n총 라인 수: 12000\n필터링된 라인 수: 8000\n출력 파일: ./filtered_1703123456795.log\n"

// 6단계: XLog 생성
// 호출: generateXlog("filtered_1703123456795.log", "pattern.json", "html")
String xlog = generateXlog("filtered_1703123456795.log", "pattern.json", "html");
// 리턴: "XLog 생성 결과\n\n입력 파일: filtered_1703123456795.log\n패턴 파일: pattern.json\n총 레코드 수: 8000\n시간 범위: 1시간\n응답시간 최대값(ms): 5000.00\n출력 파일: ./xlog_1703123456796.html\n출력 형식: html (인터랙티브)\n"
```

**MCP 도구 정의 예시**:
```json
{
  "name": "filterByCondition",
  "description": "Access log를 다양한 조건(time/statusCode/responseTime/client/urls/urisFile)으로 필터링. 시간 파라미터의 타임존은 명시되지 않은 경우 해당 access log 라인의 타임존을 따릅니다.",
  "parameters": {
    "type": "object",
    "required": ["inputFile", "logFormatFile", "condition", "params"],
    "properties": {
      "inputFile": {"type": "string", "description": "입력 로그 파일 경로 (절대 경로 또는 working directory 기준)"},
      "logFormatFile": {"type": "string", "description": "로그 포맷 파일 경로 (recommendAccessLogFormat 결과)"},
      "condition": {"type": "string", "description": "필터링 조건 ('time','statusCode','responseTime','client','urls','uriPatterns')"},
      "params": {"type": "string", "description": "조건별 파라미터 문자열"}
    }
  },
  "returns": {"type": "string", "description": "필터링 결과 문자열 (파일 경로 + 메타데이터)"}
}
```

**파이프라인의 의미**: 각 도구가 독립적으로 실행되지만, 파일 경로를 통해 데이터가 연결되어 마치 파이프라인처럼 동작합니다.

이 도구는 기존의 복잡한 로그 분석 스크립트 작성 없이도, 자연어 명령만으로도 전문적인 로그 분석을 수행할 수 있도록 도와줍니다.

## MCP Tool 등록 및 사용

### MCP 서버 구현

Access Log Analyzer는 MCP (Model Context Protocol) 서버로 등록되어 LLM이나 다른 MCP 클라이언트에서 사용할 수 있습니다.

#### 서버 파일

`mcp_server.py` 파일에 모든 MCP Tool이 등록되어 있습니다:

- `recommendAccessLogFormat` - 로그 포맷 자동 추천
- `filterByCondition` - 조건별 필터링
- `extractUriPatterns` - URI 패턴/URL 추출
- `filterUriPatterns` - URI 패턴 필터링
- `calculateStats` - 통계 계산
- `generateXlog` - XLog 시각화
- `generateRequestPerURI` - Request Count 시각화
- `generateMultiMetricDashboard` - 대시보드 생성

#### 등록 방법

자세한 등록 방법은 `MCP_TOOL_REGISTRATION.md` 문서를 참조하세요.

**요약**:
1. `pip install mcp` 설치
2. `python mcp_server.py` 실행
3. Claude Desktop 설정 파일에 서버 추가
4. Claude Desktop 재시작

### MCP Tool 개선사항

#### 1. 입력 검증 강화

모든 MCP Tool에 입력 검증이 추가되었습니다:

```python
# 파일 존재 확인
if not inputFile or not os.path.exists(inputFile):
    raise ValueError(f"Input file not found: {inputFile}")

# 파라미터 값 검증
if condition not in ['time', 'statusCode', 'responseTime', 'client', 'urls', 'uriPatterns']:
    raise ValueError(f"Invalid condition: {condition}")
```

#### 2. 절대 경로 반환

모든 `filePath` 반환값은 절대 경로로 변환됩니다:

```python
return {
    'filePath': str(output_file.resolve()),  # 절대 경로
    ...
}
```

이를 통해 클라이언트가 파일을 정확하게 찾을 수 있습니다.

#### 3. 에러 처리 개선

- 명확한 에러 메시지
- 개발 모드에서 상세한 트레이스백
- JSON 형식으로 에러 반환

### MCP Tool 사용 예시

#### Claude Desktop과 통합

Claude Desktop 설정 파일 (`claude_desktop_config.json`):

**Windows:**
```json
{
  "mcpServers": {
    "access-log-analyzer": {
      "command": "python",
      "args": [
        "C:/path/to/AccesslogVisualizer/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "C:/path/to/AccesslogVisualizer"
      }
    }
  }
}
```

**macOS/Linux:**
```json
{
  "mcpServers": {
    "access-log-analyzer": {
      "command": "python3",
      "args": [
        "/path/to/AccesslogVisualizer/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/path/to/AccesslogVisualizer"
      }
    }
  }
}
```

**참고:** `/path/to/AccesslogVisualizer`를 실제 프로젝트 경로로 변경하세요.

#### Python 클라이언트 사용

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 로그 포맷 추천
            result = await session.call_tool(
                "recommendAccessLogFormat",
                {"inputFile": "access.log"}
            )
            print(result.content)
            
            # 패턴 추출
            result = await session.call_tool(
                "extractUriPatterns",
                {
                    "inputFile": "access.log",
                    "logFormatFile": "logformat_123.json",
                    "extractionType": "patterns",
                    "params": "maxPatterns=50;minCount=100"
                }
            )
            print(result.content)

if __name__ == "__main__":
    asyncio.run(main())
```

## 결론

Access Log Analyzer는 다음과 같은 핵심 기능을 제공합니다:

1. **자동 로그 포맷 감지**: 다양한 로그 포맷을 자동으로 인식
2. **패턴 기반 분석**: URI 패턴 추출 및 재사용 가능한 패턴 파일 생성
3. **유연한 필터링**: 다양한 조건으로 로그 필터링
4. **통계 분석**: 전체/패턴별/시간별/IP별 통계 제공
5. **인터랙티브 시각화**: 고성능 WebGL 기반 차트 및 고급 필터링 기능
6. **MCP 통합**: LLM과의 자연어 상호작용을 통한 분석 파이프라인 구성

이 도구는 대용량 로그 분석을 효율적으로 수행할 수 있도록 설계되었으며, 패턴 파일 기반의 URL generalization을 통해 일관된 분석 결과를 제공합니다.
