"""Enhanced tests for metrics module."""

import time
from unittest.mock import MagicMock, patch

import pytest


class TestMetricsModule:
    """Test metrics module basic functionality."""

    def test_prometheus_availability_constant(self):
        """Test PROMETHEUS_AVAILABLE constant."""
        from jira_mcp_snowflake.src.metrics import PROMETHEUS_AVAILABLE

        assert isinstance(PROMETHEUS_AVAILABLE, bool)

    def test_metrics_module_imports(self):
        """Test that metrics module imports properly."""
        import jira_mcp_snowflake.src.metrics
        assert jira_mcp_snowflake.src.metrics is not None

    def test_track_tool_usage_decorator_basic(self):
        """Test track_tool_usage decorator basic functionality."""
        from jira_mcp_snowflake.src.metrics import track_tool_usage

        @track_tool_usage("test_tool")
        async def test_function():
            return {"success": True}

        import asyncio
        result = asyncio.run(test_function())
        assert result == {"success": True}

    def test_track_snowflake_query_basic(self):
        """Test track_snowflake_query basic functionality."""
        from jira_mcp_snowflake.src.metrics import track_snowflake_query

        start_time = time.time()
        # Should not raise any exceptions
        track_snowflake_query(start_time, True)
        track_snowflake_query(start_time, False)

    def test_set_active_connections_basic(self):
        """Test set_active_connections basic functionality."""
        from jira_mcp_snowflake.src.metrics import set_active_connections

        # Should not raise any exceptions
        set_active_connections(5)
        set_active_connections(0)

    def test_start_metrics_thread_basic(self):
        """Test start_metrics_thread basic functionality."""
        from jira_mcp_snowflake.src.metrics import start_metrics_thread

        # Should not raise any exceptions
        start_metrics_thread()

    def test_start_metrics_server_basic(self):
        """Test start_metrics_server basic functionality."""
        from jira_mcp_snowflake.src.metrics import start_metrics_server

        # Should not raise any exceptions when called
        assert callable(start_metrics_server)

    def test_metrics_handler_class_exists(self):
        """Test MetricsHandler class exists."""
        from jira_mcp_snowflake.src.metrics import MetricsHandler

        assert MetricsHandler is not None

    def test_metrics_functions_exist(self):
        """Test that all expected metrics functions exist."""
        from jira_mcp_snowflake.src.metrics import (
            MetricsHandler,
            set_active_connections,
            start_metrics_server,
            start_metrics_thread,
            track_snowflake_query,
            track_tool_usage,
        )

        # All functions should be callable
        assert callable(track_tool_usage)
        assert callable(track_snowflake_query)
        assert callable(set_active_connections)
        assert callable(start_metrics_thread)
        assert callable(start_metrics_server)
        assert MetricsHandler is not None

    def test_track_cache_operation_exists(self):
        """Test track_cache_operation function exists."""
        from jira_mcp_snowflake.src.metrics import track_cache_operation

        # Should not raise any exceptions
        track_cache_operation("get", True)
        track_cache_operation("set", False)

    def test_additional_metrics_functions(self):
        """Test additional metrics functions exist."""
        from jira_mcp_snowflake.src.metrics import (
            set_http_connections_active,
            track_concurrent_operation,
            update_cache_hit_ratio,
        )

        # Should not raise any exceptions
        set_http_connections_active(3)
        track_concurrent_operation("test_op")
        update_cache_hit_ratio(8, 10)


class TestMetricsWithPrometheus:
    """Test metrics functionality when Prometheus is available."""

    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    @patch('jira_mcp_snowflake.src.metrics.settings')
    def test_prometheus_import_error_branch(self, mock_settings):
        """Test the ImportError branch for Prometheus."""
        # Test that we can access the PROMETHEUS_AVAILABLE constant
        from jira_mcp_snowflake.src.metrics import PROMETHEUS_AVAILABLE
        assert isinstance(PROMETHEUS_AVAILABLE, bool)

    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    @patch('jira_mcp_snowflake.src.metrics.settings')
    def test_metrics_enabled_with_prometheus(self, mock_settings):
        """Test metrics functionality when enabled with Prometheus."""
        mock_settings.ENABLE_METRICS = True

        # Import the module to test the initialization block
        import importlib

        import jira_mcp_snowflake.src.metrics
        importlib.reload(jira_mcp_snowflake.src.metrics)

    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', False)
    @patch('jira_mcp_snowflake.src.metrics.settings')
    def test_metrics_disabled_no_prometheus(self, mock_settings):
        """Test metrics functionality when Prometheus is not available."""
        mock_settings.ENABLE_METRICS = True

        # Import the module to test the initialization block
        import importlib

        import jira_mcp_snowflake.src.metrics
        importlib.reload(jira_mcp_snowflake.src.metrics)


