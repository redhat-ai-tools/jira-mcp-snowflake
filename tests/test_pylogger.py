"""Tests for pylogger utility module."""

import logging
from unittest.mock import MagicMock, patch


class TestPyLogger:
    """Test cases for pylogger utility functions."""

    def test_get_python_logger_default(self):
        """Test getting logger with default level."""
        from jira_mcp_snowflake.utils.pylogger import get_python_logger

        logger = get_python_logger()

        assert isinstance(logger, logging.Logger)
        assert logger.name == "jira_mcp_snowflake"

    def test_get_python_logger_with_level(self):
        """Test getting logger with specific level."""
        from jira_mcp_snowflake.utils.pylogger import get_python_logger

        logger = get_python_logger("DEBUG")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "jira_mcp_snowflake"

    def test_get_python_logger_with_name(self):
        """Test getting logger with custom name."""
        from jira_mcp_snowflake.utils.pylogger import get_python_logger

        logger = get_python_logger(name="custom_logger")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "custom_logger"

    def test_get_python_logger_different_levels(self):
        """Test getting logger with different log levels."""
        from jira_mcp_snowflake.utils.pylogger import get_python_logger

        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in levels:
            logger = get_python_logger(level)
            assert isinstance(logger, logging.Logger)

    @patch('jira_mcp_snowflake.utils.pylogger.logging.getLogger')
    def test_get_python_logger_calls_getlogger(self, mock_getlogger):
        """Test that get_python_logger calls logging.getLogger."""
        mock_logger = MagicMock()
        mock_getlogger.return_value = mock_logger

        from jira_mcp_snowflake.utils.pylogger import get_python_logger

        result = get_python_logger("INFO", "test_logger")

        mock_getlogger.assert_called_once_with("test_logger")
        assert result == mock_logger

    def test_force_reconfigure_all_loggers_info(self):
        """Test force reconfigure with INFO level."""
        from jira_mcp_snowflake.utils.pylogger import force_reconfigure_all_loggers

        # Should not raise any exceptions
        force_reconfigure_all_loggers("INFO")

    def test_force_reconfigure_all_loggers_debug(self):
        """Test force reconfigure with DEBUG level."""
        from jira_mcp_snowflake.utils.pylogger import force_reconfigure_all_loggers

        # Should not raise any exceptions
        force_reconfigure_all_loggers("DEBUG")

    def test_force_reconfigure_all_loggers_warning(self):
        """Test force reconfigure with WARNING level."""
        from jira_mcp_snowflake.utils.pylogger import force_reconfigure_all_loggers

        # Should not raise any exceptions
        force_reconfigure_all_loggers("WARNING")

    def test_force_reconfigure_all_loggers_error(self):
        """Test force reconfigure with ERROR level."""
        from jira_mcp_snowflake.utils.pylogger import force_reconfigure_all_loggers

        # Should not raise any exceptions
        force_reconfigure_all_loggers("ERROR")

    def test_force_reconfigure_all_loggers_critical(self):
        """Test force reconfigure with CRITICAL level."""
        from jira_mcp_snowflake.utils.pylogger import force_reconfigure_all_loggers

        # Should not raise any exceptions
        force_reconfigure_all_loggers("CRITICAL")

    @patch('jira_mcp_snowflake.utils.pylogger.logging.basicConfig')
    @patch('jira_mcp_snowflake.utils.pylogger.logging.getLogger')
    def test_force_reconfigure_clears_handlers(self, mock_getlogger, mock_basicconfig):
        """Test that force reconfigure clears existing handlers."""
        # Mock root logger with existing handlers
        mock_root_logger = MagicMock()
        mock_handler1 = MagicMock()
        mock_handler2 = MagicMock()
        mock_root_logger.handlers = [mock_handler1, mock_handler2]
        mock_getlogger.return_value = mock_root_logger

        from jira_mcp_snowflake.utils.pylogger import force_reconfigure_all_loggers

        force_reconfigure_all_loggers("INFO")

        # Verify handlers were closed and cleared
        mock_handler1.close.assert_called_once()
        mock_handler2.close.assert_called_once()
        assert mock_root_logger.handlers == []

        # Verify basicConfig was called
        mock_basicconfig.assert_called_once()

    @patch('jira_mcp_snowflake.utils.pylogger.logging.basicConfig')
    @patch('jira_mcp_snowflake.utils.pylogger.logging.getLogger')
    def test_force_reconfigure_calls_basicconfig(self, mock_getlogger, mock_basicconfig):
        """Test that force reconfigure calls logging.basicConfig."""
        mock_root_logger = MagicMock()
        mock_root_logger.handlers = []
        mock_getlogger.return_value = mock_root_logger

        from jira_mcp_snowflake.utils.pylogger import force_reconfigure_all_loggers

        force_reconfigure_all_loggers("DEBUG")

        # Verify basicConfig was called with correct parameters
        mock_basicconfig.assert_called_once()
        call_args = mock_basicconfig.call_args
        assert 'level' in call_args[1]
        assert 'format' in call_args[1]
        assert 'handlers' in call_args[1]

    @patch('jira_mcp_snowflake.utils.pylogger.logging.basicConfig')
    @patch('jira_mcp_snowflake.utils.pylogger.logging.getLogger')
    def test_force_reconfigure_with_invalid_level(self, mock_getlogger, mock_basicconfig):
        """Test force reconfigure with invalid log level."""
        mock_root_logger = MagicMock()
        mock_root_logger.handlers = []
        mock_getlogger.return_value = mock_root_logger

        from jira_mcp_snowflake.utils.pylogger import force_reconfigure_all_loggers

        # Should handle invalid level gracefully
        force_reconfigure_all_loggers("INVALID")

        # Should still call basicConfig
        mock_basicconfig.assert_called_once()

    def test_logger_integration(self):
        """Test integration between functions."""
        from jira_mcp_snowflake.utils.pylogger import (
            force_reconfigure_all_loggers,
            get_python_logger,
        )

        # Reconfigure first
        force_reconfigure_all_loggers("INFO")

        # Then get logger
        logger = get_python_logger("DEBUG", "integration_test")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "integration_test"

    def test_multiple_logger_instances(self):
        """Test getting multiple logger instances."""
        from jira_mcp_snowflake.utils.pylogger import get_python_logger

        logger1 = get_python_logger("INFO", "logger1")
        logger2 = get_python_logger("DEBUG", "logger2")
        logger3 = get_python_logger("WARNING", "logger1")  # Same name as logger1

        assert logger1.name == "logger1"
        assert logger2.name == "logger2"
        assert logger3.name == "logger1"

        # Same name should return same logger instance
        assert logger1 is logger3

    @patch('jira_mcp_snowflake.utils.pylogger.structlog')
    def test_force_reconfigure_with_structlog(self, mock_structlog):
        """Test force reconfigure with structlog configuration."""
        from jira_mcp_snowflake.utils.pylogger import force_reconfigure_all_loggers

        force_reconfigure_all_loggers("INFO")

        # Should configure structlog
        mock_structlog.configure.assert_called_once()

    def test_logger_name_defaults(self):
        """Test logger name defaults."""
        from jira_mcp_snowflake.utils.pylogger import get_python_logger

        # Test default name
        logger1 = get_python_logger()
        assert logger1.name == "jira_mcp_snowflake"

        # Test with just level
        logger2 = get_python_logger("DEBUG")
        assert logger2.name == "jira_mcp_snowflake"

        # Test with level and name
        logger3 = get_python_logger("INFO", "custom")
        assert logger3.name == "custom"
