#!/usr/bin/env python3
"""
Check OCM project metadata for valid issue creation parameters.
"""

import asyncio
from enhanced_config import get_config
from enhanced_auth import JiraAuthManager
from jira_mcp_server.jira_client import JiraClient


async def check_ocm_metadata():
    """Check OCM project metadata."""
    print("🔍 OCM Project Metadata Check")
    print("=" * 40)
    
    config = get_config()
    auth_manager = JiraAuthManager(config)
    jira_client = JiraClient(config)
    
    try:
        # Authenticate
        await auth_manager.authenticate()
        await jira_client.authenticate()
        print("✅ Authenticated")
        
        # Get OCM project metadata
        loop = asyncio.get_event_loop()
        project = await loop.run_in_executor(
            None, lambda: jira_client._jira.project("OCM")
        )
        
        print(f"\n📋 Project: {project.name} ({project.key})")
        
        # Get issue types
        print("\n📝 Available Issue Types:")
        issue_types = await loop.run_in_executor(
            None, lambda: jira_client._jira.issue_types()
        )
        for issue_type in issue_types[:5]:  # Show first 5
            print(f"   - {issue_type.name}")
        
        # Get priorities
        print("\n🔥 Available Priorities:")
        priorities = await loop.run_in_executor(
            None, lambda: jira_client._jira.priorities()
        )
        for priority in priorities:
            print(f"   - {priority.name}")
        
        # Try to get project-specific create metadata
        print("\n🛠️ Create Issue Metadata for OCM:")
        try:
            create_meta = await loop.run_in_executor(
                None, lambda: jira_client._jira.createmeta(projectKeys="OCM", expand="projects.issuetypes.fields")
            )
            
            if create_meta.get('projects'):
                project_meta = create_meta['projects'][0]
                print(f"   Project: {project_meta['name']}")
                
                if project_meta.get('issuetypes'):
                    print("   Available Issue Types for this project:")
                    for issue_type in project_meta['issuetypes']:
                        print(f"     - {issue_type['name']}")
                        
                        # Check required fields
                        if issue_type.get('fields'):
                            print(f"       Required fields:")
                            for field_key, field_info in issue_type['fields'].items():
                                if field_info.get('required'):
                                    print(f"         • {field_info.get('name', field_key)}")
                            
                            # Check priority field options
                            if 'priority' in issue_type['fields']:
                                priority_field = issue_type['fields']['priority']
                                if priority_field.get('allowedValues'):
                                    print(f"       Available priorities:")
                                    for priority in priority_field['allowedValues']:
                                        print(f"         • {priority['name']}")
                        break  # Just check first issue type
            
        except Exception as e:
            print(f"   ⚠️ Could not get create metadata: {e}")
        
        await auth_manager.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(check_ocm_metadata())