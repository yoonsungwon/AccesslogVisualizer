"""
Utility classes and functions for Access Log Analyzer

This module provides common utilities used across multiple modules.
"""

from typing import Dict, List, Optional, Any
import pandas as pd
from .logging_config import get_logger
from .exceptions import ValidationError

logger = get_logger(__name__)


class FieldMapper:
    """
    Field mapping and validation utility for log data.

    This class helps find and map field names across different log formats,
    with fallback to alternative names.
    """

    # Common field name mappings
    FIELD_ALTERNATIVES = {
        'timestamp': ['time', 'timestamp', '@timestamp', 'datetime', 'date', 'request_time'],
        'url': ['request_url', 'url', 'uri', 'request_uri', 'path'],
        'method': ['request_method', 'method', 'verb', 'http_method'],
        'status': ['elb_status_code', 'status', 'status_code', 'response_code', 'http_status'],
        'response_time': ['target_processing_time', 'response_time', 'request_processing_time',
                         'elapsed_time', 'duration', 'processing_time'],
        'client_ip': ['client_ip', 'remote_addr', 'client', 'ip', 'clientip', 'client:port'],
        'bytes': ['sent_bytes', 'bytes_sent', 'body_bytes_sent', 'bytes', 'size'],
        'user_agent': ['user_agent', 'http_user_agent', 'agent', 'useragent'],
        'referer': ['referer', 'http_referer', 'referrer']
    }

    @classmethod
    def find_field(
        cls,
        df: pd.DataFrame,
        field_name: str,
        format_info: Dict[str, Any],
        possible_names: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Find field in DataFrame with fallback to alternative names.

        Args:
            df: DataFrame to search
            field_name: Primary field name to find
            format_info: Log format information with fieldMap
            possible_names: Optional list of alternative names to try

        Returns:
            Actual field name found in DataFrame, or None if not found
        """
        # Try the primary field name first
        if field_name in df.columns:
            return field_name

        # Try field map
        if 'fieldMap' in format_info:
            field_map = format_info['fieldMap']
            if field_name in field_map:
                mapped_name = field_map[field_name]
                if mapped_name in df.columns:
                    logger.debug(f"Using '{mapped_name}' for {field_name} (from fieldMap)")
                    return mapped_name

        # Try provided possible names
        if possible_names:
            for name in possible_names:
                if name in df.columns:
                    logger.info(f"Using '{name}' as {field_name}")
                    return name

        # Try default alternatives
        if field_name in cls.FIELD_ALTERNATIVES:
            for name in cls.FIELD_ALTERNATIVES[field_name]:
                if name in df.columns:
                    logger.info(f"Using '{name}' as {field_name}")
                    return name

        # Not found
        logger.warning(f"Field '{field_name}' not found in DataFrame")
        return None

    @classmethod
    def map_fields(
        cls,
        df: pd.DataFrame,
        format_info: Dict[str, Any],
        required_fields: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Map all common fields from DataFrame.

        Args:
            df: DataFrame with log data
            format_info: Log format information
            required_fields: List of required field names (raises error if not found)

        Returns:
            Dictionary mapping logical field names to actual column names

        Raises:
            ValidationError: If required field is not found
        """
        field_map = {}

        # Standard fields to map
        standard_fields = [
            'timestamp', 'url', 'method', 'status',
            'response_time', 'client_ip', 'bytes',
            'user_agent', 'referer'
        ]

        for field in standard_fields:
            actual_name = cls.find_field(df, field, format_info)
            if actual_name:
                field_map[field] = actual_name
            elif required_fields and field in required_fields:
                raise ValidationError(
                    field,
                    f"Required field '{field}' not found in log data"
                )

        return field_map

    @classmethod
    def get_field_value(
        cls,
        df: pd.DataFrame,
        field_name: str,
        format_info: Dict[str, Any],
        default: Any = None
    ) -> Optional[str]:
        """
        Get the actual column name for a field, with default fallback.

        Args:
            df: DataFrame to search
            field_name: Logical field name
            format_info: Log format information
            default: Default value if field not found

        Returns:
            Actual column name or default value
        """
        actual_name = cls.find_field(df, field_name, format_info)
        return actual_name if actual_name is not None else default

    @classmethod
    def validate_required_fields(
        cls,
        df: pd.DataFrame,
        format_info: Dict[str, Any],
        required_fields: List[str]
    ) -> None:
        """
        Validate that all required fields exist in DataFrame.

        Args:
            df: DataFrame to validate
            format_info: Log format information
            required_fields: List of required field names

        Raises:
            ValidationError: If any required field is not found
        """
        missing_fields = []

        for field in required_fields:
            actual_name = cls.find_field(df, field, format_info)
            if actual_name is None:
                missing_fields.append(field)

        if missing_fields:
            raise ValidationError(
                'required_fields',
                f"Missing required fields: {', '.join(missing_fields)}"
            )


class ParamParser:
    """
    Utility class for parsing parameter strings.

    Handles parameter strings in the format: "key1=value1;key2=value2"
    """

    @staticmethod
    def parse(params: str) -> Dict[str, str]:
        """
        Parse parameter string into dictionary.

        Args:
            params: Parameter string (e.g., "key1=value1;key2=value2")

        Returns:
            Dictionary of parameters
        """
        if not params or not params.strip():
            return {}

        param_dict = {}
        for param in params.split(';'):
            param = param.strip()
            if '=' in param:
                key, value = param.split('=', 1)
                param_dict[key.strip()] = value.strip()

        return param_dict

    @staticmethod
    def get(
        params: str,
        key: str,
        default: Optional[str] = None,
        required: bool = False
    ) -> Optional[str]:
        """
        Get a specific parameter value.

        Args:
            params: Parameter string
            key: Parameter key to retrieve
            default: Default value if key not found
            required: If True, raises ValidationError if key not found

        Returns:
            Parameter value or default

        Raises:
            ValidationError: If required=True and key not found
        """
        param_dict = ParamParser.parse(params)
        value = param_dict.get(key, default)

        if required and value is None:
            raise ValidationError(key, f"Required parameter '{key}' not provided")

        return value

    @staticmethod
    def get_bool(params: str, key: str, default: bool = False) -> bool:
        """Get boolean parameter value."""
        value = ParamParser.get(params, key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')

    @staticmethod
    def get_int(params: str, key: str, default: Optional[int] = None) -> Optional[int]:
        """Get integer parameter value."""
        value = ParamParser.get(params, key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            raise ValidationError(key, f"Invalid integer value: {value}")

    @staticmethod
    def get_float(params: str, key: str, default: Optional[float] = None) -> Optional[float]:
        """Get float parameter value."""
        value = ParamParser.get(params, key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            raise ValidationError(key, f"Invalid float value: {value}")

    @staticmethod
    def get_list(
        params: str,
        key: str,
        separator: str = ',',
        default: Optional[List[str]] = None
    ) -> List[str]:
        """Get list parameter value."""
        value = ParamParser.get(params, key)
        if value is None:
            return default or []
        return [item.strip() for item in value.split(separator) if item.strip()]
