"""
DevTrace — AI Codebase Intelligence Platform
Entry Point
"""

import uvicorn
from app.api import create_app
from app.config import settings

app = create_app()

if __name__ == "__main__":
    bind_host = "127.0.0.1"
    if settings.APP_ENV == "development":
        uvicorn.run(
            "main:app",
            host=bind_host,
            port=8000,
            reload=True,
            log_level="info",
        )
    else:
        uvicorn.run(
            app,
            host=bind_host,
            port=8000,
            log_level="info",
        )
        
