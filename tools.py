import logging
from typing import Any, Optional, List, Dict

from mcp.server.fastmcp import FastMCP

from database import (
    execute_snowflake_query,
    format_snowflake_row,
    sanitize_sql_value,
    get_issue_labels
)
from metrics import track_tool_usage

logger = logging.getLogger(__name__)

def register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools"""
    
    @mcp.tool()
    @track_tool_usage("list_issues")
    async def list_issues(
        project: Optional[str] = None,
        issue_type: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 50,
        search_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List JIRA issues from Snowflake with optional filtering.
        
        Args:
            project: Filter by project key (e.g., 'SMQE', 'OSIM')
            issue_type: Filter by issue type ID
            status: Filter by issue status ID
            priority: Filter by priority ID
            limit: Maximum number of issues to return (default: 50)
            search_text: Search in summary and description fields
        
        Returns:
            Dictionary containing issues list and metadata
        """
        try:
            # Build SQL query with filters
            sql_conditions = []
            
            if project:
                sql_conditions.append(f"PROJECT = '{sanitize_sql_value(project.upper())}'")
            
            if issue_type:
                sql_conditions.append(f"ISSUETYPE = '{sanitize_sql_value(issue_type)}'")
                
            if status:
                sql_conditions.append(f"ISSUESTATUS = '{sanitize_sql_value(status)}'")
                
            if priority:
                sql_conditions.append(f"PRIORITY = '{sanitize_sql_value(priority)}'")
            
            if search_text:
                search_condition = f"(LOWER(SUMMARY) LIKE '%{sanitize_sql_value(search_text.lower())}%' OR LOWER(DESCRIPTION) LIKE '%{sanitize_sql_value(search_text.lower())}%')"
                sql_conditions.append(search_condition)
            
            where_clause = ""
            if sql_conditions:
                where_clause = "WHERE " + " AND ".join(sql_conditions)
            
            sql = f"""
            SELECT 
                ID, ISSUE_KEY, PROJECT, ISSUENUM, ISSUETYPE, SUMMARY, 
                SUBSTRING(DESCRIPTION, 1, 500) as DESCRIPTION_TRUNCATED,
                DESCRIPTION, PRIORITY, ISSUESTATUS, RESOLUTION, 
                CREATED, UPDATED, DUEDATE, RESOLUTIONDATE, 
                VOTES, WATCHES, ENVIRONMENT, COMPONENT, FIXFOR
            FROM JIRA_ISSUE_NON_PII 
            {where_clause}
            ORDER BY CREATED DESC
            LIMIT {limit}
            """
            
            rows = await execute_snowflake_query(sql)
            
            issues = []
            issue_ids = []
            
            # Expected column order based on SELECT statement
            columns = [
                "ID", "ISSUE_KEY", "PROJECT", "ISSUENUM", "ISSUETYPE", "SUMMARY",
                "DESCRIPTION_TRUNCATED", "DESCRIPTION", "PRIORITY", "ISSUESTATUS", 
                "RESOLUTION", "CREATED", "UPDATED", "DUEDATE", "RESOLUTIONDATE",
                "VOTES", "WATCHES", "ENVIRONMENT", "COMPONENT", "FIXFOR"
            ]
            
            for row in rows:
                row_dict = format_snowflake_row(row, columns)
                
                # Build issue object
                issue = {
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
                    "component": row_dict.get("COMPONENT"),
                    "fix_version": row_dict.get("FIXFOR")
                }
                
                issues.append(issue)
                if row_dict.get("ID"):
                    issue_ids.append(str(row_dict.get("ID")))
            
            # Get labels for enrichment
            labels_data = await get_issue_labels(issue_ids)
            
            # Enrich issues with labels
            for issue in issues:
                issue_id = str(issue['id'])
                issue['labels'] = labels_data.get(issue_id, [])
            
            return {
                "issues": issues,
                "total_returned": len(issues),
                "filters_applied": {
                    "project": project,
                    "issue_type": issue_type,
                    "status": status,
                    "priority": priority,
                    "search_text": search_text,
                    "limit": limit
                }
            }
            
        except Exception as e:
            return {"error": f"Error reading issues from Snowflake: {str(e)}", "issues": []}

    @mcp.tool()
    @track_tool_usage("get_issue_details")
    async def get_issue_details(issue_key: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific JIRA issue by its key from Snowflake.
        
        Args:
            issue_key: The JIRA issue key (e.g., 'SMQE-1280')
        
        Returns:
            Dictionary containing detailed issue information
        """
        try:
            sql = f"""
            SELECT 
                ID, ISSUE_KEY, PROJECT, ISSUENUM, ISSUETYPE, SUMMARY, DESCRIPTION,
                PRIORITY, ISSUESTATUS, RESOLUTION, CREATED, UPDATED, DUEDATE, 
                RESOLUTIONDATE, VOTES, WATCHES, ENVIRONMENT, COMPONENT, FIXFOR,
                TIMEORIGINALESTIMATE, TIMEESTIMATE, TIMESPENT, WORKFLOW_ID,
                SECURITY, ARCHIVED, ARCHIVEDDATE
            FROM JIRA_ISSUE_NON_PII 
            WHERE ISSUE_KEY = '{sanitize_sql_value(issue_key)}'
            LIMIT 1
            """
            
            rows = await execute_snowflake_query(sql)
            
            if not rows:
                return {"error": f"Issue with key '{issue_key}' not found"}
            
            # Expected column order
            columns = [
                "ID", "ISSUE_KEY", "PROJECT", "ISSUENUM", "ISSUETYPE", "SUMMARY", "DESCRIPTION",
                "PRIORITY", "ISSUESTATUS", "RESOLUTION", "CREATED", "UPDATED", "DUEDATE",
                "RESOLUTIONDATE", "VOTES", "WATCHES", "ENVIRONMENT", "COMPONENT", "FIXFOR",
                "TIMEORIGINALESTIMATE", "TIMEESTIMATE", "TIMESPENT", "WORKFLOW_ID",
                "SECURITY", "ARCHIVED", "ARCHIVEDDATE"
            ]
            
            row_dict = format_snowflake_row(rows[0], columns)
            
            issue = {
                "id": row_dict.get("ID"),
                "key": row_dict.get("ISSUE_KEY"),
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
                "archived_date": row_dict.get("ARCHIVEDDATE")
            }
            
            # Get labels for this issue
            labels_data = await get_issue_labels([str(issue['id'])])
            issue['labels'] = labels_data.get(str(issue['id']), [])
            
            return {"issue": issue}
            
        except Exception as e:
            return {"error": f"Error retrieving issue details from Snowflake: {str(e)}"}

    @mcp.tool()
    @track_tool_usage("get_project_summary")
    async def get_project_summary() -> Dict[str, Any]:
        """
        Get a summary of all projects in the JIRA data from Snowflake.
        
        Returns:
            Dictionary containing project statistics
        """
        try:
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
            
            rows = await execute_snowflake_query(sql)
            columns = ["PROJECT", "ISSUESTATUS", "PRIORITY", "COUNT"]
            
            project_stats = {}
            total_issues = 0
            
            for row in rows:
                row_dict = format_snowflake_row(row, columns)
                
                project = row_dict.get("PROJECT", "Unknown")
                status = row_dict.get("ISSUESTATUS", "Unknown")
                priority = row_dict.get("PRIORITY", "Unknown")
                count = row_dict.get("COUNT", 0)
                
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
            
        except Exception as e:
            return {"error": f"Error generating project summary from Snowflake: {str(e)}"} 