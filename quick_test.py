#!/usr/bin/env python3
"""Quick test for OCM project with minimal API calls."""

import asyncio
from jira_mcp_server.config import get_config
from jira_mcp_server.jira_client import JiraClient

async def test_ocm_minimal():
    """Test OCM project with minimal API calls."""
    try:
        config = get_config()
        client = JiraClient(config)
        
        print("🔐 Authenticating...")
        await client.authenticate()
        print("✅ Authenticated!")
        
        # Just get boards for OCM without detailed project info
        print("\n📋 Getting OCM boards...")
        boards = await client.get_boards(["OCM"])
        
        if boards:
            print(f"Found {len(boards)} OCM boards:")
            for board in boards:
                print(f"  - Board {board.id}: {board.name}")
        else:
            print("No OCM boards found. Let's try getting a few issues directly...")
            
            # Try direct JQL query for OCM
            from jira_mcp_server.models import FilterCriteria
            criteria = FilterCriteria(custom_jql="project = OCM ORDER BY updated DESC")
            
            print("🔍 Querying OCM issues directly...")
            issues = await client.get_issues(criteria)
            print(f"Found {len(issues)} OCM issues")
            
            if issues:
                print("First 3 issues:")
                for issue in issues[:3]:
                    print(f"  - {issue.key}: {issue.summary}")
                    print(f"    Status: {issue.status.name}")
                    print(f"    Assignee: {issue.assignee.display_name if issue.assignee else 'Unassigned'}")
                    print()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ocm_minimal())