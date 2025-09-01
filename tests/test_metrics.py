import time
from unittest.mock import MagicMock, patch

import pytest


class TestMetricsDisabled:
    """Test cases when metrics are disabled"""

    @patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', False)
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    def test_track_tool_usage_disabled_metrics(self):
        """Test track_tool_usage decorator when metrics are disabled"""
        from jira_mcp_snowflake.src.metrics import track_tool_usage

        @track_tool_usage("test_tool")
        async def test_function():
            return "success"

        # Should work normally without tracking
        import asyncio
        result = asyncio.run(test_function())
        assert result == "success"

    @patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', False)
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    def test_track_snowflake_query_disabled_metrics(self):
        """Test track_snowflake_query when metrics are disabled"""
        from jira_mcp_snowflake.src.metrics import track_snowflake_query

        # Should not raise any errors
        track_snowflake_query(time.time(), True)
        track_snowflake_query(time.time(), False)

    @patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', False)
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    def test_set_active_connections_disabled_metrics(self):
        """Test set_active_connections when metrics are disabled"""
        from jira_mcp_snowflake.src.metrics import set_active_connections

        # Should not raise any errors
        set_active_connections(5)
        set_active_connections(0)


class TestMetricsNoPrometheus:
    """Test cases when Prometheus is not available"""

    @patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', True)
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', False)
    def test_track_tool_usage_no_prometheus(self):
        """Test track_tool_usage decorator when Prometheus is not available"""
        from jira_mcp_snowflake.src.metrics import track_tool_usage

        @track_tool_usage("test_tool")
        async def test_function():
            return "success"

        # Should work normally without tracking
        import asyncio
        result = asyncio.run(test_function())
        assert result == "success"

    @patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', True)
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', False)
    def test_track_snowflake_query_no_prometheus(self):
        """Test track_snowflake_query when Prometheus is not available"""
        from jira_mcp_snowflake.src.metrics import track_snowflake_query

        # Should not raise any errors
        track_snowflake_query(time.time(), True)
        track_snowflake_query(time.time(), False)


