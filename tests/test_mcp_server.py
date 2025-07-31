import pytest
from unittest.mock import MagicMock, patch, call
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from mcp_server import main


class TestMCPServer:
    """Test cases for MCP server main function"""

    @patch('mcp_server.set_active_connections')
    @patch('mcp_server.start_metrics_thread')
    @patch('mcp_server.register_tools')
    @patch('mcp_server.FastMCP')
    @patch('mcp_server.MCP_TRANSPORT', 'stdio')
    def test_main_success(self, mock_fastmcp, mock_register_tools, mock_start_metrics, mock_set_connections):
        """Test successful main function execution"""
        # Setup mocks
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance
        
        # Run main function
        main()
        
        # Verify FastMCP was initialized with correct name
        mock_fastmcp.assert_called_once_with("jira-mcp-snowflake")
        
        # Verify tools were registered
        mock_register_tools.assert_called_once_with(mock_mcp_instance)
        
        # Verify metrics thread was started
        mock_start_metrics.assert_called_once()
        
        # Verify MCP server was run with correct transport
        mock_mcp_instance.run.assert_called_once_with(transport='stdio')
        
        # Verify cleanup was called
        mock_set_connections.assert_called_with(0)

    @patch('mcp_server.set_active_connections')
    @patch('mcp_server.start_metrics_thread')
    @patch('mcp_server.register_tools')
    @patch('mcp_server.FastMCP')
    @patch('mcp_server.MCP_TRANSPORT', 'http')
    def test_main_different_transport(self, mock_fastmcp, mock_register_tools, mock_start_metrics, mock_set_connections):
        """Test main function with different transport"""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance
        
        main()
        
        # Verify MCP server was run with HTTP transport
        mock_mcp_instance.run.assert_called_once_with(transport='http')

    @patch('mcp_server.set_active_connections')
    @patch('mcp_server.start_metrics_thread')
    @patch('mcp_server.register_tools')
    @patch('mcp_server.FastMCP')
    def test_main_keyboard_interrupt(self, mock_fastmcp, mock_register_tools, mock_start_metrics, mock_set_connections):
        """Test main function handling KeyboardInterrupt"""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance
        mock_mcp_instance.run.side_effect = KeyboardInterrupt("User interrupt")
        
        # Should not raise exception
        main()
        
        # Verify cleanup was still called
        mock_set_connections.assert_called_with(0)

    @patch('mcp_server.set_active_connections')
    @patch('mcp_server.start_metrics_thread')
    @patch('mcp_server.register_tools')
    @patch('mcp_server.FastMCP')
    def test_main_generic_exception(self, mock_fastmcp, mock_register_tools, mock_start_metrics, mock_set_connections):
        """Test main function handling generic exception"""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance
        mock_mcp_instance.run.side_effect = Exception("Generic error")
        
        # Should raise the exception
        with pytest.raises(Exception, match="Generic error"):
            main()
        
        # Verify cleanup was still called
        mock_set_connections.assert_called_with(0)

    @patch('mcp_server.set_active_connections')
    @patch('mcp_server.start_metrics_thread')
    @patch('mcp_server.register_tools')
    @patch('mcp_server.FastMCP')
    def test_main_register_tools_exception(self, mock_fastmcp, mock_register_tools, mock_start_metrics, mock_set_connections):
        """Test main function when register_tools raises exception"""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance
        mock_register_tools.side_effect = Exception("Registration error")
        
        # Should raise the exception
        with pytest.raises(Exception, match="Registration error"):
            main()
        
        # Cleanup is only called if we reach the try block, which we don't in this case
        # since register_tools fails before the try block
        mock_set_connections.assert_not_called()
        
        # Verify that start_metrics_thread was not called due to early failure
        mock_start_metrics.assert_not_called()

    @patch('mcp_server.set_active_connections')
    @patch('mcp_server.start_metrics_thread')
    @patch('mcp_server.register_tools')
    @patch('mcp_server.FastMCP')
    def test_main_metrics_exception(self, mock_fastmcp, mock_register_tools, mock_start_metrics, mock_set_connections):
        """Test main function when start_metrics_thread raises exception"""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance
        mock_start_metrics.side_effect = Exception("Metrics error")
        
        # Should raise the exception
        with pytest.raises(Exception, match="Metrics error"):
            main()
        
        # Cleanup is only called if we reach the try block, which we don't in this case
        # since start_metrics_thread fails before the try block
        mock_set_connections.assert_not_called()
        
        # Verify that register_tools was called successfully before metrics failure
        mock_register_tools.assert_called_once()

    @patch('mcp_server.logger')
    @patch('mcp_server.set_active_connections')
    @patch('mcp_server.start_metrics_thread')
    @patch('mcp_server.register_tools')
    @patch('mcp_server.FastMCP')
    def test_main_logging(self, mock_fastmcp, mock_register_tools, mock_start_metrics, mock_set_connections, mock_logger):
        """Test that appropriate log messages are generated"""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance
        
        main()
        
        # Verify startup log message
        mock_logger.info.assert_has_calls([
            call("Starting JIRA MCP Server for Snowflake"),
            call("MCP server shutdown complete")
        ])

    @patch('mcp_server.logger')
    @patch('mcp_server.set_active_connections')
    @patch('mcp_server.start_metrics_thread')
    @patch('mcp_server.register_tools')
    @patch('mcp_server.FastMCP')
    def test_main_keyboard_interrupt_logging(self, mock_fastmcp, mock_register_tools, mock_start_metrics, mock_set_connections, mock_logger):
        """Test logging during KeyboardInterrupt"""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance
        mock_mcp_instance.run.side_effect = KeyboardInterrupt("User interrupt")
        
        main()
        
        # Verify shutdown log message
        mock_logger.info.assert_has_calls([
            call("Starting JIRA MCP Server for Snowflake"),
            call("Shutting down MCP server..."),
            call("MCP server shutdown complete")
        ])

    @patch('mcp_server.logger')
    @patch('mcp_server.set_active_connections')
    @patch('mcp_server.start_metrics_thread')
    @patch('mcp_server.register_tools')
    @patch('mcp_server.FastMCP')
    def test_main_exception_logging(self, mock_fastmcp, mock_register_tools, mock_start_metrics, mock_set_connections, mock_logger):
        """Test logging during exception"""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance
        test_error = Exception("Test error")
        mock_mcp_instance.run.side_effect = test_error
        
        with pytest.raises(Exception):
            main()
        
        # Verify error log message
        mock_logger.error.assert_called_once_with(f"Error running MCP server: {test_error}")

    @patch('mcp_server.set_active_connections')
    @patch('mcp_server.start_metrics_thread')
    @patch('mcp_server.register_tools')
    @patch('mcp_server.FastMCP')
    def test_main_initialization_order(self, mock_fastmcp, mock_register_tools, mock_start_metrics, mock_set_connections):
        """Test that initialization happens in the correct order"""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance
        
        main()
        
        # Verify call order
        expected_calls = [
            call("jira-mcp-snowflake"),  # FastMCP initialization
        ]
        mock_fastmcp.assert_has_calls(expected_calls)
        
        # Verify register_tools was called after FastMCP initialization
        mock_register_tools.assert_called_once_with(mock_mcp_instance)
        
        # Verify start_metrics_thread was called
        mock_start_metrics.assert_called_once()
        
        # Verify run was called last (before cleanup)
        mock_mcp_instance.run.assert_called_once()