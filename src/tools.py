import logging
from typing import Any, Optional, Dict, List

from mcp.server.fastmcp import FastMCP

from config import MCP_TRANSPORT, SNOWFLAKE_TOKEN, INTERNAL_GATEWAY, SNOWFLAKE_AUTH_METHOD
from database import (
    execute_snowflake_query,
    format_snowflake_row,
    sanitize_sql_value,
    get_issue_links,
    get_issue_enrichment_data_concurrent,
    SnowflakeAuthenticationError,
    get_auth_token
)
from metrics import track_tool_usage, track_concurrent_operation

logger = logging.getLogger(__name__)


def get_snowflake_token(mcp: FastMCP) -> Optional[str]:
    """Get Snowflake token from either config (stdio) or request headers (non-stdio)"""
    if MCP_TRANSPORT == "stdio" or INTERNAL_GATEWAY.lower() == "true":
        # For stdio transport, authentication is handled by the database layer
        # based on SNOWFLAKE_AUTH_METHOD configuration
        if SNOWFLAKE_AUTH_METHOD == "private_key":
            logger.info("Using private key authentication for stdio transport")
            return None  # Database layer will generate JWT token
        else:
            logger.info("Using token authentication for stdio transport")
            return SNOWFLAKE_TOKEN
    else:
        try:
            # Get token from request headers for non-stdio transports
            context = mcp.get_context()
            if context and hasattr(context, 'request_context') and context.request_context:
                token = context.request_context.request.headers["X-Snowflake-Token"]
                if token:
                    logger.info("Successfully retrieved Snowflake token from X-Snowflake-Token header")
                    return token
                else:
                    logger.warning("X-Snowflake-Token header is present but empty")
            else:
                logger.error("Request context not available for non-stdio transport")
        except KeyError:
            logger.error("X-Snowflake-Token header not found in request headers")
        except Exception as e:
            logger.error(f"Error getting token from request context: {e}")
        return None


