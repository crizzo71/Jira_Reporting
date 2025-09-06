"""
Advanced Dashboard Generator for Cross-Platform Analytics

Creates comprehensive dashboards displaying:
- Executive summary with key metrics
- Delivery pipeline visualization
- Developer productivity analytics
- Team performance trends
- Quality and efficiency insights
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import statistics

from cross_platform_analytics import TeamMetrics, DeliveryPipeline, DeveloperMetrics
from enhanced_config import OutputFormat


class DashboardGenerator:
    """Generate advanced analytics dashboards."""
    
    def __init__(self, output_dir: str = "dashboards"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.output_dir / "executive").mkdir(exist_ok=True)
        (self.output_dir / "detailed").mkdir(exist_ok=True)
        (self.output_dir / "developer").mkdir(exist_ok=True)
    
    async def generate_executive_dashboard(
        self,
        team_metrics: TeamMetrics,
        insights: Dict[str, Any]
    ) -> str:
        """Generate executive-level dashboard."""
        
        template = f"""# Executive Dashboard: {team_metrics.team_name}
**Reporting Period:** {team_metrics.period_start.strftime('%Y-%m-%d')} to {team_metrics.period_end.strftime('%Y-%m-%d')}

## 📊 Key Performance Indicators

### Delivery Metrics
- **Issues Completed:** {team_metrics.issues_completed}
- **Story Points Delivered:** {team_metrics.story_points_completed}
- **Pull Requests Merged:** {team_metrics.pull_requests_merged}
- **Completion Rate:** {insights['summary']['completion_rate']:.1%}

### Efficiency Metrics
- **Average Cycle Time:** {team_metrics.average_cycle_time:.1f} days
- **Deployment Frequency:** {team_metrics.deployment_frequency:.2f} per day
- **Cross-Platform Correlation:** {team_metrics.cross_platform_correlation:.1%}

### Quality Metrics
- **First-Time Quality:** {team_metrics.first_time_quality:.1%}
- **Defect Rate:** {team_metrics.defect_rate:.1%}
- **Code Review Coverage:** {team_metrics.code_review_coverage:.1%}

## 🎯 Team Performance Summary

### ✅ Strengths
{chr(10).join(f"- {strength}" for strength in insights['strengths'])}

### 🔧 Areas for Improvement  
{chr(10).join(f"- {area}" for area in insights['improvement_areas'])}

### 💡 Recommendations
{chr(10).join(f"- {rec}" for rec in insights['recommendations'])}

## 👥 Team Composition
**Active Developers:** {len(team_metrics.developers)}

### Top Performers
{self._format_top_performers(insights.get('trends', {}).get('top_performers', []))}

## 📈 Delivery Pipeline Analysis

### Pipeline Stages Distribution
{self._format_pipeline_stages(team_metrics.pipelines)}

### Cycle Time Breakdown
{self._format_cycle_time_breakdown(team_metrics.pipelines)}

---
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by Jira Reports Simplified*
"""
        
        output_path = self.output_dir / "executive" / f"executive-dashboard-{team_metrics.team_name.lower().replace(' ', '-')}-{datetime.now().strftime('%Y-%m-%d')}.md"
        
        with open(output_path, 'w') as f:
            f.write(template)
        
        return str(output_path)
    
    async def generate_detailed_analytics(
        self,
        team_metrics: TeamMetrics,
        insights: Dict[str, Any]
    ) -> str:
        """Generate detailed analytics dashboard."""
        
        template = f"""# Detailed Analytics: {team_metrics.team_name}
**Period:** {team_metrics.period_start.strftime('%Y-%m-%d')} to {team_metrics.period_end.strftime('%Y-%m-%d')}

## 🔄 Delivery Pipeline Analysis

### Pipeline Performance
- **Total Pipelines:** {len(team_metrics.pipelines)}
- **Completed Pipelines:** {len([p for p in team_metrics.pipelines if p.completion_date])}
- **In Progress:** {len([p for p in team_metrics.pipelines if not p.completion_date])}

### Stage Distribution
{self._format_detailed_pipeline_analysis(team_metrics.pipelines)}

