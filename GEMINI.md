# Gemini Instructions

Please refer to [AI_GUIDE.md](./AI_GUIDE.md) for comprehensive project documentation and coding guidelines.

This project is an **Access Log Analyzer** - an MCP-based tool for analyzing large-scale web server access logs.

## Key Points for Gemini

- Follow the architecture and design patterns described in AI_GUIDE.md
- Use the custom exception classes from `core/exceptions.py`
- Use the logging system from `core/logging_config.py` (no print statements)
- Use `ParamParser` and `FieldMapper` utility classes from `core/utils.py`
- All functions should have type hints
- All output files use absolute paths
