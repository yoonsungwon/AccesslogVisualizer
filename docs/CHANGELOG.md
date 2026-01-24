# 변경 로그

이 프로젝트의 주요 변경 사항을 기록합니다.

**관련 문서:**
- [DEVELOPMENT.md](./DEVELOPMENT.md) - 개발 가이드
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 기술적 아키텍처

## 최근 변경 사항 및 개선 사항

### Processing Time 필드 자동 매핑 개선 (2026-01-23)

**문제**: `generateProcessingTimePerURI` 함수가 다양한 로그 형식의 processing time 필드명 변형을 인식하지 못하는 문제가 있었습니다. 예를 들어, HTTPD 로그의 `response_time_us` 필드가 `target_processing_time`으로 요청되면 실패했습니다.

**해결책**:

#### 1. `data_visualizer.py` - `generateProcessingTimePerURI` 함수 개선
- **자동 필드 매핑 로직 추가**: `generateSentBytesPerURI`와 동일한 방식으로 필드 매핑 구현
- **다양한 필드명 지원**:
  - `target_processing_time`
  - `response_time`
  - `response_time_us`
  - `response_time_ms`
  - `request_processing_time`
  - `response_processing_time`
  - `elapsed_time`
  - `duration`
  - `processing_time`
  - `request_time`
- **명확한 로깅**: 실제 사용된 필드명을 로그에 출력
  ```
  INFO - Using 'response_time_us' as processing time field (requested: 'target_processing_time')
  ```

#### 2. `main.py` - 필드 가용성 확인 개선
- **Processing time variants 확장**: 모든 processing time 관련 필드에 대해 다양한 변형 추가
  ```python
  'request_processing_time': ['request_processing_time', 'request_time', 'response_time',
                               'response_time_us', 'response_time_ms', 'elapsed_time',
                               'duration', 'processing_time'],
  'target_processing_time': ['target_processing_time', 'upstream_response_time', 'response_time',
                             'response_time_us', 'response_time_ms', 'elapsed_time',
                             'duration', 'processing_time'],
  'response_processing_time': ['response_processing_time', 'response_time', 'response_time_us',
                               'response_time_ms', 'elapsed_time', 'duration', 'processing_time']
  ```

#### 3. 테스트 스크립트 추가
- **`tests/test_graph_gz.py`**: HTTPD 로그(log.gz)를 대상으로 두 가지 기능 테스트
  - `generateSentBytesPerURI`: Sent Bytes per URI (Sum & Average) 생성
  - `generateProcessingTimePerURI`: Processing Time per URI 생성
- **테스트 결과**: 모두 성공 (150,004 및 164,810 트랜잭션 처리)

#### 이점
- HTTPD, ALB, Nginx 등 다양한 로그 형식의 processing time 필드를 자동으로 인식
- 사용자가 정확한 필드명을 몰라도 일반적인 이름으로 요청 가능
- Interactive menu와 API 모두에서 일관된 동작
- 명확한 오류 메시지와 로깅으로 디버깅 용이

### 문서 한글화 및 구성 개선 (2025-12-04)

**문서 한글화**:
- `/docs` 디렉토리 내의 모든 마크다운 문서를 한국어로 번역했습니다.

**구성 정리**:
- `config.yaml`에서 중복된 최상위 레거시 필드를 제거하여 구조를 명확히 했습니다.
- `data_parser.py`에서 레거시 폴백 로직을 제거했습니다.

**버그 수정**:
- `data_visualizer.py`: 메모리 최적화로 인해 `url_pattern`이 범주형(Categorical) 데이터로 변환될 때 "Others" 할당이 실패하는 `TypeError`를 수정했습니다.


### 필드 가용성 확인 (2025-11-28)

**문제**: 사용자가 로그 포맷에 존재하지 않는 필드를 필요로 하는 시각화 옵션을 선택할 수 있어 (예: 해당 필드가 없는 HTTPD 로그에 대해 "target_processing_time" 선택), 파싱 후 혼란스러운 오류 메시지가 발생하는 문제가 있었습니다.

