"""Tests for RAG classification."""

from datetime import datetime, timedelta
import pytest

from jira_mcp_server.config import RAGConfig
from jira_mcp_server.models import Issue, IssueStatus, IssueType, User, RAGStatus
from jira_mcp_server.rag_classifier import RAGClassifier, RAGClassificationResult


class TestRAGClassifier:
    """Test RAG classifier functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test RAG configuration."""
        return RAGConfig(
            green_max_days_in_status=3,
            yellow_max_days_in_status=7,
            red_priority_levels=["Highest", "High"],
            blocked_statuses=["Blocked", "Waiting"]
        )
    
    @pytest.fixture
    def classifier(self, config):
        """Create RAG classifier instance."""
        return RAGClassifier(config)
    
    @pytest.fixture
    def sample_issue(self):
        """Create a sample issue for testing."""
        return Issue(
            key="TEST-123",
            summary="Test issue",
            status=IssueStatus(id="1", name="In Progress", category="indeterminate"),
            issue_type=IssueType(id="1", name="Story"),
            priority="Medium",
            assignee=User(account_id="user1", display_name="Test User"),
            reporter=User(account_id="user2", display_name="Reporter User"),
            created=datetime.now() - timedelta(days=5),
            updated=datetime.now() - timedelta(days=2),
            labels=[],
            components=[],
            blockers=[],
            days_in_status=2,
            is_blocked=False,
            url="https://test.jira.com/browse/TEST-123"
        )
    
    def test_green_classification(self, classifier, sample_issue):
        """Test green classification for normal issues."""
        sample_issue.days_in_status = 2  # Within green threshold
        sample_issue.priority = "Medium"
        
        result = classifier.classify_issue(sample_issue)
        
        assert result.status == RAGStatus.GREEN
        assert "progressing normally" in result.reason.lower()
    
    def test_amber_classification_days_in_status(self, classifier, sample_issue):
        """Test amber classification for issues with longer status time."""
        sample_issue.days_in_status = 5  # Between green and yellow thresholds
        sample_issue.priority = "Medium"
        
        result = classifier.classify_issue(sample_issue)
        
        assert result.status == RAGStatus.AMBER
        assert "days" in result.reason.lower()
    
    def test_amber_classification_high_priority(self, classifier, sample_issue):
        """Test amber classification for high priority issues."""
        sample_issue.days_in_status = 2
        sample_issue.priority = "High"
        
        result = classifier.classify_issue(sample_issue)
        
        assert result.status == RAGStatus.AMBER
        assert "high priority" in result.reason.lower()
    
    def test_red_classification_blocked_status(self, classifier, sample_issue):
        """Test red classification for blocked issues."""
        sample_issue.status.name = "Blocked"
        sample_issue.is_blocked = True
        
        result = classifier.classify_issue(sample_issue)
        
        assert result.status == RAGStatus.RED
        assert "blocked" in result.reason.lower()
    
    def test_red_classification_high_priority_overdue(self, classifier, sample_issue):
        """Test red classification for overdue high priority issues."""
        sample_issue.priority = "Highest"
        sample_issue.days_in_status = 10  # Over yellow threshold
        
        result = classifier.classify_issue(sample_issue)
        
        assert result.status == RAGStatus.RED
        assert "high priority" in result.reason.lower()
        assert "days" in result.reason.lower()
    
    def test_red_classification_with_blockers(self, classifier, sample_issue):
        """Test red classification for issues with blockers."""
        sample_issue.blockers = ["BLOCK-1", "BLOCK-2"]
        
        result = classifier.classify_issue(sample_issue)
        
        assert result.status == RAGStatus.RED
        assert "blocking dependencies" in result.reason.lower()
    
    def test_amber_classification_unassigned(self, classifier, sample_issue):
        """Test amber classification for unassigned issues."""
        sample_issue.assignee = None
        sample_issue.days_in_status = 5
        
        result = classifier.classify_issue(sample_issue)
        
        assert result.status == RAGStatus.AMBER
        assert "unassigned" in result.reason.lower()
    
    def test_batch_classification(self, classifier):
        """Test batch classification of multiple issues."""
        issues = []
        
        # Create issues with different conditions
        for i in range(3):
            issue = Issue(
                key=f"TEST-{i}",
                summary=f"Test issue {i}",
                status=IssueStatus(id=str(i), name="In Progress", category="indeterminate"),
                issue_type=IssueType(id=str(i), name="Story"),
                priority="Medium",
                assignee=User(account_id=f"user{i}", display_name=f"User {i}"),
                reporter=User(account_id="reporter", display_name="Reporter"),
                created=datetime.now() - timedelta(days=5),
                updated=datetime.now() - timedelta(days=i+1),
                labels=[],
                components=[],
                blockers=[],
                days_in_status=i+1,
                is_blocked=False,
                url=f"https://test.jira.com/browse/TEST-{i}"
            )
            issues.append(issue)
        
        # Set specific conditions
        issues[0].days_in_status = 1  # Green
        issues[1].days_in_status = 5  # Amber
        issues[2].priority = "Highest"
        issues[2].days_in_status = 10  # Red
        
        results = classifier.classify_issues_batch(issues)
        
        assert len(results) == 3
        assert results["TEST-0"].status == RAGStatus.GREEN
        assert results["TEST-1"].status == RAGStatus.AMBER
        assert results["TEST-2"].status == RAGStatus.RED
        
        # Check that issues were updated
        assert issues[0].rag_status == RAGStatus.GREEN
        assert issues[1].rag_status == RAGStatus.AMBER
        assert issues[2].rag_status == RAGStatus.RED
    
    def test_rag_summary(self, classifier):
        """Test RAG summary generation."""
        issues = []
        
        # Create issues with known RAG statuses
        for i, rag_status in enumerate([RAGStatus.GREEN, RAGStatus.AMBER, RAGStatus.RED]):
            issue = Issue(
                key=f"TEST-{i}",
                summary=f"Test issue {i}",
                status=IssueStatus(id=str(i), name="In Progress", category="indeterminate"),
                issue_type=IssueType(id=str(i), name="Story"),
                priority="Medium",
                assignee=User(account_id=f"user{i}", display_name=f"User {i}"),
                reporter=User(account_id="reporter", display_name="Reporter"),
                created=datetime.now(),
                updated=datetime.now(),
                labels=[],
                components=[],
                blockers=[],
                days_in_status=1,
                is_blocked=False,
                url=f"https://test.jira.com/browse/TEST-{i}",
                rag_status=rag_status
            )
            issues.append(issue)
        
        summary = classifier.get_rag_summary(issues)
        
        assert summary["total"] == 3
        assert summary["green"] == 1
        assert summary["amber"] == 1
        assert summary["red"] == 1
        assert summary["unclassified"] == 0
    
    def test_overall_status_calculation(self, classifier):
        """Test overall RAG status calculation."""
        # Test with red issues
        red_issues = [
            self._create_test_issue("TEST-1", RAGStatus.RED),
            self._create_test_issue("TEST-2", RAGStatus.GREEN)
        ]
        assert classifier.get_overall_status(red_issues) == RAGStatus.RED
        
        # Test with many amber issues
        amber_heavy_issues = [
            self._create_test_issue("TEST-1", RAGStatus.AMBER),
            self._create_test_issue("TEST-2", RAGStatus.AMBER),
            self._create_test_issue("TEST-3", RAGStatus.GREEN)
        ]
        assert classifier.get_overall_status(amber_heavy_issues) == RAGStatus.AMBER
        
        # Test with mostly green issues
        green_issues = [
            self._create_test_issue("TEST-1", RAGStatus.GREEN),
            self._create_test_issue("TEST-2", RAGStatus.GREEN),
            self._create_test_issue("TEST-3", RAGStatus.AMBER)
        ]
        assert classifier.get_overall_status(green_issues) == RAGStatus.GREEN
    
    def _create_test_issue(self, key: str, rag_status: RAGStatus) -> Issue:
        """Helper to create test issue with specific RAG status."""
        return Issue(
            key=key,
            summary="Test issue",
            status=IssueStatus(id="1", name="In Progress", category="indeterminate"),
            issue_type=IssueType(id="1", name="Story"),
            priority="Medium",
            assignee=User(account_id="user", display_name="User"),
            reporter=User(account_id="reporter", display_name="Reporter"),
            created=datetime.now(),
            updated=datetime.now(),
            labels=[],
            components=[],
            blockers=[],
            days_in_status=1,
            is_blocked=False,
            url=f"https://test.jira.com/browse/{key}",
            rag_status=rag_status
        )