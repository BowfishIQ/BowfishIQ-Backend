import os

from dotenv import load_dotenv


load_dotenv()


APP_NAME = os.getenv("APP_NAME", "bowfishIQ").strip() or "bowfishIQ"
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "720"))

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_FISH_MODEL = os.getenv("OPENAI_FISH_MODEL", "gpt-4.1").strip() or "gpt-4.1"
