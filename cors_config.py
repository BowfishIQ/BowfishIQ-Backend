# cors_config.py
import os

from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://fieldiqpro.com",
    "https://www.fieldiqpro.com",
    "https://staging.fieldiqpro.com",
    "https://stagging.fieldiqpro.com",
]


def _allowed_origins():
    configured = os.getenv("CORS_ALLOWED_ORIGINS", "")
    extra_origins = [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
    return list(dict.fromkeys([*ALLOWED_ORIGINS, *extra_origins]))


def setup_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_origin_regex=r"https://([a-z0-9-]+\.)*fieldiqpro\.com",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
