import os
import mysql.connector


def get_connection():
    """Create a MySQL connection using environment variables.

    The application no longer uses the insecure default of 'root' with no password.
    If the required variables are not provided, a clear RuntimeError is raised so the
    caller can handle the situation gracefully.
    """
    host = os.environ.get("MYSQL_HOST") or os.environ.get("DB_HOST")
    user = os.environ.get("MYSQL_USER") or os.environ.get("DB_USER")
    password = os.environ.get("MYSQL_PASSWORD") or os.environ.get("DB_PASSWORD")
    database = os.environ.get("MYSQL_DATABASE") or os.environ.get("DB_NAME")
    port = int(os.environ.get("MYSQL_PORT", "3306"))

    if not host or not user or not database:
        raise RuntimeError(
            "MySQL is not configured. Set MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD and MYSQL_DATABASE "
            "(or DB_HOST, DB_USER, DB_PASSWORD and DB_NAME) before starting the app."
        )

    conn = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
    )
    return conn
