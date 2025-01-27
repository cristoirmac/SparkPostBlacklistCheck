import requests
import time
from typing import Dict, Any, List
import yaml
from bs4 import BeautifulSoup
import re

class MXToolboxClient:
    def __init__(self, logger):
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        self.base_url = config['mxtoolbox']['base_url']
        self.check_interval = config['mxtoolbox']['check_interval']
        self.logger = logger

    def check_ip_blacklist(self, ip: str) -> Dict[str, Any]:
        """
        Check if an IP is blacklisted using MXToolbox
        """
        try:
            # Use the SuperTool endpoint
            url = f"https://mxtoolbox.com/SuperTool.aspx?action=mx%3a{ip}&run=toolpage"
            response = requests.get(url)
            response.raise_for_status()

            # Parse the HTML response
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find blacklist entries
            blacklists: List[Dict[str, str]] = []
            listed_count = 0
            timeout_count = 0

            # Look for the blacklist results table
            blacklist_table = soup.find('table', {'id': re.compile(r'.*GridViewResult')})
            if blacklist_table:
                for row in blacklist_table.find_all('tr')[1:]:  # Skip header row
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        status = cols[0].get_text(strip=True)
                        name = cols[1].get_text(strip=True)

                        if status.lower() == 'error':
                            timeout_count += 1
                        elif status.lower() == 'failed':
                            listed_count += 1
                            removal_url = f"https://mxtoolbox.com/blacklists.aspx#{name}"
                            blacklists.append({
                                'name': name,
                                'removal_url': removal_url
                            })

            result = {
                'ip': ip,
                'listed_count': listed_count,
                'timeout_count': timeout_count,
                'blacklists': blacklists,
                'check_url': url
            }

            self.logger.info(f"Checked IP {ip} against blacklists: {listed_count} listings, {timeout_count} timeouts")

            # Respect rate limiting
            time.sleep(self.check_interval)

            return result

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to check IP {ip}: {str(e)}")
            raise