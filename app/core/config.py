import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/capstone",
)
APP_ENV = os.getenv("APP_ENV", "dev")
GPT_API_KEY = os.getenv("GPT_API_KEY", "")
GPT_API_URL = os.getenv("GPT_API_URL", "https://api.openai.com/v1/responses")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-5.0")
GPT_TIMEOUT_SECONDS = float(os.getenv("GPT_TIMEOUT_SECONDS", "120"))
