"""Enhanced report generator for Jira Reports Simplified.

Migrates proven functionality from Node.js tools:
- jira_report/templates (Handlebars templates)
- Jira-Status-Builder/templates 
- Manual input collection
- Multi-format output (MD/HTML/Text)
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Template engine - using Jinja2 as Python equivalent to Handlebars
from jinja2 import Environment, FileSystemLoader, BaseLoader, DictLoader
import aiofiles

from enhanced_config import Config, OutputFormat
from enhanced_auth import JiraAuthManager
from jira_mcp_server.models import Issue, Board, Project, RAGStatus, WeeklyReportData

logger = logging.getLogger(__name__)


class ReportType(str, Enum):
    """Types of reports that can be generated."""
    WEEKLY_EXECUTIVE = "weekly_executive"
    WEEKLY_DETAILED = "weekly_detailed"
    MONTHLY_SUMMARY = "monthly_summary"
    CUSTOM = "custom"


@dataclass
class ReportContext:
    """Context data for report generation."""
    team_name: str
    date_range: str
    generated_on: str
    total_issues: int
    completed_issues: List[Dict[str, Any]]
    in_progress_issues: List[Dict[str, Any]]
    issues_needing_attention: List[Dict[str, Any]]
    velocity: Dict[str, Any]
    manual_input: Dict[str, Any]
    boards: List[Dict[str, Any]]
    multi_board: bool
    work_breakdown: Dict[str, Any]


@dataclass
class ManualInputData:
    """Manual input data structure (migrated from Node.js tool)."""
    report_date: str
    team_morale: Dict[str, str]
    celebrations: Dict[str, str]
    milestones: Dict[str, str]
    forward_looking: Dict[str, str]
    velocity_highlights: Dict[str, str]


class TemplateManager:
    """Manages report templates with Jinja2 (Python equivalent to Handlebars)."""
    
    def __init__(self, template_path: Optional[str] = None):
        self.template_path = template_path or self._get_default_template_path()
        self.env = self._setup_jinja_environment()
        self._register_custom_filters()
    
    def _get_default_template_path(self) -> str:
        """Get default template directory."""
        return str(Path(__file__).parent / "templates")
    
    def _setup_jinja_environment(self) -> Environment:
        """Set up Jinja2 environment."""
        # Create templates directory if it doesn't exist
        Path(self.template_path).mkdir(exist_ok=True)
        
        # Use both file system and dict loader for flexibility
        file_loader = FileSystemLoader(self.template_path)
        
        # Built-in templates (migrated from Node.js)
        dict_loader = DictLoader(self._get_builtin_templates())
        
        # Combined loader
        from jinja2 import ChoiceLoader
        combined_loader = ChoiceLoader([file_loader, dict_loader])
        
        env = Environment(
            loader=combined_loader,
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        return env
    
    def _register_custom_filters(self):
        """Register custom Jinja2 filters (equivalent to Handlebars helpers)."""
        
        def format_date(date_str: str, format_str: str = '%Y-%m-%d') -> str:
            """Format date string."""
            if isinstance(date_str, str):
                try:
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    return date_obj.strftime(format_str)
                except:
                    return date_str
            return str(date_str)
        
        def progress_bar(percentage: int, width: int = 20) -> str:
            """Create ASCII progress bar."""
            filled = int(percentage * width / 100)
            bar = '█' * filled + '░' * (width - filled)
            return f"{bar} {percentage}%"
        
        def truncate_summary(text: str, max_length: int = 60) -> str:
            """Truncate summary text."""
            if len(text) <= max_length:
                return text
            return text[:max_length-3] + "..."
        
        def jira_link(issue_key: str, base_url: str) -> str:
            """Create Jira issue link."""
            return f"{base_url}/browse/{issue_key}"
        
        def default_if_empty(value: Any, default: str = "Not specified") -> str:
            """Return default if value is empty."""
            if not value or (isinstance(value, str) and not value.strip()):
                return default
            return str(value)
        
        # Register filters
        self.env.filters['format_date'] = format_date
        self.env.filters['progress_bar'] = progress_bar
        self.env.filters['truncate_summary'] = truncate_summary
        self.env.filters['jira_link'] = jira_link
        self.env.filters['default_if_empty'] = default_if_empty
    
    def _get_builtin_templates(self) -> Dict[str, str]:
        """Get built-in templates migrated from Node.js tools."""
        return {
            'weekly_markdown.j2': self._get_weekly_markdown_template(),
            'weekly_html.j2': self._get_weekly_html_template(),
            'weekly_text.j2': self._get_weekly_text_template()
        }
    
    def _get_weekly_markdown_template(self) -> str:
        """Weekly Markdown template (migrated from weekly-summary.hbs)."""
        return """# Weekly Team Report: {{ date_range }}

