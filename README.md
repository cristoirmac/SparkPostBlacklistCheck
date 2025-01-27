# SparkPost IP Blacklist Monitor

A Python script that monitors your SparkPost sending IPs for any blacklist appearances using MXToolbox. The script runs daily checks and sends notifications to a specified Slack channel.

## Features

- Fetches sending IPs from SparkPost API
- Checks each IP against 63+ known blacklists using MXToolbox
- Sends notifications to Slack when blacklists are found
- Configurable notification settings for clean IPs
- Comprehensive logging of all checks
- Automated daily monitoring

## Prerequisites

- Python 3.11+
- SparkPost API key with IP Pools Read permissions
- Slack Bot Token with chat:write permissions
- Slack Channel ID for notifications

## Environment Variables

The following environment variables must be set:

- `SPARKPOST_API_KEY`: Your SparkPost API key
- `SLACK_BOT_TOKEN`: Slack Bot User OAuth Token (starts with xoxb-)
- `SLACK_CHANNEL_ID`: ID of the Slack channel for notifications

## Configuration

The script's behavior can be configured through `config.yaml`:

```yaml
sparkpost:
  base_url: "https://api.sparkpost.com/api/v1"

mxtoolbox:
  base_url: "https://mxtoolbox.com/api/v1"
  check_interval: 5  # seconds between checks to respect rate limits

notifications:
  slack_notify_on_clean: false  # Set to true to notify even when no blacklists are found

logging:
  level: INFO
  file: "blacklist_monitor.log"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Script

To start monitoring:

```bash
python main.py
```

The script will:
1. Run an initial check immediately
2. Schedule subsequent checks to run daily at midnight
3. Continue running in the background, performing checks at the scheduled time

## Logs

All monitoring activity is logged to `blacklist_monitor.log`, regardless of whether Slack notifications are sent. The log includes:
- IP check results
- API interaction statuses
- Error messages and stack traces when problems occur

## Sample Output

When an IP is clean:
```
Checking 156.70.5.163 against 63 known blacklists... Listed 0 times with 1 timeouts
```

When blacklists are found:
```
Checking 156.70.5.163 against 63 known blacklists... Listed 2 times with 1 timeouts

Blacklisted on:
- Spamhaus: https://mxtoolbox.com/blacklists.aspx#Spamhaus
- Barracuda: https://mxtoolbox.com/blacklists.aspx#Barracuda
```
