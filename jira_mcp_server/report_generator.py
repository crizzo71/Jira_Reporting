"""Weekly status report generator for Jira issues."""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass

from .config import ReportConfig
from .models import Issue, RAGStatus, WeeklyReportData

logger = logging.getLogger(__name__)


@dataclass
class ReportSection:
    """Represents a section in the weekly report."""
    title: str
    issues: List[Issue]
    description: str = ""
    show_assignees: bool = True
    show_priority: bool = False


class ReportGenerator:
    """Generates weekly status reports from Jira issues."""
    
    def __init__(self, config: ReportConfig):
        self.config = config
    
    async def generate_weekly_report(
        self,
        team_name: str,
        issues: List[Issue],
        week_ending: date,
        output_format: str = "markdown",
        include_manual_sections: bool = True
    ) -> str:
        """Generate a weekly status report."""
        
        # Categorize issues for the report
        report_data = self._categorize_issues_for_report(
            team_name=team_name,
            issues=issues,
            week_ending=week_ending
        )
        
        # Generate report based on format
        if output_format.lower() == "markdown":
            return self._generate_markdown_report(report_data, include_manual_sections)
        elif output_format.lower() == "html":
            return self._generate_html_report(report_data, include_manual_sections)
        elif output_format.lower() == "confluence":
            return self._generate_confluence_report(report_data, include_manual_sections)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _categorize_issues_for_report(
        self,
        team_name: str,
        issues: List[Issue],
        week_ending: date
    ) -> WeeklyReportData:
        """Categorize issues into report sections."""
        
        week_start = week_ending - timedelta(days=6)
        week_start_datetime = datetime.combine(week_start, datetime.min.time())
        week_end_datetime = datetime.combine(week_ending, datetime.max.time())
        
        # Initialize report data
        report_data = WeeklyReportData(
            team_name=team_name,
            report_week=f"{week_start.strftime('%m/%d')} - {week_ending.strftime('%m/%d/%Y')}"
        )
        
        # Categorize issues
        for issue in issues:
            # Started issues: transitioned to In Progress or similar during the week
            if self._was_started_this_week(issue, week_start_datetime, week_end_datetime):
                report_data.started_issues.append(issue)
            
            # Completed issues: resolved during the week
            if self._was_completed_this_week(issue, week_start_datetime, week_end_datetime):
                report_data.completed_issues.append(issue)
            
            # Blocked/Off-track issues: red RAG status
            if issue.rag_status == RAGStatus.RED:
                report_data.blocked_issues.append(issue)
            
            # At-risk issues: amber RAG status
            elif issue.rag_status == RAGStatus.AMBER:
                report_data.at_risk_issues.append(issue)
        
        # Calculate summary statistics
        report_data.total_issues = len(issues)
        report_data.green_count = len([i for i in issues if i.rag_status == RAGStatus.GREEN])
        report_data.amber_count = len([i for i in issues if i.rag_status == RAGStatus.AMBER])
        report_data.red_count = len([i for i in issues if i.rag_status == RAGStatus.RED])
        
        # Determine overall RAG status
        if report_data.red_count > 0:
            report_data.overall_rag_status = RAGStatus.RED
        elif report_data.amber_count > report_data.green_count * 0.3:  # More than 30% amber
            report_data.overall_rag_status = RAGStatus.AMBER
        else:
            report_data.overall_rag_status = RAGStatus.GREEN
        
        return report_data
    
    def _was_started_this_week(
        self, 
        issue: Issue, 
        week_start: datetime, 
        week_end: datetime
    ) -> bool:
        """Check if issue was started (moved to in-progress) this week."""
        # This is a simplified check - in a full implementation, you'd check status transitions
        # For now, we'll use a heuristic based on status and update time
        
        in_progress_statuses = [
            'in progress', 'development', 'coding', 'implementation', 
            'in development', 'work in progress', 'doing'
        ]
        
        is_in_progress = any(status in issue.status.name.lower() for status in in_progress_statuses)
        was_updated_this_week = week_start <= issue.updated <= week_end
        
        return is_in_progress and was_updated_this_week
    
    def _was_completed_this_week(
        self, 
        issue: Issue, 
        week_start: datetime, 
        week_end: datetime
    ) -> bool:
        """Check if issue was completed this week."""
        return (issue.resolved is not None and 
                week_start <= issue.resolved <= week_end)
    
    def _generate_markdown_report(
        self, 
        data: WeeklyReportData, 
        include_manual: bool
    ) -> str:
        """Generate Markdown format report."""
        
        # RAG status emoji mapping
        rag_emoji = {
            RAGStatus.GREEN: "🟢",
            RAGStatus.AMBER: "🟡", 
            RAGStatus.RED: "🔴"
        }
        
        lines = [
            f"# Weekly Status Report - {data.team_name}",
            f"**Week:** {data.report_week}",
            f"**Overall Status:** {rag_emoji[data.overall_rag_status]} {data.overall_rag_status.value.upper()}",
            "",
            f"**Summary:** {data.green_count} Green, {data.amber_count} Amber, {data.red_count} Red ({data.total_issues} total issues)",
            "",
            "---",
            ""
        ]
        
        # Started Issues Section
        lines.extend([
            "## 🚀 Started This Week",
            ""
        ])
        
        if data.started_issues:
            for issue in data.started_issues:
                assignee_text = f" - {issue.assignee.display_name}" if issue.assignee else " - Unassigned"
                lines.append(f"- [{issue.key}]({issue.url}) {issue.summary}{assignee_text}")
            lines.append("")
        else:
            lines.extend(["*No issues started this week.*", ""])
        
        # Completed Issues Section
        lines.extend([
            "## ✅ Completed This Week",
            ""
        ])
        
        if data.completed_issues:
            for issue in data.completed_issues:
                assignee_text = f" - {issue.assignee.display_name}" if issue.assignee else " - Unassigned"
                lines.append(f"- [{issue.key}]({issue.url}) {issue.summary}{assignee_text}")
            lines.append("")
        else:
            lines.extend(["*No issues completed this week.*", ""])
        
        # Blocked/Off-track Issues Section
        lines.extend([
            "## 🔴 Blocked/Off-track Items",
            ""
        ])
        
        if data.blocked_issues:
            for issue in data.blocked_issues:
                assignee_text = f" - {issue.assignee.display_name}" if issue.assignee else " - Unassigned"
                reason_text = f" ({issue.rag_reason})" if issue.rag_reason else ""
                lines.append(f"- [{issue.key}]({issue.url}) {issue.summary}{assignee_text}{reason_text}")
            lines.append("")
        else:
            lines.extend(["*No blocked items.*", ""])
        
        # At-risk Issues Section
        if data.at_risk_issues:
            lines.extend([
                "## 🟡 At-Risk Items",
                ""
            ])
            
            for issue in data.at_risk_issues:
                assignee_text = f" - {issue.assignee.display_name}" if issue.assignee else " - Unassigned"
                reason_text = f" ({issue.rag_reason})" if issue.rag_reason else ""
                lines.append(f"- [{issue.key}]({issue.url}) {issue.summary}{assignee_text}{reason_text}")
            lines.append("")
        
        # Manual input sections
        if include_manual:
            lines.extend([
                "## 🚨 Risks",
                "*Please add any risks, dependencies, or concerns not captured above.*",
                "",
                "- ",
                "",
                "## 🎉 Celebrations",
                "*Please add any notable achievements, milestones, or good news.*",
                "",
                "- ",
                "",
                "## 👥 Associates",
                "*Please add any team member updates, recognition, or important notes.*",
                "",
                "- ",
                ""
            ])
        
        # Footer
        lines.extend([
            "---",
            f"*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        ])
        
        return "\n".join(lines)
    
    def _generate_html_report(
        self, 
        data: WeeklyReportData, 
        include_manual: bool
    ) -> str:
        """Generate HTML format report."""
        
        # RAG status color mapping
        rag_colors = {
            RAGStatus.GREEN: "#28a745",
            RAGStatus.AMBER: "#ffc107",
            RAGStatus.RED: "#dc3545"
        }
        
        html_lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"    <title>Weekly Status Report - {data.team_name}</title>",
            "    <style>",
            "        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }",
            "        .rag-badge { display: inline-block; padding: 4px 8px; border-radius: 4px; color: white; font-weight: bold; }",
            "        .summary { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }",
            "        .section { margin: 25px 0; }",
            "        .issue-list { list-style-type: none; padding: 0; }",
            "        .issue-item { margin: 8px 0; padding: 8px; background-color: #f8f9fa; border-radius: 4px; }",
            "        .manual-section { background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; }",
            "    </style>",
            "</head>",
            "<body>",
            f"    <h1>Weekly Status Report - {data.team_name}</h1>",
            f"    <p><strong>Week:</strong> {data.report_week}</p>",
            f"    <p><strong>Overall Status:</strong> <span class='rag-badge' style='background-color: {rag_colors[data.overall_rag_status]}'>{data.overall_rag_status.value.upper()}</span></p>",
            "",
            "    <div class='summary'>",
            f"        <strong>Summary:</strong> {data.green_count} Green, {data.amber_count} Amber, {data.red_count} Red ({data.total_issues} total issues)",
            "    </div>",
            ""
        ]
        
        # Started Issues
        html_lines.extend([
            "    <div class='section'>",
            "        <h2>🚀 Started This Week</h2>"
        ])
        
        if data.started_issues:
            html_lines.append("        <ul class='issue-list'>")
            for issue in data.started_issues:
                assignee_text = f" - {issue.assignee.display_name}" if issue.assignee else " - Unassigned"
                html_lines.append(f"            <li class='issue-item'><a href='{issue.url}'>{issue.key}</a> {issue.summary}{assignee_text}</li>")
            html_lines.append("        </ul>")
        else:
            html_lines.append("        <p><em>No issues started this week.</em></p>")
        
        html_lines.append("    </div>")
        
        # Add other sections similarly...
        # (Abbreviated for space - would include completed, blocked, at-risk sections)
        
        html_lines.extend([
            f"    <hr>",
            f"    <p><em>Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>",
            "</body>",
            "</html>"
        ])
        
        return "\n".join(html_lines)
    
    def _generate_confluence_report(
        self, 
        data: WeeklyReportData, 
        include_manual: bool
    ) -> str:
        """Generate Confluence wiki markup format report."""
        
        lines = [
            f"h1. Weekly Status Report - {data.team_name}",
            f"*Week:* {data.report_week}",
            f"*Overall Status:* {data.overall_rag_status.value.upper()}",
            "",
            f"*Summary:* {data.green_count} Green, {data.amber_count} Amber, {data.red_count} Red ({data.total_issues} total issues)",
            "",
            "----",
            ""
        ]
        
        # Started Issues
        lines.extend([
            "h2. Started This Week",
            ""
        ])
        
        if data.started_issues:
            for issue in data.started_issues:
                assignee_text = f" - {issue.assignee.display_name}" if issue.assignee else " - Unassigned"
                lines.append(f"* [{issue.key}|{issue.url}] {issue.summary}{assignee_text}")
            lines.append("")
        else:
            lines.extend(["_No issues started this week._", ""])
        
        # Add other sections...
        # (Similar to markdown but with Confluence markup)
        
        return "\n".join(lines)