"""Tests for JIRA MCP tools functionality."""

from unittest.mock import patch

import pytest

from jira_mcp_snowflake.src.tools.jira_tools import (
    get_jira_issue_details,
    get_jira_issue_links,
    get_jira_project_summary,
    get_snowflake_token,
    list_jira_issues,
)


class TestGetSnowflakeToken:
    """Test cases for get_snowflake_token function."""

    @patch('jira_mcp_snowflake.src.tools.jira_tools.settings')
    def test_get_token_stdio_transport(self, mock_settings):
        """Test token retrieval for stdio transport."""
        mock_settings.MCP_TRANSPORT = 'stdio'
        mock_settings.SNOWFLAKE_TOKEN = 'test_token'
        mock_settings.INTERNAL_GATEWAY = False

        token = get_snowflake_token()
        assert token == 'test_token'

    @patch('jira_mcp_snowflake.src.tools.jira_tools.settings')
    def test_get_token_internal_gateway(self, mock_settings):
        """Test token retrieval when internal gateway is enabled."""
        mock_settings.MCP_TRANSPORT = 'http'
        mock_settings.SNOWFLAKE_TOKEN = 'test_token'
        mock_settings.INTERNAL_GATEWAY = True

        token = get_snowflake_token()
        assert token == 'test_token'

    @patch('jira_mcp_snowflake.src.tools.jira_tools.settings')
    def test_get_token_non_stdio_transport(self, mock_settings):
        """Test token retrieval for non-stdio transport without internal gateway."""
        mock_settings.MCP_TRANSPORT = 'http'
        mock_settings.SNOWFLAKE_TOKEN = 'test_token'
        mock_settings.INTERNAL_GATEWAY = False

        token = get_snowflake_token()
        assert token == 'test_token'  # Should still return token in current implementation


class TestListJiraIssues:
    """Test cases for list_jira_issues function."""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_snowflake_token')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_issue_enrichment_data_concurrent')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.settings')
    async def test_list_issues_no_token(self, mock_settings, mock_enrichment, mock_query, mock_token):
        """Test list_jira_issues when no token is available."""
        mock_settings.SNOWFLAKE_CONNECTION_METHOD = 'api'
        mock_token.return_value = None

        result = await list_jira_issues()

        assert 'error' in result
        assert result['error'] == "Snowflake token not available"
        assert result['issues'] == []

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_snowflake_token')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_issue_enrichment_data_concurrent')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.settings')
    async def test_list_issues_success(self, mock_settings, mock_enrichment, mock_query, mock_token):
        """Test successful list_jira_issues execution."""
        mock_settings.SNOWFLAKE_CONNECTION_METHOD = 'api'
        mock_token.return_value = 'test_token'

        # Mock query result
        mock_query.return_value = [
            [
                '123', 'TEST-1', 'TEST', '1', 'Bug', 'Test Summary', 'Short desc',
                'Full description', 'High', 'Open', None, '2024-01-01', '2024-01-02',
                None, None, '0', '1', None, None, None, 'Test Component||Backend',
                'Fix Version 1.0', 'Affected Version 1.0'
            ]
        ]

        # Mock enrichment data
        mock_enrichment.return_value = (
            {'123': ['bug', 'urgent']},  # labels
            {'123': [{'id': 'c1', 'body': 'Comment'}]},  # comments
            {'123': [{'link_id': '456', 'type': 'blocks'}]},  # links
            {'TEST-1': [{'from_status': 'New', 'to_status': 'Open'}]}  # status_changes
        )

        result = await list_jira_issues(project='TEST', limit=10)

        assert 'issues' in result
        assert 'total_returned' in result
        assert 'filters_applied' in result
        assert result['filters_applied']['project'] == 'TEST'
        assert result['filters_applied']['limit'] == 10
        assert len(result['issues']) == 1

        issue = result['issues'][0]
        assert issue['key'] == 'TEST-1'
        assert issue['project'] == 'TEST'
        assert issue['labels'] == ['bug', 'urgent']
        assert issue['links'] == [{'link_id': '456', 'type': 'blocks'}]

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_snowflake_token')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_issue_enrichment_data_concurrent')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.settings')
    async def test_list_issues_with_filters(self, mock_settings, mock_enrichment, mock_query, mock_token):
        """Test list_jira_issues with various filters."""
        mock_settings.SNOWFLAKE_CONNECTION_METHOD = 'api'
        mock_token.return_value = 'test_token'
        mock_query.return_value = []
        mock_enrichment.return_value = ({}, {}, {}, {})

        result = await list_jira_issues(
            project='TEST',
            issue_type='Bug',
            status='Open',
            priority='High',
            search_text='test search',
            timeframe=14
        )

        # Verify SQL conditions were built correctly
        mock_query.assert_called_once()
        sql_call = mock_query.call_args[0][0]
        assert "i.PROJECT = 'TEST'" in sql_call
        assert "i.ISSUETYPE = 'Bug'" in sql_call
        assert "i.ISSUESTATUS = 'Open'" in sql_call
        assert "i.PRIORITY = 'High'" in sql_call
        assert "LOWER(i.SUMMARY) LIKE '%test search%'" in sql_call

        # Verify filters_applied includes all parameters
        assert result['filters_applied']['project'] == 'TEST'
        assert result['filters_applied']['issue_type'] == 'Bug'
        assert result['filters_applied']['status'] == 'Open'
        assert result['filters_applied']['priority'] == 'High'
        assert result['filters_applied']['search_text'] == 'test search'
        assert result['filters_applied']['timeframe'] == 14

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_snowflake_token')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_issue_enrichment_data_concurrent')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.settings')
    async def test_list_issues_exception_handling(self, mock_settings, mock_enrichment, mock_query, mock_token):
        """Test exception handling in list_jira_issues."""
        mock_settings.SNOWFLAKE_CONNECTION_METHOD = 'api'
        mock_token.side_effect = Exception("Database error")

        result = await list_jira_issues()

        assert 'error' in result
        assert 'Database error' in result['error']


