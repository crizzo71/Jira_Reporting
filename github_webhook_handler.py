"""
GitHub Webhook Handler for Real-Time Updates

Provides webhook integration for:
- Real-time Jira-GitHub correlation updates
- Automatic pipeline status updates
- Developer activity tracking
- Quality metrics calculation
- Dashboard refresh triggers
"""

import asyncio
import json
import hashlib
import hmac
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

import aiohttp
from aiohttp import web

from github_client import GitHubClient
from cross_platform_analytics import CrossPlatformAnalytics
from enhanced_config import Config

logger = logging.getLogger(__name__)


class WebhookEventType(Enum):
    """GitHub webhook event types we handle."""
    PUSH = "push"
    PULL_REQUEST = "pull_request"
    PULL_REQUEST_REVIEW = "pull_request_review"
    ISSUES = "issues"
    ISSUE_COMMENT = "issue_comment"
    CREATE = "create"  # Branch/tag creation
    DELETE = "delete"  # Branch/tag deletion


@dataclass
class WebhookEvent:
    """Processed webhook event data."""
    event_type: WebhookEventType
    repository: str
    timestamp: datetime
    actor: str
    
    # Event-specific data
    commits: List[Dict[str, Any]] = None
    pull_request: Dict[str, Any] = None
    issue: Dict[str, Any] = None
    review: Dict[str, Any] = None
    
    # Correlation data
    jira_keys: List[str] = None
    correlation_confidence: float = 0.0


