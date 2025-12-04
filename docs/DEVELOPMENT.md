# 개발 가이드 (Development Guide)

이 가이드는 개발 설정, 테스트, 디버깅 및 코드베이스 확장을 다룹니다.

## 설정 및 설치 (Setup and Installation)

### 전제 조건 (Prerequisites)

- Python 3.7+
- pip 패키지 관리자
- UTF-8 인코딩 지원
- WSL2 또는 Unix 계열 환경 (권장)

### 종속성 설치 (Install Dependencies)

```bash
# 런타임 종속성 설치
pip install -r requirements.txt

# 개발 종속성 설치
pip install -r requirements-dev.txt
```

## 애플리케이션 실행 (Running the Application)

### 대화형 메뉴 모드 (Interactive Menu Mode)

```bash
python main.py
```

다음 작업을 수행할 수 있는 대화형 메뉴를 실행합니다:
- 로그 포맷 감지
- 로그 데이터 필터링
- URI 패턴 추출
- 통계 계산
- 시각화 생성

### 파일별 모드 (File-Specific Mode)

```bash
# 특정 로그 파일 분석
python main.py access.log.gz

# 도구가 자동으로 포맷을 감지하고 작업에 대한 프롬프트를 표시합니다
```

### 예제 파이프라인 실행 (Example Pipeline Execution)

```bash
# 데모 데이터로 예제 파이프라인 실행
python main.py --example access.log.gz
```

이 명령은 미리 정의된 파이프라인을 실행합니다:
1. 포맷 감지
2. URI 패턴 추출
3. 통계 계산
4. 다중 시각화

## 개별 MCP 도구 테스트 (Testing Individual MCP Tools)

### 로그 포맷 감지 테스트

```bash
# 로그 파일에 대한 포맷 감지 테스트
python data_parser.py <log_file>

# 예시
python data_parser.py access.log.gz
```

### MCP 서버 테스트

```bash
# MCP 서버 시작 (stdio 기반)
python mcp_server.py
```

MCP 서버는 stdin/stdout을 통해 JSON-RPC 요청을 받습니다.

## 테스트 (Testing)

### 테스트 실행

```bash
# 상세 출력과 함께 모든 테스트 실행
pytest tests/ -v

# 특정 테스트 파일 실행
pytest tests/test_core_utils.py -v

# 특정 테스트 함수 실행
pytest tests/test_core_utils.py::test_field_mapper -v

# 커버리지 리포트와 함께 실행
pytest tests/ --cov=core --cov=data_parser --cov=data_processor --cov-report=html

# 커버리지와 함께 실행하고 누락된 라인 표시
pytest tests/ --cov=core --cov-report=term-missing
```

### 테스트 구조

```
tests/
├── conftest.py              # Pytest 픽스처 (샘플 로그, 임시 파일)
├── test_core_exceptions.py  # 예외 처리 테스트
├── test_core_utils.py       # FieldMapper, ParamParser, MultiprocessingConfig 테스트
└── test_data_parser.py      # 파서 및 포맷 감지 테스트
```

### 새로운 테스트 작성

Arrange-Act-Assert 패턴을 따르세요:

```python
import pytest
from core.exceptions import ValidationError
from core.utils import ParamParser

def test_param_parser_get_int():
    """Test ParamParser.get_int with valid input"""
    # Arrange
    params = "topN=20;interval=10"

    # Act
    result = ParamParser.get_int(params, 'topN')

    # Assert
    assert result == 20
    assert isinstance(result, int)

def test_param_parser_get_int_invalid():
    """Test ParamParser.get_int with invalid input"""
    params = "topN=invalid"

    with pytest.raises(ValidationError):
        ParamParser.get_int(params, 'topN')
```

### 테스트 픽스처

`conftest.py`의 픽스처 사용:

