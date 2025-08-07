# Jira MCP Server


A Model Context Protocol (MCP) server that provides access to JIRA issue data stored in Snowflake. This server enables AI assistants to query, filter, and analyze JIRA issues through a standardized interface.

## Overview

This MCP server connects to Snowflake to query JIRA data and provides four main tools for interacting with the data:

- **`list_jira_issues`** - Query and filter JIRA issues with various criteria
- **`get_jira_issue_details`** - Get detailed information for a specific issue by key
- **`get_jira_project_summary`** - Get statistics and summaries for all projects
- **`list_jira_components`** - List and filter JIRA components with various criteria

## Features

### Data Sources
The server connects to Snowflake and queries the following tables:
- `JIRA_ISSUE_NON_PII` - Main issue data (non-personally identifiable information)
- `JIRA_LABEL_RHAI` - Issue labels and tags
- `JIRA_COMMENT_NON_PII` - Issue comments (non-personally identifiable information)
- `JIRA_COMPONENT_RHAI` - JIRA project components and their metadata

**Note**: Table names are expected to exist in your configured Snowflake database and schema.

### Available Tools

#### 1. List Issues (`list_jira_issues`)
Query JIRA issues with optional filtering:
- **Project filtering** - Filter by project key (e.g., 'SMQE', 'OSIM')
- **Issue type filtering** - Filter by issue type ID
- **Status filtering** - Filter by issue status ID  
- **Priority filtering** - Filter by priority ID
- **Text search** - Search in summary and description fields
- **Result limiting** - Control number of results returned (default: 50)

#### 2. Get Issue Details (`get_jira_issue_details`)
Retrieve comprehensive information for a specific JIRA issue by its key (e.g., 'SMQE-1280'), including:
- Basic issue information (summary, description, status, priority)
- Timestamps (created, updated, due date, resolution date)
- Time tracking (original estimate, current estimate, time spent)
- Metadata (votes, watches, environment, components)
- Associated labels
- Comments (with comment body, creation/update timestamps, and role level)

#### 3. Get Project Summary (`get_jira_project_summary`)
Generate statistics across all projects:
- Total issue counts per project
- Status distribution per project
- Priority distribution per project
- Overall statistics

#### 4. List Components (`list_jira_components`)
Query and filter JIRA components with optional criteria:
- **Project filtering** - Filter by project ID (e.g., '12325621')
- **Archived filtering** - Filter by archived status ('Y' or 'N')
- **Deleted filtering** - Filter by deleted status ('Y' or 'N')
- **Text search** - Search in component name and description fields
- **Result limiting** - Control number of results returned (default: 50)

Returns component information including:
- Component ID, project, name, and description
- Component URL and assignee details
- Archived and deleted status
- Lead information and assignee type
- Last sync timestamp

### Monitoring & Metrics

The server includes optional Prometheus metrics support for monitoring:
- **Tool usage tracking** - Track calls to each MCP tool with success/error rates and duration
- **Snowflake query monitoring** - Monitor database query performance and success rates
- **Connection tracking** - Track active MCP connections
- **HTTP endpoints** - `/metrics` for Prometheus scraping and `/health` for health checks

## Prerequisites

- Python 3.10+
- [UV](https://docs.astral.sh/uv/) (Python package manager)
- Podman or Docker
- Access to Snowflake with appropriate credentials

## Architecture

The codebase is organized into modular components in the `src/` directory:

- **`src/mcp_server.py`** - Main server entry point and MCP initialization
- **`src/config.py`** - Configuration management and environment variable handling  
- **`src/database.py`** - Snowflake database connection and query execution
- **`src/tools.py`** - MCP tool implementations and business logic
- **`src/metrics.py`** - Optional Prometheus metrics collection and HTTP server

## Environment Variables

The following environment variables are used to configure the Snowflake connection:

### Required
- **`SNOWFLAKE_TOKEN`** - Your Snowflake authentication token (Bearer token)
- **`SNOWFLAKE_BASE_URL`** - Snowflake API base URL (e.g., `https://your-account.snowflakecomputing.com/api/v2`)
- **`SNOWFLAKE_DATABASE`** - Snowflake database name containing your JIRA data
- **`SNOWFLAKE_SCHEMA`** - Snowflake schema name containing your JIRA tables

### Optional
- **`MCP_TRANSPORT`** - Transport protocol for MCP communication  
  - Default: `stdio`
- **`ENABLE_METRICS`** - Enable Prometheus metrics collection  
  - Default: `false`
- **`METRICS_PORT`** - Port for metrics HTTP server  
  - Default: `8000`


## Installation & Setup

### Migration from pip to UV

This project has been updated to use UV for dependency management. If you have an existing setup:

1. Remove your old virtual environment:
   ```bash
   rm -rf venv/
   ```

2. Install UV if you haven't already (see Local Development section below)

3. Install dependencies with UV:
   ```bash
   uv sync
   ```

### Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd jira-mcp-snowflake
```

2. Install UV if you haven't already:
```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip
pip install uv
```

3. Install dependencies:
```bash
uv sync
```

4. Set up environment variables (see Environment Variables section above)

5. Run the server:
```bash
uv run python src/mcp_server.py
```

### Using Makefile Targets

For convenience, several Makefile targets are available to streamline development tasks:

#### Development Setup
```bash
# Install dependencies including dev packages
make uv_sync_dev
```

#### Testing and Quality Assurance
```bash
# Run linting (flake8)
make lint

# Run tests with coverage
make pytest

# Run both linting and tests
make test
```

#### Building
```bash
# Build container image with Podman
make build
```

**Note**: On macOS, you may need to install a newer version of make via Homebrew:
```bash
brew install make
```

### Container Deployment

## Building locally

To build the container image locally using Podman, run:

```sh
podman build -t localhost/jira-mcp-snowflake:latest .
```

This will create a local image named `jira-mcp-snowflake:latest` that you can use to run the server. The container now uses UV for fast dependency management.

## Running with Podman or Docker

Example configuration for running with Podman:

```json
{
  "mcpServers": {
    "jira-mcp-snowflake": {
      "command": "podman",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "SNOWFLAKE_TOKEN=your_token_here",
        "-e", "SNOWFLAKE_BASE_URL=https://your-account.snowflakecomputing.com/api/v2",
        "-e", "SNOWFLAKE_DATABASE=your_database_name",
        "-e", "SNOWFLAKE_SCHEMA=your_schema_name",
        "-e", "MCP_TRANSPORT=stdio",
        "-e", "ENABLE_METRICS=true",
        "-e", "METRICS_PORT=8000",
        "localhost/jira-mcp-snowflake:latest"
      ]
    }
  }
}
```

Then access metrics at: `http://localhost:8000/metrics`

