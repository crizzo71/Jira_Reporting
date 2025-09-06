#!/usr/bin/env python3
"""Quick OCM status check with minimal queries."""

import asyncio
from jira_mcp_server.config import get_config
from jira_mcp_server.jira_client import JiraClient
from jira_mcp_server.models import FilterCriteria

async def quick_ocm_status():
    """Quick OCM status check with specific queries."""
    try:
        config = get_config()
        client = JiraClient(config)
        
        await client.authenticate()
        
        print("🎯 Quick OCM Status Check...")
        
        # Define specific status queries with limits
        queries = {
            "In Progress": "project = OCM AND status in ('In Progress', 'Development', 'In Development') ORDER BY updated DESC",
            "Review": "project = OCM AND status in ('Review', 'Code Review', 'In Review', 'Testing') ORDER BY updated DESC", 
            "Done (Recent)": "project = OCM AND status in ('Done', 'Closed', 'Resolved') AND updated >= -7d ORDER BY updated DESC"
        }
        
        results = {}
        
        for category, jql in queries.items():
            print(f"\n📝 Getting {category} issues...")
            
            try:
                # Use custom JQL with small result set
                criteria = FilterCriteria(custom_jql=jql)
                issues = await client.get_issues(criteria)
                
                # Limit to first 20 results to avoid timeouts
                issues = issues[:20]
                results[category] = issues
                
                print(f"Found {len(issues)} {category.lower()} issues")
                
                if issues:
                    # Show sample issues
                    for issue in issues[:5]:
                        assignee = issue.assignee.display_name if issue.assignee else "Unassigned"
                        components = ", ".join(issue.components[:2]) if issue.components else "No component"
                        
                        print(f"  • [{issue.key}] {issue.summary[:50]}...")
                        print(f"    Status: {issue.status.name} | Assignee: {assignee}")
                        if components != "No component":
                            print(f"    Components: {components}")
                        print()
                    
                    if len(issues) > 5:
                        print(f"  ... and {len(issues) - 5} more issues")
                
            except Exception as e:
                print(f"❌ Error with {category}: {e}")
                results[category] = []
        
        # Quick summary
        print(f"\n" + "="*60)
        print(f"OCM QUICK STATUS SUMMARY")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"="*60)
        
        total = sum(len(issues) for issues in results.values())
        print(f"Sample Issues Retrieved: {total}")
        
        for category, issues in results.items():
            if issues:
                print(f"\n🔵 {category}: {len(issues)} issues")
                
                # Status breakdown
                status_counts = {}
                component_counts = {}
                
                for issue in issues:
                    status = issue.status.name
                    status_counts[status] = status_counts.get(status, 0) + 1
                    
                    for component in issue.components:
                        component_counts[component] = component_counts.get(component, 0) + 1
                
                # Show status distribution
                for status, count in status_counts.items():
                    print(f"   • {status}: {count}")
                
                # Show top components
                if component_counts:
                    print(f"   Top Components:")
                    for component, count in sorted(component_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
                        print(f"     - {component}: {count}")
        
        print(f"="*60)
        
        # Show available components from all results
        all_components = set()
        for issues in results.values():
            for issue in issues:
                all_components.update(issue.components)
        
        if all_components:
            print(f"\n🧩 Available Components (from sample):")
            for component in sorted(list(all_components)[:10]):
                print(f"   • {component}")
            
            if len(all_components) > 10:
                print(f"   ... and {len(all_components) - 10} more")
        
        return results
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(quick_ocm_status())