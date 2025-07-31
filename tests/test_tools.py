import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from tools import get_snowflake_token, register_tools


class TestGetSnowflakeToken:
    """Test cases for get_snowflake_token function"""
    
    @patch('tools.MCP_TRANSPORT', 'stdio')
    @patch('tools.SNOWFLAKE_TOKEN', 'test_token')
    def test_get_token_stdio_transport(self):
        """Test token retrieval for stdio transport"""
        mcp = MagicMock()
        token = get_snowflake_token(mcp)
        assert token == 'test_token'

    @patch('tools.MCP_TRANSPORT', 'stdio')
    @patch('tools.INTERNAL_GATEWAY', 'true')
    @patch('tools.SNOWFLAKE_TOKEN', 'test_token')
    def test_get_token_internal_gateway(self):
        """Test token retrieval when internal gateway is enabled"""
        mcp = MagicMock()
        token = get_snowflake_token(mcp)
        assert token == 'test_token'

    @patch('tools.MCP_TRANSPORT', 'http')
    @patch('tools.INTERNAL_GATEWAY', 'false')
    def test_get_token_from_headers_success(self):
        """Test successful token retrieval from request headers"""
        mcp = MagicMock()
        context = MagicMock()
        context.request_context.request.headers = {"X-Snowflake-Token": "header_token"}
        mcp.get_context.return_value = context
        
        token = get_snowflake_token(mcp)
        assert token == "header_token"

    @patch('tools.MCP_TRANSPORT', 'http')
    @patch('tools.INTERNAL_GATEWAY', 'false')
    def test_get_token_from_headers_empty(self):
        """Test token retrieval when header is empty"""
        mcp = MagicMock()
        context = MagicMock()
        context.request_context.request.headers = {"X-Snowflake-Token": ""}
        mcp.get_context.return_value = context
        
        token = get_snowflake_token(mcp)
        assert token is None

    @patch('tools.MCP_TRANSPORT', 'http')
    @patch('tools.INTERNAL_GATEWAY', 'false')
    def test_get_token_missing_header(self):
        """Test token retrieval when header is missing"""
        mcp = MagicMock()
        context = MagicMock()
        context.request_context.request.headers = {}
        mcp.get_context.return_value = context
        
        token = get_snowflake_token(mcp)
        assert token is None

    @patch('tools.MCP_TRANSPORT', 'http')
    @patch('tools.INTERNAL_GATEWAY', 'false')
    def test_get_token_no_context(self):
        """Test token retrieval when no context is available"""
        mcp = MagicMock()
        mcp.get_context.return_value = None
        
        token = get_snowflake_token(mcp)
        assert token is None

    @patch('tools.MCP_TRANSPORT', 'http')
    @patch('tools.INTERNAL_GATEWAY', 'false')
    def test_get_token_exception(self):
        """Test token retrieval when an exception occurs"""
        mcp = MagicMock()
        mcp.get_context.side_effect = Exception("Test error")
        
        token = get_snowflake_token(mcp)
        assert token is None


