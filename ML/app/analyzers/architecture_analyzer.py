"""
Architecture Analyzer — Advanced Edition
Builds weighted module dependency graph, detects circular dependencies,
layering violations, coupling metrics, and cohesion scores
"""

import ast
import re
from typing import List, Dict, Set, Tuple, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

try:
    import networkx as nx  # type: ignore
    NX_AVAILABLE = True
except ImportError:
    NX_AVAILABLE = False

from app.utils.repo_cloner import RepoFile


@dataclass
class ArchitectureResult:
    summary: str
    total_modules: int
    circular_dependencies: List[str]
    cross_domain_deps: int
    domain_driven_score: float
    coupling_score: float        # 0-100, lower = better (afferent/efferent coupling)
    cohesion_score: float        # 0-100, higher = better
    layer_violations: List[str]  # e.g. "UI → Database (violation)"
    largest_component: str       # Most connected module
    orphan_modules: List[str]    # Modules with no dependencies
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)


# Strict layered architecture rules (higher layers should not import lower)
LAYER_ORDER = {
    "UI": 5, "API": 4, "Service": 3, "Repository": 2,
    "Model": 1, "Database": 0, "Utils": -1, "Config": -1,
    "Core": -1, "Test": 6,
}

DOMAIN_KEYWORDS = {
    "auth": "Auth", "authentication": "Auth", "login": "Auth", "jwt": "Auth", "oauth": "Auth",
    "user": "User", "account": "Account", "profile": "User",
    "api": "API", "route": "API", "view": "API", "endpoint": "API", "controller": "API", "handler": "API",
    "service": "Service", "business": "Service", "logic": "Service", "manager": "Service",
    "model": "Model", "schema": "Model", "entity": "Model", "dto": "Model",
    "repo": "Repository", "repository": "Repository", "dao": "Repository", "store": "Repository",
    "util": "Utils", "helper": "Utils", "common": "Utils", "shared": "Utils", "lib": "Utils",
    "test": "Test", "spec": "Test", "mock": "Test", "fixture": "Test",
    "config": "Config", "setting": "Config", "env": "Config",
    "hook": "Hooks", "middleware": "Middleware", "decorator": "Middleware",
    "core": "Core", "base": "Core", "abstract": "Core",
    "ui": "UI", "component": "UI", "widget": "UI", "page": "UI", "screen": "UI",
    "db": "Database", "database": "Database", "migration": "Database", "seed": "Database",
    "cache": "Cache", "redis": "Cache", "celery": "Queue", "task": "Queue", "worker": "Queue",
    "notification": "Notification", "email": "Notification", "sms": "Notification",
    "payment": "Payment", "billing": "Payment", "invoice": "Payment",
}


