"""Enhanced unified configuration for Jira Reports Simplified.

This consolidates configuration from:
- Jira_MCP (Python) - Current MCP server
- jira_report (Node.js) - Executive reporting tool  
- Jira-Status-Builder (Node.js) - Status builder with UI

Designed for Jira Cloud migration readiness and GitHub integration.
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field, validator, model_validator
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()


class JiraInstanceType(str, Enum):
    """Jira instance type for Cloud migration support."""
    SERVER = "server"
    CLOUD = "cloud"
    AUTO_DETECT = "auto"


class AuthType(str, Enum):
    """Authentication type for different Jira instances."""
    PAT = "pat"  # Personal Access Token (Server)
    BASIC = "basic"  # Basic auth (Cloud)
    BEARER = "bearer"  # Bearer token
    OAUTH = "oauth"  # OAuth (future)


class OutputFormat(str, Enum):
    """Report output formats."""
    MARKDOWN = "markdown"
    HTML = "html"
    PLAIN_TEXT = "text"
    JSON = "json"
    ALL = "all"


class JiraConfig(BaseModel):
    """Enhanced Jira connection configuration with Cloud migration support."""
    
    # Core connection
    server: str = Field(..., description="Jira server URL (Server or Cloud)")
    email: str = Field(..., description="Jira user email")
    api_token: str = Field(..., description="Jira API token")
    
    # Cloud migration support
    instance_type: JiraInstanceType = Field(default=JiraInstanceType.AUTO_DETECT, description="Jira instance type")
    auth_type: AuthType = Field(default=AuthType.PAT, description="Authentication type")
    
    # Cloud-specific settings
    cloud_server: Optional[str] = Field(default=None, description="Jira Cloud URL (for migration)")
    cloud_api_token: Optional[str] = Field(default=None, description="Cloud API token (for migration)")
    
    # Default project/board settings (migrated from Node.js tools)
    default_project_keys: List[str] = Field(default_factory=list, description="Default projects")
    default_board_ids: List[int] = Field(default_factory=list, description="Default boards")
    
    @validator('server')
    def validate_server_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Server URL must start with http:// or https://')
        return v.rstrip('/')
    
    @validator('cloud_server')
    def validate_cloud_server_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Cloud server URL must start with http:// or https://')
        return v.rstrip('/') if v else None


class GitHubConfig(BaseModel):
    """GitHub integration configuration."""
    
    enabled: bool = Field(default=False, description="Enable GitHub integration")
    api_token: Optional[str] = Field(default=None, description="GitHub API token")
    organization: Optional[str] = Field(default=None, description="GitHub organization")
    repositories: List[str] = Field(default_factory=list, description="Linked repositories")
    base_url: str = Field(default="https://api.github.com", description="GitHub API base URL")
    
    # Smart commit settings
    enable_smart_commits: bool = Field(default=True, description="Enable smart commit parsing")
    commit_patterns: List[str] = Field(
        default_factory=lambda: [
            r"(?i)(?:fix|fixes|fixed|close|closes|closed|resolve|resolves|resolved)\s+([A-Z]+-\d+)",
            r"([A-Z]+-\d+)"
        ],
        description="Regex patterns for issue linking"
    )


class RAGConfig(BaseModel):
    """Enhanced RAG status classification configuration."""
    
    # Time-based classification
    green_max_days_in_status: int = Field(default=3, description="Max days in status for green")
    yellow_max_days_in_status: int = Field(default=7, description="Max days in status for yellow")
    
    # Priority-based classification
    red_priority_levels: List[str] = Field(
        default_factory=lambda: ["Highest", "High"], 
        description="Priority levels for red status"
    )
    
    # Status-based classification
    blocked_statuses: List[str] = Field(
        default_factory=lambda: ["Blocked", "Waiting", "On Hold"], 
        description="Statuses considered blocked"
    )
    
    # Advanced RAG rules
    green_statuses: List[str] = Field(
        default_factory=lambda: ["Done", "Closed", "Resolved"],
        description="Statuses always considered green"
    )
    red_statuses: List[str] = Field(
        default_factory=lambda: ["Blocked", "Failed"],
        description="Statuses always considered red"
    )


class ReportConfig(BaseModel):
    """Enhanced report generation configuration."""
    
    # Basic settings (migrated from Node.js tools)
    default_report_day: str = Field(default="Wednesday", description="Default day for weekly reports")
    weeks_back: int = Field(default=1, description="Weeks back for report data")
    velocity_sprints_count: int = Field(default=6, description="Sprints for velocity calculation")
    
    # Output formats
    default_output_format: OutputFormat = Field(default=OutputFormat.MARKDOWN, description="Default output format")
    enable_all_formats: bool = Field(default=True, description="Generate all formats by default")
    
    # Template settings
    template_path: Optional[str] = Field(default=None, description="Custom template directory")
    use_handlebars_templates: bool = Field(default=True, description="Use Handlebars templates from Node.js tools")
    
    # Google Docs optimization
    optimize_for_google_docs: bool = Field(default=True, description="Optimize HTML for Google Docs")
    include_pretty_links: bool = Field(default=True, description="Include pretty links to Jira")
    
    # Storage and caching
    storage_days: int = Field(default=90, description="Days to store historical reports")
    cache_reports: bool = Field(default=True, description="Cache generated reports")


class AnalyticsConfig(BaseModel):
    """Advanced analytics and dashboard configuration."""
    
    enabled: bool = Field(default=False, description="Enable advanced analytics")
    
    # Data collection
    collect_historical_data: bool = Field(default=True, description="Collect historical data for trends")
    history_retention_days: int = Field(default=365, description="Days to retain historical data")
    
    # Dashboard settings
    enable_dashboards: bool = Field(default=False, description="Enable executive dashboards")
    dashboard_refresh_interval: int = Field(default=300, description="Dashboard refresh interval (seconds)")
    
    # Predictive analytics
    enable_forecasting: bool = Field(default=False, description="Enable velocity forecasting")
    forecast_periods: int = Field(default=6, description="Periods to forecast")


class CacheConfig(BaseModel):
    """Caching configuration for performance optimization."""
    
    enabled: bool = Field(default=True, description="Enable caching")
    
    # Cache types
    cache_projects: bool = Field(default=True, description="Cache project data")
    cache_boards: bool = Field(default=True, description="Cache board data")
    cache_users: bool = Field(default=True, description="Cache user data")
    
    # Cache durations (in seconds)
    project_cache_duration: int = Field(default=3600, description="Project cache duration")
    board_cache_duration: int = Field(default=1800, description="Board cache duration")
    user_cache_duration: int = Field(default=7200, description="User cache duration")
    
    # Cache storage
    cache_backend: str = Field(default="memory", description="Cache backend (memory, redis)")
    redis_url: Optional[str] = Field(default=None, description="Redis URL for distributed caching")


class MCPConfig(BaseModel):
    """Enhanced MCP server configuration."""
    
    # Server settings
    host: str = Field(default="localhost", description="MCP server host")
    port: int = Field(default=8000, description="MCP server port")
    
    # CLI settings
    enable_cli: bool = Field(default=True, description="Enable CLI interface")
    cli_command_prefix: str = Field(default="jira", description="CLI command prefix")
    
    # Tool configuration
    max_search_results: int = Field(default=1000, description="Maximum search results")
    enable_pagination: bool = Field(default=True, description="Enable result pagination")


class MigrationConfig(BaseModel):
    """Configuration migration and compatibility settings."""
    
    # Legacy support
    support_legacy_config: bool = Field(default=True, description="Support legacy Node.js configurations")
    auto_migrate_config: bool = Field(default=True, description="Auto-migrate from Node.js tools")
    
    # Migration paths
    nodejs_config_paths: List[str] = Field(
        default_factory=lambda: [
            "jira_report/.env",
            "jira_report/config.js",
            "Jira-Status-Builder/.env",
            "Jira-Status-Builder/config.js"
        ],
        description="Paths to legacy configurations"
    )
    
    # Backup settings
    backup_configs: bool = Field(default=True, description="Backup configurations before migration")
    backup_path: str = Field(default="config_backups", description="Backup directory")


class Config(BaseModel):
    """Main unified application configuration."""
    
    # Core configurations
    jira: JiraConfig
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
    analytics: AnalyticsConfig = Field(default_factory=AnalyticsConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    migration: MigrationConfig = Field(default_factory=MigrationConfig)
    
    # General settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    
    @model_validator(mode='after')
    def validate_configuration_completeness(self):
        """Validate that essential configuration is present."""
        if self.jira:
            if not all([self.jira.server, self.jira.email, self.jira.api_token]):
                raise ValueError(
                    "Jira configuration is incomplete. Please check JIRA_SERVER, "
                    "JIRA_EMAIL, and JIRA_API_TOKEN environment variables."
                )
        
        # Validate GitHub config if enabled
        if self.github and self.github.enabled:
            if not self.github.api_token:
                raise ValueError(
                    "GitHub integration is enabled but GITHUB_API_TOKEN is not provided."
                )
        
        return self
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables with legacy migration support."""
        
        # Primary Jira configuration
        jira_config = JiraConfig(
            server=os.getenv("JIRA_SERVER", os.getenv("JIRA_BASE_URL", "")),
            email=os.getenv("JIRA_EMAIL", ""),
            api_token=os.getenv("JIRA_API_TOKEN", ""),
            instance_type=JiraInstanceType(os.getenv("JIRA_INSTANCE_TYPE", "auto")),
            auth_type=AuthType(os.getenv("JIRA_AUTH_TYPE", "pat")),
            cloud_server=os.getenv("JIRA_CLOUD_SERVER"),
            cloud_api_token=os.getenv("JIRA_CLOUD_API_TOKEN"),
            default_project_keys=os.getenv("JIRA_PROJECT_KEYS", "").split(",") if os.getenv("JIRA_PROJECT_KEYS") else [],
            default_board_ids=[int(x) for x in os.getenv("JIRA_BOARD_IDS", "").split(",") if x.strip()]
        )
        
        # GitHub configuration
        github_config = GitHubConfig(
            enabled=os.getenv("GITHUB_ENABLED", "false").lower() == "true",
            api_token=os.getenv("GITHUB_API_TOKEN"),
            organization=os.getenv("GITHUB_ORGANIZATION"),
            repositories=os.getenv("GITHUB_REPOSITORIES", "").split(",") if os.getenv("GITHUB_REPOSITORIES") else []
        )
        
        # RAG configuration
        rag_config = RAGConfig(
            green_max_days_in_status=int(os.getenv("GREEN_MAX_DAYS", "3")),
            yellow_max_days_in_status=int(os.getenv("YELLOW_MAX_DAYS", "7")),
            red_priority_levels=os.getenv("RED_PRIORITIES", "Highest,High").split(","),
            blocked_statuses=os.getenv("BLOCKED_STATUSES", "Blocked,Waiting,On Hold").split(",")
        )
        
        # Report configuration (migrated from Node.js tools)
        report_config = ReportConfig(
            default_report_day=os.getenv("DEFAULT_REPORT_DAY", "Wednesday"),
            weeks_back=int(os.getenv("REPORT_WEEKS_BACK", "1")),
            velocity_sprints_count=int(os.getenv("VELOCITY_SPRINTS_COUNT", "6")),
            storage_days=int(os.getenv("REPORT_STORAGE_DAYS", "90")),
            template_path=os.getenv("TEMPLATE_PATH")
        )
        
        # Analytics configuration
        analytics_config = AnalyticsConfig(
            enabled=os.getenv("ANALYTICS_ENABLED", "false").lower() == "true",
            collect_historical_data=os.getenv("COLLECT_HISTORICAL_DATA", "true").lower() == "true",
            enable_dashboards=os.getenv("ENABLE_DASHBOARDS", "false").lower() == "true"
        )
        
        # Cache configuration
        cache_config = CacheConfig(
            enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            redis_url=os.getenv("REDIS_URL")
        )
        
        # MCP configuration
        mcp_config = MCPConfig(
            host=os.getenv("MCP_SERVER_HOST", "localhost"),
            port=int(os.getenv("MCP_SERVER_PORT", "8000")),
            enable_cli=os.getenv("ENABLE_CLI", "true").lower() == "true"
        )
        
        return cls(
            jira=jira_config,
            github=github_config,
            rag=rag_config,
            report=report_config,
            analytics=analytics_config,
            cache=cache_config,
            mcp=mcp_config,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE"),
            debug_mode=os.getenv("DEBUG_MODE", "false").lower() == "true"
        )
    
    def validate(self) -> None:
        """Validate configuration completeness and compatibility."""
        # Basic validation handled by root_validator
        pass
    
    def save_to_file(self, file_path: str) -> None:
        """Save configuration to file."""
        config_dict = self.dict()
        # Remove sensitive data
        config_dict['jira']['api_token'] = "***"
        if config_dict['jira']['cloud_api_token']:
            config_dict['jira']['cloud_api_token'] = "***"
        if config_dict['github']['api_token']:
            config_dict['github']['api_token'] = "***"
        
        with open(file_path, 'w') as f:
            json.dump(config_dict, f, indent=2, default=str)
    
    def migrate_from_nodejs(self, config_paths: List[str]) -> Dict[str, Any]:
        """Migrate configuration from Node.js tools."""
        migration_results = {}
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                try:
                    # Handle .env files
                    if config_path.endswith('.env'):
                        migration_results[config_path] = self._migrate_env_file(config_path)
                    # Handle .js config files
                    elif config_path.endswith('.js'):
                        migration_results[config_path] = self._migrate_js_config(config_path)
                except Exception as e:
                    migration_results[config_path] = {"error": str(e)}
        
        return migration_results
    
    def _migrate_env_file(self, env_path: str) -> Dict[str, Any]:
        """Migrate .env file configuration."""
        migrated = {}
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    migrated[key] = value
        return migrated
    
    def _migrate_js_config(self, js_path: str) -> Dict[str, Any]:
        """Migrate JavaScript config file (basic extraction)."""
        # This would need more sophisticated parsing for actual JS files
        # For now, just note that migration is needed
        return {"status": "Manual migration required for JS config"}


