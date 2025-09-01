import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from jira_mcp_snowflake.src.database import (
    SnowflakeConnectorPool,
    _execute_connector_query_sync,
    _process_links_rows,
    cleanup_resources,
    clear_cache,
    execute_queries_in_batches,
    execute_snowflake_query,
    execute_snowflake_query_connector,
    format_snowflake_row,
    format_snowflake_rows_concurrent,
    get_cache_key,
    get_connection_pool,
    get_connector_pool,
    get_from_cache,
    get_issue_comments,
    get_issue_enrichment_data_concurrent,
    get_issue_labels,
    get_issue_links,
    get_issue_status_changes,
    make_snowflake_request,
    parse_snowflake_timestamp,
    sanitize_sql_value,
    set_in_cache,
)


class TestSanitizeSqlValue:
    """Test cases for sanitize_sql_value function"""

    def test_sanitize_string_with_quotes(self):
        """Test sanitizing string with single quotes"""
        result = sanitize_sql_value("test'value")
        assert result == "test''value"

    def test_sanitize_string_multiple_quotes(self):
        """Test sanitizing string with multiple single quotes"""
        result = sanitize_sql_value("test'val'ue'")
        assert result == "test''val''ue''"

    def test_sanitize_string_no_quotes(self):
        """Test sanitizing string without quotes"""
        result = sanitize_sql_value("test_value")
        assert result == "test_value"

    def test_sanitize_non_string(self):
        """Test sanitizing non-string values"""
        result = sanitize_sql_value(123)
        assert result == "123"

    def test_sanitize_empty_string(self):
        """Test sanitizing empty string"""
        result = sanitize_sql_value("")
        assert result == ""


