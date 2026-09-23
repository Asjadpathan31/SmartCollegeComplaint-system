"""
database.py
Handles all MySQL connectivity for the Smart College Complaint & Resolution System.
Every other module (app.py) should go through the helpers here rather than
calling mysql.connector directly, so connection handling and error behavior
stay consistent across the whole app.
"""

import mysql.connector
from mysql.connector import pooling, Error
from config import Config

_pool = None


def init_pool():
    """Initialize a global connection pool. Called once when app.py starts."""
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="scc_pool",
            pool_size=5,
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DATABASE,
            autocommit=False,
        )
    return _pool


def get_connection():
    """Return a connection from the pool (creates the pool on first call)."""
    pool = init_pool()
    return pool.get_connection()


class DatabaseConnection:
    """
    Context manager for a single connection + cursor.

    Usage:
        with DatabaseConnection() as cursor:
            cursor.execute("SELECT * FROM departments")
            rows = cursor.fetchall()
    """

    def __init__(self, dictionary=True):
        self.dictionary = dictionary
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor(dictionary=self.dictionary)
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.cursor.close()
        self.conn.close()
        # Returning False re-raises any exception that occurred, which is what we want
        return False


def execute_query(query, params=None, fetch=None):
    """
    Run a single query and handle commit/rollback + cursor/connection cleanup.

    fetch:
        None      -> for INSERT/UPDATE/DELETE. Returns the cursor.lastrowid
                     (useful for INSERT to get the new primary key) and rowcount.
        "one"     -> returns a single row (dict) or None
        "all"     -> returns a list of rows (dicts)
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())

        if fetch == "one":
            result = cursor.fetchone()
            conn.commit()
            return result
        elif fetch == "all":
            result = cursor.fetchall()
            conn.commit()
            return result
        else:
            conn.commit()
            return {"lastrowid": cursor.lastrowid, "rowcount": cursor.rowcount}

    except Error as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def test_connection():
    """Quick health check used by the /db-test route. Returns (bool, message)."""
    try:
        with DatabaseConnection() as cursor:
            cursor.execute("SELECT DATABASE() AS db_name, VERSION() AS version")
            info = cursor.fetchone()
        return True, info
    except Error as e:
        return False, str(e)
