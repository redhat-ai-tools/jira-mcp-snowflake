import os
import json
import re
import logging
from typing import Any, Optional, List, Dict
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

# Configure logging to stderr so it doesn't interfere with MCP protocol
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

mcp = FastMCP("jira-mcp-snowflake")

MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio")

# Snowflake API configuration from environment variables
SNOWFLAKE_BASE_URL = os.environ.get("SNOWFLAKE_BASE_URL", "https://gdadclc-rhprod.snowflakecomputing.com/api/v2")
SNOWFLAKE_DATABASE = os.environ.get("SNOWFLAKE_DATABASE", "JIRA_DB")
SNOWFLAKE_SCHEMA = os.environ.get("SNOWFLAKE_SCHEMA", "RHAI_MARTS")

def sanitize_sql_value(value: str) -> str:
    """Sanitize a SQL value to prevent injection attacks"""
    if not isinstance(value, str):
        return str(value)
    # Remove or escape dangerous characters
    # For string values, we'll escape single quotes by doubling them
    return value.replace("'", "''")

def validate_identifier(identifier: str) -> bool:
    """Validate that an identifier contains only safe characters"""
    # Allow only alphanumeric characters, underscores, and hyphens
    return bool(re.match(r'^[A-Za-z0-9_-]+$', identifier))

