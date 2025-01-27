import sys
from typing import NoReturn
import schedule
import time

from logger import setup_logger
from sparkpost_client import SparkPostClient
from mxtoolbox_client import MXToolboxClient
from slack_notifier import SlackNotifier
from email_notifier import EmailNotifier
from blacklist_store import BlacklistStore

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
        email = EmailNotifier(logger)
        store = BlacklistStore(logger)

        # Get all sending IPs from SparkPost
        sending_ips = sparkpost.get_sending_ips()
        check_results = []

        logger.info(f"Starting blacklist checks for {len(sending_ips)} IPs")

        # Check each IP against blacklists
        for ip_info in sending_ips:
            ip = ip_info['ip']
            pool = ip_info.get('pool', 'default')
            hostname = ip_info.get('hostname', 'N/A')
            logger.info(f"Checking IP: {ip} (Pool: {pool})")

            # Check blacklists
            check_result = mxtoolbox.check_ip_blacklist(ip)
            # Add pool and hostname information to check result
            check_result['pool'] = pool
            check_result['hostname'] = hostname
            check_results.append(check_result)

            # Send notifications
            try:
                logger.info(f"Sending notifications for IP {ip} (Pool: {pool})")

                # Send Slack notification
                try:
                    slack.send_notification(check_result)
                except Exception as e:
                    logger.error(f"Error sending Slack notification for IP {ip}: {str(e)}")

                # Send email notification
                try:
                    email.send_notification(check_result)
                except Exception as e:
                    logger.error(f"Error sending email notification for IP {ip}: {str(e)}")

            except Exception as e:
                logger.error(f"Error sending notifications for IP {ip}: {str(e)}")

        # Store results for historical tracking
        try:
            store.store_results(check_results)
            logger.info("Successfully stored check results in database")
        except Exception as e:
            logger.error(f"Error storing results in database: {str(e)}")

        # Send summary notifications
        try:
            logger.info("Sending summary notifications")

            # Send Slack summary
            try:
                slack.send_summary(store)
                logger.info("Successfully sent Slack summary notification")
            except Exception as e:
                logger.error(f"Error sending Slack summary notification: {str(e)}")

            # Send email summary
            try:
                email.send_summary(store)
                logger.info("Successfully sent email summary notification")
            except Exception as e:
                logger.error(f"Error sending email summary notification: {str(e)}")

        except Exception as e:
            logger.error(f"Error sending summary notifications: {str(e)}")

    except Exception as e:
        logger.error(f"Error in blacklist monitoring: {str(e)}")
        sys.exit(1)

def main() -> None:
    """
    Entry point for the script
    """
    logger = setup_logger()
    logger.info("Starting SparkPost IP Blacklist Monitor")

    # Run immediately on start
    check_ips()

    # Schedule daily execution
    schedule.every().day.at("00:00").do(check_ips)
    logger.info("Scheduled daily checks for 00:00 UTC")

    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()