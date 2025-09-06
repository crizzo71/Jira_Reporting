"""RAG (Red/Amber/Green) status classifier for Jira issues."""

from datetime import datetime, timedelta
from typing import NamedTuple
import logging

from .config import RAGConfig
from .models import Issue, RAGStatus

logger = logging.getLogger(__name__)


class RAGClassificationResult(NamedTuple):
    """Result of RAG classification."""
    status: RAGStatus
    reason: str
    confidence: float = 1.0


class RAGClassifier:
    """Classifier for assigning RAG status to Jira issues."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
    
    def classify_issue(self, issue: Issue) -> RAGClassificationResult:
        """
        Classify an issue into Red, Amber, or Green status.
        
        Classification rules:
        - Red: Blocked issues, high priority with long delays, or critical blockers
        - Amber: Issues with elevated risk, date changes, or moderate concerns
        - Green: Issues progressing as expected
        """
        
        # Check for explicit blocking conditions (highest priority)
        red_result = self._check_red_conditions(issue)
        if red_result:
            return red_result
        
        # Check for amber/yellow conditions
        amber_result = self._check_amber_conditions(issue)
        if amber_result:
            return amber_result
        
        # Default to green if no concerning conditions
        return RAGClassificationResult(
            status=RAGStatus.GREEN,
            reason="Issue is progressing normally with no identified risks"
        )
    
    def _check_red_conditions(self, issue: Issue) -> RAGClassificationResult | None:
        """Check for conditions that warrant Red status."""
        
        # Explicitly blocked issues
        if issue.is_blocked or any(status in issue.status.name.lower() 
                                 for status in [s.lower() for s in self.config.blocked_statuses]):
            return RAGClassificationResult(
                status=RAGStatus.RED,
                reason=f"Issue is in blocked status: {issue.status.name}"
            )
        
        # High priority issues that have been in status too long
        if (issue.priority in self.config.red_priority_levels and 
            issue.days_in_status is not None and 
            issue.days_in_status > self.config.yellow_max_days_in_status):
            return RAGClassificationResult(
                status=RAGStatus.RED,
                reason=f"High priority issue ({issue.priority}) has been in {issue.status.name} for {issue.days_in_status} days"
            )
        
        # Issues with blocker links
        if issue.blockers:
            return RAGClassificationResult(
                status=RAGStatus.RED,
                reason=f"Issue has {len(issue.blockers)} blocking dependencies"
            )
        
        # Check for critical labels that indicate problems
        critical_labels = ['critical-blocker', 'production-issue', 'escalated']
        found_critical_labels = [label for label in issue.labels 
                               if any(critical in label.lower() for critical in critical_labels)]
        if found_critical_labels:
            return RAGClassificationResult(
                status=RAGStatus.RED,
                reason=f"Issue has critical labels: {', '.join(found_critical_labels)}"
            )
        
        return None
    
    def _check_amber_conditions(self, issue: Issue) -> RAGClassificationResult | None:
        """Check for conditions that warrant Amber/Yellow status."""
        
        # Issues that have been in status longer than green threshold
        if (issue.days_in_status is not None and 
            issue.days_in_status > self.config.green_max_days_in_status):
            
            if issue.days_in_status <= self.config.yellow_max_days_in_status:
                return RAGClassificationResult(
                    status=RAGStatus.AMBER,
                    reason=f"Issue has been in {issue.status.name} for {issue.days_in_status} days"
                )
        
        # High priority issues (even if not overdue)
        if issue.priority in self.config.red_priority_levels:
            return RAGClassificationResult(
                status=RAGStatus.AMBER,
                reason=f"High priority issue ({issue.priority}) requires close monitoring"
            )
        
        # Issues with risk-related labels
        risk_labels = ['risk', 'concern', 'dependency', 'delayed']
        found_risk_labels = [label for label in issue.labels 
                           if any(risk in label.lower() for risk in risk_labels)]
        if found_risk_labels:
            return RAGClassificationResult(
                status=RAGStatus.AMBER,
                reason=f"Issue has risk-related labels: {', '.join(found_risk_labels)}"
            )
        
        # Issues without assignee for too long
        if (not issue.assignee and 
            issue.days_in_status is not None and 
            issue.days_in_status > self.config.green_max_days_in_status):
            return RAGClassificationResult(
                status=RAGStatus.AMBER,
                reason=f"Unassigned issue has been in {issue.status.name} for {issue.days_in_status} days"
            )
        
        # Check for issues in development statuses that might be stalled
        development_statuses = ['in progress', 'development', 'coding', 'implementation']
        if (any(dev_status in issue.status.name.lower() for dev_status in development_statuses) and
            issue.days_in_status is not None and 
            issue.days_in_status > self.config.green_max_days_in_status):
            return RAGClassificationResult(
                status=RAGStatus.AMBER,
                reason=f"Development issue has been in progress for {issue.days_in_status} days"
            )
        
        return None
    
    def classify_issues_batch(self, issues: list[Issue]) -> dict[str, RAGClassificationResult]:
        """Classify multiple issues and return results keyed by issue key."""
        results = {}
        
        for issue in issues:
            try:
                result = self.classify_issue(issue)
                results[issue.key] = result
                
                # Update issue object with classification
                issue.rag_status = result.status
                issue.rag_reason = result.reason
                
            except Exception as e:
                logger.error(f"Error classifying issue {issue.key}: {e}")
                # Default to amber with error reason
                error_result = RAGClassificationResult(
                    status=RAGStatus.AMBER,
                    reason=f"Classification error: {str(e)}",
                    confidence=0.0
                )
                results[issue.key] = error_result
                issue.rag_status = error_result.status
                issue.rag_reason = error_result.reason
        
        return results
    
    def get_rag_summary(self, issues: list[Issue]) -> dict[str, int]:
        """Get summary counts of RAG classifications."""
        summary = {
            "total": len(issues),
            "green": 0,
            "amber": 0,
            "red": 0,
            "unclassified": 0
        }
        
        for issue in issues:
            if issue.rag_status == RAGStatus.GREEN:
                summary["green"] += 1
            elif issue.rag_status == RAGStatus.AMBER:
                summary["amber"] += 1
            elif issue.rag_status == RAGStatus.RED:
                summary["red"] += 1
            else:
                summary["unclassified"] += 1
        
        return summary
    
    def get_overall_status(self, issues: list[Issue]) -> RAGStatus:
        """Determine overall RAG status for a collection of issues."""
        if not issues:
            return RAGStatus.GREEN
        
        summary = self.get_rag_summary(issues)
        
        # If any red issues, overall is red
        if summary["red"] > 0:
            return RAGStatus.RED
        
        # If more than 20% amber issues, overall is amber
        amber_percentage = summary["amber"] / summary["total"] if summary["total"] > 0 else 0
        if amber_percentage > 0.2:
            return RAGStatus.AMBER
        
        # Otherwise green
        return RAGStatus.GREEN
    
    def explain_classification_rules(self) -> dict[str, str]:
        """Return explanation of current classification rules."""
        return {
            "RED": (
                f"Issues that are blocked, have blocker dependencies, "
                f"high priority ({', '.join(self.config.red_priority_levels)}) issues "
                f"in status > {self.config.yellow_max_days_in_status} days, "
                f"or have critical labels"
            ),
            "AMBER": (
                f"Issues in status > {self.config.green_max_days_in_status} days, "
                f"high priority issues, unassigned issues > {self.config.green_max_days_in_status} days, "
                f"or issues with risk-related labels"
            ),
            "GREEN": (
                f"Issues progressing normally, in status ≤ {self.config.green_max_days_in_status} days "
                f"with no identified risks"
            ),
            "Configuration": {
                "Green max days": self.config.green_max_days_in_status,
                "Yellow max days": self.config.yellow_max_days_in_status,
                "Red priority levels": self.config.red_priority_levels,
                "Blocked statuses": self.config.blocked_statuses
            }
        }