def register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools"""

    @mcp.tool()
    @track_tool_usage("list_jira_issues")
    async def list_jira_issues(
        project: Optional[str] = None,
        issue_type: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 50,
        search_text: Optional[str] = None,
        timeframe: int = 0,
        components: Optional[str] = None,
        created_days: int = 0,
        updated_days: int = 0,
        resolved_days: int = 0,
    ) -> Dict[str, Any]:
        """

        Args:
            project: Filter by project key (e.g., 'SMQE', 'OSIM')
            issue_type: Filter by issue type ID
            status: Filter by issue status ID
            priority: Filter by priority ID
            limit: Maximum number of issues to return (default: 50)
            search_text: Search in summary and description fields
            timeframe: Filter issues where ANY date (created, updated, or resolved) is within last N days (default: 0 = disabled)
            components: Comma-separated list; match ANY in component name
            created_days: Filter by creation date within last N days (overrides timeframe if > 0, default: 0 = disabled)
            updated_days: Filter by update date within last N days (default: 0 = disabled)
            resolved_days: Filter by resolution date within last N days (default: 0 = disabled)

        Returns:
            Dictionary containing issues list and metadata
        """
        try:
            # Get the Snowflake token
            snowflake_token = get_snowflake_token(mcp)

            # Check if we have a token when using token-based authentication
            if not snowflake_token and SNOWFLAKE_AUTH_METHOD == "token":
                return {"error": "No Snowflake token available", "issues": []}

            # For private key auth, validate JWT token generation early
            if SNOWFLAKE_AUTH_METHOD == "private_key":
                try:
                    test_token = get_auth_token(snowflake_token)
                    if not test_token:
                        return {"error": "Failed to generate JWT token for private key authentication", "issues": []}
                except Exception as e:
                    return {"error": f"JWT token error: {str(e)}", "issues": []}

            # Build SQL query with filters - always include component joins
            sql_conditions = []

            if project:
                sql_conditions.append(f"i.PROJECT = '{sanitize_sql_value(project.upper())}'")

            if issue_type:
                sql_conditions.append(f"i.ISSUETYPE = '{sanitize_sql_value(issue_type)}'")

            if status:
                sql_conditions.append(f"i.ISSUESTATUS = '{sanitize_sql_value(status)}'")

            if priority:
                sql_conditions.append(f"i.PRIORITY = '{sanitize_sql_value(priority)}'")

            if search_text:
                search_condition = f"(LOWER(i.SUMMARY) LIKE '%{sanitize_sql_value(search_text.lower())}%' OR LOWER(i.DESCRIPTION) LIKE '%{sanitize_sql_value(search_text.lower())}%')"
                sql_conditions.append(search_condition)

            if components:
                # Support comma-separated component filters (match ANY)
                component_terms = [
                    term.strip().lower() for term in components.split(",") if term.strip()
                ]
                if component_terms:
                    per_term_conditions = []
                    for term in component_terms:
                        safe_term = sanitize_sql_value(term)
                        per_term_conditions.append(
                            f"(LOWER(c.CNAME) LIKE '%{safe_term}%' OR LOWER(c.DESCRIPTION) LIKE '%{safe_term}%')"
                        )
                    components_condition = "(" + " OR ".join(per_term_conditions) + ")"
                    sql_conditions.append(components_condition)

            # Add date filters - specific date filters take precedence over general timeframe
            date_conditions = []

            # Use specific created_days if provided
            if created_days > 0:
                date_conditions.append(f"i.CREATED >= DATEADD(DAY, -{created_days}, CURRENT_TIMESTAMP())")

            if updated_days > 0:
                date_conditions.append(f"i.UPDATED >= DATEADD(DAY, -{updated_days}, CURRENT_TIMESTAMP())")

            if resolved_days > 0:
                date_conditions.append(f"i.RESOLUTIONDATE >= DATEADD(DAY, -{resolved_days}, CURRENT_TIMESTAMP())")

            # Apply timeframe filter if no specific date filters are provided and timeframe > 0
            if timeframe > 0 and not date_conditions:
                # Timeframe filters issues where ANY date (created, updated, or resolved) is within last N days
                timeframe_condition = f"(i.CREATED >= DATEADD(DAY, -{timeframe}, CURRENT_TIMESTAMP()) OR i.UPDATED >= DATEADD(DAY, -{timeframe}, CURRENT_TIMESTAMP()) OR i.RESOLUTIONDATE >= DATEADD(DAY, -{timeframe}, CURRENT_TIMESTAMP()))"
                sql_conditions.append(timeframe_condition)

            if date_conditions:
                # All specific date conditions must be satisfied (AND logic)
                sql_conditions.extend(date_conditions)

            where_clause = ""
            if sql_conditions:
                where_clause = "WHERE " + " AND ".join(sql_conditions)

            # Build the SQL query - always include component joins
            sql = f"""
            SELECT DISTINCT
                i.ID, i.ISSUE_KEY, i.PROJECT, i.ISSUENUM, i.ISSUETYPE, i.SUMMARY,
                SUBSTRING(i.DESCRIPTION, 1, 500) as DESCRIPTION_TRUNCATED,
                i.DESCRIPTION, i.PRIORITY, i.ISSUESTATUS, i.RESOLUTION,
                i.CREATED, i.UPDATED, i.DUEDATE, i.RESOLUTIONDATE,
                i.VOTES, i.WATCHES, i.ENVIRONMENT, i.COMPONENT, i.FIXFOR,
                compagg.COMPONENT_NAMES
            FROM JIRA_ISSUE_NON_PII i
            LEFT JOIN JIRA_DB.RHAI_MARTS.JIRA_NODEASSOCIATION_RHAI na
                ON i.ID = na.SOURCE_NODE_ID
                AND na.ASSOCIATION_TYPE = 'IssueComponent'
            LEFT JOIN JIRA_DB.RHAI_MARTS.JIRA_COMPONENT_RHAI c
                ON na.SINK_NODE_ID = c.ID
            LEFT JOIN (
                SELECT
                    na2.SOURCE_NODE_ID AS ISSUE_ID,
                    LISTAGG(DISTINCT c2.CNAME, '||') WITHIN GROUP (ORDER BY c2.CNAME) AS COMPONENT_NAMES
                FROM JIRA_DB.RHAI_MARTS.JIRA_NODEASSOCIATION_RHAI na2
                LEFT JOIN JIRA_DB.RHAI_MARTS.JIRA_COMPONENT_RHAI c2
                    ON na2.SINK_NODE_ID = c2.ID
                WHERE na2.ASSOCIATION_TYPE = 'IssueComponent'
                GROUP BY na2.SOURCE_NODE_ID
            ) compagg ON compagg.ISSUE_ID = i.ID
            {where_clause}
            ORDER BY i.CREATED DESC
            LIMIT {limit}
            """

            rows = await execute_snowflake_query(sql, snowflake_token)

            # Aggregate rows by unique issue to avoid duplicates when there are multiple components
            issues_by_id: Dict[str, Dict[str, Any]] = {}
            issue_ids: List[str] = []

            # Expected column order based on SELECT statement
            columns = [
                "ID", "ISSUE_KEY", "PROJECT", "ISSUENUM", "ISSUETYPE", "SUMMARY",
                "DESCRIPTION_TRUNCATED", "DESCRIPTION", "PRIORITY", "ISSUESTATUS",
                "RESOLUTION", "CREATED", "UPDATED", "DUEDATE", "RESOLUTIONDATE",
                "VOTES", "WATCHES", "ENVIRONMENT", "COMPONENT", "FIXFOR",
                "COMPONENT_NAMES"
            ]

            for row in rows:
                row_dict = format_snowflake_row(row, columns)

                issue_id = row_dict.get("ID")
                if issue_id is None:
                    # Skip malformed rows
                    continue

                issue_id_str = str(issue_id)

                if issue_id_str not in issues_by_id:
                    # Initialize new issue entry
                    issues_by_id[issue_id_str] = {
                        "id": row_dict.get("ID"),
                        "key": row_dict.get("ISSUE_KEY"),
                        "project": row_dict.get("PROJECT"),
                        "issue_number": row_dict.get("ISSUENUM"),
                        "issue_type": row_dict.get("ISSUETYPE"),
                        "summary": row_dict.get("SUMMARY"),
                        "description": row_dict.get("DESCRIPTION_TRUNCATED") or "",
                        "priority": row_dict.get("PRIORITY"),
                        "status": row_dict.get("ISSUESTATUS"),
                        "resolution": row_dict.get("RESOLUTION"),
                        "created": row_dict.get("CREATED"),
                        "updated": row_dict.get("UPDATED"),
                        "due_date": row_dict.get("DUEDATE"),
                        "resolution_date": row_dict.get("RESOLUTIONDATE"),
                        "votes": row_dict.get("VOTES"),
                        "watches": row_dict.get("WATCHES"),
                        "environment": row_dict.get("ENVIRONMENT"),
                        # Expose full list of component names for the issue
                        "component": [],
                        "fix_version": row_dict.get("FIXFOR"),
                        # For backwards-compatibility, keep a single representative component_name if desired
                        "component_name": None,
                    }
                    issue_ids.append(issue_id_str)

                # Aggregate component names from the precomputed aggregation string
                comp_names_str = row_dict.get("COMPONENT_NAMES") or ""
                if comp_names_str:
                    current_components = issues_by_id[issue_id_str]["component"]
                    # Split and add uniquely while preserving order
                    for name in [n.strip() for n in comp_names_str.split("||") if n and n.strip()]:
                        if name not in current_components:
                            current_components.append(name)
                    # Set a representative component_name for compatibility (first in list)
                    issues_by_id[issue_id_str]["component_name"] = current_components[0] if current_components else None

            # Get labels, comments, and links concurrently for better performance
            track_concurrent_operation("issue_enrichment")
            labels_data, comments_data, links_data = await get_issue_enrichment_data_concurrent(
                issue_ids, snowflake_token
            )

            # Enrich issues with labels and links
            issues = list(issues_by_id.values())
            for issue in issues:
                issue_id = str(issue['id'])
                issue['labels'] = labels_data.get(issue_id, [])
                issue['links'] = links_data.get(issue_id, [])
                # Don't add comments to list view to keep it lightweight
                # Comments are only added in the detailed view

            return {
                "issues": issues,
                "total_returned": len(issues),
                "filters_applied": {
                    "project": project,
                    "issue_type": issue_type,
                    "status": status,
                    "priority": priority,
                    "search_text": search_text,
                    "timeframe": timeframe,
                    "components": components,
                    "created_days": created_days,
                    "updated_days": updated_days,
                    "resolved_days": resolved_days,
                    "limit": limit
                }
            }

        except SnowflakeAuthenticationError as e:
            logger.error(f"Authentication error in list_jira_issues: {str(e)}")
            return {"error": "Authentication failed: Invalid or expired token", "issues": []}
        except Exception as e:
            return {"error": f"Error reading issues from Snowflake: {str(e)}", "issues": []}

    @mcp.tool()
    @track_tool_usage("get_jira_issue_details")
    async def get_jira_issue_details(issue_keys: List[str]) -> Dict[str, Any]:
        """
        Get detailed information for multiple JIRA issues by their keys from Snowflake.

        Args:
            issue_keys: List of JIRA issue keys (e.g., ['SMQE-1280', 'SMQE-1281'])

        Returns:
            Dictionary containing detailed issue information including comments for all found issues
        """
        try:
            # Get the Snowflake token
            snowflake_token = get_snowflake_token(mcp)

            # Check if we have a token when using token-based authentication
            if not snowflake_token and SNOWFLAKE_AUTH_METHOD == "token":
                return {"error": "No Snowflake token available"}

            # For private key auth, validate JWT token generation early
            if SNOWFLAKE_AUTH_METHOD == "private_key":
                try:
                    test_token = get_auth_token(snowflake_token)
                    if not test_token:
                        return {"error": "Failed to generate JWT token for private key authentication"}
                except Exception as e:
                    return {"error": f"JWT token error: {str(e)}"}

            # Validate input
            if not issue_keys:
                return {
                    "found_issues": {},
                    "not_found": [],
                    "total_found": 0,
                    "total_requested": 0
                }

            # Sanitize all issue keys and build IN clause
            sanitized_keys = [f"'{sanitize_sql_value(key)}'" for key in issue_keys]
            in_clause = f"({', '.join(sanitized_keys)})"

            sql = f"""
            SELECT DISTINCT
                i.ID, i.ISSUE_KEY, i.PROJECT, i.ISSUENUM, i.ISSUETYPE, i.SUMMARY, i.DESCRIPTION,
                i.PRIORITY, i.ISSUESTATUS, i.RESOLUTION, i.CREATED, i.UPDATED, i.DUEDATE,
                i.RESOLUTIONDATE, i.VOTES, i.WATCHES, i.ENVIRONMENT, i.COMPONENT, i.FIXFOR,
                i.TIMEORIGINALESTIMATE, i.TIMEESTIMATE, i.TIMESPENT, i.WORKFLOW_ID,
                i.SECURITY, i.ARCHIVED, i.ARCHIVEDDATE,
                c.CNAME as COMPONENT_NAME, c.DESCRIPTION as COMPONENT_DESCRIPTION,
                c.ARCHIVED as COMPONENT_ARCHIVED, c.DELETED as COMPONENT_DELETED
            FROM JIRA_ISSUE_NON_PII i
            LEFT JOIN JIRA_DB.RHAI_MARTS.JIRA_NODEASSOCIATION_RHAI na
                ON i.ID = na.SOURCE_NODE_ID
                AND na.ASSOCIATION_TYPE = 'IssueComponent'
            LEFT JOIN JIRA_DB.RHAI_MARTS.JIRA_COMPONENT_RHAI c
                ON na.SINK_NODE_ID = c.ID
            WHERE i.ISSUE_KEY IN {in_clause}
            ORDER BY i.ISSUE_KEY
            """

            rows = await execute_snowflake_query(sql, snowflake_token)

            # Expected column order
            columns = [
                "ID", "ISSUE_KEY", "PROJECT", "ISSUENUM", "ISSUETYPE", "SUMMARY", "DESCRIPTION",
                "PRIORITY", "ISSUESTATUS", "RESOLUTION", "CREATED", "UPDATED", "DUEDATE",
                "RESOLUTIONDATE", "VOTES", "WATCHES", "ENVIRONMENT", "COMPONENT", "FIXFOR",
                "TIMEORIGINALESTIMATE", "TIMEESTIMATE", "TIMESPENT", "WORKFLOW_ID",
                "SECURITY", "ARCHIVED", "ARCHIVEDDATE",
                "COMPONENT_NAME", "COMPONENT_DESCRIPTION", "COMPONENT_ARCHIVED", "COMPONENT_DELETED"
            ]

            # Process all rows and track found issue keys
            found_issues = {}
            issue_ids = []
            found_keys = set()

            for row in rows:
                row_dict = format_snowflake_row(row, columns)
                issue_key = row_dict.get("ISSUE_KEY")

                if issue_key:
                    found_keys.add(issue_key)

                    issue = {
                        "id": row_dict.get("ID"),
                        "key": issue_key,
                        "project": row_dict.get("PROJECT"),
                        "issue_number": row_dict.get("ISSUENUM"),
                        "issue_type": row_dict.get("ISSUETYPE"),
                        "summary": row_dict.get("SUMMARY"),
                        "description": row_dict.get("DESCRIPTION", ""),
                        "priority": row_dict.get("PRIORITY"),
                        "status": row_dict.get("ISSUESTATUS"),
                        "resolution": row_dict.get("RESOLUTION"),
                        "created": row_dict.get("CREATED"),
                        "updated": row_dict.get("UPDATED"),
                        "due_date": row_dict.get("DUEDATE"),
                        "resolution_date": row_dict.get("RESOLUTIONDATE"),
                        "votes": row_dict.get("VOTES"),
                        "watches": row_dict.get("WATCHES"),
                        "environment": row_dict.get("ENVIRONMENT"),
                        "component": row_dict.get("COMPONENT"),
                        "fix_version": row_dict.get("FIXFOR"),
                        "time_original_estimate": row_dict.get("TIMEORIGINALESTIMATE"),
                        "time_estimate": row_dict.get("TIMEESTIMATE"),
                        "time_spent": row_dict.get("TIMESPENT"),
                        "workflow_id": row_dict.get("WORKFLOW_ID"),
                        "security": row_dict.get("SECURITY"),
                        "archived": row_dict.get("ARCHIVED"),
                        "archived_date": row_dict.get("ARCHIVEDDATE"),
                        "component_name": row_dict.get("COMPONENT_NAME"),
                    }

                    found_issues[issue_key] = issue
                    if row_dict.get("ID"):
                        issue_ids.append(str(row_dict.get("ID")))

            # Determine which keys were not found
            not_found_keys = [key for key in issue_keys if key not in found_keys]

            # Get labels, comments, and links concurrently for all found issues
            if issue_ids:
                track_concurrent_operation("multiple_issue_enrichment")
                labels_data, comments_data, links_data = await get_issue_enrichment_data_concurrent(
                    issue_ids, snowflake_token
                )

                # Enrich each issue with labels, comments, and links
                for issue_key, issue in found_issues.items():
                    issue_id = str(issue['id'])
                    issue['labels'] = labels_data.get(issue_id, [])
                    issue['comments'] = comments_data.get(issue_id, [])
                    issue['links'] = links_data.get(issue_id, [])

            return {
                "found_issues": found_issues,
                "not_found": not_found_keys,
                "total_found": len(found_issues),
                "total_requested": len(issue_keys)
            }

        except SnowflakeAuthenticationError as e:
            logger.error(f"Authentication error in get_jira_issue_details: {str(e)}")
            return {"error": "Authentication failed: Invalid or expired token"}
        except Exception as e:
            return {"error": f"Error reading issue details from Snowflake: {str(e)}"}

    @mcp.tool()
    @track_tool_usage("get_jira_project_summary")
    async def get_jira_project_summary() -> Dict[str, Any]:
        """
        Get a summary of all projects in the JIRA data from Snowflake.

        Returns:
            Dictionary containing project statistics
        """
        try:
            # Get the Snowflake token
            snowflake_token = get_snowflake_token(mcp)

            # Check if we have a token when using token-based authentication
            if not snowflake_token and SNOWFLAKE_AUTH_METHOD == "token":
                return {"error": "No Snowflake token available"}

            # For private key auth, validate JWT token generation early
            if SNOWFLAKE_AUTH_METHOD == "private_key":
                try:
                    test_token = get_auth_token(snowflake_token)
                    if not test_token:
                        return {"error": "Failed to generate JWT token for private key authentication"}
                except Exception as e:
                    return {"error": f"JWT token error: {str(e)}"}

            sql = """
            SELECT
                PROJECT,
                ISSUESTATUS,
                PRIORITY,
                COUNT(*) as COUNT
            FROM JIRA_ISSUE_NON_PII
            GROUP BY PROJECT, ISSUESTATUS, PRIORITY
            ORDER BY PROJECT, ISSUESTATUS, PRIORITY
            """

            rows = await execute_snowflake_query(sql, snowflake_token)
            columns = ["PROJECT", "ISSUESTATUS", "PRIORITY", "COUNT"]

            project_stats = {}
            total_issues = 0

            for row in rows:
                row_dict = format_snowflake_row(row, columns)

                project = row_dict.get("PROJECT", "Unknown")
                status = row_dict.get("ISSUESTATUS", "Unknown")
                priority = row_dict.get("PRIORITY", "Unknown")
                count = int(row_dict.get("COUNT", 0)) if row_dict.get("COUNT") is not None else 0

                if project not in project_stats:
                    project_stats[project] = {
                        'total_issues': 0,
                        'statuses': {},
                        'priorities': {}
                    }

                project_stats[project]['total_issues'] += count
                project_stats[project]['statuses'][status] = project_stats[project]['statuses'].get(status, 0) + count
                project_stats[project]['priorities'][priority] = project_stats[project]['priorities'].get(priority, 0) + count

                total_issues += count

            return {
                "total_issues": total_issues,
                "total_projects": len(project_stats),
                "projects": project_stats
            }

        except SnowflakeAuthenticationError as e:
            logger.error(f"Authentication error in get_jira_project_summary: {str(e)}")
            return {"error": "Authentication failed: Invalid or expired token"}
        except Exception as e:
            return {"error": f"Error generating project summary from Snowflake: {str(e)}"}

    @mcp.tool()
    @track_tool_usage("get_jira_issue_links")
    async def get_jira_issue_links(issue_key: str) -> Dict[str, Any]:
        """
        Get issue links for a specific JIRA issue by its key from Snowflake.

        Args:
            issue_key: The JIRA issue key (e.g., 'SMQE-1280')

        Returns:
            Dictionary containing issue links information
        """
        try:
            # Get the Snowflake token
            snowflake_token = get_snowflake_token(mcp)

            # Check if we have a token when using token-based authentication
            if not snowflake_token and SNOWFLAKE_AUTH_METHOD == "token":
                return {"error": "No Snowflake token available"}

            # For private key auth, validate JWT token generation early
            if SNOWFLAKE_AUTH_METHOD == "private_key":
                try:
                    test_token = get_auth_token(snowflake_token)
                    if not test_token:
                        return {"error": "Failed to generate JWT token for private key authentication"}
                except Exception as e:
                    return {"error": f"JWT token error: {str(e)}"}

            # First get the issue ID from the issue key
            sql = f"""
            SELECT ID
            FROM JIRA_ISSUE_NON_PII
            WHERE ISSUE_KEY = '{sanitize_sql_value(issue_key)}'
            LIMIT 1
            """

            rows = await execute_snowflake_query(sql, snowflake_token)

            if not rows:
                return {"error": f"Issue with key '{issue_key}' not found"}

            issue_id = str(rows[0][0])  # Get the ID from the first row, first column

            # Get issue links for this issue ID
            links_data = await get_issue_links([issue_id], snowflake_token)
            issue_links = links_data.get(issue_id, [])

            return {
                "issue_key": issue_key,
                "issue_id": issue_id,
                "links": issue_links,
                "total_links": len(issue_links)
            }

        except SnowflakeAuthenticationError as e:
            logger.error(f"Authentication error in get_jira_issue_links: {str(e)}")
            return {"error": "Authentication failed: Invalid or expired token"}
        except Exception as e:
            return {"error": f"Error reading issue links from Snowflake: {str(e)}"}
