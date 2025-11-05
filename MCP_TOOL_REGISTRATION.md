# MCP Tool 등록 가이드

이 문서는 Access Log Analyzer의 MCP Tools를 MCP 서버에 등록하는 방법을 설명합니다.

## 개요

MCP (Model Context Protocol)는 클라이언트와 서버 간 통신을 위한 프로토콜입니다. 현재 코드베이스의 Python 함수들을 MCP Tool로 등록하여 LLM이나 다른 MCP 클라이언트에서 사용할 수 있도록 합니다.

## 필수 요구사항

```bash
pip install mcp
```

또는 Python 3.11+ 환경에서:

```bash
pip install mcp-server-python
```

## MCP 서버 구현

### 1. 기본 서버 구조

`mcp_server.py` 파일을 생성합니다:

```python
#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
MCP Server for Access Log Analyzer
"""
import asyncio
import json
from typing import Any, Sequence
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Import MCP tools
from data_parser import recommendAccessLogFormat
from data_processor import (
    filterByCondition,
    extractUriPatterns,
    filterUriPatterns,
    calculateStats
)
from data_visualizer import (
    generateXlog,
    generateRequestPerURI,
    generateMultiMetricDashboard
)

# Create MCP server instance
server = Server("access-log-analyzer")


# ============================================================================
# Tool Registration
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools"""
    return [
        Tool(
            name="recommendAccessLogFormat",
            description="접근 로그 포맷을 자동 추천하여 최종 패턴을 반환합니다.",
            inputSchema={
                "type": "object",
                "required": ["inputFile"],
                "properties": {
                    "inputFile": {
                        "type": "string",
                        "description": "입력 로그 파일 경로"
                    }
                }
            }
        ),
        Tool(
            name="filterByCondition",
            description="Access log를 다양한 조건으로 필터링합니다.",
            inputSchema={
                "type": "object",
                "required": ["inputFile", "logFormatFile", "condition", "params"],
                "properties": {
                    "inputFile": {
                        "type": "string",
                        "description": "입력 로그 파일 경로"
                    },
                    "logFormatFile": {
                        "type": "string",
                        "description": "로그 포맷 파일 경로 (recommendAccessLogFormat 결과)"
                    },
                    "condition": {
                        "type": "string",
                        "enum": ["time", "statusCode", "responseTime", "client", "urls", "uriPatterns"],
                        "description": "필터링 조건"
                    },
                    "params": {
                        "type": "string",
                        "description": "조건별 파라미터 문자열 (예: 'startTime=2024-08-08T09:00:00;endTime=2024-08-08T10:00:00')"
                    }
                }
            }
        ),
        Tool(
            name="extractUriPatterns",
            description="URI 패턴/URL을 추출합니다 (extractionType: 'urls'|'patterns').",
            inputSchema={
                "type": "object",
                "required": ["inputFile", "logFormatFile", "extractionType"],
                "properties": {
                    "inputFile": {
                        "type": "string",
                        "description": "입력 로그 파일 경로"
                    },
                    "logFormatFile": {
                        "type": "string",
                        "description": "로그 포맷 파일 경로"
                    },
                    "extractionType": {
                        "type": "string",
                        "enum": ["urls", "patterns"],
                        "description": "추출 타입"
                    },
                    "params": {
                        "type": "string",
                        "description": "파라미터 문자열 (includeParams, maxPatterns, minCount 등)",
                        "default": ""
                    }
                }
            }
        ),
        Tool(
            name="filterUriPatterns",
            description="URI 패턴 파일을 필터링합니다 (포함/제외 패턴 기반).",
            inputSchema={
                "type": "object",
                "required": ["urisFile"],
                "properties": {
                    "urisFile": {
                        "type": "string",
                        "description": "URI 패턴 파일 경로 (extractUriPatterns의 결과 파일)"
                    },
                    "params": {
                        "type": "string",
                        "description": "필터링 파라미터 문자열 (excludePatterns, includePatterns 등)",
                        "default": ""
                    }
                }
            }
        ),
        Tool(
            name="calculateStats",
            description="접근 로그 통계를 계산합니다 (전체/패턴별/시간별/IP별 통계).",
            inputSchema={
                "type": "object",
                "required": ["inputFile", "logFormatFile"],
                "properties": {
                    "inputFile": {
                        "type": "string",
                        "description": "입력 로그 파일 경로"
                    },
                    "logFormatFile": {
                        "type": "string",
                        "description": "로그 포맷 파일 경로"
                    },
                    "params": {
                        "type": "string",
                        "description": "파라미터 문자열 (statsType, timeInterval 등)",
                        "default": ""
                    }
                }
            }
        ),
        Tool(
            name="generateXlog",
            description="XLog (response time scatter plot) 시각화를 생성합니다.",
            inputSchema={
                "type": "object",
                "required": ["inputFile", "logFormatFile"],
                "properties": {
                    "inputFile": {
                        "type": "string",
                        "description": "입력 로그 파일 경로"
                    },
                    "logFormatFile": {
                        "type": "string",
                        "description": "로그 포맷 파일 경로"
                    },
                    "outputFormat": {
                        "type": "string",
                        "enum": ["html"],
                        "description": "출력 포맷",
                        "default": "html"
                    }
                }
            }
        ),
        Tool(
            name="generateRequestPerURI",
            description="Request Count per URI time-series 시각화를 생성합니다.",
            inputSchema={
                "type": "object",
                "required": ["inputFile", "logFormatFile"],
                "properties": {
                    "inputFile": {
                        "type": "string",
                        "description": "입력 로그 파일 경로"
                    },
                    "logFormatFile": {
                        "type": "string",
                        "description": "로그 포맷 파일 경로"
                    },
                    "outputFormat": {
                        "type": "string",
                        "enum": ["html"],
                        "description": "출력 포맷",
                        "default": "html"
                    },
                    "topN": {
                        "type": "integer",
                        "description": "표시할 상위 URI 패턴 수",
                        "default": 20
                    },
                    "interval": {
                        "type": "string",
                        "description": "집계 시간 간격 (예: '10s', '1min', '5min', '1h')",
                        "default": "10s"
                    },
                    "patternsFile": {
                        "type": "string",
                        "description": "패턴 파일 경로 (선택사항)",
                        "default": None
                    }
                }
            }
        ),
        Tool(
            name="generateMultiMetricDashboard",
            description="다중 메트릭 대시보드를 생성합니다.",
            inputSchema={
                "type": "object",
                "required": ["inputFile", "logFormatFile"],
                "properties": {
                    "inputFile": {
                        "type": "string",
                        "description": "입력 로그 파일 경로"
                    },
                    "logFormatFile": {
                        "type": "string",
                        "description": "로그 포맷 파일 경로"
                    },
                    "outputFormat": {
                        "type": "string",
                        "enum": ["html"],
                        "description": "출력 포맷",
                        "default": "html"
                    }
                }
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Execute MCP tool"""
    try:
        if name == "recommendAccessLogFormat":
            result = recommendAccessLogFormat(arguments["inputFile"])
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        elif name == "filterByCondition":
            result = filterByCondition(
                arguments["inputFile"],
                arguments["logFormatFile"],
                arguments["condition"],
                arguments.get("params", "")
            )
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        elif name == "extractUriPatterns":
            result = extractUriPatterns(
                arguments["inputFile"],
                arguments["logFormatFile"],
                arguments["extractionType"],
                arguments.get("params", "")
            )
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        elif name == "filterUriPatterns":
            result = filterUriPatterns(
                arguments["urisFile"],
                arguments.get("params", "")
            )
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        elif name == "calculateStats":
            result = calculateStats(
                arguments["inputFile"],
                arguments["logFormatFile"],
                arguments.get("params", "")
            )
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        elif name == "generateXlog":
            result = generateXlog(
                arguments["inputFile"],
                arguments["logFormatFile"],
                arguments.get("outputFormat", "html")
            )
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        elif name == "generateRequestPerURI":
            result = generateRequestPerURI(
                arguments["inputFile"],
                arguments["logFormatFile"],
                arguments.get("outputFormat", "html"),
                arguments.get("topN", 20),
                arguments.get("interval", "10s"),
                arguments.get("patternsFile")
            )
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        elif name == "generateMultiMetricDashboard":
            result = generateMultiMetricDashboard(
                arguments["inputFile"],
                arguments["logFormatFile"],
                arguments.get("outputFormat", "html")
            )
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        return [TextContent(
            type="text",
            text=json.dumps({"error": error_msg}, indent=2)
        )]


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Main entry point for MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
```

