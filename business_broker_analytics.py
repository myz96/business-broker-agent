#!/usr/bin/env python3
"""
Business Broker Agent Analytics
===============================

Analyzes task performance and metrics for Louise and Roger agents.
Provides insights into success rates, error analysis, and action counts.
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import requests
from relevanceai import RelevanceAI


# Configuration
@dataclass
class Config:
    """Configuration for the analytics system."""
    region: str
    project: str
    api_key: str
    roger_agent_id: str
    louise_agent_id: str
    default_hours: int = 24
    max_results: int = 200
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables."""
        return cls(
            region=os.getenv('RELEVANCE_REGION', '1e3042'),
            project=os.getenv('RELEVANCE_PROJECT', 'e1f79d13-29c3-4c8e-95a4-314c09c3f906'),
            api_key=os.getenv('RELEVANCE_API_KEY', 'sk-MjMxYjRiZmUtZTZlMC00OGZkLTgwMWYtZjM5ODIzMzRkOTBi'),
            roger_agent_id=os.getenv('ROGER_AGENT_ID', '8e447f3c-9388-483f-b3ad-e35f4de1091b'),
            louise_agent_id=os.getenv('LOUISE_AGENT_ID', 'c647e657-233e-4c86-85a4-edf62fc93d36')
        )


class TaskState(Enum):
    """Task state enumeration."""
    IDLE = "State.idle"
    RUNNING = "State.running"
    COMPLETED = "State.completed"
    ERRORED = "State.errored_pending_approval"


@dataclass
class TaskMetrics:
    """Metrics for task analysis."""
    total_tasks: int = 0
    successful_tasks: int = 0
    errored_tasks: int = 0
    unknown_status_tasks: int = 0
    idle_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    state_breakdown: Dict[str, int] = None
    error_details: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.state_breakdown is None:
            self.state_breakdown = {}
        if self.error_details is None:
            self.error_details = []
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.successful_tasks / self.total_tasks) * 100
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.errored_tasks / self.total_tasks) * 100


@dataclass
class ActionMetrics:
    """Metrics for action analysis."""
    total_conversations_checked: int = 0
    conversations_with_target_action: int = 0
    target_action_count: int = 0
    target_title: str = ""
    conversation_details: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.conversation_details is None:
            self.conversation_details = []


class DateTimeHelper:
    """Helper class for datetime operations."""
    
    @staticmethod
    def parse_iso_date(date_str: str) -> datetime:
        """Parse ISO date string to datetime object."""
        if not date_str:
            raise ValueError("Date string cannot be empty")
        
        # Handle 'Z' suffix for UTC
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        
        return datetime.fromisoformat(date_str)
    
    @staticmethod
    def get_cutoff_time(hours: int) -> datetime:
        """Get cutoff time for filtering tasks."""
        return datetime.now(timezone.utc) - timedelta(hours=hours)
    
    @staticmethod
    def is_within_timeframe(date_str: str, cutoff_time: datetime) -> bool:
        """Check if date is within specified timeframe."""
        try:
            date_obj = DateTimeHelper.parse_iso_date(date_str)
            return date_obj >= cutoff_time
        except (ValueError, TypeError):
            return False


class TaskFilter:
    """Handles task filtering operations."""
    
    @staticmethod
    def filter_by_timeframe(tasks: List[Any], hours: int = 24) -> List[Any]:
        """Filter tasks by time window based on their insert_date."""
        cutoff_time = DateTimeHelper.get_cutoff_time(hours)
        recent_tasks = []
        
        for task in tasks:
            try:
                if (task.metadata and 
                    task.metadata.insert_date and 
                    DateTimeHelper.is_within_timeframe(task.metadata.insert_date, cutoff_time)):
                    recent_tasks.append(task)
            except Exception as e:
                logging.warning(f"Error filtering task: {e}")
                continue
        
        return recent_tasks


class TaskAnalyzer:
    """Analyzes task metrics and performance."""
    
    @staticmethod
    def analyze_task_success_and_errors(tasks: List[Any]) -> TaskMetrics:
        """Analyze tasks to determine success vs error rates."""
        metrics = TaskMetrics()
        metrics.total_tasks = len(tasks)
        
        for task in tasks:
            try:
                if not (task.metadata and task.metadata.conversation):
                    metrics.unknown_status_tasks += 1
                    continue
                
                conv = task.metadata.conversation
                state = str(conv.state) if conv.state else 'None'
                
                # Update state breakdown
                metrics.state_breakdown[state] = metrics.state_breakdown.get(state, 0) + 1
                
                # Count by state type
                if state == TaskState.IDLE.value:
                    metrics.idle_tasks += 1
                elif state == TaskState.RUNNING.value:
                    metrics.running_tasks += 1
                elif state == TaskState.COMPLETED.value:
                    metrics.completed_tasks += 1
                
                # Analyze error status
                if conv.has_errored is True or 'errored' in state.lower():
                    metrics.errored_tasks += 1
                    metrics.error_details.append({
                        'task_id': task.knowledge_set,
                        'title': conv.title if conv.title else 'No title',
                        'state': state,
                        'insert_date': task.metadata.insert_date
                    })
                elif (conv.has_errored is False or 
                      state in [TaskState.IDLE.value, TaskState.RUNNING.value, 
                               'State.starting_up', TaskState.COMPLETED.value]):
                    metrics.successful_tasks += 1
                else:
                    metrics.unknown_status_tasks += 1
                    
            except Exception as e:
                logging.warning(f"Error analyzing task: {e}")
                metrics.unknown_status_tasks += 1
        
        return metrics


