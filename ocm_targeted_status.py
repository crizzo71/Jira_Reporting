#!/usr/bin/env python3
"""Get OCM issues by specific statuses with better performance."""

import asyncio
from jira_mcp_server.config import get_config
from jira_mcp_server.jira_client import JiraClient
from jira_mcp_server.models import FilterCriteria
from jira_mcp_server.rag_classifier import RAGClassifier
from datetime import datetime, timedelta

async def get_ocm_status_summary():
    """Get OCM issues summary by status - more targeted approach."""
    try:
        config = get_config()
        client = JiraClient(config)
        classifier = RAGClassifier(config.rag)
        
        await client.authenticate()
        
        print("🎯 Getting OCM project status summary...")
        
        # Get only recent issues to avoid timeout
        print("\n📝 Getting recent issues from OCM (last 14 days)...")
        criteria = FilterCriteria(
            projects=["OCM"],
            updated_after=datetime.now() - timedelta(days=14)
        )
        
        issues = await client.get_issues(criteria)
        print(f"Found {len(issues)} recent issues in OCM")
        
        if not issues:
            print("No recent issues found. Try expanding the date range.")
            return
        
        # Apply RAG classification
        print("🎯 Applying RAG classification...")
        classifier.classify_issues_batch(issues)
        
        # Group by status
        status_groups = {}
        component_set = set()
        
        for issue in issues:
            status = issue.status.name
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(issue)
            
            # Collect components
            component_set.update(issue.components)
        
        # Categorize statuses
        in_progress_statuses = []
        review_statuses = []
        done_statuses = []
        other_statuses = []
        
        for status, issues_list in status_groups.items():
            status_lower = status.lower()
            if any(word in status_lower for word in ['progress', 'development', 'coding', 'implementation', 'doing']):
                in_progress_statuses.append((status, issues_list))
            elif any(word in status_lower for word in ['review', 'testing', 'qa', 'verification', 'validate']):
                review_statuses.append((status, issues_list))
            elif any(word in status_lower for word in ['done', 'closed', 'resolved', 'complete', 'finished']):
                done_statuses.append((status, issues_list))
            else:
                other_statuses.append((status, issues_list))
        
        # Generate report
        print(f"\n" + "="*80)
        print(f"OCM PROJECT STATUS SUMMARY")
        print(f"Period: Last 14 days (Updated since {(datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')})")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"="*80)
        
        print(f"📊 OVERVIEW:")
        print(f"   Total Recent Issues: {len(issues)}")
        
        # RAG Summary
        rag_summary = classifier.get_rag_summary(issues)
        print(f"   🟢 Green: {rag_summary['green']}, 🟡 Amber: {rag_summary['amber']}, 🔴 Red: {rag_summary['red']}")
        
        # Status Categories
        def print_status_category(title, status_list, emoji):
            if status_list:
                total_in_category = sum(len(issues_list) for _, issues_list in status_list)
                print(f"\n{emoji} {title.upper()} ({total_in_category} issues):")
                
                for status, issues_list in status_list:
                    rag_counts = {"green": 0, "amber": 0, "red": 0}
                    for issue in issues_list:
                        if issue.rag_status:
                            rag_counts[issue.rag_status.value] += 1
                    
                    print(f"   • {status}: {len(issues_list)} issues "
                          f"(🟢{rag_counts['green']} 🟡{rag_counts['amber']} 🔴{rag_counts['red']})")
                    
                    # Show a few sample issues
                    for issue in issues_list[:3]:
                        rag_emoji = {"red": "🔴", "amber": "🟡", "green": "🟢"}
                        emoji = rag_emoji.get(issue.rag_status.value if issue.rag_status else "green", "⚪")
                        assignee = issue.assignee.display_name if issue.assignee else "Unassigned"
                        components = ", ".join(issue.components[:2]) if issue.components else "No component"
                        
                        print(f"     {emoji} [{issue.key}] {issue.summary[:40]}... | {assignee}")
                        if issue.components:
                            print(f"        Components: {components}")
                    
                    if len(issues_list) > 3:
                        print(f"     ... and {len(issues_list) - 3} more issues")
        
        print_status_category("In Progress", in_progress_statuses, "🔄")
        print_status_category("In Review", review_statuses, "👀")
        print_status_category("Done", done_statuses, "✅")
        
        if other_statuses:
            print_status_category("Other Statuses", other_statuses, "📋")
        
        # Components breakdown
        if component_set:
            print(f"\n🧩 AVAILABLE COMPONENTS ({len(component_set)} total):")
            component_counts = {}
            for issue in issues:
                for component in issue.components:
                    component_counts[component] = component_counts.get(component, 0) + 1
            
            # Show top 10 components by issue count
            sorted_components = sorted(component_counts.items(), key=lambda x: x[1], reverse=True)
            for component, count in sorted_components[:10]:
                print(f"   • {component}: {count} issues")
            
            if len(sorted_components) > 10:
                print(f"   ... and {len(sorted_components) - 10} more components")
            
            print(f"\nTo filter by a specific component, use:")
            print(f"python ocm_targeted_status.py --component 'ComponentName'")
        
        print(f"="*80)
        
        return issues, component_set
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(get_ocm_status_summary())