class GitHubWebhookHandler:
    """Handle GitHub webhooks for real-time integration."""
    
    def __init__(self, config: Config, github_client: GitHubClient = None):
        self.config = config
        self.github_client = github_client
        self.app = web.Application()
        self.setup_routes()
        
        # Event handlers
        self.event_handlers = {
            WebhookEventType.PUSH: self._handle_push_event,
            WebhookEventType.PULL_REQUEST: self._handle_pull_request_event,
            WebhookEventType.PULL_REQUEST_REVIEW: self._handle_review_event,
            WebhookEventType.ISSUES: self._handle_issues_event,
            WebhookEventType.ISSUE_COMMENT: self._handle_comment_event,
        }
        
        # Correlation patterns for Jira key extraction
        self.jira_patterns = [
            r"(?i)(?:fix|fixes|fixed|close|closes|closed|resolve|resolves|resolved)\s+([A-Z]+-\d+)",
            r"([A-Z]+-\d+)"
        ]
    
    def setup_routes(self):
        """Setup webhook routes."""
        self.app.router.add_post('/webhook', self.handle_webhook)
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/status', self.webhook_status)
    
    async def handle_webhook(self, request: web.Request) -> web.Response:
        """Main webhook handler."""
        try:
            # Verify webhook signature
            if not await self._verify_signature(request):
                logger.warning("Invalid webhook signature")
                return web.Response(text="Invalid signature", status=401)
            
            # Get event type and payload
            event_type = request.headers.get('X-GitHub-Event')
            payload = await request.json()
            
            if not event_type:
                return web.Response(text="Missing event type", status=400)
            
            # Process the event
            webhook_event = await self._process_webhook_event(event_type, payload)
            
            if webhook_event:
                # Handle the event
                await self._handle_event(webhook_event)
                
                logger.info(f"Processed {event_type} event for {webhook_event.repository}")
                return web.Response(text="Event processed", status=200)
            else:
                logger.info(f"Ignored {event_type} event (not relevant)")
                return web.Response(text="Event ignored", status=200)
        
        except Exception as e:
            logger.error(f"Webhook processing error: {e}", exc_info=True)
            return web.Response(text="Internal error", status=500)
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.Response(text="OK", status=200)
    
    async def webhook_status(self, request: web.Request) -> web.Response:
        """Webhook status endpoint."""
        status = {
            "webhook_handler": "active",
            "github_integration": self.config.github.enabled,
            "jira_integration": True,
            "supported_events": [e.value for e in WebhookEventType],
            "correlation_patterns": len(self.jira_patterns)
        }
        return web.Response(text=json.dumps(status, indent=2), 
                           content_type='application/json')
    
    async def _verify_signature(self, request: web.Request) -> bool:
        """Verify GitHub webhook signature."""
        if not self.config.github.webhook_secret:
            logger.warning("No webhook secret configured, skipping verification")
            return True
        
        signature = request.headers.get('X-Hub-Signature-256')
        if not signature:
            return False
        
        body = await request.read()
        expected_signature = hmac.new(
            self.config.github.webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    
    async def _process_webhook_event(self, event_type: str, payload: Dict[str, Any]) -> Optional[WebhookEvent]:
        """Process raw webhook payload into structured event."""
        try:
            webhook_event_type = WebhookEventType(event_type)
        except ValueError:
            # Unknown event type
            return None
        
        repository = payload.get('repository', {}).get('full_name', 'unknown')
        timestamp = datetime.now()
        
        # Extract actor based on event type
        actor = "unknown"
        if 'sender' in payload:
            actor = payload['sender'].get('login', 'unknown')
        elif 'pusher' in payload:
            actor = payload['pusher'].get('name', 'unknown')
        
        event = WebhookEvent(
            event_type=webhook_event_type,
            repository=repository,
            timestamp=timestamp,
            actor=actor
        )
        
        # Extract event-specific data and correlate with Jira
        if webhook_event_type == WebhookEventType.PUSH:
            event.commits = payload.get('commits', [])
            event.jira_keys = self._extract_jira_keys_from_commits(event.commits)
            
        elif webhook_event_type == WebhookEventType.PULL_REQUEST:
            event.pull_request = payload.get('pull_request', {})
            pr_text = f"{event.pull_request.get('title', '')} {event.pull_request.get('body', '')}"
            event.jira_keys = self._extract_jira_keys_from_text(pr_text)
            
        elif webhook_event_type == WebhookEventType.ISSUES:
            event.issue = payload.get('issue', {})
            issue_text = f"{event.issue.get('title', '')} {event.issue.get('body', '')}"
            event.jira_keys = self._extract_jira_keys_from_text(issue_text)
        
        # Calculate correlation confidence
        if event.jira_keys:
            event.correlation_confidence = self._calculate_correlation_confidence(event)
        
        return event
    
    def _extract_jira_keys_from_commits(self, commits: List[Dict[str, Any]]) -> List[str]:
        """Extract Jira keys from commit messages."""
        jira_keys = set()
        
        for commit in commits:
            message = commit.get('message', '')
            keys = self._extract_jira_keys_from_text(message)
            jira_keys.update(keys)
        
        return list(jira_keys)
    
    def _extract_jira_keys_from_text(self, text: str) -> List[str]:
        """Extract Jira keys from text using regex patterns."""
        import re
        
        if not text:
            return []
        
        jira_keys = set()
        
        for pattern in self.jira_patterns:
            matches = re.findall(pattern, text)
            jira_keys.update(matches)
        
        return list(jira_keys)
    
    def _calculate_correlation_confidence(self, event: WebhookEvent) -> float:
        """Calculate confidence score for Jira correlation."""
        if not event.jira_keys:
            return 0.0
        
        confidence = 0.5  # Base confidence
        
        # Higher confidence for explicit fix/close keywords
        text_to_check = ""
        if event.event_type == WebhookEventType.PUSH and event.commits:
            text_to_check = " ".join(commit.get('message', '') for commit in event.commits)
        elif event.event_type == WebhookEventType.PULL_REQUEST and event.pull_request:
            text_to_check = f"{event.pull_request.get('title', '')} {event.pull_request.get('body', '')}"
        elif event.event_type == WebhookEventType.ISSUES and event.issue:
            text_to_check = f"{event.issue.get('title', '')} {event.issue.get('body', '')}"
        
        if any(keyword in text_to_check.lower() for keyword in ['fix', 'close', 'resolve']):
            confidence += 0.3
        
        # Higher confidence for fewer Jira keys (more specific)
        if len(event.jira_keys) == 1:
            confidence += 0.2
        elif len(event.jira_keys) <= 3:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    async def _handle_event(self, event: WebhookEvent):
        """Handle processed webhook event."""
        try:
            # Log the event
            logger.info(f"Handling {event.event_type.value} event from {event.repository}")
            logger.info(f"Actor: {event.actor}, Jira keys: {event.jira_keys}")
            
            # Call appropriate handler
            handler = self.event_handlers.get(event.event_type)
            if handler:
                await handler(event)
            
            # Trigger analytics update if we have Jira correlation
            if event.jira_keys and event.correlation_confidence > 0.5:
                await self._trigger_analytics_update(event)
        
        except Exception as e:
            logger.error(f"Error handling {event.event_type.value} event: {e}", exc_info=True)
    
    async def _handle_push_event(self, event: WebhookEvent):
        """Handle push event."""
        if not event.commits:
            return
        
        logger.info(f"Processing {len(event.commits)} commits from {event.actor}")
        
        # Update commit tracking
        for commit in event.commits:
            commit_sha = commit.get('id', '')[:8]
            logger.info(f"  Commit {commit_sha}: {commit.get('message', '')[:50]}...")
        
        # If correlated with Jira, update pipeline status
        if event.jira_keys:
            logger.info(f"Commits correlated with Jira issues: {', '.join(event.jira_keys)}")
    
    async def _handle_pull_request_event(self, event: WebhookEvent):
        """Handle pull request event."""
        if not event.pull_request:
            return
        
        pr_number = event.pull_request.get('number')
        pr_action = event.pull_request.get('action', 'unknown')
        pr_state = event.pull_request.get('state', 'unknown')
        
        logger.info(f"PR #{pr_number} {pr_action} by {event.actor} (state: {pr_state})")
        
        # Track PR lifecycle for pipeline metrics
        if pr_action == 'opened':
            logger.info("  → Development to Review transition")
        elif pr_action == 'closed' and event.pull_request.get('merged'):
            logger.info("  → Review to Integration transition")
        
        # Update cross-platform correlation
        if event.jira_keys:
            logger.info(f"PR correlated with Jira issues: {', '.join(event.jira_keys)}")
    
    async def _handle_review_event(self, event: WebhookEvent):
        """Handle pull request review event."""
        logger.info(f"PR review by {event.actor}")
        
        # Track review metrics for quality analysis
        if event.jira_keys:
            logger.info(f"Review correlated with Jira issues: {', '.join(event.jira_keys)}")
    
    async def _handle_issues_event(self, event: WebhookEvent):
        """Handle GitHub issues event."""
        if not event.issue:
            return
        
        issue_number = event.issue.get('number')
        issue_action = event.issue.get('action', 'unknown')
        
        logger.info(f"Issue #{issue_number} {issue_action} by {event.actor}")
        
        # Track GitHub issue correlation with Jira
        if event.jira_keys:
            logger.info(f"GitHub issue correlated with Jira issues: {', '.join(event.jira_keys)}")
    
    async def _handle_comment_event(self, event: WebhookEvent):
        """Handle issue/PR comment event."""
        logger.info(f"Comment added by {event.actor}")
        
        # Track collaboration metrics
        if event.jira_keys:
            logger.info(f"Comment correlated with Jira issues: {', '.join(event.jira_keys)}")
    
    async def _trigger_analytics_update(self, event: WebhookEvent):
        """Trigger analytics update for correlated events."""
        logger.info(f"Triggering analytics update for {', '.join(event.jira_keys)}")
        
        # Here you could:
        # 1. Update delivery pipeline status
        # 2. Recalculate team metrics
        # 3. Refresh dashboards
        # 4. Send notifications
        
        # For now, just log the trigger
        logger.info("Analytics update triggered (implementation pending)")
    
    async def start_server(self, host: str = '0.0.0.0', port: int = 8080):
        """Start the webhook server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"GitHub webhook server started on {host}:{port}")
        logger.info(f"Webhook URL: http://{host}:{port}/webhook")
        logger.info(f"Health check: http://{host}:{port}/health")
        
        return runner
    
    async def stop_server(self, runner):
        """Stop the webhook server."""
        await runner.cleanup()
        logger.info("GitHub webhook server stopped")


# Webhook server CLI
async def run_webhook_server():
    """Run standalone webhook server."""
    import argparse
    from enhanced_config import get_config
    
    parser = argparse.ArgumentParser(description='GitHub Webhook Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    config = get_config()
    
    if not config.github.enabled:
        logger.error("GitHub integration is not enabled")
        return
    
    webhook_handler = GitHubWebhookHandler(config)
    runner = await webhook_handler.start_server(args.host, args.port)
    
    try:
        # Keep the server running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down webhook server...")
    finally:
        await webhook_handler.stop_server(runner)


if __name__ == "__main__":
    asyncio.run(run_webhook_server())