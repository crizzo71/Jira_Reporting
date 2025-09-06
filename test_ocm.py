#!/usr/bin/env python3
"""Quick test script to query OCM project via MCP server."""

import asyncio
import json
from jira_mcp_server.config import get_config
from jira_mcp_server.jira_client import JiraClient
from jira_mcp_server.models import FilterCriteria
from jira_mcp_server.rag_classifier import RAGClassifier

async def test_ocm_project():
    """Test querying OCM project directly."""
    try:
        config = get_config()
        client = JiraClient(config)
        classifier = RAGClassifier(config.rag)
        
        print("🔐 Authenticating with Jira...")
        await client.authenticate()
        print("✅ Authentication successful!")
        
        print("\n📋 Getting boards for OCM project...")
        boards = await client.get_boards(["OCM"])
        print(f"Found {len(boards)} boards:")
        for board in boards:
            print(f"  - {board.id}: {board.name} ({board.type})")
        
        print("\n📝 Getting recent issues from OCM...")
        criteria = FilterCriteria(
            projects=["OCM"],
            updated_since_days=7  # Last week
        )
        issues = await client.get_issues(criteria)
        print(f"Found {len(issues)} recent issues")
        
        if issues:
            print("\nApplying RAG classification...")
            classifier.classify_issues_batch(issues)
            
            # Show first 5 issues
            print(f"\nFirst 5 issues:")
            for issue in issues[:5]:
                rag_emoji = {"red": "🔴", "amber": "🟡", "green": "🟢"}
                emoji = rag_emoji.get(issue.rag_status.value if issue.rag_status else "green", "⚪")
                print(f"  {emoji} {issue.key}: {issue.summary[:60]}...")
                if issue.assignee:
                    print(f"     Assignee: {issue.assignee.display_name}")
                print(f"     Status: {issue.status.name} ({issue.days_in_status} days)")
                if issue.rag_reason:
                    print(f"     RAG Reason: {issue.rag_reason}")
                print()
        
        # RAG Summary
        if issues:
            summary = classifier.get_rag_summary(issues)
            print(f"📊 RAG Summary:")
            print(f"   🟢 Green: {summary['green']}")
            print(f"   🟡 Amber: {summary['amber']}")
            print(f"   🔴 Red: {summary['red']}")
            print(f"   Total: {summary['total']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ocm_project())