class ConversationDataReader:
    """Handles reading conversation data from Relevance API."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def read_dataset_from_relevance(self, knowledge_set: str) -> List[Dict[str, Any]]:
        """Read conversation data from Relevance API."""
        url = f"https://api-{self.config.region}.stack.tryrelevance.com/latest/knowledge/list"
        headers = {"Authorization": f"{self.config.project}:{self.config.api_key}"}
        payload = {"knowledge_set": knowledge_set, "page_size": 999999999999}
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            results = response.json()
            return [result['data'] for result in results.get('results', [])]
        except requests.RequestException as e:
            logging.error(f"Error reading dataset {knowledge_set}: {e}")
            return []


class ActionAnalyzer:
    """Analyzes actions within conversations."""
    
    def __init__(self, data_reader: ConversationDataReader):
        self.data_reader = data_reader
    
    def count_actions_by_chain_title(self, tasks: List[Any], target_title: str) -> ActionMetrics:
        """Count conversations that contain actions with a specific chain config title."""
        metrics = ActionMetrics()
        metrics.target_title = target_title
        
        for task in tasks:
            try:
                conversation_data = self.data_reader.read_dataset_from_relevance(task.knowledge_set)
                metrics.total_conversations_checked += 1
                
                found_target_action = False
                action_count_in_conversation = 0
                
                for message_data in conversation_data:
                    message = message_data.get('message', {})
                    
                    if 'chain_config' in message:
                        chain_title = message['chain_config'].get('title', '')
                        if chain_title == target_title:
                            found_target_action = True
                            action_count_in_conversation += 1
                            metrics.target_action_count += 1
                
                if found_target_action:
                    metrics.conversations_with_target_action += 1
                    
                    conv_title = "No title"
                    if (task.metadata and task.metadata.conversation and 
                        task.metadata.conversation.title):
                        conv_title = task.metadata.conversation.title
                    
                    metrics.conversation_details.append({
                        'task_id': task.knowledge_set,
                        'conversation_title': conv_title,
                        'action_count': action_count_in_conversation,
                        'insert_date': task.metadata.insert_date if task.metadata else 'Unknown'
                    })
                    
            except Exception as e:
                logging.error(f"Error processing task {task.knowledge_set}: {e}")
                continue
        
        return metrics


class ReportGenerator:
    """Generates formatted reports from metrics."""
    
    @staticmethod
    def print_task_analysis_report(agent_name: str, metrics: TaskMetrics, hours: int = 24):
        """Print formatted task analysis report."""
        print("=" * 60)
        print(f"{agent_name.upper()} TASK SUCCESS AND ERROR ANALYSIS - LAST {hours} HOURS")
        print("=" * 60)
        
        print(f"Total tasks in last {hours} hours: {metrics.total_tasks}")
        print(f"Successful tasks: {metrics.successful_tasks}")
        print(f"Errored tasks: {metrics.errored_tasks}")
        print(f"Unknown status tasks: {metrics.unknown_status_tasks}")
        
        if metrics.total_tasks > 0:
            print(f"\nSuccess rate: {metrics.success_rate:.1f}%")
            print(f"Error rate: {metrics.error_rate:.1f}%")
        
        print(f"\nTask states breakdown:")
        for state, count in metrics.state_breakdown.items():
            percentage = (count / metrics.total_tasks) * 100 if metrics.total_tasks > 0 else 0
            print(f"  {state}: {count} ({percentage:.1f}%)")
        
        if metrics.errored_tasks > 0:
            print(f"\nError details:")
            for i, error in enumerate(metrics.error_details[:5], 1):
                print(f"  {i}. {error['title']}")
                print(f"     State: {error['state']}")
                print(f"     Date: {error['insert_date']}")
                print()
            
            if len(metrics.error_details) > 5:
                print(f"     ... and {len(metrics.error_details) - 5} more errors")
    
    @staticmethod
    def print_summary_metrics(louise_metrics: TaskMetrics, roger_metrics: TaskMetrics, 
                            email_metrics: ActionMetrics, call_metrics: ActionMetrics):
        """Print summary metrics report."""
        print("\n" + "=" * 60)
        print("24-HOUR SUMMARY METRICS")
        print("=" * 60)
        
        print(f"📊 SUBURBS PROCESSED: {louise_metrics.successful_tasks}")
        print(f"❌ SUBURBS WITH ERRORS: {louise_metrics.errored_tasks}")
        print(f"✅ BUSINESSES SUCCESSFULLY PROCESSED: {roger_metrics.successful_tasks}")
        print(f"❌ BUSINESSES WITH ERRORS: {roger_metrics.errored_tasks}")
        print(f"📧 OUTLOOK EMAILS SENT: {email_metrics.target_action_count}")
        print(f"📞 CALLS MADE: {call_metrics.target_action_count}")
        
        if louise_metrics.total_tasks > 0:
            print(f"📈 SUBURB SUCCESS RATE: {louise_metrics.success_rate:.1f}%")
        
        if roger_metrics.total_tasks > 0:
            print(f"📈 BUSINESS SUCCESS RATE: {roger_metrics.success_rate:.1f}%")
        
        print(f"\n⏳ LOUISE TASKS CURRENTLY IDLE: {louise_metrics.idle_tasks}")
        print(f"🏃 LOUISE TASKS CURRENTLY RUNNING: {louise_metrics.running_tasks}")
        print(f"⏳ ROGER TASKS CURRENTLY IDLE: {roger_metrics.idle_tasks}")
        print(f"🏃 ROGER TASKS CURRENTLY RUNNING: {roger_metrics.running_tasks}")
        
        print(f"\n📈 EMAIL EFFICIENCY:")
        if email_metrics.conversations_with_target_action > 0:
            avg_emails = email_metrics.target_action_count / email_metrics.conversations_with_target_action
            print(f"   Conversations with emails: {email_metrics.conversations_with_target_action}")
            print(f"   Average emails per conversation: {avg_emails:.1f}")
        else:
            print(f"   No email actions found in the last 24 hours")


class BusinessBrokerAnalytics:
    """Main analytics class that orchestrates the analysis."""
    
    def __init__(self, config: Config):
        self.config = config
        self.rai = RelevanceAI(
            api_key=config.api_key,
            region=config.region,
            project=config.project
        )
        self.data_reader = ConversationDataReader(config)
        self.action_analyzer = ActionAnalyzer(self.data_reader)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def run_analysis(self, hours: int = 24) -> Tuple[TaskMetrics, TaskMetrics, ActionMetrics, ActionMetrics]:
        """Run complete analysis and return metrics."""
        try:
            # Retrieve agents and tasks
            logging.info("Retrieving agents and tasks...")
            louise = self.rai.agents.retrieve_agent(self.config.louise_agent_id)
            roger = self.rai.agents.retrieve_agent(self.config.roger_agent_id)
            
            louise_tasks = louise.list_tasks(max_results=self.config.max_results)
            roger_tasks = roger.list_tasks(max_results=self.config.max_results)
            
            logging.info(f"Retrieved {len(louise_tasks)} Louise tasks and {len(roger_tasks)} Roger tasks")
            
            # Filter tasks by timeframe
            louise_tasks_recent = TaskFilter.filter_by_timeframe(louise_tasks, hours)
            roger_tasks_recent = TaskFilter.filter_by_timeframe(roger_tasks, hours)
            
            logging.info(f"Filtered to {len(louise_tasks_recent)} Louise and {len(roger_tasks_recent)} Roger recent tasks")
            
            # Analyze task metrics
            louise_metrics = TaskAnalyzer.analyze_task_success_and_errors(louise_tasks_recent)
            roger_metrics = TaskAnalyzer.analyze_task_success_and_errors(roger_tasks_recent)
            
            # Analyze actions
            email_metrics = self.action_analyzer.count_actions_by_chain_title(
                roger_tasks_recent, "Send Outlook email"
            )
            call_metrics = self.action_analyzer.count_actions_by_chain_title(
                roger_tasks_recent, "Call Business via Bland AI"
            )
            
            # Generate reports
            ReportGenerator.print_task_analysis_report("Louise", louise_metrics, hours)
            ReportGenerator.print_task_analysis_report("Roger", roger_metrics, hours)
            ReportGenerator.print_summary_metrics(louise_metrics, roger_metrics, email_metrics, call_metrics)
            
            return louise_metrics, roger_metrics, email_metrics, call_metrics
            
        except Exception as e:
            logging.error(f"Error during analysis: {e}")
            raise


def main():
    """Main entry point."""
    try:
        config = Config.from_env()
        analytics = BusinessBrokerAnalytics(config)
        analytics.run_analysis()
        
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 