**해결책**: `main.py`에 필드 가용성 확인 기능을 추가했습니다.

#### 새로운 헬퍼 함수

**`_get_available_columns(log_format_file)`**
- 로그 포맷 파일에서 사용 가능한 컬럼을 가져옵니다.
- 파생 컬럼을 포함합니다 (예: HTTPD의 request_method, request_url).

**`_check_field_availability(field_name, available_columns)`**
- 필드가 로그 포맷에서 사용 가능한지 확인합니다.
- 다양한 로그 포맷에 걸쳐 필드 이름 변형을 지원합니다:
  - `sent_bytes`: ['sent_bytes', 'bytes_sent', 'size', 'response_size', 'body_bytes_sent']
  - `received_bytes`: ['received_bytes', 'bytes', 'request_size']
  - `target_ip`: ['target_ip', 'backend_ip', 'upstream_addr']
  - `client_ip`: ['client_ip', 'remote_addr', 'clientIp']
  - `request_processing_time`: ['request_processing_time', 'request_time']
  - `target_processing_time`: ['target_processing_time', 'upstream_response_time']
  - `response_processing_time`: ['response_processing_time']

#### 업데이트된 함수

모든 필드 의존적 시각화 함수는 이제 가용성 상태를 표시합니다:

1. **`generate_processing_time()`** - 각 처리 시간 필드에 대한 가용성 표시:
   ```
   Select processing time field:
     1. request_processing_time - ✗ Not available
     2. target_processing_time (default) - ✗ Not available
     3. response_processing_time - ✗ Not available

     ✗ Field Not Found: target_processing_time
     Available columns in log format: client_ip, identity, user, time, request, status, bytes_sent, referer, user_agent, request_method
   ```

2. **`generate_sent_bytes()`** - 실행 전 sent_bytes 필드 확인
3. **`generate_received_bytes()`** - 실행 전 received_bytes 필드 확인
4. **`generate_request_per_target()`** - 실행 전 target_ip 필드 확인

#### 이점
- 사용자가 로그 포맷에서 사용 가능한 필드를 즉시 확인할 수 있습니다.
- 사용할 수 없는 기능에 대해 로그를 파싱하는 시간 낭비를 방지합니다.
- 사용 가능한 대안을 보여주는 명확한 오류 메시지를 제공합니다.
- 다양한 로그 포맷에 걸쳐 필드 이름 변형을 지원합니다.

### HTTPD 로그를 위한 컬럼 타입 변환 (2025-11-28)

**문제**: HTTPD 로그 시간 필드가 문자열로 저장되어 시각화에서 "Total transactions: 0"이 발생하는 문제가 있었습니다.

**해결책**:
1. 포맷 파일 생성(`recommendAccessLogFormat`)에 `columnTypes`를 추가했습니다.
2. `parse_log_file_with_format()`에 컬럼 타입 변환을 추가했습니다:

```python
# Apply column type conversions
for col, dtype in column_types.items():
    if dtype == 'datetime':
        if pattern_type == 'HTTPD':
            # Apache format: 12/Dec/2021:03:13:02 +0900
            df[col] = pd.to_datetime(df[col], format='%d/%b/%Y:%H:%M:%S %z', errors='coerce')
        else:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    elif dtype in ('int', 'integer'):
        df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
    elif dtype in ('float', 'double'):
        df[col] = pd.to_numeric(df[col], errors='coerce')
```

**결과**: 1,764,211개의 모든 HTTPD 로그 항목이 적절한 datetime 변환과 함께 올바르게 파싱됩니다.

### HTTPD 요청 필드 처리 (2025-11-28)

**문제**: HTTPD 로그에는 "METHOD URL PROTOCOL"을 포함하는 단일 "request" 필드가 있지만, 시각화에는 별도의 필드가 필요합니다.

