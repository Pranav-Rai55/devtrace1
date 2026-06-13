"""
Test Coverage Mapper
Estimates which source modules have test coverage WITHOUT running tests.
Maps test files to source files using naming conventions and import analysis.
"""

import ast
import re
import os
from typing import List, Dict, Set, Tuple, Any
from dataclasses import dataclass, field
from app.utils.repo_cloner import RepoFile


@dataclass
class CoverageEstimate:
    module:            str
    source_file:       str
    has_tests:         bool
    test_files:        List[str]
    test_count:        int    # Number of test functions found
    coverage_estimate: float  # 0–100 (structural, not line-level)
    untested_functions: List[str]
    risk_level:        str    # HIGH / MEDIUM / LOW (based on complexity + no coverage)


@dataclass
class CoverageReport:
    total_source_files:  int
    tested_files:        int
    untested_files:      int
    overall_coverage:    float
    test_framework:      str
    total_test_count:    int
    uncovered_modules:   List[CoverageEstimate]
    well_tested_modules: List[CoverageEstimate]
    hotspot_files:       List[str]   # Complex + untested = highest risk


class TestCoverageMapper:
    """
    Maps test files to source files via:
    1. Name matching (test_auth.py → auth.py, auth.test.ts → auth.ts)
    2. Import analysis (test files that import source modules)
    3. Directory convention (tests/, __tests__/, spec/)
    """

    TEST_PATTERNS = [
        r'test[_-]',
        r'[_-]test',
        r'\.test\.',
        r'\.spec\.',
        r'_spec\.',
        r'spec_',
    ]
    TEST_DIRS = {"tests", "test", "__tests__", "spec", "specs", "testing"}

    def analyze(self, files: List[RepoFile]) -> CoverageReport:
        source_files = [f for f in files if self._is_source(f)]
        test_files   = [f for f in files if self._is_test(f)]

        framework = self._detect_framework(test_files, files)
        test_map  = self._build_test_map(source_files, test_files)

        estimates: List[CoverageEstimate] = []
        total_tests = 0

        for src in source_files:
            tests = test_map.get(src.relative_path, [])
            test_count = self._count_tests(tests)
            total_tests += test_count
            untested_fns = self._find_untested_functions(src, tests)
            cov = self._estimate_coverage(src, tests, test_count)
            risk = self._risk_level(src, cov)

            estimates.append(CoverageEstimate(
                module=self._module_name(src.relative_path),
                source_file=src.relative_path,
                has_tests=len(tests) > 0,
                test_files=[t.relative_path for t in tests],
                test_count=test_count,
                coverage_estimate=cov,
                untested_functions=untested_fns[:8],
                risk_level=risk,
            ))

        tested   = [e for e in estimates if e.has_tests]
        untested = [e for e in estimates if not e.has_tests]

        overall = (
            sum(e.coverage_estimate for e in estimates) / len(estimates)
            if estimates else 0.0
        )

        # Hotspots: complex source files with zero coverage
        hotspots = [
            e.source_file for e in estimates
            if not e.has_tests and e.risk_level == "HIGH"
        ]

        untested.sort(key=lambda e: (
            {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[e.risk_level]
        ))

        return CoverageReport(
            total_source_files=len(source_files),
            tested_files=len(tested),
            untested_files=len(untested),
            overall_coverage=round(overall, 1),
            test_framework=framework,
            total_test_count=total_tests,
            uncovered_modules=untested[:15],
            well_tested_modules=sorted(tested, key=lambda e: -e.coverage_estimate)[:5],
            hotspot_files=hotspots[:10],
        )

    # ── Helpers ────────────────────────────────────────────────────

    def _is_test(self, f: RepoFile) -> bool:
        path = f.relative_path.replace("\\", "/").lower()
        parts = path.split("/")
        # Check if in a test directory
        if any(p in self.TEST_DIRS for p in parts):
            return True
        filename = parts[-1]
        return any(re.search(p, filename) for p in self.TEST_PATTERNS)

    def _is_source(self, f: RepoFile) -> bool:
        if self._is_test(f):
            return False
        return f.language in (
            "Python", "JavaScript", "TypeScript",
            "Java", "Go", "Ruby", "PHP",
        )

    def _detect_framework(self, test_files: List[RepoFile],
                           all_files: List[RepoFile]) -> str:
        all_content = " ".join(f.content[:500] for f in test_files[:20])
        if "import pytest" in all_content or "from pytest" in all_content:
            return "pytest"
        if "import unittest" in all_content:
            return "unittest"
        if "describe(" in all_content and "it(" in all_content:
            return "jest/mocha"
        if "expect(" in all_content:
            return "jest"
        if "@Test" in all_content:
            return "JUnit"
        if "func Test" in all_content:
            return "Go testing"
        # Check requirements/package.json
        for f in all_files:
            if "requirements" in f.relative_path and "pytest" in f.content:
                return "pytest"
            if "package.json" in f.relative_path and "jest" in f.content:
                return "jest"
        return "unknown"

    def _build_test_map(
        self,
        sources: List[RepoFile],
        tests: List[RepoFile],
    ) -> Dict[str, List[RepoFile]]:
        """Map each source file to the test files that cover it."""
        mapping: Dict[str, List[RepoFile]] = {s.relative_path: [] for s in sources}

        # Build a lookup by base name
        source_by_stem: Dict[str, RepoFile] = {}
        for s in sources:
            stem = self._stem(s.relative_path)
            source_by_stem[stem] = s

        for test in tests:
            test_stem = self._stem(test.relative_path)
            # Remove test prefix/suffix
            clean = re.sub(r'^test[_-]|[_-]test$|[_-]spec$|^spec[_-]', "", test_stem)

            # Match by name
            for stem, src in source_by_stem.items():
                if clean == stem or clean in stem or stem in clean:
                    mapping[src.relative_path].append(test)
                    break
            else:
                # Match by import analysis
                for src in sources:
                    if self._test_imports_source(test, src):
                        mapping[src.relative_path].append(test)

        return mapping

    def _stem(self, path: str) -> str:
        base = os.path.splitext(os.path.basename(path))[0]
        return re.sub(r'^test[_-]|[_-]test$|[_-]spec$', "", base.lower())

    def _test_imports_source(self, test: RepoFile, src: RepoFile) -> bool:
        src_stem = os.path.splitext(os.path.basename(src.relative_path))[0].lower()
        imports  = re.findall(r'(?:import|from)\s+[\w./]+', test.content[:2000])
        return any(src_stem in imp.lower() for imp in imports)

    def _count_tests(self, test_files: List[RepoFile]) -> int:
        count = 0
        for tf in test_files:
            count += len(re.findall(
                r'def\s+test_\w+|it\s*\(["\']|test\s*\(["\']|func\s+Test\w+',
                tf.content,
            ))
        return count

    def _find_untested_functions(
        self,
        src: RepoFile,
        tests: List[RepoFile],
    ) -> List[str]:
        """Return public function names that don't appear in any test file."""
        if src.language != "Python":
            return []
        try:
            tree = ast.parse(src.content)
        except SyntaxError:
            return []

        public_fns = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not node.name.startswith("_")
        ]

        test_content = " ".join(tf.content for tf in tests)
        return [fn for fn in public_fns if fn not in test_content]

    def _estimate_coverage(
        self,
        src: RepoFile,
        tests: List[RepoFile],
        test_count: int,
    ) -> float:
        if not tests:
            return 0.0

        # Rough heuristic: test count vs public functions
        try:
            tree = ast.parse(src.content)
            fn_count = sum(
                1 for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
        except SyntaxError:
            fn_count = max(src.line_count // 15, 1)

        if fn_count == 0:
            return 80.0

        ratio = min(test_count / fn_count, 1.0)
        return round(ratio * 85 + 10, 1)   # 10–95% range

    def _risk_level(self, src: RepoFile, coverage: float) -> str:
        lines = src.line_count
        if coverage < 10 and lines > 100:
            return "HIGH"
        if coverage < 30 and lines > 50:
            return "MEDIUM"
        return "LOW"

    def _module_name(self, path: str) -> str:
        parts = path.replace("\\", "/").split("/")
        if len(parts) >= 2:
            return parts[-2].capitalize() + "/" + parts[-1]
        return path
