"""
JS/TS Analyzer — Speed-Optimized
Pre-compiled patterns, skip tiny files, fast line-scan loop.
"""

import re
import json
import subprocess
import os
from typing import List, Dict, Any
from dataclasses import dataclass
from app.utils.repo_cloner import RepoFile


@dataclass
class JSIssue:
    severity: str; rule_id: str; title: str; description: str
    file_path: str; line_number: int
    code_snippet: str = ""; fix_suggestion: str = ""; category: str = "QUALITY"


_RAW = [
    {"id":"no-eval","title":"Dangerous eval()","pattern":r'\beval\s*\(','sev':"HIGH","cat":"SECURITY","desc":"eval() is a major XSS vector.","fix":"Use JSON.parse() or refactor."},
    {"id":"no-innerHTML","title":"Unsafe innerHTML","pattern":r'\.innerHTML\s*=(?!=)','sev':"HIGH","cat":"SECURITY","desc":"innerHTML can introduce XSS.","fix":"Use textContent or DOMPurify.sanitize()."},
    {"id":"no-dangerouslySetInnerHTML","title":"React dangerouslySetInnerHTML","pattern":r'dangerouslySetInnerHTML\s*=','sev':"MEDIUM","cat":"SECURITY","desc":"Bypasses React XSS protection.","fix":"Sanitize with DOMPurify first."},
    {"id":"hardcoded-secret","title":"Hardcoded Secret","pattern":r'(?i)(api[_-]?key|secret|password|token|auth)\s*[:=]\s*["\'][A-Za-z0-9\-_]{10,}["\']','sev':"HIGH","cat":"SECURITY","desc":"Hardcoded credential.","fix":"Use process.env.API_KEY or import.meta.env."},
    {"id":"no-document-write","title":"document.write()","pattern":r'document\.write\s*\(','sev':"MEDIUM","cat":"SECURITY","desc":"XSS risk and overwrites page.","fix":"Use DOM manipulation methods."},
    {"id":"no-async-forEach","title":"async/await in forEach","pattern":r'\.forEach\s*\(\s*async\s','sev':"MEDIUM","cat":"PERFORMANCE","desc":"async callbacks in forEach don't await.","fix":"Use Promise.all(items.map(async i => ...))"},
    {"id":"promise-antipattern","title":"Promise Constructor Anti-pattern","pattern":r'new\s+Promise\s*\(\s*(?:async\s*)?\(?resolve','sev':"LOW","cat":"QUALITY","desc":"Wrapping existing promise is redundant.","fix":"Return the existing promise directly."},
    {"id":"react-hooks-cond","title":"Conditional Hook Call","pattern":r'if\s*\([^)]+\)\s*\{[^}]*\buse[A-Z]\w+\s*\(','sev':"HIGH","cat":"QUALITY","desc":"Violates Rules of Hooks.","fix":"Move hook to top level."},
    {"id":"missing-dep-array","title":"useEffect Without Deps","pattern":r'useEffect\s*\(\s*(?:async\s*)?\(?(?:\(\)|\w+)\s*=>\s*\{[^}]+\}\s*\)','sev':"MEDIUM","cat":"QUALITY","desc":"Runs on every render.","fix":"Add dependency array: useEffect(() => {}, [dep])"},
    {"id":"react-key-prop","title":"Missing key Prop in List","pattern":r'\.map\s*\([^)]*=>\s*(?:\(?\s*)?<(?!React\.Fragment)','sev':"MEDIUM","cat":"QUALITY","desc":"Elements in .map() need key prop.","fix":"Add key={item.id} to rendered element."},
    {"id":"state-mutation","title":"Direct State Mutation","pattern":r'(?:this\.state\.\w+|state\.\w+)\s*=(?!=)','sev':"HIGH","cat":"QUALITY","desc":"Bypasses React rendering cycle.","fix":"Use setState() or useState() setter."},
    {"id":"no-any","title":"Explicit any Type","pattern":r':\s*any\b|as\s+any\b','sev':"LOW","cat":"QUALITY","desc":"Defeats TypeScript type safety.","fix":"Use specific types or unknown with guards."},
    {"id":"ts-ignore","title":"@ts-ignore Comment","pattern":r'//\s*@ts-ignore|//\s*@ts-nocheck','sev':"MEDIUM","cat":"QUALITY","desc":"Suppresses TypeScript errors.","fix":"Fix the underlying type error."},
    {"id":"non-null-assert","title":"Non-null Assertion Overuse","pattern":r'\w+!\.','sev':"LOW","cat":"QUALITY","desc":"Can cause runtime errors.","fix":"Use optional chaining ?. instead."},
    {"id":"console-log","title":"console.log in Production","pattern":r'\bconsole\.(log|debug|info)\s*\(','sev':"LOW","cat":"PERFORMANCE","desc":"Leaks info and degrades performance.","fix":"Remove or replace with proper logger."},
    {"id":"large-bundle","title":"Whole-Library Import","pattern":r"import\s+\w+\s+from\s+['\"](?:lodash|moment|rxjs|antd)['\"]",'sev':"MEDIUM","cat":"PERFORMANCE","desc":"Prevents tree-shaking.","fix":"Import only: import debounce from 'lodash/debounce'"},
    {"id":"sync-xhr","title":"Synchronous XHR","pattern":r'\.open\s*\(\s*["\'][A-Z]+["\'],\s*[^,]+,\s*false\s*\)','sev':"HIGH","cat":"PERFORMANCE","desc":"Blocks the main thread.","fix":"Use fetch() with async/await."},
    {"id":"var-decl","title":"var Declaration","pattern":r'\bvar\s+\w+','sev':"LOW","cat":"QUALITY","desc":"var has hoisting issues.","fix":"Replace with const or let."},
    {"id":"loose-eq","title":"Loose Equality (==)","pattern":r'(?<!=)={2}(?!=)','sev':"LOW","cat":"QUALITY","desc":"Type coercion causes bugs.","fix":"Use === for strict equality."},
    {"id":"empty-catch","title":"Empty catch Block","pattern":r'catch\s*\([^)]*\)\s*\{\s*\}','sev':"MEDIUM","cat":"QUALITY","desc":"Silently swallows errors.","fix":"At minimum: catch (err) { console.error(err); }"},
    {"id":"debugger","title":"debugger Statement","pattern":r'^\s*debugger\s*;',"flags":re.MULTILINE,'sev':"MEDIUM","cat":"QUALITY","desc":"Halts execution in DevTools.","fix":"Remove before committing."},
]
_COMPILED = [
    {**r, "_re": re.compile(r["pattern"], r.get("flags", re.IGNORECASE))}
    for r in _RAW
]