class TestRegisterTools:
    """Test cases for register_tools function and individual tool implementations"""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock MCP instance"""
        mcp = MagicMock()
        # Store registered functions for testing
        mcp._registered_tools = []
        
        def mock_tool_decorator():
            def decorator(func):
                mcp._registered_tools.append(func)
                return func
            return decorator
        
        mcp.tool = mock_tool_decorator
        return mcp

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies"""
        with patch('tools.get_snowflake_token') as mock_token, \
             patch('tools.execute_snowflake_query') as mock_query, \
             patch('tools.get_issue_labels') as mock_labels, \
             patch('tools.get_issue_comments') as mock_comments, \
             patch('tools.get_issue_links') as mock_links, \
             patch('tools.format_snowflake_row') as mock_format, \
             patch('tools.sanitize_sql_value') as mock_sanitize:
            
            mock_token.return_value = 'test_token'
            mock_query.return_value = []
            mock_labels.return_value = {}
            mock_comments.return_value = {}
            mock_links.return_value = {}
            mock_format.return_value = {}
            mock_sanitize.side_effect = lambda x: str(x).replace("'", "''")
            
            yield {
                'token': mock_token,
                'query': mock_query,
                'labels': mock_labels,
                'comments': mock_comments,
                'links': mock_links,
                'format': mock_format,
                'sanitize': mock_sanitize
            }

    def test_register_tools(self, mock_mcp):
        """Test that register_tools completes without error"""
        register_tools(mock_mcp)
        # Verify that 5 tools were registered
        assert len(mock_mcp._registered_tools) == 5

    @pytest.mark.asyncio
    async def test_list_jira_issues_no_token(self, mock_mcp, mock_dependencies):
        """Test list_jira_issues when no token is available"""
        mock_dependencies['token'].return_value = None
        
        register_tools(mock_mcp)
        
        # Get the registered function
        list_jira_issues = mock_mcp._registered_tools[0]
        
        result = await list_jira_issues()
        assert result['error'] == "Snowflake token not available"
        assert result['issues'] == []

    @pytest.mark.asyncio
    async def test_list_jira_issues_success(self, mock_mcp, mock_dependencies):
        """Test successful list_jira_issues execution"""
        # Mock successful query result
        mock_dependencies['query'].return_value = [
            ['123', 'TEST-1', 'TEST', '1', 'Bug', 'Test Summary', 'Short desc', 'Full description',
             'High', 'Open', None, '2024-01-01', '2024-01-02', None, None, '0', '1', None, None, None]
        ]
        
        mock_dependencies['format'].return_value = {
            'ID': '123', 'ISSUE_KEY': 'TEST-1', 'PROJECT': 'TEST', 'ISSUENUM': '1',
            'ISSUETYPE': 'Bug', 'SUMMARY': 'Test Summary', 'DESCRIPTION_TRUNCATED': 'Short desc',
            'DESCRIPTION': 'Full description', 'PRIORITY': 'High', 'ISSUESTATUS': 'Open',
            'RESOLUTION': None, 'CREATED': '2024-01-01', 'UPDATED': '2024-01-02',
            'DUEDATE': None, 'RESOLUTIONDATE': None, 'VOTES': '0', 'WATCHES': '1',
            'ENVIRONMENT': None, 'COMPONENT': None, 'FIXFOR': None
        }
        
        mock_dependencies['labels'].return_value = {'123': ['label1', 'label2']}
        mock_dependencies['links'].return_value = {'123': [{'link_id': '456'}]}
        
        register_tools(mock_mcp)
        list_jira_issues = mock_mcp._registered_tools[0]
        
        result = await list_jira_issues(project='TEST', limit=10)
        
        assert 'issues' in result
        assert 'total_returned' in result
        assert 'filters_applied' in result
        assert result['filters_applied']['project'] == 'TEST'
        assert result['filters_applied']['limit'] == 10

    @pytest.mark.asyncio
    async def test_list_jira_issues_with_filters(self, mock_mcp, mock_dependencies):
        """Test list_jira_issues with various filters"""
        mock_dependencies['query'].return_value = []
        
        register_tools(mock_mcp)
        list_jira_issues = mock_mcp._registered_tools[0]
        
        result = await list_jira_issues(
            project='TEST',
            issue_type='Bug',
            status='Open',
            priority='High',
            search_text='test search'
        )
        
        # Verify SQL conditions were built correctly
        mock_dependencies['query'].assert_called_once()
        sql_call = mock_dependencies['query'].call_args[0][0]
        assert "PROJECT = 'TEST'" in sql_call
        assert "ISSUETYPE = 'Bug'" in sql_call
        assert "ISSUESTATUS = 'Open'" in sql_call
        assert "PRIORITY = 'High'" in sql_call
        assert "LOWER(SUMMARY) LIKE '%test search%'" in sql_call

    @pytest.mark.asyncio
    async def test_get_jira_issue_details_not_found(self, mock_mcp, mock_dependencies):
        """Test get_jira_issue_details when issue is not found"""
        mock_dependencies['query'].return_value = []
        
        register_tools(mock_mcp)
        get_jira_issue_details = mock_mcp._registered_tools[1]
        
        result = await get_jira_issue_details('TEST-999')
        assert result['error'] == "Issue with key 'TEST-999' not found"

    @pytest.mark.asyncio
    async def test_get_jira_issue_details_success(self, mock_mcp, mock_dependencies):
        """Test successful get_jira_issue_details execution"""
        mock_dependencies['query'].return_value = [
            ['123', 'TEST-1', 'TEST', '1', 'Bug', 'Test Summary', 'Full description',
             'High', 'Open', None, '2024-01-01', '2024-01-02', None, None, '0', '1',
             None, None, None, '3600', '1800', '900', 'WF-1', None, 'N', None]
        ]
        
        mock_dependencies['format'].return_value = {
            'ID': '123', 'ISSUE_KEY': 'TEST-1', 'PROJECT': 'TEST', 'ISSUENUM': '1',
            'ISSUETYPE': 'Bug', 'SUMMARY': 'Test Summary', 'DESCRIPTION': 'Full description',
            'PRIORITY': 'High', 'ISSUESTATUS': 'Open', 'RESOLUTION': None,
            'CREATED': '2024-01-01', 'UPDATED': '2024-01-02', 'DUEDATE': None,
            'RESOLUTIONDATE': None, 'VOTES': '0', 'WATCHES': '1', 'ENVIRONMENT': None,
            'COMPONENT': None, 'FIXFOR': None, 'TIMEORIGINALESTIMATE': '3600',
            'TIMEESTIMATE': '1800', 'TIMESPENT': '900', 'WORKFLOW_ID': 'WF-1',
            'SECURITY': None, 'ARCHIVED': 'N', 'ARCHIVEDDATE': None
        }
        
        mock_dependencies['labels'].return_value = {'123': ['label1']}
        mock_dependencies['comments'].return_value = {'123': [{'id': '789', 'body': 'Comment'}]}
        mock_dependencies['links'].return_value = {'123': [{'link_id': '456'}]}
        
        register_tools(mock_mcp)
        get_jira_issue_details = mock_mcp._registered_tools[1]
        
        result = await get_jira_issue_details('TEST-1')
        
        assert result['key'] == 'TEST-1'
        assert result['summary'] == 'Test Summary'
        assert 'labels' in result
        assert 'comments' in result
        assert 'links' in result

    @pytest.mark.asyncio
    async def test_get_jira_project_summary_success(self, mock_mcp, mock_dependencies):
        """Test successful get_jira_project_summary execution"""
        mock_dependencies['query'].return_value = [
            ['TEST', 'Open', 'High', '5'],
            ['TEST', 'Open', 'Medium', '10'],
            ['PROD', 'Closed', 'Low', '3']
        ]
        
        def mock_format_side_effect(row, columns):
            return dict(zip(columns, row))
        
        mock_dependencies['format'].side_effect = mock_format_side_effect
        
        register_tools(mock_mcp)
        get_jira_project_summary = mock_mcp._registered_tools[2]
        
        result = await get_jira_project_summary()
        
        assert result['total_issues'] == 18
        assert result['total_projects'] == 2
        assert 'TEST' in result['projects']
        assert 'PROD' in result['projects']
        assert result['projects']['TEST']['total_issues'] == 15

    @pytest.mark.asyncio
    async def test_list_jira_components_success(self, mock_mcp, mock_dependencies):
        """Test successful list_jira_components execution"""
        mock_dependencies['query'].return_value = [
            ['comp1', 'proj1', 'Component 1', 'Description 1', 'http://url1',
             'lead1', 'PROJECT_DEFAULT', 'N', 'N', '2024-01-01']
        ]
        
        mock_dependencies['format'].return_value = {
            'ID': 'comp1', 'PROJECT': 'proj1', 'COMPONENT_NAME': 'Component 1',
            'DESCRIPTION': 'Description 1', 'URL': 'http://url1', 'LEAD': 'lead1',
            'ASSIGNEETYPE': 'PROJECT_DEFAULT', 'ARCHIVED': 'N', 'DELETED': 'N',
            '_FIVETRAN_SYNCED': '2024-01-01'
        }
        
        register_tools(mock_mcp)
        list_jira_components = mock_mcp._registered_tools[3]
        
        result = await list_jira_components(project='proj1')
        
        assert 'components' in result
        assert 'total_returned' in result
        assert 'filters_applied' in result
        assert result['filters_applied']['project'] == 'proj1'

    @pytest.mark.asyncio
    async def test_get_jira_issue_links_success(self, mock_mcp, mock_dependencies):
        """Test successful get_jira_issue_links execution"""
        # First query returns issue ID
        mock_dependencies['query'].return_value = [['123']]
        mock_dependencies['links'].return_value = {'123': [{'link_id': '456', 'type': 'blocks'}]}
        
        register_tools(mock_mcp)
        get_jira_issue_links = mock_mcp._registered_tools[4]
        
        result = await get_jira_issue_links('TEST-1')
        
        assert result['issue_key'] == 'TEST-1'
        assert result['issue_id'] == '123'
        assert 'links' in result
        assert result['total_links'] == 1

    @pytest.mark.asyncio
    async def test_exception_handling(self, mock_mcp, mock_dependencies):
        """Test exception handling in tools"""
        mock_dependencies['token'].side_effect = Exception("Database error")
        
        register_tools(mock_mcp)
        list_jira_issues = mock_mcp._registered_tools[0]
        
        result = await list_jira_issues()
        assert 'error' in result
        assert 'Database error' in result['error']