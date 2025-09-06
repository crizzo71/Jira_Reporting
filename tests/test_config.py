"""Tests for configuration management."""

import os
import pytest
from unittest.mock import patch

from jira_mcp_server.config import Config, JiraConfig, RAGConfig, get_config


class TestJiraConfig:
    """Test Jira configuration."""
    
    def test_valid_config(self):
        """Test valid Jira configuration."""
        config = JiraConfig(
            server="https://issues.redhat.com",
            email="test@redhat.com",
            api_token="test-token"
        )
        
        assert config.server == "https://issues.redhat.com"
        assert config.email == "test@redhat.com"
        assert config.api_token == "test-token"
    
    def test_server_url_validation(self):
        """Test server URL validation."""
        with pytest.raises(ValueError, match="Server URL must start with"):
            JiraConfig(
                server="invalid-url",
                email="test@redhat.com",
                api_token="test-token"
            )
    
    def test_server_url_normalization(self):
        """Test server URL normalization."""
        config = JiraConfig(
            server="https://issues.redhat.com/",
            email="test@redhat.com",
            api_token="test-token"
        )
        
        assert config.server == "https://issues.redhat.com"


class TestRAGConfig:
    """Test RAG configuration."""
    
    def test_default_config(self):
        """Test default RAG configuration."""
        config = RAGConfig()
        
        assert config.green_max_days_in_status == 3
        assert config.yellow_max_days_in_status == 7
        assert "Highest" in config.red_priority_levels
        assert "Blocked" in config.blocked_statuses
    
    def test_custom_config(self):
        """Test custom RAG configuration."""
        config = RAGConfig(
            green_max_days_in_status=5,
            yellow_max_days_in_status=10,
            red_priority_levels=["Critical"],
            blocked_statuses=["Stopped"]
        )
        
        assert config.green_max_days_in_status == 5
        assert config.yellow_max_days_in_status == 10
        assert config.red_priority_levels == ["Critical"]
        assert config.blocked_statuses == ["Stopped"]


class TestConfig:
    """Test main configuration."""
    
    @patch.dict(os.environ, {
        'JIRA_SERVER': 'https://test.jira.com',
        'JIRA_EMAIL': 'test@example.com',
        'JIRA_API_TOKEN': 'test-token-123',
        'LOG_LEVEL': 'DEBUG'
    })
    def test_from_env(self):
        """Test configuration from environment variables."""
        config = Config.from_env()
        
        assert config.jira.server == "https://test.jira.com"
        assert config.jira.email == "test@example.com"
        assert config.jira.api_token == "test-token-123"
        assert config.log_level == "DEBUG"
    
    def test_validation_missing_jira_config(self):
        """Test validation with missing Jira configuration."""
        config = Config(
            jira=JiraConfig(server="", email="", api_token="")
        )
        
        with pytest.raises(ValueError, match="Jira configuration is incomplete"):
            config.validate()
    
    @patch.dict(os.environ, {
        'JIRA_SERVER': 'https://test.jira.com',
        'JIRA_EMAIL': 'test@example.com',
        'JIRA_API_TOKEN': 'test-token-123'
    })
    def test_get_config(self):
        """Test get_config function."""
        config = get_config()
        
        assert isinstance(config, Config)
        assert config.jira.server == "https://test.jira.com"