**Prepared For:** Executive Leadership  
**Prepared By:** Multi-Cluster Management Engineering Team  
**Team:** {{ team_name }}  
**Report Date:** {{ generated_on }}

---

## 1.0 Team Performance Metrics

### 1.1 Team Velocity

**Average Velocity:** {{ velocity.average }} {{ velocity.unit }}  
**Velocity Trend:** {{ velocity.trend }}  

{% if velocity.data %}
**Recent Performance:**
{% for period in velocity.data %}
- **{{ period.period }}**: {{ period.value }} {{ velocity.unit }}
{% endfor %}
{% endif %}

**Highlights:** {{ manual_input.velocity_highlights.trends | default_if_empty("No specific trends noted.") }}

{% if manual_input.velocity_highlights.anomalies %}
**Context:** {{ manual_input.velocity_highlights.anomalies }}
{% endif %}

### 1.2 Key Epic-Level Accomplishments

**Completed Epics and Major Initiatives:**
{% for issue in completed_issues %}
- **[{{ issue.key }}]({{ issue.url }})** - {{ issue.summary }}
  - Type: {{ issue.issuetype }} | Priority: {{ issue.priority }}
  - Assignee: {{ issue.assignee | default_if_empty("Unassigned") }}
  {% if issue.epic %}- Epic: **[{{ issue.epic.key }}]({{ issue.epic.url }})** - {{ issue.epic.summary }}{% if issue.epic.progress %} ({{ issue.epic.progress.percentage }}% complete - {{ issue.epic.progress.completed }}/{{ issue.epic.progress.total }} issues){% endif %}{% endif %}
  {% if issue.parent %}- Parent: **[{{ issue.parent.key }}]({{ issue.parent.url }})** - {{ issue.parent.summary }}{% endif %}
{% endfor %}

{% if not completed_issues %}
_No Epic-level work items were completed during this period._
{% endif %}

**Milestones Reached:**
{{ manual_input.milestones.milestones_reached | default_if_empty("No major milestones reported.") }}

{% if manual_input.milestones.releases %}
**Releases/Deliverables:** {{ manual_input.milestones.releases }}
{% endif %}

---

## 2.0 Team Morale and Culture

### 2.1 Associate Morale

{{ manual_input.team_morale.assessment | default_if_empty("No morale assessment provided.") }}

{% if manual_input.team_morale.challenges %}
**Current Challenges:** {{ manual_input.team_morale.challenges }}
{% endif %}

{% if manual_input.team_morale.support_needed %}
**Support Needed:** {{ manual_input.team_morale.support_needed }}
{% endif %}

### 2.2 Celebrations and Noteworthy Achievements

**Celebrations:**
{{ manual_input.celebrations.team_celebrations | default_if_empty("No team celebrations reported.") }}

**Kudos/Shoutouts:**
{{ manual_input.celebrations.kudos | default_if_empty("No individual recognition reported.") }}

{% if manual_input.celebrations.noteworthy %}
**Other Achievements:** {{ manual_input.celebrations.noteworthy }}
{% endif %}

---

## 3.0 Roadmap and Forward-Looking Items

### 3.1 Upcoming Epic-Level Priorities

**Epics and Major Initiatives In Progress:**
{% for issue in in_progress_issues %}
- **[{{ issue.key }}]({{ issue.url }})** - {{ issue.summary }}
  - Status: {{ issue.status }} | Priority: {{ issue.priority }}
  - Assignee: {{ issue.assignee | default_if_empty("Unassigned") }}
  {% if issue.epic %}- Epic: **[{{ issue.epic.key }}]({{ issue.epic.url }})** - {{ issue.epic.summary }}{% if issue.epic.progress %} ({{ issue.epic.progress.percentage }}% complete - {{ issue.epic.progress.completed }}/{{ issue.epic.progress.total }} issues){% endif %}{% endif %}
  {% if issue.parent %}- Parent: **[{{ issue.parent.key }}]({{ issue.parent.url }})** - {{ issue.parent.summary }}{% endif %}
{% endfor %}

