import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

# VITO STT (optional - text input only if not set)
VITO_CLIENT_ID = os.getenv("VITO_CLIENT_ID", "")
VITO_CLIENT_SECRET = os.getenv("VITO_CLIENT_SECRET", "")

# Asana (required)
ASANA_TOKEN = os.getenv("ASANA_TOKEN", "")

# Notion (required)
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")

# Misc
DEFAULT_AUTHOR = os.getenv("DEFAULT_AUTHOR", "")