class TestGetJiraIssueDetails:
    """Test cases for get_jira_issue_details function."""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_snowflake_token')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_issue_enrichment_data_concurrent')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.settings')
    async def test_get_issue_details_success(self, mock_settings, mock_enrichment, mock_query, mock_token):
        """Test successful get_jira_issue_details execution."""
        mock_settings.SNOWFLAKE_CONNECTION_METHOD = 'api'
        mock_token.return_value = 'test_token'

        # Mock query result
        mock_query.return_value = [
            [
                '123', 'TEST-1', 'TEST', '1', 'Bug', 'Test Summary', 'Full description',
                'High', 'Open', None, '2024-01-01', '2024-01-02', None, None, '0', '1',
                None, None, None, '3600', '1800', '900', 'WF-1', None, 'N', None,
                'Test Component', 'Component Description', 'N', 'N', 'Fix Version 1.0', 'Affected Version 1.0'
            ]
        ]

        # Mock enrichment data
        mock_enrichment.return_value = (
            {'123': ['bug']},  # labels
            {'123': [{'id': '789', 'body': 'Comment'}]},  # comments
            {'123': [{'link_id': '456'}]},  # links
            {'TEST-1': [{'from_status': 'New', 'to_status': 'Open'}]}  # status_changes
        )

        result = await get_jira_issue_details(['TEST-1'])

        assert 'found_issues' in result
        assert 'not_found' in result
        assert 'total_found' in result
        assert 'total_requested' in result

        assert 'TEST-1' in result['found_issues']
        assert result['found_issues']['TEST-1']['key'] == 'TEST-1'
        assert result['found_issues']['TEST-1']['summary'] == 'Test Summary'
        assert 'labels' in result['found_issues']['TEST-1']
        assert 'comments' in result['found_issues']['TEST-1']
        assert 'links' in result['found_issues']['TEST-1']
        assert result['not_found'] == []
        assert result['total_found'] == 1
        assert result['total_requested'] == 1

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_snowflake_token')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_issue_enrichment_data_concurrent')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.settings')
    async def test_get_issue_details_not_found(self, mock_settings, mock_enrichment, mock_query, mock_token):
        """Test get_jira_issue_details when issue is not found."""
        mock_settings.SNOWFLAKE_CONNECTION_METHOD = 'api'
        mock_token.return_value = 'test_token'
        mock_query.return_value = []
        mock_enrichment.return_value = ({}, {}, {}, {})

        result = await get_jira_issue_details(['TEST-999'])

        assert result['found_issues'] == {}
        assert result['not_found'] == ['TEST-999']
        assert result['total_found'] == 0
        assert result['total_requested'] == 1

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_snowflake_token')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.settings')
    async def test_get_issue_details_empty_list(self, mock_settings, mock_token):
        """Test get_jira_issue_details with empty list input."""
        mock_settings.SNOWFLAKE_CONNECTION_METHOD = 'api'
        mock_token.return_value = 'test_token'

        result = await get_jira_issue_details([])

        assert result['found_issues'] == {}
        assert result['not_found'] == []
        assert result['total_found'] == 0
        assert result['total_requested'] == 0