### Timing Analysis
{self._format_timing_analysis(team_metrics.pipelines)}

## 👨‍💻 Developer Productivity Analysis

### Individual Performance
{self._format_developer_details(team_metrics.developers)}

### Collaboration Metrics
{self._format_collaboration_metrics(team_metrics.developers)}

## 🔍 Quality Analysis

### Defect Analysis
{self._format_quality_analysis(team_metrics.pipelines)}

### Code Review Analysis
{self._format_code_review_analysis(team_metrics.pipelines)}

## 🔗 Cross-Platform Correlation

### Jira-GitHub Integration
{self._format_correlation_analysis(team_metrics)}

### Issue Tracking Effectiveness
{self._format_tracking_analysis(team_metrics.pipelines)}

## 📊 Trend Analysis

### Weekly Patterns
{self._format_weekly_patterns(team_metrics.pipelines)}

### Velocity Trends
{self._format_velocity_trends(team_metrics)}

---
*Detailed analysis generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        output_path = self.output_dir / "detailed" / f"detailed-analytics-{team_metrics.team_name.lower().replace(' ', '-')}-{datetime.now().strftime('%Y-%m-%d')}.md"
        
        with open(output_path, 'w') as f:
            f.write(template)
        
        return str(output_path)
    
    async def generate_developer_dashboard(
        self,
        developer_metrics: List[DeveloperMetrics],
        team_name: str
    ) -> str:
        """Generate individual developer performance dashboard."""
        
        template = f"""# Developer Performance Dashboard: {team_name}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 👨‍💻 Individual Developer Analysis

{self._format_individual_developer_analysis(developer_metrics)}

## 📊 Productivity Comparison

### Delivery Metrics Comparison
{self._format_productivity_comparison(developer_metrics)}

### Quality Metrics Comparison  
{self._format_quality_comparison(developer_metrics)}

### Collaboration Metrics
{self._format_collaboration_comparison(developer_metrics)}

## 🎯 Performance Insights

### Top Contributors
{self._format_top_contributors(developer_metrics)}

### Development Patterns
{self._format_development_patterns(developer_metrics)}

### Improvement Opportunities
{self._format_improvement_opportunities(developer_metrics)}

---
*Developer dashboard generated by Advanced Analytics Engine*
"""
        
        output_path = self.output_dir / "developer" / f"developer-dashboard-{team_name.lower().replace(' ', '-')}-{datetime.now().strftime('%Y-%m-%d')}.md"
        
        with open(output_path, 'w') as f:
            f.write(template)
        
        return str(output_path)
    
    async def generate_html_dashboard(
        self,
        team_metrics: TeamMetrics,
        insights: Dict[str, Any]
    ) -> str:
        """Generate interactive HTML dashboard."""
        
        html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Analytics Dashboard - {team_metrics.team_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .dashboard {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 30px;
        }}
        .metric-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #007bff;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
        }}
        .metric-label {{
            color: #6c757d;
            margin-top: 5px;
        }}
        .chart-container {{
            padding: 30px;
            border-top: 1px solid #e9ecef;
        }}
        .progress-bar {{
            background: #e9ecef;
            border-radius: 10px;
            height: 20px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .progress-fill {{
            background: linear-gradient(90deg, #28a745, #20c997);
            height: 100%;
            transition: width 0.3s ease;
        }}
        .insights {{
            background: #f8f9fa;
            padding: 30px;
            border-top: 1px solid #e9ecef;
        }}
        .insight-section {{
            margin-bottom: 20px;
        }}
        .insight-section h3 {{
            color: #495057;
            margin-bottom: 10px;
        }}
        .insight-item {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            margin: 10px 0;
            border-left: 3px solid #007bff;
        }}
        .developer-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .developer-card {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>📊 Analytics Dashboard</h1>
            <h2>{team_metrics.team_name}</h2>
            <p>{team_metrics.period_start.strftime('%B %d, %Y')} - {team_metrics.period_end.strftime('%B %d, %Y')}</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{team_metrics.issues_completed}</div>
                <div class="metric-label">Issues Completed</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{team_metrics.story_points_completed}</div>
                <div class="metric-label">Story Points Delivered</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{team_metrics.average_cycle_time:.1f}</div>
                <div class="metric-label">Average Cycle Time (days)</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{team_metrics.first_time_quality:.1%}</div>
                <div class="metric-label">First-Time Quality</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{team_metrics.cross_platform_correlation:.1%}</div>
                <div class="metric-label">Cross-Platform Correlation</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{len(team_metrics.developers)}</div>
                <div class="metric-label">Active Developers</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h3>🎯 Performance Overview</h3>
            
            <div style="margin: 20px 0;">
                <strong>Completion Rate</strong>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {insights['summary']['completion_rate']*100:.0f}%"></div>
                </div>
                <small>{insights['summary']['completion_rate']:.1%}</small>
            </div>
            
            <div style="margin: 20px 0;">
                <strong>Code Review Coverage</strong>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {team_metrics.code_review_coverage*100:.0f}%"></div>
                </div>
                <small>{team_metrics.code_review_coverage:.1%}</small>
            </div>
            
            <div style="margin: 20px 0;">
                <strong>Quality Score</strong>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {team_metrics.first_time_quality*100:.0f}%"></div>
                </div>
                <small>{team_metrics.first_time_quality:.1%}</small>
            </div>
        </div>
        
        <div class="insights">
            <h3>💡 Key Insights</h3>
            
            <div class="insight-section">
                <h4>✅ Strengths</h4>
                {chr(10).join(f'<div class="insight-item">{strength}</div>' for strength in insights['strengths'])}
            </div>
            
            <div class="insight-section">
                <h4>🔧 Improvement Areas</h4>
                {chr(10).join(f'<div class="insight-item">{area}</div>' for area in insights['improvement_areas'])}
            </div>
            
            <div class="insight-section">
                <h4>📈 Recommendations</h4>
                {chr(10).join(f'<div class="insight-item">{rec}</div>' for rec in insights['recommendations'])}
            </div>
        </div>
        
        <div class="chart-container">
            <h3>👥 Developer Performance</h3>
            <div class="developer-grid">
                {self._format_developer_cards_html(team_metrics.developers)}
            </div>
        </div>
    </div>
    
    <script>
        // Add interactivity
        document.addEventListener('DOMContentLoaded', function() {{
            // Animate progress bars
            const progressBars = document.querySelectorAll('.progress-fill');
            progressBars.forEach(bar => {{
                const width = bar.style.width;
                bar.style.width = '0%';
                setTimeout(() => {{
                    bar.style.width = width;
                }}, 500);
            }});
        }});
    </script>
</body>
</html>"""
        
        output_path = self.output_dir / f"dashboard-{team_metrics.team_name.lower().replace(' ', '-')}-{datetime.now().strftime('%Y-%m-%d')}.html"
        
        with open(output_path, 'w') as f:
            f.write(html_template)
        
        return str(output_path)
    
    def _format_top_performers(self, top_performers: List[Dict]) -> str:
        """Format top performers section."""
        if not top_performers:
            return "_No performance data available._"
        
        lines = []
        for i, performer in enumerate(top_performers, 1):
            lines.append(f"{i}. **{performer['developer']}** - Quality Score: {performer['quality_score']:.2f}, Deliveries: {performer['deliveries']}")
        
        return '\n'.join(lines)
    
    def _format_pipeline_stages(self, pipelines: List[DeliveryPipeline]) -> str:
        """Format pipeline stages distribution."""
        from collections import Counter
        
        stages = Counter(pipeline.current_stage.value for pipeline in pipelines)
        total = len(pipelines)
        
        lines = []
        for stage, count in stages.items():
            percentage = (count / total * 100) if total > 0 else 0
            lines.append(f"- **{stage.title()}**: {count} ({percentage:.1f}%)")
        
        return '\n'.join(lines)
    
    def _format_cycle_time_breakdown(self, pipelines: List[DeliveryPipeline]) -> str:
        """Format cycle time breakdown."""
        completed_pipelines = [p for p in pipelines if p.total_cycle_time]
        
        if not completed_pipelines:
            return "_No completed pipelines for cycle time analysis._"
        
        cycle_times = [p.total_cycle_time for p in completed_pipelines]
        
        return f"""- **Average**: {statistics.mean(cycle_times):.1f} days
- **Median**: {statistics.median(cycle_times):.1f} days
- **Range**: {min(cycle_times):.1f} - {max(cycle_times):.1f} days
- **Standard Deviation**: {statistics.stdev(cycle_times):.1f} days"""
    
    def _format_detailed_pipeline_analysis(self, pipelines: List[DeliveryPipeline]) -> str:
        """Format detailed pipeline analysis."""
        total = len(pipelines)
        with_commits = len([p for p in pipelines if p.commits])
        with_prs = len([p for p in pipelines if p.pull_requests])
        
        return f"""**GitHub Integration:**
- Issues with commits: {with_commits}/{total} ({with_commits/total*100:.1f}%)
- Issues with pull requests: {with_prs}/{total} ({with_prs/total*100:.1f}%)

**Development Activity:**
- Total commits: {sum(len(p.commits) for p in pipelines)}
- Total pull requests: {sum(len(p.pull_requests) for p in pipelines)}
- Average commits per issue: {sum(len(p.commits) for p in pipelines)/total:.1f}"""
    
    def _format_timing_analysis(self, pipelines: List[DeliveryPipeline]) -> str:
        """Format timing analysis."""
        planning_times = [p.planning_time for p in pipelines if p.planning_time]
        dev_times = [p.development_time for p in pipelines if p.development_time]
        review_times = [p.review_time for p in pipelines if p.review_time]
        
        result = []
        
        if planning_times:
            result.append(f"**Planning Time**: {statistics.mean(planning_times):.1f} days average")
        
        if dev_times:
            result.append(f"**Development Time**: {statistics.mean(dev_times):.1f} days average")
        
        if review_times:
            result.append(f"**Review Time**: {statistics.mean(review_times):.1f} days average")
        
        return '\n'.join(result) if result else "_Insufficient timing data available._"
    
    def _format_developer_details(self, developers: List[DeveloperMetrics]) -> str:
        """Format developer details section."""
        lines = []
        
        for dev in sorted(developers, key=lambda d: d.delivery_pipelines_completed, reverse=True):
            quality_display = f"{dev.quality_score:.2f}" if dev.quality_score is not None else "N/A"
            lines.append(f"""**{dev.developer}**
- Deliveries: {dev.delivery_pipelines_completed}
- Commits: {dev.commits_count}
- Lines Changed: +{dev.lines_added}/-{dev.lines_deleted}
- Pull Requests: {dev.pull_requests_created} created, {dev.pull_requests_reviewed} reviewed
- Quality Score: {quality_display}
""")
        
        return '\n'.join(lines)
    
    def _format_collaboration_metrics(self, developers: List[DeveloperMetrics]) -> str:
        """Format collaboration metrics."""
        total_reviews = sum(dev.pull_requests_reviewed for dev in developers)
        total_prs = sum(dev.pull_requests_created for dev in developers)
        
        if total_prs == 0:
            return "_No pull request data available._"
        
        review_ratio = total_reviews / total_prs
        
        return f"""**Team Collaboration:**
- Review participation ratio: {review_ratio:.2f}
- Developers participating in reviews: {len([d for d in developers if d.pull_requests_reviewed > 0])}
- Cross-team reviews: {sum(dev.cross_team_collaboration for dev in developers)}"""
    
    def _format_quality_analysis(self, pipelines: List[DeliveryPipeline]) -> str:
        """Format quality analysis."""
        total_defects = sum(p.defects_found for p in pipelines)
        total_rework = sum(p.rework_commits for p in pipelines)
        total_pipelines = len(pipelines)
        
        if total_pipelines == 0:
            return "_No pipeline data available._"
        
        return f"""**Quality Metrics:**
- Total defects found: {total_defects}
- Defect rate: {total_defects/total_pipelines:.2f} per pipeline
- Rework commits: {total_rework}
- Rework rate: {total_rework/total_pipelines:.2f} per pipeline
- First-time quality: {1 - total_rework/max(1, sum(len(p.commits) for p in pipelines)):.1%}"""
    
    def _format_code_review_analysis(self, pipelines: List[DeliveryPipeline]) -> str:
        """Format code review analysis."""
        all_prs = [pr for pipeline in pipelines for pr in pipeline.pull_requests]
        
        if not all_prs:
            return "_No pull request data available._"
        
        with_reviews = len([pr for pr in all_prs if pr.reviewers])
        avg_review_comments = statistics.mean([pr.review_comments for pr in all_prs]) if all_prs else 0
        
        return f"""**Code Review Metrics:**
- Pull requests with reviews: {with_reviews}/{len(all_prs)} ({with_reviews/len(all_prs)*100:.1f}%)
- Average review comments: {avg_review_comments:.1f}
- Average reviewers per PR: {statistics.mean([len(pr.reviewers) for pr in all_prs]):.1f}"""
    
    def _format_correlation_analysis(self, team_metrics: TeamMetrics) -> str:
        """Format correlation analysis."""
        return f"""**Integration Health:**
- Cross-platform correlation: {team_metrics.cross_platform_correlation:.1%}
- Issues with GitHub activity: {len([p for p in team_metrics.pipelines if p.commits or p.pull_requests])}/{len(team_metrics.pipelines)}
- Deployment frequency: {team_metrics.deployment_frequency:.2f} per day"""
    
    def _format_tracking_analysis(self, pipelines: List[DeliveryPipeline]) -> str:
        """Format tracking analysis."""
        with_jira_keys = len([
            pr for pipeline in pipelines 
            for pr in pipeline.pull_requests 
            if pr.title and ('OCM-' in pr.title or 'OCM-' in (pr.body or ''))
        ])
        
        total_prs = sum(len(p.pull_requests) for p in pipelines)
        
        tracking_rate = with_jira_keys / max(1, total_prs)
        
        return f"""**Issue Tracking Effectiveness:**
- PRs with Jira references: {with_jira_keys}/{total_prs} ({tracking_rate:.1%})
- Recommendation: {'Good tracking' if tracking_rate > 0.8 else 'Improve Jira key usage in PR titles/descriptions'}"""
    
    def _format_weekly_patterns(self, pipelines: List[DeliveryPipeline]) -> str:
        """Format weekly patterns analysis."""
        # This would typically analyze commit/PR patterns by day of week
        return "_Weekly pattern analysis requires more detailed timestamp data._"
    
    def _format_velocity_trends(self, team_metrics: TeamMetrics) -> str:
        """Format velocity trends."""
        return f"""**Velocity Summary:**
- Story points per week: {team_metrics.story_points_completed / max(1, (team_metrics.period_end - team_metrics.period_start).days / 7):.1f}
- Issues per week: {team_metrics.issues_completed / max(1, (team_metrics.period_end - team_metrics.period_start).days / 7):.1f}
- Pull requests per week: {team_metrics.pull_requests_merged / max(1, (team_metrics.period_end - team_metrics.period_start).days / 7):.1f}"""
    
    def _format_individual_developer_analysis(self, developers: List[DeveloperMetrics]) -> str:
        """Format individual developer analysis."""
        lines = []
        
        for dev in developers:
            lines.append(f"""### {dev.developer}

**Delivery Metrics:**
- Issues completed: {dev.issues_completed}
- Pull requests created: {dev.pull_requests_created}
- Pull requests merged: {dev.pull_requests_merged}
- Cycle time: {dev.average_cycle_time:.1f} days (average)

**Code Metrics:**
- Commits: {dev.commits_count}
- Lines added: {dev.lines_added:,}
- Lines deleted: {dev.lines_deleted:,}
- Net contribution: {dev.lines_added - dev.lines_deleted:,} lines

**Collaboration:**
- Reviews performed: {dev.pull_requests_reviewed}
- Review participation: {dev.code_review_participation:.2f}
- Quality score: {f"{dev.quality_score:.2f}" if dev.quality_score is not None else "N/A"}

---""")
        
        return '\n'.join(lines)
    
    def _format_productivity_comparison(self, developers: List[DeveloperMetrics]) -> str:
        """Format productivity comparison."""
        if not developers:
            return "_No developer data available._"
        
        # Sort by deliveries
        top_by_deliveries = sorted(developers, key=lambda d: d.delivery_pipelines_completed, reverse=True)[:3]
        
        lines = ["**Top by Deliveries:**"]
        for i, dev in enumerate(top_by_deliveries, 1):
            lines.append(f"{i}. {dev.developer}: {dev.delivery_pipelines_completed} deliveries")
        
        return '\n'.join(lines)
    
    def _format_quality_comparison(self, developers: List[DeveloperMetrics]) -> str:
        """Format quality comparison."""
        developers_with_quality = [d for d in developers if d.quality_score is not None]
        
        if not developers_with_quality:
            return "_No quality data available._"
        
        top_quality = sorted(developers_with_quality, key=lambda d: d.quality_score, reverse=True)[:3]
        
        lines = ["**Top by Quality Score:**"]
        for i, dev in enumerate(top_quality, 1):
            lines.append(f"{i}. {dev.developer}: {dev.quality_score:.2f}")
        
        return '\n'.join(lines)
    
    def _format_collaboration_comparison(self, developers: List[DeveloperMetrics]) -> str:
        """Format collaboration comparison."""
        top_reviewers = sorted(developers, key=lambda d: d.pull_requests_reviewed, reverse=True)[:3]
        
        lines = ["**Top Code Reviewers:**"]
        for i, dev in enumerate(top_reviewers, 1):
            lines.append(f"{i}. {dev.developer}: {dev.pull_requests_reviewed} reviews")
        
        return '\n'.join(lines)
    
    def _format_top_contributors(self, developers: List[DeveloperMetrics]) -> str:
        """Format top contributors."""
        top_by_commits = sorted(developers, key=lambda d: d.commits_count, reverse=True)[:3]
        
        lines = ["**Most Active Contributors:**"]
        for i, dev in enumerate(top_by_commits, 1):
            lines.append(f"{i}. {dev.developer}: {dev.commits_count} commits")
        
        return '\n'.join(lines)
    
    def _format_development_patterns(self, developers: List[DeveloperMetrics]) -> str:
        """Format development patterns."""
        total_lines = sum(dev.lines_added + dev.lines_deleted for dev in developers)
        avg_lines_per_dev = total_lines / len(developers) if developers else 0
        
        return f"""**Development Patterns:**
- Average code change per developer: {avg_lines_per_dev:.0f} lines
- Most productive: {max(developers, key=lambda d: d.lines_added + d.lines_deleted).developer if developers else 'N/A'}
- Best reviewer: {max(developers, key=lambda d: d.pull_requests_reviewed).developer if developers else 'N/A'}"""
    
    def _format_improvement_opportunities(self, developers: List[DeveloperMetrics]) -> str:
        """Format improvement opportunities."""
        low_review_participation = [d for d in developers if d.code_review_participation < 0.5]
        
        opportunities = []
        
        if low_review_participation:
            opportunities.append(f"Increase review participation for: {', '.join([d.developer for d in low_review_participation])}")
        
        low_quality = [d for d in developers if d.quality_score and d.quality_score < 0.7]
        if low_quality:
            opportunities.append(f"Focus on quality improvement for: {', '.join([d.developer for d in low_quality])}")
        
        return '\n'.join(f"- {opp}" for opp in opportunities) if opportunities else "_No specific improvement opportunities identified._"
    
    def _format_developer_cards_html(self, developers: List[DeveloperMetrics]) -> str:
        """Format developer cards for HTML dashboard."""
        cards = []
        
        for dev in developers:
            cards.append(f"""
                <div class="developer-card">
                    <h4>👨‍💻 {dev.developer}</h4>
                    <p><strong>Deliveries:</strong> {dev.delivery_pipelines_completed}</p>
                    <p><strong>Commits:</strong> {dev.commits_count}</p>
                    <p><strong>Reviews:</strong> {dev.pull_requests_reviewed}</p>
                    <p><strong>Quality:</strong> {f"{dev.quality_score:.2f}" if dev.quality_score is not None else "N/A"}</p>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {dev.quality_score*100 if dev.quality_score else 0:.0f}%"></div>
                    </div>
                </div>
            """)
        
        return ''.join(cards)