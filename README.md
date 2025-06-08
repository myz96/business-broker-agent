# Business Broker Analytics

Automated monitoring system for Louise and Roger agents via RelevanceAI API. Generates daily reports and automatically updates Apple Notes.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure credentials:**
   ```bash
   cp config.env.example config.env
   # Edit config.env with your RelevanceAI credentials
   ```

3. **Run analytics manually:**
   ```bash
   python analytics_for_notes.py 24
   ```

4. **Set up automated daily reports:**
   ```bash
   crontab -e
   # Add: 0 9 * * * /path/to/business-broker-agent/run_analytics_cron.sh
   ```

## Architecture

### Core Files

- **`business_broker_analytics.py`** - Main analytics engine with modular classes
- **`analytics_for_notes.py`** - Notes-optimized reporting with clean text output
- **`update_notes.py`** - Apple Notes integration with proper line break handling
- **`run_analytics_cron.sh`** - Cron job orchestration and error handling
- **`config.env`** - Secure credential storage

### Features

- **Real-time Monitoring**: Track Louise (suburb processing) and Roger (business outreach) performance
- **Success Rate Analysis**: Monitor task completion rates and error patterns
- **Action Tracking**: Count emails sent and calls made
- **Apple Notes Integration**: Automated daily reports with proper formatting
- **Error Handling**: Comprehensive logging and graceful failure recovery

## Configuration

Required environment variables in `config.env`:

```env
RELEVANCE_REGION=your_region
RELEVANCE_PROJECT=your_project_id
RELEVANCE_API_KEY=your_api_key
LOUISE_AGENT_ID=louise_agent_id
ROGER_AGENT_ID=roger_agent_id
```

## Reports

Daily reports are automatically appended to the "📈 Business Broker Monitoring" note in the "building" folder of Apple Notes, showing:

- Processing volumes (suburbs/businesses)
- Success rates and error analysis
- Communication metrics (emails/calls)
- Current agent status
- Detailed task breakdowns

## Usage Examples

```bash
# Generate 24-hour report
python analytics_for_notes.py 24

# Generate 12-hour report  
python analytics_for_notes.py 12

# Test cron job without updating Notes
./run_analytics_cron.sh 24 dryrun

# Manual run with Notes update
./run_analytics_cron.sh 24
```

## Logging

- **`logs/analytics_cron.log`** - Main execution logs
- **`logs/notes_update.log`** - Apple Notes update logs

## System Requirements

- Python 3.8+
- macOS (for Apple Notes integration)
- RelevanceAI API access 