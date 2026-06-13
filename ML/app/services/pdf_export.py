"""
Phase 5 — PDF Report Export
Generates a polished HTML-to-PDF report using reportlab
Falls back to HTML if reportlab is not available
"""

import os
import json
from typing import Dict, Any, List
from datetime import datetime


def _unique_insights(insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique = []
    for item in insights:
        key = (
            str(item.get("title", "")).strip(),
            str(item.get("category", "")).strip(),
            str(item.get("file_path", "")).strip(),
            str(item.get("severity", "")).strip(),
        )
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def generate_pdf(report: Dict[str, Any], output_path: str) -> str:
    """
    Generate a PDF report. Returns the path to the generated file.
    Uses reportlab if available, otherwise generates styled HTML.
    """
    try:
        from reportlab.lib.pagesizes import A4  # type: ignore
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
        from reportlab.lib.units import cm  # type: ignore
        from reportlab.lib import colors  # type: ignore
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,  # type: ignore
                                         Table, TableStyle, HRFlowable)
        from reportlab.lib.enums import TA_CENTER, TA_LEFT  # type: ignore

        _generate_with_reportlab(report, output_path)
    except ImportError:
        # Fallback: HTML
        output_path = output_path.replace(".pdf", ".html")
        _generate_html_report(report, output_path)
    return output_path


