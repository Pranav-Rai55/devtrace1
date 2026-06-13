"""
DevTrace — Analysis Routes
POST   /api/v1/analyze           Start analysis
GET    /api/v1/analyze/{id}      Poll status
DELETE /api/v1/analyze/{id}      Cancel task
WS     /api/v1/ws/{id}           Real-time WebSocket stream
GET    /api/v1/search            NL code search
GET    /api/v1/cache/stats       Cache info
DELETE /api/v1/cache             Clear cache
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from app.models.schemas import AnalysisRequest, AnalysisStatusResponse, AnalysisReport
from app.analyzers.orchestrator import (
    AnalysisOrchestrator, create_task, get_task, update_task, _report_cache
)

router = APIRouter()
logger = logging.getLogger(__name__)


async def run_analysis_task(orch: AnalysisOrchestrator):
    """Wrapper to run the async orchestrator in background."""
    try:
        await orch.run()
    except Exception as e:
        logger.error(f"Analysis task {orch.task_id} failed: {e}", exc_info=True)
        update_task(orch.task_id, status="failed", error=str(e), message=f"Error: {e}")


@router.post("/analyze", response_model=AnalysisStatusResponse, status_code=202)
async def start_analysis(body: AnalysisRequest, request: Request):
    task_id = create_task()
    user_id = request.cookies.get("devtrace_uid", "anonymous")

    logger.info(f"Starting analysis for: {body.repo_url} (task={task_id})")

    # Schedule the real analysis task for all repos
    orch = AnalysisOrchestrator(task_id=task_id, repo_url=body.repo_url, user_id=user_id)
    asyncio.create_task(run_analysis_task(orch))

    return AnalysisStatusResponse(
        task_id=task_id,
        status="pending",
        progress=0,
        message="Analysis queued — poll /analyze/{task_id} for updates.",
    )


@router.get("/analyze/{task_id}", response_model=AnalysisStatusResponse)
async def get_status(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(404, f"Task '{task_id}' not found.")
    report = None
    if task["status"] == "completed" and task.get("report"):
        report = AnalysisReport(**task["report"])
    return AnalysisStatusResponse(
        task_id=task_id,
        status=task["status"],
        progress=task["progress"],
        message=task["message"],
        cached=task.get("cached", False),
        report=report,
        error=task.get("error"),
    )


@router.delete("/analyze/{task_id}", status_code=204)
async def cancel(task_id: str):
    if not get_task(task_id):
        raise HTTPException(404, f"Task '{task_id}' not found.")
    update_task(task_id, status="cancelled", message="Cancelled by user.")


@router.websocket("/ws/{task_id}")
async def ws_progress(websocket: WebSocket, task_id: str):
    """Real-time WebSocket progress stream for a running analysis."""
    await websocket.accept()
    try:
        while True:
            task = get_task(task_id)
            if not task:
                await websocket.send_json({"error": "Task not found"})
                break
            msg = {
                "status":   task["status"],
                "progress": task["progress"],
                "message":  task["message"],
                "cached":   task.get("cached", False),
            }
            if task["status"] == "completed":
                msg["report"] = task.get("report")
                await websocket.send_json(msg)
                break
            elif task["status"] == "failed":
                msg["error"] = task.get("error")
                await websocket.send_json(msg)
                break
            await websocket.send_json(msg)
            await asyncio.sleep(0.8)
    except WebSocketDisconnect:
        pass


@router.get("/search")
async def code_search(q: str, top_k: int = 5):
    """Natural language search across the last-analyzed repository."""
    from app.analyzers.ml_engine import search_code
    if not q or len(q.strip()) < 2:
        raise HTTPException(400, "Query must be at least 2 characters.")
    results = search_code(q.strip(), top_k=min(top_k, 20))
    return {
        "query": q,
        "results": [
            {
                "file_path":     r.file_path,
                "function_name": r.function_name,
                "line_number":   r.line_number,
                "score":         r.score,
                "preview":       r.preview,
            }
            for r in results
        ],
    }


@router.get("/cache/stats")
async def cache_stats():
    return {"cached_reports": len(_report_cache), "cache_keys": list(_report_cache.keys())}


@router.delete("/cache")
async def clear_cache():
    _report_cache.clear()
    return {"message": "Cache cleared."}
