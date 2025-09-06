"""
GitHub API Client for Jira Reports Simplified

Provides GitHub integration for cross-platform analytics:
- Repository information and statistics
- Issue tracking and correlation with Jira
- Pull request metrics and delivery tracking
- Commit activity and developer productivity
- Webhook support for real-time updates
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class GitHubClientError(Exception):
    """Base exception for GitHub client errors."""
    pass


class GitHubAuthenticationError(GitHubClientError):
    """Raised when GitHub authentication fails."""
    pass


class GitHubRateLimitError(GitHubClientError):
    """Raised when GitHub API rate limit is exceeded."""
    pass


@dataclass
class GitHubRepository:
    """GitHub repository information."""
    id: int
    name: str
    full_name: str
    owner: str
    description: Optional[str]
    private: bool
    clone_url: str
    html_url: str
    default_branch: str
    language: Optional[str]
    size: int
    stargazers_count: int
    watchers_count: int
    forks_count: int
    open_issues_count: int
    created_at: datetime
    updated_at: datetime
    pushed_at: Optional[datetime]


@dataclass
class GitHubIssue:
    """GitHub issue information."""
    id: int
    number: int
    title: str
    body: Optional[str]
    state: str  # open, closed
    user: str
    assignee: Optional[str]
    assignees: List[str]
    labels: List[str]
    milestone: Optional[str]
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    html_url: str
    repository: str
    comments: int
    
    # Correlation fields for Jira integration
    jira_issue_key: Optional[str] = None
    correlation_confidence: Optional[float] = None


@dataclass
class GitHubPullRequest:
    """GitHub pull request information."""
    id: int
    number: int
    title: str
    body: Optional[str]
    state: str  # open, closed, merged
    user: str
    assignee: Optional[str]
    assignees: List[str]
    reviewers: List[str]
    labels: List[str]
    milestone: Optional[str]
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    merged_at: Optional[datetime]
    html_url: str
    repository: str
    base_branch: str
    head_branch: str
    commits: int
    additions: int
    deletions: int
    changed_files: int
    comments: int
    review_comments: int
    
    # Correlation fields
    jira_issue_keys: List[str]
    correlation_confidence: Optional[float] = None


@dataclass
class GitHubCommit:
    """GitHub commit information."""
    sha: str
    message: str
    author: str
    author_email: str
    committer: str
    committer_email: str
    authored_date: datetime
    committed_date: datetime
    html_url: str
    repository: str
    additions: int
    deletions: int
    total: int
    
    # Correlation fields
    jira_issue_keys: List[str]


@dataclass
class GitHubStats:
    """GitHub repository statistics."""
    repository: str
    total_commits: int
    total_contributors: int
    total_issues: int
    open_issues: int
    closed_issues: int
    total_pull_requests: int
    open_pull_requests: int
    merged_pull_requests: int
    closed_pull_requests: int
    lines_of_code: int
    primary_language: Optional[str]
    languages: Dict[str, int]


class GitHubClient:
    """Async GitHub API client for integration with Jira reports."""
    
    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        self.token = token
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_remaining = 5000
        self._rate_limit_reset = datetime.now()
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def _ensure_session(self):
        """Ensure aiohttp session is created."""
        if self.session is None or self.session.closed:
            headers = {
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Jira-Reports-Simplified/1.0'
            }
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _check_rate_limit(self):
        """Check and handle GitHub API rate limits."""
        if self._rate_limit_remaining <= 10:
            wait_time = (self._rate_limit_reset - datetime.now()).total_seconds()
            if wait_time > 0:
                logger.warning(f"GitHub rate limit low, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to GitHub API."""
        await self._ensure_session()
        await self._check_rate_limit()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                # Update rate limit info
                self._rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
                reset_timestamp = int(response.headers.get('X-RateLimit-Reset', 0))
                self._rate_limit_reset = datetime.fromtimestamp(reset_timestamp)
                
                if response.status == 401:
                    raise GitHubAuthenticationError("Invalid GitHub token")
                elif response.status == 403:
                    if 'rate limit' in (await response.text()).lower():
                        raise GitHubRateLimitError("GitHub API rate limit exceeded")
                    else:
                        raise GitHubAuthenticationError("GitHub access forbidden")
                elif response.status >= 400:
                    error_text = await response.text()
                    raise GitHubClientError(f"GitHub API error {response.status}: {error_text}")
                
                return await response.json()
                
        except aiohttp.ClientError as e:
            raise GitHubClientError(f"GitHub API request failed: {e}")
    
    async def authenticate(self) -> Dict[str, Any]:
        """Test authentication and get user info."""
        try:
            user_info = await self._make_request('GET', '/user')
            logger.info(f"GitHub authentication successful for user: {user_info.get('login')}")
            return user_info
        except Exception as e:
            logger.error(f"GitHub authentication failed: {e}")
            raise
    
    async def get_repository(self, owner: str, repo: str) -> GitHubRepository:
        """Get repository information."""
        repo_data = await self._make_request('GET', f'/repos/{owner}/{repo}')
        
        return GitHubRepository(
            id=repo_data['id'],
            name=repo_data['name'],
            full_name=repo_data['full_name'],
            owner=repo_data['owner']['login'],
            description=repo_data.get('description'),
            private=repo_data['private'],
            clone_url=repo_data['clone_url'],
            html_url=repo_data['html_url'],
            default_branch=repo_data['default_branch'],
            language=repo_data.get('language'),
            size=repo_data['size'],
            stargazers_count=repo_data['stargazers_count'],
            watchers_count=repo_data['watchers_count'],
            forks_count=repo_data['forks_count'],
            open_issues_count=repo_data['open_issues_count'],
            created_at=datetime.fromisoformat(repo_data['created_at'].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(repo_data['updated_at'].replace('Z', '+00:00')),
            pushed_at=datetime.fromisoformat(repo_data['pushed_at'].replace('Z', '+00:00')) if repo_data.get('pushed_at') else None
        )
    
    async def get_repositories(self, org: Optional[str] = None, user: Optional[str] = None) -> List[GitHubRepository]:
        """Get repositories for organization or user."""
        if org:
            endpoint = f'/orgs/{org}/repos'
        elif user:
            endpoint = f'/users/{user}/repos'
        else:
            endpoint = '/user/repos'
        
        repos_data = await self._make_request('GET', endpoint, params={'per_page': 100})
        
        repositories = []
        for repo_data in repos_data:
            repositories.append(GitHubRepository(
                id=repo_data['id'],
                name=repo_data['name'],
                full_name=repo_data['full_name'],
                owner=repo_data['owner']['login'],
                description=repo_data.get('description'),
                private=repo_data['private'],
                clone_url=repo_data['clone_url'],
                html_url=repo_data['html_url'],
                default_branch=repo_data['default_branch'],
                language=repo_data.get('language'),
                size=repo_data['size'],
                stargazers_count=repo_data['stargazers_count'],
                watchers_count=repo_data['watchers_count'],
                forks_count=repo_data['forks_count'],
                open_issues_count=repo_data['open_issues_count'],
                created_at=datetime.fromisoformat(repo_data['created_at'].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(repo_data['updated_at'].replace('Z', '+00:00')),
                pushed_at=datetime.fromisoformat(repo_data['pushed_at'].replace('Z', '+00:00')) if repo_data.get('pushed_at') else None
            ))
        
        return repositories
    
    async def get_issues(self, owner: str, repo: str, state: str = 'all', since: Optional[datetime] = None) -> List[GitHubIssue]:
        """Get issues for repository."""
        params = {
            'state': state,
            'per_page': 100
        }
        
        if since:
            params['since'] = since.isoformat()
        
        issues_data = await self._make_request('GET', f'/repos/{owner}/{repo}/issues', params=params)
        
        issues = []
        for issue_data in issues_data:
            # Skip pull requests (they appear in issues API)
            if 'pull_request' in issue_data:
                continue
                
            issues.append(GitHubIssue(
                id=issue_data['id'],
                number=issue_data['number'],
                title=issue_data['title'],
                body=issue_data.get('body'),
                state=issue_data['state'],
                user=issue_data['user']['login'],
                assignee=issue_data['assignee']['login'] if issue_data.get('assignee') else None,
                assignees=[a['login'] for a in issue_data.get('assignees', [])],
                labels=[l['name'] for l in issue_data.get('labels', [])],
                milestone=issue_data['milestone']['title'] if issue_data.get('milestone') else None,
                created_at=datetime.fromisoformat(issue_data['created_at'].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(issue_data['updated_at'].replace('Z', '+00:00')),
                closed_at=datetime.fromisoformat(issue_data['closed_at'].replace('Z', '+00:00')) if issue_data.get('closed_at') else None,
                html_url=issue_data['html_url'],
                repository=f"{owner}/{repo}",
                comments=issue_data['comments']
            ))
        
        return issues
    
    async def get_pull_requests(self, owner: str, repo: str, state: str = 'all', since: Optional[datetime] = None) -> List[GitHubPullRequest]:
        """Get pull requests for repository."""
        params = {
            'state': state,
            'per_page': 100
        }
        
        if since:
            params['since'] = since.isoformat()
        
        prs_data = await self._make_request('GET', f'/repos/{owner}/{repo}/pulls', params=params)
        
        pull_requests = []
        for pr_data in prs_data:
            # Get detailed PR info for metrics
            pr_detail = await self._make_request('GET', f'/repos/{owner}/{repo}/pulls/{pr_data["number"]}')
            
            pull_requests.append(GitHubPullRequest(
                id=pr_data['id'],
                number=pr_data['number'],
                title=pr_data['title'],
                body=pr_data.get('body'),
                state=pr_data['state'],
                user=pr_data['user']['login'],
                assignee=pr_data['assignee']['login'] if pr_data.get('assignee') else None,
                assignees=[a['login'] for a in pr_data.get('assignees', [])],
                reviewers=[r['login'] for r in pr_data.get('requested_reviewers', [])],
                labels=[l['name'] for l in pr_data.get('labels', [])],
                milestone=pr_data['milestone']['title'] if pr_data.get('milestone') else None,
                created_at=datetime.fromisoformat(pr_data['created_at'].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(pr_data['updated_at'].replace('Z', '+00:00')),
                closed_at=datetime.fromisoformat(pr_data['closed_at'].replace('Z', '+00:00')) if pr_data.get('closed_at') else None,
                merged_at=datetime.fromisoformat(pr_data['merged_at'].replace('Z', '+00:00')) if pr_data.get('merged_at') else None,
                html_url=pr_data['html_url'],
                repository=f"{owner}/{repo}",
                base_branch=pr_data['base']['ref'],
                head_branch=pr_data['head']['ref'],
                commits=pr_detail.get('commits', 0),
                additions=pr_detail.get('additions', 0),
                deletions=pr_detail.get('deletions', 0),
                changed_files=pr_detail.get('changed_files', 0),
                comments=pr_detail.get('comments', 0),
                review_comments=pr_detail.get('review_comments', 0),
                jira_issue_keys=[]  # Will be populated by correlation
            ))
        
        return pull_requests
    
    async def get_commits(self, owner: str, repo: str, since: Optional[datetime] = None, until: Optional[datetime] = None) -> List[GitHubCommit]:
        """Get commits for repository."""
        params = {'per_page': 100}
        
        if since:
            params['since'] = since.isoformat()
        if until:
            params['until'] = until.isoformat()
        
        commits_data = await self._make_request('GET', f'/repos/{owner}/{repo}/commits', params=params)
        
        commits = []
        for commit_data in commits_data:
            # Get detailed commit info for metrics
            commit_detail = await self._make_request('GET', f'/repos/{owner}/{repo}/commits/{commit_data["sha"]}')
            
            commits.append(GitHubCommit(
                sha=commit_data['sha'],
                message=commit_data['commit']['message'],
                author=commit_data['commit']['author']['name'],
                author_email=commit_data['commit']['author']['email'],
                committer=commit_data['commit']['committer']['name'],
                committer_email=commit_data['commit']['committer']['email'],
                authored_date=datetime.fromisoformat(commit_data['commit']['author']['date'].replace('Z', '+00:00')),
                committed_date=datetime.fromisoformat(commit_data['commit']['committer']['date'].replace('Z', '+00:00')),
                html_url=commit_data['html_url'],
                repository=f"{owner}/{repo}",
                additions=commit_detail.get('stats', {}).get('additions', 0),
                deletions=commit_detail.get('stats', {}).get('deletions', 0),
                total=commit_detail.get('stats', {}).get('total', 0),
                jira_issue_keys=[]  # Will be populated by correlation
            ))
        
        return commits
    
    async def get_repository_stats(self, owner: str, repo: str) -> GitHubStats:
        """Get comprehensive repository statistics."""
        # Get basic repo info
        repo_info = await self.get_repository(owner, repo)
        
        # Get languages
        languages = await self._make_request('GET', f'/repos/{owner}/{repo}/languages')
        
        # Get issues and PRs for counts
        all_issues = await self.get_issues(owner, repo, state='all')
        all_prs = await self.get_pull_requests(owner, repo, state='all')
        
        # Get contributors
        contributors = await self._make_request('GET', f'/repos/{owner}/{repo}/contributors')
        
        # Calculate statistics
        open_issues = len([i for i in all_issues if i.state == 'open'])
        closed_issues = len([i for i in all_issues if i.state == 'closed'])
        
        open_prs = len([pr for pr in all_prs if pr.state == 'open'])
        merged_prs = len([pr for pr in all_prs if pr.merged_at is not None])
        closed_prs = len([pr for pr in all_prs if pr.state == 'closed' and pr.merged_at is None])
        
        total_lines = sum(languages.values()) if languages else 0
        primary_language = max(languages.items(), key=lambda x: x[1])[0] if languages else None
        
        return GitHubStats(
            repository=f"{owner}/{repo}",
            total_commits=len(await self.get_commits(owner, repo)),
            total_contributors=len(contributors),
            total_issues=len(all_issues),
            open_issues=open_issues,
            closed_issues=closed_issues,
            total_pull_requests=len(all_prs),
            open_pull_requests=open_prs,
            merged_pull_requests=merged_prs,
            closed_pull_requests=closed_prs,
            lines_of_code=total_lines,
            primary_language=primary_language,
            languages=languages
        )
    
    def extract_jira_keys_from_text(self, text: str) -> List[str]:
        """Extract Jira issue keys from text using regex."""
        import re
        
        if not text:
            return []
        
        # Common Jira project key patterns (2-10 uppercase letters followed by hyphen and numbers)
        jira_pattern = r'\b([A-Z]{2,10}-\d+)\b'
        matches = re.findall(jira_pattern, text)
        
        return list(set(matches))  # Remove duplicates
    
    async def correlate_with_jira(self, github_items: List[Union[GitHubIssue, GitHubPullRequest, GitHubCommit]]) -> List[Union[GitHubIssue, GitHubPullRequest, GitHubCommit]]:
        """Add Jira correlation data to GitHub items."""
        for item in github_items:
            # Extract Jira keys from title and body/message
            text_fields = []
            
            if isinstance(item, (GitHubIssue, GitHubPullRequest)):
                text_fields.extend([item.title, item.body or ''])
            elif isinstance(item, GitHubCommit):
                text_fields.append(item.message)
            
            all_text = ' '.join(text_fields)
            jira_keys = self.extract_jira_keys_from_text(all_text)
            
            # Update correlation fields
            if isinstance(item, GitHubIssue):
                if jira_keys:
                    item.jira_issue_key = jira_keys[0]  # Primary correlation
                    item.correlation_confidence = 0.8 if len(jira_keys) == 1 else 0.6
            elif isinstance(item, (GitHubPullRequest, GitHubCommit)):
                item.jira_issue_keys = jira_keys
                if jira_keys:
                    item.correlation_confidence = 0.9 if any(key in item.title for key in jira_keys) else 0.7
        
        return github_items