```python
def test_with_sample_log(sample_alb_log):
    """Test using sample ALB log fixture"""
    # sample_alb_log is a temporary file path
    result = recommendAccessLogFormat(sample_alb_log)
    assert result['patternType'] == 'ALB'
```

## 에러 처리 (Error Handling)

### 사용자 정의 예외 사용

```python
from core.exceptions import (
    FileNotFoundError,
    ValidationError,
    ParseError,
    InvalidFormatError
)

# 파일 존재 여부 검증
if not os.path.exists(file_path):
    raise FileNotFoundError(file_path)

# 파라미터 검증
if value not in allowed_values:
    raise ValidationError('parameter_name', f"Invalid value: {value}")

# 컨텍스트가 포함된 파싱 에러
if parse_failed:
    raise ParseError(line_number, line_content, "Regex pattern did not match")
```

### 에러 캐치 및 로깅

```python
from core.logging_config import get_logger
from core.exceptions import LogAnalyzerError

logger = get_logger(__name__)

try:
    result = some_operation()
except LogAnalyzerError as e:
    logger.error(f"Operation failed: {e}")
    raise
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    raise LogAnalyzerError(f"Unexpected error: {e}") from e
```

## 로깅 (Logging)

### 로깅 시스템 사용

```python
from core.logging_config import get_logger

logger = get_logger(__name__)

# 다른 레벨로 로깅
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning messages")
logger.error("Error messages")
logger.critical("Critical errors")
```

### 파일 로깅 활성화

```python
from core.logging_config import enable_file_logging, set_log_level

# 파일 로깅 활성화 (logs/access_log_analyzer_YYYYMMDD.log 생성)
enable_file_logging()

# 모든 로거에 대해 로그 레벨 설정
set_log_level('DEBUG')
```

### 로그 파일 위치

로그 파일은 `logs/` 디렉토리에 일일 로테이션으로 저장됩니다:
- 포맷: `access_log_analyzer_YYYYMMDD.log`
- 로테이션: 매일 자정
- 보존: 구성 가능 (기본값: 30일)

## 구성 관리 (Configuration Management)

### ConfigManager 사용

```python
from core.config import ConfigManager

config_mgr = ConfigManager()

# 표준 위치에서 config.yaml 자동 검색
config = config_mgr.load_config()

# 기본값으로 특정 값 가져오기
port = config_mgr.get('server.port', default=8080)
workers = config_mgr.get('multiprocessing.num_workers', default=4)

# 구성 강제 다시 로드
config_mgr.reload()
```

### 구성 파일 검색 순서

1. 입력 파일과 동일한 디렉토리
2. 입력 파일의 상위 디렉토리
3. 현재 작업 디렉토리
4. 스크립트 디렉토리

## 유틸리티 클래스 사용 (Using Utility Classes)

### FieldMapper - 스마트 필드 매핑

```python
from core.utils import FieldMapper
import pandas as pd

df = pd.DataFrame({'timestamp': [...], 'request_url': [...]})
format_info = {'fieldMap': {...}}

# 대체 대안으로 필드 찾기
time_field = FieldMapper.find_field(df, 'time', format_info)
# 정확한 일치가 없으면 'timestamp' 반환

# 모든 일반 필드를 한 번에 매핑
field_map = FieldMapper.map_fields(df, format_info)
# 반환값: {'timestamp': 'timestamp', 'url': 'request_url', ...}

# 필수 필드 검증
FieldMapper.validate_required_fields(df, format_info, ['time', 'url'])
# 필드가 누락되면 ValidationError 발생
```

### ParamParser - 타입 안전 파라미터 파싱

```python
from core.utils import ParamParser

params = "startTime=2024-01-01;endTime=2024-12-31;topN=20;enabled=true"

# 모든 파라미터 파싱
parsed = ParamParser.parse(params)

# 타입 지정 값 가져오기
start_time = ParamParser.get(params, 'startTime', required=True)
top_n = ParamParser.get_int(params, 'topN', default=10)
enabled = ParamParser.get_bool(params, 'enabled')
filters = ParamParser.get_list(params, 'filters', separator=',')
```

