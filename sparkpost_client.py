import requests
import yaml
from typing import List, Dict, Any
import os

class SparkPostClient:
    def __init__(self, logger):
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        self.base_url = config['sparkpost']['base_url']
        self.api_key = os.environ.get('SPARKPOST_API_KEY')
        if not self.api_key:
            raise ValueError("SPARKPOST_API_KEY environment variable must be set")

        self.logger = logger
        self.headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }

    def get_sending_ips(self) -> List[Dict[str, Any]]:
        """
        Fetch all sending IPs from SparkPost
        """
        try:
            response = requests.get(
                f"{self.base_url}/sending-ips",
                headers=self.headers
            )
            response.raise_for_status()

            data = response.json()
            # Extract just the IP addresses and relevant information
            ips = [{'ip': ip_info['external_ip']} for ip_info in data['results']]

            self.logger.info("Successfully retrieved sending IPs from SparkPost")
            return ips

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch sending IPs: {str(e)}")
            raise