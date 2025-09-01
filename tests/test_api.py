"""Tests for FastAPI application module."""


from fastapi.testclient import TestClient


class TestAPI:
    """Test cases for FastAPI application."""

    def test_health_check_endpoint(self):
        """Test health check endpoint returns correct response."""
        from jira_mcp_snowflake.src.api import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "jira-mcp-snowflake"
        assert "transport_protocol" in data
        assert data["version"] == "0.1.0"

    def test_app_configuration(self):
        """Test FastAPI app configuration."""
        from jira_mcp_snowflake.src.api import app

        assert app.title == "JIRA MCP Snowflake Server"
        # Verify the app has the lifespan handler
        assert app.router.lifespan_context is not None

    def test_app_has_mcp_mount(self):
        """Test that MCP app is mounted."""
        from jira_mcp_snowflake.src.api import app

        # Check that the app has routes (which includes the mounted MCP app)
        assert len(app.routes) > 0

    def test_server_initialization(self):
        """Test that server is properly initialized."""
        from jira_mcp_snowflake.src.api import server

        # Verify server object exists and has expected attributes
        assert server is not None
        assert hasattr(server, 'mcp')

    def test_mcp_app_creation(self):
        """Test that MCP app is created."""
        from jira_mcp_snowflake.src.api import mcp_app

        # Verify MCP app exists
        assert mcp_app is not None