class TestMakeSnowflakeRequest:
    """Test cases for make_snowflake_request function"""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_TOKEN', 'default_token')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_BASE_URL', 'https://test.snowflake.com')
    @patch('jira_mcp_snowflake.src.database.httpx.AsyncClient')
    async def test_successful_post_request(self, mock_client_class):
        """Test successful POST request"""
        # Create mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        # Create mock client instance
        mock_client_instance = AsyncMock()
        mock_client_instance.request = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        # Set up the client class to return our mock instance
        mock_client_class.return_value = mock_client_instance

        result = await make_snowflake_request("endpoint", "POST", {"test": "data"})

        assert result == {"data": []}
        mock_client_instance.request.assert_called_once()

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_TOKEN', None)
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_BASE_URL', 'https://test.snowflake.com')
    async def test_missing_token(self):
        """Test request with missing token"""
        result = await make_snowflake_request("endpoint", "POST", {"test": "data"})
        assert result is None

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_TOKEN', 'default_token')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_BASE_URL', 'https://test.snowflake.com')
    @patch('jira_mcp_snowflake.src.database.httpx.AsyncClient')
    async def test_provided_token_override(self, mock_client_class):
        """Test that provided token overrides default"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.request = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client_instance

        await make_snowflake_request("endpoint", "POST", {"test": "data"}, "custom_token")

        # Verify custom token was used
        args, kwargs = mock_client_instance.request.call_args
        headers = kwargs['headers']
        assert headers['Authorization'] == 'Bearer custom_token'

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_TOKEN', 'test_token')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_BASE_URL', 'https://test.snowflake.com')
    @patch('jira_mcp_snowflake.src.database.httpx.AsyncClient')
    async def test_get_request(self, mock_client_class):
        """Test GET request with params"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.request = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client_instance

        await make_snowflake_request("endpoint", "GET", {"param": "value"})

        # Verify params were used instead of json
        args, kwargs = mock_client_instance.request.call_args
        assert 'params' in kwargs
        assert 'json' not in kwargs

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_TOKEN', 'test_token')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_BASE_URL', 'https://test.snowflake.com')
    @patch('jira_mcp_snowflake.src.database.httpx.AsyncClient')
    async def test_json_decode_error(self, mock_client_class):
        """Test handling of JSON decode error"""
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Invalid response"
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.request = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client_instance

        result = await make_snowflake_request("endpoint", "POST", {"test": "data"})
        assert result is None

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_TOKEN', 'test_token')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_BASE_URL', 'https://test.snowflake.com')
    @patch('jira_mcp_snowflake.src.database.httpx.AsyncClient')
    async def test_http_error(self, mock_client_class):
        """Test handling of HTTP error"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        mock_client_instance = AsyncMock()
        mock_client_instance.request = AsyncMock(side_effect=httpx.HTTPStatusError("400", request=None, response=mock_response))
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client_instance

        result = await make_snowflake_request("endpoint", "POST", {"test": "data"})
        assert result is None


class TestExecuteSnowflakeQuery:
    """Test cases for execute_snowflake_query function"""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.make_snowflake_request')
    @patch('jira_mcp_snowflake.src.database.track_snowflake_query')
    async def test_successful_query(self, mock_track, mock_request):
        """Test successful query execution"""
        mock_request.return_value = {
            "data": [["row1col1", "row1col2"], ["row2col1", "row2col2"]]
        }

        result = await execute_snowflake_query("SELECT * FROM test", "token")

        assert len(result) == 2
        assert result[0] == ["row1col1", "row1col2"]
        mock_track.assert_called_once()

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.make_snowflake_request')
    @patch('jira_mcp_snowflake.src.database.track_snowflake_query')
    @patch('jira_mcp_snowflake.src.database.get_from_cache')
    @patch('jira_mcp_snowflake.src.database.set_in_cache')
    async def test_query_with_pagination(self, mock_set_cache, mock_get_cache, mock_track, mock_request):
        """Test query execution with pagination"""
        # Mock cache miss
        mock_get_cache.return_value = None

        # First call returns data with partition info
        first_response = {
            "data": [["row1col1", "row1col2"]],
            "statementHandle": "handle123",
            "resultSetMetaData": {
                "partitionInfo": [{"startRow": 0}, {"startRow": 1}]
            }
        }

        # Second call returns additional partition data
        second_response = {
            "data": [["row2col1", "row2col2"]]
        }

        mock_request.side_effect = [first_response, second_response]

        result = await execute_snowflake_query("SELECT * FROM test", "token")

        assert len(result) == 2
        assert result[0] == ["row1col1", "row1col2"]
        assert result[1] == ["row2col1", "row2col2"]
        assert mock_request.call_count == 2

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.make_snowflake_request')
    @patch('jira_mcp_snowflake.src.database.track_snowflake_query')
    @patch('jira_mcp_snowflake.src.database.clear_cache')
    async def test_query_resultset_format(self, mock_clear_cache, mock_track, mock_request):
        """Test query execution with resultSet format"""
        mock_clear_cache()  # Clear cache before test
        mock_request.return_value = {
            "resultSet": {
                "data": [["row1col1", "row1col2"]]
            }
        }

        result = await execute_snowflake_query("SELECT * FROM test", "token", use_cache=False)

        assert len(result) == 1
        assert result[0] == ["row1col1", "row1col2"]

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.make_snowflake_request')
    @patch('jira_mcp_snowflake.src.database.track_snowflake_query')
    @patch('jira_mcp_snowflake.src.database.clear_cache')
    async def test_query_no_response(self, mock_clear_cache, mock_track, mock_request):
        """Test query execution when no response is returned"""
        mock_clear_cache()  # Clear cache before test
        mock_request.return_value = None

        result = await execute_snowflake_query("SELECT * FROM test", "token", use_cache=False)

        assert result == []
        mock_track.assert_called_once()

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.make_snowflake_request')
    @patch('jira_mcp_snowflake.src.database.track_snowflake_query')
    @patch('jira_mcp_snowflake.src.database.clear_cache')
    async def test_query_exception(self, mock_clear_cache, mock_track, mock_request):
        """Test query execution when exception occurs"""
        mock_clear_cache()  # Clear cache before test
        mock_request.side_effect = Exception("Database error")

        result = await execute_snowflake_query("SELECT * FROM test", "token", use_cache=False)

        assert result == []
        mock_track.assert_called_once()


class TestParseSnowflakeTimestamp:
    """Test cases for parse_snowflake_timestamp function"""

    def test_parse_timestamp_with_offset(self):
        """Test parsing timestamp with timezone offset"""
        # Test with actual KONFLUX-9430 timestamp
        timestamp_str = "1753767533.658000000 1440"
        result = parse_snowflake_timestamp(timestamp_str)

        # Should convert to simplified format with timezone offset applied
        assert result == "2025-07-30T05:38:53"

    def test_parse_timestamp_different_offsets(self):
        """Test parsing timestamps with different timezone offsets"""
        test_cases = [
            ("1753767533.658000000 1440", "2025-07-30T05:38:53"),  # +24 hours
            ("1753767533.658000000 0", "2025-07-29T05:38:53"),     # no offset
            ("1753767533.658000000 -300", "2025-07-29T00:38:53"),  # -5 hours
        ]

        for input_timestamp, expected_output in test_cases:
            result = parse_snowflake_timestamp(input_timestamp)
            assert result == expected_output

    def test_parse_timestamp_without_offset(self):
        """Test parsing timestamp without timezone offset"""
        timestamp_str = "1753767533.658000000"
        result = parse_snowflake_timestamp(timestamp_str)

        # Should convert to simplified format
        assert result == "2025-07-29T05:38:53"

    def test_parse_timestamp_integer_seconds(self):
        """Test parsing timestamp with integer seconds"""
        timestamp_str = "1753767533 1440"
        result = parse_snowflake_timestamp(timestamp_str)

        # Should handle integer timestamps
        assert result == "2025-07-30T05:38:53"

    def test_parse_timestamp_none_input(self):
        """Test parsing None input"""
        result = parse_snowflake_timestamp(None)
        assert result is None

    def test_parse_timestamp_empty_string(self):
        """Test parsing empty string"""
        result = parse_snowflake_timestamp("")
        assert result == ""

    def test_parse_timestamp_non_string_input(self):
        """Test parsing non-string input"""
        result = parse_snowflake_timestamp(123)
        assert result == 123

    def test_parse_timestamp_invalid_format(self):
        """Test parsing invalid timestamp format"""
        invalid_timestamps = [
            "invalid_timestamp",
            "1753767533.658000000 invalid_offset",
            "not_a_number 1440",
        ]

        for invalid_ts in invalid_timestamps:
            result = parse_snowflake_timestamp(invalid_ts)
            # Should return original string if parsing fails
            assert result == invalid_ts

    def test_parse_timestamp_with_extra_data(self):
        """Test parsing timestamp with extra data - should still parse the valid parts"""
        timestamp_str = "1753767533.658000000 1440 extra_data"
        result = parse_snowflake_timestamp(timestamp_str)

        # Function should parse the first two parts and ignore extra data
        assert result == "2025-07-30T05:38:53"

    def test_parse_timestamp_edge_cases(self):
        """Test parsing edge case timestamps"""
        test_cases = [
            # Very large offset
            ("1753767533.658000000 43200", "2025-08-28T05:38:53"),  # +30 days
            # Negative large offset
            ("1753767533.658000000 -43200", "2025-06-29T05:38:53"),  # -30 days
            # Zero timestamp
            ("0.0 0", "1970-01-01T00:00:00"),
        ]

        for input_timestamp, expected_output in test_cases:
            result = parse_snowflake_timestamp(input_timestamp)
            assert result == expected_output


class TestFormatSnowflakeRow:
    """Test cases for format_snowflake_row function"""

    def test_format_matching_lengths(self):
        """Test formatting with matching row and column lengths"""
        row_data = ["value1", "value2", "value3"]
        columns = ["col1", "col2", "col3"]

        result = format_snowflake_row(row_data, columns)

        expected = {"col1": "value1", "col2": "value2", "col3": "value3"}
        assert result == expected

    def test_format_mismatched_lengths(self):
        """Test formatting with mismatched row and column lengths"""
        row_data = ["value1", "value2"]
        columns = ["col1", "col2", "col3"]

        result = format_snowflake_row(row_data, columns)

        assert result == {}

    def test_format_empty_data(self):
        """Test formatting with empty data"""
        row_data = []
        columns = []

        result = format_snowflake_row(row_data, columns)

        assert result == {}

    def test_format_with_timestamp_columns(self):
        """Test formatting with timestamp columns that should be parsed"""
        row_data = ["123", "1753767533.658000000 1440", "1753824211.261000000 1440", "regular_value"]
        columns = ["ID", "CREATED", "RESOLUTIONDATE", "SUMMARY"]

        result = format_snowflake_row(row_data, columns)

        expected = {
            "ID": "123",
            "CREATED": "2025-07-30T05:38:53",
            "RESOLUTIONDATE": "2025-07-30T21:23:31",
            "SUMMARY": "regular_value"
        }
        assert result == expected

    def test_format_with_change_timestamp_column(self):
        """Test formatting with CHANGE_TIMESTAMP column specifically"""
        row_data = ["ITBEAKER-549", "1751291507.768000000", "New", "In Progress"]
        columns = ["ISSUE_KEY", "CHANGE_TIMESTAMP", "FROM_STATUS", "TO_STATUS"]

        result = format_snowflake_row(row_data, columns)

        expected = {
            "ISSUE_KEY": "ITBEAKER-549",
            "CHANGE_TIMESTAMP": "2025-06-30T13:51:47",
            "FROM_STATUS": "New",
            "TO_STATUS": "In Progress"
        }
        assert result == expected

    def test_format_with_non_timestamp_columns(self):
        """Test formatting with non-timestamp columns that should not be parsed"""
        row_data = ["123", "1753767533.658000000 1440", "some_description"]
        columns = ["ID", "SOME_NUMBER", "DESCRIPTION"]  # SOME_NUMBER is not a recognized timestamp column

        result = format_snowflake_row(row_data, columns)

        expected = {
            "ID": "123",
            "SOME_NUMBER": "1753767533.658000000 1440",  # Should not be parsed
            "DESCRIPTION": "some_description"
        }
        assert result == expected

    def test_format_with_null_timestamp_values(self):
        """Test formatting with null timestamp values"""
        row_data = ["123", None, "", "value"]
        columns = ["ID", "CREATED", "UPDATED", "SUMMARY"]

        result = format_snowflake_row(row_data, columns)

        expected = {
            "ID": "123",
            "CREATED": None,  # None should remain None
            "UPDATED": "",    # Empty string should remain empty
            "SUMMARY": "value"
        }
        assert result == expected

    def test_format_case_insensitive_timestamp_columns(self):
        """Test that timestamp column detection is case insensitive"""
        row_data = ["123", "1753767533.658000000 1440", "1753824211.261000000 1440"]
        columns = ["id", "created", "Updated"]  # Mixed case

        result = format_snowflake_row(row_data, columns)

        # Should still parse timestamps regardless of case
        assert "2025-07-30T05:38:53" in result["created"]
        assert "2025-07-30T21:23:31" in result["Updated"]


class TestGetIssueLabels:
    """Test cases for get_issue_labels function"""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.database.format_snowflake_row')
    async def test_get_labels_success(self, mock_format, mock_query):
        """Test successful label retrieval"""
        mock_query.return_value = [
            ["123", "bug"],
            ["123", "urgent"],
            ["456", "feature"]
        ]

        mock_format.side_effect = [
            {"ISSUE": "123", "LABEL": "bug"},
            {"ISSUE": "123", "LABEL": "urgent"},
            {"ISSUE": "456", "LABEL": "feature"}
        ]

        result = await get_issue_labels(["123", "456"], "token")

        expected = {
            "123": ["bug", "urgent"],
            "456": ["feature"]
        }
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_labels_empty_input(self):
        """Test with empty issue IDs list"""
        result = await get_issue_labels([], "token")
        assert result == {}

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    async def test_get_labels_invalid_ids(self, mock_query):
        """Test with invalid issue IDs"""
        result = await get_issue_labels(["abc", "def"], "token")
        assert result == {}
        mock_query.assert_not_called()

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    async def test_get_labels_mixed_valid_invalid_ids(self, mock_query):
        """Test with mix of valid and invalid issue IDs"""
        mock_query.return_value = []

        await get_issue_labels(["123", "abc", "456"], "token")

        # Should only query with valid IDs
        mock_query.assert_called_once()
        sql_call = mock_query.call_args[0][0]
        assert "'123','456'" in sql_call
        assert "'abc'" not in sql_call

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    async def test_get_labels_exception(self, mock_query):
        """Test exception handling"""
        mock_query.side_effect = Exception("Database error")

        result = await get_issue_labels(["123"], "token")
        assert result == {}


class TestGetIssueComments:
    """Test cases for get_issue_comments function"""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.database.format_snowflake_row')
    async def test_get_comments_success(self, mock_format, mock_query):
        """Test successful comment retrieval"""
        mock_query.return_value = [
            ["comment1", "123", "public", "Comment body 1", "2024-01-01", "2024-01-02"],
            ["comment2", "123", "private", "Comment body 2", "2024-01-03", "2024-01-04"]
        ]

        mock_format.side_effect = [
            {
                "ID": "comment1", "ISSUEID": "123", "ROLELEVEL": "public",
                "BODY": "Comment body 1", "CREATED": "2024-01-01", "UPDATED": "2024-01-02"
            },
            {
                "ID": "comment2", "ISSUEID": "123", "ROLELEVEL": "private",
                "BODY": "Comment body 2", "CREATED": "2024-01-03", "UPDATED": "2024-01-04"
            }
        ]

        result = await get_issue_comments(["123"], "token")

        expected = {
            "123": [
                {
                    "id": "comment1", "role_level": "public", "body": "Comment body 1",
                    "created": "2024-01-01", "updated": "2024-01-02"
                },
                {
                    "id": "comment2", "role_level": "private", "body": "Comment body 2",
                    "created": "2024-01-03", "updated": "2024-01-04"
                }
            ]
        }
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_comments_empty_input(self):
        """Test with empty issue IDs list"""
        result = await get_issue_comments([], "token")
        assert result == {}

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.database.clear_cache')
    async def test_get_comments_exception(self, mock_clear_cache, mock_query):
        """Test exception handling"""
        mock_clear_cache()  # Clear cache before test
        mock_query.side_effect = Exception("Database error")

        result = await get_issue_comments(["123"], "token", use_cache=False)
        assert result == {}


class TestGetIssueLinks:
    """Test cases for get_issue_links function"""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.database.format_snowflake_row')
    async def test_get_links_success(self, mock_format, mock_query):
        """Test successful link retrieval"""
        mock_query.return_value = [
            [
                "link1", "123", "456", "1", "blocks", "is blocked by", "blocks",
                "TEST-1", "TEST-2", "Source summary", "Destination summary"
            ]
        ]

        mock_format.return_value = {
            "LINK_ID": "link1", "SOURCE": "123", "DESTINATION": "456", "SEQUENCE": "1",
            "LINKNAME": "blocks", "INWARD": "is blocked by", "OUTWARD": "blocks",
            "SOURCE_KEY": "TEST-1", "DESTINATION_KEY": "TEST-2",
            "SOURCE_SUMMARY": "Source summary", "DESTINATION_SUMMARY": "Destination summary"
        }

        result = await get_issue_links(["123"], "token")

        assert "123" in result
        assert len(result["123"]) == 1
        link = result["123"][0]
        assert link["relationship"] == "outward"
        assert link["related_issue_id"] == "456"
        assert link["related_issue_key"] == "TEST-2"

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.database.format_snowflake_row')
    async def test_get_links_bidirectional(self, mock_format, mock_query):
        """Test that links appear for both source and destination issues"""
        mock_query.return_value = [
            [
                "link1", "123", "456", "1", "blocks", "is blocked by", "blocks",
                "TEST-1", "TEST-2", "Source summary", "Destination summary"
            ]
        ]

        mock_format.return_value = {
            "LINK_ID": "link1", "SOURCE": "123", "DESTINATION": "456", "SEQUENCE": "1",
            "LINKNAME": "blocks", "INWARD": "is blocked by", "OUTWARD": "blocks",
            "SOURCE_KEY": "TEST-1", "DESTINATION_KEY": "TEST-2",
            "SOURCE_SUMMARY": "Source summary", "DESTINATION_SUMMARY": "Destination summary"
        }

        result = await get_issue_links(["123", "456"], "token")

        # Should have links for both issues
        assert "123" in result
        assert "456" in result

        # Check source perspective
        source_link = result["123"][0]
        assert source_link["relationship"] == "outward"
        assert source_link["related_issue_id"] == "456"

        # Check destination perspective
        dest_link = result["456"][0]
        assert dest_link["relationship"] == "inward"
        assert dest_link["related_issue_id"] == "123"

    @pytest.mark.asyncio
    async def test_get_links_empty_input(self):
        """Test with empty issue IDs list"""
        result = await get_issue_links([], "token")
        assert result == {}

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.database.clear_cache')
    async def test_get_links_exception(self, mock_clear_cache, mock_query):
        """Test exception handling"""
        mock_clear_cache()  # Clear cache before test
        mock_query.side_effect = Exception("Database error")

        result = await get_issue_links(["123"], "token", use_cache=False)
        assert result == {}


class TestGetIssueStatusChanges:
    """Test cases for get_issue_status_changes function"""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.database.format_snowflake_row')
    async def test_get_status_changes_success(self, mock_format, mock_query):
        """Test successful status change retrieval"""
        mock_query.return_value = [
            ["ITBEAKER-549", "2025-02-20 15:22:08.961 Z", "New", "In Progress", "New → In Progress"],
            ["ITBEAKER-549", "2025-03-05 13:51:54.818 Z", "In Progress", "Closed", "In Progress → Closed"]
        ]

        mock_format.side_effect = [
            {
                "ISSUE_KEY": "ITBEAKER-549",
                "CHANGE_TIMESTAMP": "2025-02-20 15:22:08.961 Z",
                "FROM_STATUS": "New",
                "TO_STATUS": "In Progress",
                "STATUS_TRANSITION": "New → In Progress"
            },
            {
                "ISSUE_KEY": "ITBEAKER-549",
                "CHANGE_TIMESTAMP": "2025-03-05 13:51:54.818 Z",
                "FROM_STATUS": "In Progress",
                "TO_STATUS": "Closed",
                "STATUS_TRANSITION": "In Progress → Closed"
            }
        ]

        result = await get_issue_status_changes(["123"], "token")

        assert "ITBEAKER-549" in result
        assert len(result["ITBEAKER-549"]) == 2

        # Check first status change
        first_change = result["ITBEAKER-549"][0]
        assert first_change["issue_key"] == "ITBEAKER-549"
        assert first_change["from_status"] == "New"
        assert first_change["to_status"] == "In Progress"
        assert first_change["status_transition"] == "New → In Progress"

        # Check second status change
        second_change = result["ITBEAKER-549"][1]
        assert second_change["from_status"] == "In Progress"
        assert second_change["to_status"] == "Closed"

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.database.clear_cache')
    async def test_get_status_changes_connector_method(self, mock_clear_cache, mock_query):
        """Test status change retrieval with connector method"""
        mock_clear_cache()  # Clear cache before test
        with patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTION_METHOD', 'connector'):
            mock_query.return_value = [
                {
                    "ISSUE_KEY": "ITBEAKER-549",
                    "CHANGE_TIMESTAMP": "2025-02-20 15:22:08.961 Z",
                    "FROM_STATUS": "New",
                    "TO_STATUS": "In Progress",
                    "STATUS_TRANSITION": "New → In Progress"
                }
            ]

            result = await get_issue_status_changes(["123"], None, use_cache=False)

            assert "ITBEAKER-549" in result
            assert len(result["ITBEAKER-549"]) == 1
            change = result["ITBEAKER-549"][0]
            assert change["from_status"] == "New"
            assert change["to_status"] == "In Progress"

    @pytest.mark.asyncio
    async def test_get_status_changes_empty_input(self):
        """Test with empty issue IDs list"""
        result = await get_issue_status_changes([], "token")
        assert result == {}

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    async def test_get_status_changes_invalid_ids(self, mock_query):
        """Test with invalid issue IDs"""
        result = await get_issue_status_changes(["invalid", "abc"], "token")
        assert result == {}
        # Should not call query with invalid IDs
        mock_query.assert_not_called()

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.database.clear_cache')
    async def test_get_status_changes_exception(self, mock_clear_cache, mock_query):
        """Test exception handling"""
        mock_clear_cache()  # Clear cache before test
        mock_query.side_effect = Exception("Database error")

        result = await get_issue_status_changes(["123"], "token", use_cache=False)
        assert result == {}


class TestCacheFunctionality:
    """Test cases for caching functionality"""

    def test_get_cache_key(self):
        """Test cache key generation"""
        key = get_cache_key("test_op", param1="value1", param2="value2")
        assert key == "test_op:param1:value1:param2:value2"

    def test_get_cache_key_with_none_values(self):
        """Test cache key generation with None values"""
        key = get_cache_key("test_op", param1="value1", param2=None)
        assert key == "test_op:param1:value1"

    def test_get_cache_key_empty_params(self):
        """Test cache key generation with no parameters"""
        key = get_cache_key("test_op")
        assert key == "test_op"

    @patch('jira_mcp_snowflake.src.database.ENABLE_CACHING', True)
    def test_cache_operations_enabled(self):
        """Test cache operations when caching is enabled"""
        clear_cache()  # Start fresh

        # Test cache miss
        result = get_from_cache("test_key")
        assert result is None

        # Test cache set and hit
        test_data = {"test": "data"}
        set_in_cache("test_key", test_data)
        result = get_from_cache("test_key")
        assert result == test_data

    @patch('jira_mcp_snowflake.src.database.ENABLE_CACHING', False)
    def test_cache_operations_disabled(self):
        """Test cache operations when caching is disabled"""
        # Should not cache when disabled
        set_in_cache("test_key", {"test": "data"})
        result = get_from_cache("test_key")
        assert result is None

    def test_clear_cache(self):
        """Test cache clearing"""
        set_in_cache("test_key", {"test": "data"})
        clear_cache()
        result = get_from_cache("test_key")
        assert result is None


class TestConnectionPool:
    """Test cases for connection pool functionality"""

    def test_get_connection_pool(self):
        """Test connection pool creation"""
        pool = get_connection_pool()
        assert pool is not None
        assert hasattr(pool, 'max_connections')
        assert hasattr(pool, 'timeout')

    def test_connection_pool_singleton(self):
        """Test that connection pool is a singleton"""
        pool1 = get_connection_pool()
        pool2 = get_connection_pool()
        assert pool1 is pool2

    @pytest.mark.asyncio
    async def test_connection_pool_client(self):
        """Test connection pool client creation"""
        pool = get_connection_pool()
        client = await pool.get_client()
        assert client is not None
        assert hasattr(client, 'request')

    @pytest.mark.asyncio
    async def test_cleanup_resources(self):
        """Test resource cleanup"""
        # Should not raise any exceptions
        await cleanup_resources()


class TestMakeSnowflakeRequestWithCaching:
    """Test cases for make_snowflake_request with caching"""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_TOKEN', 'test_token')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_BASE_URL', 'https://test.snowflake.com')
    @patch('jira_mcp_snowflake.src.database.get_connection_pool')
    @patch('jira_mcp_snowflake.src.database._throttler')
    async def test_request_with_caching_enabled(self, mock_throttler, mock_pool):
        """Test request with caching enabled"""
        # Setup mocks
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        mock_pool_instance = MagicMock()
        mock_pool_instance.get_client = AsyncMock(return_value=mock_client)
        mock_pool.return_value = mock_pool_instance

        mock_throttler.__aenter__ = AsyncMock()
        mock_throttler.__aexit__ = AsyncMock()

        clear_cache()  # Start fresh

        # First request should hit the API
        result1 = await make_snowflake_request("test", "GET", {"param": "value"}, use_cache=True)
        assert result1 == {"data": "test"}

        # Second identical request should hit cache (if caching is enabled)
        result2 = await make_snowflake_request("test", "GET", {"param": "value"}, use_cache=True)
        assert result2 == {"data": "test"}

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_TOKEN', 'test_token')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_BASE_URL', 'https://test.snowflake.com')
    @patch('jira_mcp_snowflake.src.database.get_connection_pool')
    @patch('jira_mcp_snowflake.src.database._throttler')
    async def test_request_with_caching_disabled(self, mock_throttler, mock_pool):
        """Test request with caching disabled"""
        # Setup mocks
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        mock_pool_instance = MagicMock()
        mock_pool_instance.get_client = AsyncMock(return_value=mock_client)
        mock_pool.return_value = mock_pool_instance

        mock_throttler.__aenter__ = AsyncMock()
        mock_throttler.__aexit__ = AsyncMock()

        result = await make_snowflake_request("test", "POST", {"param": "value"}, use_cache=False)
        assert result == {"data": "test"}
        mock_client.request.assert_called_once()


class TestExecuteSnowflakeQueryWithCaching:
    """Test cases for execute_snowflake_query with caching"""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.make_snowflake_request')
    @patch('jira_mcp_snowflake.src.database.track_snowflake_query')
    async def test_query_with_cache_hit(self, mock_track, mock_request):
        """Test query execution with cache hit"""
        mock_request.return_value = {"data": [["row1", "row2"]]}

        clear_cache()  # Start fresh

        # First query should hit the API
        result1 = await execute_snowflake_query("SELECT * FROM test", "token", use_cache=True)
        assert result1 == [["row1", "row2"]]

        # Second identical query should hit cache (if caching is enabled)
        result2 = await execute_snowflake_query("SELECT * FROM test", "token", use_cache=True)
        assert result2 == [["row1", "row2"]]

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.make_snowflake_request')
    @patch('jira_mcp_snowflake.src.database.track_snowflake_query')
    async def test_query_without_caching(self, mock_track, mock_request):
        """Test query execution without caching"""
        mock_request.return_value = {"data": [["row1", "row2"]]}

        result = await execute_snowflake_query("INSERT INTO test VALUES (1)", "token", use_cache=False)
        assert result == [["row1", "row2"]]
        mock_request.assert_called_once()


class TestConcurrentFunctions:
    """Test cases for concurrent processing functions"""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.get_issue_labels')
    @patch('jira_mcp_snowflake.src.database.get_issue_comments')
    @patch('jira_mcp_snowflake.src.database.get_issue_links')
    @patch('jira_mcp_snowflake.src.database.get_issue_status_changes')
    async def test_get_issue_enrichment_data_concurrent_success(self, mock_status_changes, mock_links, mock_comments, mock_labels):
        """Test successful concurrent data enrichment"""
        # Setup mocks
        mock_labels.return_value = {"123": ["bug", "urgent"]}
        mock_comments.return_value = {"123": [{"id": "c1", "body": "comment"}]}
        mock_links.return_value = {"123": [{"id": "l1", "type": "blocks"}]}
        mock_status_changes.return_value = {"TEST-123": [{"from_status": "New", "to_status": "In Progress"}]}

        labels, comments, links, status_changes = await get_issue_enrichment_data_concurrent(["123"], "token")

        assert labels == {"123": ["bug", "urgent"]}
        assert comments == {"123": [{"id": "c1", "body": "comment"}]}
        assert links == {"123": [{"id": "l1", "type": "blocks"}]}
        assert status_changes == {"TEST-123": [{"from_status": "New", "to_status": "In Progress"}]}

        # Verify all functions were called concurrently
        mock_labels.assert_called_once_with(["123"], "token", True)
        mock_comments.assert_called_once_with(["123"], "token", True)
        mock_links.assert_called_once_with(["123"], "token", True)
        mock_status_changes.assert_called_once_with(["123"], "token", True)

    @pytest.mark.asyncio
    async def test_get_issue_enrichment_data_concurrent_empty_input(self):
        """Test concurrent data enrichment with empty input"""
        labels, comments, links, status_changes = await get_issue_enrichment_data_concurrent([], "token")

        assert labels == {}
        assert comments == {}
        assert links == {}
        assert status_changes == {}

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.get_issue_labels')
    @patch('jira_mcp_snowflake.src.database.get_issue_comments')
    @patch('jira_mcp_snowflake.src.database.get_issue_links')
    @patch('jira_mcp_snowflake.src.database.get_issue_status_changes')
    async def test_get_issue_enrichment_data_concurrent_with_exception(self, mock_status_changes, mock_links, mock_comments, mock_labels):
        """Test concurrent data enrichment with one function failing"""
        # Setup mocks - one fails, others succeed
        mock_labels.side_effect = Exception("Labels error")
        mock_comments.return_value = {"123": [{"id": "c1", "body": "comment"}]}
        mock_links.return_value = {"123": [{"id": "l1", "type": "blocks"}]}
        mock_status_changes.return_value = {"TEST-123": [{"from_status": "New", "to_status": "In Progress"}]}

        labels, comments, links, status_changes = await get_issue_enrichment_data_concurrent(["123"], "token")

        # Failed operation should return empty dict
        assert labels == {}
        assert comments == {"123": [{"id": "c1", "body": "comment"}]}
        assert links == {"123": [{"id": "l1", "type": "blocks"}]}
        assert status_changes == {"TEST-123": [{"from_status": "New", "to_status": "In Progress"}]}

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    async def test_execute_queries_in_batches_success(self, mock_query):
        """Test successful batch query execution"""
        # Mock query returns
        mock_query.side_effect = [
            [["row1", "col1"]],
            [["row2", "col2"]],
            [["row3", "col3"]]
        ]

        queries = ["SELECT 1", "SELECT 2", "SELECT 3"]
        results = await execute_queries_in_batches(queries, "token", batch_size=2)

        assert len(results) == 3
        assert results[0] == [["row1", "col1"]]
        assert results[1] == [["row2", "col2"]]
        assert results[2] == [["row3", "col3"]]

        # Should be called 3 times (once per query)
        assert mock_query.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_queries_in_batches_empty_input(self):
        """Test batch query execution with empty input"""
        results = await execute_queries_in_batches([], "token")
        assert results == []

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    async def test_execute_queries_in_batches_with_exception(self, mock_query):
        """Test batch query execution with one query failing"""
        # First query succeeds, second fails
        mock_query.side_effect = [
            [["row1", "col1"]],
            Exception("Query error")
        ]

        queries = ["SELECT 1", "SELECT 2"]
        results = await execute_queries_in_batches(queries, "token", batch_size=1)

        assert len(results) == 2
        assert results[0] == [["row1", "col1"]]
        assert results[1] == []  # Failed query returns empty list

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database._thread_pool')
    async def test_format_snowflake_rows_concurrent_small_dataset(self, mock_thread_pool):
        """Test concurrent row formatting with small dataset"""
        import asyncio

        rows = [["val1", "val2"], ["val3", "val4"]]
        columns = ["col1", "col2"]

        # Mock the thread pool execution
        expected_result = [{"col1": "val1", "col2": "val2"}, {"col1": "val3", "col2": "val4"}]

        loop = asyncio.get_event_loop()
        future = asyncio.Future()
        future.set_result(expected_result)
        loop.run_in_executor = AsyncMock(return_value=expected_result)

        with patch('jira_mcp_snowflake.src.database.asyncio.get_event_loop', return_value=loop):
            result = await format_snowflake_rows_concurrent(rows, columns, batch_size=100)

        assert result == expected_result

    @pytest.mark.asyncio
    async def test_format_snowflake_rows_concurrent_empty_input(self):
        """Test concurrent row formatting with empty input"""
        result = await format_snowflake_rows_concurrent([], ["col1", "col2"])
        assert result == []


class TestSnowflakeConnectorPool:
    """Test cases for SnowflakeConnectorPool class"""

    def test_init(self):
        """Test SnowflakeConnectorPool initialization"""
        pool = SnowflakeConnectorPool()
        assert pool._connection is None
        assert pool._lock is not None

    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTOR_AVAILABLE', False)
    def test_build_connection_params_no_connector(self):
        """Test connection params building when connector is not available"""
        pool = SnowflakeConnectorPool()
        with pytest.raises(ImportError, match="snowflake-connector-python is not installed"):
            pool._build_connection_params()

    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTOR_AVAILABLE', True)
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_ACCOUNT', None)
    def test_build_connection_params_no_account(self):
        """Test connection params building without account"""
        pool = SnowflakeConnectorPool()
        with pytest.raises(ValueError, match="SNOWFLAKE_ACCOUNT is required"):
            pool._build_connection_params()

    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTOR_AVAILABLE', True)
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_ACCOUNT', 'test-account')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_DATABASE', 'test-db')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_SCHEMA', 'test-schema')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_WAREHOUSE', 'test-warehouse')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_AUTHENTICATOR', 'snowflake')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_USER', 'test-user')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_PASSWORD', 'test-password')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_ROLE', 'test-role')
    def test_build_connection_params_default_auth(self):
        """Test connection params building with default authentication"""
        pool = SnowflakeConnectorPool()
        params = pool._build_connection_params()

        assert params['account'] == 'test-account'
        assert params['database'] == 'test-db'
        assert params['schema'] == 'test-schema'
        assert params['warehouse'] == 'test-warehouse'
        assert params['user'] == 'test-user'
        assert params['password'] == 'test-password'
        assert params['role'] == 'test-role'

    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTOR_AVAILABLE', True)
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_ACCOUNT', 'test-account')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_DATABASE', 'test-db')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_SCHEMA', 'test-schema')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_WAREHOUSE', 'test-warehouse')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_AUTHENTICATOR', 'snowflake_jwt')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_USER', 'test-user')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_PRIVATE_KEY_FILE', '/path/to/key.p8')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_PRIVATE_KEY_FILE_PWD', 'key-password')
    def test_build_connection_params_jwt_auth(self):
        """Test connection params building with JWT authentication"""
        pool = SnowflakeConnectorPool()
        params = pool._build_connection_params()

        assert params['authenticator'] == 'SNOWFLAKE_JWT'
        assert params['user'] == 'test-user'
        assert params['private_key_file'] == '/path/to/key.p8'
        assert params['private_key_file_pwd'] == 'key-password'

    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTOR_AVAILABLE', True)
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_ACCOUNT', 'test-account')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_DATABASE', 'test-db')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_SCHEMA', 'test-schema')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_WAREHOUSE', 'test-warehouse')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_AUTHENTICATOR', 'snowflake_jwt')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_USER', 'test-user')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_PRIVATE_KEY_FILE', None)
    def test_build_connection_params_jwt_auth_no_key_file(self):
        """Test connection params building with JWT authentication but no key file"""
        pool = SnowflakeConnectorPool()
        with pytest.raises(ValueError, match="SNOWFLAKE_PRIVATE_KEY_FILE is required for JWT authentication"):
            pool._build_connection_params()

    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTOR_AVAILABLE', True)
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_ACCOUNT', 'test-account')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_DATABASE', 'test-db')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_SCHEMA', 'test-schema')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_WAREHOUSE', 'test-warehouse')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_AUTHENTICATOR', 'oauth_client_credentials')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_OAUTH_CLIENT_ID', None)
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_OAUTH_CLIENT_SECRET', None)
    def test_build_connection_params_oauth_client_credentials_missing_creds(self):
        """Test connection params building with OAuth client credentials but missing credentials"""
        pool = SnowflakeConnectorPool()
        with pytest.raises(ValueError, match="SNOWFLAKE_OAUTH_CLIENT_ID and SNOWFLAKE_OAUTH_CLIENT_SECRET are required"):
            pool._build_connection_params()

    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTOR_AVAILABLE', True)
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_ACCOUNT', 'test-account')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_DATABASE', 'test-db')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_SCHEMA', 'test-schema')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_WAREHOUSE', 'test-warehouse')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_AUTHENTICATOR', 'oauth')
    @patch('config.SNOWFLAKE_TOKEN', None)
    def test_build_connection_params_oauth_token_missing_token(self):
        """Test connection params building with OAuth token but missing token"""
        pool = SnowflakeConnectorPool()
        with pytest.raises(ValueError, match="SNOWFLAKE_TOKEN is required for OAuth token authentication"):
            pool._build_connection_params()

    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTOR_AVAILABLE', True)
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_ACCOUNT', 'test-account')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_DATABASE', 'test-db')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_SCHEMA', 'test-schema')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_WAREHOUSE', 'test-warehouse')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_AUTHENTICATOR', 'snowflake')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_USER', None)
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_PASSWORD', None)
    def test_build_connection_params_default_auth_missing_creds(self):
        """Test connection params building with default auth but missing credentials"""
        pool = SnowflakeConnectorPool()
        with pytest.raises(ValueError, match="SNOWFLAKE_USER and SNOWFLAKE_PASSWORD are required"):
            pool._build_connection_params()

    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTOR_AVAILABLE', True)
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_ACCOUNT', 'test-account')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_DATABASE', 'test-db')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_SCHEMA', 'test-schema')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_WAREHOUSE', 'test-warehouse')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_AUTHENTICATOR', 'oauth_client_credentials')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_OAUTH_CLIENT_ID', 'client-id')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_OAUTH_CLIENT_SECRET', 'client-secret')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_OAUTH_TOKEN_URL', 'https://token.url')
    def test_build_connection_params_oauth_client_credentials(self):
        """Test connection params building with OAuth client credentials"""
        pool = SnowflakeConnectorPool()
        params = pool._build_connection_params()

        assert params['authenticator'] == 'OAUTH_CLIENT_CREDENTIALS'
        assert params['oauth_client_id'] == 'client-id'
        assert params['oauth_client_secret'] == 'client-secret'
        assert params['oauth_token_request_url'] == 'https://token.url'

    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTOR_AVAILABLE', True)
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_ACCOUNT', 'test-account')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_DATABASE', 'test-db')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_SCHEMA', 'test-schema')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_WAREHOUSE', 'test-warehouse')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_AUTHENTICATOR', 'oauth')
    @patch('config.SNOWFLAKE_TOKEN', 'oauth-token')
    def test_build_connection_params_oauth_token(self):
        """Test connection params building with OAuth token"""
        pool = SnowflakeConnectorPool()
        params = pool._build_connection_params()

        assert params['authenticator'] == 'OAUTH'
        assert params['token'] == 'oauth-token'

    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTOR_AVAILABLE', True)
    @patch('jira_mcp_snowflake.src.database.snowflake.connector.connect')
    def test_get_connection_new(self, mock_connect):
        """Test getting a new connection"""
        mock_connection = MagicMock()
        mock_connection.is_closed.return_value = True
        mock_connect.return_value = mock_connection

        with patch.object(SnowflakeConnectorPool, '_build_connection_params') as mock_build:
            mock_build.return_value = {'account': 'test'}

            pool = SnowflakeConnectorPool()
            conn = pool.get_connection()

            assert conn == mock_connection
            mock_connect.assert_called_once_with(account='test')

    def test_get_connection_reuse_existing(self):
        """Test reusing existing connection"""
        mock_connection = MagicMock()
        mock_connection.is_closed.return_value = False

        pool = SnowflakeConnectorPool()
        pool._connection = mock_connection

        conn = pool.get_connection()
        assert conn == mock_connection

    def test_close_connection(self):
        """Test closing connection"""
        mock_connection = MagicMock()
        mock_connection.is_closed.return_value = False

        pool = SnowflakeConnectorPool()
        pool._connection = mock_connection

        pool.close()
        mock_connection.close.assert_called_once()
        assert pool._connection is None

    def test_close_no_connection(self):
        """Test closing when no connection exists"""
        pool = SnowflakeConnectorPool()
        pool.close()  # Should not raise exception


class TestConnectorPool:
    """Test cases for get_connector_pool function"""

    def test_get_connector_pool_singleton(self):
        """Test that get_connector_pool returns singleton instance"""
        pool1 = get_connector_pool()
        pool2 = get_connector_pool()
        assert pool1 is pool2
        assert isinstance(pool1, SnowflakeConnectorPool)


class TestConnectorQueries:
    """Test cases for connector-based query execution"""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTION_METHOD', 'connector')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTOR_AVAILABLE', True)
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query_connector')
    async def test_execute_snowflake_query_connector_method(self, mock_connector_query):
        """Test query routing to connector method"""
        mock_connector_query.return_value = [{"id": 1, "name": "test"}]

        result = await execute_snowflake_query("SELECT * FROM test", use_cache=False)

        mock_connector_query.assert_called_once_with("SELECT * FROM test", False)
        assert result == [{"id": 1, "name": "test"}]

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTION_METHOD', 'connector')
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTOR_AVAILABLE', False)
    async def test_execute_snowflake_query_connector_unavailable(self):
        """Test query when connector method requested but unavailable"""
        result = await execute_snowflake_query("SELECT * FROM test")
        assert result == []

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTION_METHOD', 'api')
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query_api')
    async def test_execute_snowflake_query_api_method(self, mock_api_query):
        """Test query routing to API method"""
        mock_api_query.return_value = [{"id": 1, "name": "test"}]

        result = await execute_snowflake_query("SELECT * FROM test", "token")

        mock_api_query.assert_called_once_with("SELECT * FROM test", "token", True)
        assert result == [{"id": 1, "name": "test"}]

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database._thread_pool')
    @patch('jira_mcp_snowflake.src.database.get_cache_key')
    @patch('jira_mcp_snowflake.src.database.get_from_cache')
    @patch('jira_mcp_snowflake.src.database.set_in_cache')
    async def test_execute_snowflake_query_connector_with_cache(self, mock_set_cache, mock_get_cache, mock_cache_key, mock_thread_pool):
        """Test connector query with caching"""
        mock_cache_key.return_value = "cache_key"
        mock_get_cache.return_value = [{"cached": "result"}]

        result = await execute_snowflake_query_connector("SELECT * FROM test", True)

        assert result == [{"cached": "result"}]
        mock_get_cache.assert_called_once_with("cache_key")

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database._thread_pool')
    @patch('jira_mcp_snowflake.src.database._execute_connector_query_sync')
    async def test_execute_snowflake_query_connector_execution(self, mock_sync_query, mock_thread_pool):
        """Test connector query execution"""
        import asyncio

        mock_sync_query.return_value = [{"id": 1, "name": "test"}]

        # Mock the thread pool execution
        loop = asyncio.get_event_loop()
        future = asyncio.Future()
        future.set_result([{"id": 1, "name": "test"}])
        loop.run_in_executor = AsyncMock(return_value=[{"id": 1, "name": "test"}])

        with patch('jira_mcp_snowflake.src.database.asyncio.get_event_loop', return_value=loop):
            result = await execute_snowflake_query_connector("SELECT * FROM test", False)

        assert result == [{"id": 1, "name": "test"}]

    @patch('jira_mcp_snowflake.src.database.get_connector_pool')
    def test_execute_connector_query_sync(self, mock_get_pool):
        """Test synchronous connector query execution"""
        # Mock connection and cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("value1", "2023-01-01T10:00:00")]
        mock_cursor.description = [("col1",), ("CREATED",)]

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.get_connection.return_value = mock_connection
        mock_get_pool.return_value = mock_pool

        result = _execute_connector_query_sync("SELECT * FROM test")

        assert len(result) == 1
        assert result[0]["col1"] == "value1"
        assert result[0]["CREATED"] == "2023-01-01T10:00:00"
        mock_cursor.close.assert_called_once()

    @patch('jira_mcp_snowflake.src.database.get_connector_pool')
    def test_execute_connector_query_sync_snowflake_error(self, mock_get_pool):
        """Test synchronous connector query with Snowflake error"""
        from database import SnowflakeError

        mock_pool = MagicMock()
        mock_pool.get_connection.side_effect = SnowflakeError("Connection failed")
        mock_get_pool.return_value = mock_pool

        with pytest.raises(SnowflakeError):
            _execute_connector_query_sync("SELECT * FROM test")

    @patch('jira_mcp_snowflake.src.database.get_connector_pool')
    def test_execute_connector_query_sync_general_error(self, mock_get_pool):
        """Test synchronous connector query with general error"""
        mock_pool = MagicMock()
        mock_pool.get_connection.side_effect = Exception("General error")
        mock_get_pool.return_value = mock_pool

        with pytest.raises(Exception):
            _execute_connector_query_sync("SELECT * FROM test")

    @patch('jira_mcp_snowflake.src.database.get_connector_pool')
    def test_execute_connector_query_sync_timestamp_handling(self, mock_get_pool):
        """Test timestamp handling in synchronous connector query"""
        from datetime import datetime

        # Mock connection and cursor with datetime object
        mock_cursor = MagicMock()
        timestamp_obj = datetime(2023, 1, 1, 10, 0, 0)
        mock_cursor.fetchall.return_value = [("value1", timestamp_obj)]
        mock_cursor.description = [("col1",), ("CREATED",)]

        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.get_connection.return_value = mock_connection
        mock_get_pool.return_value = mock_pool

        result = _execute_connector_query_sync("SELECT * FROM test")

        assert len(result) == 1
        assert result[0]["col1"] == "value1"
        assert result[0]["CREATED"] == "2023-01-01T10:00:00"

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database._thread_pool')
    @patch('jira_mcp_snowflake.src.database._execute_connector_query_sync')
    async def test_execute_snowflake_query_connector_exception(self, mock_sync_query, mock_thread_pool):
        """Test connector query execution with exception"""
        import asyncio

        mock_sync_query.side_effect = Exception("Query failed")

        # Mock the thread pool execution
        loop = asyncio.get_event_loop()
        loop.run_in_executor = AsyncMock(side_effect=Exception("Query failed"))

        with patch('jira_mcp_snowflake.src.database.asyncio.get_event_loop', return_value=loop):
            result = await execute_snowflake_query_connector("SELECT * FROM test", False)

        assert result == []


class TestProcessLinksRows:
    """Test cases for _process_links_rows helper function"""

    def test_process_links_rows_basic(self):
        """Test basic links processing"""
        rows = [
            {
                "LINK_ID": "1",
                "SOURCE": "100",
                "DESTINATION": "200",
                "SEQUENCE": 1,
                "LINKNAME": "blocks",
                "INWARD": "is blocked by",
                "OUTWARD": "blocks",
                "SOURCE_KEY": "PROJ-100",
                "DESTINATION_KEY": "PROJ-200",
                "SOURCE_SUMMARY": "Source issue",
                "DESTINATION_SUMMARY": "Dest issue"
            }
        ]

        sanitized_ids = ["100", "200"]
        links_data = {}

        _process_links_rows(rows, sanitized_ids, links_data)

        # Should have entries for both source and destination
        assert "100" in links_data
        assert "200" in links_data

        # Check source perspective (outward)
        source_link = links_data["100"][0]
        assert source_link["relationship"] == "outward"
        assert source_link["related_issue_id"] == "200"
        assert source_link["relationship_description"] == "blocks"

        # Check destination perspective (inward)
        dest_link = links_data["200"][0]
        assert dest_link["relationship"] == "inward"
        assert dest_link["related_issue_id"] == "100"
        assert dest_link["relationship_description"] == "is blocked by"

    def test_process_links_rows_filtered_ids(self):
        """Test links processing with filtered IDs"""
        rows = [
            {
                "LINK_ID": "1",
                "SOURCE": "100",
                "DESTINATION": "200",
                "SEQUENCE": 1,
                "LINKNAME": "blocks",
                "INWARD": "is blocked by",
                "OUTWARD": "blocks",
                "SOURCE_KEY": "PROJ-100",
                "DESTINATION_KEY": "PROJ-200",
                "SOURCE_SUMMARY": "Source issue",
                "DESTINATION_SUMMARY": "Dest issue"
            }
        ]

        # Only include source ID in sanitized_ids
        sanitized_ids = ["100"]
        links_data = {}

        _process_links_rows(rows, sanitized_ids, links_data)

        # Should only have entry for source
        assert "100" in links_data
        assert "200" not in links_data
        assert len(links_data["100"]) == 1

    def test_process_links_rows_empty(self):
        """Test links processing with empty input"""
        rows = []
        sanitized_ids = ["100"]
        links_data = {}

        _process_links_rows(rows, sanitized_ids, links_data)

        assert len(links_data) == 0


class TestConnectorMethodIntegration:
    """Integration tests for connector method in existing functions"""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTION_METHOD', 'connector')
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    async def test_get_issue_labels_connector_method(self, mock_query):
        """Test get_issue_labels with connector method"""
        # Mock connector returning dictionaries directly
        mock_query.return_value = [
            {"ISSUE": "123", "LABEL": "bug"},
            {"ISSUE": "123", "LABEL": "urgent"}
        ]

        result = await get_issue_labels(["123"], use_cache=False)

        assert "123" in result
        assert result["123"] == ["bug", "urgent"]
        mock_query.assert_called_once()

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTION_METHOD', 'connector')
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    async def test_get_issue_comments_connector_method(self, mock_query):
        """Test get_issue_comments with connector method"""
        mock_query.return_value = [
            {
                "ID": "1",
                "ISSUEID": "123",
                "ROLELEVEL": "user",
                "BODY": "Test comment",
                "CREATED": "2023-01-01T10:00:00",
                "UPDATED": "2023-01-01T10:00:00"
            }
        ]

        result = await get_issue_comments(["123"], use_cache=False)

        assert "123" in result
        assert len(result["123"]) == 1
        assert result["123"][0]["body"] == "Test comment"

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.SNOWFLAKE_CONNECTION_METHOD', 'connector')
    @patch('jira_mcp_snowflake.src.database.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.database._process_links_rows')
    async def test_get_issue_links_connector_method(self, mock_process, mock_query):
        """Test get_issue_links with connector method"""
        mock_query.return_value = [{"LINK_ID": "1", "SOURCE": "100"}]

        await get_issue_links(["100"], use_cache=False)

        mock_query.assert_called_once()
        mock_process.assert_called_once()

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.database.cleanup_resources')
    @patch('jira_mcp_snowflake.src.database._connector_pool')
    async def test_cleanup_resources_with_connector(self, mock_connector_pool, mock_orig_cleanup):
        """Test cleanup_resources includes connector pool cleanup"""
        mock_pool = MagicMock()

        # Import and patch the module-level variable
        import database
        database._connector_pool = mock_pool

        await cleanup_resources()

        mock_pool.close.assert_called_once()
