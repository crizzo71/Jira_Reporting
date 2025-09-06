#!/usr/bin/env python3
"""Find Openshift Cluster Manager project."""

import asyncio
from jira_mcp_server.config import get_config
from jira_mcp_server.jira_client import JiraClient

async def find_ocm_project():
    """Find Openshift Cluster Manager project."""
    try:
        config = get_config()
        client = JiraClient(config)
        
        await client.authenticate()
        
        print("🔍 Searching for Openshift Cluster Manager related projects...")
        
        # Try different possible project keys
        possible_keys = ["OCM", "OCMGMT", "OSM", "CLUSTER", "OPENSHIFT"]
        
        for key in possible_keys:
            try:
                print(f"\n📋 Checking project key: {key}")
                boards = await client.get_boards([key])
                
                if boards:
                    print(f"✅ Found {len(boards)} boards in project {key}:")
                    for board in boards[:5]:  # Show first 5
                        print(f"  - Board {board.id}: {board.name}")
                    
                    # Check if board 21633 or 21634 is in this project
                    target_boards = [b for b in boards if b.id in [21633, 21634]]
                    if target_boards:
                        for tb in target_boards:
                            print(f"🎯 FOUND TARGET BOARD {tb.id}: {tb.name}")
                    
                    if len(boards) > 5:
                        print(f"  ... and {len(boards) - 5} more boards")
                else:
                    print(f"❌ No boards found for project {key}")
                    
            except Exception as e:
                print(f"❌ Error checking project {key}: {e}")
        
        # Also try searching by board name containing "cluster" or "openshift"
        print(f"\n🔍 Searching all boards for 'cluster' or 'openshift' in name...")
        all_boards = await client.get_boards()
        
        matching_boards = []
        for board in all_boards:
            if any(term in board.name.lower() for term in ['cluster', 'openshift', 'ocm']):
                matching_boards.append(board)
        
        if matching_boards:
            print(f"Found {len(matching_boards)} boards with cluster/openshift/ocm in name:")
            for board in matching_boards[:10]:  # Show first 10
                print(f"  - Board {board.id}: {board.name}")
                if board.project_key:
                    print(f"    Project: {board.project_key}")
                
                # Check if this is our target board
                if board.id in [21633, 21634]:
                    print(f"🎯 THIS IS YOUR TARGET BOARD!")
                print()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(find_ocm_project())