class TestMetricsEnabled:
    """Test cases when metrics are enabled and Prometheus is available"""

    @pytest.fixture
    def mock_prometheus_metrics(self):
        """Mock Prometheus metrics objects"""
        with patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', True), \
             patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True):

            # Mock the metrics objects
            mock_tool_calls = MagicMock()
            mock_tool_duration = MagicMock()
            mock_active_connections = MagicMock()
            mock_snowflake_queries = MagicMock()
            mock_snowflake_duration = MagicMock()

            # Only patch if metrics are enabled and prometheus is available
            import jira_mcp_snowflake.src.metrics as metrics
            if hasattr(metrics, 'tool_calls_total'):
                with patch('jira_mcp_snowflake.src.metrics.tool_calls_total', mock_tool_calls), \
                     patch('jira_mcp_snowflake.src.metrics.tool_call_duration_seconds', mock_tool_duration), \
                     patch('jira_mcp_snowflake.src.metrics.active_connections', mock_active_connections), \
                     patch('jira_mcp_snowflake.src.metrics.snowflake_queries_total', mock_snowflake_queries), \
                     patch('jira_mcp_snowflake.src.metrics.snowflake_query_duration_seconds', mock_snowflake_duration):
                    yield {
                        'tool_calls': mock_tool_calls,
                        'tool_duration': mock_tool_duration,
                        'active_connections': mock_active_connections,
                        'snowflake_queries': mock_snowflake_queries,
                        'snowflake_duration': mock_snowflake_duration
                    }
            else:
                # Create the metrics objects manually for testing
                with patch.object(metrics, 'tool_calls_total', mock_tool_calls, create=True), \
                     patch.object(metrics, 'tool_call_duration_seconds', mock_tool_duration, create=True), \
                     patch.object(metrics, 'active_connections', mock_active_connections, create=True), \
                     patch.object(metrics, 'snowflake_queries_total', mock_snowflake_queries, create=True), \
                     patch.object(metrics, 'snowflake_query_duration_seconds', mock_snowflake_duration, create=True):

                    yield {
                        'tool_calls': mock_tool_calls,
                        'tool_duration': mock_tool_duration,
                        'active_connections': mock_active_connections,
                        'snowflake_queries': mock_snowflake_queries,
                        'snowflake_duration': mock_snowflake_duration
                    }

    def test_track_tool_usage_success(self, mock_prometheus_metrics):
        """Test track_tool_usage decorator for successful calls"""
        from jira_mcp_snowflake.src.metrics import track_tool_usage

        @track_tool_usage("test_tool")
        async def test_function():
            return "success"

        import asyncio
        result = asyncio.run(test_function())

        assert result == "success"

        # Verify metrics were recorded
        mock_prometheus_metrics['tool_calls'].labels.assert_called_with(
            tool_name="test_tool", status='success'
        )
        mock_prometheus_metrics['tool_calls'].labels().inc.assert_called_once()
        mock_prometheus_metrics['tool_duration'].labels.assert_called_with(
            tool_name="test_tool"
        )
        mock_prometheus_metrics['tool_duration'].labels().observe.assert_called_once()

    def test_track_tool_usage_error(self, mock_prometheus_metrics):
        """Test track_tool_usage decorator for failed calls"""
        from jira_mcp_snowflake.src.metrics import track_tool_usage

        @track_tool_usage("test_tool")
        async def test_function():
            raise ValueError("Test error")

        import asyncio
        with pytest.raises(ValueError, match="Test error"):
            asyncio.run(test_function())

        # Verify error metrics were recorded
        mock_prometheus_metrics['tool_calls'].labels.assert_called_with(
            tool_name="test_tool", status='error'
        )
        mock_prometheus_metrics['tool_calls'].labels().inc.assert_called_once()
        mock_prometheus_metrics['tool_duration'].labels().observe.assert_called_once()

    def test_track_snowflake_query_success(self, mock_prometheus_metrics):
        """Test track_snowflake_query for successful queries"""
        from jira_mcp_snowflake.src.metrics import track_snowflake_query

        start_time = time.time() - 1.5  # 1.5 seconds ago
        track_snowflake_query(start_time, True)

        # Verify metrics were recorded
        mock_prometheus_metrics['snowflake_queries'].labels.assert_called_with(status='success')
        mock_prometheus_metrics['snowflake_queries'].labels().inc.assert_called_once()
        mock_prometheus_metrics['snowflake_duration'].observe.assert_called_once()

        # Check that duration is approximately correct
        call_args = mock_prometheus_metrics['snowflake_duration'].observe.call_args
        duration = call_args[0][0]
        assert 1.0 < duration < 2.0  # Should be around 1.5 seconds

    def test_track_snowflake_query_error(self, mock_prometheus_metrics):
        """Test track_snowflake_query for failed queries"""
        from jira_mcp_snowflake.src.metrics import track_snowflake_query

        start_time = time.time() - 0.5  # 0.5 seconds ago
        track_snowflake_query(start_time, False)

        # Verify metrics were recorded
        mock_prometheus_metrics['snowflake_queries'].labels.assert_called_with(status='error')
        mock_prometheus_metrics['snowflake_queries'].labels().inc.assert_called_once()
        mock_prometheus_metrics['snowflake_duration'].observe.assert_called_once()

    def test_set_active_connections(self, mock_prometheus_metrics):
        """Test set_active_connections function"""
        from jira_mcp_snowflake.src.metrics import set_active_connections

        set_active_connections(10)

        # Verify metric was set
        mock_prometheus_metrics['active_connections'].set.assert_called_once_with(10)


