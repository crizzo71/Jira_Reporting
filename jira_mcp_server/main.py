"""Main entry point for Jira MCP Server."""

import asyncio
import logging
import sys
import signal
from typing import Optional

import click
from dotenv import load_dotenv

from .config import get_config, Config
from .mcp_server import JiraMCPServer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_logging(config: Config) -> None:
    """Setup logging configuration."""
    level = getattr(logging, config.log_level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if config.log_file:
        file_handler = logging.FileHandler(config.log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--log-file', help='Log file path')
@click.pass_context
def cli(ctx: click.Context, verbose: bool, log_file: Optional[str]) -> None:
    """Jira MCP Server for Weekly Status Reporting."""
    ctx.ensure_object(dict)
    
    try:
        config = get_config()
        
        # Override log settings from CLI
        if verbose:
            config.log_level = "DEBUG"
        if log_file:
            config.log_file = log_file
        
        setup_logging(config)
        ctx.obj['config'] = config
        
    except Exception as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--transport', '-t', default='stdio', 
              type=click.Choice(['stdio']), 
              help='Transport type for MCP server')
@click.pass_context
def serve(ctx: click.Context, transport: str) -> None:
    """Start the MCP server."""
    config = ctx.obj['config']
    
    async def run_server():
        server = JiraMCPServer(config)
        
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info(f"Starting Jira MCP Server with {transport} transport")
        logger.info(f"Jira server: {config.jira.server}")
        
        try:
            await server.run(transport)
        except KeyboardInterrupt:
            logger.info("Server interrupted by user")
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
            sys.exit(1)
    
    # Run the server
    asyncio.run(run_server())


@cli.command()
@click.pass_context
def test_connection(ctx: click.Context) -> None:
    """Test connection to Jira instance."""
    config = ctx.obj['config']
    
    async def test():
        from .jira_client import JiraClient, JiraClientError
        
        client = JiraClient(config)
        
        try:
            click.echo("Testing Jira connection...")
            await client.authenticate()
            click.echo("✅ Successfully connected to Jira!")
            
            click.echo("Fetching accessible projects...")
            projects = await client.get_projects()
            click.echo(f"✅ Found {len(projects)} accessible projects:")
            
            for project in projects[:5]:  # Show first 5 projects
                click.echo(f"  - {project.key}: {project.name}")
            
            if len(projects) > 5:
                click.echo(f"  ... and {len(projects) - 5} more")
                
        except JiraClientError as e:
            click.echo(f"❌ Connection failed: {e}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"❌ Unexpected error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(test())


@cli.command()
@click.option('--project', '-p', multiple=True, help='Project key(s) to include')
@click.option('--days', '-d', default=7, help='Number of days to look back')
@click.option('--format', '-f', default='markdown', 
              type=click.Choice(['markdown', 'html', 'confluence']),
              help='Output format')
@click.option('--team-name', '-t', required=True, help='Team name for the report')
@click.option('--output', '-o', help='Output file path')
@click.pass_context
def generate_report(
    ctx: click.Context, 
    project: tuple, 
    days: int, 
    format: str, 
    team_name: str,
    output: Optional[str]
) -> None:
    """Generate a weekly status report."""
    config = ctx.obj['config']
    
    async def generate():
        from .jira_client import JiraClient
        from .models import FilterCriteria
        from .rag_classifier import RAGClassifier
        from .report_generator import ReportGenerator
        from datetime import datetime, timedelta
        
        try:
            # Initialize components
            client = JiraClient(config)
            classifier = RAGClassifier(config.rag)
            generator = ReportGenerator(config.report)
            
            # Authenticate
            click.echo("Authenticating with Jira...")
            await client.authenticate()
            
            # Build filter criteria
            criteria = FilterCriteria()
            if project:
                criteria.projects = list(project)
            
            # Set date range
            criteria.updated_after = datetime.now() - timedelta(days=days)
            
            # Get issues
            click.echo(f"Fetching issues from last {days} days...")
            issues = await client.get_issues(criteria)
            click.echo(f"Found {len(issues)} issues")
            
            # Apply RAG classification
            click.echo("Applying RAG classification...")
            classifier.classify_issues_batch(issues)
            
            # Generate report
            click.echo("Generating report...")
            report_content = await generator.generate_weekly_report(
                team_name=team_name,
                issues=issues,
                week_ending=datetime.now().date(),
                output_format=format
            )
            
            # Output report
            if output:
                with open(output, 'w') as f:
                    f.write(report_content)
                click.echo(f"Report saved to {output}")
            else:
                click.echo(report_content)
                
        except Exception as e:
            click.echo(f"❌ Report generation failed: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(generate())


@cli.command()
@click.pass_context
def validate_config(ctx: click.Context) -> None:
    """Validate configuration settings."""
    config = ctx.obj['config']
    
    click.echo("Validating configuration...")
    
    # Check required fields
    issues = []
    
    if not config.jira.server:
        issues.append("JIRA_SERVER is not set")
    if not config.jira.email:
        issues.append("JIRA_EMAIL is not set")
    if not config.jira.api_token:
        issues.append("JIRA_API_TOKEN is not set")
    
    if issues:
        click.echo("❌ Configuration issues found:")
        for issue in issues:
            click.echo(f"  - {issue}")
        click.echo("\nPlease check your .env file or environment variables.")
        sys.exit(1)
    else:
        click.echo("✅ Configuration is valid!")
        click.echo(f"Jira Server: {config.jira.server}")
        click.echo(f"Jira Email: {config.jira.email}")
        click.echo(f"Log Level: {config.log_level}")


def main() -> None:
    """Main entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()