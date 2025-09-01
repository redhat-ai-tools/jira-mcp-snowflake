"""Tests for settings module using Pydantic."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from jira_mcp_snowflake.src.settings import Settings, validate_config


class TestSettings:
    """Test cases for Pydantic settings."""

    @patch.dict('os.environ', {
        'MCP_TRANSPORT': 'http',
        'SNOWFLAKE_BASE_URL': 'https://test.snowflake.com/api/v2',
        'SNOWFLAKE_DATABASE': 'TEST_DB',
        'SNOWFLAKE_SCHEMA': 'TEST_SCHEMA',
        'SNOWFLAKE_WAREHOUSE': 'TEST_WH',
        'INTERNAL_GATEWAY': 'true',
        'ENABLE_METRICS': 'true',
        'METRICS_PORT': '9090'
    })
    def test_settings_from_environment(self):
        """Test settings loading from environment variables."""
        settings = Settings()

        assert settings.MCP_TRANSPORT == 'http'
        assert settings.SNOWFLAKE_BASE_URL == 'https://test.snowflake.com/api/v2'
        assert settings.SNOWFLAKE_DATABASE == 'TEST_DB'
        assert settings.SNOWFLAKE_SCHEMA == 'TEST_SCHEMA'
        assert settings.SNOWFLAKE_WAREHOUSE == 'TEST_WH'
        assert settings.INTERNAL_GATEWAY is True
        assert settings.ENABLE_METRICS is True
        assert settings.METRICS_PORT == 9090

    @patch.dict('os.environ', {}, clear=True)
    def test_settings_defaults(self):
        """Test settings defaults when environment variables are not set."""
        settings = Settings()

        assert settings.MCP_TRANSPORT == 'stdio'
        assert settings.SNOWFLAKE_WAREHOUSE == 'DEFAULT'
        assert settings.INTERNAL_GATEWAY is False
        assert settings.ENABLE_METRICS is False
        assert settings.METRICS_PORT == 8000

        # These should be None when not set
        assert settings.SNOWFLAKE_BASE_URL is None
        assert settings.SNOWFLAKE_DATABASE is None
        assert settings.SNOWFLAKE_SCHEMA is None

    @patch.dict('os.environ', {
        'SNOWFLAKE_CONNECTION_METHOD': 'connector',
        'SNOWFLAKE_ACCOUNT': 'test-account.snowflakecomputing.com',
        'SNOWFLAKE_AUTHENTICATOR': 'snowflake_jwt',
        'SNOWFLAKE_USER': 'test-user',
        'SNOWFLAKE_PRIVATE_KEY_FILE': '/path/to/key.p8',
        'SNOWFLAKE_ROLE': 'test-role'
    })
    def test_connector_settings(self):
        """Test connector-specific settings."""
        settings = Settings()

        assert settings.SNOWFLAKE_CONNECTION_METHOD == 'connector'
        assert settings.SNOWFLAKE_ACCOUNT == 'test-account.snowflakecomputing.com'
        assert settings.SNOWFLAKE_AUTHENTICATOR == 'snowflake_jwt'
        assert settings.SNOWFLAKE_USER == 'test-user'
        assert settings.SNOWFLAKE_PRIVATE_KEY_FILE == '/path/to/key.p8'
        assert settings.SNOWFLAKE_ROLE == 'test-role'

    @patch.dict('os.environ', {
        'ENABLE_METRICS': 'true',
        'FASTMCP_HOST': '0.0.0.0',
        'FASTMCP_PORT': '8080'
    })
    def test_fastmcp_settings(self):
        """Test FastMCP-specific settings."""
        settings = Settings()

        assert settings.ENABLE_METRICS is True
        assert settings.FASTMCP_HOST == '0.0.0.0'
        assert settings.FASTMCP_PORT == 8080

    @patch.dict('os.environ', {'METRICS_PORT': 'not_a_number'})
    def test_invalid_port_validation(self):
        """Test validation of invalid port numbers."""
        with pytest.raises(ValidationError):
            Settings()

    @patch.dict('os.environ', {'FASTMCP_PORT': '-1'})
    def test_negative_port_validation(self):
        """Test validation of negative port numbers."""
        with pytest.raises(ValidationError):
            Settings()

    @patch.dict('os.environ', {'FASTMCP_PORT': '70000'})
    def test_out_of_range_port_validation(self):
        """Test validation of out-of-range port numbers."""
        with pytest.raises(ValidationError):
            Settings()

    def test_settings_immutability(self):
        """Test that settings have expected attributes."""
        settings = Settings()

        # Core MCP settings
        assert hasattr(settings, 'MCP_TRANSPORT')
        assert hasattr(settings, 'INTERNAL_GATEWAY')

        # Snowflake connection settings
        assert hasattr(settings, 'SNOWFLAKE_CONNECTION_METHOD')
        assert hasattr(settings, 'SNOWFLAKE_TOKEN')
        assert hasattr(settings, 'SNOWFLAKE_BASE_URL')
        assert hasattr(settings, 'SNOWFLAKE_DATABASE')
        assert hasattr(settings, 'SNOWFLAKE_SCHEMA')
        assert hasattr(settings, 'SNOWFLAKE_WAREHOUSE')

        # Connector settings
        assert hasattr(settings, 'SNOWFLAKE_ACCOUNT')
        assert hasattr(settings, 'SNOWFLAKE_AUTHENTICATOR')
        assert hasattr(settings, 'SNOWFLAKE_USER')
        assert hasattr(settings, 'SNOWFLAKE_PASSWORD')
        assert hasattr(settings, 'SNOWFLAKE_ROLE')

        # OAuth settings
        assert hasattr(settings, 'SNOWFLAKE_OAUTH_CLIENT_ID')
        assert hasattr(settings, 'SNOWFLAKE_OAUTH_CLIENT_SECRET')
        assert hasattr(settings, 'SNOWFLAKE_OAUTH_TOKEN_URL')

        # Private key settings
        assert hasattr(settings, 'SNOWFLAKE_PRIVATE_KEY_FILE')
        assert hasattr(settings, 'SNOWFLAKE_PRIVATE_KEY_FILE_PWD')

        # Metrics and monitoring
        assert hasattr(settings, 'ENABLE_METRICS')
        assert hasattr(settings, 'METRICS_PORT')

        # FastMCP settings
        assert hasattr(settings, 'FASTMCP_HOST')
        assert hasattr(settings, 'FASTMCP_PORT')

        # Logging settings
        assert hasattr(settings, 'PYTHON_LOG_LEVEL')

    @patch.dict('os.environ', {
        'SNOWFLAKE_BASE_URL': 'invalid-url',
    })
    def test_url_validation(self):
        """Test URL validation."""
        # URL validation might be implemented in the future
        settings = Settings()
        assert settings.SNOWFLAKE_BASE_URL == 'invalid-url'


class TestValidateConfig:
    """Test cases for configuration validation."""

    def test_validate_config_valid(self):
        """Test validation with valid configuration."""
        settings = Settings(
            SNOWFLAKE_CONNECTION_METHOD='api',
            SNOWFLAKE_TOKEN='test_token',
            SNOWFLAKE_BASE_URL='https://test.snowflake.com/api/v2',
            SNOWFLAKE_DATABASE='TEST_DB',
            SNOWFLAKE_SCHEMA='TEST_SCHEMA'
        )

        # Should not raise any exceptions
        validate_config(settings)

    def test_validate_config_invalid_mcp_port(self):
        """Test validation with invalid MCP port."""
        # Pydantic validation should prevent invalid ports at creation time
        with pytest.raises(ValidationError):
            Settings(MCP_PORT=80)  # Below minimum

    def test_validate_config_invalid_fastmcp_port(self):
        """Test validation with invalid FastMCP port."""
        # Pydantic validation should prevent invalid ports at creation time
        with pytest.raises(ValidationError):
            Settings(FASTMCP_PORT=70000)  # Above maximum

    def test_validate_config_invalid_log_level(self):
        """Test validation with invalid log level."""
        settings = Settings(PYTHON_LOG_LEVEL='INVALID')

        with pytest.raises(ValueError, match="PYTHON_LOG_LEVEL must be one of"):
            validate_config(settings)

    def test_validate_config_invalid_transport(self):
        """Test validation with invalid transport protocol."""
        settings = Settings(MCP_TRANSPORT='invalid')

        with pytest.raises(ValueError, match="MCP_TRANSPORT must be one of"):
            validate_config(settings)

    def test_validate_config_invalid_connection_method(self):
        """Test validation with invalid connection method."""
        settings = Settings(SNOWFLAKE_CONNECTION_METHOD='invalid')

        with pytest.raises(ValueError, match="SNOWFLAKE_CONNECTION_METHOD must be one of"):
            validate_config(settings)


class TestPerformanceSettings:
    """Test cases for performance-related settings."""

    @patch.dict('os.environ', {
        'ENABLE_CACHING': 'false',
        'CACHE_TTL_SECONDS': '600',
        'CACHE_MAX_SIZE': '2000',
        'MAX_HTTP_CONNECTIONS': '50',
        'HTTP_TIMEOUT_SECONDS': '120'
    })
    def test_performance_settings_from_environment(self):
        """Test performance settings from environment variables."""
        settings = Settings()

        assert settings.ENABLE_CACHING is False
        assert settings.CACHE_TTL_SECONDS == 600
        assert settings.CACHE_MAX_SIZE == 2000
        assert settings.MAX_HTTP_CONNECTIONS == 50
        assert settings.HTTP_TIMEOUT_SECONDS == 120

    @patch.dict('os.environ', {}, clear=True)
    def test_performance_settings_defaults(self):
        """Test performance settings defaults."""
        settings = Settings()

        assert settings.ENABLE_CACHING is True  # Default enabled
        assert settings.CACHE_TTL_SECONDS == 300  # 5 minutes
        assert settings.CACHE_MAX_SIZE == 1000
        assert settings.MAX_HTTP_CONNECTIONS == 20
        assert settings.HTTP_TIMEOUT_SECONDS == 60
