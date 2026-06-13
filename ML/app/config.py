"""
DevTrace — Application Configuration
All settings are read from environment variables or .env file.
"""

import os
import tempfile
from pydantic_settings import BaseSettings
from typing import List

DEFAULT_CLONE_DIR = os.path.join(tempfile.gettempdir(), "devtrace_repos")


class Settings(BaseSettings):
    # ── GitHub ────────────────────────────────────────────────────
    GITHUB_TOKEN:         str = ""
    GITHUB_CLIENT_ID:     str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI:  str = "http://localhost:8000/api/v1/auth/callback"

    # ── Session ───────────────────────────────────────────────────
    SESSION_SECRET: str = "devtrace-change-this-in-production"

    # ── App ───────────────────────────────────────────────────────
    APP_ENV: str = "development"
    ALLOWED_ORIGINS: List[str] = ["*"]

    # ── Cloning ───────────────────────────────────────────────────
    CLONE_BASE_DIR: str = DEFAULT_CLONE_DIR

    # ── AI Fix Generation ─────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY:    str = ""

    # ── Notifications ─────────────────────────────────────────────
    SLACK_WEBHOOK_URL: str = ""
    TEAMS_WEBHOOK_URL: str = ""

    # ── Limits ────────────────────────────────────────────────────
    MAX_FILE_SIZE_KB: int = 500
    MAX_REPO_SIZE_MB: int = 200

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
