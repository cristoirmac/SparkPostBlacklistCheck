import sys
from typing import NoReturn
import schedule
import time

from logger import setup_logger
from sparkpost_client import SparkPostClient
from mxtoolbox_client import MXToolboxClient
from slack_notifier import SlackNotifier

def check_ips() -> None:
    """
    Main function to check IPs for blacklisting
    """
    logger = setup_logger()

    try:
        # Initialize clients
        sparkpost = SparkPostClient(logger)
        mxtoolbox = MXToolboxClient(logger)
        slack = SlackNotifier(logger)

        # Get all sending IPs from SparkPost
        sending_ips = sparkpost.get_sending_ips()

        # Check each IP against blacklists
        for ip_info in sending_ips:
            ip = ip_info['ip']
            logger.info(f"Checking IP: {ip}")

            # Check blacklists
            check_result = mxtoolbox.check_ip_blacklist(ip)

            # Send notification if needed
            slack.send_notification(check_result)

    except Exception as e:
        logger.error(f"Error in blacklist monitoring: {str(e)}")
        sys.exit(1)

def main() -> None:
    """
    Entry point for the script
    """
    # Run immediately on start
    check_ips()

    # Schedule daily execution
    schedule.every().day.at("00:00").do(check_ips)

    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()