def _generate_with_reportlab(report: Dict[str, Any], path: str):
    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
    from reportlab.lib.units import cm  # type: ignore
    from reportlab.lib import colors  # type: ignore
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,  # type: ignore
                                     Table, TableStyle, HRFlowable)
    from reportlab.lib.enums import TA_CENTER  # type: ignore

    PURPLE = colors.HexColor("#6c63ff")
    DARK   = colors.HexColor("#0d1117")
    GRAY   = colors.HexColor("#7c8fa6")
    GREEN  = colors.HexColor("#22d3a0")
    RED    = colors.HexColor("#ff4d6a")

    doc = SimpleDocTemplate(path, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle("title", parent=styles["Title"],
                                  fontSize=24, textColor=PURPLE, spaceAfter=6)
    h2_style    = ParagraphStyle("h2", parent=styles["Heading2"],
                                  fontSize=14, textColor=DARK, spaceBefore=12, spaceAfter=4)
    body_style  = ParagraphStyle("body", parent=styles["Normal"],
                                  fontSize=10, textColor=GRAY, spaceAfter=4)

    # Header
    story.append(Paragraph("DevTrace Analysis Report", title_style))
    story.append(Paragraph(f"Repository: <b>{report.get('repo_name','')}</b>", body_style))
    story.append(Paragraph(f"Analyzed: {report.get('analyzed_at','')[:19].replace('T',' ')}", body_style))
    story.append(Paragraph(f"Commit: {report.get('commit_sha','N/A')}", body_style))
    story.append(HRFlowable(width="100%", color=PURPLE, spaceAfter=12))

    # Core metrics table
    story.append(Paragraph("Core Metrics", h2_style))
    metrics_data = [
        ["Metric", "Value", "Status"],
        ["Quality Score", str(_v(report, "quality_score")), _v(report, "quality_score", "status")],
        ["Security Risks", str(_v(report, "security_risks")), _v(report, "security_risks", "status")],
        ["Maintainability", str(_v(report, "maintainability")), "Stable"],
        ["Tech Debt", str(_v(report, "estimated_tech_debt_hours")), ""],
        ["Total Files", str(report.get("total_files_analyzed", 0)), ""],
        ["Lines of Code", f"{report.get('total_lines_of_code', 0):,}", ""],
        ["Vulnerable Deps", str(report.get("vulnerable_dependencies", 0)), ""],
    ]
    t = Table(metrics_data, colWidths=[6*cm, 4*cm, 4*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), PURPLE),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#e0e0e0")),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING",(0,0), (-1,-1), 8),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph("Executive Summary", h2_style))
    story.append(Paragraph(report.get("executive_summary", "No executive summary available."), body_style))
    roadmap = report.get("recommended_roadmap", [])
    if roadmap:
        story.append(Paragraph("Recommended Roadmap", body_style))
        for item in roadmap:
            story.append(Paragraph(f"• {item}", body_style))
    story.append(Spacer(1, 0.4*cm))

    # AI suggestion highlights
    all_insights = _unique_insights(report.get("actionable_insights", []))
    ai_suggestions = [i for i in all_insights if i.get("ai_fix_available")]
    if ai_suggestions:
        story.append(Paragraph("Top AI Suggestions", h2_style))
        ai_title_style = ParagraphStyle("aititle", parent=styles["Heading3"], fontSize=11, textColor=PURPLE, spaceAfter=2)
        ai_body_style = ParagraphStyle("aibody", parent=styles["BodyText"], fontSize=9, textColor=GRAY, leftIndent=12, spaceAfter=6)
        for ins in ai_suggestions[:5]:
            story.append(Paragraph(f"• {ins.get('title','No title')}", ai_title_style))
            fix_text = ins.get('suggested_fix') or ins.get('description', '')
            story.append(Paragraph(fix_text, ai_body_style))
        story.append(Spacer(1, 0.5*cm))

    # Top insights
    story.append(Paragraph("Top Actionable Insights", h2_style))
    insights = all_insights[:10]
    if insights:
        ins_data = [["Severity", "Category", "Title", "File"]]
        for ins in insights:
            ins_data.append([
                ins.get("severity",""),
                ins.get("category",""),
                ins.get("title","")[:50],
                ins.get("file_path","")[:30],
            ])
        ti = Table(ins_data, colWidths=[2.5*cm, 3*cm, 7*cm, 4*cm])
        sev_colors = {"HIGH": RED, "MEDIUM": colors.HexColor("#fbbf24"), "LOW": colors.HexColor("#38bdf8")}
        style_cmds = [
            ("BACKGROUND",  (0,0), (-1,0), PURPLE),
            ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 8),
            ("GRID",        (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0e0")),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING",  (0,0), (-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ]
        for i, ins in enumerate(insights, 1):
            c = sev_colors.get(ins.get("severity",""), GRAY)
            style_cmds.append(("TEXTCOLOR", (0,i), (0,i), c))
            style_cmds.append(("FONTNAME",  (0,i), (0,i), "Helvetica-Bold"))
        ti.setStyle(TableStyle(style_cmds))
        story.append(ti)

    story.append(Spacer(1, 0.5*cm))

    # Architecture summary
    arch = report.get("architecture", {})
    if arch:
        story.append(Paragraph("Architecture", h2_style))
        story.append(Paragraph(arch.get("summary",""), body_style))
        arch_data = [
            ["Domain-Driven Score", f"{arch.get('domain_driven_score',0)}%"],
            ["Circular Dependencies", str(len(arch.get("circular_dependencies",[])))],
            ["Total Modules", str(arch.get("total_modules",0))],
            ["Coupling Score", f"{arch.get('coupling_score',0)}%"],
            ["Cohesion Score", f"{arch.get('cohesion_score',0)}%"],
        ]
        ta = Table(arch_data, colWidths=[7*cm, 4*cm])
        ta.setStyle(TableStyle([
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0e0")),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(ta)

    lang = report.get("language_breakdown", {})
    if lang:
        story.append(Paragraph("Language Breakdown", h2_style))
        lang_items = [["Language", "Percent"]]
        for name, pct in sorted(lang.items(), key=lambda item: item[1], reverse=True):
            lang_items.append([name, f"{pct:.1f}%"])
        lang_table = Table(lang_items, colWidths=[7*cm, 4*cm])
        lang_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), PURPLE),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), 0.2, colors.HexColor("#e0e0e0")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(lang_table)
        story.append(Spacer(1, 0.3*cm))

    halstead = report.get("halstead_metrics", {})
    if halstead:
        story.append(Paragraph("Halstead Metrics", h2_style))
        hald_items = [["Metric", "Value"]]
        for key, value in sorted(halstead.items()):
            hald_items.append([key.replace("_"," ").title(), str(value)])
        hald_table = Table(hald_items, colWidths=[7*cm, 4*cm])
        hald_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), PURPLE),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), 0.2, colors.HexColor("#e0e0e0")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(hald_table)
        story.append(Spacer(1, 0.3*cm))

    coverage = report.get("test_coverage", {})
    if coverage:
        story.append(Paragraph("Test Coverage", h2_style))
        cov_items = [["Metric", "Value"]]
        for key in ["overall", "lines_tested", "lines_untested", "tests", "frameworks"]:
            if key in coverage:
                cov_items.append([key.replace("_"," ").title(), str(coverage.get(key))])
        cov_table = Table(cov_items, colWidths=[7*cm, 4*cm])
        cov_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), PURPLE),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), 0.2, colors.HexColor("#e0e0e0")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(cov_table)
        story.append(Spacer(1, 0.3*cm))

    ml_summary = report.get("ml_summary", {})
    if ml_summary or report.get("models_used"):
        story.append(Paragraph("ML Engine Summary", h2_style))
        for key, value in ml_summary.items():
            story.append(Paragraph(f"{key.replace('_',' ').title()}: {value}", body_style))
        if report.get("models_used"):
            story.append(Paragraph(f"Models Used: {', '.join(report.get('models_used', []))}", body_style))
        story.append(Spacer(1, 0.3*cm))

    js_issues = report.get("js_issues", [])
    if js_issues:
        story.append(Paragraph("JavaScript / TypeScript Issues", h2_style))
        js_items = [["Severity", "Title", "File"]]
        for issue in js_issues[:8]:
            js_items.append([issue.get("severity",""), issue.get("title", issue.get("description",""))[:50], issue.get("file_path","")[:30]])
        js_table = Table(js_items, colWidths=[3*cm, 7*cm, 5*cm])
        js_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), PURPLE),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), 0.2, colors.HexColor("#e0e0e0")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(js_table)
        story.append(Spacer(1, 0.3*cm))

    module_graph = report.get("module_graph", {})
    if module_graph:
        story.append(Paragraph("Module Graph Summary", h2_style))
        story.append(Paragraph(f"Nodes: {len(module_graph.get('nodes', []))} · Edges: {len(module_graph.get('edges', []))}", body_style))
        story.append(Spacer(1, 0.3*cm))

    author_stats = report.get("author_stats", [])
    if author_stats:
        story.append(Paragraph("Author Stats", h2_style))
        author_items = [["Author", "Contributions"]]
        for author in author_stats[:8]:
            author_items.append([author.get("name", author.get("author",""))[:30], str(author.get("commits", author.get("contributions","")))])
        author_table = Table(author_items, colWidths=[7*cm, 4*cm])
        author_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), PURPLE),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), 0.2, colors.HexColor("#e0e0e0")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(author_table)
        story.append(Spacer(1, 0.3*cm))

    incremental = report.get("incremental_stats", {})
    if incremental:
        story.append(Paragraph("Incremental Analysis", h2_style))
        for key, value in incremental.items():
            story.append(Paragraph(f"{key.replace('_',' ').title()}: {value}", body_style))

    # Footer
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", color=PURPLE))
    story.append(Paragraph("Generated by DevTrace — AI Code Intelligence Platform", 
                             ParagraphStyle("footer", parent=styles["Normal"],
                                             fontSize=8, textColor=GRAY, alignment=TA_CENTER)))
    doc.build(story)


