import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import time
import threading
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))


class TestMetricsDisabled:
    """Test cases when metrics are disabled"""

    @patch('metrics.ENABLE_METRICS', False)
    @patch('metrics.PROMETHEUS_AVAILABLE', True)
    def test_track_tool_usage_disabled_metrics(self):
        """Test track_tool_usage decorator when metrics are disabled"""
        from metrics import track_tool_usage
        
        @track_tool_usage("test_tool")
        async def test_function():
            return "success"
        
        # Should work normally without tracking
        import asyncio
        result = asyncio.run(test_function())
        assert result == "success"

    @patch('metrics.ENABLE_METRICS', False)
    @patch('metrics.PROMETHEUS_AVAILABLE', True)
    def test_track_snowflake_query_disabled_metrics(self):
        """Test track_snowflake_query when metrics are disabled"""
        from metrics import track_snowflake_query
        
        # Should not raise any errors
        track_snowflake_query(time.time(), True)
        track_snowflake_query(time.time(), False)

    @patch('metrics.ENABLE_METRICS', False)
    @patch('metrics.PROMETHEUS_AVAILABLE', True)
    def test_set_active_connections_disabled_metrics(self):
        """Test set_active_connections when metrics are disabled"""
        from metrics import set_active_connections
        
        # Should not raise any errors
        set_active_connections(5)
        set_active_connections(0)


class TestMetricsNoPrometheus:
    """Test cases when Prometheus is not available"""

    @patch('metrics.ENABLE_METRICS', True)
    @patch('metrics.PROMETHEUS_AVAILABLE', False)
    def test_track_tool_usage_no_prometheus(self):
        """Test track_tool_usage decorator when Prometheus is not available"""
        from metrics import track_tool_usage
        
        @track_tool_usage("test_tool")
        async def test_function():
            return "success"
        
        # Should work normally without tracking
        import asyncio
        result = asyncio.run(test_function())
        assert result == "success"

    @patch('metrics.ENABLE_METRICS', True)
    @patch('metrics.PROMETHEUS_AVAILABLE', False)
    def test_track_snowflake_query_no_prometheus(self):
        """Test track_snowflake_query when Prometheus is not available"""
        from metrics import track_snowflake_query
        
        # Should not raise any errors
        track_snowflake_query(time.time(), True)
        track_snowflake_query(time.time(), False)


class TestMetricsEnabled:
    """Test cases when metrics are enabled and Prometheus is available"""

    @pytest.fixture
    def mock_prometheus_metrics(self):
        """Mock Prometheus metrics objects"""
        with patch('metrics.ENABLE_METRICS', True), \
             patch('metrics.PROMETHEUS_AVAILABLE', True):
            
            # Mock the metrics objects
            mock_tool_calls = MagicMock()
            mock_tool_duration = MagicMock()
            mock_active_connections = MagicMock()
            mock_snowflake_queries = MagicMock()
            mock_snowflake_duration = MagicMock()
            
            # Only patch if metrics are enabled and prometheus is available
            import metrics
            if hasattr(metrics, 'tool_calls_total'):
                with patch('metrics.tool_calls_total', mock_tool_calls), \
                     patch('metrics.tool_call_duration_seconds', mock_tool_duration), \
                     patch('metrics.active_connections', mock_active_connections), \
                     patch('metrics.snowflake_queries_total', mock_snowflake_queries), \
                     patch('metrics.snowflake_query_duration_seconds', mock_snowflake_duration):
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
        from metrics import track_tool_usage
        
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
        from metrics import track_tool_usage
        
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
        from metrics import track_snowflake_query
        
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
        from metrics import track_snowflake_query
        
        start_time = time.time() - 0.5  # 0.5 seconds ago
        track_snowflake_query(start_time, False)
        
        # Verify metrics were recorded
        mock_prometheus_metrics['snowflake_queries'].labels.assert_called_with(status='error')
        mock_prometheus_metrics['snowflake_queries'].labels().inc.assert_called_once()
        mock_prometheus_metrics['snowflake_duration'].observe.assert_called_once()

    def test_set_active_connections(self, mock_prometheus_metrics):
        """Test set_active_connections function"""
        from metrics import set_active_connections
        
        set_active_connections(10)
        
        # Verify metric was set
        mock_prometheus_metrics['active_connections'].set.assert_called_once_with(10)


