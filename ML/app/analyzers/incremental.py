"""
Incremental Analysis Engine
On re-analysis of a repo we've seen before, only re-scan files
that changed since the last run (via git diff). 10x faster on large repos.
"""

import subprocess
import os
from typing import List, Set, Optional, Dict, Any
from app.utils.repo_cloner import RepoFile


class IncrementalEngine:
    """
    Compares the current commit to the previous cached run commit
    and returns only the changed/added files for re-analysis.
    Unchanged files reuse their cached findings.
    """

    def get_changed_files(
        self,
        repo_dir:    str,
        from_sha:    str,
        to_sha:      str = "HEAD",
    ) -> Set[str]:
        """Return relative paths of files changed between two commits."""
        changed: Set[str] = set()
        if not from_sha or from_sha == "unknown":
            return changed   # full scan needed

        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", from_sha, to_sha],
                capture_output=True, text=True, timeout=15,
                cwd=repo_dir,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if line.strip():
                        changed.add(line.strip().replace("\\", "/"))
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass

        return changed

    def split_files(
        self,
        files:         List[RepoFile],
        changed_paths: Set[str],
    ) -> tuple:
        """
        Split a file list into (changed_files, unchanged_files).
        changed_files  → need full re-analysis
        unchanged_files → can reuse cached results
        """
        if not changed_paths:
            # No diff info — full scan
            return files, []

        changed   = []
        unchanged = []
        for f in files:
            normalized = f.relative_path.replace("\\", "/")
            if normalized in changed_paths:
                changed.append(f)
            else:
                unchanged.append(f)

        return changed, unchanged

    def merge_results(
        self,
        new_results:    Dict[str, Any],
        cached_results: Dict[str, Any],
        changed_paths:  Set[str],
    ) -> Dict[str, Any]:
        """
        Merge new analysis results for changed files with cached
        results for unchanged files into a single report.
        """
        if not cached_results:
            return new_results

        merged = dict(new_results)

        # For insights, keep cached ones for unchanged files
        cached_insights = [
            i for i in cached_results.get("actionable_insights", [])
            if i.get("file_path", "").replace("\\", "/") not in changed_paths
            and i.get("file_path", "") != "architecture"
        ]
        new_insights = new_results.get("actionable_insights", [])
        merged["actionable_insights"] = new_insights + cached_insights

        # Recalculate critical count
        merged["critical_issues_count"] = sum(
            1 for i in merged["actionable_insights"]
            if i.get("severity") == "HIGH"
        )

        return merged

    def stats(self, changed: List[RepoFile], total: List[RepoFile]) -> Dict[str, Any]:
        pct = round(len(changed) / max(len(total), 1) * 100, 1)
        return {
            "total_files":   len(total),
            "changed_files": len(changed),
            "reused_files":  len(total) - len(changed),
            "scan_percent":  pct,
        }
