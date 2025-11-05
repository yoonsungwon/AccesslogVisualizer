#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
MCP Server for Access Log Analyzer

This server exposes all MCP tools for access log analysis.
Run this script to start the MCP server.

Usage:
    python mcp_server.py
"""
import asyncio
import json
import sys
from typing import Any, Sequence
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("Error: mcp package not installed. Install it with:")
    print("  pip install mcp")
    sys.exit(1)

# Import core modules
from core.exceptions import LogAnalyzerError
from core.logging_config import get_logger

# Setup logger
logger = get_logger(__name__)

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
            description="Access log를 다양한 조건으로 필터링합니다. (time, statusCode, responseTime, client, urls, uriPatterns)",
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
            description="URI 패턴/URL을 추출합니다 (extractionType: 'urls'|'patterns'). Path variable을 *로 처리합니다.",
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
                        "description": "추출 타입: 'urls' 또는 'patterns'"
                    },
                    "params": {
                        "type": "string",
                        "description": "파라미터 문자열 (includeParams=false, maxPatterns=100, minCount=1 등)",
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
                        "description": "필터링 파라미터 문자열 (excludePatterns, includePatterns, caseSensitive, useRegex)",
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
                        "description": "파라미터 문자열 (statsType=all,summary,url,time,ip; timeInterval=10m)",
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
                        "description": "패턴 파일 경로 (선택사항, patterns_*.json)",
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
    
    except LogAnalyzerError as e:
        # Handle custom exceptions
        error_msg = f"Error executing {name}: {str(e)}"
        logger.error(error_msg)
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": error_msg,
                "type": type(e).__name__
            }, indent=2, ensure_ascii=False)
        )]
    except Exception as e:
        # Handle unexpected exceptions
        error_msg = f"Unexpected error executing {name}: {str(e)}"
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"{error_msg}\n{error_details}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": error_msg,
                "details": error_details
            }, indent=2, ensure_ascii=False)
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

