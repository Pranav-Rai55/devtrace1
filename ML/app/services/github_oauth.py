"""
Phase 3 — GitHub OAuth Service
Handles login, token exchange, user profile fetching
"""

import json
import urllib.request
import urllib.parse
from typing import Dict, Optional
from app.config import settings


GITHUB_AUTH_URL  = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API       = "https://api.github.com"


def get_oauth_url(state: str) -> str:
    """Build the GitHub OAuth redirect URL."""
    params = urllib.parse.urlencode({
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "scope": "repo read:user user:email",
        "state": state,
    })
    return f"{GITHUB_AUTH_URL}?{params}"


def exchange_code(code: str) -> Optional[str]:
    """Exchange OAuth code for access token."""
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        return None
    body = urllib.parse.urlencode({
        "client_id":     settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GITHUB_CLIENT_SECRET,
        "code":          code,
        "redirect_uri":  settings.GITHUB_REDIRECT_URI,
    }).encode()
    req = urllib.request.Request(
        GITHUB_TOKEN_URL, data=body,
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("access_token")
    except Exception:
        return None


def get_github_user(token: str) -> Optional[Dict]:
    """Fetch GitHub user profile using access token."""
    try:
        req = urllib.request.Request(
            f"{GITHUB_API}/user",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            data["access_token"] = token
            return data
    except Exception:
        return None


def get_user_repos(token: str, page: int = 1) -> list:
    """List the user's GitHub repos for quick-select."""
    try:
        url = f"{GITHUB_API}/user/repos?sort=updated&per_page=30&page={page}"
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        return []
