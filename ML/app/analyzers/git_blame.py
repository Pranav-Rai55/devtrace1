"""
Git Blame Analyzer
Enriches every finding with author + commit metadata.
Shows who introduced each issue and when, enabling accountability.
"""

import re
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class BlameEntry:
    commit_sha:   str
    author_name:  str
    author_email: str
    commit_date:  str
    line_number:  int
    summary:      str     # First line of commit message


@dataclass
class AuthorStats:
    name:           str
    email:          str
    total_issues:   int
    high_issues:    int
    files_touched:  int
    first_commit:   str
    last_commit:    str


class GitBlameAnalyzer:
    """
    Runs git blame on files that have findings, attaches author info
    to each issue, and produces per-author accountability stats.
    """

    def __init__(self, repo_dir: str):
        self.repo_dir = repo_dir
        self._blame_cache: Dict[str, Dict[int, BlameEntry]] = {}

    def enrich_insights(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add blame metadata to a list of insight dicts."""
        enriched = []
        for insight in insights:
            file_path = insight.get("file_path", "")
            line = insight.get("line_number") or 0
            if file_path and line > 0 and file_path != "architecture":
                blame = self._get_blame(file_path, line)
                if blame:
                    insight = dict(insight)
                    insight["blame"] = {
                        "author":      blame.author_name,
                        "email":       blame.author_email,
                        "commit":      blame.commit_sha[:8],
                        "date":        blame.commit_date,
                        "summary":     blame.summary[:60],
                    }
            enriched.append(insight)
        return enriched

    def author_stats(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aggregate per-author issue counts from enriched insights."""
        stats: Dict[str, AuthorStats] = {}
        for i in insights:
            blame = i.get("blame")
            if not blame:
                continue
            name  = blame.get("author", "Unknown")
            email = blame.get("email", "")
            key   = email or name
            if key not in stats:
                stats[key] = AuthorStats(
                    name=name, email=email,
                    total_issues=0, high_issues=0, files_touched=0,
                    first_commit=blame.get("date", ""),
                    last_commit=blame.get("date", ""),
                )
            s = stats[key]
            s.total_issues += 1
            if i.get("severity") == "HIGH":
                s.high_issues += 1
            fp = i.get("file_path", "")
            if fp:
                s.files_touched += 1
            d = blame.get("date", "")
            if d and d < s.first_commit:
                s.first_commit = d
            if d and d > s.last_commit:
                s.last_commit = d

        result = sorted(stats.values(), key=lambda x: -(x.high_issues * 10 + x.total_issues))
        return [
            {
                "name":          s.name,
                "email":         s.email,
                "total_issues":  s.total_issues,
                "high_issues":   s.high_issues,
                "first_commit":  s.first_commit,
                "last_commit":   s.last_commit,
            }
            for s in result[:10]
        ]

    def recent_hotspots(self) -> List[Dict[str, Any]]:
        """
        Find files changed most recently with most commits — churn hotspots.
        High churn + issues = highest priority for refactoring.
        """
        hotspots = []
        try:
            result = subprocess.run(
                ["git", "log", "--format=%H %ae %ad %s", "--date=short",
                 "--name-only", "--diff-filter=M", "-n", "100"],
                capture_output=True, text=True, timeout=15,
                cwd=self.repo_dir,
            )
            if not result.stdout:
                return hotspots

            file_counts: Dict[str, int] = {}
            file_authors: Dict[str, set] = {}
            current_author = ""
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split(" ", 3)
                if len(parts) >= 3 and len(parts[0]) == 40:
                    current_author = parts[1] if len(parts) > 1 else ""
                elif "." in line and "/" in line:
                    file_counts[line] = file_counts.get(line, 0) + 1
                    if line not in file_authors:
                        file_authors[line] = set()
                    if current_author:
                        file_authors[line].add(current_author)

            for filepath, count in sorted(file_counts.items(), key=lambda x: -x[1])[:10]:
                hotspots.append({
                    "file":         filepath,
                    "commit_count": count,
                    "unique_authors": len(file_authors.get(filepath, set())),
                })
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass

        return hotspots

    # ── Private ────────────────────────────────────────────────────

    def _get_blame(self, relative_path: str, line: int) -> Optional[BlameEntry]:
        """Run git blame once per file and cache all line entries."""
        if relative_path not in self._blame_cache:
            self._populate_file_blame(relative_path)
        return self._blame_cache.get(relative_path, {}).get(line)

    def _populate_file_blame(self, relative_path: str):
        file_cache: Dict[int, BlameEntry] = {}
        try:
            result = subprocess.run(
                ["git", "blame", "-p", "--", relative_path],
                capture_output=True, text=True, timeout=15,
                cwd=self.repo_dir,
            )
            if result.returncode != 0 or not result.stdout:
                self._blame_cache[relative_path] = file_cache
                return

            current_sha = None
            current_data: Dict[str, str] = {}
            current_line = 0
            for ln in result.stdout.splitlines():
                if ln.startswith("\t"):
                    if current_sha is not None and current_line:
                        blame = self._create_blame_entry(current_sha, current_data, current_line)
                        if blame:
                            file_cache[current_line] = blame
                        current_line += 1
                    current_data = {}
                else:
                    parts = ln.split(" ", 3)
                    if len(parts) >= 3 and len(parts[0]) == 40:
                        current_sha = parts[0]
                        try:
                            current_line = int(parts[2])
                        except ValueError:
                            current_line = 0
                    elif " " in ln:
                        key, _, val = ln.partition(" ")
                        current_data[key] = val
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass
        self._blame_cache[relative_path] = file_cache

    def _create_blame_entry(self, sha: str, data: Dict[str, str], line: int) -> Optional[BlameEntry]:
        try:
            return BlameEntry(
                commit_sha=sha,
                author_name=data.get("author", "Unknown"),
                author_email=data.get("author-mail", "").strip("<>"),
                commit_date=data.get("author-time", ""),
                line_number=line,
                summary=data.get("summary", ""),
            )
        except Exception:
            return None

    def _parse_porcelain(self, output: str, line: int) -> Optional[BlameEntry]:
        """Parse git blame --porcelain output."""
        try:
            lines = output.splitlines()
            sha = lines[0].split()[0] if lines else "unknown"
            data: Dict[str, str] = {}
            for l in lines[1:]:
                if " " in l:
                    k, _, v = l.partition(" ")
                    data[k] = v
            return BlameEntry(
                commit_sha=sha,
                author_name=data.get("author", "Unknown"),
                author_email=data.get("author-mail", "").strip("<>"),
                commit_date=data.get("author-time", ""),
                line_number=line,
                summary=data.get("summary", ""),
            )
        except Exception:
            return None