**해결책**: `parse_log_file_with_format()`에 파싱 후 분할 기능을 구현했습니다:

```python
# For HTTPD logs: split request into method, url, protocol
if pattern_type == 'HTTPD' and 'request' in df.columns:
    def split_request(request_str):
        if pd.isna(request_str) or request_str in ('', '-', ' '):
            return None, None, None
        parts = request_str.strip().split(' ', 2)
        if len(parts) == 3:
            return parts[0], parts[1], parts[2]
        # Handle malformed requests
        return None, None, None

    split_results = df['request'].apply(split_request)
    df['request_method'] = split_results.apply(lambda x: x[0])
    df['request_url'] = split_results.apply(lambda x: x[1])
    df['request_proto'] = split_results.apply(lambda x: x[2])
```

**스마트 컬럼 필터링**: 파생 컬럼(request_url, request_method, request_proto)이 요청되면, 자동으로 소스 'request' 컬럼을 포함한 후 분할 후 제거합니다.

**결과**:
- 100% 파싱 성공 (1,764,211 항목, 0 실패)
- 잘못된 형식의 요청을 우아하게 처리
- 메모리 효율적 (분할 후 소스 컬럼 제거)

### AI 어시스턴트를 위한 주요 교훈

1. **필드 변형**: 필드 가용성을 확인할 때 항상 변형을 고려하세요. 다른 로그 포맷은 동일한 개념에 대해 다른 필드 이름을 사용합니다 (예: bytes_sent vs sent_bytes).

2. **포맷별 Datetime**: Apache/HTTPD 로그는 `%d/%b/%Y:%H:%M:%S %z` 포맷을 사용하는 반면, ALB는 ISO 포맷을 사용합니다. 항상 올바른 포맷 문자열을 지정하세요.

3. **파생 컬럼**: 일부 로그 포맷(HTTPD)은 일반적으로 사용되는 필드를 생성하기 위해 파싱 후 처리가 필요합니다. 항상 파생 컬럼 로직을 확인하세요.

4. **사용자 경험**: 사용자가 긴 파싱 작업을 시작하기 전에 필드 가용성을 보여주세요. 이는 시간을 절약하고 좌절을 방지합니다.

5. **우아한 성능 저하**: 필드를 사용할 수 없는 경우 오류만 표시하는 대신 대안을 보여주세요. `_check_field_availability()` 함수는 변형을 자동으로 확인합니다.

## 이전 주요 기능

### 다중 포맷 로그 지원 (2024-11-11)

**다양한 로그 포맷 유형 지원 추가:**
- ALB - AWS Application Load Balancer 로그
- HTTPD - Apache/Nginx Combined Log Format
- HTTPD_WITH_TIME - 응답 시간이 포함된 Apache 로그
- NGINX - 사용자 정의 포맷의 Nginx 액세스 로그
- JSON - JSON 형식 로그
- GROK - 정규식 패턴을 사용한 사용자 정의 로그 포맷

**구성 구조:**
- config.yaml의 포맷별 섹션
- 스마트 매칭을 통한 자동 필드 매핑
- 컬럼 타입 변환 지원

### 통합 패턴 파일 관리 (2024-11-10)

**패턴 파일 명명 변경:**
- 기존: 다중 타임스탬프 파일 (`patterns_241111_120000.json`, `patterns_proctime_241111_120000.json`)
- 신규: 로그당 단일 통합 파일 (`patterns_access.json`)

**기능:**
- 모든 시각화 함수가 동일한 패턴 파일 공유
- 패턴 규칙 자동 병합
- 수동으로 추가된 규칙 보존

### 메모리 최적화 (2024-11-09)

