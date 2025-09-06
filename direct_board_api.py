#!/usr/bin/env python3
"""Try to access board 21633 via direct REST API."""

import asyncio
import aiohttp
import base64
from jira_mcp_server.config import get_config

async def get_board_21633_via_api():
    """Try to get board 21633 information via direct REST API."""
    try:
        config = get_config()
        
        # Create basic auth header
        credentials = f"{config.jira.email}:{config.jira.api_token}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            print("🔍 Trying to get board 21633 information directly...")
            
            # Try to get board info
            board_url = f"{config.jira.server}/rest/agile/1.0/board/21633"
            async with session.get(board_url) as response:
                if response.status == 200:
                    board_data = await response.json()
                    print(f"✅ Found board 21633!")
                    print(f"   Name: {board_data.get('name', 'Unknown')}")
                    print(f"   Type: {board_data.get('type', 'Unknown')}")
                    
                    # Try to get board configuration
                    config_url = f"{config.jira.server}/rest/agile/1.0/board/21633/configuration"
                    async with session.get(config_url) as config_response:
                        if config_response.status == 200:
                            config_data = await config_response.json()
                            if 'location' in config_data:
                                project_key = config_data['location'].get('projectKey')
                                print(f"   Project: {project_key}")
                            
                    # Try to get issues from this board
                    print(f"\n📝 Getting issues from board 21633...")
                    issues_url = f"{config.jira.server}/rest/agile/1.0/board/21633/issue"
                    params = {
                        "maxResults": 10,
                        "fields": "summary,status,assignee,updated,created"
                    }
                    
                    async with session.get(issues_url, params=params) as issues_response:
                        if issues_response.status == 200:
                            issues_data = await issues_response.json()
                            issues = issues_data.get('issues', [])
                            print(f"Found {len(issues)} recent issues:")
                            
                            for issue in issues[:5]:
                                key = issue.get('key', 'Unknown')
                                summary = issue.get('fields', {}).get('summary', 'No summary')
                                status = issue.get('fields', {}).get('status', {}).get('name', 'Unknown')
                                assignee = issue.get('fields', {}).get('assignee')
                                assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
                                
                                print(f"  - {key}: {summary[:60]}...")
                                print(f"    Status: {status}")
                                print(f"    Assignee: {assignee_name}")
                                print()
                                
                        else:
                            print(f"❌ Could not get issues: {issues_response.status}")
                            error_text = await issues_response.text()
                            print(f"Error: {error_text}")
                            
                elif response.status == 404:
                    print("❌ Board 21633 not found")
                elif response.status == 403:
                    print("❌ Access denied to board 21633")
                else:
                    print(f"❌ Error {response.status} accessing board 21633")
                    error_text = await response.text()
                    print(f"Error: {error_text}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(get_board_21633_via_api())