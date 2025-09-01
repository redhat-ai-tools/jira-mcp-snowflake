from unittest.mock import MagicMock, patch

import pytest

from jira_mcp_snowflake.src.main import main
from jira_mcp_snowflake.src.mcp import JiraMCPSnowflakeServer


class TestMCPServer:
    """Test cases for MCP server main function"""

    @patch('jira_mcp_snowflake.src.main.JiraMCPSnowflakeServer')
    @patch('jira_mcp_snowflake.src.main.validate_config')
    def test_main_success(self, mock_validate_config, mock_server_class):
        """Test successful main function execution"""
        # Setup mocks
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server

        # Run main function
        main()

        # Verify configuration was validated
        mock_validate_config.assert_called_once()

        # Verify server was created and run
        mock_server_class.assert_called_once()
        mock_server.mcp.run.assert_called_once()

    @patch('jira_mcp_snowflake.src.main.JiraMCPSnowflakeServer')
    @patch('jira_mcp_snowflake.src.main.validate_config')
    def test_main_keyboard_interrupt(self, mock_validate_config, mock_server_class):
        """Test main function handling KeyboardInterrupt"""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.mcp.run.side_effect = KeyboardInterrupt("User interrupt")

        # Should not raise exception
        main()

        # Verify server was attempted to be created
        mock_server_class.assert_called_once()

    @patch('jira_mcp_snowflake.src.main.JiraMCPSnowflakeServer')
    @patch('jira_mcp_snowflake.src.main.validate_config')
    def test_main_generic_exception(self, mock_validate_config, mock_server_class):
        """Test main function handling generic exception"""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_server.mcp.run.side_effect = Exception("Generic error")

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch('jira_mcp_snowflake.src.main.JiraMCPSnowflakeServer')
    @patch('jira_mcp_snowflake.src.main.validate_config')
    def test_validation_error(self, mock_validate_config, mock_server_class):
        """Test main function when validation fails"""
        mock_validate_config.side_effect = ValueError("Invalid config")

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        # Should not try to create server
        mock_server_class.assert_not_called()


class TestJiraMCPSnowflakeServer:
    """Test cases for JiraMCPSnowflakeServer class"""

    @patch('jira_mcp_snowflake.src.mcp.FastMCP')
    def test_server_initialization(self, mock_fastmcp):
        """Test server initialization"""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance

        JiraMCPSnowflakeServer()

        # Verify FastMCP was initialized
        mock_fastmcp.assert_called_once()

        # Verify tools were registered
        assert mock_mcp_instance.tool.call_count == 4  # 4 tools should be registered

    @patch('jira_mcp_snowflake.src.mcp.FastMCP')
    def test_server_initialization_failure(self, mock_fastmcp):
        """Test server initialization failure"""
        mock_fastmcp.side_effect = Exception("Initialization error")

        with pytest.raises(Exception, match="Initialization error"):
            JiraMCPSnowflakeServer()
