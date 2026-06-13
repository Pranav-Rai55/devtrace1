"""
DevTrace — FastAPI Application Factory (Ultimate)
"""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.config import settings
from app.db.database import init_db

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="DevTrace API",
        description="AI-Powered GitHub Repository Code Intelligence — Ultimate Edition",
        version="5.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    PREFIX = "/api/v1"

    from app.routes import health, analysis
    from app.routes.auth          import router as auth_router
    from app.routes.history       import router as history_router
    from app.routes.notifications import router as notif_router
    from app.routes.export        import router as export_router

    app.include_router(health.router,    prefix=PREFIX, tags=["Health"])
    app.include_router(analysis.router,  prefix=PREFIX, tags=["Analysis"])
    app.include_router(auth_router,      prefix=PREFIX, tags=["Auth"])
    app.include_router(history_router,   prefix=PREFIX, tags=["History"])
    app.include_router(notif_router,     prefix=PREFIX, tags=["Notifications"])
    app.include_router(export_router,    prefix=PREFIX, tags=["Export"])

    @app.get("/", include_in_schema=False)
    async def root():
        dashboard_path = Path(__file__).resolve().parent.parent / "devtrace_dashboard.html"
        if not dashboard_path.exists():
            raise HTTPException(404, "Dashboard file not found.")
        return FileResponse(dashboard_path, media_type="text/html")

    @app.on_event("startup")
    async def startup():
        init_db()
        _print_status()

    @app.on_event("shutdown")
    async def shutdown():
        logger.info("🛑  DevTrace shutting down")

    return app


def _print_status():
    logger.info("\n" + "═"*52)
    logger.info("  DevTrace v5.0 — Ultimate Edition")
    logger.info("═"*52)

    # ML deps
    try:
        import sklearn, numpy
        logger.info("  ✅  ML Engine:    sklearn + numpy (7 models active)")
    except ImportError:
        logger.warning("  ⚠️   ML Engine:    heuristic fallbacks (pip install scikit-learn numpy)")

    # AI fixes
    if settings.ANTHROPIC_API_KEY:
        logger.info("  ✅  AI Fixes:     Anthropic Claude (claude-haiku)")
    elif settings.OPENAI_API_KEY:
        logger.info("  ✅  AI Fixes:     OpenAI GPT-4o-mini")
    else:
        logger.info("  💡  AI Fixes:     template-based (set ANTHROPIC_API_KEY)")

    # ESLint
    import subprocess
    try:
        subprocess.run(["eslint","--version"], capture_output=True, timeout=5)
        logger.info("  ✅  ESLint:       available (JS/TS deep scan)")
    except Exception:
        logger.warning("  💡  ESLint:       not found (npm install -g eslint for deeper JS scan)")

    # Auth
    if settings.GITHUB_CLIENT_ID:
        logger.info("  ✅  OAuth:        GitHub login configured")
    else:
        logger.info("  💡  OAuth:        set GITHUB_CLIENT_ID for login")

    # Notifications
    if settings.SLACK_WEBHOOK_URL:
        logger.info("  ✅  Slack:        webhook configured")
    if settings.TEAMS_WEBHOOK_URL:
        logger.info("  ✅  Teams:        webhook configured")

    logger.info("═"*52)
    logger.info("  Analyzers: Quality · Security · Performance ·")
    logger.info("             Architecture · Dependencies · ML ·")
    logger.info("             JS/TS · Test Coverage · Git Blame ·")
    logger.info("             Incremental · AI Fixes")
    logger.info("═"*52 + "\n")