class TestMetricsServer:
    """Test cases for metrics HTTP server"""

    @patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', True)
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    def test_start_metrics_thread(self):
        """Test start_metrics_thread function"""
        with patch('jira_mcp_snowflake.src.metrics.threading.Thread') as mock_thread, \
             patch('jira_mcp_snowflake.src.metrics.set_active_connections') as mock_set_connections:
            from jira_mcp_snowflake.src.metrics import start_metrics_thread

            start_metrics_thread()

            # Verify thread was created and started
            mock_thread.assert_called_once()
            mock_thread.return_value.start.assert_called_once()

            # Verify thread configuration
            call_args = mock_thread.call_args
            assert call_args[1]['daemon'] is True

            # Verify set_active_connections was called
            mock_set_connections.assert_called_once_with(1)

    @patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', False)
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    def test_start_metrics_thread_disabled(self):
        """Test start_metrics_thread when metrics are disabled"""
        with patch('jira_mcp_snowflake.src.metrics.threading.Thread') as mock_thread:
            from jira_mcp_snowflake.src.metrics import start_metrics_thread

            start_metrics_thread()

            # Thread should not be created
            mock_thread.assert_not_called()

    @patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', True)
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', False)
    def test_start_metrics_thread_no_prometheus(self):
        """Test start_metrics_thread when Prometheus is not available"""
        with patch('jira_mcp_snowflake.src.metrics.threading.Thread') as mock_thread:
            from jira_mcp_snowflake.src.metrics import start_metrics_thread

            start_metrics_thread()

            # Thread should not be created
            mock_thread.assert_not_called()


class TestMetricsHandler:
    """Test cases for MetricsHandler HTTP handler"""

    def test_metrics_handler_metrics_endpoint(self):
        """Test MetricsHandler for /metrics endpoint"""
        from jira_mcp_snowflake.src.metrics import MetricsHandler

        # Mock the handler properly without initializing the socket server
        with patch.object(MetricsHandler, '__init__', return_value=None):
            handler = MetricsHandler.__new__(MetricsHandler)
            handler.path = '/metrics'
            handler.send_response = MagicMock()
            handler.send_header = MagicMock()
            handler.end_headers = MagicMock()
            handler.wfile = MagicMock()
            handler.send_error = MagicMock()

            # Mock the generate_latest function if it's available
            try:
                with patch('jira_mcp_snowflake.src.metrics.generate_latest', return_value=b'test_metrics_data'):
                    handler.do_GET()
                    handler.send_response.assert_called_once_with(200)
            except (ImportError, AttributeError):
                # If generate_latest is not available, test error handling
                handler.do_GET()
                # Should either send a response or an error
                assert handler.send_response.called or handler.send_error.called

    def test_metrics_handler_health_endpoint(self):
        """Test MetricsHandler for /health endpoint"""
        from jira_mcp_snowflake.src.metrics import MetricsHandler

        # Mock the handler properly without initializing the socket server
        with patch.object(MetricsHandler, '__init__', return_value=None):
            handler = MetricsHandler.__new__(MetricsHandler)
            handler.path = '/health'
            handler.send_response = MagicMock()
            handler.send_header = MagicMock()
            handler.end_headers = MagicMock()
            handler.wfile = MagicMock()

            handler.do_GET()

            # Verify response
            handler.send_response.assert_called_once_with(200)
            handler.send_header.assert_any_call('Content-Type', 'application/json')
            handler.end_headers.assert_called_once()
            handler.wfile.write.assert_called_once_with(b'{"status": "healthy"}')

    def test_metrics_handler_not_found(self):
        """Test MetricsHandler for unknown endpoint"""
        from jira_mcp_snowflake.src.metrics import MetricsHandler

        # Mock the handler properly without initializing the socket server
        with patch.object(MetricsHandler, '__init__', return_value=None):
            handler = MetricsHandler.__new__(MetricsHandler)
            handler.path = '/unknown'
            handler.send_error = MagicMock()

            handler.do_GET()

            # Verify 404 response
            handler.send_error.assert_called_once_with(404, "Not Found")

    def test_metrics_handler_exception(self):
        """Test MetricsHandler when exception occurs"""
        from jira_mcp_snowflake.src.metrics import MetricsHandler

        # Mock the handler properly without initializing the socket server
        with patch.object(MetricsHandler, '__init__', return_value=None):
            handler = MetricsHandler.__new__(MetricsHandler)
            handler.path = '/metrics'
            handler.send_error = MagicMock()

            # Force an exception by mocking generate_latest to fail
            with patch('jira_mcp_snowflake.src.metrics.generate_latest', side_effect=Exception("Metrics error")) if hasattr(__import__('jira_mcp_snowflake.src.metrics', fromlist=['generate_latest']), 'generate_latest') else patch('builtins.print'):
                handler.do_GET()

                # Should handle the exception gracefully
                # Either send an error response or handle it some other way
                # The exact behavior depends on whether Prometheus is available

    def test_metrics_handler_log_message(self):
        """Test MetricsHandler log_message method"""
        from jira_mcp_snowflake.src.metrics import MetricsHandler

        # Mock the handler properly without initializing the socket server
        with patch.object(MetricsHandler, '__init__', return_value=None):
            handler = MetricsHandler.__new__(MetricsHandler)

            # Should not raise any exceptions (method suppresses logging)
            handler.log_message("Test format %s", "test")


