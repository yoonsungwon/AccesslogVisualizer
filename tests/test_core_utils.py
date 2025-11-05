"""
Tests for core.utils module
"""

import pytest
import pandas as pd
from core.utils import FieldMapper, ParamParser
from core.exceptions import ValidationError


class TestParamParser:
    """Tests for ParamParser class"""

    def test_parse_empty_string(self):
        """Test parsing empty string"""
        result = ParamParser.parse("")
        assert result == {}

    def test_parse_single_param(self):
        """Test parsing single parameter"""
        result = ParamParser.parse("key1=value1")
        assert result == {"key1": "value1"}

    def test_parse_multiple_params(self):
        """Test parsing multiple parameters"""
        result = ParamParser.parse("key1=value1;key2=value2;key3=value3")
        assert result == {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }

    def test_parse_with_spaces(self):
        """Test parsing with spaces"""
        result = ParamParser.parse(" key1 = value1 ; key2 = value2 ")
        assert result == {"key1": "value1", "key2": "value2"}

    def test_get_existing_key(self):
        """Test getting existing key"""
        value = ParamParser.get("key1=value1;key2=value2", "key1")
        assert value == "value1"

    def test_get_nonexistent_key(self):
        """Test getting nonexistent key with default"""
        value = ParamParser.get("key1=value1", "key2", default="default_value")
        assert value == "default_value"

    def test_get_required_missing(self):
        """Test getting required key that's missing"""
        with pytest.raises(ValidationError):
            ParamParser.get("key1=value1", "key2", required=True)

    def test_get_bool_true(self):
        """Test parsing boolean true values"""
        assert ParamParser.get_bool("enabled=true", "enabled") is True
        assert ParamParser.get_bool("enabled=1", "enabled") is True
        assert ParamParser.get_bool("enabled=yes", "enabled") is True
        assert ParamParser.get_bool("enabled=on", "enabled") is True

    def test_get_bool_false(self):
        """Test parsing boolean false values"""
        assert ParamParser.get_bool("enabled=false", "enabled") is False
        assert ParamParser.get_bool("enabled=0", "enabled") is False
        assert ParamParser.get_bool("enabled=no", "enabled") is False

    def test_get_bool_default(self):
        """Test boolean default value"""
        assert ParamParser.get_bool("", "enabled", default=True) is True

    def test_get_int(self):
        """Test parsing integer"""
        value = ParamParser.get_int("count=42", "count")
        assert value == 42
        assert isinstance(value, int)

    def test_get_int_invalid(self):
        """Test parsing invalid integer"""
        with pytest.raises(ValidationError):
            ParamParser.get_int("count=abc", "count")

    def test_get_float(self):
        """Test parsing float"""
        value = ParamParser.get_float("rate=3.14", "rate")
        assert value == 3.14
        assert isinstance(value, float)

    def test_get_float_invalid(self):
        """Test parsing invalid float"""
        with pytest.raises(ValidationError):
            ParamParser.get_float("rate=abc", "rate")

    def test_get_list(self):
        """Test parsing list"""
        result = ParamParser.get_list("items=a,b,c", "items")
        assert result == ["a", "b", "c"]

    def test_get_list_with_spaces(self):
        """Test parsing list with spaces"""
        result = ParamParser.get_list("items= a , b , c ", "items")
        assert result == ["a", "b", "c"]

    def test_get_list_empty(self):
        """Test parsing empty list"""
        result = ParamParser.get_list("", "items", default=[])
        assert result == []


class TestFieldMapper:
    """Tests for FieldMapper class"""

    def test_find_field_exact_match(self):
        """Test finding exact field match"""
        df = pd.DataFrame({"time": [1, 2], "url": ["a", "b"]})
        format_info = {"fieldMap": {}}

        result = FieldMapper.find_field(df, "time", format_info)
        assert result == "time"

    def test_find_field_from_fieldmap(self):
        """Test finding field from fieldMap"""
        df = pd.DataFrame({"timestamp": [1, 2], "url": ["a", "b"]})
        format_info = {"fieldMap": {"time": "timestamp"}}

        result = FieldMapper.find_field(df, "time", format_info)
        assert result == "timestamp"

    def test_find_field_from_alternatives(self):
        """Test finding field from default alternatives"""
        df = pd.DataFrame({"@timestamp": [1, 2], "url": ["a", "b"]})
        format_info = {"fieldMap": {}}

        result = FieldMapper.find_field(df, "timestamp", format_info)
        assert result == "@timestamp"

    def test_find_field_not_found(self):
        """Test field not found"""
        df = pd.DataFrame({"url": ["a", "b"]})
        format_info = {"fieldMap": {}}

        result = FieldMapper.find_field(df, "time", format_info)
        assert result is None

    def test_map_fields(self):
        """Test mapping multiple fields"""
        df = pd.DataFrame({
            "timestamp": [1, 2],
            "request_url": ["a", "b"],
            "status_code": [200, 404]
        })
        format_info = {"fieldMap": {}}

        result = FieldMapper.map_fields(df, format_info)
        assert "timestamp" in result
        assert "url" in result
        assert "status" in result

    def test_validate_required_fields_success(self):
        """Test validating required fields - success"""
        df = pd.DataFrame({"time": [1, 2], "url": ["a", "b"]})
        format_info = {"fieldMap": {}}

        # Should not raise
        FieldMapper.validate_required_fields(df, format_info, ["time", "url"])

    def test_validate_required_fields_failure(self):
        """Test validating required fields - failure"""
        df = pd.DataFrame({"time": [1, 2]})
        format_info = {"fieldMap": {}}

        with pytest.raises(ValidationError):
            FieldMapper.validate_required_fields(df, format_info, ["time", "url"])
