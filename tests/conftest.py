"""Pytest configuration and shared fixtures."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from jira_mcp_server.config import Config, JiraConfig, RAGConfig, ReportConfig, MCPConfig
from jira_mcp_server.models import Issue, IssueStatus, IssueType, User, RAGStatus


@pytest.fixture
def test_config():
    """Create test configuration."""
    return Config(
        jira=JiraConfig(
            server="https://test.jira.com",
            email="test@example.com",
            api_token="test-token"
        ),
        rag=RAGConfig(),
        report=ReportConfig(),
        mcp=MCPConfig(),
        log_level="DEBUG"
    )


@pytest.fixture
def sample_user():
    """Create a sample user."""
    return User(
        account_id="user123",
        display_name="Test User",
        email_address="test.user@example.com"
    )


@pytest.fixture
def sample_issue_status():
    """Create a sample issue status."""
    return IssueStatus(
        id="10001",
        name="In Progress",
        category="indeterminate"
    )


@pytest.fixture
def sample_issue_type():
    """Create a sample issue type."""
    return IssueType(
        id="10001",
        name="Story",
        icon_url="https://test.jira.com/icon.png"
    )


@pytest.fixture
def sample_issue(sample_user, sample_issue_status, sample_issue_type):
    """Create a sample issue for testing."""
    return Issue(
        key="TEST-123",
        summary="Sample test issue for unit tests",
        description="This is a test issue used in unit tests",
        status=sample_issue_status,
        issue_type=sample_issue_type,
        priority="Medium",
        assignee=sample_user,
        reporter=sample_user,
        created=datetime.now() - timedelta(days=5),
        updated=datetime.now() - timedelta(days=1),
        resolved=None,
        labels=["test", "unit-test"],
        components=["Backend"],
        blockers=[],
        story_points=5.0,
        sprint="Sprint 23",
        days_in_status=3,
        is_blocked=False,
        url="https://test.jira.com/browse/TEST-123"
    )


@pytest.fixture
def mock_jira_client():
    """Create a mock Jira client."""
    client = Mock()
    client.authenticate = AsyncMock()
    client.get_projects = AsyncMock(return_value=[])
    client.get_boards = AsyncMock(return_value=[])
    client.get_issues = AsyncMock(return_value=[])
    client.get_status_transitions = AsyncMock(return_value=[])
    return client


@pytest.fixture
def issues_with_different_rag_status(sample_user, sample_issue_status, sample_issue_type):
    """Create issues with different RAG statuses for testing."""
    base_issue_data = {
        "description": "Test issue",
        "status": sample_issue_status,
        "issue_type": sample_issue_type,
        "assignee": sample_user,
        "reporter": sample_user,
        "created": datetime.now() - timedelta(days=5),
        "updated": datetime.now() - timedelta(days=1),
        "labels": [],
        "components": [],
        "blockers": [],
        "is_blocked": False
    }
    
    return [
        Issue(
            key="GREEN-1",
            summary="Green issue",
            priority="Low",
            days_in_status=1,
            rag_status=RAGStatus.GREEN,
            url="https://test.jira.com/browse/GREEN-1",
            **base_issue_data
        ),
        Issue(
            key="AMBER-1",
            summary="Amber issue",
            priority="Medium",
            days_in_status=5,
            rag_status=RAGStatus.AMBER,
            url="https://test.jira.com/browse/AMBER-1",
            **base_issue_data
        ),
        Issue(
            key="RED-1",
            summary="Red issue",
            priority="High",
            days_in_status=10,
            is_blocked=True,
            rag_status=RAGStatus.RED,
            url="https://test.jira.com/browse/RED-1",
            **base_issue_data
        )
    ]