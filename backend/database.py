from contextlib import contextmanager
import logging

import mysql.connector
from mysql.connector import Error

from config import Config


logger = logging.getLogger(__name__)


class DatabaseError(RuntimeError):
    """Raised when SmartPlan cannot complete a database operation."""


@contextmanager
def get_connection():
    """Open one MySQL connection using the configured environment values."""
    connection = None

    try:
        connection = mysql.connector.connect(**Config.DB_CONFIG)
        yield connection

    except Error as exc:
        logger.error(
            "MySQL connection failed: host=%s port=%s database=%s user=%s error=%s",
            Config.DB_CONFIG["host"],
            Config.DB_CONFIG["port"],
            Config.DB_CONFIG["database"],
            Config.DB_CONFIG["user"],
            exc,
        )
        raise DatabaseError(str(exc)) from exc

    finally:
        if connection and connection.is_connected():
            connection.close()


@contextmanager
def get_cursor(dictionary=True):
    """
    Yield a buffered MySQL cursor and always close
    both cursor and connection.
    """
    with get_connection() as connection:

        cursor = connection.cursor(
            dictionary=dictionary,
            buffered=True
        )

        try:
            yield connection, cursor

        finally:
            cursor.close()


def initialize_database():
    """
    Verify that the configured SmartPlan MySQL database
    is reachable.
    """
    with get_cursor(dictionary=False) as (_, cursor):

        cursor.execute("SELECT 1")

        # Read the result so MySQL Connector does not
        # leave an unread result on the connection.
        result = cursor.fetchone()

        if result != (1,):
            raise DatabaseError(
                "Database health check returned an unexpected result."
            )

        logger.info("MySQL database connection verified successfully.")


def execute_query(query, params=None, fetchone=False, fetchall=False):
    """
    Execute a SELECT query and optionally return one or all rows.
    """
    with get_cursor(dictionary=True) as (_, cursor):

        cursor.execute(query, params or ())

        if fetchone:
            return cursor.fetchone()

        if fetchall:
            return cursor.fetchall()

        return None


def execute_write(query, params=None):
    """
    Execute INSERT, UPDATE, or DELETE query and commit changes.
    """
    with get_cursor(dictionary=False) as (connection, cursor):

        cursor.execute(query, params or ())

        connection.commit()

        return cursor.lastrowid


def execute_many(query, data):
    """
    Execute the same INSERT/UPDATE query for multiple records.
    """
    with get_cursor(dictionary=False) as (connection, cursor):

        cursor.executemany(query, data)

        connection.commit()

        return cursor.rowcount