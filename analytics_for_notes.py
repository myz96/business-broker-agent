#!/usr/bin/env python3
"""
Business Broker Analytics - Apple Notes Version
===============================================

Clean, text-only output optimized for Apple Notes integration.
No ANSI colors, emojis, or complex formatting.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Import our main analytics classes
from business_broker_analytics import BusinessBrokerAnalytics, Config


class NotesReportGenerator:
    """Generates clean reports optimized for Apple Notes."""
    
    @staticmethod
    def format_timestamp() -> str:
        """Generate a clean timestamp header."""
        now = datetime.now(timezone.utc)
        date_str = now.strftime('%m/%d/%Y %H:%M UTC')
        return f"📊 Daily Report - {date_str}"
    
    @staticmethod
    def format_error_details(metrics) -> str:
        """Format just the error details if there are any."""
        if metrics.errored_tasks == 0:
            return ""
        
        lines = []
        lines.append(f"⚠️ Recent Errors:")
        
        for i, error in enumerate(metrics.error_details[:2], 1):  # Show only 2 most recent
            # Clean up the title and make it more readable
            title = error['title']
            if len(title) > 50:
                title = title[:47] + "..."
            lines.append(f"   {i}. {title}")
        
        if len(metrics.error_details) > 2:
            lines.append(f"   ... and {len(metrics.error_details) - 2} more")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_summary_metrics(louise_metrics, roger_metrics, email_metrics, call_metrics, hours: int = 24) -> str:
        """Format summary metrics for Notes."""
        lines = []
        
        # Compact key metrics
        lines.append(f"🏢 Suburbs: {louise_metrics.successful_tasks} processed ({louise_metrics.success_rate:.0f}% success)")
        lines.append(f"🏪 Businesses: {roger_metrics.successful_tasks} processed ({roger_metrics.success_rate:.0f}% success)")
        lines.append(f"📧 Communications: {email_metrics.target_action_count} emails, {call_metrics.target_action_count} calls")
        
        # Show errors if any
        total_errors = louise_metrics.errored_tasks + roger_metrics.errored_tasks
        if total_errors > 0:
            lines.append(f"⚠️ Errors: {total_errors} total ({louise_metrics.errored_tasks} Louise, {roger_metrics.errored_tasks} Roger)")
        
        # Current status - only show if anything is running
        running_total = louise_metrics.running_tasks + roger_metrics.running_tasks
        if running_total > 0:
            lines.append(f"🏃 Currently running: {running_total} tasks")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_complete_report(louise_metrics, roger_metrics, email_metrics, call_metrics, hours: int = 24) -> str:
        """Format complete report for Notes."""
        lines = []
        
        # Header with timestamp
        lines.append(NotesReportGenerator.format_timestamp())
        lines.append("")
        
        # Compact summary (most important info)
        lines.append(NotesReportGenerator.format_summary_metrics(
            louise_metrics, roger_metrics, email_metrics, call_metrics, hours
        ))
        
        # Only show errors if there are any
        error_details = NotesReportGenerator.format_error_details(roger_metrics)
        if error_details:
            lines.append("")
            lines.append(error_details)
        
        # Footer separator with spacing for next report
        lines.append("")
        lines.append("─" * 30)
        lines.append("")
        lines.append("")
        
        return "\n".join(lines)


class NotesAnalytics(BusinessBrokerAnalytics):
    """Analytics class optimized for Apple Notes output."""
    
    def __init__(self, config: Config):
        super().__init__(config)
        
        # Configure logging for minimal output
        logging.basicConfig(
            level=logging.WARNING,  # Only warnings and errors
            format='%(levelname)s: %(message)s'
        )
        
        # Suppress HTTP request logs from relevanceai
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    def run_analysis_for_notes(self, hours: int = 24) -> str:
        """Run analysis and return formatted string for Notes."""
        try:
            # Retrieve agents and tasks (suppress info logging)
            louise = self.rai.agents.retrieve_agent(self.config.louise_agent_id)
            roger = self.rai.agents.retrieve_agent(self.config.roger_agent_id)
            
            louise_tasks = louise.list_tasks(max_results=self.config.max_results)
            roger_tasks = roger.list_tasks(max_results=self.config.max_results)
            
            # Filter tasks by timeframe
            from business_broker_analytics import TaskFilter, TaskAnalyzer
            
            louise_tasks_recent = TaskFilter.filter_by_timeframe(louise_tasks, hours)
            roger_tasks_recent = TaskFilter.filter_by_timeframe(roger_tasks, hours)
            
            # Analyze task metrics
            louise_metrics = TaskAnalyzer.analyze_task_success_and_errors(louise_tasks_recent)
            roger_metrics = TaskAnalyzer.analyze_task_success_and_errors(roger_tasks_recent)
            
            # Analyze actions (only if there are recent tasks)
            email_metrics = None
            call_metrics = None
            
            if roger_tasks_recent:
                email_metrics = self.action_analyzer.count_actions_by_chain_title(
                    roger_tasks_recent, "Send Outlook email"
                )
                call_metrics = self.action_analyzer.count_actions_by_chain_title(
                    roger_tasks_recent, "Call Business via Bland AI"
                )
            else:
                # Create empty metrics if no tasks
                from business_broker_analytics import ActionMetrics
                email_metrics = ActionMetrics()
                email_metrics.target_title = "Send Outlook email"
                call_metrics = ActionMetrics()
                call_metrics.target_title = "Call Business via Bland AI"
            
            # Generate formatted report
            report = NotesReportGenerator.format_complete_report(
                louise_metrics, roger_metrics, email_metrics, call_metrics, hours
            )
            
            return report
            
        except Exception as e:
            error_msg = f"Error during analysis: {str(e)}\n"
            error_msg += f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n"
            error_msg += "=" * 40 + "\n"
            return error_msg


def load_env_file(filepath: str = "config.env"):
    """Load environment variables from a file."""
    env_path = Path(filepath)
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()


def main():
    """Main entry point for Notes analytics."""
    try:
        # Load configuration
        load_env_file()
        
        config = Config.from_env()
        analytics = NotesAnalytics(config)
        
        # Parse command line arguments for hours
        hours = 24
        if len(sys.argv) > 1:
            try:
                hours = int(sys.argv[1])
            except ValueError:
                print(f"Invalid hours value: {sys.argv[1]}, using default 24", file=sys.stderr)
        
        # Run analysis and output result
        report = analytics.run_analysis_for_notes(hours=hours)
        print(report)
        
    except Exception as e:
        error_report = f"ANALYTICS ERROR\n"
        error_report += f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n"
        error_report += f"Error: {str(e)}\n"
        error_report += "=" * 40 + "\n"
        print(error_report)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 