## Connecting to a remote instance

Example configuration for connecting to a remote instance:

```json
{
  "mcpServers": {
    "jira-mcp-snowflake": {
      "url": "https://jira-mcp-snowflake.example.com/sse",
      "headers": {
        "X-Snowflake-Token": "your_token_here"
      }
    }
  }
}
```

### VS Code Continue Integration

Example configuration to add to VS Code Continue:

```json
{
  "experimental": {
    "modelContextProtocolServers": [
      {
        "name": "jira-mcp-snowflake",
        "transport": {
          "type": "stdio",
          "command": "podman",
          "args": [
            "run",
            "-i",
            "--rm",
            "-e", "SNOWFLAKE_TOKEN=your_token_here",
            "-e", "SNOWFLAKE_BASE_URL=https://your-account.snowflakecomputing.com/api/v2",
            "-e", "SNOWFLAKE_DATABASE=your_database_name",
            "-e", "SNOWFLAKE_SCHEMA=your_schema_name",
            "-e", "MCP_TRANSPORT=stdio",
            "-e", "ENABLE_METRICS=true",
            "-e", "METRICS_PORT=8000",
            "localhost/jira-mcp-snowflake:latest"
          ]
        }
      }
    ]
  }
}
```

## Usage Examples

### Query Issues by Project
```python
# List all issues from the SMQE project
result = await list_jira_issues(project="SMQE", limit=10)
```

### Search Issues by Text
```python
# Search for issues containing "authentication" in summary or description
result = await list_jira_issues(search_text="authentication", limit=20)
```

### Get Specific Issue Details
```python
# Get detailed information for a specific issue
result = await get_jira_issue_details(issue_key="SMQE-1280")
```

### Get Project Overview
```python
# Get statistics for all projects
result = await get_jira_project_summary()
```

## Monitoring

When metrics are enabled, the server provides the following monitoring endpoints:

- **`/metrics`** - Prometheus metrics endpoint for scraping
- **`/health`** - Health check endpoint returning JSON status

### Available Metrics

- `mcp_tool_calls_total` - Counter of tool calls by tool name and status
- `mcp_tool_call_duration_seconds` - Histogram of tool call durations
- `mcp_active_connections` - Gauge of active MCP connections
- `mcp_snowflake_queries_total` - Counter of Snowflake queries by status
- `mcp_snowflake_query_duration_seconds` - Histogram of Snowflake query durations

## Data Privacy

This server is designed to work with non-personally identifiable information (non-PII) data only. The Snowflake tables should contain sanitized data with any sensitive personal information removed.

## Security Considerations

- **Environment Variables**: Store sensitive information like `SNOWFLAKE_TOKEN` in environment variables, never in code
- **Token Security**: Ensure your Snowflake token is kept secure and rotated regularly
- **Network Security**: Use HTTPS endpoints and secure network connections
- **Access Control**: Follow principle of least privilege for Snowflake database access
- **SQL Injection Prevention**: The server includes input sanitization to prevent SQL injection attacks

## Dependencies

- `httpx` - HTTP client library for Snowflake API communication
- `fastmcp` - Fast MCP server framework
- `prometheus_client` - Prometheus metrics client (optional, for monitoring)

## Development

### Code Structure

The project follows a modular architecture:

```
jira-mcp-snowflake/
├── src/
│   ├── mcp_server.py      # Main entry point
│   ├── config.py          # Configuration and environment variables
│   ├── database.py        # Snowflake database operations
│   ├── tools.py           # MCP tool implementations
│   └── metrics.py         # Prometheus metrics (optional)
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

### Adding New Tools

To add new MCP tools:

1. Add the tool function to `src/tools.py`
2. Decorate with `@mcp.tool()` and `@track_tool_usage("tool_name")`
3. Follow the existing patterns for error handling and logging
4. Update this README with documentation for the new tool

