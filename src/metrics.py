import time
import threading
import logging
import http.server
import socketserver
from functools import wraps
from typing import Callable, Any

from config import ENABLE_METRICS, METRICS_PORT, PROMETHEUS_AVAILABLE

logger = logging.getLogger(__name__)

# Initialize Prometheus metrics if enabled
if ENABLE_METRICS and PROMETHEUS_AVAILABLE:
    from prometheus_client import Counter, Histogram, Gauge, CONTENT_TYPE_LATEST, generate_latest

    # Create metrics
    tool_calls_total = Counter(
        'mcp_tool_calls_total',
        'Total number of MCP tool calls',
        ['tool_name', 'status']
    )

    tool_call_duration_seconds = Histogram(
        'mcp_tool_call_duration_seconds',
        'Duration of MCP tool calls in seconds',
        ['tool_name']
    )

    active_connections = Gauge(
        'mcp_active_connections',
        'Number of active MCP connections'
    )

    snowflake_queries_total = Counter(
        'mcp_snowflake_queries_total',
        'Total number of Snowflake queries executed',
        ['status']
    )

    snowflake_query_duration_seconds = Histogram(
        'mcp_snowflake_query_duration_seconds',
        'Duration of Snowflake queries in seconds'
    )

    logger.info(f"Prometheus metrics enabled on port {METRICS_PORT}")
elif ENABLE_METRICS and not PROMETHEUS_AVAILABLE:
    logger.warning("Metrics enabled but prometheus_client not available. Install with: pip install prometheus_client")
else:
    logger.info("Prometheus metrics disabled")


def track_tool_usage(tool_name: str):
    """Decorator to track tool usage metrics"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            if ENABLE_METRICS and PROMETHEUS_AVAILABLE:
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    # Track successful call
                    tool_calls_total.labels(tool_name=tool_name, status='success').inc()
                    return result
                except Exception:
                    # Track failed call
                    tool_calls_total.labels(tool_name=tool_name, status='error').inc()
                    raise
                finally:
                    # Track duration
                    duration = time.time() - start_time
                    tool_call_duration_seconds.labels(tool_name=tool_name).observe(duration)
            else:
                return await func(*args, **kwargs)
        return wrapper
    return decorator


def track_snowflake_query(start_time: float, success: bool) -> None:
    """Track Snowflake query metrics"""
    if ENABLE_METRICS and PROMETHEUS_AVAILABLE:
        status = 'success' if success else 'error'
        snowflake_queries_total.labels(status=status).inc()

        duration = time.time() - start_time
        snowflake_query_duration_seconds.observe(duration)


def set_active_connections(count: int) -> None:
    """Set the number of active connections"""
    if ENABLE_METRICS and PROMETHEUS_AVAILABLE:
        active_connections.set(count)


class MetricsHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for Prometheus metrics endpoint"""

    def do_GET(self):
        if self.path == '/metrics':
            try:
                metrics_data = generate_latest()
                self.send_response(200)
                self.send_header('Content-Type', CONTENT_TYPE_LATEST)
                self.send_header('Content-Length', str(len(metrics_data)))
                self.end_headers()
                self.wfile.write(metrics_data)
            except Exception as e:
                logger.error(f"Error generating metrics: {e}")
                self.send_error(500, f"Internal Server Error: {e}")
        elif self.path == '/health':
            # Health check endpoint
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
        else:
            self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        # Suppress default HTTP server logging to avoid interfering with MCP protocol
        pass


def start_metrics_server() -> None:
    """Start the metrics HTTP server in a separate thread"""
    if not (ENABLE_METRICS and PROMETHEUS_AVAILABLE):
        return

    try:
        httpd = socketserver.TCPServer(("", METRICS_PORT), MetricsHandler)
        httpd.allow_reuse_address = True
        logger.info(f"Metrics server started on port {METRICS_PORT}")
        logger.info(f"Metrics available at http://localhost:{METRICS_PORT}/metrics")
        logger.info(f"Health check available at http://localhost:{METRICS_PORT}/health")
        httpd.serve_forever()
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")


def start_metrics_thread() -> None:
    """Start metrics server in a background thread"""
    if ENABLE_METRICS and PROMETHEUS_AVAILABLE:
        metrics_thread = threading.Thread(target=start_metrics_server, daemon=True)
        metrics_thread.start()
        set_active_connections(1)