**다층 메모리 최적화 접근 방식:**
1. **컬럼 필터링**: 필요한 컬럼만 로드 (80-90% 감소)
2. **Dtype 최적화**: 숫자 타입 다운캐스트 (50-70% 감소)
3. **명시적 메모리 정리**: 대규모 작업 후 `gc.collect()` 사용
4. **결합 효과**: 전체 메모리 사용량을 90% 이상 줄일 수 있음

**모든 시각화 함수에 적용:**
- `generateXlog`
- `generateRequestPerURI`
- `generateReceivedBytesPerURI`
- `generateSentBytesPerURI`
- `generateProcessingTimePerURI`

### 멀티프로세싱 지원 (2024-11-08)

**대용량 파일을 위한 병렬 처리 추가:**
- 로그 파싱: 멀티코어 시스템에서 약 3-4배 더 빠름
- 통계 계산: 대규모 데이터셋에서 약 2-3배 더 빠름
- config.yaml을 통해 구성 가능
- 최적의 작업자 수 자동 감지

**구성 옵션:**
- `enabled`: 전역 활성화/비활성화
- `num_workers`: 자동 감지 또는 숫자 지정
- `chunk_size`: 청크 당 라인 수
- `min_lines_for_parallel`: 병렬 처리를 위한 최소 라인 수

### 타겟 및 클라이언트 IP 시각화 (2024-11-07)

**새로운 시각화 함수:**
- `generateRequestPerTarget`: 백엔드 서버별 요청 분포
- `generateRequestPerClientIP`: 클라이언트 소스별 요청 분포

**기능:**
- 인터랙티브 체크박스 필터링
- 상태 색상 코딩이 포함된 IP 그룹화
- 시계열 분석

### 처리 시간 분석 (2024-11-06)

**향상된 처리 시간 분석:**
- 다중 처리 시간 필드 지원
- 특정 메트릭별 상위 N개 URL
- 유연한 정렬 옵션 (avg, sum, median, p95, p99)
- URI 패턴별 시계열 시각화

**새로운 파라미터:**
- `processingTimeFields`: 여러 필드를 동시에 분석
- `sortBy`: 정렬 기준 필드
- `sortMetric`: 정렬에 사용할 메트릭
- `topN`: 상위 N개 결과만 반환

### 핵심 인프라 (2024-11-05)

**핵심 인프라 모듈 추가:**
- `core/exceptions.py` - 사용자 정의 예외 클래스
- `core/config.py` - 중앙 집중식 구성 관리
- `core/logging_config.py` - 파일 로테이션이 포함된 로깅 시스템
- `core/utils.py` - 유틸리티 클래스 (FieldMapper, ParamParser, MultiprocessingConfig)

**모든 `print()` 문을 적절한 로깅으로 대체**

### 패턴 규칙 시스템 (2024-11-04)

**향상된 URI 패턴 일반화:**
- ID 유사 세그먼트 → `*`
- 정적 파일 → 확장자별 분류 (*.css, *.js, *.image 등)
- 정규식 규칙을 통한 사용자 정의 패턴
- 효율적인 캐싱을 위한 `PatternRulesManager`

**파일 확장자 분류:**
- 스타일시트: *.css
- 스크립트: *.js
- 이미지: *.image
- 폰트: *.font
- 문서: *.doc
- 비디오: *.video
- 오디오: *.audio
- 데이터: *.data
- 아카이브: *.archive

### 시간 필드 선택 (2024-11-03)

**모든 시각화 함수가 이제 `timeField` 파라미터를 지원합니다:**
- 'time'과 'request_creation_time' 중 선택 가능
- 여러 시간 필드가 있는 ALB 로그에 유용
- 모든 시각화에서 일관성 유지

### 유연한 시간 간격 (2024-11-02)

**향상된 시간 간격 지원:**
- 일반적인 약어 자동 정규화
- 지원 단위: s (초), min (분), h (시간), d (일)
- 예시: '1m' → '1min', '30sec' → '30s'

**적용 대상:**
- `calculateStats`
- `generateRequestPerURI`
- `generateProcessingTimePerURI`

