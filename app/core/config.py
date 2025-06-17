from pydantic_settings import BaseSettings
from dotenv import load_dotenv


load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str
    EMAIL: str
    PASSWORD: str

    BASE_URL: str = "https://app-api.pixverse.ai/creative_platform"
    RETRY_STATUS_CODES: set = {429, 500, 502, 503, 504}
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2

    class Config:
        env_file = "../../.env"


settings = Settings()
