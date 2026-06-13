"""
Phase 1 — History & Trends Routes
GET /api/v1/history/{repo_url_encoded}  → List past runs
GET /api/v1/history/{repo_url_encoded}/trend → Trend data for charts
GET /api/v1/runs/{run_id}               → Full report for a past run
GET /api/v1/repos                       → All repos analysed by user
GET /api/v1/leaderboard                 → Top repos by quality
"""
import base64
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from app.db.database import get_history, get_run, get_all_repos, get_trend, get_leaderboard

router = APIRouter()


def _uid(request: Request) -> str:
    return request.cookies.get("devtrace_uid", "anonymous")


@router.get("/history/{repo_b64}")
async def repo_history(repo_b64: str, request: Request, limit: int = 30):
    try:
        repo_url = base64.urlsafe_b64decode(repo_b64 + "==").decode()
    except Exception:
        repo_url = repo_b64
    runs = get_history(repo_url, limit=limit)
    return JSONResponse({"repo_url": repo_url, "runs": runs, "total": len(runs)})


@router.get("/history/{repo_b64}/trend")
async def repo_trend(repo_b64: str, limit: int = 20):
    try:
        repo_url = base64.urlsafe_b64decode(repo_b64 + "==").decode()
    except Exception:
        repo_url = repo_b64
    trend = get_trend(repo_url, limit=limit)
    return JSONResponse({"repo_url": repo_url, "trend": trend})


@router.get("/runs/{run_id}")
async def get_run_detail(run_id: int):
    run = get_run(run_id)
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")
    return JSONResponse(run)


@router.get("/repos")
async def list_repos(request: Request):
    repos = get_all_repos(_uid(request))
    return JSONResponse({"repos": repos})


@router.get("/leaderboard")
async def leaderboard(limit: int = 10):
    return JSONResponse({"leaderboard": get_leaderboard(limit)})
