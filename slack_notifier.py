from typing import Dict, Any
import os
import yaml
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

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

    def format_message(self, check_result: Dict[str, Any]) -> str:
        """
        Format the blacklist check results into a Slack message
        """
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
        """
        Send notification to Slack if conditions are met
        """
        if check_result['listed_count'] > 0 or self.notify_on_clean:
            try:
                message = self.format_message(check_result)
                response = self.client.chat_postMessage(
                    channel=self.channel_id,
                    text=message
                )
                self.logger.info(f"Sent Slack notification for IP {check_result['ip']}")
                
            except SlackApiError as e:
                self.logger.error(f"Failed to send Slack notification: {str(e)}")
                raise