class TestGetJiraProjectSummary:
    """Test cases for get_jira_project_summary function."""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_snowflake_token')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.settings')
    async def test_get_project_summary_success(self, mock_settings, mock_query, mock_token):
        """Test successful get_jira_project_summary execution."""
        mock_settings.SNOWFLAKE_CONNECTION_METHOD = 'api'
        mock_token.return_value = 'test_token'

        # Mock query result
        mock_query.return_value = [
            ['TEST', 'Open', 'High', '5'],
            ['TEST', 'Open', 'Medium', '10'],
            ['PROD', 'Closed', 'Low', '3']
        ]

        result = await get_jira_project_summary()

        assert 'total_issues' in result
        assert 'total_projects' in result
        assert 'projects' in result
        assert result['total_issues'] == 18
        assert result['total_projects'] == 2
        assert 'TEST' in result['projects']
        assert 'PROD' in result['projects']
        assert result['projects']['TEST']['total_issues'] == 15


class TestGetJiraIssueLinks:
    """Test cases for get_jira_issue_links function."""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_snowflake_token')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_issue_links')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.settings')
    async def test_get_issue_links_success(self, mock_settings, mock_get_links, mock_query, mock_token):
        """Test successful get_jira_issue_links execution."""
        mock_settings.SNOWFLAKE_CONNECTION_METHOD = 'api'
        mock_token.return_value = 'test_token'

        # First query returns issue ID
        mock_query.return_value = [['123']]

        # Mock get_issue_links function
        mock_get_links.return_value = {'123': [{'link_id': '456', 'type': 'blocks'}]}

        result = await get_jira_issue_links('TEST-1')

        assert result['issue_key'] == 'TEST-1'
        assert result['issue_id'] == '123'
        assert 'links' in result
        assert result['total_links'] == 1

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_snowflake_token')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.settings')
    async def test_get_issue_links_not_found(self, mock_settings, mock_query, mock_token):
        """Test get_jira_issue_links when issue is not found."""
        mock_settings.SNOWFLAKE_CONNECTION_METHOD = 'api'
        mock_token.return_value = 'test_token'

        # Issue not found
        mock_query.return_value = []

        result = await get_jira_issue_links('TEST-999')

        assert 'error' in result
        assert "Issue with key 'TEST-999' not found" in result['error']


class TestFunctionIntegration:
    """Integration tests for function interaction."""

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_snowflake_token')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.execute_snowflake_query')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_issue_enrichment_data_concurrent')
    @patch('jira_mcp_snowflake.src.tools.jira_tools.settings')
    async def test_connector_vs_api_method(self, mock_settings, mock_enrichment, mock_query, mock_token):
        """Test that both connector and API methods work."""
        # Test API method
        mock_settings.SNOWFLAKE_CONNECTION_METHOD = 'api'
        mock_token.return_value = 'test_token'
        mock_query.return_value = []
        mock_enrichment.return_value = ({}, {}, {}, {})

        result_api = await list_jira_issues(project='TEST')
        assert 'issues' in result_api

        # Test connector method
        mock_settings.SNOWFLAKE_CONNECTION_METHOD = 'connector'
        mock_token.return_value = None  # Token not needed for connector

        result_connector = await list_jira_issues(project='TEST')
        assert 'issues' in result_connector

    @pytest.mark.asyncio
    @patch('jira_mcp_snowflake.src.tools.jira_tools.get_snowflake_token')
    async def test_error_handling(self, mock_token):
        """Test that all functions handle errors gracefully."""
        mock_token.side_effect = Exception("Connection error")

        # All functions should return error objects, not raise exceptions
        result1 = await list_jira_issues()
        assert 'error' in result1

        result2 = await get_jira_issue_details(['TEST-1'])
        assert 'error' in result2

        result3 = await get_jira_project_summary()
        assert 'error' in result3

        result4 = await get_jira_issue_links('TEST-1')
        assert 'error' in result4
