import logging
import os
import sqlite3
from typing import Set

logger = logging.getLogger(__name__)


class LocalCacheManager:
    """Manages cache synchronization with a local SQLite Database."""

    def __init__(self, db_path: str = "harvester_cache.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS processed_links (
                        url TEXT PRIMARY KEY,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS rejections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT,
                        organization TEXT,
                        title TEXT,
                        reason TEXT,
                        rejected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize SQLite database: {e}")

    def download_processed_links(self) -> Set[str]:
        """Load processed links from the local SQLite database."""
        links: Set[str] = set()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT url FROM processed_links")
                for row in cursor:
                    links.add(row[0])
        except Exception as e:
            logger.error(f"Error reading processed_links from DB: {e}")

        # Legacy Migration: read from processed_links.txt if it exists and migrate to DB
        legacy_file = "processed_links.txt"
        if os.path.exists(legacy_file):
            try:
                with open(legacy_file, "r", encoding="utf-8") as f:
                    legacy_links = {line.strip() for line in f if line.strip()}
                    if legacy_links:
                        self.upload_processed_links(legacy_links)
                        links.update(legacy_links)
                        logger.info(f"Migrated {len(legacy_links)} legacy links to SQLite.")
            except Exception as e:
                logger.warning(f"Error migrating legacy links: {e}")

        return links

    def upload_processed_links(self, links: Set[str]) -> bool:
        """Persist processed links set to the local SQLite database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.executemany(
                    "INSERT OR IGNORE INTO processed_links (url) VALUES (?)",
                    [(link,) for link in links]
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to write local processed links to DB: {e}")
            return False

    def sync_rejection_log(self, local_log_file: str, date_str: str) -> bool:
        """Deprecated in favor of log_rejection_to_db. Retained for backwards compatibility."""
        return True

    def log_rejection_to_db(self, url: str, org: str, title: str, reason: str) -> bool:
        """Log a rejection directly to the SQLite database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO rejections (url, organization, title, reason) VALUES (?, ?, ?, ?)",
                    (url, org, title, reason)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to log rejection to DB: {e}")
            return False
