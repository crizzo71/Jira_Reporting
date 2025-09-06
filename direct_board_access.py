#!/usr/bin/env python3
"""Direct access to board 21633."""

import asyncio
from jira_mcp_server.config import get_config
from jira_mcp_server.jira_client import JiraClient
from jira_mcp_server.models import FilterCriteria
from jira_mcp_server.rag_classifier import RAGClassifier
from jira_mcp_server.report_generator import ReportGenerator
from datetime import datetime, timedelta

async def access_board_21633():
    """Try to access board 21633 directly."""
    try:
        config = get_config()
        client = JiraClient(config)
        
        await client.authenticate()
        
        print("🎯 Attempting direct access to board 21633...")
        
        # Try to get issues from board 21633 directly using JQL
        print("📝 Querying issues from board 21633...")
        
        # Direct board query using JQL
        criteria = FilterCriteria(
            custom_jql=f"board = 21633 AND updated >= -{7}d ORDER BY updated DESC"
        )
        
        issues = await client.get_issues(criteria)
        
        if issues:
            print(f"✅ Successfully accessed board 21633!")
            print(f"Found {len(issues)} recent issues from board 21633")
            
            # Apply RAG classification
            classifier = RAGClassifier(config.rag)
            classifier.classify_issues_batch(issues)
            
            # Show summary
            summary = classifier.get_rag_summary(issues)
            print(f"\n📊 RAG Summary for Board 21633:")
            print(f"   🟢 Green: {summary['green']}")
            print(f"   🟡 Amber: {summary['amber']}")
            print(f"   🔴 Red: {summary['red']}")
            print(f"   Total: {summary['total']}")
            
            # Show first few issues
            print(f"\nRecent Issues from Board 21633:")
            for issue in issues[:5]:
                rag_emoji = {"red": "🔴", "amber": "🟡", "green": "🟢"}
                emoji = rag_emoji.get(issue.rag_status.value if issue.rag_status else "green", "⚪")
                print(f"  {emoji} {issue.key}: {issue.summary[:60]}...")
                print(f"    Status: {issue.status.name} ({issue.days_in_status} days)")
                print(f"    Assignee: {issue.assignee.display_name if issue.assignee else 'Unassigned'}")
                if issue.rag_reason:
                    print(f"    RAG Reason: {issue.rag_reason}")
                print()
            
            # Generate weekly report
            print("📋 Generating weekly status report for Board 21633...")
            generator = ReportGenerator(config.report)
            
            report = await generator.generate_weekly_report(
                team_name="Board 21633 Team",
                issues=issues,
                week_ending=datetime.now().date(),
                output_format="markdown",
                include_manual_sections=True
            )
            
            print("\n" + "="*80)
            print("WEEKLY STATUS REPORT - BOARD 21633")
            print("="*80)
            print(report)
            print("="*80)
            
        else:
            print("❌ No issues found for board 21633")
            print("This could mean:")
            print("1. Board 21633 doesn't exist")
            print("2. You don't have permission to access it")
            print("3. There are no recent issues in this board")
            
            # Try alternative JQL syntax
            print("\n🔄 Trying alternative board access method...")
            criteria2 = FilterCriteria(
                custom_jql=f"boardId = 21633 ORDER BY updated DESC"
            )
            issues2 = await client.get_issues(criteria2)
            
            if issues2:
                print(f"✅ Alternative method worked! Found {len(issues2)} issues")
            else:
                print("❌ Alternative method also failed")
        
    except Exception as e:
        print(f"❌ Error accessing board 21633: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(access_board_21633())