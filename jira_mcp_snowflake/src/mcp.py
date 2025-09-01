"""JIRA MCP Snowflake Server implementation.

This module contains the main JIRA MCP Snowflake Server class that provides
tools for MCP clients. It uses FastMCP to register and manage MCP capabilities.
"""

from fastmcp import FastMCP

from jira_mcp_snowflake.src.settings import settings

# Import tools from the tools package
from jira_mcp_snowflake.src.tools.jira_tools import (
    get_jira_issue_details,
    get_jira_issue_links,
    get_jira_project_summary,
    list_jira_issues,
)
from jira_mcp_snowflake.utils.pylogger import (
    force_reconfigure_all_loggers,
    get_python_logger,
)

logger = get_python_logger()


class JiraMCPSnowflakeServer:
    """Main JIRA MCP Snowflake Server implementation following tools-first architecture.

    This server provides tools for accessing JIRA data from Snowflake,
    adhering to the tools-first architectural pattern for MCP servers.
    """

    def __init__(self):
        """Initialize the MCP server with JIRA tools following tools-first architecture."""
        try:
            # Initialize FastMCP server
            self.mcp = FastMCP("jira-mcp-snowflake")

            # Force reconfigure all loggers after FastMCP initialization to ensure structured logging
            force_reconfigure_all_loggers(settings.PYTHON_LOG_LEVEL)

            self._register_mcp_tools()

            logger.info("JIRA MCP Snowflake Server initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize JIRA MCP Snowflake Server: {e}")
            raise

    def _register_mcp_tools(self) -> None:
        """Register MCP tools for JIRA operations (tools-first architecture).

        Registers all available tools with the FastMCP server instance.
        In tools-first architecture, the server only provides tools.
        Currently includes:
        - list_jira_issues: List and filter JIRA issues
        - get_jira_issue_details: Get detailed information for specific issues
        - get_jira_project_summary: Get project statistics and summaries
        - get_jira_issue_links: Get issue links for a specific issue
        """
        # Register all the imported tools
        self.mcp.tool()(list_jira_issues)
        self.mcp.tool()(get_jira_issue_details)
        self.mcp.tool()(get_jira_project_summary)
        self.mcp.tool()(get_jira_issue_links)