### MultiprocessingConfig - 멀티프로세싱 설정

```python
from core.utils import MultiprocessingConfig

# config.yaml에서 구성 가져오기
config = MultiprocessingConfig.get_config()

# 최적의 작업자 수 가져오기
workers = MultiprocessingConfig.get_optimal_workers(data_size=100000)

# 멀티프로세싱 사용 여부 확인
should_use = MultiprocessingConfig.should_use_multiprocessing(data_size=50000)

# 전체 처리 파라미터 가져오기
params = MultiprocessingConfig.get_processing_params(
    use_multiprocessing=True,
    data_size=100000
)
```

## 새로운 MCP 도구 추가 (Adding a New MCP Tool)

새로운 MCP 도구를 추가하려면 다음 단계를 따르세요:

### 1. 함수 구현

적절한 모듈(`data_processor.py` 또는 `data_visualizer.py`)에 함수를 추가합니다:

```python
from typing import Dict, Any
from core.exceptions import FileNotFoundError, ValidationError
from core.logging_config import get_logger
from core.utils import ParamParser

logger = get_logger(__name__)

def myNewTool(inputFile: str, logFormatFile: str, params: str = '') -> Dict[str, Any]:
    """
    Description of what the tool does.

    Args:
        inputFile: Path to the log file
        logFormatFile: Path to the format file
        params: Semicolon-separated parameters

    Returns:
        Dictionary with filePath and metadata

    Raises:
        FileNotFoundError: If input file not found
        ValidationError: If parameters are invalid
    """
    logger.info(f"Running myNewTool on {inputFile}")

    # Validate file exists
    if not os.path.exists(inputFile):
        raise FileNotFoundError(inputFile)

    # Parse parameters
    topN = ParamParser.get_int(params, 'topN', default=20)
    interval = ParamParser.get(params, 'interval', default='10min')

    # Implement tool logic here
    # ...

    # Generate output file path (use appropriate naming convention)
    output_file = f"mytool_{os.path.splitext(os.path.basename(inputFile))[0]}.json"
    output_path = os.path.abspath(output_file)

    # Save results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"Tool output saved to {output_path}")

    # Return result with absolute path
    return {
        'filePath': output_path,
        'metadata1': value1,
        'metadata2': value2
    }
```

### 2. mcp_server.py에 도구 등록 추가

`list_tools()` 함수에 도구를 추가합니다:

```python
Tool(
    name="myNewTool",
    description="한글 설명 - 도구가 하는 일에 대한 설명",
    inputSchema={
        "type": "object",
        "properties": {
            "inputFile": {
                "type": "string",
                "description": "로그 파일 경로"
            },
            "logFormatFile": {
                "type": "string",
                "description": "로그 포맷 파일 경로"
            },
            "params": {
                "type": "string",
                "description": "세미콜론으로 구분된 파라미터 (예: topN=20;interval=10min)"
            }
        },
        "required": ["inputFile", "logFormatFile"]
    }
)
```

### 3. mcp_server.py에 핸들러 추가

`call_tool()` 함수에 핸들러를 추가합니다:

```python
async def call_tool(self, name: str, arguments: dict) -> Sequence[TextContent]:
    # ... existing handlers ...

    elif name == "myNewTool":
        input_file = arguments.get("inputFile")
        logformat_file = arguments.get("logFormatFile")
        params = arguments.get("params", "")

        result = myNewTool(input_file, logformat_file, params)

        return [
            TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )
        ]
```

### 4. main.py에 메뉴 항목 추가

대화형 메뉴에 메뉴 항목을 추가합니다:

```python
def interactive_menu():
    # ... existing menu items ...

    print("\n=== My New Tool ===")
    print("10. Run My New Tool")

    choice = input("\nSelect option: ")

    if choice == "10":
        run_my_new_tool()

def run_my_new_tool():
    """Run my new tool"""
    if not current_log_file or not current_format_file:
        print("Please detect log format first (option 1)")
        return

    # Get parameters from user
    topN = input("Enter topN (default: 20): ") or "20"
    interval = input("Enter interval (default: 10min): ") or "10min"

    params = f"topN={topN};interval={interval}"

    print(f"\nRunning myNewTool...")
    result = myNewTool(current_log_file, current_format_file, params)

    print(f"\n✓ Output saved: {result['filePath']}")
    print(f"Metadata1: {result['metadata1']}")
    print(f"Metadata2: {result['metadata2']}")
```

### 5. 테스트 작성

`tests/test_my_new_tool.py`에 테스트를 생성합니다:

```python
import pytest
from my_module import myNewTool
from core.exceptions import ValidationError, FileNotFoundError

def test_my_new_tool_basic(sample_alb_log, sample_format_file):
    """Test basic functionality"""
    result = myNewTool(sample_alb_log, sample_format_file, "topN=10")

    assert 'filePath' in result
    assert os.path.exists(result['filePath'])

def test_my_new_tool_invalid_params():
    """Test with invalid parameters"""
    with pytest.raises(ValidationError):
        myNewTool("test.log", "format.json", "topN=invalid")

def test_my_new_tool_file_not_found():
    """Test with non-existent file"""
    with pytest.raises(FileNotFoundError):
        myNewTool("nonexistent.log", "format.json")
```

### 6. 문서 업데이트

- `docs/API_REFERENCE.md`에 함수 시그니처 추가
- `docs/WORKFLOWS.md`에 사용 예제 추가
- 필요한 경우 `docs/ARCHITECTURE.md` 업데이트

## 디버깅 (Debugging)

### 파싱 실패 디버깅

로그 파싱이 실패하면 시스템이 다음을 출력합니다:
- 라인 번호와 잘린 내용이 포함된 `⚠️ 파싱에 실패한 라인`
- 포맷 추천 중 처음 10개의 실패 라인
- 실제 파싱 중 모든 실패 라인 (처음 10개까지 표시됨)

다음 사항을 확인하세요:
- `config.yaml`의 패턴/컬럼 불일치
- 예상치 못한 로그 포맷 변형
- ALB 로그의 추가/누락된 필드

### 디버그 로깅 활성화

```python
from core.logging_config import set_log_level, enable_file_logging

# 디버그 출력 활성화
set_log_level('DEBUG')
enable_file_logging()

# 이제 모든 모듈이 상세한 디버그 정보를 출력합니다
```

### pytest로 디버깅

```bash
# 상세 출력 및 print 문과 함께 테스트 실행
pytest tests/ -v -s

# 디버깅과 함께 특정 테스트 실행
pytest tests/test_my_module.py::test_my_function -v -s

# 실패 시 디버거 진입
pytest tests/ --pdb
```

### 일반적인 문제 및 해결책

#### 문제: "Field Not Found" 에러

**해결책**: config.yaml의 필드 매핑을 확인하고 사용 가능한 컬럼을 검증하세요:

```python
from data_parser import parse_log_file_with_format

# 사용 가능한 항목을 확인하기 위해 모든 컬럼으로 파싱
df = parse_log_file_with_format(log_file, format_file)
print("Available columns:", df.columns.tolist())
```

#### 문제: 성능 저하

**해결책**: 멀티프로세싱을 활성화하고 청크 크기를 조정하세요:

```yaml
# config.yaml
multiprocessing:
  enabled: true
  num_workers: 8
  chunk_size: 10000
```

#### 문제: 메모리 부족

**해결책**: 컬럼 필터링을 사용하고 작업자 수를 줄이세요:

