import os
import yaml
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, List
from email_validator import validate_email, EmailNotValidError

class EmailNotifier:
    def __init__(self, logger):
        self.logger = logger

        # Load config
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        self.config = config['notifications']['email']
        self.enabled = self.config['enabled']
        self.notify_on_clean = self.config['notify_on_clean']
        self.recipients = self.config['recipients']
        self.from_name = self.config['from_name']
        self.subject_prefix = self.config['subject_prefix']

        # SparkPost SMTP settings
        self.smtp_host = "smtp.sparkpostmail.com"
        self.smtp_port = 587
        self.smtp_username = "SMTP_Injection"
        self.api_key = os.environ.get('SPARKPOST_API_KEY')

        if not self.api_key:
            raise ValueError("SPARKPOST_API_KEY environment variable must be set")

        # Validate recipients if any are configured
        if self.recipients:
            self._validate_emails()
        else:
            self.logger.warning("No email recipients configured. Email notifications will be skipped.")
            self.enabled = False

        # Store results for summary
        self.current_run_results = []

    def _validate_emails(self) -> None:
        """Validate all email addresses in configuration"""
        try:
            # Validate recipient emails
            for email in self.recipients:
                validate_email(email)

        except EmailNotValidError as e:
            self.logger.error(f"Invalid email address found: {str(e)}")
            raise

    def format_message(self, check_result: Dict[str, Any]) -> str:
        """Format the blacklist check results into an email message"""
        ip = check_result['ip']
        listed_count = check_result['listed_count']
        timeout_count = check_result['timeout_count']
        ip_pool = check_result.get('pool', 'default')

        message = f"[{ip_pool}] Checking {ip} against 63 known blacklists...\n"
        message += f"Listed {listed_count} times with {timeout_count} timeouts\n\n"

        if listed_count > 0:
            message += "Blacklisted on:\n"
            for blacklist in check_result['blacklists']:
                message += f"- {blacklist['name']}: {blacklist['removal_url']}\n"

        message += f"\nFull report: {check_result['check_url']}"

        return message

    def send_notification(self, check_result: Dict[str, Any]) -> None:
        """Send email notification if conditions are met"""
        if not self.enabled:
            return

        try:
            # Store result for summary
            self.current_run_results.append(check_result)

            ip = check_result['ip']
            pool = check_result.get('pool', 'default')
            self.logger.info(f"Processing email notification for IP {ip} (Pool: {pool})")

            # Only send if blacklisted or notify_on_clean is true
            if check_result['listed_count'] > 0 or self.notify_on_clean:
                message = self.format_message(check_result)
                subject = f"{self.subject_prefix} Blacklist Alert - IP {ip} ({pool})"

                self._send_email(subject, message)
                self.logger.info(f"Successfully sent email notification for IP {ip}")

        except Exception as e:
            self.logger.error(f"Error in send_notification for IP {ip}: {str(e)}")
            raise

    def send_summary(self, store) -> None:
        """Send a summary email after all IPs have been checked"""
        if not self.enabled:
            return

        try:
            # Group results by IP pool
            clean_ips_by_pool = {}
            problem_ips_by_pool = {}

            # Process current results
            for result in self.current_run_results:
                ip_pool = result.get('pool', 'default')
                if result['listed_count'] > 0:
                    if ip_pool not in problem_ips_by_pool:
                        problem_ips_by_pool[ip_pool] = []
                    problem_ips_by_pool[ip_pool].append(result)
                else:
                    if ip_pool not in clean_ips_by_pool:
                        clean_ips_by_pool[ip_pool] = []
                    clean_ips_by_pool[ip_pool].append(result['ip'])

            # Get previous results for comparison
            previous_results = store.get_previous_results()
            last_check_time = store.get_last_check_time()

            # Format summary message
            summary = "SparkPost IP Blacklist Check Summary\n"
            summary += "=" * 40 + "\n\n"

            if last_check_time:
                last_check = datetime.fromisoformat(last_check_time)
                summary += f"Last check: {last_check.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"

            total_ips = sum(len(ips) for ips in clean_ips_by_pool.values()) + \
                       sum(len(ips) for ips in problem_ips_by_pool.values())
            summary += f"Total IPs Checked: {total_ips}\n\n"

            # Clean IPs by pool
            if clean_ips_by_pool:
                summary += "Clean IPs:\n"
                for pool, ips in sorted(clean_ips_by_pool.items()):
                    if ips:
                        summary += f"Pool: {pool} ({len(ips)} IPs)\n"
                        summary += f"{', '.join(ips)}\n\n"

            # Problem IPs by pool
            if problem_ips_by_pool:
                summary += "Problems Found:\n"
                summary += "=" * 20 + "\n\n"
                for pool, results in sorted(problem_ips_by_pool.items()):
                    summary += f"Pool: {pool} ({len(results)} affected IPs)\n"
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
                        summary += "\n\n"
            else:
                summary += "No blacklist issues found!\n"

            # Send summary email
            subject = f"{self.subject_prefix} Daily Summary Report"
            self._send_email(subject, summary)
            self.logger.info("Successfully sent summary email notification")

            # Clear current run results
            self.current_run_results = []

        except Exception as e:
            self.logger.error(f"Failed to send summary email notification: {str(e)}")
            raise

    def _send_email(self, subject: str, body: str) -> None:
        """Helper method to send an email"""
        if not self.recipients:
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = f"{self.from_name} <noreply@sparkpostmail.com>"
            msg['To'] = ", ".join(self.recipients)
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.api_key)
                server.send_message(msg)

        except Exception as e:
            self.logger.error(f"Failed to send email: {str(e)}")
            raise