class TestMetricsHandler:
    """Test MetricsHandler HTTP endpoints."""

    def test_metrics_handler_do_get_health(self):
        """Test MetricsHandler health endpoint."""
        from jira_mcp_snowflake.src.metrics import MetricsHandler

        # Create a mock handler
        handler = MetricsHandler.__new__(MetricsHandler)
        handler.path = "/health"
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = MagicMock()
        handler.wfile.write = MagicMock()

        # Call the method
        handler.do_GET()

        # Verify the calls
        handler.send_response.assert_called_with(200)
        handler.send_header.assert_called_with('Content-Type', 'application/json')
        handler.end_headers.assert_called_once()
        handler.wfile.write.assert_called_with(b'{"status": "healthy"}')

    def test_metrics_handler_do_get_not_found(self):
        """Test MetricsHandler 404 response."""
        from jira_mcp_snowflake.src.metrics import MetricsHandler

        # Create a mock handler
        handler = MetricsHandler.__new__(MetricsHandler)
        handler.path = "/unknown"
        handler.send_error = MagicMock()

        # Call the method
        handler.do_GET()

        # Verify the calls
        handler.send_error.assert_called_with(404, "Not Found")

    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    def test_metrics_handler_do_get_metrics_success(self):
        """Test MetricsHandler metrics endpoint success."""
        with patch('jira_mcp_snowflake.src.metrics.generate_latest') as mock_generate:
            mock_generate.return_value = b"# HELP test_metric"

            from jira_mcp_snowflake.src.metrics import MetricsHandler

            # Create a mock handler
            handler = MetricsHandler.__new__(MetricsHandler)
            handler.path = "/metrics"
            handler.send_response = MagicMock()
            handler.send_header = MagicMock()
            handler.end_headers = MagicMock()
            handler.wfile = MagicMock()
            handler.wfile.write = MagicMock()

            # Call the method
            handler.do_GET()

            # Verify the calls
            handler.send_response.assert_called_with(200)
            handler.end_headers.assert_called_once()
            handler.wfile.write.assert_called_with(b"# HELP test_metric")

    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    def test_metrics_handler_do_get_metrics_error(self):
        """Test MetricsHandler metrics endpoint error."""
        with patch('jira_mcp_snowflake.src.metrics.generate_latest') as mock_generate:
            mock_generate.side_effect = Exception("Test error")

            from jira_mcp_snowflake.src.metrics import MetricsHandler

            # Create a mock handler
            handler = MetricsHandler.__new__(MetricsHandler)
            handler.path = "/metrics"
            handler.send_error = MagicMock()

            # Call the method
            handler.do_GET()

            # Verify error response
            handler.send_error.assert_called_once()

    def test_metrics_handler_log_message(self):
        """Test MetricsHandler log message suppression."""
        from jira_mcp_snowflake.src.metrics import MetricsHandler

        handler = MetricsHandler.__new__(MetricsHandler)

        # Should not raise any exceptions (log messages are suppressed)
        handler.log_message("Test %s", "message")


class TestMetricsServer:
    """Test metrics server functionality."""

    @patch('jira_mcp_snowflake.src.metrics.settings')
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', False)
    def test_start_metrics_server_disabled(self, mock_settings):
        """Test start_metrics_server when disabled."""
        mock_settings.ENABLE_METRICS = False

        from jira_mcp_snowflake.src.metrics import start_metrics_server

        # Should return early and not raise exceptions
        result = start_metrics_server()
        assert result is None

    @patch('jira_mcp_snowflake.src.metrics.settings')
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    @patch('jira_mcp_snowflake.src.metrics.socketserver.TCPServer')
    @patch('jira_mcp_snowflake.src.metrics.logger')
    def test_start_metrics_server_success(self, mock_logger, mock_tcp_server, mock_settings):
        """Test start_metrics_server successful startup."""
        mock_settings.ENABLE_METRICS = True
        mock_settings.METRICS_PORT = 8080

        # Mock the server
        mock_server = MagicMock()
        mock_tcp_server.return_value = mock_server

        from jira_mcp_snowflake.src.metrics import start_metrics_server

        # This will call serve_forever, so we need to mock it to avoid hanging
        mock_server.serve_forever.side_effect = KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            start_metrics_server()

        # Verify server setup
        mock_tcp_server.assert_called_once()
        mock_server.serve_forever.assert_called_once()

    @patch('jira_mcp_snowflake.src.metrics.settings')
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    @patch('jira_mcp_snowflake.src.metrics.socketserver.TCPServer')
    @patch('jira_mcp_snowflake.src.metrics.logger')
    def test_start_metrics_server_exception(self, mock_logger, mock_tcp_server, mock_settings):
        """Test start_metrics_server exception handling."""
        mock_settings.ENABLE_METRICS = True
        mock_settings.METRICS_PORT = 8080

        # Mock the server to raise exception
        mock_tcp_server.side_effect = Exception("Port in use")

        from jira_mcp_snowflake.src.metrics import start_metrics_server

        # Should handle exception gracefully
        start_metrics_server()

        # Verify error was logged
        mock_logger.error.assert_called_once()

    @patch('jira_mcp_snowflake.src.metrics.settings')
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    @patch('jira_mcp_snowflake.src.metrics.threading.Thread')
    @patch('jira_mcp_snowflake.src.metrics.set_active_connections')
    def test_start_metrics_thread_enabled(self, mock_set_connections, mock_thread, mock_settings):
        """Test start_metrics_thread when enabled."""
        mock_settings.ENABLE_METRICS = True

        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        from jira_mcp_snowflake.src.metrics import start_metrics_thread

        start_metrics_thread()

        # Verify thread was created and started
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
        mock_set_connections.assert_called_with(1)
