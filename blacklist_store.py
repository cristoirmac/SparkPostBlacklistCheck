import sqlite3
from typing import Dict, List, Any
from datetime import datetime

class BlacklistStore:
    def __init__(self, logger):
        self.logger = logger
        self.conn = sqlite3.connect('blacklist_history.db')
        self.create_tables()

    def create_tables(self) -> None:
        """Create the necessary tables if they don't exist"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS check_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_timestamp TEXT NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS blacklist_results (
                    run_id INTEGER,
                    ip TEXT NOT NULL,
                    blacklist_name TEXT,
                    removal_url TEXT,
                    FOREIGN KEY (run_id) REFERENCES check_runs(id)
                )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Failed to create tables: {str(e)}")
            raise

    def store_results(self, results: List[Dict[str, Any]]) -> int:
        """Store the results of a check run"""
        try:
            cursor = self.conn.cursor()

            # Create new run record
            cursor.execute('INSERT INTO check_runs (run_timestamp) VALUES (?)',
                          (datetime.now().isoformat(),))
            run_id = cursor.lastrowid
            if run_id is None:
                raise ValueError("Failed to get last insert ID")

            # Store results
            for result in results:
                ip = result['ip']
                for blacklist in result.get('blacklists', []):
                    cursor.execute('''
                        INSERT INTO blacklist_results 
                        (run_id, ip, blacklist_name, removal_url)
                        VALUES (?, ?, ?, ?)
                    ''', (run_id, ip, blacklist['name'], blacklist['removal_url']))

            self.conn.commit()
            return run_id
        except sqlite3.Error as e:
            self.logger.error(f"Failed to store results: {str(e)}")
            raise

    def get_previous_results(self) -> Dict[str, List[str]]:
        """Get results from the previous run"""
        try:
            cursor = self.conn.cursor()

            # Get the last run ID
            cursor.execute('SELECT id FROM check_runs ORDER BY run_timestamp DESC LIMIT 1')
            result = cursor.fetchone()

            if not result:
                return {}

            last_run_id = result[0]

            # Get blacklisted IPs from the last run
            cursor.execute('''
                SELECT DISTINCT ip, blacklist_name
                FROM blacklist_results
                WHERE run_id = ?
            ''', (last_run_id,))

            results = {}
            for ip, blacklist in cursor.fetchall():
                if ip not in results:
                    results[ip] = []
                results[ip].append(blacklist)

            return results
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get previous results: {str(e)}")
            return {}

    def get_last_check_time(self) -> str:
        """Get the timestamp of the last check"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT run_timestamp FROM check_runs ORDER BY run_timestamp DESC LIMIT 1')
            result = cursor.fetchone()
            return result[0] if result else "No previous checks found"
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get last check time: {str(e)}")
            return "Error retrieving last check time"