def get_config() -> Config:
    """Get validated configuration instance with migration support."""
    config = Config.from_env()
    config.validate()
    
    # Auto-migrate if enabled
    if config.migration.auto_migrate_config:
        migration_results = config.migrate_from_nodejs(config.migration.nodejs_config_paths)
        if migration_results:
            print("Configuration migration completed:", migration_results)
    
    return config


def create_sample_env_file(file_path: str = ".env.example") -> None:
    """Create a comprehensive sample environment file."""
    sample_env = """# Jira Reports Simplified - Unified Configuration
# This file consolidates settings from all three tools:
# - Jira_MCP (Python)
# - jira_report (Node.js) 
# - Jira-Status-Builder (Node.js)

# === JIRA CONFIGURATION ===
# Primary Jira server (current)
JIRA_SERVER=https://issues.redhat.com
JIRA_EMAIL=your.email@redhat.com
JIRA_API_TOKEN=your_personal_access_token_here

# Jira instance type and authentication
JIRA_INSTANCE_TYPE=auto  # auto, server, cloud
JIRA_AUTH_TYPE=pat       # pat, basic, bearer

# Jira Cloud migration settings (for 6-month migration)
JIRA_CLOUD_SERVER=https://your-domain.atlassian.net
JIRA_CLOUD_API_TOKEN=your_cloud_api_token_here

# Default projects and boards (migrated from Node.js tools)
JIRA_PROJECT_KEYS=OCM,TEAM1,TEAM2
JIRA_BOARD_IDS=20600,17975,17291

# === GITHUB INTEGRATION ===
GITHUB_ENABLED=false
GITHUB_API_TOKEN=your_github_token_here
GITHUB_ORGANIZATION=your_org
GITHUB_REPOSITORIES=repo1,repo2,repo3

# === RAG STATUS CLASSIFICATION ===
GREEN_MAX_DAYS=3
YELLOW_MAX_DAYS=7
RED_PRIORITIES=Highest,High
BLOCKED_STATUSES=Blocked,Waiting,On Hold

# === REPORT CONFIGURATION ===
# Basic settings (from Node.js tools)
DEFAULT_REPORT_DAY=Wednesday
REPORT_WEEKS_BACK=1
VELOCITY_SPRINTS_COUNT=6
REPORT_STORAGE_DAYS=90

# Template settings
TEMPLATE_PATH=./templates
USE_HANDLEBARS_TEMPLATES=true
OPTIMIZE_FOR_GOOGLE_DOCS=true

# === ADVANCED ANALYTICS ===
ANALYTICS_ENABLED=false
COLLECT_HISTORICAL_DATA=true
ENABLE_DASHBOARDS=false

# === PERFORMANCE & CACHING ===
CACHE_ENABLED=true
REDIS_URL=redis://localhost:6379

# === MCP SERVER ===
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8000
ENABLE_CLI=true

# === LOGGING & DEBUG ===
LOG_LEVEL=INFO
LOG_FILE=jira_mcp.log
DEBUG_MODE=false
"""
    
    with open(file_path, 'w') as f:
        f.write(sample_env)
    
    print(f"Sample environment file created: {file_path}")


if __name__ == "__main__":
    # Create sample environment file
    create_sample_env_file()
    
    # Test configuration loading
    try:
        config = get_config()
        print("Configuration loaded successfully!")
        config.save_to_file("config_sample.json")
        print("Sample configuration saved to config_sample.json")
    except Exception as e:
        print(f"Configuration error: {e}")
        print("Please check your environment variables.")