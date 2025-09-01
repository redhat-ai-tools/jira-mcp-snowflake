"""Comprehensive tests for database module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jira_mcp_snowflake.src.database import (
    format_snowflake_row,
    parse_snowflake_timestamp,
    sanitize_sql_value,
)


class TestDatabaseCore:
    """Test core database functionality."""

    def test_sanitize_sql_value_string_with_quotes(self):
        """Test sanitizing string values with quotes."""
        result = sanitize_sql_value("test's value")
        assert result == "test''s value"

    def test_sanitize_sql_value_string_multiple_quotes(self):
        """Test sanitizing string with multiple quotes."""
        result = sanitize_sql_value("it's a 'test' value")
        assert result == "it''s a ''test'' value"

    def test_sanitize_sql_value_non_string(self):
        """Test sanitizing non-string values."""
        assert sanitize_sql_value(123) == 123
        assert sanitize_sql_value(None) is None
        assert sanitize_sql_value(True) is True

    def test_parse_snowflake_timestamp_with_offset(self):
        """Test parsing timestamp with timezone offset."""
        timestamp_str = "2024-01-01 12:00:00.000 -0800"
        result = parse_snowflake_timestamp(timestamp_str)
        assert "2024-01-01" in result
        assert "20:00:00" in result  # Converted to UTC

    def test_parse_snowflake_timestamp_without_offset(self):
        """Test parsing timestamp without timezone offset."""
        timestamp_str = "2024-01-01 12:00:00.000"
        result = parse_snowflake_timestamp(timestamp_str)
        assert "2024-01-01" in result
        assert "12:00:00" in result

    def test_parse_snowflake_timestamp_none(self):
        """Test parsing None timestamp."""
        result = parse_snowflake_timestamp(None)
        assert result is None

    def test_parse_snowflake_timestamp_empty(self):
        """Test parsing empty string timestamp."""
        result = parse_snowflake_timestamp("")
        assert result is None

    def test_parse_snowflake_timestamp_invalid(self):
        """Test parsing invalid timestamp format."""
        result = parse_snowflake_timestamp("invalid timestamp")
        assert result == "invalid timestamp"

    def test_format_snowflake_row_matching_lengths(self):
        """Test formatting row with matching column and data lengths."""
        columns = ["col1", "col2", "created_timestamp"]
        data = ["value1", "value2", "2024-01-01 12:00:00.000"]

        result = format_snowflake_row(columns, data)

        assert result["col1"] == "value1"
        assert result["col2"] == "value2"
        assert "2024-01-01" in result["created_timestamp"]

    def test_format_snowflake_row_mismatched_lengths(self):
        """Test formatting row with mismatched lengths."""
        columns = ["col1", "col2", "col3"]
        data = ["value1", "value2"]

        result = format_snowflake_row(columns, data)

        assert result["col1"] == "value1"
        assert result["col2"] == "value2"
        assert result["col3"] is None

    def test_format_snowflake_row_empty_data(self):
        """Test formatting row with empty data."""
        columns = ["col1", "col2"]
        data = []

        result = format_snowflake_row(columns, data)

        assert result["col1"] is None
        assert result["col2"] is None


class TestMakeSnowflakeRequest:
    """Test Snowflake HTTP request functionality."""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.settings')
    @patch('jira_mcp_snowflake.src.database.httpx.AsyncClient')
    async def test_make_snowflake_request_success(self, mock_client_class, mock_settings):
        """Test successful Snowflake request."""
        from jira_mcp_snowflake.src.database import make_snowflake_request

        mock_settings.SNOWFLAKE_BASE_URL = "https://test.snowflake.com/api/v2"

        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "data": []}
        mock_response.raise_for_status = MagicMock()

        # Mock client
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await make_snowflake_request("SELECT 1", "test_token")

        assert result == {"success": True, "data": []}
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.settings')
    async def test_make_snowflake_request_missing_token(self, mock_settings):
        """Test Snowflake request with missing token."""
        from jira_mcp_snowflake.src.database import make_snowflake_request

        mock_settings.SNOWFLAKE_BASE_URL = "https://test.snowflake.com/api/v2"

        with pytest.raises(ValueError, match="Snowflake token is required"):
            await make_snowflake_request("SELECT 1", None)

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.settings')
    @patch('jira_mcp_snowflake.src.database.httpx.AsyncClient')
    async def test_make_snowflake_request_http_error(self, mock_client_class, mock_settings):
        """Test Snowflake request with HTTP error."""
        from jira_mcp_snowflake.src.database import make_snowflake_request

        mock_settings.SNOWFLAKE_BASE_URL = "https://test.snowflake.com/api/v2"

        # Mock client that raises HTTP error
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection error")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        with pytest.raises(Exception, match="Connection error"):
            await make_snowflake_request("SELECT 1", "test_token")


class TestExecuteSnowflakeQuery:
    """Test Snowflake query execution."""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.settings')
    @patch('jira_mcp_snowflake.src.database.make_snowflake_request')
    async def test_execute_snowflake_query_success(self, mock_request, mock_settings):
        """Test successful query execution."""
        from jira_mcp_snowflake.src.database import execute_snowflake_query

        mock_settings.SNOWFLAKE_CONNECTION_METHOD = "api"

        # Mock successful response
        mock_request.return_value = {
            "data": {
                "resultSetMetaData": {
                    "rowType": [
                        {"name": "ID"},
                        {"name": "NAME"}
                    ]
                },
                "rowset": [
                    ["1", "test1"],
                    ["2", "test2"]
                ]
            }
        }

        result = await execute_snowflake_query("SELECT * FROM test", "test_token")

        assert len(result) == 2
        assert result[0] == ["1", "test1"]
        assert result[1] == ["2", "test2"]

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.settings')
    @patch('jira_mcp_snowflake.src.database.make_snowflake_request')
    async def test_execute_snowflake_query_no_data(self, mock_request, mock_settings):
        """Test query execution with no data."""
        from jira_mcp_snowflake.src.database import execute_snowflake_query

        mock_settings.SNOWFLAKE_CONNECTION_METHOD = "api"

        # Mock response with no data
        mock_request.return_value = {"data": None}

        result = await execute_snowflake_query("SELECT * FROM empty", "test_token")

        assert result == []

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.settings')
    @patch('jira_mcp_snowflake.src.database._execute_connector_query_sync')
    async def test_execute_snowflake_query_connector_method(self, mock_connector, mock_settings):
        """Test query execution using connector method."""
        from jira_mcp_snowflake.src.database import execute_snowflake_query

        mock_settings.SNOWFLAKE_CONNECTION_METHOD = "connector"

        # Mock connector response
        mock_connector.return_value = [["1", "test1"], ["2", "test2"]]

        result = await execute_snowflake_query("SELECT * FROM test")

        assert len(result) == 2
        assert result[0] == ["1", "test1"]
        mock_connector.assert_called_once_with("SELECT * FROM test")


class TestGetIssueEnrichmentData:
    """Test issue enrichment data functions."""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.get_issue_labels')
    @patch('jira_mcp_snowflake.src.database.get_issue_comments')
    @patch('jira_mcp_snowflake.src.database.get_issue_links')
    @patch('jira_mcp_snowflake.src.database.get_issue_status_changes')
    async def test_get_issue_enrichment_data_concurrent(
        self, mock_status_changes, mock_links, mock_comments, mock_labels
    ):
        """Test concurrent enrichment data retrieval."""
        from jira_mcp_snowflake.src.database import get_issue_enrichment_data_concurrent

        # Mock return values
        mock_labels.return_value = {"123": ["bug", "urgent"]}
        mock_comments.return_value = {"123": [{"id": "c1", "body": "Comment"}]}
        mock_links.return_value = {"123": [{"link_id": "456"}]}
        mock_status_changes.return_value = {"TEST-1": [{"from": "New", "to": "Open"}]}

        issue_ids = ["123"]
        issue_keys = ["TEST-1"]

        labels, comments, links, status_changes = await get_issue_enrichment_data_concurrent(
            issue_ids, issue_keys
        )

        assert labels == {"123": ["bug", "urgent"]}
        assert comments == {"123": [{"id": "c1", "body": "Comment"}]}
        assert links == {"123": [{"link_id": "456"}]}
        assert status_changes == {"TEST-1": [{"from": "New", "to": "Open"}]}

        # Verify all functions were called
        mock_labels.assert_called_once_with(["123"])
        mock_comments.assert_called_once_with(["123"])
        mock_links.assert_called_once_with(["123"])
        mock_status_changes.assert_called_once_with(["TEST-1"])

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.get_issue_labels')
    @patch('jira_mcp_snowflake.src.database.get_issue_comments')
    @patch('jira_mcp_snowflake.src.database.get_issue_links')
    @patch('jira_mcp_snowflake.src.database.get_issue_status_changes')
    async def test_get_issue_enrichment_data_concurrent_empty(
        self, mock_status_changes, mock_links, mock_comments, mock_labels
    ):
        """Test concurrent enrichment data with empty inputs."""
        from jira_mcp_snowflake.src.database import get_issue_enrichment_data_concurrent

        # Mock return values for empty inputs
        mock_labels.return_value = {}
        mock_comments.return_value = {}
        mock_links.return_value = {}
        mock_status_changes.return_value = {}

        labels, comments, links, status_changes = await get_issue_enrichment_data_concurrent(
            [], []
        )

        assert labels == {}
        assert comments == {}
        assert links == {}
        assert status_changes == {}

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.get_issue_labels')
    @patch('jira_mcp_snowflake.src.database.get_issue_comments')
    @patch('jira_mcp_snowflake.src.database.get_issue_links')
    @patch('jira_mcp_snowflake.src.database.get_issue_status_changes')
    async def test_get_issue_enrichment_data_concurrent_exception(
        self, mock_status_changes, mock_links, mock_comments, mock_labels
    ):
        """Test concurrent enrichment data with exception."""
        from jira_mcp_snowflake.src.database import get_issue_enrichment_data_concurrent

        # Mock one function to raise exception
        mock_labels.side_effect = Exception("Database error")
        mock_comments.return_value = {}
        mock_links.return_value = {}
        mock_status_changes.return_value = {}

        labels, comments, links, status_changes = await get_issue_enrichment_data_concurrent(
            ["123"], ["TEST-1"]
        )

        # Should return empty dict for the failed function
        assert labels == {}
        assert comments == {}
        assert links == {}
        assert status_changes == {}


class TestGetIssueLabels:
    """Test get_issue_labels function."""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    async def test_get_issue_labels_success(self, mock_execute):
        """Test successful label retrieval."""
        from jira_mcp_snowflake.src.database import get_issue_labels

        # Mock query response
        mock_execute.return_value = [
            ["123", "bug"],
            ["123", "urgent"],
            ["456", "feature"]
        ]

        result = await get_issue_labels(["123", "456"])

        assert result == {
            "123": ["bug", "urgent"],
            "456": ["feature"]
        }

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    async def test_get_issue_labels_empty_input(self, mock_execute):
        """Test label retrieval with empty input."""
        from jira_mcp_snowflake.src.database import get_issue_labels

        result = await get_issue_labels([])

        assert result == {}
        mock_execute.assert_not_called()

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    async def test_get_issue_labels_exception(self, mock_execute):
        """Test label retrieval with exception."""
        from jira_mcp_snowflake.src.database import get_issue_labels

        mock_execute.side_effect = Exception("Database error")

        result = await get_issue_labels(["123"])

        assert result == {}


class TestGetIssueComments:
    """Test get_issue_comments function."""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    async def test_get_issue_comments_success(self, mock_execute):
        """Test successful comment retrieval."""
        from jira_mcp_snowflake.src.database import get_issue_comments

        # Mock query response with formatted timestamp
        mock_execute.return_value = [
            ["123", "c1", "Comment body", "2024-01-01T12:00:00Z", "2024-01-01T12:00:00Z", "user", "public"]
        ]

        result = await get_issue_comments(["123"])

        assert "123" in result
        assert len(result["123"]) == 1
        comment = result["123"][0]
        assert comment["id"] == "c1"
        assert comment["body"] == "Comment body"
        assert comment["author"] == "user"
        assert comment["visibility_level"] == "public"

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    async def test_get_issue_comments_empty_input(self, mock_execute):
        """Test comment retrieval with empty input."""
        from jira_mcp_snowflake.src.database import get_issue_comments

        result = await get_issue_comments([])

        assert result == {}
        mock_execute.assert_not_called()


class TestGetIssueLinks:
    """Test get_issue_links function."""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    async def test_get_issue_links_success(self, mock_execute):
        """Test successful link retrieval."""
        from jira_mcp_snowflake.src.database import get_issue_links

        # Mock query response
        mock_execute.return_value = [
            ["123", "link1", "456", "TEST-2", "blocks", "outward"]
        ]

        result = await get_issue_links(["123"])

        assert "123" in result
        assert len(result["123"]) == 1
        link = result["123"][0]
        assert link["link_id"] == "link1"
        assert link["destination_issue_id"] == "456"
        assert link["destination_issue_key"] == "TEST-2"
        assert link["link_type"] == "blocks"
        assert link["direction"] == "outward"

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    async def test_get_issue_links_empty_input(self, mock_execute):
        """Test link retrieval with empty input."""
        from jira_mcp_snowflake.src.database import get_issue_links

        result = await get_issue_links([])

        assert result == {}
        mock_execute.assert_not_called()


class TestConnectorQueryExecution:
    """Test connector-based query execution."""

    @patch('jira_mcp_snowflake.src.database.settings')
    @patch('jira_mcp_snowflake.src.database.SnowflakeConnectorPool')
    def test_execute_connector_query_sync_success(self, mock_pool_class, mock_settings):
        """Test successful connector query execution."""
        from jira_mcp_snowflake.src.database import _execute_connector_query_sync

        # Mock settings
        mock_settings.SNOWFLAKE_ACCOUNT = "test-account"
        mock_settings.SNOWFLAKE_DATABASE = "test_db"
        mock_settings.SNOWFLAKE_SCHEMA = "test_schema"
        mock_settings.SNOWFLAKE_WAREHOUSE = "test_wh"

        # Mock pool and connection
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("1", "test1"), ("2", "test2")]
        mock_connection.cursor.return_value = mock_cursor
        mock_pool.get_connection.return_value = mock_connection

        result = _execute_connector_query_sync("SELECT * FROM test")

        assert result == [["1", "test1"], ["2", "test2"]]
        mock_cursor.execute.assert_called_once_with("SELECT * FROM test")
        mock_pool.return_connection.assert_called_once_with(mock_connection)

    @patch('jira_mcp_snowflake.src.database.settings')
    @patch('jira_mcp_snowflake.src.database.SnowflakeConnectorPool')
    def test_execute_connector_query_sync_exception(self, mock_pool_class, mock_settings):
        """Test connector query execution with exception."""
        from jira_mcp_snowflake.src.database import _execute_connector_query_sync

        # Mock settings
        mock_settings.SNOWFLAKE_ACCOUNT = "test-account"

        # Mock pool that raises exception
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool
        mock_pool.get_connection.side_effect = Exception("Connection error")

        result = _execute_connector_query_sync("SELECT * FROM test")

        assert result == []


class TestCleanupResources:
    """Test resource cleanup functionality."""

    @patch('jira_mcp_snowflake.src.database.connector_pool')
    def test_cleanup_resources_with_pool(self, mock_pool):
        """Test cleanup when connector pool exists."""
        from jira_mcp_snowflake.src.database import cleanup_resources

        mock_pool.close_all_connections = MagicMock()

        cleanup_resources()

        mock_pool.close_all_connections.assert_called_once()

    @patch('jira_mcp_snowflake.src.database.connector_pool', None)
    def test_cleanup_resources_without_pool(self):
        """Test cleanup when no connector pool exists."""
        from jira_mcp_snowflake.src.database import cleanup_resources

        # Should not raise any exceptions
        cleanup_resources()


class TestDatabaseUtilities:
    """Test various database utility functions."""

    def test_process_links_rows(self):
        """Test processing link rows."""
        from jira_mcp_snowflake.src.database import _process_links_rows

        rows = [
            ["123", "link1", "456", "TEST-2", "blocks", "outward"],
            ["123", "link2", "789", "TEST-3", "depends", "inward"]
        ]

        result = _process_links_rows(rows)

        assert "123" in result
        assert len(result["123"]) == 2

        link1 = result["123"][0]
        assert link1["link_id"] == "link1"
        assert link1["destination_issue_id"] == "456"
        assert link1["link_type"] == "blocks"

        link2 = result["123"][1]
        assert link2["link_id"] == "link2"
        assert link2["destination_issue_id"] == "789"
        assert link2["link_type"] == "depends"

    def test_process_links_rows_empty(self):
        """Test processing empty link rows."""
        from jira_mcp_snowflake.src.database import _process_links_rows

        result = _process_links_rows([])

        assert result == {}

    @patch('jira_mcp_snowflake.src.database.settings')
    def test_database_initialization_with_settings(self, mock_settings):
        """Test database module initialization with settings."""
        mock_settings.SNOWFLAKE_CONNECTION_METHOD = "connector"
        mock_settings.SNOWFLAKE_ACCOUNT = "test-account"

        # Re-import to test with mocked settings
        import importlib

        import jira_mcp_snowflake.src.database
        importlib.reload(jira_mcp_snowflake.src.database)

        # Should not raise any exceptions
        from jira_mcp_snowflake.src.database import settings
        assert settings is not None
