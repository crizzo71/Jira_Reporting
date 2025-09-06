#!/usr/bin/env python3
"""Access board 21634 specifically via Agile REST API."""

import asyncio
import aiohttp
import base64
from jira_mcp_server.config import get_config
from jira_mcp_server.jira_client import JiraClient
from jira_mcp_server.models import FilterCriteria
from jira_mcp_server.rag_classifier import RAGClassifier
from jira_mcp_server.report_generator import ReportGenerator
from datetime import datetime, timedelta

async def access_kanban_board_21634():
    """Access Kanban board 21634 and generate report."""
    try:
        config = get_config()
        
        # Create basic auth header for direct API calls
        credentials = f"{config.jira.email}:{config.jira.api_token}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            print("🎯 Accessing Kanban board 21634...")
            
            # Get board information
            board_url = f"{config.jira.server}/rest/agile/1.0/board/21634"
            async with session.get(board_url) as response:
                if response.status == 200:
                    board_data = await response.json()
                    board_name = board_data.get('name', 'Unknown Board')
                    board_type = board_data.get('type', 'Unknown')
                    
                    print(f"✅ Found Kanban board 21634!")
                    print(f"   Name: {board_name}")
                    print(f"   Type: {board_type}")
                    
                    # Get board configuration to find project
                    config_url = f"{config.jira.server}/rest/agile/1.0/board/21634/configuration"
                    project_key = None
                    async with session.get(config_url) as config_response:
                        if config_response.status == 200:
                            config_data = await config_response.json()
                            if 'location' in config_data:
                                project_key = config_data['location'].get('projectKey')
                                print(f"   Project: {project_key}")
                    
                    # Get issues from this board using Agile API
                    print(f"\n📝 Getting issues from board 21634...")
                    issues_url = f"{config.jira.server}/rest/agile/1.0/board/21634/issue"
                    
                    all_issues = []
                    start_at = 0
                    max_results = 50
                    
                    while True:
                        params = {
                            "startAt": start_at,
                            "maxResults": max_results,
                            "fields": "summary,status,assignee,updated,created,priority,issuetype,description,labels,components"
                        }
                        
                        async with session.get(issues_url, params=params) as issues_response:
                            if issues_response.status == 200:
                                issues_data = await issues_response.json()
                                issues = issues_data.get('issues', [])
                                
                                if not issues:
                                    break
                                    
                                all_issues.extend(issues)
                                
                                # Check if we have more issues
                                if len(issues) < max_results:
                                    break
                                    
                                start_at += max_results
                            else:
                                print(f"❌ Error getting issues: {issues_response.status}")
                                break
                    
                    print(f"Found {len(all_issues)} total issues in board 21634")
                    
                    if all_issues:
                        # Filter for recent issues (last 7 days)
                        recent_issues = []
                        cutoff_date = datetime.now() - timedelta(days=7)
                        
                        for issue in all_issues:
                            updated_str = issue.get('fields', {}).get('updated', '')
                            if updated_str:
                                try:
                                    updated_date = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
                                    if updated_date >= cutoff_date:
                                        recent_issues.append(issue)
                                except:
                                    continue
                        
                        print(f"Found {len(recent_issues)} issues updated in the last 7 days")
                        
                        # Show recent issues summary
                        print(f"\nRecent Issues Summary:")
                        status_counts = {}
                        for issue in recent_issues[:10]:  # Show first 10
                            key = issue.get('key', 'Unknown')
                            summary = issue.get('fields', {}).get('summary', 'No summary')
                            status = issue.get('fields', {}).get('status', {}).get('name', 'Unknown')
                            assignee = issue.get('fields', {}).get('assignee')
                            assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
                            
                            status_counts[status] = status_counts.get(status, 0) + 1
                            
                            print(f"  - {key}: {summary[:50]}...")
                            print(f"    Status: {status}, Assignee: {assignee_name}")
                        
                        if len(recent_issues) > 10:
                            print(f"  ... and {len(recent_issues) - 10} more recent issues")
                        
                        print(f"\n📊 Status Distribution (Recent Issues):")
                        for status, count in sorted(status_counts.items()):
                            print(f"   {status}: {count}")
                        
                        # Generate a simple weekly report
                        print(f"\n📋 WEEKLY STATUS REPORT - {board_name}")
                        print(f"=" * 60)
                        print(f"Board: {board_name} (ID: 21634)")
                        if project_key:
                            print(f"Project: {project_key}")
                        print(f"Week ending: {datetime.now().strftime('%Y-%m-%d')}")
                        print(f"Total issues: {len(all_issues)}")
                        print(f"Recently active: {len(recent_issues)}")
                        print(f"\nStatus Summary:")
                        for status, count in sorted(status_counts.items()):
                            print(f"  • {status}: {count} issues")
                        
                        print(f"\nRecent Activity (Last 7 Days):")
                        for issue in recent_issues[:5]:
                            key = issue.get('key', 'Unknown')
                            summary = issue.get('fields', {}).get('summary', 'No summary')
                            status = issue.get('fields', {}).get('status', {}).get('name', 'Unknown')
                            assignee = issue.get('fields', {}).get('assignee')
                            assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
                            
                            print(f"  • [{key}](https://issues.redhat.com/browse/{key}) {summary[:60]}...")
                            print(f"    Status: {status} | Assignee: {assignee_name}")
                        
                        print(f"=" * 60)
                        
                    else:
                        print("No issues found in this board")
                        
                elif response.status == 404:
                    print("❌ Board 21634 not found")
                elif response.status == 403:
                    print("❌ Access denied to board 21634")
                else:
                    print(f"❌ Error {response.status} accessing board 21634")
                    error_text = await response.text()
                    print(f"Error: {error_text[:200]}...")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(access_kanban_board_21634())