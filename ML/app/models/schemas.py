"""
DevTrace — Pydantic Schemas (Ultimate Final)
"""

import os
from pathlib import Path
from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Any
from enum import Enum


class SeverityLevel(str, Enum):
    HIGH   = "HIGH"
    MEDIUM = "MEDIUM"
    LOW    = "LOW"


class InsightCategory(str, Enum):
    SECURITY        = "SECURITY"
    PERFORMANCE     = "PERFORMANCE"
    QUALITY         = "QUALITY"
    MAINTAINABILITY = "MAINTAINABILITY"


class AnalysisRequest(BaseModel):
    repo_url: str

    @field_validator("repo_url")
    @classmethod
    def validate(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Repository input cannot be empty.")
        if v.startswith(("http://", "https://", "git@")):
            return v
        if v.startswith("github.com/"):
            return "https://" + v

        local_path = Path(v).expanduser()
        if local_path.exists():
            return str(local_path.resolve())

        if os.path.exists(v):
            return str(Path(v).resolve())

        if "/" in v and not v.startswith("http"):
            return f"https://github.com/{v}"
        raise ValueError("Use a GitHub repo, git URL, or an existing local repository path.")


class MetricCard(BaseModel):
    value:  Any
    delta:  Optional[str] = None
    status: Optional[str] = None


class ComplexityHeatmapEntry(BaseModel):
    module: str
    score:  float
    issues: int


class CodeHealthTrend(BaseModel):
    cyclomatic_complexity:   float
    duplication_rate:        float
    documentation_coverage:  float
    commit_history:          List[Dict[str, Any]] = []


class ActionableInsight(BaseModel):
    severity:          SeverityLevel
    category:          InsightCategory
    title:             str
    description:       str
    file_path:         str
    line_number:       Optional[int] = None
    ai_fix_available:  bool = True
    suggested_fix:     Optional[str] = None


class ArchitectureSummary(BaseModel):
    summary:               str
    domain_driven_score:   float
    circular_dependencies: List[str] = []
    total_modules:         int
    cross_domain_deps:     int
    coupling_score:        float = 0.0
    cohesion_score:        float = 0.0
    layer_violations:      List[str] = []
    largest_component:     str = ""
    orphan_modules:        List[str] = []


class ModuleGraph(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class AnalysisReport(BaseModel):
    # Meta
    repo_url:             str
    repo_name:            str
    repo_source:          str = "remote"
    analyzed_at:          str
    commit_sha:           str = ""
    run_id:               Optional[int] = None
    cached:               bool = False
    total_files_analyzed: int
    total_lines_of_code:  int
    executive_summary:    str = ""
    recommended_roadmap:  List[str] = []

    # Core metric cards
    quality_score:             MetricCard
    security_risks:            MetricCard
    maintainability:           MetricCard
    estimated_tech_debt_hours: MetricCard

    # Charts
    complexity_heatmap: List[ComplexityHeatmapEntry]
    code_health_trend:  CodeHealthTrend

    # Insights
    actionable_insights:   List[ActionableInsight]
    critical_issues_count: int

    # Architecture
    architecture: ArchitectureSummary
    module_graph: ModuleGraph

    # Code stats
    language_breakdown:  Dict[str, float] = {}
    halstead_metrics:    Dict[str, float] = {}
    total_code_smells:   int = 0
    god_class_count:     int = 0
    avg_function_length: float = 0.0
    dead_code_count:     int = 0
    vulnerable_dependencies: int = 0

    # ML Engine (7 models)
    ml_summary:           Dict[str, Any] = {}
    clone_pairs:          List[Dict[str, Any]] = []
    bug_risks:            List[Dict[str, Any]] = []
    missing_type_hints:   List[Dict[str, Any]] = []
    generated_docstrings: List[Dict[str, Any]] = []
    ml_complexities:      List[Dict[str, Any]] = []
    vuln_classifications: List[Dict[str, Any]] = []
    models_used:          List[str] = []

    # New: JS/TS, Coverage, Blame, Incremental
    js_issues:         List[Dict[str, Any]] = []
    test_coverage:     Dict[str, Any] = {}
    author_stats:      List[Dict[str, Any]] = []
    git_hotspots:      List[Dict[str, Any]] = []
    incremental_stats: Dict[str, Any] = {}


class AnalysisStatusResponse(BaseModel):
    task_id:  str
    status:   str
    progress: int
    message:  str
    cached:   bool = False
    report:   Optional[AnalysisReport] = None
    error:    Optional[str] = None