class JSAnalyzer:

    def analyze(self, files: List[RepoFile]) -> List[JSIssue]:
        js_files = [f for f in files if f.language in ("JavaScript","TypeScript") and f.line_count >= 5]
        if not js_files:
            return []

        issues: List[JSIssue] = []
        for f in js_files:
            for rule in _COMPILED:
                for i, line in enumerate(f.lines, 1):
                    if rule["_re"].search(line):
                        issues.append(JSIssue(
                            severity=rule["sev"], rule_id=rule["id"],
                            title=rule["title"], description=rule["desc"],
                            file_path=f.relative_path, line_number=i,
                            code_snippet=line.strip()[:100],
                            fix_suggestion=rule.get("fix",""),
                            category=rule.get("cat","QUALITY"),
                        ))

        issues.extend(self._eslint(js_files))

        seen = set(); unique = []
        for i in issues:
            k = (i.file_path, i.line_number, i.rule_id)
            if k not in seen:
                seen.add(k); unique.append(i)

        unique.sort(key=lambda x: {"HIGH":0,"MEDIUM":1,"LOW":2}[x.severity])
        return unique[:40]

    def _eslint(self, files: List[RepoFile]) -> List[JSIssue]:
        issues = []
        try:
            result = subprocess.run(
                ["eslint","--format","json","--no-eslintrc",
                 "--rule",'{"no-eval":["error"],"no-undef":["warn"],"no-unused-vars":["warn"]}',
                 *[f.path for f in files[:10] if os.path.exists(f.path)]],
                capture_output=True, text=True, timeout=20,
            )
            if result.stdout:
                pm = {f.path: f.relative_path for f in files}
                for fr in json.loads(result.stdout):
                    rel = pm.get(fr.get("filePath",""),"")
                    for m in fr.get("messages",[]):
                        sev = "HIGH" if m.get("severity")==2 else "LOW"
                        issues.append(JSIssue(sev, f"eslint/{m.get('ruleId','?')}",
                            f"ESLint: {m.get('ruleId','?')}", m.get("message",""),
                            rel, m.get("line",0)))
        except Exception:
            pass
        return issues