```python
# 필요한 컬럼만 로드
df = parse_log_file_with_format(
    log_file,
    format_file,
    columns_to_load=['time', 'request_url', 'status'],
    num_workers=2
)
```

## 코드 스타일 및 모범 사례 (Code Style and Best Practices)

### 코드 스타일

- PEP 8 스타일 가이드 준수
- 함수 시그니처에 타입 힌트 사용
- 모든 공개 함수에 독스트링 사용
- 함수를 집중적이고 작게 유지
- 설명적인 변수 이름 사용

### 에러 처리

- `core.exceptions`의 사용자 정의 예외 사용
- 발생시키기 전에 항상 에러 로깅
- 에러 메시지에 컨텍스트 제공
- 입력을 조기에 검증

### 로깅

- 적절한 로그 레벨 사용 (DEBUG, INFO, WARNING, ERROR)
- 중요한 작업 및 마일스톤 로깅
- 로그 메시지에 관련 컨텍스트 포함
- `print()`를 절대 사용하지 않음 - 항상 로거 사용

### 테스트

- 모든 새로운 기능에 대한 테스트 작성
- 80% 이상의 코드 커버리지 목표
- 성공 및 실패 케이스 모두 테스트
- 설명적인 테스트 이름 사용

## Git 워크플로우 (Git Workflow)

### 브랜치 전략

- `main` - 프로덕션 준비 코드
- `develop` - 기능을 위한 통합 브랜치
- `feature/*` - 기능 브랜치
- `bugfix/*` - 버그 수정 브랜치

### 커밋 메시지

Conventional commit 포맷을 따르세요:

```
feat: Add support for custom log formats
fix: Handle missing fields in HTTPD logs
docs: Update API reference for new tool
test: Add tests for ParamParser
refactor: Simplify field mapping logic
```

### 풀 리퀘스트 프로세스

1. `develop`에서 기능 브랜치 생성
2. 테스트와 함께 변경 사항 구현
3. 문서 업데이트
4. 테스트 실행: `pytest tests/ -v`
5. `develop`으로 풀 리퀘스트 생성
6. 리뷰 코멘트 해결
7. 승인 후 병합

## 성능 프로파일링 (Performance Profiling)

### 코드 실행 프로파일링

```python
import cProfile
import pstats

# 함수 프로파일링
cProfile.run('my_function()', 'profile_stats')

# 결과 분석
p = pstats.Stats('profile_stats')
p.sort_stats('cumulative')
p.print_stats(20)  # 상위 20개 함수
```

### 메모리 프로파일링

```python
from memory_profiler import profile

@profile
def my_function():
    # Function code here
    pass

# 실행: python -m memory_profiler script.py
```

## 문서화 (Documentation)

### 문서 생성

문서는 `docs/` 디렉토리의 Markdown 파일에 저장됩니다:

- `docs/ARCHITECTURE.md` - 아키텍처 및 설계
- `docs/API_REFERENCE.md` - 함수 시그니처 및 파라미터
- `docs/CONFIGURATION.md` - 설정 가이드
- `docs/WORKFLOWS.md` - 일반적인 워크플로우
- `docs/DEVELOPMENT.md` - 이 파일
- `docs/CHANGELOG.md` - 최근 변경 사항

### 문서 업데이트

새로운 기능을 추가할 때:
1. 관련 문서 파일 업데이트
2. `WORKFLOWS.md`에 예제 추가
3. `API_REFERENCE.md`에 API 참조 추가
4. `CHANGELOG.md`에 변경 사항 업데이트

## 릴리스 프로세스 (Release Process)

1. `__version__.py`의 버전 번호 업데이트
2. `CHANGELOG.md`에 릴리스 노트 업데이트
3. 전체 테스트 스위트 실행: `pytest tests/ -v`
4. `main` 브랜치에 병합
5. 릴리스 태그: `git tag v1.0.0`
6. 태그 푸시: `git push --tags`
7. 노트와 함께 GitHub 릴리스 생성