## 클라이언트 설정

### Claude Desktop 설정

Claude Desktop에서 MCP 서버를 사용하려면 설정 파일을 수정합니다.

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

설정 파일 내용:

```json
{
  "mcpServers": {
    "access-log-analyzer": {
      "command": "python",
      "args": [
        "C:/bucket/itop/TA/user.sungwon/python/alb_accesslog_analyzer/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "C:/bucket/itop/TA/user.sungwon/python/alb_accesslog_analyzer"
      }
    }
  }
}
```

### Python MCP 클라이언트 사용

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # MCP 서버에 연결
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
        env={"PYTHONPATH": "."}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 서버 초기화
            await session.initialize()
            
            # 도구 목록 조회
            tools = await session.list_tools()
            print(f"Available tools: {[tool.name for tool in tools.tools]}")
            
            # 도구 실행 예제
            result = await session.call_tool(
                "recommendAccessLogFormat",
                {"inputFile": "access.log"}
            )
            print(result.content)

if __name__ == "__main__":
    asyncio.run(main())
```

## 실행 방법

### 1. 직접 실행 (테스트용)

```bash
python mcp_server.py
```

### 2. Claude Desktop과 통합

1. Claude Desktop 설정 파일에 서버 추가
2. Claude Desktop 재시작
3. Claude Desktop에서 "MCP Tools" 메뉴에서 도구 확인

### 3. Python 클라이언트로 사용

```bash
python mcp_client_example.py
```

## 도구 실행 예제

### 1. 로그 포맷 추천

```python
result = await session.call_tool(
    "recommendAccessLogFormat",
    {
        "inputFile": "/path/to/access.log"
    }
)
```

### 2. 필터링

```python
result = await session.call_tool(
    "filterByCondition",
    {
        "inputFile": "/path/to/access.log",
        "logFormatFile": "/path/to/logformat_123.json",
        "condition": "time",
        "params": "startTime=2024-08-08T09:00:00;endTime=2024-08-08T10:00:00"
    }
)
```

### 3. URI 패턴 추출

```python
result = await session.call_tool(
    "extractUriPatterns",
    {
        "inputFile": "/path/to/access.log",
        "logFormatFile": "/path/to/logformat_123.json",
        "extractionType": "patterns",
        "params": "maxPatterns=50;minCount=100"
    }
)
```

### 4. 시각화 생성

```python
result = await session.call_tool(
    "generateRequestPerURI",
    {
        "inputFile": "/path/to/access.log",
        "logFormatFile": "/path/to/logformat_123.json",
        "topN": 20,
        "interval": "10s"
    }
)
```

## 주의사항

1. **경로 문제**: 모든 파일 경로는 절대 경로를 사용하는 것이 안전합니다.
2. **에러 처리**: MCP Tool은 예외를 발생시키면 클라이언트에 에러 메시지가 전달됩니다.
3. **비동기 처리**: MCP 서버는 비동기로 동작하므로, 모든 도구 함수는 동기 함수여도 async/await로 래핑됩니다.
4. **환경 변수**: Python 경로나 필요한 환경 변수는 `env` 설정에서 지정할 수 있습니다.

## 추가 리소스

- [MCP 공식 문서](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Claude Desktop MCP 가이드](https://docs.anthropic.com/claude/docs/mcp)

