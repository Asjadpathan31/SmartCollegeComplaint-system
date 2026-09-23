import os
from dotenv import load_dotenv

# Load .env by absolute path next to this file — not relative to whatever
# folder the app happens to be launched from — so "python app.py" works
# the same whether run from the project root or elsewhere.
_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_ENV_PATH)


class Config:
    """Application configuration, loaded from environment variables (.env)."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "smart_college_complaint")

    SESSION_PERMANENT = False
    SESSION_TYPE = "filesystem"


def config_debug_summary():
    """Used by the /config-check route so setup problems are visible in the browser,
    not just guessed at from a stack trace."""
    return {
        "env_file_found": os.path.isfile(_ENV_PATH),
        "env_file_path": _ENV_PATH,
        "MYSQL_HOST": Config.MYSQL_HOST,
        "MYSQL_PORT": Config.MYSQL_PORT,
        "MYSQL_USER": Config.MYSQL_USER,
        "MYSQL_PASSWORD_set": bool(Config.MYSQL_PASSWORD),
        "MYSQL_DATABASE": Config.MYSQL_DATABASE,
    }