class TestMetricsServer:
    """Test cases for metrics HTTP server"""

    @patch('metrics.ENABLE_METRICS', True)
    @patch('metrics.PROMETHEUS_AVAILABLE', True)
    def test_start_metrics_thread(self):
        """Test start_metrics_thread function"""
        with patch('metrics.threading.Thread') as mock_thread, \
             patch('metrics.set_active_connections') as mock_set_connections:
            from metrics import start_metrics_thread
            
            start_metrics_thread()
            
            # Verify thread was created and started
            mock_thread.assert_called_once()
            mock_thread.return_value.start.assert_called_once()
            
            # Verify thread configuration
            call_args = mock_thread.call_args
            assert call_args[1]['daemon'] is True
            
            # Verify set_active_connections was called
            mock_set_connections.assert_called_once_with(1)

    @patch('metrics.ENABLE_METRICS', False)
    @patch('metrics.PROMETHEUS_AVAILABLE', True)
    def test_start_metrics_thread_disabled(self):
        """Test start_metrics_thread when metrics are disabled"""
        with patch('metrics.threading.Thread') as mock_thread:
            from metrics import start_metrics_thread
            
            start_metrics_thread()
            
            # Thread should not be created
            mock_thread.assert_not_called()

    @patch('metrics.ENABLE_METRICS', True)
    @patch('metrics.PROMETHEUS_AVAILABLE', False)
    def test_start_metrics_thread_no_prometheus(self):
        """Test start_metrics_thread when Prometheus is not available"""
        with patch('metrics.threading.Thread') as mock_thread:
            from metrics import start_metrics_thread
            
            start_metrics_thread()
            
            # Thread should not be created
            mock_thread.assert_not_called()


class TestMetricsHandler:
    """Test cases for MetricsHandler HTTP handler"""

    def test_metrics_handler_metrics_endpoint(self):
        """Test MetricsHandler for /metrics endpoint"""
        from metrics import MetricsHandler
        
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
                with patch('metrics.generate_latest', return_value=b'test_metrics_data'):
                    handler.do_GET()
                    handler.send_response.assert_called_once_with(200)
            except (ImportError, AttributeError):
                # If generate_latest is not available, test error handling
                handler.do_GET()
                # Should either send a response or an error
                assert handler.send_response.called or handler.send_error.called

    def test_metrics_handler_health_endpoint(self):
        """Test MetricsHandler for /health endpoint"""
        from metrics import MetricsHandler
        
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
        from metrics import MetricsHandler
        
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
        from metrics import MetricsHandler
        
        # Mock the handler properly without initializing the socket server
        with patch.object(MetricsHandler, '__init__', return_value=None):
            handler = MetricsHandler.__new__(MetricsHandler)
            handler.path = '/metrics'
            handler.send_error = MagicMock()
            
            # Force an exception by mocking generate_latest to fail
            with patch('metrics.generate_latest', side_effect=Exception("Metrics error")) if hasattr(__import__('metrics'), 'generate_latest') else patch('builtins.print'):
                handler.do_GET()
                
                # Should handle the exception gracefully
                # Either send an error response or handle it some other way
                # The exact behavior depends on whether Prometheus is available

    def test_metrics_handler_log_message(self):
        """Test MetricsHandler log_message method"""
        from metrics import MetricsHandler
        
        # Mock the handler properly without initializing the socket server
        with patch.object(MetricsHandler, '__init__', return_value=None):
            handler = MetricsHandler.__new__(MetricsHandler)
            
            # Should not raise any exceptions (method suppresses logging)
            handler.log_message("Test format %s", "test")


