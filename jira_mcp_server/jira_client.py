"""Jira API client for MCP server."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
from jira import JIRA
from jira.exceptions import JIRAError

from .config import Config
from .models import (
    Issue, Board, Project, User, IssueStatus, IssueType, 
    StatusTransition, FilterCriteria
)

logger = logging.getLogger(__name__)


class JiraClientError(Exception):
    """Base exception for Jira client errors."""
    pass


class JiraAuthenticationError(JiraClientError):
    """Raised when Jira authentication fails."""
    pass


class JiraClient:
    """Async Jira API client with MCP integration."""
    
    def __init__(self, config: Config):
        self.config = config
        self._jira: Optional[JIRA] = None
        self._authenticated = False
    
    async def authenticate(self) -> None:
        """Authenticate with Jira using API token."""
        try:
            # Run JIRA connection in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            # For Jira Server, try PAT authentication first, then fall back to basic auth
            try:
                # Try PAT authentication (Jira Server)
                self._jira = await loop.run_in_executor(
                    None,
                    lambda: JIRA(
                        server=self.config.jira.server,
                        token_auth=self.config.jira.api_token,
                        options={'verify': True, 'timeout': 30}
                    )
                )
            except Exception:
                # Fall back to basic auth (Jira Cloud)
                self._jira = await loop.run_in_executor(
                    None,
                    lambda: JIRA(
                        server=self.config.jira.server,
                        basic_auth=(self.config.jira.email, self.config.jira.api_token),
                        options={'verify': True, 'timeout': 30}
                    )
                )
            
            # Test authentication by getting current user
            await loop.run_in_executor(None, lambda: self._jira.current_user())
            self._authenticated = True
            logger.info(f"Successfully authenticated with Jira at {self.config.jira.server}")
            
        except JIRAError as e:
            self._authenticated = False
            if e.status_code == 401:
                raise JiraAuthenticationError(
                    f"Authentication failed: Invalid credentials for {self.config.jira.email}"
                ) from e
            elif e.status_code == 403:
                raise JiraAuthenticationError(
                    f"Authentication failed: Access denied for {self.config.jira.email}"
                ) from e
            else:
                raise JiraClientError(f"Jira connection failed: {e}") from e
        except Exception as e:
            self._authenticated = False
            raise JiraClientError(f"Unexpected error connecting to Jira: {e}") from e
    
    def _ensure_authenticated(self) -> None:
        """Ensure client is authenticated before API calls."""
        if not self._authenticated or not self._jira:
            raise JiraClientError("Not authenticated. Call authenticate() first.")
    
    async def get_projects(self) -> List[Project]:
        """Get all projects accessible to the authenticated user."""
        self._ensure_authenticated()
        
        try:
            loop = asyncio.get_event_loop()
            projects_data = await loop.run_in_executor(
                None, lambda: self._jira.projects()
            )
            
            projects = []
            for proj_data in projects_data:
                # Get detailed project info
                project_detail = await loop.run_in_executor(
                    None, lambda: self._jira.project(proj_data.key)
                )
                
                lead_user = None
                if hasattr(project_detail, 'lead') and project_detail.lead:
                    # Handle both Jira Server and Cloud user objects
                    account_id = getattr(project_detail.lead, 'accountId', 
                                       getattr(project_detail.lead, 'name', 
                                             getattr(project_detail.lead, 'key', 'unknown')))
                    display_name = getattr(project_detail.lead, 'displayName', 
                                         getattr(project_detail.lead, 'name', 'Unknown'))
                    email = getattr(project_detail.lead, 'emailAddress', None)
                    
                    lead_user = User(
                        account_id=str(account_id),
                        display_name=display_name,
                        email_address=email
                    )
                
                project = Project(
                    id=project_detail.id,
                    key=project_detail.key,
                    name=project_detail.name,
                    project_type=getattr(project_detail, 'projectTypeKey', 'unknown'),
                    lead=lead_user
                )
                projects.append(project)
            
            logger.info(f"Retrieved {len(projects)} projects")
            return projects
            
        except JIRAError as e:
            raise JiraClientError(f"Failed to retrieve projects: {e}") from e
    
    async def get_boards(self, project_keys: Optional[List[str]] = None) -> List[Board]:
        """Get all boards, optionally filtered by project keys."""
        self._ensure_authenticated()
        
        try:
            loop = asyncio.get_event_loop()
            
            # Get all boards
            boards_data = await loop.run_in_executor(
                None, lambda: self._jira.boards()
            )
            
            boards = []
            for board_data in boards_data:
                # Filter by project if specified
                if project_keys:
                    board_project = getattr(board_data, 'location', {}).get('projectKey')
                    if board_project and board_project not in project_keys:
                        continue
                
                board = Board(
                    id=board_data.id,
                    name=board_data.name,
                    type=board_data.type,
                    project_key=getattr(board_data, 'location', {}).get('projectKey'),
                    location=str(getattr(board_data, 'location', ''))
                )
                boards.append(board)
            
            logger.info(f"Retrieved {len(boards)} boards")
            return boards
            
        except JIRAError as e:
            raise JiraClientError(f"Failed to retrieve boards: {e}") from e
    
    async def get_issues(self, criteria: FilterCriteria) -> List[Issue]:
        """Get issues based on filter criteria."""
        self._ensure_authenticated()
        
        try:
            jql = self._build_jql(criteria)
            logger.info(f"Executing JQL: {jql}")
            
            loop = asyncio.get_event_loop()
            
            # Use search_issues with expand to get all necessary fields
            issues_data = await loop.run_in_executor(
                None, 
                lambda: self._jira.search_issues(
                    jql,
                    expand='changelog',
                    fields='*all',
                    maxResults=1000  # Adjust based on needs
                )
            )
            
            issues = []
            for issue_data in issues_data:
                issue = await self._convert_jira_issue(issue_data)
                issues.append(issue)
            
            logger.info(f"Retrieved {len(issues)} issues")
            return issues
            
        except JIRAError as e:
            raise JiraClientError(f"Failed to retrieve issues: {e}") from e
    
    def _build_jql(self, criteria: FilterCriteria) -> str:
        """Build JQL query from filter criteria."""
        if criteria.custom_jql:
            return criteria.custom_jql
        
        jql_parts = []
        
        # Project filter
        if criteria.projects:
            projects_str = ','.join(f'"{p}"' for p in criteria.projects)
            jql_parts.append(f"project in ({projects_str})")
        
        # Status filter
        if criteria.statuses:
            statuses_str = ','.join(f'"{s}"' for s in criteria.statuses)
            jql_parts.append(f"status in ({statuses_str})")
        
        # Assignee filter
        if criteria.assignees:
            assignees_str = ','.join(f'"{a}"' for a in criteria.assignees)
            jql_parts.append(f"assignee in ({assignees_str})")
        
        # Issue type filter
        if criteria.issue_types:
            types_str = ','.join(f'"{t}"' for t in criteria.issue_types)
            jql_parts.append(f"issuetype in ({types_str})")
        
        # Labels filter
        if criteria.labels:
            for label in criteria.labels:
                jql_parts.append(f'labels = "{label}"')
        
        # Date filters
        if criteria.created_after:
            jql_parts.append(f'created >= "{criteria.created_after.strftime("%Y-%m-%d")}"')
        if criteria.created_before:
            jql_parts.append(f'created <= "{criteria.created_before.strftime("%Y-%m-%d")}"')
        if criteria.updated_after:
            jql_parts.append(f'updated >= "{criteria.updated_after.strftime("%Y-%m-%d")}"')
        if criteria.updated_before:
            jql_parts.append(f'updated <= "{criteria.updated_before.strftime("%Y-%m-%d")}"')
        
        # Default ordering
        jql = ' AND '.join(jql_parts) if jql_parts else 'project is not EMPTY'
        jql += ' ORDER BY updated DESC'
        
        return jql
    
    async def _convert_jira_issue(self, issue_data: Any) -> Issue:
        """Convert Jira API issue data to our Issue model."""
        fields = issue_data.fields
        
        # Status
        status = IssueStatus(
            id=fields.status.id,
            name=fields.status.name,
            category=getattr(fields.status.statusCategory, 'name', 'Unknown')
        )
        
        # Issue type
        issue_type = IssueType(
            id=fields.issuetype.id,
            name=fields.issuetype.name,
            icon_url=getattr(fields.issuetype, 'iconUrl', None)
        )
        
        # Assignee - handle both Jira Server and Cloud
        assignee = None
        if fields.assignee:
            account_id = getattr(fields.assignee, 'accountId', 
                               getattr(fields.assignee, 'name', 
                                     getattr(fields.assignee, 'key', 'unknown')))
            display_name = getattr(fields.assignee, 'displayName', 
                                 getattr(fields.assignee, 'name', 'Unknown'))
            email = getattr(fields.assignee, 'emailAddress', None)
            
            assignee = User(
                account_id=str(account_id),
                display_name=display_name,
                email_address=email
            )
        
        # Reporter - handle both Jira Server and Cloud
        reporter_account_id = getattr(fields.reporter, 'accountId', 
                                    getattr(fields.reporter, 'name', 
                                          getattr(fields.reporter, 'key', 'unknown')))
        reporter_display_name = getattr(fields.reporter, 'displayName', 
                                      getattr(fields.reporter, 'name', 'Unknown'))
        reporter_email = getattr(fields.reporter, 'emailAddress', None)
        
        reporter = User(
            account_id=str(reporter_account_id),
            display_name=reporter_display_name,
            email_address=reporter_email
        )
        
        # Dates
        created = datetime.fromisoformat(fields.created.replace('Z', '+00:00'))
        updated = datetime.fromisoformat(fields.updated.replace('Z', '+00:00'))
        resolved = None
        if fields.resolutiondate:
            resolved = datetime.fromisoformat(fields.resolutiondate.replace('Z', '+00:00'))
        
        # Labels and components
        labels = [label for label in getattr(fields, 'labels', [])]
        components = [comp.name for comp in getattr(fields, 'components', [])]
        
        # Story points
        story_points = getattr(fields, 'customfield_10016', None)  # Common story points field
        
        # Sprint information
        sprint = None
        sprint_field = getattr(fields, 'customfield_10020', None)  # Common sprint field
        if sprint_field and isinstance(sprint_field, list) and sprint_field:
            sprint = str(sprint_field[-1])  # Get current sprint
        
        # Calculate days in status (handle timezone awareness)
        now = datetime.now()
        if updated.tzinfo is not None:
            # If updated is timezone-aware, make now timezone-aware too
            from datetime import timezone
            now = now.replace(tzinfo=timezone.utc)
        days_in_status = (now - updated).days
        
        # Check for blockers (this might need customization based on Jira setup)
        is_blocked = 'blocked' in status.name.lower() or 'waiting' in status.name.lower()
        
        # Build issue URL
        url = f"{self.config.jira.server}/browse/{issue_data.key}"
        
        return Issue(
            key=issue_data.key,
            summary=fields.summary,
            description=getattr(fields, 'description', None),
            status=status,
            issue_type=issue_type,
            priority=fields.priority.name if fields.priority else 'Unknown',
            assignee=assignee,
            reporter=reporter,
            created=created,
            updated=updated,
            resolved=resolved,
            labels=labels,
            components=components,
            blockers=[],  # TODO: Implement blocker detection
            story_points=story_points,
            sprint=sprint,
            days_in_status=days_in_status,
            is_blocked=is_blocked,
            url=url
        )
    
    async def get_status_transitions(
        self, 
        issue_keys: List[str], 
        since: Optional[datetime] = None
    ) -> List[StatusTransition]:
        """Get status transitions for specified issues."""
        self._ensure_authenticated()
        
        transitions = []
        loop = asyncio.get_event_loop()
        
        for issue_key in issue_keys:
            try:
                issue = await loop.run_in_executor(
                    None, 
                    lambda: self._jira.issue(issue_key, expand='changelog')
                )
                
                if hasattr(issue, 'changelog'):
                    for history in issue.changelog.histories:
                        created = datetime.fromisoformat(history.created.replace('Z', '+00:00'))
                        
                        if since and created < since:
                            continue
                        
                        for item in history.items:
                            if item.field == 'status':
                                # Handle both Jira Server and Cloud author objects
                                author_account_id = getattr(history.author, 'accountId', 
                                                          getattr(history.author, 'name', 
                                                                getattr(history.author, 'key', 'unknown')))
                                author_display_name = getattr(history.author, 'displayName', 
                                                            getattr(history.author, 'name', 'Unknown'))
                                author_email = getattr(history.author, 'emailAddress', None)
                                
                                author = User(
                                    account_id=str(author_account_id),
                                    display_name=author_display_name,
                                    email_address=author_email
                                )
                                
                                transition = StatusTransition(
                                    issue_key=issue_key,
                                    from_status=item.fromString,
                                    to_status=item.toString,
                                    transition_date=created,
                                    author=author
                                )
                                transitions.append(transition)
                
            except JIRAError as e:
                logger.warning(f"Failed to get transitions for {issue_key}: {e}")
                continue
        
        return transitions
    
    async def get_issue(self, issue_key: str) -> Issue:
        """Get a single issue by key."""
        self._ensure_authenticated()
        
        try:
            loop = asyncio.get_event_loop()
            issue_data = await loop.run_in_executor(
                None, 
                lambda: self._jira.issue(issue_key, expand='changelog', fields='*all')
            )
            
            return await self._convert_jira_issue(issue_data)
            
        except JIRAError as e:
            raise JiraClientError(f"Failed to retrieve issue {issue_key}: {e}") from e
    
    async def create_issue(self, issue_data: Dict[str, Any]) -> Issue:
        """Create a new Jira issue."""
        self._ensure_authenticated()
        
        try:
            loop = asyncio.get_event_loop()
            
            # Create the issue
            created_issue = await loop.run_in_executor(
                None, 
                lambda: self._jira.create_issue(fields=issue_data)
            )
            
            # Return the created issue as our Issue model
            return await self._convert_jira_issue(created_issue)
            
        except JIRAError as e:
            raise JiraClientError(f"Failed to create issue: {e}") from e
    
    async def update_issue(self, issue_key: str, update_data: Dict[str, Any]) -> None:
        """Update an existing Jira issue."""
        self._ensure_authenticated()
        
        try:
            loop = asyncio.get_event_loop()
            
            # Update the issue
            await loop.run_in_executor(
                None, 
                lambda: self._jira.issue(issue_key).update(fields=update_data)
            )
            
        except JIRAError as e:
            raise JiraClientError(f"Failed to update issue {issue_key}: {e}") from e
    
    async def transition_issue(self, issue_key: str, status_name: str) -> None:
        """Transition an issue to a new status."""
        self._ensure_authenticated()
        
        try:
            loop = asyncio.get_event_loop()
            
            # Get available transitions
            issue = await loop.run_in_executor(
                None, lambda: self._jira.issue(issue_key)
            )
            transitions = await loop.run_in_executor(
                None, lambda: self._jira.transitions(issue)
            )
            
            # Find matching transition
            transition_id = None
            for transition in transitions:
                if transition['to']['name'].lower() == status_name.lower():
                    transition_id = transition['id']
                    break
            
            if not transition_id:
                available = [t['to']['name'] for t in transitions]
                raise JiraClientError(
                    f"Status '{status_name}' not available for issue {issue_key}. "
                    f"Available: {', '.join(available)}"
                )
            
            # Execute transition
            await loop.run_in_executor(
                None, lambda: self._jira.transition_issue(issue, transition_id)
            )
            
        except JIRAError as e:
            raise JiraClientError(f"Failed to transition issue {issue_key}: {e}") from e
    
    async def add_comment(self, issue_key: str, comment_data: Dict[str, Any]) -> Any:
        """Add a comment to an issue."""
        self._ensure_authenticated()
        
        try:
            loop = asyncio.get_event_loop()
            
            # Add the comment
            comment = await loop.run_in_executor(
                None, 
                lambda: self._jira.add_comment(issue_key, comment_data['body'])
            )
            
            return comment
            
        except JIRAError as e:
            raise JiraClientError(f"Failed to add comment to issue {issue_key}: {e}") from e
    
    async def add_attachment(self, issue_key: str, file_path: str, filename: Optional[str] = None) -> Any:
        """Add an attachment to an issue."""
        self._ensure_authenticated()
        
        try:
            loop = asyncio.get_event_loop()
            
            # Add the attachment
            with open(file_path, 'rb') as file:
                attachment = await loop.run_in_executor(
                    None, 
                    lambda: self._jira.add_attachment(
                        issue=issue_key, 
                        attachment=file,
                        filename=filename
                    )
                )
            
            return attachment
            
        except JIRAError as e:
            raise JiraClientError(f"Failed to add attachment to issue {issue_key}: {e}") from e
        except IOError as e:
            raise JiraClientError(f"Failed to read file {file_path}: {e}") from e
    
    async def link_to_epic(self, issue_key: str, epic_key: str) -> None:
        """Link an issue to an epic."""
        self._ensure_authenticated()
        
        try:
            loop = asyncio.get_event_loop()
            
            # This is typically done through a custom field
            # The exact field name varies by Jira configuration
            epic_link_field = "customfield_10014"  # Common epic link field
            
            await loop.run_in_executor(
                None, 
                lambda: self._jira.issue(issue_key).update(
                    fields={epic_link_field: epic_key}
                )
            )
            
        except JIRAError as e:
            raise JiraClientError(f"Failed to link issue {issue_key} to epic {epic_key}: {e}") from e