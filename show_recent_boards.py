#!/usr/bin/env python3
"""Show recent/high-ID boards that might be the one you're looking for."""

import asyncio
from jira_mcp_server.config import get_config
from jira_mcp_server.jira_client import JiraClient

async def show_recent_boards():
    """Show boards with IDs near 21633/21634."""
    try:
        config = get_config()
        client = JiraClient(config)
        
        await client.authenticate()
        
        print("🔍 Looking for boards with IDs around 21633-21634...")
        
        # Get all boards
        boards = await client.get_boards()
        
        # Filter boards with IDs near the target
        target_range_boards = []
        for board in boards:
            if 21600 <= board.id <= 21700:  # Range around your target
                target_range_boards.append(board)
        
        if target_range_boards:
            print(f"Found {len(target_range_boards)} boards in the 21600-21700 range:")
            for board in sorted(target_range_boards, key=lambda b: b.id):
                print(f"  - Board {board.id}: {board.name}")
                if board.project_key:
                    print(f"    Project: {board.project_key}")
                print()
        else:
            print("No boards found in the 21600-21700 range.")
            print("\nHere are the highest ID boards you have access to:")
            sorted_boards = sorted(boards, key=lambda b: b.id, reverse=True)
            for board in sorted_boards[:10]:
                print(f"  - Board {board.id}: {board.name}")
                if board.project_key:
                    print(f"    Project: {board.project_key}")
                print()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(show_recent_boards())