{% if not in_progress_issues %}
_No Epic-level work currently in progress._
{% endif %}

**Next Period Focus:**
{{ manual_input.forward_looking.upcoming_priorities | default_if_empty("No specific priorities identified for next period.") }}

**Potential Blockers/Risks:**
{{ manual_input.forward_looking.potential_blockers | default_if_empty("No significant blockers or risks identified.") }}

---

## 4.0 Issues Requiring Attention

{% for issue in issues_needing_attention %}
- **[{{ issue.key }}]({{ issue.url }})** - {{ issue.summary }}
  - Status: {{ issue.status }}
  - Last Updated: {{ issue.last_updated | format_date }}
  - Concern: {{ issue.reason }}
  {% if issue.epic %}- Epic: **[{{ issue.epic.key }}]({{ issue.epic.url }})** - {{ issue.epic.summary }}{% if issue.epic.progress %} ({{ issue.epic.progress.percentage }}% complete - {{ issue.epic.progress.completed }}/{{ issue.epic.progress.total }} issues){% endif %}{% endif %}
  {% if issue.parent %}- Parent: **[{{ issue.parent.key }}]({{ issue.parent.url }})** - {{ issue.parent.summary }}{% endif %}
{% endfor %}

{% if not issues_needing_attention %}
_No issues require special attention at this time._
{% endif %}

---

## 5.0 Detailed Metrics

### 5.1 Work Breakdown
- **Total Issues Reviewed:** {{ total_issues }}
- **Completed Issues:** {{ completed_issues | length }}
- **Issues In Progress:** {{ in_progress_issues | length }}
- **Issues Requiring Attention:** {{ issues_needing_attention | length }}

{% if multi_board %}
### 5.2 Board Coverage
This report aggregates data from **{{ boards | length }} boards**:
{% for board in boards %}
- {{ board.name }} ({{ board.type }})
{% endfor %}
{% endif %}

---

