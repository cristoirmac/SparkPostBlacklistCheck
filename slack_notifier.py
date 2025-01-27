import os
import yaml
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime
from typing import Dict, Any, List
from collections import defaultdict

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
        ip_pool = check_result.get('pool', 'default')

        message = f"[{ip_pool}] Checking {ip} against 63 known blacklists... "
        message += f"Listed {listed_count} times with {timeout_count} timeouts"

        if listed_count > 0:
            message += "\n\nBlacklisted on:"
            for blacklist in check_result['blacklists']:
                message += f"\n- {blacklist['name']}: {blacklist['removal_url']}"

        message += f"\n\nFull report: {check_result['check_url']}"

        return message

    def send_notification(self, check_result: Dict[str, Any]) -> None:
        """Send notification to Slack if conditions are met"""
        try:
            # Store result for summary
            self.current_run_results.append(check_result)

            ip = check_result['ip']
            pool = check_result.get('pool', 'default')
            self.logger.info(f"Processing notification for IP {ip} (Pool: {pool})")

            # Only send if blacklisted or notify_on_clean is true
            if check_result['listed_count'] > 0 or self.notify_on_clean:
                try:
                    message = self.format_message(check_result)
                    self.logger.info(f"Sending Slack message for IP {ip}: {message[:100]}...")

                    response = self.client.chat_postMessage(
                        channel=self.channel_id,
                        text=message,
                        unfurl_links=False  # Prevent link previews for cleaner messages
                    )

                    if response['ok']:
                        self.logger.info(f"Successfully sent Slack notification for IP {ip}")
                    else:
                        self.logger.error(f"Failed to send Slack message: {response.get('error', 'Unknown error')}")

                except SlackApiError as e:
                    self.logger.error(f"Failed to send Slack notification for IP {ip}: {str(e)}")
                    if e.response['error'] == 'invalid_auth':
                        self.logger.error("Invalid Slack authentication. Please check your SLACK_BOT_TOKEN.")
                    elif e.response['error'] == 'channel_not_found':
                        self.logger.error("Invalid Slack channel. Please check your SLACK_CHANNEL_ID.")
                    raise

        except Exception as e:
            self.logger.error(f"Error in send_notification: {str(e)}")
            raise

    def send_summary(self, store) -> None:
        """Send a summary message after all IPs have been checked"""
        try:
            # Group results by IP pool
            clean_ips_by_pool = defaultdict(list)
            problem_ips_by_pool = defaultdict(list)

            # Process current results
            for result in self.current_run_results:
                ip_pool = result.get('pool', 'default')
                if result['listed_count'] > 0:
                    problem_ips_by_pool[ip_pool].append(result)
                else:
                    clean_ips_by_pool[ip_pool].append(result['ip'])

            # Get previous results for comparison
            previous_results = store.get_previous_results()
            last_check_time = store.get_last_check_time()

            # Format summary message
            summary = "*SparkPost IP Blacklist Check Summary*\n"

            if last_check_time:
                last_check = datetime.fromisoformat(last_check_time)
                summary += f"Last check: {last_check.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"

            total_ips = sum(len(ips) for ips in clean_ips_by_pool.values()) + \
                       sum(len(ips) for ips in problem_ips_by_pool.values())
            summary += f"*Total IPs Checked: {total_ips}*\n\n"

            # Clean IPs by pool
            if clean_ips_by_pool:
                summary += "✅ *Clean IPs:*\n"
                for pool, ips in sorted(clean_ips_by_pool.items()):
                    if ips:
                        summary += f"• *Pool: {pool}* ({len(ips)} IPs)\n"
                        summary += f"  {', '.join(ips)}\n"
                summary += "\n"

            # Problem IPs by pool
            if problem_ips_by_pool:
                summary += "⚠️ *Problems Found:*\n"
                for pool, results in sorted(problem_ips_by_pool.items()):
                    summary += f"\n*Pool: {pool}* ({len(results)} affected IPs)\n"
                    for result in results:
                        ip = result['ip']
                        summary += f"• {ip}:"

                        # Check if this is a new or existing problem
                        if ip in previous_results:
                            new_blacklists = [b['name'] for b in result['blacklists']
                                              if b['name'] not in previous_results[ip]['blacklists']]
                            if new_blacklists:
                                summary += " [NEW] "
                        else:
                            summary += " [NEW IP] "

                        for blacklist in result['blacklists']:
                            summary += f"\n  - {blacklist['name']}: {blacklist['removal_url']}"
                        summary += "\n"
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