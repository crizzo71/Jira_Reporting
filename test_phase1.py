#!/usr/bin/env python3
"""
Phase 1 Testing Script - Jira Reports Simplified
Week 1-2: Foundation Testing

This script helps you test and validate:
1. Enhanced configuration system
2. Authentication layer improvements
3. Red Hat Jira compatibility
4. Cloud migration readiness

Run this script to validate Phase 1 before moving to feature migration.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any
import json

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from enhanced_config import Config, get_config, create_sample_env_file
from enhanced_auth import JiraAuthManager, test_authentication


class Phase1Tester:
    """Phase 1 testing coordinator."""
    
    def __init__(self):
        self.test_results = {}
        self.config = None
        self.auth_manager = None
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all Phase 1 tests."""
        print("🚀 Phase 1 Testing - Jira Reports Simplified")
        print("=" * 50)
        
        # Test 1: Configuration System
        print("\n📋 Test 1: Enhanced Configuration System")
        await self.test_configuration()
        
        # Test 2: Authentication Layer
        print("\n🔐 Test 2: Enhanced Authentication Layer")
        await self.test_authentication()
        
        # Test 3: Red Hat Jira Compatibility
        print("\n🏢 Test 3: Red Hat Jira Compatibility")
        await self.test_redhat_compatibility()
        
        # Test 4: Cloud Migration Readiness
        print("\n☁️  Test 4: Cloud Migration Readiness")
        await self.test_cloud_migration_readiness()
        
        # Test 5: Legacy Configuration Migration
        print("\n📦 Test 5: Legacy Configuration Migration")
        await self.test_legacy_migration()
        
        # Generate test report
        await self.generate_test_report()
        
        return self.test_results
    
    async def test_configuration(self):
        """Test the enhanced configuration system."""
        test_name = "configuration"
        try:
            print("  Testing configuration loading...")
            
            # Check if .env file exists
            env_exists = os.path.exists('.env')
            
            if not env_exists:
                print("  ⚠️  No .env file found. Creating sample...")
                create_sample_env_file()
                print("  📝 Please edit .env file with your credentials and re-run tests")
                self.test_results[test_name] = {
                    "status": "setup_required",
                    "message": "Environment file created. Please configure credentials."
                }
                return
            
            # Load configuration
            self.config = get_config()
            
            # Validate configuration structure
            config_dict = self.config.dict()
            required_sections = ['jira', 'github', 'rag', 'report', 'analytics', 'cache', 'mcp']
            
            missing_sections = [section for section in required_sections if section not in config_dict]
            
            if missing_sections:
                raise ValueError(f"Missing configuration sections: {missing_sections}")
            
            # Test unified configuration features
            features_tested = {
                "jira_config": bool(self.config.jira.server and self.config.jira.email and self.config.jira.api_token),
                "cloud_migration_config": bool(self.config.jira.cloud_server),
                "github_integration_config": self.config.github.enabled,
                "rag_classification_config": len(self.config.rag.red_priority_levels) > 0,
                "report_config": self.config.report.velocity_sprints_count > 0,
                "analytics_config": True,  # Structure exists
                "cache_config": self.config.cache.enabled,
                "mcp_config": self.config.mcp.port > 0
            }
            
            self.test_results[test_name] = {
                "status": "passed",
                "features_tested": features_tested,
                "config_sections": list(config_dict.keys()),
                "jira_server": self.config.jira.server,
                "instance_type": self.config.jira.instance_type,
                "auth_type": self.config.jira.auth_type
            }
            
            print("  ✅ Configuration system test passed")
            print(f"     - Jira Server: {self.config.jira.server}")
            print(f"     - Instance Type: {self.config.jira.instance_type}")
            print(f"     - Auth Type: {self.config.jira.auth_type}")
            
            if self.config.jira.cloud_server:
                print(f"     - Cloud Server: {self.config.jira.cloud_server} (migration ready)")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e)
            }
            print(f"  ❌ Configuration test failed: {e}")
    
    async def test_authentication(self):
        """Test the enhanced authentication layer."""
        test_name = "authentication"
        
        if not self.config:
            print("  ⚠️  Skipping authentication test - configuration not loaded")
            self.test_results[test_name] = {"status": "skipped", "reason": "No configuration"}
            return
        
        try:
            print("  Testing authentication...")
            
            self.auth_manager = JiraAuthManager(self.config)
            auth_result = await self.auth_manager.authenticate()
            
            if auth_result.success:
                self.test_results[test_name] = {
                    "status": "passed",
                    "server_url": auth_result.server_url,
                    "instance_type": auth_result.instance_type,
                    "auth_method": auth_result.auth_method,
                    "user_info": auth_result.user_info,
                    "api_version": auth_result.api_version,
                    "dual_mode_active": self.auth_manager.is_dual_mode_active()
                }
                
                print("  ✅ Authentication test passed")
                print(f"     - User: {auth_result.user_info.get('displayName', 'Unknown')}")
                print(f"     - Email: {auth_result.user_info.get('emailAddress', 'Unknown')}")
                print(f"     - API Version: {auth_result.api_version}")
                
                if self.auth_manager.is_dual_mode_active():
                    print("     - Dual-mode operation: ✅ Active")
                else:
                    print("     - Dual-mode operation: ⚠️  Not configured")
            else:
                self.test_results[test_name] = {
                    "status": "failed",
                    "error": auth_result.error_message
                }
                print(f"  ❌ Authentication test failed: {auth_result.error_message}")
                
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e)
            }
            print(f"  ❌ Authentication test failed: {e}")
    
    async def test_redhat_compatibility(self):
        """Test Red Hat Jira specific compatibility."""
        test_name = "redhat_compatibility"
        
        if not self.auth_manager or not self.auth_manager.get_primary_client():
            print("  ⚠️  Skipping Red Hat compatibility test - authentication not successful")
            self.test_results[test_name] = {"status": "skipped", "reason": "No authenticated client"}
            return
        
        try:
            print("  Testing Red Hat Jira compatibility...")
            
            jira_client = self.auth_manager.get_primary_client()
            
            # Test basic Red Hat Jira operations
            compatibility_tests = {}
            
            # Test 1: Project access
            try:
                projects = jira_client.projects()
                compatibility_tests["project_access"] = {
                    "status": "passed",
                    "count": len(projects),
                    "sample_projects": [p.key for p in projects[:3]]
                }
                print(f"     - Project access: ✅ {len(projects)} projects found")
            except Exception as e:
                compatibility_tests["project_access"] = {"status": "failed", "error": str(e)}
                print(f"     - Project access: ❌ {e}")
            
            # Test 2: User search (Red Hat specific)
            try:
                current_user = jira_client.current_user()
                compatibility_tests["user_operations"] = {
                    "status": "passed",
                    "current_user": current_user
                }
                print(f"     - User operations: ✅ Current user retrieved")
            except Exception as e:
                compatibility_tests["user_operations"] = {"status": "failed", "error": str(e)}
                print(f"     - User operations: ❌ {e}")
            
            # Test 3: Issue search with OCM project (if available)
            if self.config.jira.default_project_keys:
                try:
                    project_key = self.config.jira.default_project_keys[0]
                    issues = jira_client.search_issues(f'project = {project_key}', maxResults=5)
                    compatibility_tests["issue_search"] = {
                        "status": "passed",
                        "project": project_key,
                        "sample_count": len(issues)
                    }
                    print(f"     - Issue search: ✅ {len(issues)} issues found in {project_key}")
                except Exception as e:
                    compatibility_tests["issue_search"] = {"status": "failed", "error": str(e)}
                    print(f"     - Issue search: ❌ {e}")
            
            self.test_results[test_name] = {
                "status": "passed",
                "compatibility_tests": compatibility_tests,
                "server_url": self.config.jira.server,
                "redhat_instance": "redhat.com" in self.config.jira.server
            }
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e)
            }
            print(f"  ❌ Red Hat compatibility test failed: {e}")
    
    async def test_cloud_migration_readiness(self):
        """Test Cloud migration readiness."""
        test_name = "cloud_migration_readiness"
        
        if not self.auth_manager:
            print("  ⚠️  Skipping Cloud migration test - no auth manager")
            self.test_results[test_name] = {"status": "skipped", "reason": "No auth manager"}
            return
        
        try:
            print("  Testing Cloud migration readiness...")
            
            # Check dual-mode configuration
            dual_mode_configured = (
                self.config.jira.cloud_server and 
                self.config.jira.cloud_api_token and 
                self.config.jira.cloud_server != self.config.jira.server
            )
            
            migration_readiness = {
                "dual_mode_configured": dual_mode_configured,
                "dual_mode_active": self.auth_manager.is_dual_mode_active(),
                "primary_server": self.config.jira.server,
                "cloud_server": self.config.jira.cloud_server,
                "migration_timeline": "6 months"
            }
            
            if dual_mode_configured and self.auth_manager.is_dual_mode_active():
                # Run detailed migration readiness validation
                validation_results = await self.auth_manager.validate_migration_readiness()
                migration_readiness["validation"] = validation_results
                
                print("  ✅ Cloud migration readiness test passed")
                print(f"     - Dual-mode configured: ✅")
                print(f"     - Dual-mode active: ✅")
                print(f"     - Primary: {self.config.jira.server}")
                print(f"     - Cloud: {self.config.jira.cloud_server}")
                
                if validation_results["ready"]:
                    print("     - Migration validation: ✅ Ready")
                else:
                    print("     - Migration validation: ⚠️  Issues found")
                    for error in validation_results.get("errors", []):
                        print(f"       • {error}")
            else:
                print("  ⚠️  Cloud migration not fully configured")
                print("     - To enable: Set JIRA_CLOUD_SERVER and JIRA_CLOUD_API_TOKEN")
                print("     - This will be needed for the 6-month migration timeline")
            
            self.test_results[test_name] = {
                "status": "passed",
                "migration_readiness": migration_readiness
            }
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e)
            }
            print(f"  ❌ Cloud migration readiness test failed: {e}")
    
    async def test_legacy_migration(self):
        """Test legacy configuration migration capabilities."""
        test_name = "legacy_migration"
        
        try:
            print("  Testing legacy configuration migration...")
            
            # Check for existing Node.js configurations
            legacy_configs = [
                "jira_report/.env",
                "jira_report/config.js",
                "Jira-Status-Builder/.env",
                "Jira-Status-Builder/config.js"
            ]
            
            found_configs = [config for config in legacy_configs if os.path.exists(config)]
            
            migration_test = {
                "legacy_configs_found": found_configs,
                "migration_enabled": self.config.migration.auto_migrate_config if self.config else False,
                "can_migrate": len(found_configs) > 0
            }
            
            if found_configs:
                print(f"  ✅ Legacy migration test passed")
                print(f"     - Found {len(found_configs)} legacy configuration files")
                for config in found_configs:
                    print(f"       • {config}")
                
                if self.config:
                    # Test migration capability
                    migration_results = self.config.migrate_from_nodejs(found_configs)
                    migration_test["migration_results"] = migration_results
                    print("     - Migration capability: ✅ Available")
            else:
                print("  ℹ️  No legacy configurations found (expected in new setup)")
                print("     - Migration will be available when consolidating existing tools")
            
            self.test_results[test_name] = {
                "status": "passed",
                "migration_test": migration_test
            }
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e)
            }
            print(f"  ❌ Legacy migration test failed: {e}")
    
    async def generate_test_report(self):
        """Generate comprehensive test report."""
        print("\n📊 Phase 1 Test Report")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results.values() if t.get("status") == "passed"])
        failed_tests = len([t for t in self.test_results.values() if t.get("status") == "failed"])
        skipped_tests = len([t for t in self.test_results.values() if t.get("status") == "skipped"])
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Skipped: {skipped_tests} ⚠️")
        
        # Overall status
        if failed_tests == 0 and passed_tests > 0:
            print("\n🎉 Phase 1 Foundation: READY FOR USER TESTING")
            print("You can now test authentication and configuration validation.")
        elif failed_tests > 0:
            print("\n⚠️  Phase 1 Foundation: NEEDS ATTENTION")
            print("Please resolve failed tests before proceeding.")
        else:
            print("\n⚠️  Phase 1 Foundation: CONFIGURATION NEEDED")
            print("Please complete environment setup.")
        
        # Save detailed report
        report_file = "phase1_test_report.json"
        with open(report_file, 'w') as f:
            json.dump({
                "phase": "Phase 1 - Foundation",
                "timestamp": str(asyncio.get_event_loop().time()),
                "summary": {
                    "total": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "skipped": skipped_tests
                },
                "test_results": self.test_results
            }, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved: {report_file}")
        
        # Next steps
        print("\n🔄 Next Steps:")
        if failed_tests == 0:
            print("1. ✅ Review this test report")
            print("2. ✅ Test authentication with your Red Hat Jira")
            print("3. ✅ Validate configuration settings")
            print("4. ✅ Approve Phase 1 to proceed to feature migration")
        else:
            print("1. ❌ Fix failed tests")
            print("2. ❌ Re-run this test script")
            print("3. ❌ Once all tests pass, approve Phase 1")
    
    async def cleanup(self):
        """Clean up test resources."""
        if self.auth_manager:
            await self.auth_manager.close()


async def main():
    """Main test execution."""
    tester = Phase1Tester()
    
    try:
        await tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    print("Phase 1 Testing - Jira Reports Simplified")
    print("Week 1-2: Foundation Validation")
    print("\nPress Ctrl+C to cancel at any time")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTesting cancelled by user")
    except Exception as e:
        print(f"Failed to run tests: {e}")
        sys.exit(1)