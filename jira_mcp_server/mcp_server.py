"""MCP Server implementation for Jira weekly status reporting."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.types import (
    CallToolRequest,
    ListToolsRequest,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

from .config import Config, get_config
from .jira_client import JiraClient, JiraClientError
from .models import FilterCriteria, RAGStatus
from .rag_classifier import RAGClassifier
from .report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class JiraMCPServer:
    """MCP Server for Jira integration."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.server = Server("jira-mcp-server")
        self.jira_client = JiraClient(self.config)
        self.rag_classifier = RAGClassifier(self.config.rag)
        self.report_generator = ReportGenerator(self.config.report)
        
        # Register tool handlers
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register MCP tool handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="authenticate",
                    description="Authenticate with Jira using configured credentials",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="get_projects",
                    description="Get all accessible Jira projects",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="get_boards",
                    description="Get Jira boards, optionally filtered by project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_keys": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional list of project keys to filter boards"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_issues",
                    description="Get Jira issues with filtering and RAG classification",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "projects": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Project keys to include"
                            },
                            "boards": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "Board IDs to include"
                            },
                            "statuses": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Status names to filter by"
                            },
                            "updated_since_days": {
                                "type": "integer",
                                "description": "Only include issues updated in the last N days",
                                "default": 7
                            },
                            "include_resolved": {
                                "type": "boolean",
                                "description": "Include resolved issues",
                                "default": True
                            },
                            "apply_rag_classification": {
                                "type": "boolean",
                                "description": "Apply RAG status classification",
                                "default": True
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="generate_weekly_report",
                    description="Generate weekly status report for specified teams/boards",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "team_name": {
                                "type": "string",
                                "description": "Name of the team for the report"
                            },
                            "projects": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Project keys to include in report"
                            },
                            "boards": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "Board IDs to include in report"
                            },
                            "week_ending": {
                                "type": "string",
                                "description": "Week ending date in YYYY-MM-DD format (defaults to last Friday)",
                                "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                            },
                            "format": {
                                "type": "string",
                                "enum": ["markdown", "html", "confluence"],
                                "description": "Output format for the report",
                                "default": "markdown"
                            },
                            "include_manual_sections": {
                                "type": "boolean",
                                "description": "Include placeholder sections for manual input",
                                "default": True
                            }
                        },
                        "required": ["team_name"]
                    }
                ),
                Tool(
                    name="configure_rag_rules",
                    description="Configure RAG status classification rules",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "green_max_days": {
                                "type": "integer",
                                "description": "Maximum days in status for green classification"
                            },
                            "yellow_max_days": {
                                "type": "integer",
                                "description": "Maximum days in status for yellow classification"
                            },
                            "red_priorities": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Priority levels that should be classified as red"
                            },
                            "blocked_statuses": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Status names that indicate blocked issues"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_status_transitions",
                    description="Get status transitions for issues within a time period",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issue_keys": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Issue keys to get transitions for"
                            },
                            "since_days": {
                                "type": "integer",
                                "description": "Number of days back to look for transitions",
                                "default": 7
                            }
                        },
                        "required": ["issue_keys"]
                    }
                ),
                Tool(
                    name="create_issue",
                    description="Create a new Jira issue",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_key": {
                                "type": "string",
                                "description": "Project key where the issue will be created"
                            },
                            "issue_type": {
                                "type": "string",
                                "description": "Type of issue (Story, Bug, Epic, Task, etc.)"
                            },
                            "summary": {
                                "type": "string",
                                "description": "Issue summary/title"
                            },
                            "description": {
                                "type": "string",
                                "description": "Issue description (optional)"
                            },
                            "priority": {
                                "type": "string",
                                "description": "Issue priority (Highest, High, Medium, Low, Lowest)",
                                "default": "Medium"
                            },
                            "assignee": {
                                "type": "string",
                                "description": "Username or email of assignee (optional)"
                            },
                            "parent_key": {
                                "type": "string",
                                "description": "Parent issue key for sub-tasks (optional)"
                            },
                            "epic_key": {
                                "type": "string",
                                "description": "Epic issue key to link to (optional)"
                            },
                            "labels": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Issue labels (optional)"
                            },
                            "components": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Component names (optional)"
                            }
                        },
                        "required": ["project_key", "issue_type", "summary"]
                    }
                ),
                Tool(
                    name="update_issue",
                    description="Update an existing Jira issue",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issue_key": {
                                "type": "string",
                                "description": "Issue key to update"
                            },
                            "summary": {
                                "type": "string",
                                "description": "New issue summary (optional)"
                            },
                            "description": {
                                "type": "string",
                                "description": "New issue description (optional)"
                            },
                            "priority": {
                                "type": "string",
                                "description": "New issue priority (optional)"
                            },
                            "assignee": {
                                "type": "string",
                                "description": "New assignee username or email (optional)"
                            },
                            "status": {
                                "type": "string",
                                "description": "New status name for transition (optional)"
                            },
                            "labels": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "New labels list (replaces existing, optional)"
                            },
                            "add_labels": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Labels to add to existing (optional)"
                            },
                            "remove_labels": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Labels to remove from existing (optional)"
                            }
                        },
                        "required": ["issue_key"]
                    }
                ),
                Tool(
                    name="add_comment",
                    description="Add a comment to a Jira issue",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issue_key": {
                                "type": "string",
                                "description": "Issue key to comment on"
                            },
                            "comment": {
                                "type": "string",
                                "description": "Comment text content"
                            },
                            "visibility": {
                                "type": "string",
                                "description": "Comment visibility (all, internal, role-based)",
                                "default": "all"
                            }
                        },
                        "required": ["issue_key", "comment"]
                    }
                ),
                Tool(
                    name="add_attachment",
                    description="Add an attachment to a Jira issue",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issue_key": {
                                "type": "string",
                                "description": "Issue key to attach file to"
                            },
                            "file_path": {
                                "type": "string",
                                "description": "Local file path to attach"
                            },
                            "filename": {
                                "type": "string",
                                "description": "Custom filename for attachment (optional)"
                            }
                        },
                        "required": ["issue_key", "file_path"]
                    }
                ),
                Tool(
                    name="get_github_repositories",
                    description="Get GitHub repositories for organization or user",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "organization": {
                                "type": "string",
                                "description": "GitHub organization name (optional)"
                            },
                            "user": {
                                "type": "string",
                                "description": "GitHub user name (optional)"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="analyze_cross_platform_metrics",
                    description="Analyze delivery metrics across Jira and GitHub",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "team_name": {
                                "type": "string",
                                "description": "Team name for analysis"
                            },
                            "jira_projects": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Jira project keys to analyze"
                            },
                            "github_repositories": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "GitHub repositories in format 'owner/repo'"
                            },
                            "period_days": {
                                "type": "integer",
                                "description": "Number of days to analyze (default 30)",
                                "default": 30
                            }
                        },
                        "required": ["team_name"]
                    }
                ),
                Tool(
                    name="generate_analytics_dashboard",
                    description="Generate advanced analytics dashboard with cross-platform metrics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "team_name": {
                                "type": "string",
                                "description": "Team name for dashboard"
                            },
                            "dashboard_type": {
                                "type": "string",
                                "enum": ["executive", "detailed", "developer", "html"],
                                "description": "Type of dashboard to generate",
                                "default": "executive"
                            },
                            "jira_projects": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Jira project keys to include"
                            },
                            "github_repositories": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "GitHub repositories to include"
                            },
                            "period_days": {
                                "type": "integer",
                                "description": "Analysis period in days",
                                "default": 30
                            }
                        },
                        "required": ["team_name"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(request: CallToolRequest) -> List[TextContent | ImageContent | EmbeddedResource]:
            """Handle tool execution requests."""
            try:
                if request.name == "authenticate":
                    return await self._handle_authenticate(request.arguments or {})
                elif request.name == "get_projects":
                    return await self._handle_get_projects(request.arguments or {})
                elif request.name == "get_boards":
                    return await self._handle_get_boards(request.arguments or {})
                elif request.name == "get_issues":
                    return await self._handle_get_issues(request.arguments or {})
                elif request.name == "generate_weekly_report":
                    return await self._handle_generate_report(request.arguments or {})
                elif request.name == "configure_rag_rules":
                    return await self._handle_configure_rag_rules(request.arguments or {})
                elif request.name == "get_status_transitions":
                    return await self._handle_get_status_transitions(request.arguments or {})
                elif request.name == "create_issue":
                    return await self._handle_create_issue(request.arguments or {})
                elif request.name == "update_issue":
                    return await self._handle_update_issue(request.arguments or {})
                elif request.name == "add_comment":
                    return await self._handle_add_comment(request.arguments or {})
                elif request.name == "add_attachment":
                    return await self._handle_add_attachment(request.arguments or {})
                elif request.name == "get_github_repositories":
                    return await self._handle_get_github_repositories(request.arguments or {})
                elif request.name == "analyze_cross_platform_metrics":
                    return await self._handle_analyze_cross_platform_metrics(request.arguments or {})
                elif request.name == "generate_analytics_dashboard":
                    return await self._handle_generate_analytics_dashboard(request.arguments or {})
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {request.name}")]
            
            except Exception as e:
                logger.error(f"Error handling tool {request.name}: {e}", exc_info=True)
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def _handle_authenticate(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle authentication request."""
        try:
            await self.jira_client.authenticate()
            return [TextContent(
                type="text",
                text=f"Successfully authenticated with Jira at {self.config.jira.server}"
            )]
        except JiraClientError as e:
            return [TextContent(type="text", text=f"Authentication failed: {e}")]
    
    async def _handle_get_projects(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle get projects request."""
        try:
            projects = await self.jira_client.get_projects()
            
            result = {
                "projects": [
                    {
                        "id": p.id,
                        "key": p.key,
                        "name": p.name,
                        "type": p.project_type,
                        "lead": p.lead.display_name if p.lead else None
                    }
                    for p in projects
                ],
                "count": len(projects)
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        except JiraClientError as e:
            return [TextContent(type="text", text=f"Error retrieving projects: {e}")]
    
    async def _handle_get_boards(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle get boards request."""
        try:
            project_keys = args.get("project_keys")
            boards = await self.jira_client.get_boards(project_keys)
            
            result = {
                "boards": [
                    {
                        "id": b.id,
                        "name": b.name,
                        "type": b.type,
                        "project_key": b.project_key
                    }
                    for b in boards
                ],
                "count": len(boards)
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        except JiraClientError as e:
            return [TextContent(type="text", text=f"Error retrieving boards: {e}")]
    
    async def _handle_get_issues(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle get issues request."""
        try:
            # Build filter criteria
            criteria = FilterCriteria()
            
            if "projects" in args:
                criteria.projects = args["projects"]
            if "boards" in args:
                criteria.boards = args["boards"]
            if "statuses" in args:
                criteria.statuses = args["statuses"]
            
            # Date filtering
            updated_since_days = args.get("updated_since_days", 7)
            if updated_since_days > 0:
                criteria.updated_after = datetime.now() - timedelta(days=updated_since_days)
            
            # Get issues
            issues = await self.jira_client.get_issues(criteria)
            
            # Apply RAG classification if requested
            if args.get("apply_rag_classification", True):
                for issue in issues:
                    rag_result = self.rag_classifier.classify_issue(issue)
                    issue.rag_status = rag_result.status
                    issue.rag_reason = rag_result.reason
            
            # Build response
            result = {
                "issues": [
                    {
                        "key": issue.key,
                        "summary": issue.summary,
                        "status": issue.status.name,
                        "assignee": issue.assignee.display_name if issue.assignee else None,
                        "priority": issue.priority,
                        "created": issue.created.isoformat(),
                        "updated": issue.updated.isoformat(),
                        "resolved": issue.resolved.isoformat() if issue.resolved else None,
                        "url": issue.url,
                        "rag_status": issue.rag_status.value if issue.rag_status else None,
                        "rag_reason": issue.rag_reason,
                        "days_in_status": issue.days_in_status,
                        "is_blocked": issue.is_blocked
                    }
                    for issue in issues
                ],
                "count": len(issues),
                "rag_summary": {
                    "green": len([i for i in issues if i.rag_status == RAGStatus.GREEN]),
                    "amber": len([i for i in issues if i.rag_status == RAGStatus.AMBER]),
                    "red": len([i for i in issues if i.rag_status == RAGStatus.RED]),
                } if args.get("apply_rag_classification", True) else None
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        except JiraClientError as e:
            return [TextContent(type="text", text=f"Error retrieving issues: {e}")]
    
    async def _handle_generate_report(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle generate weekly report request."""
        try:
            team_name = args["team_name"]
            
            # Parse week ending date
            week_ending_str = args.get("week_ending")
            if week_ending_str:
                week_ending = datetime.strptime(week_ending_str, "%Y-%m-%d").date()
            else:
                # Default to last Friday
                today = datetime.now().date()
                days_since_friday = (today.weekday() + 3) % 7
                week_ending = today - timedelta(days=days_since_friday)
            
            # Build filter criteria for the week
            week_start = week_ending - timedelta(days=6)
            criteria = FilterCriteria(
                updated_after=datetime.combine(week_start, datetime.min.time()),
                updated_before=datetime.combine(week_ending, datetime.max.time())
            )
            
            if "projects" in args:
                criteria.projects = args["projects"]
            if "boards" in args:
                criteria.boards = args["boards"]
            
            # Get issues and apply RAG classification
            issues = await self.jira_client.get_issues(criteria)
            for issue in issues:
                rag_result = self.rag_classifier.classify_issue(issue)
                issue.rag_status = rag_result.status
                issue.rag_reason = rag_result.reason
            
            # Generate report
            report_format = args.get("format", "markdown")
            include_manual = args.get("include_manual_sections", True)
            
            report_content = await self.report_generator.generate_weekly_report(
                team_name=team_name,
                issues=issues,
                week_ending=week_ending,
                output_format=report_format,
                include_manual_sections=include_manual
            )
            
            return [TextContent(type="text", text=report_content)]
        
        except Exception as e:
            return [TextContent(type="text", text=f"Error generating report: {e}")]
    
    async def _handle_configure_rag_rules(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle RAG rules configuration request."""
        try:
            updated_rules = []
            
            if "green_max_days" in args:
                self.config.rag.green_max_days_in_status = args["green_max_days"]
                updated_rules.append(f"Green max days: {args['green_max_days']}")
            
            if "yellow_max_days" in args:
                self.config.rag.yellow_max_days_in_status = args["yellow_max_days"]
                updated_rules.append(f"Yellow max days: {args['yellow_max_days']}")
            
            if "red_priorities" in args:
                self.config.rag.red_priority_levels = args["red_priorities"]
                updated_rules.append(f"Red priorities: {', '.join(args['red_priorities'])}")
            
            if "blocked_statuses" in args:
                self.config.rag.blocked_statuses = args["blocked_statuses"]
                updated_rules.append(f"Blocked statuses: {', '.join(args['blocked_statuses'])}")
            
            # Recreate classifier with new config
            self.rag_classifier = RAGClassifier(self.config.rag)
            
            result = {
                "message": "RAG rules updated successfully",
                "updated_rules": updated_rules,
                "current_config": {
                    "green_max_days": self.config.rag.green_max_days_in_status,
                    "yellow_max_days": self.config.rag.yellow_max_days_in_status,
                    "red_priorities": self.config.rag.red_priority_levels,
                    "blocked_statuses": self.config.rag.blocked_statuses
                }
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        except Exception as e:
            return [TextContent(type="text", text=f"Error configuring RAG rules: {e}")]
    
    async def _handle_get_status_transitions(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle get status transitions request."""
        try:
            issue_keys = args["issue_keys"]
            since_days = args.get("since_days", 7)
            since_date = datetime.now() - timedelta(days=since_days)
            
            transitions = await self.jira_client.get_status_transitions(issue_keys, since_date)
            
            result = {
                "transitions": [
                    {
                        "issue_key": t.issue_key,
                        "from_status": t.from_status,
                        "to_status": t.to_status,
                        "transition_date": t.transition_date.isoformat(),
                        "author": t.author.display_name
                    }
                    for t in transitions
                ],
                "count": len(transitions)
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        except JiraClientError as e:
            return [TextContent(type="text", text=f"Error retrieving status transitions: {e}")]
    
    async def _handle_create_issue(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle create issue request."""
        try:
            project_key = args["project_key"]
            issue_type = args["issue_type"]
            summary = args["summary"]
            
            # Build issue data
            issue_data = {
                "project": {"key": project_key},
                "issuetype": {"name": issue_type},
                "summary": summary
            }
            
            # Add optional fields
            if "description" in args and args["description"]:
                issue_data["description"] = args["description"]
            
            if "priority" in args and args["priority"]:
                issue_data["priority"] = {"name": args["priority"]}
            
            if "assignee" in args and args["assignee"]:
                issue_data["assignee"] = {"name": args["assignee"]}
            
            if "parent_key" in args and args["parent_key"]:
                issue_data["parent"] = {"key": args["parent_key"]}
            
            if "labels" in args and args["labels"]:
                issue_data["labels"] = args["labels"]
            
            if "components" in args and args["components"]:
                issue_data["components"] = [{"name": comp} for comp in args["components"]]
            
            # Create the issue
            created_issue = await self.jira_client.create_issue(issue_data)
            
            # Handle Epic linking if specified
            if "epic_key" in args and args["epic_key"]:
                await self.jira_client.link_to_epic(created_issue.key, args["epic_key"])
            
            result = {
                "success": True,
                "issue_key": created_issue.key,
                "issue_url": created_issue.url,
                "message": f"Successfully created issue {created_issue.key}"
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        except JiraClientError as e:
            return [TextContent(type="text", text=f"Error creating issue: {e}")]
    
    async def _handle_update_issue(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle update issue request."""
        try:
            issue_key = args["issue_key"]
            
            # Build update data
            update_data = {}
            
            if "summary" in args and args["summary"]:
                update_data["summary"] = args["summary"]
            
            if "description" in args and args["description"]:
                update_data["description"] = args["description"]
            
            if "priority" in args and args["priority"]:
                update_data["priority"] = {"name": args["priority"]}
            
            if "assignee" in args and args["assignee"]:
                update_data["assignee"] = {"name": args["assignee"]}
            
            # Handle labels operations
            if "labels" in args and args["labels"]:
                update_data["labels"] = args["labels"]
            elif "add_labels" in args or "remove_labels" in args:
                # Get current issue to manage labels
                current_issue = await self.jira_client.get_issue(issue_key)
                current_labels = set(current_issue.labels or [])
                
                if "add_labels" in args:
                    current_labels.update(args["add_labels"])
                
                if "remove_labels" in args:
                    current_labels.discard(args["remove_labels"])
                
                update_data["labels"] = list(current_labels)
            
            # Update the issue
            if update_data:
                await self.jira_client.update_issue(issue_key, update_data)
            
            # Handle status transition if specified
            if "status" in args and args["status"]:
                await self.jira_client.transition_issue(issue_key, args["status"])
            
            result = {
                "success": True,
                "issue_key": issue_key,
                "message": f"Successfully updated issue {issue_key}",
                "updated_fields": list(update_data.keys())
            }
            
            if "status" in args:
                result["status_transition"] = args["status"]
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        except JiraClientError as e:
            return [TextContent(type="text", text=f"Error updating issue: {e}")]
    
    async def _handle_add_comment(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle add comment request."""
        try:
            issue_key = args["issue_key"]
            comment_text = args["comment"]
            visibility = args.get("visibility", "all")
            
            # Build comment data
            comment_data = {"body": comment_text}
            
            # Add visibility restrictions if needed
            if visibility != "all":
                # This would need to be implemented based on Jira instance configuration
                # For now, we'll just add the comment as public
                pass
            
            # Add the comment
            comment = await self.jira_client.add_comment(issue_key, comment_data)
            
            result = {
                "success": True,
                "issue_key": issue_key,
                "comment_id": comment.id,
                "message": f"Successfully added comment to issue {issue_key}"
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        except JiraClientError as e:
            return [TextContent(type="text", text=f"Error adding comment: {e}")]
    
    async def _handle_add_attachment(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle add attachment request."""
        try:
            issue_key = args["issue_key"]
            file_path = args["file_path"]
            filename = args.get("filename")
            
            # Verify file exists
            import os
            if not os.path.exists(file_path):
                return [TextContent(type="text", text=f"Error: File not found: {file_path}")]
            
            # Add the attachment
            attachment = await self.jira_client.add_attachment(issue_key, file_path, filename)
            
            result = {
                "success": True,
                "issue_key": issue_key,
                "attachment_id": attachment.id,
                "filename": attachment.filename,
                "size": attachment.size,
                "message": f"Successfully added attachment to issue {issue_key}"
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        except JiraClientError as e:
            return [TextContent(type="text", text=f"Error adding attachment: {e}")]
    
    async def _handle_get_github_repositories(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle get GitHub repositories request."""
        try:
            if not self.config.github.enabled or not self.config.github.api_token:
                return [TextContent(type="text", text="GitHub integration is not enabled or configured")]
            
            from github_client import GitHubClient
            
            async with GitHubClient(self.config.github.api_token, self.config.github.base_url) as github_client:
                organization = args.get("organization")
                user = args.get("user")
                
                repositories = await github_client.get_repositories(org=organization, user=user)
                
                result = {
                    "repositories": [
                        {
                            "id": repo.id,
                            "name": repo.name,
                            "full_name": repo.full_name,
                            "owner": repo.owner,
                            "description": repo.description,
                            "private": repo.private,
                            "html_url": repo.html_url,
                            "language": repo.language,
                            "stargazers_count": repo.stargazers_count,
                            "forks_count": repo.forks_count,
                            "open_issues_count": repo.open_issues_count
                        }
                        for repo in repositories
                    ],
                    "count": len(repositories)
                }
                
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        except Exception as e:
            return [TextContent(type="text", text=f"Error retrieving GitHub repositories: {e}")]
    
    async def _handle_analyze_cross_platform_metrics(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle cross-platform metrics analysis request."""
        try:
            if not self.config.github.enabled or not self.config.github.api_token:
                return [TextContent(type="text", text="GitHub integration is required for cross-platform analysis")]
            
            from github_client import GitHubClient
            from cross_platform_analytics import CrossPlatformAnalytics
            from jira_mcp_server.models import FilterCriteria
            
            team_name = args["team_name"]
            jira_projects = args.get("jira_projects", ["OCM"])
            github_repositories = args.get("github_repositories", ["openshift/cluster-manager"])
            period_days = args.get("period_days", 30)
            
            # Calculate date range
            period_end = datetime.now()
            period_start = period_end - timedelta(days=period_days)
            
            # Get Jira issues
            criteria = FilterCriteria(
                projects=jira_projects,
                updated_after=period_start
            )
            jira_issues = await self.jira_client.get_issues(criteria)
            
            # Analyze with GitHub data
            async with GitHubClient(self.config.github.api_token, self.config.github.base_url) as github_client:
                analytics = CrossPlatformAnalytics(self.jira_client, github_client)
                
                pipelines = await analytics.analyze_delivery_pipelines(
                    jira_issues, github_repositories, period_start, period_end
                )
                
                team_metrics = await analytics.calculate_team_metrics(
                    team_name, pipelines, period_start, period_end
                )
                
                insights = await analytics.generate_cross_platform_insights(team_metrics)
                
                result = {
                    "team_name": team_name,
                    "period": {
                        "start": period_start.isoformat(),
                        "end": period_end.isoformat(),
                        "days": period_days
                    },
                    "metrics": {
                        "issues_completed": team_metrics.issues_completed,
                        "story_points_completed": team_metrics.story_points_completed,
                        "pull_requests_merged": team_metrics.pull_requests_merged,
                        "average_cycle_time": team_metrics.average_cycle_time,
                        "cross_platform_correlation": team_metrics.cross_platform_correlation,
                        "quality_score": team_metrics.first_time_quality,
                        "deployment_frequency": team_metrics.deployment_frequency
                    },
                    "pipelines_analyzed": len(pipelines),
                    "developers_active": len(team_metrics.developers),
                    "insights": insights
                }
                
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        except Exception as e:
            return [TextContent(type="text", text=f"Error analyzing cross-platform metrics: {e}")]
    
    async def _handle_generate_analytics_dashboard(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle analytics dashboard generation request."""
        try:
            if not self.config.github.enabled or not self.config.github.api_token:
                return [TextContent(type="text", text="GitHub integration is required for analytics dashboard")]
            
            from github_client import GitHubClient
            from cross_platform_analytics import CrossPlatformAnalytics
            from dashboard_generator import DashboardGenerator
            from jira_mcp_server.models import FilterCriteria
            
            team_name = args["team_name"]
            dashboard_type = args.get("dashboard_type", "executive")
            jira_projects = args.get("jira_projects", ["OCM"])
            github_repositories = args.get("github_repositories", ["openshift/cluster-manager"])
            period_days = args.get("period_days", 30)
            
            # Calculate date range
            period_end = datetime.now()
            period_start = period_end - timedelta(days=period_days)
            
            # Get Jira issues
            criteria = FilterCriteria(
                projects=jira_projects,
                updated_after=period_start
            )
            jira_issues = await self.jira_client.get_issues(criteria)
            
            # Analyze with GitHub data
            async with GitHubClient(self.config.github.api_token, self.config.github.base_url) as github_client:
                analytics = CrossPlatformAnalytics(self.jira_client, github_client)
                
                pipelines = await analytics.analyze_delivery_pipelines(
                    jira_issues, github_repositories, period_start, period_end
                )
                
                team_metrics = await analytics.calculate_team_metrics(
                    team_name, pipelines, period_start, period_end
                )
                
                insights = await analytics.generate_cross_platform_insights(team_metrics)
                
                # Generate dashboard
                dashboard_generator = DashboardGenerator()
                
                if dashboard_type == "executive":
                    dashboard_path = await dashboard_generator.generate_executive_dashboard(team_metrics, insights)
                elif dashboard_type == "detailed":
                    dashboard_path = await dashboard_generator.generate_detailed_analytics(team_metrics, insights)
                elif dashboard_type == "developer":
                    dashboard_path = await dashboard_generator.generate_developer_dashboard(team_metrics.developers, team_name)
                elif dashboard_type == "html":
                    dashboard_path = await dashboard_generator.generate_html_dashboard(team_metrics, insights)
                else:
                    return [TextContent(type="text", text=f"Unknown dashboard type: {dashboard_type}")]
                
                result = {
                    "dashboard_generated": True,
                    "dashboard_type": dashboard_type,
                    "file_path": dashboard_path,
                    "team_name": team_name,
                    "metrics_summary": {
                        "issues_completed": team_metrics.issues_completed,
                        "pipelines_analyzed": len(pipelines),
                        "developers_active": len(team_metrics.developers),
                        "cross_platform_correlation": team_metrics.cross_platform_correlation
                    }
                }
                
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        except Exception as e:
            return [TextContent(type="text", text=f"Error generating analytics dashboard: {e}")]
    
    async def run(self, transport_type: str = "stdio") -> None:
        """Run the MCP server."""
        if transport_type == "stdio":
            from mcp.server.stdio import stdio_server
            
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream, write_stream, self.server.create_initialization_options()
                )
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")