"""
Phase 5 — Export Routes
GET  /api/v1/export/{run_id}/pdf   → Download PDF report
GET  /api/v1/export/{run_id}/html  → Download HTML report
GET  /api/v1/export/{run_id}/json  → Download JSON report
"""
import os
import json
import tempfile
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from app.db.database import get_run
from app.services.pdf_export import generate_pdf

router = APIRouter()


@router.get("/export/{run_id}/pdf")
async def export_pdf(run_id: int):
    run = get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    report = run.get("full_report", run)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_path = tmp_file.name
    out = generate_pdf(report, tmp_path)
    ext = "pdf" if out.endswith(".pdf") else "html"
    media = "application/pdf" if ext == "pdf" else "text/html"
    repo = report.get("repo_name", "report").replace("/", "-")
    return FileResponse(out, media_type=media,
                        filename=f"devtrace-{repo}.{ext}")


@router.get("/export/{run_id}/html")
async def export_html(run_id: int):
    run = get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    report = run.get("full_report", run)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
        tmp_path = tmp_file.name
    # Force HTML
    from app.services.pdf_export import _generate_html_report
    _generate_html_report(report, tmp_path)
    repo = report.get("repo_name", "report").replace("/", "-")
    return FileResponse(tmp_path, media_type="text/html",
                        filename=f"devtrace-{repo}.html")


@router.get("/export/{run_id}/json")
async def export_json(run_id: int):
    run = get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return JSONResponse(run.get("full_report", run))