class ArchitectureAnalyzer:

    def analyze(self, files: List[RepoFile]) -> ArchitectureResult:
        # Build import graph
        graph, file_modules = self._build_import_graph(files)
        modules = list(set(graph.keys()) | {dep for deps in graph.values() for dep in deps})

        # Find circular dependencies
        circulars = self._find_circular_deps(graph)

        # Find layer violations
        layer_violations = self._find_layer_violations(graph)

        # Coupling metrics
        coupling_score = self._compute_coupling(graph, modules)
        cohesion_score = self._compute_cohesion(files, file_modules)

        # Domain driven score
        domain_score = self._domain_score(modules, circulars, layer_violations)

        # Graph visualization data
        nodes, edges = self._graph_to_viz(graph, modules)

        # Largest + orphans
        in_degrees = defaultdict(int)
        for deps in graph.values():
            for d in deps:
                in_degrees[d] += 1
        largest = max(in_degrees, key=in_degrees.get) if in_degrees else "N/A"
        all_referenced = set(in_degrees.keys()) | set(graph.keys())
        orphans = [m for m in modules if m not in all_referenced or (in_degrees.get(m, 0) == 0 and not graph.get(m))]

        summary = self._build_summary(circulars, layer_violations, coupling_score, len(modules))

        return ArchitectureResult(
            summary=summary,
            total_modules=len(modules),
            circular_dependencies=circulars,
            cross_domain_deps=len(circulars),
            domain_driven_score=domain_score,
            coupling_score=coupling_score,
            cohesion_score=cohesion_score,
            layer_violations=layer_violations,
            largest_component=largest,
            orphan_modules=orphans[:5],
            nodes=nodes,
            edges=edges,
        )

    def _build_import_graph(self, files: List[RepoFile]) -> Tuple[Dict[str, Set[str]], Dict[str, str]]:
        graph: Dict[str, Set[str]] = defaultdict(set)
        file_modules: Dict[str, str] = {}

        for f in files:
            module = self._path_to_module(f.relative_path)
            file_modules[f.relative_path] = module

            if f.language == "Python":
                imports = self._parse_python_imports(f.content)
            elif f.language in ("JavaScript", "TypeScript"):
                imports = self._parse_js_imports(f.content)
            elif f.language == "Java":
                imports = self._parse_java_imports(f.content)
            elif f.language == "Go":
                imports = self._parse_go_imports(f.content)
            else:
                imports = []

            for imp in imports:
                target = self._resolve_to_domain(imp)
                if target and target != module:
                    graph[module].add(target)

        return dict(graph), file_modules

    def _parse_python_imports(self, content: str) -> List[str]:
        imports = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except SyntaxError:
            for match in re.finditer(r'^(?:from|import)\s+([\w.]+)', content, re.MULTILINE):
                imports.append(match.group(1))
        return imports

    def _parse_js_imports(self, content: str) -> List[str]:
        return re.findall(r'(?:import|require)\s*[\(\s]["\']([^"\']+)["\']', content)

    def _parse_java_imports(self, content: str) -> List[str]:
        return re.findall(r'import\s+([\w.]+);', content)

    def _parse_go_imports(self, content: str) -> List[str]:
        return re.findall(r'"([\w./]+)"', content)

    def _resolve_to_domain(self, import_path: str) -> str:
        parts = re.split(r'[./\\]', import_path.lower())
        for part in parts:
            for keyword, label in DOMAIN_KEYWORDS.items():
                if keyword in part:
                    return label
        return parts[0].capitalize() if parts else ""

    def _path_to_module(self, path: str) -> str:
        parts = path.replace("\\", "/").lower().split("/")
        for part in parts:
            for keyword, label in DOMAIN_KEYWORDS.items():
                if keyword in part:
                    return label
        return parts[0].capitalize() if parts else "Root"

    def _find_circular_deps(self, graph: Dict[str, Set[str]]) -> List[str]:
        if NX_AVAILABLE:
            G = nx.DiGraph()
            for node, deps in graph.items():
                for dep in deps:
                    G.add_edge(node, dep)
            try:
                cycles = list(nx.simple_cycles(G))
                return [" → ".join(c + [c[0]]) for c in cycles[:10]]
            except Exception:
                return []
        return self._dfs_cycles(graph)

    def _dfs_cycles(self, graph: Dict[str, Set[str]]) -> List[str]:
        visited: Set[str] = set()
        path: List[str] = []
        cycles: List[str] = []

        def dfs(node: str):
            if node in path:
                idx = path.index(node)
                cycles.append(" → ".join(path[idx:] + [node]))
                return
            if node in visited or len(cycles) >= 10:
                return
            visited.add(node)
            path.append(node)
            for n in graph.get(node, []):
                dfs(n)
            path.pop()

        for node in list(graph.keys()):
            dfs(node)
        return cycles

    def _find_layer_violations(self, graph: Dict[str, Set[str]]) -> List[str]:
        violations = []
        for src, targets in graph.items():
            src_level = LAYER_ORDER.get(src, 2)
            for tgt in targets:
                tgt_level = LAYER_ORDER.get(tgt, 2)
                if tgt_level > src_level and src_level >= 0:
                    violations.append(f"{src} → {tgt} (layer violation)")
        return violations[:5]

    def _compute_coupling(self, graph: Dict[str, Set[str]], modules: List[str]) -> float:
        """Instability metric: I = Ce / (Ca + Ce). High instability = high coupling."""
        if not modules:
            return 0.0
        efferent = {m: len(graph.get(m, [])) for m in modules}
        afferent = defaultdict(int)
        for deps in graph.values():
            for d in deps:
                afferent[d] += 1
        instabilities = []
        for m in modules:
            ce = efferent.get(m, 0)
            ca = afferent.get(m, 0)
            total = ce + ca
            if total > 0:
                instabilities.append(ce / total)
        avg_instability = sum(instabilities) / len(instabilities) if instabilities else 0.5
        return round(avg_instability * 100, 1)

    def _compute_cohesion(self, files: List[RepoFile], file_modules: Dict[str, str]) -> float:
        """LCOM-inspired: files in same module that share imports = higher cohesion."""
        module_files: Dict[str, List[RepoFile]] = defaultdict(list)
        for f in files:
            m = file_modules.get(f.relative_path, "Root")
            module_files[m].append(f)

        scores = []
        for module, mfiles in module_files.items():
            if len(mfiles) < 2:
                scores.append(1.0)
                continue
            # Check how many file pairs share at least one import keyword
            shared = 0
            total = 0
            for i in range(len(mfiles)):
                for j in range(i+1, len(mfiles)):
                    total += 1
                    words_i = set(re.findall(r'\b\w{4,}\b', mfiles[i].content[:2000]))
                    words_j = set(re.findall(r'\b\w{4,}\b', mfiles[j].content[:2000]))
                    if len(words_i & words_j) > 5:
                        shared += 1
            scores.append(shared / total if total else 0.5)

        return round((sum(scores) / len(scores)) * 100, 1) if scores else 50.0

    def _domain_score(self, modules: List[str], circulars: List[str], violations: List[str]) -> float:
        base = 100.0
        base -= len(circulars) * 6
        base -= len(violations) * 4
        return max(0.0, round(base, 1))

    def _build_summary(self, circulars: List[str], violations: List[str],
                        coupling: float, n_modules: int) -> str:
        parts = []
        if not circulars and not violations:
            parts.append("Clean layered architecture detected.")
        else:
            if circulars:
                parts.append(f"{len(circulars)} circular {'dependency' if len(circulars)==1 else 'dependencies'} found.")
            if violations:
                parts.append(f"{len(violations)} layer violations detected.")
        parts.append(f"{n_modules} modules analyzed.")
        return " ".join(parts)

    def _graph_to_viz(self, graph: Dict[str, Set[str]], modules: List[str]) -> Tuple[List[Dict], List[Dict]]:
        all_nodes = set(modules)
        for deps in graph.values():
            all_nodes.update(deps)

        nodes = [{"id": n, "label": n, "weight": len(graph.get(n, []))} for n in all_nodes]
        edges = [
            {"source": src, "target": tgt, "weight": 1}
            for src, targets in graph.items()
            for tgt in targets
        ]
        return nodes, edges