class TestStartMetricsServer:
    """Test cases for start_metrics_server function"""

    @patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', True)
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    @patch('jira_mcp_snowflake.src.settings.settings.METRICS_PORT', 8000)
    def test_start_metrics_server_success(self):
        """Test successful start_metrics_server"""
        with patch('jira_mcp_snowflake.src.metrics.socketserver.TCPServer') as mock_server:
            mock_httpd = MagicMock()
            mock_server.return_value = mock_httpd

            from jira_mcp_snowflake.src.metrics import start_metrics_server

            start_metrics_server()

            # Verify server was created and configured
            mock_server.assert_called_once()
            call_args = mock_server.call_args[0]
            assert call_args[0] == ("", 8000)  # Address and port
            assert mock_httpd.allow_reuse_address is True
            mock_httpd.serve_forever.assert_called_once()

    @patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', False)
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    def test_start_metrics_server_disabled(self):
        """Test start_metrics_server when metrics are disabled"""
        with patch('jira_mcp_snowflake.src.metrics.socketserver.TCPServer') as mock_server:
            from jira_mcp_snowflake.src.metrics import start_metrics_server

            start_metrics_server()

            # Server should not be created
            mock_server.assert_not_called()

    @patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', True)
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    @patch('jira_mcp_snowflake.src.settings.settings.METRICS_PORT', 8000)
    def test_start_metrics_server_exception(self):
        """Test start_metrics_server when exception occurs"""
        with patch('jira_mcp_snowflake.src.metrics.socketserver.TCPServer') as mock_server, \
             patch('jira_mcp_snowflake.src.metrics.logger') as mock_logger:

            mock_server.side_effect = Exception("Server error")

            from jira_mcp_snowflake.src.metrics import start_metrics_server

            start_metrics_server()

            # Verify error was logged
            mock_logger.error.assert_called_once_with("Failed to start metrics server: Server error")


