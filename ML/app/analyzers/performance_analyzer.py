"""
Performance Analyzer — Speed-Optimized
Key optimisations:
  • Pre-compiled regex patterns (module-level)
  • Skip files under 5 lines
  • AST visitor only on Python files
"""

import ast
import re
from typing import List, Set
from dataclasses import dataclass

from app.utils.repo_cloner import RepoFile


@dataclass
class PerformanceIssue:
    severity: str; title: str; description: str
    file_path: str; line_number: int
    function_name: str = ""; fix_suggestion: str = ""; category: str = "PERFORMANCE"


_RAW = [
    {"id":"print_prod","title":"print() in Production","pattern":r'^\s*print\s*\(','flags':re.MULTILINE,"severity":"LOW","description":"print() pollutes stdout.","fix":"Replace with logging.debug/info."},
    {"id":"bare_except","title":"Bare except Clause","pattern":r'except\s*:',"severity":"MEDIUM","description":"Bare except catches all errors silently.","fix":"Specify exception type: except ValueError as e:"},
    {"id":"mutable_default","title":"Mutable Default Argument","pattern":r'def \w+\([^)]*=\s*(\[\]|\{\}|\(\))',"severity":"MEDIUM","description":"Shared mutable default causes bugs.","fix":"Use None default and initialize inside."},
    {"id":"global_state","title":"Mutable Global State","pattern":r'^\s*global\s+\w+',"flags":re.MULTILINE,"severity":"LOW","description":"Globals cause hidden coupling.","fix":"Pass state as arguments or use a class."},
    {"id":"list_in_agg","title":"Unnecessary List in Aggregation","pattern":r'\b(sum|min|max|any|all)\s*\(\s*\[',"severity":"LOW","description":"Builds an unneeded list.","fix":"Use generator: sum(x for x in ...)"},
    {"id":"regex_str","title":"Regex Compiled Inside Loop","pattern":r'for .+:\n(?:[^\n]*\n)*?\s*re\.(compile|match|search|findall)\(',"flags":re.MULTILINE,"severity":"MEDIUM","description":"Recompiling regex every iteration wastes CPU.","fix":"Compile outside the loop: pat = re.compile(...)"},
    {"id":"open_in_loop","title":"File Open Inside Loop","pattern":r'for .+:\n(?:[^\n]*\n)*?\s*open\s*\(',"flags":re.MULTILINE,"severity":"MEDIUM","description":"Excessive I/O syscalls.","fix":"Open outside loop and pass the handle."},
    {"id":"str_concat","title":"String Concatenation in Loop","pattern":r'for .+:\n(?:[^\n]*\n)*?\s*\w+\s*\+=\s*["\']',"flags":re.MULTILINE,"severity":"LOW","description":"O(n²) string copies.","fix":"Use a list and ''.join(parts) at the end."},
]
_COMPILED = [
    {**r, "_re": re.compile(r["pattern"], r.get("flags", 0))}
    for r in _RAW
]


class PerformanceAnalyzer:

    def analyze(self, files: List[RepoFile]) -> List[PerformanceIssue]:
        issues: List[PerformanceIssue] = []

        for f in files:
            if f.line_count < 5:
                continue
            # Regex rules
            for rule in _COMPILED:
                for match in rule["_re"].finditer(f.content):
                    line_no = f.content[:match.start()].count("\n") + 1
                    issues.append(PerformanceIssue(
                        severity=rule["severity"], title=rule["title"],
                        description=rule["description"],
                        file_path=f.relative_path, line_number=line_no,
                        fix_suggestion=rule.get("fix",""),
                    ))
            # AST rules (Python only)
            if f.language == "Python":
                issues.extend(_PerfVisitor(f.relative_path).run(f.content))

        # Deduplicate
        seen = set(); unique = []
        for i in issues:
            k = (i.file_path, i.line_number, i.title)
            if k not in seen:
                seen.add(k); unique.append(i)

        return sorted(unique, key=lambda x: {"HIGH":0,"MEDIUM":1,"LOW":2}[x.severity])


class _PerfVisitor(ast.NodeVisitor):
    def __init__(self, path: str):
        self.path = path
        self.issues: List[PerformanceIssue] = []
        self._fn_stack: List[str] = []
        self._loop_depth = 0
        self._async = False

    def run(self, source: str) -> List[PerformanceIssue]:
        try:
            self.visit(ast.parse(source))
        except SyntaxError:
            pass
        return self.issues

    def visit_FunctionDef(self, node):
        self._fn_stack.append(node.name); self.generic_visit(node); self._fn_stack.pop()
    def visit_AsyncFunctionDef(self, node):
        prev = self._async; self._async = True
        self._fn_stack.append(node.name); self.generic_visit(node); self._fn_stack.pop()
        self._async = prev
    def visit_For(self, node):
        self._loop_depth += 1; self.generic_visit(node); self._loop_depth -= 1
    def visit_While(self, node):
        self._loop_depth += 1; self.generic_visit(node); self._loop_depth -= 1

    def visit_Call(self, node):
        fn = self._fn_stack[-1] if self._fn_stack else "<module>"
        name = self._name(node); full = self._full_name(node)

        if self._loop_depth > 0:
            ORM = {"filter","get","all","first","last","execute","query",
                   "fetchone","fetchall","find","aggregate","count","exists"}
            if name in ORM:
                self._add("MEDIUM","N+1 Query Pattern",
                          f'"{fn}" runs individual DB queries in a loop.',
                          node.lineno, fn,
                          "Batch with select_related(), prefetch_related(), or IN query.")
            if name in {"get","post","put","delete","patch"}:
                if isinstance(node.func, ast.Attribute) and \
                   isinstance(node.func.value, ast.Name) and node.func.value.id == "requests":
                    self._add("MEDIUM","HTTP Request in Loop",
                              f'"{fn}" creates a new TCP connection per iteration.',
                              node.lineno, fn,
                              "Create requests.Session() outside the loop and reuse it.")

        if self._async:
            BLOCKING = {"time.sleep","requests.get","requests.post","input"}
            if any(b in full for b in BLOCKING):
                self._add("HIGH","Blocking I/O in Async Function",
                          f'Blocking call "{full}" in async "{fn}" blocks the event loop.',
                          node.lineno, fn,
                          "Use asyncio.sleep(), aiofiles, or httpx.AsyncClient().")

        if name in {"sum","min","max","any","all","sorted"}:
            for arg in node.args:
                if isinstance(arg, ast.ListComp):
                    self._add("LOW","Unnecessary List in Aggregation",
                              f"{name}() doesn't need a list comprehension.",
                              node.lineno, fn, f"Use generator: {name}(x for x in ...)")

        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.names and any(a.name == "*" for a in node.names):
            self._add("LOW","Wildcard Import",
                      f"'from {node.module} import *' pollutes namespace.",
                      node.lineno, "",
                      f"Import only what you need from {node.module}.")
        self.generic_visit(node)

    def _add(self, sev, title, desc, line, fn, fix=""):
        self.issues.append(PerformanceIssue(sev, title, desc, self.path, line, fn, fix))

    def _name(self, node):
        try:
            if isinstance(node.func, ast.Attribute): return node.func.attr
            if isinstance(node.func, ast.Name): return node.func.id
        except Exception: pass
        return ""

    def _full_name(self, node):
        try:
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                return f"{node.func.value.id}.{node.func.attr}"
            return self._name(node)
        except Exception: return ""
