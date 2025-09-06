"""Configuration management for Jira MCP Server."""

import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

load_dotenv()


class JiraConfig(BaseModel):
    """Jira connection configuration."""
    
    server: str = Field(..., description="Jira server URL")
    email: str = Field(..., description="Jira user email")
    api_token: str = Field(..., description="Jira API token")
    
    @validator('server')
    def validate_server_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Server URL must start with http:// or https://')
        return v.rstrip('/')


class RAGConfig(BaseModel):
    """RAG status classification configuration."""
    
    green_max_days_in_status: int = Field(default=3, description="Max days in status for green")
    yellow_max_days_in_status: int = Field(default=7, description="Max days in status for yellow")
    red_priority_levels: list[str] = Field(default=["Highest", "High"], description="Priority levels for red status")
    blocked_statuses: list[str] = Field(default=["Blocked", "Waiting"], description="Statuses considered blocked")


class ReportConfig(BaseModel):
    """Report generation configuration."""
    
    default_report_day: str = Field(default="Wednesday", description="Default day for weekly reports")
    storage_days: int = Field(default=90, description="Days to store historical reports")
    template_path: Optional[str] = Field(default=None, description="Custom template path")


class MCPConfig(BaseModel):
    """MCP server configuration."""
    
    host: str = Field(default="localhost", description="MCP server host")
    port: int = Field(default=8000, description="MCP server port")


class Config(BaseModel):
    """Main application configuration."""
    
    jira: JiraConfig
    rag: RAGConfig = Field(default_factory=RAGConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        jira_config = JiraConfig(
            server=os.getenv("JIRA_SERVER", ""),
            email=os.getenv("JIRA_EMAIL", ""),
            api_token=os.getenv("JIRA_API_TOKEN", "")
        )
        
        rag_config = RAGConfig(
            green_max_days_in_status=int(os.getenv("GREEN_MAX_DAYS", "3")),
            yellow_max_days_in_status=int(os.getenv("YELLOW_MAX_DAYS", "7")),
            red_priority_levels=os.getenv("RED_PRIORITIES", "Highest,High").split(","),
            blocked_statuses=os.getenv("BLOCKED_STATUSES", "Blocked,Waiting").split(",")
        )
        
        report_config = ReportConfig(
            default_report_day=os.getenv("DEFAULT_REPORT_DAY", "Wednesday"),
            storage_days=int(os.getenv("REPORT_STORAGE_DAYS", "90")),
            template_path=os.getenv("TEMPLATE_PATH")
        )
        
        mcp_config = MCPConfig(
            host=os.getenv("MCP_SERVER_HOST", "localhost"),
            port=int(os.getenv("MCP_SERVER_PORT", "8000"))
        )
        
        return cls(
            jira=jira_config,
            rag=rag_config,
            report=report_config,
            mcp=mcp_config,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE")
        )
    
    def validate(self) -> None:
        """Validate configuration completeness."""
        if not all([self.jira.server, self.jira.email, self.jira.api_token]):
            raise ValueError("Jira configuration is incomplete. Please check JIRA_SERVER, JIRA_EMAIL, and JIRA_API_TOKEN environment variables.")


def get_config() -> Config:
    """Get validated configuration instance."""
    config = Config.from_env()
    config.validate()
    return config