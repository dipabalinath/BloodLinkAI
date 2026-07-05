"""
Database module for BloodLink AI.
Handles SQLite connections and query execution.
"""
import sqlite3
import os
from contextlib import contextmanager
from typing import Any, List, Optional, Tuple, Generator

from config.settings import settings
from utils.logger import logger


class DatabaseManager:
    """
    Manages SQLite database connections and executes queries.
    """
    def __init__(self) -> None:
        # Extract the file path from the DATABASE_URL
        # e.g., 'sqlite:///database/bloodlink.db' -> 'database/bloodlink.db'
        db_url = settings.DATABASE_URL
        if db_url.startswith("sqlite:///"):
            relative_path = db_url.replace("sqlite:///", "", 1)
        else:
            relative_path = db_url

        # Ensure we are using an absolute path relative to the project root
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_absolute_path = os.path.join(base_dir, relative_path)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_absolute_path), exist_ok=True)
        
        self.db_path = db_absolute_path
        self.connection: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """Establishes a connection to the SQLite database."""
        if not self.connection:
            try:
                # Using check_same_thread=False allowing it to be used across threads if needed
                self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
                # Setting row_factory to sqlite3.Row allows accessing columns by name
                self.connection.row_factory = sqlite3.Row
                logger.info(f"Connected to SQLite database at {self.db_path}")
            except sqlite3.Error as e:
                logger.error(f"Failed to connect to database: {e}")
                raise
        return self.connection

    def close(self) -> None:
        """Closes the active database connection."""
        if self.connection:
            try:
                self.connection.close()
                logger.info("Database connection closed.")
            except sqlite3.Error as e:
                logger.error(f"Error closing database connection: {e}")
            finally:
                self.connection = None

    def commit(self) -> None:
        """Commits the current transaction."""
        if self.connection:
            try:
                self.connection.commit()
            except sqlite3.Error as e:
                logger.error(f"Failed to commit transaction: {e}")
                raise

    def rollback(self) -> None:
        """Rolls back the current transaction."""
        if self.connection:
            try:
                self.connection.rollback()
            except sqlite3.Error as e:
                logger.error(f"Failed to rollback transaction: {e}")
                raise

    @contextmanager
    def get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """
        Context manager to provide a database cursor.
        Automatically handles commits or rollbacks on exit.
        """
        conn = self.connect()
        cursor = conn.cursor()
        try:
            yield cursor
            self.commit()
        except Exception as e:
            self.rollback()
            logger.error(f"Transaction failed, rolling back. Error: {e}")
            raise
        finally:
            cursor.close()

    def execute(self, query: str, params: tuple = ()) -> None:
        """Executes a single query (e.g., INSERT, UPDATE, DELETE)."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Executes a query and returns a single result."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()

    def fetch_all(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Executes a query and returns all results."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
