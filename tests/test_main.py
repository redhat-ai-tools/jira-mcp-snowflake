"""Tests for main entry point module."""

from unittest.mock import MagicMock, patch

import pytest

from jira_mcp_snowflake.src.main import main


class TestMain:
    """Test cases for main function."""

    @patch('jira_mcp_snowflake.src.main.JiraMCPSnowflakeServer')
    @patch('jira_mcp_snowflake.src.main.validate_config')
    @patch('jira_mcp_snowflake.src.main.settings')
    def test_main_stdio_transport(self, mock_settings, mock_validate, mock_server_class):
        """Test main function with stdio transport."""
        mock_settings.MCP_TRANSPORT = 'stdio'
        mock_settings.ENABLE_METRICS = False

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server

        main()

        mock_validate.assert_called_once_with(mock_settings)
        mock_server_class.assert_called_once()
        mock_server.mcp.run.assert_called_once_with(transport="stdio")

    @patch('jira_mcp_snowflake.src.main.JiraMCPSnowflakeServer')
    @patch('jira_mcp_snowflake.src.main.validate_config')
    @patch('jira_mcp_snowflake.src.main.settings')
    def test_main_http_transport(self, mock_settings, mock_validate, mock_server_class):
        """Test main function with HTTP transport."""
        mock_settings.MCP_TRANSPORT = 'http'
        mock_settings.ENABLE_METRICS = False
        mock_settings.FASTMCP_HOST = '127.0.0.1'
        mock_settings.FASTMCP_PORT = 8080

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server

        main()

        mock_validate.assert_called_once_with(mock_settings)
        mock_server_class.assert_called_once()
        mock_server.mcp.run.assert_called_once_with(
            transport="http",
            host="127.0.0.1",
            port=8080
        )

    @patch('jira_mcp_snowflake.src.metrics.start_metrics_thread')
    @patch('jira_mcp_snowflake.src.main.JiraMCPSnowflakeServer')
    @patch('jira_mcp_snowflake.src.main.validate_config')
    @patch('jira_mcp_snowflake.src.main.settings')
    def test_main_with_metrics_enabled(self, mock_settings, mock_validate, mock_server_class, mock_metrics):
        """Test main function with metrics enabled."""
        mock_settings.MCP_TRANSPORT = 'stdio'
        mock_settings.ENABLE_METRICS = True

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server

        main()

        mock_validate.assert_called_once_with(mock_settings)
        mock_server_class.assert_called_once()
        mock_metrics.assert_called_once()
        mock_server.mcp.run.assert_called_once_with(transport="stdio")

    @patch('jira_mcp_snowflake.src.main.JiraMCPSnowflakeServer')
    @patch('jira_mcp_snowflake.src.main.validate_config')
    @patch('jira_mcp_snowflake.src.main.settings')
    def test_main_keyboard_interrupt(self, mock_settings, mock_validate, mock_server_class):
        """Test main function handling KeyboardInterrupt."""
        mock_settings.MCP_TRANSPORT = 'stdio'
        mock_settings.ENABLE_METRICS = False

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.mcp.run.side_effect = KeyboardInterrupt("User interrupt")

        main()  # Should not raise exception

        mock_validate.assert_called_once_with(mock_settings)
        mock_server_class.assert_called_once()

    @patch('jira_mcp_snowflake.src.main.JiraMCPSnowflakeServer')
    @patch('jira_mcp_snowflake.src.main.validate_config')
    @patch('jira_mcp_snowflake.src.main.settings')
    def test_main_generic_exception(self, mock_settings, mock_validate, mock_server_class):
        """Test main function handling generic exception."""
        mock_settings.MCP_TRANSPORT = 'stdio'
        mock_settings.ENABLE_METRICS = False

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.mcp.run.side_effect = Exception("Generic error")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        mock_validate.assert_called_once_with(mock_settings)
        mock_server_class.assert_called_once()

    @patch('jira_mcp_snowflake.src.main.validate_config')
    @patch('jira_mcp_snowflake.src.main.settings')
    def test_main_validation_error(self, mock_settings, mock_validate):
        """Test main function handling validation error."""
        mock_validate.side_effect = ValueError("Invalid configuration")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        mock_validate.assert_called_once_with(mock_settings)

    @patch('jira_mcp_snowflake.src.main.JiraMCPSnowflakeServer')
    @patch('jira_mcp_snowflake.src.main.validate_config')
    @patch('jira_mcp_snowflake.src.main.settings')
    def test_main_sse_transport(self, mock_settings, mock_validate, mock_server_class):
        """Test main function with SSE transport."""
        mock_settings.MCP_TRANSPORT = 'sse'
        mock_settings.ENABLE_METRICS = False
        mock_settings.FASTMCP_HOST = '0.0.0.0'
        mock_settings.FASTMCP_PORT = 9000

        mock_server = MagicMock()
        mock_server_class.return_value = mock_server

        main()

        mock_server.mcp.run.assert_called_once_with(
            transport="sse",
            host="0.0.0.0",
            port=9000
        )