def _generate_html_report(report: Dict[str, Any], path: str):
    """Fallback styled HTML report."""
    quality = _v(report, "quality_score")
    security = _v(report, "security_risks")
    maint = _v(report, "maintainability")
    debt = _v(report, "estimated_tech_debt_hours")
    insights = _unique_insights(report.get("actionable_insights", []))[:10]
    arch = report.get("architecture", {})
    trend = report.get("code_health_trend", {})
    heatmap = sorted(report.get("complexity_heatmap", []), key=lambda x: x.get("score", 0), reverse=True)[:10]
    lang = report.get("language_breakdown", {})
    halstead = report.get("halstead_metrics", {})
    coverage = report.get("test_coverage", {})
    ml_summary = report.get("ml_summary", {})
    models_used = report.get("models_used", [])
    js_issues = report.get("js_issues", [])[:10]
    author_stats = report.get("author_stats", [])[:8]

    repo_name = report.get("repo_name", "Your Project")
    risk_outlook = report.get("risk_outlook", "3 critical issues identified")
    primary_focus = report.get("primary_focus", "Code quality assessment")
    critical_items = report.get("critical_issues_count", 0)
    executive_summary = report.get("executive_summary", "Your project has been analyzed for code quality, security vulnerabilities, and maintainability. The analysis found several areas for improvement, primarily focused on security hardening.")
    roadmap_html = "".join(f"<li>{item}</li>" for item in report.get("recommended_roadmap", []))

    ins_rows = ""
    for i in insights:
        sev = i.get("severity", "")
        colors_map = {"HIGH": "#ff4d6a", "MEDIUM": "#fbbf24", "LOW": "#38bdf8"}
        c = colors_map.get(sev, "#888")
        ins_rows += f"""
        <div class=\"insight-item\">
          <div class=\"insight-sev sev-high\">{sev} · {i.get('category','').upper()}</div>
          <div class=\"insight-title\">{i.get('title','')}</div>
          <div class=\"insight-desc\">{i.get('description', i.get('title',''))}</div>
          <div class=\"insight-file\"><span>← {i.get('file_path','')}</span></div>
        </div>"""

    heat_rows = ""
    for item in heatmap:
        heat_rows += f"""
        <tr>
          <td>{item.get('module','')}</td>
          <td>{item.get('score','')}</td>
          <td>{item.get('issues','')}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
<meta charset=\"UTF-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
<title>{repo_name} — DevTrace Report</title>
<link href=\"https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap\" rel=\"stylesheet\">
<style>
  :root {
    --bg: #0d0f1a;
    --bg2: #12151f;
    --bg3: #181b28;
    --bg4: #1e2130;
    --border: #252838;
    --border2: #2e3248;
    --text: #e2e4f0;
    --text2: #8b90a8;
    --text3: #555a72;
    --accent: #7c6ef5;
    --accent2: #6457e8;
    --green: #22d3a0;
    --red: #f43f5e;
    --yellow: #eab308;
    --cyan: #06b6d4;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); font-size: 13px; min-height: 100vh; }
  .nav { position: sticky; top: 0; z-index: 100; background: var(--bg2); border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 16px; padding: 0 20px; height: 48px; }
  .nav-logo { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 15px; }
  .nav-logo-icon { width: 28px; height: 28px; background: var(--accent); border-radius: 6px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 11px; }
  .nav-repo { color: var(--text2); font-size: 13px; font-family: 'JetBrains Mono', monospace; }
  .nav-spacer { flex: 1; }
  .nav-btn { display: flex; align-items: center; gap: 6px; padding: 5px 12px; border-radius: 6px; border: 1px solid var(--border2); background: transparent; color: var(--text); cursor: pointer; font-size: 12px; font-family: inherit; transition: all .15s; }
  .nav-btn:hover { background: var(--bg4); border-color: var(--accent); }
  .page { max-width: 1500px; margin: 0 auto; padding: 0 20px 40px; }
  .risk-banner { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; background: var(--border); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; margin: 20px 0 0; }
  .risk-cell { background: var(--bg2); padding: 16px 20px; }
  .risk-label { font-size: 10px; text-transform: uppercase; letter-spacing: .1em; color: var(--text3); margin-bottom: 6px; }
  .risk-value { font-weight: 700; font-size: 15px; }
  .section-label { font-size: 10px; text-transform: uppercase; letter-spacing: .12em; color: var(--text3); margin: 28px 0 12px; padding-bottom: 6px; border-bottom: 1px solid var(--border); }
  .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
  .metric-card { background: var(--bg2); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; position: relative; overflow: hidden; }
  .metric-card-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
  .metric-icon { width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; font-size: 14px; }
  .metric-tag { font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 20px; font-family: 'JetBrains Mono', monospace; }
  .tag-red { background: rgba(244,63,94,.15); color: var(--red); }
  .tag-green { background: rgba(34,211,160,.12); color: var(--green); }
  .tag-yellow { background: rgba(234,179,8,.12); color: var(--yellow); }
  .metric-label { font-size: 11px; color: var(--text2); margin-bottom: 6px; }
  .metric-value { font-size: 32px; font-weight: 800; line-height: 1; }
  .val-green { color: var(--green); }
  .val-red { color: var(--red); }
  .val-cyan { color: var(--cyan); }
  .val-yellow { color: var(--yellow); }
  .chart-card { background: var(--bg2); border: 1px solid var(--border); border-radius: 10px; padding: 20px; }
  .chart-title { font-weight: 700; font-size: 14px; margin-bottom: 16px; }
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .insights-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
  .critical-badge { font-size: 11px; font-weight: 700; color: var(--red); background: rgba(244,63,94,.1); padding: 3px 10px; border-radius: 20px; }
  .insight-item { background: var(--bg3); border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px; margin-bottom: 10px; position: relative; }
  .insight-sev { display: inline-flex; align-items: center; gap: 5px; font-size: 9px; font-weight: 800; letter-spacing: .08em; padding: 2px 7px; border-radius: 3px; margin-bottom: 8px; }
  .sev-high { background: rgba(244,63,94,.2); color: var(--red); }
  .insight-title { font-weight: 700; font-size: 13px; margin-bottom: 4px; }
  .insight-desc { font-size: 11px; color: var(--text2); margin-bottom: 6px; }
  .insight-file { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--text3); display: flex; align-items: center; gap: 8px; }
  .mt-12 { margin-top: 12px; }
  .mt-16 { margin-top: 16px; }
  .fw700 { font-weight: 700; }
  .mono { font-family: 'JetBrains Mono', monospace; }
</style>
</head>
<body>
<nav class="nav">
  <div class="nav-logo">
    <div class="nav-logo-icon">YR</div>
    Your Report
  </div>
  <span class="nav-repo">{repo_name}</span>
  <div class="nav-spacer"></div>
  <button class="nav-btn">📊 Dashboard</button>
  <button class="nav-btn">↓ Export</button>
</nav>
<div class="page">
  <div class="risk-banner">
    <div class="risk-cell">
      <div class="risk-label">Risk Outlook</div>
      <div class="risk-value">{risk_outlook}</div>
    </div>
    <div class="risk-cell">
      <div class="risk-label">Primary Focus</div>
      <div class="risk-value">{primary_focus}</div>
    </div>
  </div>
  <div class="section-label">Core Metrics</div>
  <div class="metrics-grid">
    <div class="metric-card">
      <div class="metric-card-top">
        <div class="metric-icon">👁</div>
        <span class="metric-tag tag-green">Good</span>
      </div>
      <div class="metric-label">Quality Score</div>
      <div class="metric-value val-green">{quality}</div>
    </div>
    <div class="metric-card">
      <div class="metric-card-top">
        <div class="metric-icon">⚠️</div>
        <span class="metric-tag tag-red">Issues found</span>
      </div>
      <div class="metric-label">Security Risks</div>
      <div class="metric-value val-red">{security}</div>
    </div>
    <div class="metric-card">
      <div class="metric-card-top">
        <div class="metric-icon">&lt;/&gt;</div>
        <span class="metric-tag tag-green">Stable</span>
      </div>
      <div class="metric-label">Maintainability</div>
      <div class="metric-value val-cyan">{maint}</div>
    </div>
    <div class="metric-card">
      <div class="metric-card-top">
        <div class="metric-icon">〜</div>
        <span class="metric-tag tag-yellow">Medium</span>
      </div>
      <div class="metric-label">Est. Tech Debt</div>
      <div class="metric-value val-yellow">{debt}</div>
    </div>
  </div>
  <div class="section-label">Analysis</div>
  <div class="two-col">
    <div class="chart-card">
      <div class="insights-header">
        <div class="fw700" style="font-size:14px">Key Findings</div>
        <span class="critical-badge">{critical_items} critical items found</span>
      </div>
      {ins_rows if ins_rows else '<div class="insight-item"><div class="insight-title">No insights available.</div></div>'}
    </div>
    <div class="chart-card">
      <div class="chart-title">Analysis Summary</div>
      <div style="padding:20px 0;">
        <div style="margin-bottom:16px;">
          <div style="font-size:14px;font-weight:700;margin-bottom:8px;">Project Overview</div>
          <div style="color:var(--text2);font-size:12px;line-height:1.5;">{executive_summary}</div>
        </div>
        {f'<div><div style="font-size:14px;font-weight:700;margin-bottom:8px;">Recommendations</div><ul style="color:var(--text2);font-size:12px;line-height:1.6;margin:0;padding-left:16px;">{roadmap_html}</ul></div>' if roadmap_html else ''}
      </div>
    </div>
  </div>
</div>
</body>
</html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def _v(report, key, sub="value"):
    v = report.get(key, {})
    if isinstance(v, dict):
        return v.get(sub, "—")
    return str(v)
