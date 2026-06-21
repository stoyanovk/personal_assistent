from dotenv import load_dotenv
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, ValidationError

logger = logging.getLogger(__name__)
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict()
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    database_url: str = Field(alias="DATABASE_URL")
    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    default_timezone: str = Field(alias="DEFAULT_TIMEZONE")


settings = None
try:
    settings = Settings()
except ValidationError as e:
    logger.exception("config creation failed", e)
