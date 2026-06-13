"""
Phase 4 — Notification Routes
GET  /api/v1/notifications/settings    → Get current settings
POST /api/v1/notifications/settings    → Save webhook URLs
POST /api/v1/notifications/test        → Send a test message
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.db.database import get_notification_settings, save_notification_settings
from app.notifications.notifier import notifier

router = APIRouter()


class NotificationSettings(BaseModel):
    slack_webhook:    str = ""
    teams_webhook:    str = ""
    notify_high:      bool = True
    notify_complete:  bool = True


class TestPayload(BaseModel):
    platform: str = "slack"


def _uid(request: Request) -> str:
    return request.cookies.get("devtrace_uid", "anonymous")


@router.get("/notifications/settings")
async def get_settings(request: Request):
    return JSONResponse(get_notification_settings(_uid(request)))


@router.post("/notifications/settings")
async def save_settings(payload: NotificationSettings, request: Request):
    save_notification_settings(
        _uid(request),
        payload.slack_webhook, payload.teams_webhook,
        payload.notify_high, payload.notify_complete,
    )
    return JSONResponse({"message": "Settings saved"})


@router.post("/notifications/test")
async def test_notification(payload: TestPayload, request: Request):
    uid = _uid(request)
    settings = get_notification_settings(uid)
    webhook = settings.get("slack_webhook" if payload.platform == "slack" else "teams_webhook", "")
    if not webhook:
        return JSONResponse({"ok": False, "message": "No webhook URL configured for this platform."})
    notifier.send_analysis_complete(webhook, payload.platform, {
        "repo_name": "devtrace/test",
        "quality_score": {"value": 85},
        "security_risks": {"value": 2},
        "maintainability": {"value": "A-"},
        "estimated_tech_debt_hours": {"value": "8h"},
        "critical_issues_count": 1,
        "vulnerable_dependencies": 0,
    })
    return JSONResponse({"ok": True, "message": f"Test notification sent to {payload.platform}."})
