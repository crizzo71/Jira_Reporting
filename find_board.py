#!/usr/bin/env python3
"""Find board 21634 across all accessible projects."""

import asyncio
from jira_mcp_server.config import get_config
from jira_mcp_server.jira_client import JiraClient

async def find_board_21634():
    """Find board 21634 across all projects."""
    try:
        config = get_config()
        client = JiraClient(config)
        
        await client.authenticate()
        
        print("🔍 Searching for board 21634 across all accessible boards...")
        
        # Get all boards (no project filter)
        boards = await client.get_boards()
        
        target_board = None
        for board in boards:
            if board.id == 21634:
                target_board = board
                break
        
        if target_board:
            print(f"✅ Found board 21634!")
            print(f"   Name: {target_board.name}")
            print(f"   Type: {target_board.type}")
            print(f"   Project: {target_board.project_key}")
            
            # Now let's get issues from this board
            print(f"\n📝 Getting recent issues from board 21634...")
            from jira_mcp_server.models import FilterCriteria
            
            # Use board-specific query
            criteria = FilterCriteria(
                boards=[21634],
                updated_since_days=7
            )
            
            issues = await client.get_issues(criteria)
            print(f"Found {len(issues)} recent issues from this board")
            
            if issues:
                print("\nFirst 5 recent issues:")
                for issue in issues[:5]:
                    print(f"  - {issue.key}: {issue.summary[:60]}...")
                    print(f"    Status: {issue.status.name}")
                    print(f"    Assignee: {issue.assignee.display_name if issue.assignee else 'Unassigned'}")
                    print()
        else:
            print("❌ Board 21634 not found in accessible boards")
            print("You might not have permission to access this board.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(find_board_21634())