async def make_snowflake_request(
    endpoint: str, 
    method: str = "POST", 
    data: dict[str, Any] = None
) -> dict[str, Any] | None:
    """Make a request to Snowflake API"""
    snowflake_token = (
        os.environ["SNOWFLAKE_TOKEN"]
        if MCP_TRANSPORT == "stdio"
        else mcp.get_context().request_context.request.headers["X-Snowflake-Token"]
    )
    if not snowflake_token:
        logger.error("SNOWFLAKE_TOKEN environment variable is required but not set")
        return None
        
    headers = {
        "Authorization": f"Bearer {snowflake_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    url = f"{SNOWFLAKE_BASE_URL}/{endpoint}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "GET":
                response = await client.request(method, url, headers=headers, params=data)
            else:
                response = await client.request(method, url, headers=headers, json=data)
            
            response.raise_for_status()
            
            # Try to parse JSON, but handle cases where response is not valid JSON
            try:
                return response.json()
            except json.JSONDecodeError as json_error:
                logger.error(f"Failed to parse JSON response from Snowflake API: {json_error}")
                logger.error(f"Response content: {response.text[:500]}...")  # Log first 500 chars
                # Return None to indicate error, which will be handled by calling functions
                return None
                
    except httpx.HTTPStatusError as http_error:
        logger.error(f"HTTP error from Snowflake API: {http_error.response.status_code} - {http_error.response.text}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in Snowflake API request: {str(e)}")
        return None

async def execute_snowflake_query(sql: str) -> List[Dict[str, Any]]:
    """Execute a SQL query against Snowflake and return results"""
    try:
        # Use the statements endpoint to execute SQL
        endpoint = "statements"
        payload = {
            "statement": sql,
            "timeout": 60,
            "database": SNOWFLAKE_DATABASE,
            "schema": SNOWFLAKE_SCHEMA
        }
        
        logger.info(f"Executing Snowflake query: {sql[:100]}...")  # Log first 100 chars of query
        
        response = await make_snowflake_request(endpoint, "POST", payload)
        
        # Check if response is None (indicating an error in API request or JSON parsing)
        if response is None:
            logger.error("Failed to get valid response from Snowflake API")
            return []
        
        # Parse the response to extract data
        if response and "data" in response:
            logger.info(f"Successfully got {len(response['data'])} rows from Snowflake")
            return response["data"]
        elif response and "resultSet" in response:
            # Handle different response formats
            result_set = response["resultSet"]
            if "data" in result_set:
                logger.info(f"Successfully got {len(result_set['data'])} rows from Snowflake (resultSet format)")
                return result_set["data"]
        
        logger.warning("No data found in Snowflake response")
        return []
        
    except Exception as e:
        logger.error(f"Error executing Snowflake query: {str(e)}")
        logger.error(f"Query that failed: {sql}")
        return []

def format_snowflake_row(row_data: List[Any], columns: List[str]) -> Dict[str, Any]:
    """Convert Snowflake row data to dictionary using column names"""
    if len(row_data) != len(columns):
        return {}
    
    return {columns[i]: row_data[i] for i in range(len(columns))}

@mcp.tool()
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
        labels_data = await _get_issue_labels(issue_ids)
        
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

async def _get_issue_labels(issue_ids: List[str]) -> Dict[str, List[str]]:
    """Get labels for given issue IDs from Snowflake"""
    if not issue_ids:
        return {}
    
    labels_data = {}
    
    try:
        # Sanitize and validate issue IDs (should be numeric)
        sanitized_ids = []
        for issue_id in issue_ids:
            # Ensure issue IDs are numeric to prevent injection
            if isinstance(issue_id, (str, int)) and str(issue_id).isdigit():
                sanitized_ids.append(str(issue_id))
        
        if not sanitized_ids:
            return {}
        
        # Create comma-separated list for IN clause
        ids_str = "'" + "','".join(sanitized_ids) + "'"
        
        sql = f"""
        SELECT ISSUE, LABEL 
        FROM JIRA_LABEL_RHAI 
        WHERE ISSUE IN ({ids_str}) AND LABEL IS NOT NULL
        """
        
        rows = await execute_snowflake_query(sql)
        columns = ["ISSUE", "LABEL"]
        
        for row in rows:
            row_dict = format_snowflake_row(row, columns)
            issue_id = str(row_dict.get("ISSUE"))
            label = row_dict.get("LABEL")
            
            if issue_id and label:
                if issue_id not in labels_data:
                    labels_data[issue_id] = []
                labels_data[issue_id].append(label)
    
    except Exception as e:
        logger.error(f"Error fetching labels: {str(e)}")
    
    return labels_data

@mcp.tool()
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
        labels_data = await _get_issue_labels([str(issue['id'])])
        issue['labels'] = labels_data.get(str(issue['id']), [])
        
        return {"issue": issue}
        
    except Exception as e:
        return {"error": f"Error retrieving issue details from Snowflake: {str(e)}"}

@mcp.tool()
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

@mcp.tool()
async def list_components(
    project: Optional[str] = None,
    archived: Optional[str] = None,
    deleted: Optional[str] = None,
    limit: int = 50,
    search_text: Optional[str] = None
) -> Dict[str, Any]:
    """
    List JIRA components from Snowflake with optional filtering.
    
    Args:
        project: Filter by project ID (e.g., '12325621')
        archived: Filter by archived status ('Y' or 'N')
        deleted: Filter by deleted status ('Y' or 'N')
        limit: Maximum number of components to return (default: 50)
        search_text: Search in component name and description fields
    
    Returns:
        Dictionary containing components list and metadata
    """
    try:
        # Build SQL query with filters
        sql_conditions = []
        
        if project:
            sql_conditions.append(f"PROJECT = '{sanitize_sql_value(project)}'")
        
        if archived:
            sql_conditions.append(f"ARCHIVED = '{sanitize_sql_value(archived.upper())}'")
            
        if deleted:
            sql_conditions.append(f"DELETED = '{sanitize_sql_value(deleted.upper())}'")
        
        if search_text:
            search_condition = f"(LOWER(CNAME) LIKE '%{sanitize_sql_value(search_text.lower())}%' OR LOWER(DESCRIPTION) LIKE '%{sanitize_sql_value(search_text.lower())}%')"
            sql_conditions.append(search_condition)
        
        where_clause = ""
        if sql_conditions:
            where_clause = "WHERE " + " AND ".join(sql_conditions)
        
        sql = f"""
        SELECT 
            ID, PROJECT, CNAME, DESCRIPTION, URL, LEAD, 
            ASSIGNEETYPE, ARCHIVED, DELETED, _FIVETRAN_SYNCED
        FROM JIRA_COMPONENT_RHAI 
        {where_clause}
        ORDER BY CNAME ASC
        LIMIT {limit}
        """
        
        rows = await execute_snowflake_query(sql)
        
        components = []
        
        # Expected column order based on SELECT statement
        columns = [
            "ID", "PROJECT", "CNAME", "DESCRIPTION", "URL", "LEAD",
            "ASSIGNEETYPE", "ARCHIVED", "DELETED", "_FIVETRAN_SYNCED"
        ]
        
        for row in rows:
            row_dict = format_snowflake_row(row, columns)
            
            # Build component object
            component = {
                "id": row_dict.get("ID"),
                "project": row_dict.get("PROJECT"),
                "name": row_dict.get("CNAME"),
                "description": row_dict.get("DESCRIPTION") or "",
                "url": row_dict.get("URL"),
                "lead": row_dict.get("LEAD"),
                "assignee_type": row_dict.get("ASSIGNEETYPE"),
                "archived": row_dict.get("ARCHIVED"),
                "deleted": row_dict.get("DELETED"),
                "synced": row_dict.get("_FIVETRAN_SYNCED")
            }
            
            components.append(component)
        
        return {
            "components": components,
            "total_returned": len(components),
            "filters_applied": {
                "project": project,
                "archived": archived,
                "deleted": deleted,
                "search_text": search_text,
                "limit": limit
            }
        }
        
    except Exception as e:
        return {"error": f"Error reading components from Snowflake: {str(e)}", "components": []}

if __name__ == "__main__":
    mcp.run(transport=MCP_TRANSPORT)
