#!/usr/bin/env python3
"""Generate a report for an available OCM board."""

import asyncio
from datetime import datetime, timedelta
from jira_mcp_server.config import get_config
from jira_mcp_server.jira_client import JiraClient
from jira_mcp_server.models import FilterCriteria
from jira_mcp_server.rag_classifier import RAGClassifier
from jira_mcp_server.report_generator import ReportGenerator

async def generate_ocm_report():
    """Generate a report for OCM project."""
    try:
        config = get_config()
        client = JiraClient(config)
        classifier = RAGClassifier(config.rag)
        generator = ReportGenerator(config.report)
        
        await client.authenticate()
        
        print("📝 Generating OCM Team Weekly Status Report...")
        
        # Get issues from OCM project from the last week
        criteria = FilterCriteria(
            projects=["OCM"],
            updated_after=datetime.now() - timedelta(days=7)
        )
        
        print("🔍 Fetching recent issues from OCM project...")
        issues = await client.get_issues(criteria)
        print(f"Found {len(issues)} recent issues")
        
        if issues:
            # Apply RAG classification
            print("🎯 Applying RAG classification...")
            classifier.classify_issues_batch(issues)
            
            # Generate the report
            print("📊 Generating weekly report...")
            report = await generator.generate_weekly_report(
                team_name="OpenShift Cluster Manager Team",
                issues=issues,
                week_ending=datetime.now().date(),
                output_format="markdown",
                include_manual_sections=True
            )
            
            print("✅ Report generated successfully!")
            print("=" * 80)
            print(report)
            print("=" * 80)
            
            # Also show summary
            summary = classifier.get_rag_summary(issues)
            print(f"\n📊 Quick Summary:")
            print(f"   🟢 Green: {summary['green']}")
            print(f"   🟡 Amber: {summary['amber']}")
            print(f"   🔴 Red: {summary['red']}")
            print(f"   Total: {summary['total']}")
            
        else:
            print("No recent issues found in OCM project for the last week.")
            print("This might mean:")
            print("1. No issues were updated recently")
            print("2. There are permission restrictions")
            print("3. The project key might be different")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(generate_ocm_report())