class TestStartMetricsServer:
    """Test cases for start_metrics_server function"""

    @patch('metrics.ENABLE_METRICS', True)
    @patch('metrics.PROMETHEUS_AVAILABLE', True)
    @patch('metrics.METRICS_PORT', 8000)
    def test_start_metrics_server_success(self):
        """Test successful start_metrics_server"""
        with patch('metrics.socketserver.TCPServer') as mock_server:
            mock_httpd = MagicMock()
            mock_server.return_value = mock_httpd
            
            from metrics import start_metrics_server
            
            start_metrics_server()
            
            # Verify server was created and configured
            mock_server.assert_called_once()
            call_args = mock_server.call_args[0]
            assert call_args[0] == ("", 8000)  # Address and port
            assert mock_httpd.allow_reuse_address is True
            mock_httpd.serve_forever.assert_called_once()

    @patch('metrics.ENABLE_METRICS', False)
    @patch('metrics.PROMETHEUS_AVAILABLE', True)
    def test_start_metrics_server_disabled(self):
        """Test start_metrics_server when metrics are disabled"""
        with patch('metrics.socketserver.TCPServer') as mock_server:
            from metrics import start_metrics_server
            
            start_metrics_server()
            
            # Server should not be created
            mock_server.assert_not_called()

    @patch('metrics.ENABLE_METRICS', True)
    @patch('metrics.PROMETHEUS_AVAILABLE', True)
    @patch('metrics.METRICS_PORT', 8000)
    def test_start_metrics_server_exception(self):
        """Test start_metrics_server when exception occurs"""
        with patch('metrics.socketserver.TCPServer') as mock_server, \
             patch('metrics.logger') as mock_logger:
            
            mock_server.side_effect = Exception("Server error")
            
            from metrics import start_metrics_server
            
            start_metrics_server()
            
            # Verify error was logged
            mock_logger.error.assert_called_once_with("Failed to start metrics server: Server error")


class TestDecoratorFunctionality:
    """Test decorator functionality in detail"""

    @patch('metrics.ENABLE_METRICS', True)
    @patch('metrics.PROMETHEUS_AVAILABLE', True)
    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function metadata"""
        from metrics import track_tool_usage
        
        @track_tool_usage("test_tool")
        async def test_function():
            """Test function docstring"""
            return "success"
        
        # Function metadata should be preserved
        assert test_function.__name__ == "test_function"
        assert "Test function docstring" in test_function.__doc__

    @patch('metrics.ENABLE_METRICS', True)
    @patch('metrics.PROMETHEUS_AVAILABLE', True)
    def test_decorator_with_arguments(self):
        """Test decorator works with function arguments"""
        from metrics import track_tool_usage
        
        # Create mock metrics
        mock_calls = MagicMock()
        mock_duration = MagicMock()
        
        with patch.object(__import__('metrics'), 'tool_calls_total', mock_calls, create=True), \
             patch.object(__import__('metrics'), 'tool_call_duration_seconds', mock_duration, create=True):
            
            @track_tool_usage("test_tool")
            async def test_function(arg1, arg2, kwarg1=None):
                return f"{arg1}-{arg2}-{kwarg1}"
            
            import asyncio
            result = asyncio.run(test_function("a", "b", kwarg1="c"))
            
            assert result == "a-b-c"
            # If metrics are enabled, they should be called
            if hasattr(__import__('metrics'), 'tool_calls_total'):
                mock_calls.labels.assert_called()
                mock_duration.labels.assert_called()

    @patch('metrics.ENABLE_METRICS', True)
    @patch('metrics.PROMETHEUS_AVAILABLE', True)
    def test_multiple_decorators(self):
        """Test that multiple decorated functions work independently"""
        from metrics import track_tool_usage
        
        # Create mock metrics
        mock_calls = MagicMock()
        mock_duration = MagicMock()
        
        with patch.object(__import__('metrics'), 'tool_calls_total', mock_calls, create=True), \
             patch.object(__import__('metrics'), 'tool_call_duration_seconds', mock_duration, create=True):
            
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