*This report was automatically generated from Jira data and manual team input on {{ generated_on }}*"""
    
    def _get_weekly_html_template(self) -> str:
        """Weekly HTML template (migrated from google-docs.hbs)."""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Weekly Team Report: {{ date_range }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: white;
        }
        h1 {
            color: #1a73e8;
            border-bottom: 2px solid #1a73e8;
            padding-bottom: 10px;
        }
        h2 {
            color: #34a853;
            margin-top: 30px;
        }
        h3 {
            color: #ea4335;
            margin-top: 25px;
        }
        .header-info {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .metric-box {
            background-color: #e8f0fe;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
        .issue-item {
            background-color: #f8f9fa;
            padding: 10px;
            margin: 5px 0;
            border-left: 4px solid #34a853;
            border-radius: 4px;
        }
        .issue-key {
            font-weight: bold;
            color: #1a73e8;
        }
        .epic-info {
            color: #9c27b0;
            font-size: 0.9em;
            margin-left: 10px;
        }
        .parent-info {
            color: #ff9800;
            font-size: 0.9em;
            margin-left: 10px;
        }
        .progress-bar {
            background-color: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            height: 12px;
            display: inline-block;
            width: 60px;
            margin-left: 5px;
        }
        .progress-fill {
            background-color: #4caf50;
            height: 100%;
            transition: width 0.3s ease;
        }
        .velocity-data {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 10px 0;
        }
        .velocity-item {
            background-color: #fff;
            padding: 8px 12px;
            border: 1px solid #dadce0;
            border-radius: 4px;
            min-width: 120px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }
        th, td {
            border: 1px solid #dadce0;
            padding: 8px 12px;
            text-align: left;
        }
        th {
            background-color: #f8f9fa;
            font-weight: bold;
        }
        .section-summary {
            background-color: #e8f5e8;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #dadce0;
            font-style: italic;
            color: #5f6368;
        }
    </style>
</head>
<body>

<h1>Weekly Team Report: {{ date_range }}</h1>

<div class="header-info">
    <strong>Prepared For:</strong> Executive Leadership<br>
    <strong>Prepared By:</strong> Multi-Cluster Management Engineering Team<br>
    <strong>Team:</strong> {{ team_name }}<br>
    <strong>Report Date:</strong> {{ generated_on }}<br>
    <strong>Total Issues Reviewed:</strong> {{ total_issues }}
</div>

<h2>1.0 Team Performance Metrics</h2>

<h3>1.1 Team Velocity</h3>
<div class="metric-box">
    <strong>Average Velocity:</strong> {{ velocity.average }} {{ velocity.unit }}<br>
    <strong>Velocity Trend:</strong> {{ velocity.trend }}<br>
    
    {% if velocity.data %}
    <h4>Recent Performance:</h4>
    <div class="velocity-data">
        {% for period in velocity.data %}
        <div class="velocity-item">
            <strong>{{ period.period }}:</strong> {{ period.value }} {{ velocity.unit }}
        </div>
        {% endfor %}
    </div>
    {% endif %}
    
    <p><strong>Highlights:</strong> {{ manual_input.velocity_highlights.trends | default_if_empty("No specific trends noted.") }}</p>
</div>

<h3>1.2 Key Epic-Level Accomplishments</h3>

{% if completed_issues %}
<h4>Completed Epics and Major Initiatives:</h4>
{% for issue in completed_issues %}
<div class="issue-item">
    <a href="{{ issue.url }}" class="issue-key">{{ issue.key }}</a> - {{ issue.summary }}<br>
    <small>Type: {{ issue.issuetype }} | Priority: {{ issue.priority }}{% if issue.assignee %} | Assignee: {{ issue.assignee }}{% endif %}</small>
    {% if issue.epic %}<br><span class="epic-info">Epic: <a href="{{ issue.epic.url }}">{{ issue.epic.key }}</a> - {{ issue.epic.summary }}{% if issue.epic.progress %} <span class="progress-bar"><span class="progress-fill" style="width: {{ issue.epic.progress.percentage }}%"></span></span> {{ issue.epic.progress.percentage }}% ({{ issue.epic.progress.completed }}/{{ issue.epic.progress.total }}){% endif %}</span>{% endif %}
    {% if issue.parent %}<br><span class="parent-info">Parent: <a href="{{ issue.parent.url }}">{{ issue.parent.key }}</a> - {{ issue.parent.summary }}</span>{% endif %}
</div>
{% endfor %}
{% else %}
<p><em>No completed work found in this period.</em></p>
{% endif %}

<div class="section-summary">
    <strong>Summary:</strong> {{ completed_issues | length }} issues completed this period.
</div>

<h2>2.0 Team Morale and Culture</h2>

<h3>2.1 Associate Morale</h3>
<p>{{ manual_input.team_morale.assessment | default_if_empty("No morale update provided for this period.") }}</p>

<h3>2.2 Celebrations and Achievements</h3>
<p>{{ manual_input.celebrations.team_celebrations | default_if_empty("No celebrations reported for this period.") }}</p>

<h2>3.0 Roadmap and Forward-Looking</h2>

<h3>3.1 Upcoming Epic-Level Priorities</h3>
{% if in_progress_issues %}
<h4>Epics and Major Initiatives in Progress:</h4>
{% for issue in in_progress_issues %}
<div class="issue-item">
    <a href="{{ issue.url }}" class="issue-key">{{ issue.key }}</a> - {{ issue.summary }}<br>
    <small>Type: {{ issue.issuetype }} | Priority: {{ issue.priority }}{% if issue.assignee %} | Assignee: {{ issue.assignee }}{% endif %}</small>
    {% if issue.epic %}<br><span class="epic-info">Epic: <a href="{{ issue.epic.url }}">{{ issue.epic.key }}</a> - {{ issue.epic.summary }}{% if issue.epic.progress %} <span class="progress-bar"><span class="progress-fill" style="width: {{ issue.epic.progress.percentage }}%"></span></span> {{ issue.epic.progress.percentage }}% ({{ issue.epic.progress.completed }}/{{ issue.epic.progress.total }}){% endif %}</span>{% endif %}
    {% if issue.parent %}<br><span class="parent-info">Parent: <a href="{{ issue.parent.url }}">{{ issue.parent.key }}</a> - {{ issue.parent.summary }}</span>{% endif %}
</div>
{% endfor %}
{% endif %}

{% if manual_input.forward_looking.upcoming_priorities %}
<h4>Strategic Priorities:</h4>
<p>{{ manual_input.forward_looking.upcoming_priorities }}</p>
{% endif %}

<h3>3.2 Potential Blockers</h3>
{% if manual_input.forward_looking.potential_blockers %}
<p>{{ manual_input.forward_looking.potential_blockers }}</p>
{% endif %}

{% if issues_needing_attention %}
<h4>Issues Requiring Attention:</h4>
{% for issue in issues_needing_attention %}
<div class="issue-item">
    <a href="{{ issue.url }}" class="issue-key">{{ issue.key }}</a> - {{ issue.summary }}<br>
    <small>Status: {{ issue.status }} | Last Updated: {{ issue.updated | format_date }}{% if issue.assignee %} | Assignee: {{ issue.assignee }}{% endif %}</small>
    {% if issue.epic %}<br><span class="epic-info">Epic: <a href="{{ issue.epic.url }}">{{ issue.epic.key }}</a> - {{ issue.epic.summary }}{% if issue.epic.progress %} <span class="progress-bar"><span class="progress-fill" style="width: {{ issue.epic.progress.percentage }}%"></span></span> {{ issue.epic.progress.percentage }}% ({{ issue.epic.progress.completed }}/{{ issue.epic.progress.total }}){% endif %}</span>{% endif %}
    {% if issue.parent %}<br><span class="parent-info">Parent: <a href="{{ issue.parent.url }}">{{ issue.parent.key }}</a> - {{ issue.parent.summary }}</span>{% endif %}
</div>
{% endfor %}
{% endif %}

<h2>4.0 Detailed Metrics</h2>

<h3>4.1 Work Breakdown</h3>
<table>
    <tr>
        <th>Category</th>
        <th>Count</th>
        <th>Percentage</th>
    </tr>
    <tr>
        <td>Total Issues Reviewed</td>
        <td>{{ total_issues }}</td>
        <td>100%</td>
    </tr>
    <tr>
        <td>Completed Issues</td>
        <td>{{ completed_issues | length }}</td>
        <td>{{ work_breakdown.completed_percentage }}%</td>
    </tr>
    <tr>
        <td>Issues In Progress</td>
        <td>{{ in_progress_issues | length }}</td>
        <td>{{ work_breakdown.in_progress_percentage }}%</td>
    </tr>
    <tr>
        <td>Issues Needing Attention</td>
        <td>{{ issues_needing_attention | length }}</td>
        <td>{{ work_breakdown.attention_percentage }}%</td>
    </tr>
</table>

{% if multi_board %}
<h3>4.2 Board Coverage</h3>
<p>This report aggregates data from <strong>{{ boards | length }} boards</strong>:</p>
<ul>
{% for board in boards %}
    <li>{{ board.name }} ({{ board.type }})</li>
{% endfor %}
</ul>
{% endif %}

<div class="footer">
    Generated on {{ generated_on }} | Multi-Cluster Management Engineering Team
</div>

</body>
</html>"""
    
    def _get_weekly_text_template(self) -> str:
        """Weekly plain text template (migrated from plain-text.hbs)."""
        return """Weekly Team Report: {{ date_range }}
====================================================

Prepared For: Executive Leadership
Prepared By: Multi-Cluster Management Engineering Team
Team: {{ team_name }}
Report Date: {{ generated_on }}
Total Issues Reviewed: {{ total_issues }}

1.0 TEAM PERFORMANCE METRICS
============================

1.1 Team Velocity
-----------------
Average Velocity: {{ velocity.average }} {{ velocity.unit }}
Velocity Trend: {{ velocity.trend }}

Recent Performance:
{% for period in velocity.data %}
- {{ period.period }}: {{ period.value }} {{ velocity.unit }}
{% endfor %}

Highlights: {{ manual_input.velocity_highlights.trends | default_if_empty("No specific trends noted.") }}

1.2 Key Activities and Accomplishments
---------------------------------------

Completed Work:
{% for issue in completed_issues %}
• {{ issue.key }} - {{ issue.summary }} ({{ issue.url }})
  Type: {{ issue.issuetype }} | Priority: {{ issue.priority }}{% if issue.assignee %} | Assignee: {{ issue.assignee }}{% endif %}
  {% if issue.epic %}Epic: {{ issue.epic.key }} - {{ issue.epic.summary }} ({{ issue.epic.url }}){% if issue.epic.progress %} [{{ issue.epic.progress.percentage }}% complete - {{ issue.epic.progress.completed }}/{{ issue.epic.progress.total }} issues]{% endif %}{% endif %}
  {% if issue.parent %}Parent: {{ issue.parent.key }} - {{ issue.parent.summary }} ({{ issue.parent.url }}){% endif %}

{% endfor %}

Summary: {{ completed_issues | length }} issues completed this period.

2.0 TEAM MORALE AND CULTURE
============================

2.1 Associate Morale
--------------------
{{ manual_input.team_morale.assessment | default_if_empty("No morale update provided for this period.") }}

2.2 Celebrations and Achievements
----------------------------------
{{ manual_input.celebrations.team_celebrations | default_if_empty("No celebrations reported for this period.") }}

3.0 ROADMAP AND FORWARD-LOOKING
================================

3.1 Upcoming Priorities
------------------------

Current Work in Progress:
{% for issue in in_progress_issues %}
• {{ issue.key }} - {{ issue.summary }} ({{ issue.url }})
  Type: {{ issue.issuetype }} | Priority: {{ issue.priority }}{% if issue.assignee %} | Assignee: {{ issue.assignee }}{% endif %}
  {% if issue.epic %}Epic: {{ issue.epic.key }} - {{ issue.epic.summary }} ({{ issue.epic.url }}){% if issue.epic.progress %} [{{ issue.epic.progress.percentage }}% complete - {{ issue.epic.progress.completed }}/{{ issue.epic.progress.total }} issues]{% endif %}{% endif %}
  {% if issue.parent %}Parent: {{ issue.parent.key }} - {{ issue.parent.summary }} ({{ issue.parent.url }}){% endif %}

{% endfor %}

{% if manual_input.forward_looking.upcoming_priorities %}
Strategic Priorities:
{{ manual_input.forward_looking.upcoming_priorities }}
{% endif %}

3.2 Potential Blockers
-----------------------
{% if manual_input.forward_looking.potential_blockers %}
{{ manual_input.forward_looking.potential_blockers }}
{% endif %}

{% if issues_needing_attention %}
Issues Requiring Attention:
{% for issue in issues_needing_attention %}
• {{ issue.key }} - {{ issue.summary }} ({{ issue.url }})
  Status: {{ issue.status }} | Last Updated: {{ issue.updated | format_date }}{% if issue.assignee %} | Assignee: {{ issue.assignee }}{% endif %}
  {% if issue.epic %}Epic: {{ issue.epic.key }} - {{ issue.epic.summary }} ({{ issue.epic.url }}){% if issue.epic.progress %} [{{ issue.epic.progress.percentage }}% complete - {{ issue.epic.progress.completed }}/{{ issue.epic.progress.total }} issues]{% endif %}{% endif %}
  {% if issue.parent %}Parent: {{ issue.parent.key }} - {{ issue.parent.summary }} ({{ issue.parent.url }}){% endif %}

{% endfor %}
{% endif %}

4.0 DETAILED METRICS
=====================

4.1 Work Breakdown
-------------------
Completed Issues: {{ completed_issues | length }} ({{ work_breakdown.completed_percentage }}%)
In Progress: {{ in_progress_issues | length }} ({{ work_breakdown.in_progress_percentage }}%)
Needs Attention: {{ issues_needing_attention | length }} ({{ work_breakdown.attention_percentage }}%)

{% if multi_board %}
4.2 Board Coverage
-------------------
This report aggregates data from {{ boards | length }} boards:
{% for board in boards %}
- {{ board.name }} ({{ board.type }})
{% endfor %}
{% endif %}

----------------------------------------------------
Generated on {{ generated_on }}
Multi-Cluster Management Engineering Team"""
    
    def get_template(self, template_name: str):
        """Get template by name."""
        return self.env.get_template(template_name)
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render template with context."""
        template = self.get_template(template_name)
        return template.render(**context)


class ManualInputCollector:
    """Collects manual input data (migrated from Node.js manual-input.js)."""
    
    def __init__(self, input_file_path: str = "manual-input.json"):
        self.input_file_path = input_file_path
        self.input_data = {}
    
    async def load_existing_input(self) -> ManualInputData:
        """Load existing manual input data."""
        try:
            if os.path.exists(self.input_file_path):
                async with aiofiles.open(self.input_file_path, 'r') as f:
                    content = await f.read()
                    data = json.loads(content)
                    logger.info("📄 Loaded existing manual input data")
                    return self._dict_to_manual_input(data)
        except Exception as e:
            logger.warning(f"Could not load existing input: {e}")
        
        logger.info("📝 No existing manual input found, starting fresh")
        return self._get_default_template()
    
    def _get_default_template(self) -> ManualInputData:
        """Get default manual input template."""
        return ManualInputData(
            report_date=datetime.now().strftime('%Y-%m-%d'),
            team_morale={
                "assessment": "",
                "challenges": "",
                "support_needed": ""
            },
            celebrations={
                "team_celebrations": "",
                "kudos": "",
                "noteworthy": ""
            },
            milestones={
                "milestones_reached": "",
                "releases": ""
            },
            forward_looking={
                "upcoming_priorities": "",
                "potential_blockers": "",
                "risks": ""
            },
            velocity_highlights={
                "trends": "",
                "anomalies": "",
                "context": ""
            }
        )
    
    def _dict_to_manual_input(self, data: Dict[str, Any]) -> ManualInputData:
        """Convert dictionary to ManualInputData."""
        return ManualInputData(
            report_date=data.get('report_date', datetime.now().strftime('%Y-%m-%d')),
            team_morale=data.get('team_morale', {}),
            celebrations=data.get('celebrations', {}),
            milestones=data.get('milestones', {}),
            forward_looking=data.get('forward_looking', {}),
            velocity_highlights=data.get('velocity_highlights', {})
        )
    
    async def save_input_data(self, data: ManualInputData) -> None:
        """Save manual input data to file."""
        try:
            async with aiofiles.open(self.input_file_path, 'w') as f:
                await f.write(json.dumps(asdict(data), indent=2))
            logger.info(f"💾 Manual input data saved to {self.input_file_path}")
        except Exception as e:
            logger.error(f"Failed to save manual input data: {e}")
    
    async def collect_interactive_input(self) -> ManualInputData:
        """Collect manual input interactively (simplified version)."""
        # For now, return existing data or defaults
        # In Phase 3, we'll add interactive CLI input collection
        existing_data = await self.load_existing_input()
        
        # TODO: Add interactive CLI collection in Phase 3
        logger.info("📋 Manual input collection - using existing/default data")
        logger.info("   (Interactive collection will be added in Phase 3)")
        
        return existing_data


class EnhancedReportGenerator:
    """Enhanced report generator with multi-format support."""
    
    def __init__(self, config: Config, auth_manager: JiraAuthManager):
        self.config = config
        self.auth_manager = auth_manager
        self.template_manager = TemplateManager(config.report.template_path)
        self.manual_input_collector = ManualInputCollector()
        
        # Report output directories
        self.output_dir = Path("reports")
        self.markdown_dir = self.output_dir / "markdown"
        self.html_dir = self.output_dir / "google-docs"
        self.text_dir = self.output_dir / "plain-text"
        
        # Create output directories
        for dir_path in [self.markdown_dir, self.html_dir, self.text_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    async def generate_weekly_report(
        self,
        team_name: str,
        board_ids: Optional[List[int]] = None,
        project_keys: Optional[List[str]] = None,
        output_formats: Optional[List[OutputFormat]] = None,
        include_manual_input: bool = True
    ) -> Dict[str, str]:
        """Generate weekly report in specified formats."""
        
        logger.info(f"🚀 Generating weekly report for team: {team_name}")
        
        # Default output formats
        if output_formats is None:
            if self.config.report.enable_all_formats:
                output_formats = [OutputFormat.MARKDOWN, OutputFormat.HTML, OutputFormat.PLAIN_TEXT]
            else:
                output_formats = [self.config.report.default_output_format]
        
        # Collect manual input if requested
        if include_manual_input:
            manual_input_data = await self.manual_input_collector.load_existing_input()
        else:
            manual_input_data = self.manual_input_collector._get_default_template()
        
        # Get Jira data
        report_context = await self._build_report_context(
            team_name=team_name,
            board_ids=board_ids,
            project_keys=project_keys,
            manual_input_data=manual_input_data
        )
        
        # Generate reports in requested formats
        generated_files = {}
        
        for output_format in output_formats:
            try:
                file_path = await self._generate_format_specific_report(
                    report_context=report_context,
                    output_format=output_format
                )
                generated_files[output_format.value] = file_path
                logger.info(f"✅ Generated {output_format.value} report: {file_path}")
            except Exception as e:
                logger.error(f"❌ Failed to generate {output_format.value} report: {e}")
                generated_files[output_format.value] = None
        
        return generated_files
    
    async def _build_report_context(
        self,
        team_name: str,
        board_ids: Optional[List[int]],
        project_keys: Optional[List[str]],
        manual_input_data: ManualInputData
    ) -> ReportContext:
        """Build report context from Jira data and manual input."""
        
        # TODO: Implement full Jira data collection
        # For Phase 2, we'll use placeholder data to test templates
        
        # Placeholder context for testing
        date_range = f"{(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}"
        
        context = ReportContext(
            team_name=team_name,
            date_range=date_range,
            generated_on=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_issues=15,  # Placeholder
            completed_issues=[
                {
                    "key": "OCM-18340",
                    "summary": "Example completed issue",
                    "url": f"{self.config.jira.server}/browse/OCM-18340",
                    "issuetype": "Story",
                    "priority": "High",
                    "assignee": "Christine Rizzo"
                }
            ],
            in_progress_issues=[
                {
                    "key": "OCM-18341",
                    "summary": "Example in-progress issue", 
                    "url": f"{self.config.jira.server}/browse/OCM-18341",
                    "issuetype": "Epic",
                    "priority": "Medium",
                    "assignee": "Team Member",
                    "status": "In Progress"
                }
            ],
            issues_needing_attention=[],
            velocity={
                "average": 12,
                "unit": "story points",
                "trend": "Stable",
                "data": [
                    {"period": "Sprint 1", "value": 11},
                    {"period": "Sprint 2", "value": 13},
                    {"period": "Sprint 3", "value": 12}
                ]
            },
            manual_input=asdict(manual_input_data),
            boards=[],
            multi_board=len(board_ids) > 1 if board_ids else False,
            work_breakdown={
                "completed_percentage": 67,
                "in_progress_percentage": 27,
                "attention_percentage": 6
            }
        )
        
        return context
    
    async def _generate_format_specific_report(
        self,
        report_context: ReportContext,
        output_format: OutputFormat
    ) -> str:
        """Generate report in specific format."""
        
        # Convert context to dict for template rendering
        context_dict = asdict(report_context)
        
        # Determine template and output file
        if output_format == OutputFormat.MARKDOWN:
            template_name = "weekly_markdown.j2"
            file_extension = "md"
            output_dir = self.markdown_dir
        elif output_format == OutputFormat.HTML:
            template_name = "weekly_html.j2"
            file_extension = "html"
            output_dir = self.html_dir
        elif output_format == OutputFormat.PLAIN_TEXT:
            template_name = "weekly_text.j2"
            file_extension = "txt"
            output_dir = self.text_dir
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
        
        # Generate filename
        safe_team_name = report_context.team_name.replace(" ", "-").lower()
        timestamp = datetime.now().strftime('%Y-%m-%d')
        filename = f"weekly-report-{safe_team_name}-{timestamp}.{file_extension}"
        file_path = output_dir / filename
        
        # Render template
        rendered_content = self.template_manager.render_template(template_name, context_dict)
        
        # Save to file
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(rendered_content)
        
        return str(file_path)


# Test function for Phase 2 validation
async def test_report_generation(config: Config) -> None:
    """Test the enhanced report generator."""
    auth_manager = JiraAuthManager(config)
    
    try:
        # Authenticate
        auth_result = await auth_manager.authenticate()
        if not auth_result.success:
            print(f"❌ Authentication failed: {auth_result.error_message}")
            return
        
        print("✅ Authentication successful")
        
        # Create report generator
        report_generator = EnhancedReportGenerator(config, auth_manager)
        
        # Generate test reports
        print("🚀 Generating test reports...")
        
        generated_files = await report_generator.generate_weekly_report(
            team_name="Multi-Cluster Management Engineering",
            output_formats=[OutputFormat.MARKDOWN, OutputFormat.HTML, OutputFormat.PLAIN_TEXT]
        )
        
        print("\n📊 Generated Reports:")
        for format_name, file_path in generated_files.items():
            if file_path:
                print(f"  ✅ {format_name}: {file_path}")
            else:
                print(f"  ❌ {format_name}: Failed to generate")
        
        print("\n🎉 Phase 2 template migration test complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    finally:
        await auth_manager.close()


if __name__ == "__main__":
    from enhanced_config import get_config
    
    config = get_config()
    asyncio.run(test_report_generation(config))