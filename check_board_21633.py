#!/usr/bin/env python3
"""Check board 21633 specifically."""

import asyncio
from jira_mcp_server.config import get_config
from jira_mcp_server.jira_client import JiraClient

async def check_board_21633():
    """Check board 21633 across all projects."""
    try:
        config = get_config()
        client = JiraClient(config)
        
        await client.authenticate()
        
        print("🔍 Searching for board 21633...")
        
        # Get all boards and find 21633
        boards = await client.get_boards()
        
        target_board = None
        for board in boards:
            if board.id == 21633:
                target_board = board
                break
        
        if target_board:
            print(f"✅ Found board 21633!")
            print(f"   Name: {target_board.name}")
            print(f"   Type: {target_board.type}")
            print(f"   Project: {target_board.project_key}")
            
            # Get recent issues from this board
            print(f"\n📝 Getting recent issues from board 21633...")
            from jira_mcp_server.models import FilterCriteria
            from jira_mcp_server.rag_classifier import RAGClassifier
            
            # Query issues from this board
            criteria = FilterCriteria(
                boards=[21633],
                updated_since_days=7
            )
            
            issues = await client.get_issues(criteria)
            print(f"Found {len(issues)} recent issues from board 21633")
            
            if issues:
                # Apply RAG classification
                classifier = RAGClassifier(config.rag)
                classifier.classify_issues_batch(issues)
                
                print(f"\n📊 RAG Summary:")
                summary = classifier.get_rag_summary(issues)
                print(f"   🟢 Green: {summary['green']}")
                print(f"   🟡 Amber: {summary['amber']}")
                print(f"   🔴 Red: {summary['red']}")
                print(f"   Total: {summary['total']}")
                
                print(f"\nFirst 5 recent issues:")
                for issue in issues[:5]:
                    rag_emoji = {"red": "🔴", "amber": "🟡", "green": "🟢"}
                    emoji = rag_emoji.get(issue.rag_status.value if issue.rag_status else "green", "⚪")
                    print(f"  {emoji} {issue.key}: {issue.summary[:60]}...")
                    print(f"    Status: {issue.status.name} ({issue.days_in_status} days)")
                    print(f"    Assignee: {issue.assignee.display_name if issue.assignee else 'Unassigned'}")
                    if issue.rag_reason:
                        print(f"    RAG Reason: {issue.rag_reason}")
                    print()
                    
            return target_board
        else:
            print("❌ Board 21633 not found in accessible boards")
            return None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(check_board_21633())