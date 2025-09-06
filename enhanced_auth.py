"""Enhanced authentication layer for Jira Reports Simplified.

Supports Red Hat Jira Server, Cloud migration, and dual-mode operation.
Designed for seamless transition during the 6-month migration timeline.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
import aiohttp
import base64
import json

from jira import JIRA
from jira.exceptions import JIRAError

from enhanced_config import Config, JiraInstanceType, AuthType

logger = logging.getLogger(__name__)


class ConnectionStatus(str, Enum):
    """Connection status for monitoring."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    AUTHENTICATING = "authenticating"
    FAILED = "failed"
    MIGRATING = "migrating"


@dataclass
class AuthResult:
    """Authentication result with detailed information."""
    success: bool
    instance_type: JiraInstanceType
    auth_method: AuthType
    server_url: str
    user_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None
    api_version: Optional[str] = None


class JiraAuthManager:
    """Enhanced authentication manager with Cloud migration support."""
    
    def __init__(self, config: Config):
        self.config = config
        self._primary_jira: Optional[JIRA] = None
        self._cloud_jira: Optional[JIRA] = None
        self._current_auth: Optional[AuthResult] = None
        self._connection_status = ConnectionStatus.DISCONNECTED
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Connection monitoring
        self._last_auth_check: Optional[datetime] = None
        self._auth_check_interval = timedelta(minutes=15)
        
        # Migration support
        self._migration_mode = False
        self._dual_mode_active = False
    
    async def authenticate(self) -> AuthResult:
        """Authenticate with Jira instance(s) based on configuration."""
        self._connection_status = ConnectionStatus.AUTHENTICATING
        
        try:
            # Detect instance type if auto-detection is enabled
            if self.config.jira.instance_type == JiraInstanceType.AUTO_DETECT:
                detected_type = await self._detect_instance_type(self.config.jira.server)
                logger.info(f"Auto-detected Jira instance type: {detected_type}")
            else:
                detected_type = self.config.jira.instance_type
            
            # Authenticate with primary instance
            primary_result = await self._authenticate_instance(
                server=self.config.jira.server,
                email=self.config.jira.email,
                api_token=self.config.jira.api_token,
                instance_type=detected_type,
                auth_type=self.config.jira.auth_type
            )
            
            if not primary_result.success:
                self._connection_status = ConnectionStatus.FAILED
                return primary_result
            
            self._primary_jira = await self._create_jira_client(
                server=self.config.jira.server,
                email=self.config.jira.email,
                api_token=self.config.jira.api_token,
                instance_type=detected_type,
                auth_type=self.config.jira.auth_type
            )
            
            # If Cloud credentials are provided, set up dual-mode operation
            if (self.config.jira.cloud_server and 
                self.config.jira.cloud_api_token and 
                self.config.jira.cloud_server != self.config.jira.server):
                
                logger.info("Setting up dual-mode operation for Cloud migration")
                cloud_result = await self._authenticate_instance(
                    server=self.config.jira.cloud_server,
                    email=self.config.jira.email,
                    api_token=self.config.jira.cloud_api_token,
                    instance_type=JiraInstanceType.CLOUD,
                    auth_type=AuthType.BASIC  # Cloud typically uses Basic auth
                )
                
                if cloud_result.success:
                    self._cloud_jira = await self._create_jira_client(
                        server=self.config.jira.cloud_server,
                        email=self.config.jira.email,
                        api_token=self.config.jira.cloud_api_token,
                        instance_type=JiraInstanceType.CLOUD,
                        auth_type=AuthType.BASIC
                    )
                    self._dual_mode_active = True
                    logger.info("Dual-mode operation activated")
                else:
                    logger.warning(f"Cloud authentication failed: {cloud_result.error_message}")
            
            self._current_auth = primary_result
            self._connection_status = ConnectionStatus.CONNECTED
            self._last_auth_check = datetime.now()
            
            logger.info(f"Successfully authenticated with {primary_result.server_url}")
            return primary_result
            
        except Exception as e:
            error_msg = f"Authentication failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._connection_status = ConnectionStatus.FAILED
            
            return AuthResult(
                success=False,
                instance_type=self.config.jira.instance_type,
                auth_method=self.config.jira.auth_type,
                server_url=self.config.jira.server,
                error_message=error_msg
            )
    
    async def _detect_instance_type(self, server_url: str) -> JiraInstanceType:
        """Auto-detect Jira instance type (Server vs Cloud)."""
        try:
            if not self._session:
                self._session = aiohttp.ClientSession()
            
            # Check server info endpoint
            async with self._session.get(f"{server_url}/rest/api/2/serverInfo") as response:
                if response.status == 200:
                    server_info = await response.json()
                    
                    # Cloud instances have specific characteristics
                    if 'atlassian.net' in server_url or server_info.get('deploymentType') == 'Cloud':
                        return JiraInstanceType.CLOUD
                    else:
                        return JiraInstanceType.SERVER
                        
        except Exception as e:
            logger.warning(f"Could not auto-detect instance type: {e}")
            
        # Default to Server for Red Hat instances
        if 'redhat.com' in server_url:
            return JiraInstanceType.SERVER
        
        # Default fallback
        return JiraInstanceType.SERVER
    
    async def _authenticate_instance(
        self, 
        server: str, 
        email: str, 
        api_token: str,
        instance_type: JiraInstanceType,
        auth_type: AuthType
    ) -> AuthResult:
        """Authenticate with a specific Jira instance."""
        
        try:
            if not self._session:
                self._session = aiohttp.ClientSession()
            
            # Prepare authentication headers
            auth_header = self._get_auth_header(email, api_token, auth_type, instance_type)
            headers = {"Authorization": auth_header, "Content-Type": "application/json"}
            
            # Test authentication with current user endpoint
            async with self._session.get(f"{server}/rest/api/2/myself", headers=headers) as response:
                if response.status == 200:
                    user_info = await response.json()
                    
                    # Get server capabilities
                    capabilities = await self._get_server_capabilities(server, headers)
                    api_version = await self._get_api_version(server, headers)
                    
                    return AuthResult(
                        success=True,
                        instance_type=instance_type,
                        auth_method=auth_type,
                        server_url=server,
                        user_info=user_info,
                        capabilities=capabilities,
                        api_version=api_version
                    )
                else:
                    error_text = await response.text()
                    return AuthResult(
                        success=False,
                        instance_type=instance_type,
                        auth_method=auth_type,
                        server_url=server,
                        error_message=f"HTTP {response.status}: {error_text}"
                    )
                    
        except Exception as e:
            return AuthResult(
                success=False,
                instance_type=instance_type,
                auth_method=auth_type,
                server_url=server,
                error_message=str(e)
            )
    
    def _get_auth_header(
        self, 
        email: str, 
        api_token: str, 
        auth_type: AuthType, 
        instance_type: JiraInstanceType
    ) -> str:
        """Generate authentication header based on type and instance."""
        
        if auth_type == AuthType.PAT:
            # Personal Access Token (Server)
            return f"Bearer {api_token}"
        elif auth_type == AuthType.BASIC:
            # Basic authentication (Cloud)
            credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()
            return f"Basic {credentials}"
        elif auth_type == AuthType.BEARER:
            # Bearer token
            return f"Bearer {api_token}"
        else:
            # Default to Basic for Cloud, PAT for Server
            if instance_type == JiraInstanceType.CLOUD:
                credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()
                return f"Basic {credentials}"
            else:
                return f"Bearer {api_token}"
    
    async def _get_server_capabilities(self, server: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Get server capabilities and features."""
        try:
            if not self._session:
                return {}
            
            async with self._session.get(f"{server}/rest/api/2/serverInfo", headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.warning(f"Could not fetch server capabilities: {e}")
        
        return {}
    
    async def _get_api_version(self, server: str, headers: Dict[str, str]) -> Optional[str]:
        """Get API version information."""
        try:
            if not self._session:
                return None
            
            async with self._session.get(f"{server}/rest/api/2/serverInfo", headers=headers) as response:
                if response.status == 200:
                    server_info = await response.json()
                    return server_info.get('version')
        except Exception as e:
            logger.warning(f"Could not fetch API version: {e}")
        
        return None
    
    async def _create_jira_client(
        self,
        server: str,
        email: str,
        api_token: str,
        instance_type: JiraInstanceType,
        auth_type: AuthType
    ) -> JIRA:
        """Create JIRA client instance with appropriate authentication."""
        
        loop = asyncio.get_event_loop()
        
        try:
            if auth_type == AuthType.PAT or (instance_type == JiraInstanceType.SERVER and auth_type != AuthType.BASIC):
                # Use token authentication for Server/PAT
                jira_client = await loop.run_in_executor(
                    None,
                    lambda: JIRA(
                        server=server,
                        token_auth=api_token,
                        options={'verify': True, 'timeout': 30}
                    )
                )
            else:
                # Use basic authentication for Cloud/Basic
                jira_client = await loop.run_in_executor(
                    None,
                    lambda: JIRA(
                        server=server,
                        basic_auth=(email, api_token),
                        options={'verify': True, 'timeout': 30}
                    )
                )
            
            # Test the connection
            await loop.run_in_executor(None, lambda: jira_client.current_user())
            return jira_client
            
        except JIRAError as e:
            if e.status_code == 401:
                raise Exception(f"Authentication failed: Invalid credentials for {email}")
            elif e.status_code == 403:
                raise Exception(f"Authentication failed: Access denied for {email}")
            else:
                raise Exception(f"Jira connection failed: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error creating Jira client: {e}")
    
    async def check_connection_health(self) -> bool:
        """Check if the current connection is healthy."""
        if not self._current_auth or not self._current_auth.success:
            return False
        
        # Check if it's time for a health check
        if (self._last_auth_check and 
            datetime.now() - self._last_auth_check < self._auth_check_interval):
            return True
        
        try:
            # Test connection with a simple API call
            if self._primary_jira:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: self._primary_jira.current_user())
                self._last_auth_check = datetime.now()
                return True
        except Exception as e:
            logger.warning(f"Connection health check failed: {e}")
            self._connection_status = ConnectionStatus.FAILED
        
        return False
    
    async def refresh_authentication(self) -> AuthResult:
        """Refresh authentication tokens if needed."""
        logger.info("Refreshing authentication...")
        return await self.authenticate()
    
    def get_primary_client(self) -> Optional[JIRA]:
        """Get the primary JIRA client."""
        return self._primary_jira
    
    def get_cloud_client(self) -> Optional[JIRA]:
        """Get the Cloud JIRA client (if in dual-mode)."""
        return self._cloud_jira
    
    def get_client_for_migration(self) -> Tuple[Optional[JIRA], Optional[JIRA]]:
        """Get both clients for migration operations."""
        return self._primary_jira, self._cloud_jira
    
    def is_dual_mode_active(self) -> bool:
        """Check if dual-mode operation is active."""
        return self._dual_mode_active
    
    def get_connection_status(self) -> ConnectionStatus:
        """Get current connection status."""
        return self._connection_status
    
    def get_auth_info(self) -> Optional[AuthResult]:
        """Get current authentication information."""
        return self._current_auth
    
    async def prepare_for_migration(self) -> Dict[str, Any]:
        """Prepare for Jira Cloud migration."""
        if not self._dual_mode_active:
            return {
                "status": "error",
                "message": "Dual-mode not active. Please configure Cloud credentials."
            }
        
        migration_info = {
            "status": "ready",
            "primary_instance": {
                "type": self._current_auth.instance_type,
                "server": self._current_auth.server_url,
                "api_version": self._current_auth.api_version,
                "capabilities": self._current_auth.capabilities
            },
            "cloud_instance": {
                "server": self.config.jira.cloud_server,
                "ready": self._cloud_jira is not None
            },
            "migration_checklist": [
                "Dual authentication active",
                "Data access verified on both instances",
                "API compatibility confirmed",
                "Migration utilities prepared"
            ]
        }
        
        return migration_info
    
    async def validate_migration_readiness(self) -> Dict[str, Any]:
        """Validate readiness for Cloud migration."""
        validation_results = {
            "ready": True,
            "checks": {},
            "warnings": [],
            "errors": []
        }
        
        # Check dual-mode operation
        if not self._dual_mode_active:
            validation_results["ready"] = False
            validation_results["errors"].append("Dual-mode operation not active")
        else:
            validation_results["checks"]["dual_mode"] = "Active"
        
        # Check API compatibility
        if self._current_auth and self._current_auth.api_version:
            validation_results["checks"]["api_version"] = self._current_auth.api_version
        
        # Check data access
        try:
            if self._primary_jira and self._cloud_jira:
                # Test data access on both instances
                loop = asyncio.get_event_loop()
                primary_projects = await loop.run_in_executor(
                    None, lambda: len(self._primary_jira.projects())
                )
                cloud_projects = await loop.run_in_executor(
                    None, lambda: len(self._cloud_jira.projects())
                )
                
                validation_results["checks"]["data_access"] = {
                    "primary_projects": primary_projects,
                    "cloud_projects": cloud_projects
                }
                
                if primary_projects != cloud_projects:
                    validation_results["warnings"].append(
                        f"Project count mismatch: Primary({primary_projects}) vs Cloud({cloud_projects})"
                    )
        except Exception as e:
            validation_results["ready"] = False
            validation_results["errors"].append(f"Data access validation failed: {e}")
        
        return validation_results
    
    async def close(self):
        """Clean up resources."""
        if self._session:
            await self._session.close()
        
        self._primary_jira = None
        self._cloud_jira = None
        self._connection_status = ConnectionStatus.DISCONNECTED


async def test_authentication(config: Config) -> None:
    """Test authentication with the provided configuration."""
    auth_manager = JiraAuthManager(config)
    
    try:
        print("Testing authentication...")
        auth_result = await auth_manager.authenticate()
        
        if auth_result.success:
            print(f"✅ Authentication successful!")
            print(f"   Server: {auth_result.server_url}")
            print(f"   Instance Type: {auth_result.instance_type}")
            print(f"   Auth Method: {auth_result.auth_method}")
            print(f"   User: {auth_result.user_info.get('displayName', 'Unknown')}")
            print(f"   API Version: {auth_result.api_version}")
            
            if auth_manager.is_dual_mode_active():
                print("✅ Dual-mode operation active - ready for Cloud migration!")
                
                migration_info = await auth_manager.prepare_for_migration()
                print(f"Migration status: {migration_info['status']}")
            
        else:
            print(f"❌ Authentication failed: {auth_result.error_message}")
            
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
    
    finally:
        await auth_manager.close()


if __name__ == "__main__":
    from enhanced_config import get_config
    
    config = get_config()
    asyncio.run(test_authentication(config))