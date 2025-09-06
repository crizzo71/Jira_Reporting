#!/usr/bin/env python3
"""
Cloud Migration Demo - Jira Reports Simplified

This script demonstrates the Cloud migration readiness features.
To test dual-mode operation, you would set these environment variables:

JIRA_CLOUD_SERVER=https://your-domain.atlassian.net
JIRA_CLOUD_API_TOKEN=your_cloud_token

This prepares for Red Hat's Jira Cloud migration in 6 months.
"""

import asyncio
import os
from enhanced_config import get_config
from enhanced_auth import JiraAuthManager

async def demo_cloud_migration():
    """Demonstrate Cloud migration preparation."""
    print("☁️  Jira Cloud Migration Demo")
    print("=" * 40)
    
    config = get_config()
    auth_manager = JiraAuthManager(config)
    
    try:
        print("\n1. Current Configuration:")
        print(f"   Primary Server: {config.jira.server}")
        print(f"   Instance Type: {config.jira.instance_type}")
        print(f"   Auth Type: {config.jira.auth_type}")
        
        if config.jira.cloud_server:
            print(f"   Cloud Server: {config.jira.cloud_server}")
            print("   Status: ✅ Cloud migration configured")
        else:
            print("   Cloud Server: Not configured")
            print("   Status: ⚠️  Cloud migration not ready")
        
        print("\n2. Authentication Test:")
        auth_result = await auth_manager.authenticate()
        
        if auth_result.success:
            print(f"   ✅ Primary authentication successful")
            print(f"   User: {auth_result.user_info.get('displayName', 'Unknown')}")
            print(f"   API Version: {auth_result.api_version}")
            
            if auth_manager.is_dual_mode_active():
                print(f"   ✅ Dual-mode operation active")
                
                # Test migration preparation
                migration_info = await auth_manager.prepare_for_migration()
                print(f"\n3. Migration Preparation:")
                print(f"   Status: {migration_info['status']}")
                
                if migration_info['status'] == 'ready':
                    print("   ✅ Ready for 6-month migration timeline")
                    
                    # Validate migration readiness
                    validation = await auth_manager.validate_migration_readiness()
                    print(f"\n4. Migration Validation:")
                    print(f"   Ready: {validation['ready']}")
                    
                    for check, result in validation.get('checks', {}).items():
                        print(f"   {check}: {result}")
                    
                    if validation.get('warnings'):
                        print("   Warnings:")
                        for warning in validation['warnings']:
                            print(f"     - {warning}")
                    
                    if validation.get('errors'):
                        print("   Errors:")
                        for error in validation['errors']:
                            print(f"     - {error}")
                
            else:
                print(f"   ⚠️  Dual-mode not configured")
                print("\n3. To Enable Cloud Migration:")
                print("   Add to your .env file:")
                print("   JIRA_CLOUD_SERVER=https://your-domain.atlassian.net")
                print("   JIRA_CLOUD_API_TOKEN=your_cloud_token")
                print("   ")
                print("   This prepares for Red Hat's 6-month migration timeline")
        
        else:
            print(f"   ❌ Authentication failed: {auth_result.error_message}")
    
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    
    finally:
        await auth_manager.close()
    
    print("\n" + "=" * 40)
    print("Cloud migration features are ready!")
    print("When Red Hat provides Cloud instance details,")
    print("simply add them to the configuration for")
    print("seamless dual-mode operation.")

if __name__ == "__main__":
    asyncio.run(demo_cloud_migration())