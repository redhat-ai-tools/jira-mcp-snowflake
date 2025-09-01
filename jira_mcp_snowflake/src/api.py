"""This module sets up the FastAPI application for the JIRA MCP Snowflake server.

It initializes the FastAPI app and sets up the MCP server with appropriate
transport protocols.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from jira_mcp_snowflake.src.mcp import JiraMCPSnowflakeServer
from jira_mcp_snowflake.src.settings import settings
from jira_mcp_snowflake.utils.pylogger import get_python_logger

logger = get_python_logger(settings.PYTHON_LOG_LEVEL)

server = JiraMCPSnowflakeServer()

# Create the MCP HTTP app
mcp_app = server.mcp.http_app(path="/mcp")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan handler for the FastAPI application."""
    logger.info("Starting JIRA MCP Snowflake server")

    # Run MCP lifespan
    async with mcp_app.lifespan(app):
        logger.info("Server is ready to accept connections")
        yield

    logger.info("Shutting down JIRA MCP Snowflake server")


# Create FastAPI app
app = FastAPI(lifespan=lifespan, title="JIRA MCP Snowflake Server")


@app.get("/health")
async def health_check():
    """Health check endpoint for the MCP server."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "jira-mcp-snowflake",
            "transport_protocol": settings.MCP_TRANSPORT,
            "version": "0.1.0",
        },
    )


# Mount the MCP app
app.mount("/", mcp_app)
