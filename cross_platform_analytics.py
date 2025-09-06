"""
Cross-Platform Analytics Module

Provides advanced analytics combining Jira and GitHub data:
- Delivery pipeline metrics (Jira issue → GitHub PR → deployment)
- Developer productivity analysis across platforms
- Sprint/milestone correlation and velocity tracking
- Quality metrics (defect rates, cycle times)
- Team collaboration insights
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import statistics

from jira_mcp_server.jira_client import JiraClient
from jira_mcp_server.models import Issue as JiraIssue
from github_client import GitHubClient, GitHubIssue, GitHubPullRequest, GitHubCommit

logger = logging.getLogger(__name__)


class DeliveryStage(Enum):
    """Stages in the delivery pipeline."""
    PLANNING = "planning"           # Jira issue created
    DEVELOPMENT = "development"     # GitHub branch/commits
    REVIEW = "review"              # GitHub PR review
    INTEGRATION = "integration"    # PR merged
    DEPLOYMENT = "deployment"      # Deployed to production
    COMPLETED = "completed"        # Jira issue resolved


@dataclass
class DeliveryPipeline:
    """Represents a complete delivery pipeline from Jira to deployment."""
    jira_issue: JiraIssue
    github_issues: List[GitHubIssue] = field(default_factory=list)
    pull_requests: List[GitHubPullRequest] = field(default_factory=list)
    commits: List[GitHubCommit] = field(default_factory=list)
    
    # Timeline metrics
    planning_start: Optional[datetime] = None
    development_start: Optional[datetime] = None
    review_start: Optional[datetime] = None
    integration_date: Optional[datetime] = None
    deployment_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    
    # Calculated metrics
    planning_time: Optional[float] = None      # Days
    development_time: Optional[float] = None   # Days
    review_time: Optional[float] = None        # Days
    total_cycle_time: Optional[float] = None   # Days
    
    # Quality metrics
    defects_found: int = 0
    rework_commits: int = 0
    review_iterations: int = 0
    
    # Team metrics
    developers: List[str] = field(default_factory=list)
    reviewers: List[str] = field(default_factory=list)
    
    @property
    def current_stage(self) -> DeliveryStage:
        """Determine current stage in delivery pipeline."""
        if self.completion_date:
            return DeliveryStage.COMPLETED
        elif self.deployment_date:
            return DeliveryStage.DEPLOYMENT
        elif self.integration_date:
            return DeliveryStage.INTEGRATION
        elif self.review_start:
            return DeliveryStage.REVIEW
        elif self.development_start:
            return DeliveryStage.DEVELOPMENT
        else:
            return DeliveryStage.PLANNING


@dataclass
class DeveloperMetrics:
    """Developer productivity metrics across Jira and GitHub."""
    developer: str
    
    # Jira metrics
    issues_assigned: int = 0
    issues_completed: int = 0
    average_issue_completion_time: Optional[float] = None
    
    # GitHub metrics
    commits_count: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    pull_requests_created: int = 0
    pull_requests_reviewed: int = 0
    pull_requests_merged: int = 0
    
    # Cross-platform metrics
    delivery_pipelines_completed: int = 0
    average_cycle_time: Optional[float] = None
    quality_score: Optional[float] = None  # Based on defects, rework, etc.
    
    # Collaboration metrics
    code_review_participation: float = 0.0
    cross_team_collaboration: int = 0


@dataclass
class TeamMetrics:
    """Team-level metrics combining Jira and GitHub data."""
    team_name: str
    period_start: datetime
    period_end: datetime
    
    # Velocity metrics
    story_points_completed: int = 0
    issues_completed: int = 0
    pull_requests_merged: int = 0
    
    # Quality metrics
    defect_rate: float = 0.0
    rework_rate: float = 0.0
    first_time_quality: float = 0.0
    
    # Efficiency metrics
    average_cycle_time: Optional[float] = None
    average_lead_time: Optional[float] = None
    deployment_frequency: float = 0.0
    
    # Collaboration metrics
    cross_platform_correlation: float = 0.0
    code_review_coverage: float = 0.0
    
    # Developer metrics
    developers: List[DeveloperMetrics] = field(default_factory=list)
    
    # Delivery pipelines
    pipelines: List[DeliveryPipeline] = field(default_factory=list)


class CrossPlatformAnalytics:
    """Advanced analytics combining Jira and GitHub data."""
    
    def __init__(self, jira_client: JiraClient, github_client: GitHubClient):
        self.jira_client = jira_client
        self.github_client = github_client
        
    async def analyze_delivery_pipelines(
        self,
        jira_issues: List[JiraIssue],
        github_repos: List[str],
        period_start: datetime,
        period_end: datetime
    ) -> List[DeliveryPipeline]:
        """Analyze complete delivery pipelines from Jira to GitHub."""
        pipelines = []
        
        for jira_issue in jira_issues:
            pipeline = DeliveryPipeline(jira_issue=jira_issue)
            
            # Set planning timeline
            pipeline.planning_start = jira_issue.created
            
            # Find correlated GitHub items for this Jira issue
            for repo in github_repos:
                owner, repo_name = repo.split('/', 1)
                
                # Get GitHub issues
                gh_issues = await self.github_client.get_issues(owner, repo_name, since=period_start)
                correlated_issues = [
                    issue for issue in gh_issues 
                    if jira_issue.key in self.github_client.extract_jira_keys_from_text(f"{issue.title} {issue.body or ''}")
                ]
                pipeline.github_issues.extend(correlated_issues)
                
                # Get pull requests
                prs = await self.github_client.get_pull_requests(owner, repo_name, since=period_start)
                correlated_prs = [
                    pr for pr in prs
                    if jira_issue.key in self.github_client.extract_jira_keys_from_text(f"{pr.title} {pr.body or ''}")
                ]
                pipeline.pull_requests.extend(correlated_prs)
                
                # Get commits
                commits = await self.github_client.get_commits(owner, repo_name, since=period_start, until=period_end)
                correlated_commits = [
                    commit for commit in commits
                    if jira_issue.key in self.github_client.extract_jira_keys_from_text(commit.message)
                ]
                pipeline.commits.extend(correlated_commits)
            
            # Calculate timeline metrics
            await self._calculate_pipeline_metrics(pipeline)
            pipelines.append(pipeline)
        
        return pipelines
    
    async def _calculate_pipeline_metrics(self, pipeline: DeliveryPipeline):
        """Calculate timing and quality metrics for a delivery pipeline."""
        
        # Development start (first commit)
        if pipeline.commits:
            pipeline.development_start = min(commit.authored_date for commit in pipeline.commits)
            pipeline.developers = list(set(commit.author for commit in pipeline.commits))
        
        # Review start (first PR created)
        if pipeline.pull_requests:
            pipeline.review_start = min(pr.created_at for pr in pipeline.pull_requests)
            pipeline.reviewers = list(set(
                reviewer for pr in pipeline.pull_requests 
                for reviewer in pr.reviewers
            ))
        
        # Integration (first PR merged)
        merged_prs = [pr for pr in pipeline.pull_requests if pr.merged_at]
        if merged_prs:
            pipeline.integration_date = min(pr.merged_at for pr in merged_prs)
        
        # Completion (Jira issue resolved)
        if pipeline.jira_issue.resolved:
            pipeline.completion_date = pipeline.jira_issue.resolved
        
        # Calculate timing metrics
        if pipeline.planning_start and pipeline.development_start:
            pipeline.planning_time = (pipeline.development_start - pipeline.planning_start).days
        
        if pipeline.development_start and pipeline.review_start:
            pipeline.development_time = (pipeline.review_start - pipeline.development_start).days
        
        if pipeline.review_start and pipeline.integration_date:
            pipeline.review_time = (pipeline.integration_date - pipeline.review_start).days
        
        if pipeline.planning_start and pipeline.completion_date:
            pipeline.total_cycle_time = (pipeline.completion_date - pipeline.planning_start).days
        
        # Calculate quality metrics
        pipeline.rework_commits = len([
            commit for commit in pipeline.commits
            if any(keyword in commit.message.lower() for keyword in ['fix', 'bug', 'hotfix', 'patch'])
        ])
        
        pipeline.review_iterations = sum(pr.review_comments for pr in pipeline.pull_requests)
        
        # Count defects (linked bug issues)
        pipeline.defects_found = len([
            issue for issue in pipeline.github_issues
            if 'bug' in [label.lower() for label in issue.labels]
        ])
    
    async def calculate_developer_metrics(
        self,
        pipelines: List[DeliveryPipeline],
        period_start: datetime,
        period_end: datetime
    ) -> List[DeveloperMetrics]:
        """Calculate individual developer metrics."""
        developer_data = {}
        
        for pipeline in pipelines:
            # Jira issue assignee
            if pipeline.jira_issue.assignee:
                dev_name = pipeline.jira_issue.assignee.display_name
                if dev_name not in developer_data:
                    developer_data[dev_name] = DeveloperMetrics(developer=dev_name)
                
                developer_data[dev_name].issues_assigned += 1
                if pipeline.completion_date:
                    developer_data[dev_name].issues_completed += 1
            
            # GitHub contributors
            for commit in pipeline.commits:
                dev_name = commit.author
                if dev_name not in developer_data:
                    developer_data[dev_name] = DeveloperMetrics(developer=dev_name)
                
                developer_data[dev_name].commits_count += 1
                developer_data[dev_name].lines_added += commit.additions
                developer_data[dev_name].lines_deleted += commit.deletions
            
            # Pull request metrics
            for pr in pipeline.pull_requests:
                # PR creator
                dev_name = pr.user
                if dev_name not in developer_data:
                    developer_data[dev_name] = DeveloperMetrics(developer=dev_name)
                
                developer_data[dev_name].pull_requests_created += 1
                if pr.merged_at:
                    developer_data[dev_name].pull_requests_merged += 1
                
                # PR reviewers
                for reviewer in pr.reviewers:
                    if reviewer not in developer_data:
                        developer_data[reviewer] = DeveloperMetrics(developer=reviewer)
                    developer_data[reviewer].pull_requests_reviewed += 1
        
        # Calculate aggregate metrics
        for dev_metrics in developer_data.values():
            # Average cycle time for completed pipelines
            completed_pipelines = [
                p for p in pipelines 
                if p.completion_date and (
                    (p.jira_issue.assignee and p.jira_issue.assignee.display_name == dev_metrics.developer) or
                    any(commit.author == dev_metrics.developer for commit in p.commits)
                )
            ]
            
            if completed_pipelines:
                cycle_times = [p.total_cycle_time for p in completed_pipelines if p.total_cycle_time]
                if cycle_times:
                    dev_metrics.average_cycle_time = statistics.mean(cycle_times)
                
                dev_metrics.delivery_pipelines_completed = len(completed_pipelines)
                
                # Quality score (lower defects/rework = higher score)
                total_defects = sum(p.defects_found for p in completed_pipelines)
                total_rework = sum(p.rework_commits for p in completed_pipelines)
                total_work = len(completed_pipelines)
                
                if total_work > 0:
                    defect_rate = total_defects / total_work
                    rework_rate = total_rework / total_work
                    dev_metrics.quality_score = max(0, 1.0 - (defect_rate * 0.3 + rework_rate * 0.2))
            
            # Code review participation
            if dev_metrics.commits_count > 0:
                dev_metrics.code_review_participation = dev_metrics.pull_requests_reviewed / max(1, dev_metrics.commits_count)
        
        return list(developer_data.values())
    
    async def calculate_team_metrics(
        self,
        team_name: str,
        pipelines: List[DeliveryPipeline],
        period_start: datetime,
        period_end: datetime
    ) -> TeamMetrics:
        """Calculate team-level metrics."""
        team_metrics = TeamMetrics(
            team_name=team_name,
            period_start=period_start,
            period_end=period_end
        )
        
        # Basic counts
        team_metrics.issues_completed = len([p for p in pipelines if p.completion_date])
        team_metrics.pull_requests_merged = len([
            pr for pipeline in pipelines 
            for pr in pipeline.pull_requests 
            if pr.merged_at
        ])
        
        # Story points (if available)
        team_metrics.story_points_completed = sum(
            pipeline.jira_issue.story_points or 0 
            for pipeline in pipelines 
            if pipeline.completion_date
        )
        
        # Quality metrics
        total_pipelines = len(pipelines)
        if total_pipelines > 0:
            total_defects = sum(p.defects_found for p in pipelines)
            total_rework = sum(p.rework_commits for p in pipelines)
            
            team_metrics.defect_rate = total_defects / total_pipelines
            team_metrics.rework_rate = total_rework / total_pipelines
            team_metrics.first_time_quality = 1.0 - team_metrics.rework_rate
        
        # Timing metrics
        completed_pipelines = [p for p in pipelines if p.total_cycle_time]
        if completed_pipelines:
            cycle_times = [p.total_cycle_time for p in completed_pipelines]
            team_metrics.average_cycle_time = statistics.mean(cycle_times)
        
        # Deployment frequency (PRs merged per day)
        period_days = (period_end - period_start).days or 1
        team_metrics.deployment_frequency = team_metrics.pull_requests_merged / period_days
        
        # Cross-platform correlation (percentage of Jira issues with GitHub activity)
        jira_with_github = len([p for p in pipelines if p.commits or p.pull_requests])
        if total_pipelines > 0:
            team_metrics.cross_platform_correlation = jira_with_github / total_pipelines
        
        # Code review coverage (percentage of PRs with reviews)
        all_prs = [pr for pipeline in pipelines for pr in pipeline.pull_requests]
        reviewed_prs = len([pr for pr in all_prs if pr.reviewers])
        if all_prs:
            team_metrics.code_review_coverage = reviewed_prs / len(all_prs)
        
        # Calculate developer metrics
        team_metrics.developers = await self.calculate_developer_metrics(
            pipelines, period_start, period_end
        )
        
        team_metrics.pipelines = pipelines
        
        return team_metrics
    
    async def generate_cross_platform_insights(
        self,
        team_metrics: TeamMetrics
    ) -> Dict[str, Any]:
        """Generate actionable insights from cross-platform analytics."""
        insights = {
            "summary": {},
            "strengths": [],
            "improvement_areas": [],
            "recommendations": [],
            "trends": {},
            "comparisons": {}
        }
        
        # Summary
        insights["summary"] = {
            "total_issues": len(team_metrics.pipelines),
            "completion_rate": team_metrics.issues_completed / max(1, len(team_metrics.pipelines)),
            "average_cycle_time": team_metrics.average_cycle_time,
            "cross_platform_correlation": team_metrics.cross_platform_correlation,
            "quality_score": team_metrics.first_time_quality
        }
        
        # Identify strengths
        if team_metrics.cross_platform_correlation > 0.8:
            insights["strengths"].append("Excellent cross-platform tracking and correlation")
        
        if team_metrics.code_review_coverage > 0.9:
            insights["strengths"].append("High code review coverage indicates good collaboration")
        
        if team_metrics.first_time_quality > 0.8:
            insights["strengths"].append("Low rework rate shows good initial quality")
        
        # Identify improvement areas
        if team_metrics.average_cycle_time and team_metrics.average_cycle_time > 14:
            insights["improvement_areas"].append("Cycle time is longer than recommended (>14 days)")
        
        if team_metrics.defect_rate > 0.2:
            insights["improvement_areas"].append("Defect rate is higher than target (<20%)")
        
        if team_metrics.cross_platform_correlation < 0.6:
            insights["improvement_areas"].append("Low correlation between Jira and GitHub - improve process tracking")
        
        # Generate recommendations
        if team_metrics.average_cycle_time and team_metrics.average_cycle_time > 10:
            insights["recommendations"].append("Consider breaking down large issues into smaller, deliverable chunks")
        
        if team_metrics.code_review_coverage < 0.8:
            insights["recommendations"].append("Increase code review participation to improve quality")
        
        if team_metrics.deployment_frequency < 0.5:
            insights["recommendations"].append("Increase deployment frequency for faster feedback loops")
        
        # Developer performance insights
        top_performers = sorted(
            team_metrics.developers,
            key=lambda d: d.quality_score or 0,
            reverse=True
        )[:3]
        
        if top_performers:
            insights["trends"]["top_performers"] = [
                {
                    "developer": dev.developer,
                    "quality_score": dev.quality_score,
                    "deliveries": dev.delivery_pipelines_completed
                }
                for dev in top_performers
            ]
        
        return insights