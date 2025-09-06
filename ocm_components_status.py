#!/usr/bin/env python3
"""Get OCM issues by status and component."""

import asyncio
from jira_mcp_server.config import get_config
from jira_mcp_server.jira_client import JiraClient
from jira_mcp_server.models import FilterCriteria
from jira_mcp_server.rag_classifier import RAGClassifier
from datetime import datetime, timedelta

async def get_ocm_by_status_and_component(component_name=None):
    """Get OCM issues filtered by status and optionally by component."""
    try:
        config = get_config()
        client = JiraClient(config)
        classifier = RAGClassifier(config.rag)
        
        await client.authenticate()
        
        print("🔍 Getting OCM issues by status and component...")
        
        # First, let's see what components exist in OCM
        if not component_name:
            print("\n📋 Finding available components in OCM project...")
            criteria = FilterCriteria(
                projects=["OCM"],
                updated_after=datetime.now() - timedelta(days=30)  # Last 30 days
            )
            
            sample_issues = await client.get_issues(criteria)
            
            # Collect all unique components
            all_components = set()
            for issue in sample_issues:
                all_components.update(issue.components)
            
            if all_components:
                print(f"Available components in OCM:")
                for component in sorted(all_components):
                    print(f"  - {component}")
                print(f"\nTo filter by a specific component, run:")
                print(f"python ocm_components_status.py --component 'ComponentName'")
                component_name = None  # Show all for now
            else:
                print("No components found in recent OCM issues")
        
        # Define status categories we're interested in
        status_categories = {
            "In Progress": ["In Progress", "Development", "In Development", "Work In Progress", "Coding", "Implementation"],
            "Review": ["Review", "Code Review", "In Review", "QA Review", "Testing", "QA", "Verification"],
            "Done": ["Done", "Closed", "Resolved", "Complete", "Finished"]
        }
        
        print(f"\n🎯 Getting issues by status categories...")
        if component_name:
            print(f"Filtering by component: {component_name}")
        
        all_results = {}
        
        for category, statuses in status_categories.items():
            print(f"\n📝 Getting {category} issues...")
            
            # Build JQL query
            status_list = "', '".join(statuses)
            jql_parts = [
                f"project = OCM",
                f"status in ('{status_list}')"
            ]
            
            if component_name:
                jql_parts.append(f"component = '{component_name}'")
            
            jql_query = " AND ".join(jql_parts) + " ORDER BY updated DESC"
            
            criteria = FilterCriteria(custom_jql=jql_query)
            
            try:
                issues = await client.get_issues(criteria)
                all_results[category] = issues
                
                print(f"Found {len(issues)} {category.lower()} issues")
                
                if issues:
                    # Apply RAG classification
                    classifier.classify_issues_batch(issues)
                    
                    # Show first few issues
                    print(f"Recent {category.lower()} issues:")
                    for issue in issues[:5]:
                        rag_emoji = {"red": "🔴", "amber": "🟡", "green": "🟢"}
                        emoji = rag_emoji.get(issue.rag_status.value if issue.rag_status else "green", "⚪")
                        
                        components_str = ", ".join(issue.components) if issue.components else "No component"
                        assignee_str = issue.assignee.display_name if issue.assignee else "Unassigned"
                        
                        print(f"  {emoji} [{issue.key}] {issue.summary[:50]}...")
                        print(f"     Status: {issue.status.name} | Assignee: {assignee_str}")
                        print(f"     Components: {components_str}")
                        if issue.rag_reason:
                            print(f"     RAG: {issue.rag_reason}")
                        print()
                    
                    if len(issues) > 5:
                        print(f"  ... and {len(issues) - 5} more {category.lower()} issues")
                
            except Exception as e:
                print(f"❌ Error getting {category} issues: {e}")
                all_results[category] = []
        
        # Generate summary report
        print(f"\n" + "="*80)
        print(f"OCM PROJECT STATUS REPORT")
        if component_name:
            print(f"Component: {component_name}")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"="*80)
        
        total_issues = sum(len(issues) for issues in all_results.values())
        print(f"Total Issues: {total_issues}")
        
        for category, issues in all_results.items():
            if issues:
                # RAG summary for this category
                summary = classifier.get_rag_summary(issues)
                print(f"\n🔵 {category.upper()} ({len(issues)} issues)")
                print(f"   🟢 Green: {summary['green']}, 🟡 Amber: {summary['amber']}, 🔴 Red: {summary['red']}")
                
                # Group by status
                status_groups = {}
                for issue in issues:
                    status = issue.status.name
                    if status not in status_groups:
                        status_groups[status] = []
                    status_groups[status].append(issue)
                
                for status, status_issues in status_groups.items():
                    print(f"   • {status}: {len(status_issues)} issues")
        
        # Component breakdown if not filtering by component
        if not component_name and total_issues > 0:
            print(f"\n📊 COMPONENT BREAKDOWN:")
            component_counts = {}
            for issues in all_results.values():
                for issue in issues:
                    for component in issue.components:
                        component_counts[component] = component_counts.get(component, 0) + 1
            
            if component_counts:
                for component, count in sorted(component_counts.items(), key=lambda x: x[1], reverse=True):
                    print(f"   • {component}: {count} issues")
            else:
                print("   No components assigned to issues")
        
        print(f"="*80)
        
        return all_results
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {}

if __name__ == "__main__":
    import sys
    
    component_name = None
    if len(sys.argv) > 1 and sys.argv[1] == "--component" and len(sys.argv) > 2:
        component_name = sys.argv[2]
    
    asyncio.run(get_ocm_by_status_and_component(component_name))