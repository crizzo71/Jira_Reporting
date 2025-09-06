#!/usr/bin/env python3
"""Check specific board 21634."""

import asyncio
from jira_mcp_server.config import get_config
from jira_mcp_server.jira_client import JiraClient

async def check_board_21634():
    """Check board 21634 specifically."""
    try:
        config = get_config()
        client = JiraClient(config)
        
        await client.authenticate()
        
        # Get all OCM boards and find 21634
        boards = await client.get_boards(["OCM"])
        
        target_board = None
        for board in boards:
            if board.id == 21634:
                target_board = board
                break
        
        if target_board:
            print(f"✅ Found board 21634: {target_board.name}")
            print(f"   Type: {target_board.type}")
            print(f"   Project: {target_board.project_key}")
        else:
            print("❌ Board 21634 not found in OCM project")
            print("Available boards with similar IDs:")
            for board in boards:
                if "21" in str(board.id):
                    print(f"  - Board {board.id}: {board.name}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_board_21634())