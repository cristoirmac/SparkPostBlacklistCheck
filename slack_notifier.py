import os
import yaml
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime
from typing import Dict, Any, List

class SlackNotifier:
    def __init__(self, logger):
        self.slack_token = os.environ.get('SLACK_BOT_TOKEN')
        self.channel_id = os.environ.get('SLACK_CHANNEL_ID')

        if not self.slack_token or not self.channel_id:
            raise ValueError("SLACK_BOT_TOKEN and SLACK_CHANNEL_ID environment variables must be set")

        self.client = WebClient(token=self.slack_token)
        self.logger = logger

        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        self.notify_on_clean = config['notifications']['slack_notify_on_clean']
        self.current_run_results = []

        # Verify Slack connection on initialization
        try:
            self.client.auth_test()
            self.logger.info("Successfully connected to Slack")
        except SlackApiError as e:
            self.logger.error(f"Failed to connect to Slack: {str(e)}")
            raise

    def format_message(self, check_result: Dict[str, Any]) -> str:
        """Format the blacklist check results into a Slack message"""
        ip = check_result['ip']
        listed_count = check_result['listed_count']
        timeout_count = check_result['timeout_count']

        message = f"Checking {ip} against 63 known blacklists... "
        message += f"Listed {listed_count} times with {timeout_count} timeouts"

        if listed_count > 0:
            message += "\n\nBlacklisted on:"
            for blacklist in check_result['blacklists']:
                message += f"\n- {blacklist['name']}: {blacklist['removal_url']}"

        message += f"\n\nFull report: {check_result['check_url']}"

        return message

    def send_notification(self, check_result: Dict[str, Any]) -> None:
        """Send notification to Slack if conditions are met"""
        # Store result for summary
        self.current_run_results.append(check_result)

        # Only send if blacklisted or notify_on_clean is true
        if check_result['listed_count'] > 0 or self.notify_on_clean:
            try:
                message = self.format_message(check_result)
                response = self.client.chat_postMessage(
                    channel=self.channel_id,
                    text=message,
                    unfurl_links=False  # Prevent link previews for cleaner messages
                )
                self.logger.info(f"Sent Slack notification for IP {check_result['ip']}")

            except SlackApiError as e:
                self.logger.error(f"Failed to send Slack notification: {str(e)}")
                if e.response['error'] == 'invalid_auth':
                    self.logger.error("Invalid Slack authentication. Please check your SLACK_BOT_TOKEN.")
                elif e.response['error'] == 'channel_not_found':
                    self.logger.error("Invalid Slack channel. Please check your SLACK_CHANNEL_ID.")
                raise

    def send_summary(self, store) -> None:
        """Send a summary message after all IPs have been checked"""
        try:
            clean_ips = []
            problem_ips = []

            # Process current results
            for result in self.current_run_results:
                if result['listed_count'] > 0:
                    problem_ips.append(result)
                else:
                    clean_ips.append(result['ip'])

            # Get previous results for comparison
            previous_results = store.get_previous_results()
            last_check_time = store.get_last_check_time()

            # Format summary message
            summary = "*SparkPost IP Blacklist Check Summary*\n"

            if last_check_time:
                last_check = datetime.fromisoformat(last_check_time)
                summary += f"Last check: {last_check.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"

            summary += f"*Total IPs Checked: {len(clean_ips) + len(problem_ips)}*\n\n"

            # Clean IPs
            if clean_ips:
                summary += f"✅ Clean IPs ({len(clean_ips)}):\n"
                summary += ", ".join(clean_ips) + "\n\n"

            # Problem IPs
            if problem_ips:
                summary += f"⚠️ *Problems Found ({len(problem_ips)} IPs):*\n"
                for result in problem_ips:
                    ip = result['ip']
                    summary += f"\n• {ip}:"

                    # Check if this is a new or existing problem
                    if ip in previous_results:
                        new_blacklists = [b['name'] for b in result['blacklists'] 
                                      if b['name'] not in previous_results[ip]]
                        if new_blacklists:
                            summary += " [NEW] "
                    else:
                        summary += " [NEW IP] "

                    for blacklist in result['blacklists']:
                        summary += f"\n  - {blacklist['name']}: {blacklist['removal_url']}"
            else:
                summary += "✨ *No blacklist issues found!* 🎉"

            # Send summary
            self.client.chat_postMessage(
                channel=self.channel_id,
                text=summary,
                unfurl_links=False
            )
            self.logger.info("Successfully sent summary notification to Slack")

            # Clear current run results
            self.current_run_results = []

        except SlackApiError as e:
            self.logger.error(f"Failed to send summary notification: {str(e)}")
            if e.response['error'] == 'invalid_auth':
                self.logger.error("Invalid Slack authentication. Please check your SLACK_BOT_TOKEN.")
            elif e.response['error'] == 'channel_not_found':
                self.logger.error("Invalid Slack channel. Please check your SLACK_CHANNEL_ID.")
            raise