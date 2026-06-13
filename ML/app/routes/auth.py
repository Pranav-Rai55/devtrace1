"""
Phase 3 — Auth Routes
GET  /api/v1/auth/login          → Redirect to GitHub OAuth
GET  /api/v1/auth/callback       → Handle OAuth callback
GET  /api/v1/auth/me             → Current user profile
POST /api/v1/auth/logout         → Clear session
"""
import secrets
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from app.services.github_oauth import get_oauth_url, exchange_code, get_github_user
from app.db.database import upsert_user, get_user
from app.config import settings

router = APIRouter()
_states: dict = {}  # Simple in-memory state store


@router.get("/auth/login")
async def login():
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(400, "GitHub OAuth not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in .env")
    state = secrets.token_urlsafe(16)
    _states[state] = True
    return RedirectResponse(get_oauth_url(state))


@router.get("/auth/callback")
async def callback(code: str, state: str, request: Request):
    if state not in _states:
        raise HTTPException(400, "Invalid OAuth state")
    del _states[state]

    token = exchange_code(code)
    if not token:
        raise HTTPException(400, "Failed to exchange OAuth code")

    user = get_github_user(token)
    if not user:
        raise HTTPException(400, "Failed to fetch GitHub user")

    user_id = str(user["id"])
    upsert_user({**user, "id": user_id, "access_token": token})

    resp = RedirectResponse(url="/#logged-in")
    resp.set_cookie("devtrace_uid", user_id, httponly=True, max_age=60*60*24*30, samesite="lax")
    resp.set_cookie("devtrace_token", token, httponly=True, max_age=60*60*24*30, samesite="lax")
    return resp


@router.get("/auth/me")
async def me(request: Request):
    uid = request.cookies.get("devtrace_uid")
    if not uid:
        return JSONResponse({"authenticated": False, "user": None})
    user = get_user(uid)
    if not user:
        return JSONResponse({"authenticated": False, "user": None})
    return JSONResponse({"authenticated": True, "user": {
        "id": user["id"],
        "login": user["github_login"],
        "name": user["github_name"],
        "avatar_url": user["avatar_url"],
    }})


@router.post("/auth/logout")
async def logout():
    resp = JSONResponse({"message": "Logged out"})
    resp.delete_cookie("devtrace_uid")
    resp.delete_cookie("devtrace_token")
    return resp