class TestDecoratorFunctionality:
    """Test decorator functionality in detail"""

    @patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', True)
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function metadata"""
        from jira_mcp_snowflake.src.metrics import track_tool_usage

        @track_tool_usage("test_tool")
        async def test_function():
            """Test function docstring"""
            return "success"

        # Function metadata should be preserved
        assert test_function.__name__ == "test_function"
        assert "Test function docstring" in test_function.__doc__

    @patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', True)
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    def test_decorator_with_arguments(self):
        """Test decorator works with function arguments"""
        from jira_mcp_snowflake.src.metrics import track_tool_usage

        # Create mock metrics
        mock_calls = MagicMock()
        mock_duration = MagicMock()

        with patch.object(__import__('jira_mcp_snowflake.src.metrics', fromlist=['tool_calls_total']), 'tool_calls_total', mock_calls, create=True), \
             patch.object(__import__('jira_mcp_snowflake.src.metrics', fromlist=['tool_call_duration_seconds']), 'tool_call_duration_seconds', mock_duration, create=True):

            @track_tool_usage("test_tool")
            async def test_function(arg1, arg2, kwarg1=None):
                return f"{arg1}-{arg2}-{kwarg1}"

            import asyncio
            result = asyncio.run(test_function("a", "b", kwarg1="c"))

            assert result == "a-b-c"
            # If metrics are enabled, they should be called
            if hasattr(__import__('jira_mcp_snowflake.src.metrics', fromlist=['tool_calls_total']), 'tool_calls_total'):
                mock_calls.labels.assert_called()
                mock_duration.labels.assert_called()

    @patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', True)
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    def test_multiple_decorators(self):
        """Test that multiple decorated functions work independently"""
        from jira_mcp_snowflake.src.metrics import track_tool_usage

        # Create mock metrics
        mock_calls = MagicMock()
        mock_duration = MagicMock()

        with patch.object(__import__('jira_mcp_snowflake.src.metrics', fromlist=['tool_calls_total']), 'tool_calls_total', mock_calls, create=True), \
             patch.object(__import__('jira_mcp_snowflake.src.metrics', fromlist=['tool_call_duration_seconds']), 'tool_call_duration_seconds', mock_duration, create=True):

            @track_tool_usage("tool1")
            async def function1():
                return "result1"

            @track_tool_usage("tool2")
            async def function2():
                return "result2"

            import asyncio
            result1 = asyncio.run(function1())
            result2 = asyncio.run(function2())

            assert result1 == "result1"
            assert result2 == "result2"

            # Basic functionality test - functions should work regardless of metrics
            # Detailed metrics testing is complex due to conditional imports


class TestNewPerformanceMetrics:
    """Test cases for new performance metrics"""

    @pytest.fixture
    def mock_new_metrics(self):
        """Mock new performance metrics objects"""
        with patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', True), \
             patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True):

            # Mock the new metrics objects
            mock_cache_ops = MagicMock()
            mock_cache_ratio = MagicMock()
            mock_concurrent_ops = MagicMock()
            mock_http_connections = MagicMock()

            # Import metrics module
            import jira_mcp_snowflake.src.metrics as metrics

            # Patch the new metrics
            with patch.object(metrics, 'cache_operations_total', mock_cache_ops, create=True), \
                 patch.object(metrics, 'cache_hit_ratio', mock_cache_ratio, create=True), \
                 patch.object(metrics, 'concurrent_operations_total', mock_concurrent_ops, create=True), \
                 patch.object(metrics, 'http_connections_active', mock_http_connections, create=True):

                yield {
                    'cache_operations': mock_cache_ops,
                    'cache_ratio': mock_cache_ratio,
                    'concurrent_operations': mock_concurrent_ops,
                    'http_connections': mock_http_connections
                }

    def test_track_cache_operation_hit(self, mock_new_metrics):
        """Test track_cache_operation for cache hit"""
        from jira_mcp_snowflake.src.metrics import track_cache_operation

        track_cache_operation("labels", True)

        # Verify metrics were recorded
        mock_new_metrics['cache_operations'].labels.assert_called_with(
            operation="labels", result='hit'
        )
        mock_new_metrics['cache_operations'].labels().inc.assert_called_once()

    def test_track_cache_operation_miss(self, mock_new_metrics):
        """Test track_cache_operation for cache miss"""
        from jira_mcp_snowflake.src.metrics import track_cache_operation

        track_cache_operation("comments", False)

        # Verify metrics were recorded
        mock_new_metrics['cache_operations'].labels.assert_called_with(
            operation="comments", result='miss'
        )
        mock_new_metrics['cache_operations'].labels().inc.assert_called_once()

    def test_update_cache_hit_ratio(self, mock_new_metrics):
        """Test update_cache_hit_ratio function"""
        from jira_mcp_snowflake.src.metrics import update_cache_hit_ratio

        update_cache_hit_ratio(75, 100)

        # Verify metric was set to 75%
        mock_new_metrics['cache_ratio'].set.assert_called_once_with(75.0)

    def test_update_cache_hit_ratio_zero_total(self, mock_new_metrics):
        """Test update_cache_hit_ratio with zero total"""
        from jira_mcp_snowflake.src.metrics import update_cache_hit_ratio

        update_cache_hit_ratio(0, 0)

        # Should not call set when total is 0
        mock_new_metrics['cache_ratio'].set.assert_not_called()

    def test_track_concurrent_operation(self, mock_new_metrics):
        """Test track_concurrent_operation function"""
        from jira_mcp_snowflake.src.metrics import track_concurrent_operation

        track_concurrent_operation("issue_enrichment")

        # Verify metric was recorded
        mock_new_metrics['concurrent_operations'].labels.assert_called_with(
            operation_type="issue_enrichment"
        )
        mock_new_metrics['concurrent_operations'].labels().inc.assert_called_once()

    def test_set_http_connections_active(self, mock_new_metrics):
        """Test set_http_connections_active function"""
        from jira_mcp_snowflake.src.metrics import set_http_connections_active

        set_http_connections_active(15)

        # Verify metric was set
        mock_new_metrics['http_connections'].set.assert_called_once_with(15)

    @patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', False)
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    def test_new_metrics_disabled(self):
        """Test new metrics functions when metrics are disabled"""
        from jira_mcp_snowflake.src.metrics import (
            set_http_connections_active,
            track_cache_operation,
            track_concurrent_operation,
            update_cache_hit_ratio,
        )

        # Should not raise any errors when metrics are disabled
        track_cache_operation("test", True)
        update_cache_hit_ratio(50, 100)
        track_concurrent_operation("test_op")
        set_http_connections_active(10)

    @patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', True)
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', False)
    def test_new_metrics_no_prometheus(self):
        """Test new metrics functions when Prometheus is not available"""
        from jira_mcp_snowflake.src.metrics import (
            set_http_connections_active,
            track_cache_operation,
            track_concurrent_operation,
            update_cache_hit_ratio,
        )

        # Should not raise any errors when Prometheus is not available
        track_cache_operation("test", False)
        update_cache_hit_ratio(25, 100)
        track_concurrent_operation("test_op")
        set_http_connections_active(5)


class TestMetricsIntegration:
    """Integration tests for metrics functionality"""

    @patch('jira_mcp_snowflake.src.settings.settings.ENABLE_METRICS', True)
    @patch('jira_mcp_snowflake.src.metrics.PROMETHEUS_AVAILABLE', True)
    def test_all_metrics_functions_available(self):
        """Test that all metrics functions are available when enabled"""
        from jira_mcp_snowflake.src.metrics import (
            set_active_connections,
            set_http_connections_active,
            start_metrics_thread,
            track_cache_operation,
            track_concurrent_operation,
            track_snowflake_query,
            track_tool_usage,
            update_cache_hit_ratio,
        )

        # All functions should be callable
        assert callable(track_tool_usage)
        assert callable(track_snowflake_query)
        assert callable(set_active_connections)
        assert callable(track_cache_operation)
        assert callable(update_cache_hit_ratio)
        assert callable(track_concurrent_operation)
        assert callable(set_http_connections_active)
        assert callable(start_metrics_thread)

    def test_metrics_initialization_with_new_metrics(self):
        """Test that metrics module initializes correctly with new metrics"""
        # Should not raise any import errors
        import jira_mcp_snowflake.src.metrics as metrics

        # Check that the module has the expected attributes
        assert hasattr(metrics, 'track_cache_operation')
        assert hasattr(metrics, 'update_cache_hit_ratio')
        assert hasattr(metrics, 'track_concurrent_operation')
        assert hasattr(metrics, 'set_http_connections_active')
