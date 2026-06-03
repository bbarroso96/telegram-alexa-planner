import os
import json
from dataclasses import dataclass


@dataclass
class Config:
    bot_token: str
    spreadsheet_id: str
    allowed_user_ids: set
    google_creds: dict

    @classmethod
    def from_env(cls) -> "Config":
        raw_ids = os.environ["ALLOWED_USER_IDS"]
        user_ids = {int(i.strip()) for i in raw_ids.split(",")}

        raw_creds = os.environ["GOOGLE_CREDS_JSON"]
        creds = json.loads(raw_creds)

        return cls(
            bot_token=os.environ["BOT_TOKEN"],
            spreadsheet_id=os.environ["SPREADSHEET_ID"],
            allowed_user_ids=user_ids,
            google_creds=creds,
        )


config = Config.from_env()