## 버그 수정

### 파싱 실패 표시 수정 (2024-11-28)
- 포맷 추천 중 처음 10개의 실패 라인을 표시합니다.
- 실제 파싱 중 모든 실패 라인을 표시합니다 (최대 10개).
- 디버깅을 위한 라인 번호와 잘린 내용을 제공합니다.

### 타임존 처리 수정 (2024-11-05)
- 나이브(naive) 및 타임존 인식(timezone-aware) 타임스탬프 모두 지원
- 비교 호환성을 위한 자동 변환
- 필터 파라미터의 ISO 8601 포맷 오버라이드

### 패턴 파일 중복 수정 (2024-11-04)
- 다중 타임스탬프 패턴 파일 제거
- 로그 파일당 단일 패턴 파일
- 중복 없는 자동 병합

## 마이그레이션 가이드

### 통합 패턴 파일로 마이그레이션 (2024-11-10부터)

**이전 워크플로우:**
```python
# Generated: patterns_241111_120000.json, patterns_proctime_241111_120000.json
extractUriPatterns(...)
generateProcessingTimePerURI(..., patternsFile='patterns_proctime_241111_120000.json')
```

**새로운 워크플로우:**
```python
# Generates: patterns_access.json (unified)
extractUriPatterns(...)
generateProcessingTimePerURI(..., patternsFile='patterns_access.json')
# Or omit patternsFile to auto-generate
```

**필요한 조치:**
- 없음 - 이전 패턴 파일도 여전히 작동함
- 권장 사항: 앞으로는 새로운 통합 패턴 파일 사용

### 다중 포맷 지원으로 마이그레이션 (2024-11-11부터)

**이전 config.yaml:**
```yaml
input_path: '*.gz'
log_pattern: '...'
columns: [...]
```

**새로운 config.yaml:**
```yaml
log_format_type: 'ALB'  # Specify format type

alb:
  input_path: '*.gz'
  log_pattern: '...'
  columns: [...]
```

**필요한 조치:**
- config.yaml에 `log_format_type` 추가
- 포맷별 설정을 포맷 섹션 아래로 이동
- 레거시 최상위 설정은 ALB에 대해 여전히 작동함

## 지원 중단 (Deprecations)

현재 없음.

## 향후 로드맵

### 계획된 기능

- **실시간 로그 모니터링** - 스트림 처리 지원
- **이상 징후 탐지** - 통계적 이상 징후 탐지
- **사용자 정의 대시보드** - 사용자 구성 가능한 대시보드 템플릿
- **내보내기 포맷** - CSV, Excel, PDF 보고서 생성
- **API 엔드포인트** - 프로그래밍 방식 액세스를 위한 REST API
- **데이터베이스 통합** - 로그 데이터베이스에 대한 직접 쿼리 지원
- **알림** - 임계값 기반 알림 시스템
- **머신 러닝** - 패턴 학습 및 예측

### 성능 개선

- **증분 파싱** - 새로운 로그 항목만 처리
- **인덱스 캐싱** - 더 빠른 재분석을 위해 파싱된 데이터 캐싱
- **분석 저장** - 분산 컴퓨팅 지원 (Dask, Spark)
- **GPU 가속** - 대규모 데이터셋을 위한 GPU 가속 처리

### 사용성 개선

- **웹 UI** - 브라우저 기반 인터페이스
- **대화형 쿼리** - 로그를 위한 SQL 유사 쿼리 언어
- **분석 저장** - 분석 세션 저장 및 복원
- **템플릿** - 미리 구성된 분석 템플릿
- **공유** - 시각화 내보내기 및 공유

## 기여하기

다음 가이드라인은 [DEVELOPMENT.md](DEVELOPMENT.md)를 참조하세요:
- 개발 환경 설정
- 테스트 실행
- 코드 스타일 및 모범 사례
- 풀 리퀘스트 프로세스
