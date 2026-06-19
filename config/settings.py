import os
import json
from dataclasses import dataclass, field


@dataclass
class Config:
    """App configuration, read from environment / .env.

    The bot needs BOT_TOKEN / ALLOWED_USER_IDS; the web API and seed scripts run
    fine without them. The Google Sheets fields are only needed by the one-time
    migration script (scripts/migrate_from_sheets.py) and are optional otherwise.
    """

    db_path: str
    bot_token: str | None
    allowed_user_ids: set = field(default_factory=set)
    spreadsheet_id: str | None = None
    google_creds: dict | None = None

    @classmethod
    def from_env(cls) -> "Config":
        raw_ids = os.environ.get("ALLOWED_USER_IDS", "")
        user_ids = {int(i.strip()) for i in raw_ids.split(",") if i.strip()}

        raw_creds = os.environ.get("GOOGLE_CREDS_JSON")
        creds = json.loads(raw_creds) if raw_creds else None

        return cls(
            db_path=os.environ.get("DB_PATH", "data/planner.db"),
            bot_token=os.environ.get("BOT_TOKEN"),
            allowed_user_ids=user_ids,
            spreadsheet_id=os.environ.get("SPREADSHEET_ID"),
            google_creds=creds,
        )


config = Config.from_env()
