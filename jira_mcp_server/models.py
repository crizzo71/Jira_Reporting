"""Data models for Jira MCP Server."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class RAGStatus(str, Enum):
    """RAG status classification."""
    RED = "red"
    AMBER = "amber"
    GREEN = "green"


class IssueStatus(BaseModel):
    """Jira issue status information."""
    
    id: str
    name: str
    category: str


class IssueType(BaseModel):
    """Jira issue type information."""
    
    id: str
    name: str
    icon_url: Optional[str] = None


class User(BaseModel):
    """Jira user information."""
    
    account_id: str
    display_name: str
    email_address: Optional[str] = None


class Issue(BaseModel):
    """Jira issue representation."""
    
    key: str
    summary: str
    description: Optional[str] = None
    status: IssueStatus
    issue_type: IssueType
    priority: str
    assignee: Optional[User] = None
    reporter: User
    created: datetime
    updated: datetime
    resolved: Optional[datetime] = None
    labels: List[str] = Field(default_factory=list)
    components: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    story_points: Optional[float] = None
    sprint: Optional[str] = None
    
    # RAG classification
    rag_status: Optional[RAGStatus] = None
    rag_reason: Optional[str] = None
    
    # Calculated fields
    days_in_status: Optional[int] = None
    is_blocked: bool = False
    url: Optional[str] = None


class Board(BaseModel):
    """Jira board representation."""
    
    id: int
    name: str
    type: str
    project_key: Optional[str] = None
    location: Optional[str] = None


class Project(BaseModel):
    """Jira project representation."""
    
    id: str
    key: str
    name: str
    project_type: str
    lead: Optional[User] = None


class StatusTransition(BaseModel):
    """Issue status transition information."""
    
    issue_key: str
    from_status: str
    to_status: str
    transition_date: datetime
    author: User


class WeeklyReportData(BaseModel):
    """Data structure for weekly report generation."""
    
    team_name: str
    report_week: str
    started_issues: List[Issue] = Field(default_factory=list)
    completed_issues: List[Issue] = Field(default_factory=list)
    blocked_issues: List[Issue] = Field(default_factory=list)
    at_risk_issues: List[Issue] = Field(default_factory=list)
    
    # Manual input sections
    risks: List[str] = Field(default_factory=list)
    celebrations: List[str] = Field(default_factory=list)
    associates: List[str] = Field(default_factory=list)
    
    # Summary statistics
    total_issues: int = 0
    green_count: int = 0
    amber_count: int = 0
    red_count: int = 0
    
    overall_rag_status: RAGStatus = RAGStatus.GREEN


class ReportTemplate(BaseModel):
    """Template configuration for report generation."""
    
    template_name: str
    sections: List[str]
    include_links: bool = True
    include_assignees: bool = True
    custom_fields: Dict[str, str] = Field(default_factory=dict)


class FilterCriteria(BaseModel):
    """Criteria for filtering issues."""
    
    projects: List[str] = Field(default_factory=list)
    boards: List[int] = Field(default_factory=list)
    statuses: List[str] = Field(default_factory=list)
    assignees: List[str] = Field(default_factory=list)
    issue_types: List[str] = Field(default_factory=list)
    labels: List[str] = Field(default_factory=list)
    
    # Date filtering
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    updated_after: Optional[datetime] = None
    updated_before: Optional[datetime] = None
    resolved_after: Optional[datetime] = None
    resolved_before: Optional[datetime] = None
    
    # JQL override
    custom_jql: Optional[str] = None