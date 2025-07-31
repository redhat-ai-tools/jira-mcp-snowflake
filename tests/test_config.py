import pytest
from unittest.mock import patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))


class TestConfig:
    """Test cases for configuration module"""

    @patch.dict('os.environ', {
        'MCP_TRANSPORT': 'http',
        'SNOWFLAKE_BASE_URL': 'https://test.snowflake.com',
        'SNOWFLAKE_DATABASE': 'TEST_DB',
        'SNOWFLAKE_SCHEMA': 'TEST_SCHEMA',
        'SNOWFLAKE_WAREHOUSE': 'TEST_WH',
        'INTERNAL_GATEWAY': 'true',
        'ENABLE_METRICS': 'true',
        'METRICS_PORT': '9090'
    })
    def test_config_from_environment(self):
        """Test configuration loading from environment variables"""
        # Re-import to get fresh config with mocked environment
        import importlib
        import config
        importlib.reload(config)
        
        assert config.MCP_TRANSPORT == 'http'
        assert config.SNOWFLAKE_BASE_URL == 'https://test.snowflake.com'
        assert config.SNOWFLAKE_DATABASE == 'TEST_DB'
        assert config.SNOWFLAKE_SCHEMA == 'TEST_SCHEMA'
        assert config.SNOWFLAKE_WAREHOUSE == 'TEST_WH'
        assert config.INTERNAL_GATEWAY == 'true'
        assert config.ENABLE_METRICS is True
        assert config.METRICS_PORT == 9090

    @patch.dict('os.environ', {}, clear=True)
    def test_config_defaults(self):
        """Test configuration defaults when environment variables are not set"""
        import importlib
        import config
        importlib.reload(config)
        
        assert config.MCP_TRANSPORT == 'stdio'  # Default
        assert config.SNOWFLAKE_WAREHOUSE == 'DEFAULT'  # Default
        assert config.INTERNAL_GATEWAY == 'false'  # Default
        assert config.ENABLE_METRICS is False  # Default
        assert config.METRICS_PORT == 8000  # Default
        
        # These should be None when not set
        assert config.SNOWFLAKE_BASE_URL is None
        assert config.SNOWFLAKE_DATABASE is None
        assert config.SNOWFLAKE_SCHEMA is None

    @patch.dict('os.environ', {'MCP_TRANSPORT': 'stdio', 'SNOWFLAKE_TOKEN': 'test_token'})
    def test_stdio_transport_token_handling(self):
        """Test token handling for stdio transport"""
        import importlib
        import config
        importlib.reload(config)
        
        assert config.MCP_TRANSPORT == 'stdio'
        assert config.SNOWFLAKE_TOKEN == 'test_token'

    @patch.dict('os.environ', {'MCP_TRANSPORT': 'http', 'SNOWFLAKE_TOKEN': 'test_token'})
    def test_non_stdio_transport_token_handling(self):
        """Test token handling for non-stdio transport"""
        import importlib
        import config
        importlib.reload(config)
        
        assert config.MCP_TRANSPORT == 'http'
        assert config.SNOWFLAKE_TOKEN is None  # Should be None for non-stdio

    @patch.dict('os.environ', {'ENABLE_METRICS': 'false'})
    def test_metrics_disabled(self):
        """Test metrics configuration when disabled"""
        import importlib
        import config
        importlib.reload(config)
        
        assert config.ENABLE_METRICS is False

    @patch.dict('os.environ', {'ENABLE_METRICS': 'true'})
    def test_metrics_enabled(self):
        """Test metrics configuration when enabled"""
        import importlib
        import config
        importlib.reload(config)
        
        assert config.ENABLE_METRICS is True

    @patch.dict('os.environ', {'ENABLE_METRICS': 'TRUE'})
    def test_metrics_case_insensitive(self):
        """Test that metrics configuration is case insensitive"""
        import importlib
        import config
        importlib.reload(config)
        
        assert config.ENABLE_METRICS is True

    @patch.dict('os.environ', {'ENABLE_METRICS': 'yes'})
    def test_metrics_non_true_value(self):
        """Test that non-'true' values disable metrics"""
        import importlib
        import config
        importlib.reload(config)
        
        assert config.ENABLE_METRICS is False

    @patch.dict('os.environ', {'METRICS_PORT': 'not_a_number'})
    def test_invalid_metrics_port(self):
        """Test handling of invalid metrics port"""
        import importlib
        
        with pytest.raises(ValueError):
            import config
            importlib.reload(config)

    def test_prometheus_availability_check(self):
        """Test Prometheus availability detection"""
        import importlib
        import config
        importlib.reload(config)
        
        # PROMETHEUS_AVAILABLE should be True or False
        assert isinstance(config.PROMETHEUS_AVAILABLE, bool)

    @patch('config.logging.basicConfig')
    def test_logging_configuration(self, mock_basicconfig):
        """Test that logging is configured"""
        import importlib
        import config
        importlib.reload(config)
        
        # Verify logging.basicConfig was called
        mock_basicconfig.assert_called_once()
        
        # Check the configuration parameters
        call_args = mock_basicconfig.call_args
        assert call_args[1]['level'] == config.logging.INFO
        assert 'format' in call_args[1]
        assert 'handlers' in call_args[1]

    @patch.dict('os.environ', {'INTERNAL_GATEWAY': 'FALSE'})
    def test_internal_gateway_case_insensitive(self):
        """Test that internal gateway configuration is case insensitive"""
        import importlib
        import config
        importlib.reload(config)
        
        assert config.INTERNAL_GATEWAY == 'FALSE'  # Should preserve original case

    @patch.dict('os.environ', {
        'SNOWFLAKE_BASE_URL': '',
        'SNOWFLAKE_DATABASE': '',
        'SNOWFLAKE_SCHEMA': ''
    })
    def test_empty_string_environment_variables(self):
        """Test handling of empty string environment variables"""
        import importlib
        import config
        importlib.reload(config)
        
        # Empty strings should be treated as None/empty
        assert config.SNOWFLAKE_BASE_URL == ''
        assert config.SNOWFLAKE_DATABASE == ''
        assert config.SNOWFLAKE_SCHEMA == ''

    def test_config_constants_immutability(self):
        """Test that configuration values are set as expected"""
        import config
        
        # Test that we can access the configuration values
        # (immutability would be tested by trying to modify them)
        assert hasattr(config, 'MCP_TRANSPORT')
        assert hasattr(config, 'SNOWFLAKE_BASE_URL')
        assert hasattr(config, 'SNOWFLAKE_DATABASE')
        assert hasattr(config, 'SNOWFLAKE_SCHEMA')
        assert hasattr(config, 'SNOWFLAKE_WAREHOUSE')
        assert hasattr(config, 'INTERNAL_GATEWAY')
        assert hasattr(config, 'SNOWFLAKE_TOKEN')
        assert hasattr(config, 'ENABLE_METRICS')
        assert hasattr(config, 'METRICS_PORT')
        assert hasattr(config, 'PROMETHEUS_AVAILABLE')

    def test_prometheus_import_error(self):
        """Test handling when prometheus_client import fails"""
        # Test the import check logic directly
        import sys
        import importlib
        
        # Temporarily remove prometheus_client from modules if it exists
        prometheus_module = sys.modules.pop('prometheus_client', None)
        
        try:
            # Mock the import to fail
            with patch.dict('sys.modules', {'prometheus_client': None}):
                # Reload config to trigger the import check
                import config
                importlib.reload(config)
                
                # Should detect that prometheus is not available
                assert config.PROMETHEUS_AVAILABLE is False
        finally:
            # Restore the module if it was there
            if prometheus_module is not None:
                sys.modules['prometheus_client'] = prometheus_module