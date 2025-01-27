# SparkPost IP Blacklist Monitor

A Python script that monitors your SparkPost sending IPs for any blacklist appearances using MXToolbox. The script runs daily checks and sends notifications to Slack and email.

## Features

- Fetches sending IPs from SparkPost API
- Checks each IP against 63+ known blacklists using MXToolbox
- Sends notifications to Slack when blacklists are found
- Sends backup email notifications via SparkPost SMTP
- Configurable notification settings for clean IPs
- Comprehensive logging of all checks
- Automated daily monitoring
- Groups IPs by pool for better organization
- Historical tracking of blacklist appearances

## Prerequisites

- Python 3.11+
- SparkPost API key with IP Pools Read permissions
- Slack Bot Token with chat:write permissions
- Slack Channel ID for notifications

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/sparkpost-blacklist-monitor.git
   cd sparkpost-blacklist-monitor
   ```

2. Install dependencies:
   ```bash
   pip install beautifulsoup4 email-validator pyyaml requests schedule slack-sdk
   ```

## Environment Variables

Set the following environment variables:

- `SPARKPOST_API_KEY`: Your SparkPost API key
- `SLACK_BOT_TOKEN`: Slack Bot User OAuth Token (starts with xoxb-)
- `SLACK_CHANNEL_ID`: ID of the Slack channel for notifications

You can set these using a .env file or export them directly:

```bash
export SPARKPOST_API_KEY='your-sparkpost-api-key'
export SLACK_BOT_TOKEN='xoxb-your-slack-bot-token'
export SLACK_CHANNEL_ID='your-slack-channel-id'
```

## Configuration

Configure the script through `config.yaml`:

```yaml
sparkpost:
  base_url: "https://api.sparkpost.com/api/v1"

mxtoolbox:
  base_url: "https://mxtoolbox.com/api/v1"
  check_interval: 5  # seconds between checks to respect rate limits

notifications:
  slack_notify_on_clean: false  # Set to true to notify even when no blacklists are found
  email:
    enabled: true
    notify_on_clean: false  # Set to true to notify even when no blacklists are found
    recipients: []  # List of email addresses to notify
    from_name: "SparkPost IP Monitor"
    subject_prefix: "[IP Monitor]"

logging:
  level: INFO
  file: "blacklist_monitor.log"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## Usage

1. Start monitoring:
   ```bash
   python main.py
   ```

The script will:
1. Run an initial check immediately
2. Schedule subsequent checks to run daily at midnight
3. Continue running in the background, performing checks at the scheduled time

## Logs

All monitoring activity is logged to `blacklist_monitor.log`. The log includes:
- IP check results
- API interaction statuses
- Notification delivery status
- Error messages and stack traces

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

## Contributing

Feel free to open issues or submit pull requests with improvements.

## License

This project is open source and available under the MIT License.