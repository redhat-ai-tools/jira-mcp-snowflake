"""Tests for MCP server initialization."""

from unittest.mock import MagicMock, patch

import pytest

from jira_mcp_snowflake.src.mcp import JiraMCPSnowflakeServer


class TestJiraMCPSnowflakeServer:
    """Test cases for JIRA MCP Snowflake Server."""

    @patch('jira_mcp_snowflake.src.mcp.FastMCP')
    @patch('jira_mcp_snowflake.src.mcp.force_reconfigure_all_loggers')
    def test_server_initialization_success(self, mock_logger_config, mock_fastmcp):
        """Test successful server initialization."""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance

        server = JiraMCPSnowflakeServer()

        assert server.mcp == mock_mcp_instance
        mock_fastmcp.assert_called_once_with("jira-mcp-snowflake")
        mock_logger_config.assert_called_once()

    @patch('jira_mcp_snowflake.src.mcp.FastMCP')
    def test_server_initialization_failure(self, mock_fastmcp):
        """Test server initialization failure."""
        mock_fastmcp.side_effect = Exception("FastMCP init failed")

        with pytest.raises(Exception, match="FastMCP init failed"):
            JiraMCPSnowflakeServer()

    @patch('jira_mcp_snowflake.src.mcp.FastMCP')
    @patch('jira_mcp_snowflake.src.mcp.force_reconfigure_all_loggers')
    def test_tools_registration(self, mock_logger_config, mock_fastmcp):
        """Test that tools are properly registered."""
        mock_mcp_instance = MagicMock()
        mock_tool_decorator = MagicMock()
        mock_mcp_instance.tool.return_value = mock_tool_decorator
        mock_fastmcp.return_value = mock_mcp_instance

        JiraMCPSnowflakeServer()

        # Verify that tool() was called 4 times (for each tool)
        assert mock_mcp_instance.tool.call_count == 4

    @patch('jira_mcp_snowflake.src.mcp.FastMCP')
    @patch('jira_mcp_snowflake.src.mcp.force_reconfigure_all_loggers')
    def test_logging_setup(self, mock_logger_config, mock_fastmcp):
        """Test that logging is properly set up."""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance

        # This should not raise any exceptions
        JiraMCPSnowflakeServer()

        # Verify logger reconfiguration was called
        mock_logger_config.assert_called_once()
