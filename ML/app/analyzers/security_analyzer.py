"""
Security Analyzer — Speed-Optimized
Key optimisations:
  • Compile all regex patterns once at module load (not per-file)
  • Skip files under 5 lines
  • Bandit timeout reduced to 60 s with --skip for low-severity tests
  • Dedup by (file, line, title) at the end
"""

import re
import subprocess
import json
import os
from typing import List, Dict, Any
from dataclasses import dataclass, field
from app.utils.repo_cloner import RepoFile


@dataclass
class SecurityIssue:
    severity: str; title: str; description: str
    file_path: str; line_number: int
    code_snippet: str = ""; cwe: str = ""; owasp: str = ""
    fix_suggestion: str = ""; confidence: str = "MEDIUM"


_RAW_PATTERNS: List[Dict[str, Any]] = [
    {"id":"jwt_none","title":"Insecure JWT Algorithm (none)","pattern":r'algorithm[s]?\s*=\s*[\["]none["\]]|"alg"\s*:\s*"none"',"severity":"HIGH","cwe":"CWE-347","owasp":"A02:2021","description":"JWT 'none' algorithm bypasses signature verification.","fix":"Use RS256 or HS256."},
    {"id":"jwt_weak","title":"Weak JWT Secret","pattern":r'jwt\.encode\(.*secret.*=\s*["\'][a-zA-Z0-9]{1,12}["\']',"severity":"HIGH","cwe":"CWE-326","owasp":"A02:2021","description":"Short/predictable JWT secret.","fix":"Use a 256-bit random secret."},
    {"id":"hardcoded_pw","title":"Hardcoded Password","pattern":r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{4,}["\']',"severity":"HIGH","cwe":"CWE-798","owasp":"A07:2021","description":"Hardcoded password in source.","fix":"Use os.environ.get('DB_PASSWORD')"},
    {"id":"hardcoded_key","title":"Hardcoded API Key","pattern":r'(?i)(api_key|apikey|api_token|auth_token|access_token|secret_key)\s*=\s*["\'][A-Za-z0-9\-_]{16,}["\']',"severity":"HIGH","cwe":"CWE-798","owasp":"A07:2021","description":"Hardcoded API key.","fix":"Store in environment variables or vault."},
    {"id":"aws_key","title":"AWS Access Key Exposed","pattern":r'AKIA[0-9A-Z]{16}',"severity":"HIGH","cwe":"CWE-798","owasp":"A07:2021","description":"AWS Access Key ID detected.","fix":"Revoke immediately and use IAM roles."},
    {"id":"sql_fstr","title":"SQL Injection via f-string","pattern":r'(?:execute|query)\s*\(\s*f["\'].*(?:SELECT|INSERT|UPDATE|DELETE|WHERE)',"severity":"HIGH","cwe":"CWE-89","owasp":"A03:2021","description":"SQL query built with f-string.","fix":"Use parameterized queries."},
    {"id":"cmd_inject","title":"OS Command Injection","pattern":r'os\.system\s*\(|subprocess\.(run|call|Popen)\s*\([^)]*shell\s*=\s*True',"severity":"HIGH","cwe":"CWE-78","owasp":"A03:2021","description":"Shell execution risk.","fix":"Avoid shell=True; pass args as list."},
    {"id":"eval_exec","title":"Use of eval()/exec()","pattern":r'\b(eval|exec)\s*\(',"severity":"HIGH","cwe":"CWE-95","owasp":"A03:2021","description":"Arbitrary code execution risk.","fix":"Use ast.literal_eval() instead."},
    {"id":"weak_md5","title":"Weak Hash (MD5)","pattern":r'hashlib\.md5\s*\(',"severity":"MEDIUM","cwe":"CWE-328","owasp":"A02:2021","description":"MD5 is cryptographically broken.","fix":"Use hashlib.sha256()."},
    {"id":"weak_sha1","title":"Weak Hash (SHA1)","pattern":r'hashlib\.sha1\s*\(',"severity":"MEDIUM","cwe":"CWE-328","owasp":"A02:2021","description":"SHA1 is vulnerable to collision attacks.","fix":"Use hashlib.sha256()."},
    {"id":"weak_rand","title":"Insecure Random","pattern":r'\brandom\.(random|randint|choice|shuffle)\s*\(',"severity":"MEDIUM","cwe":"CWE-338","owasp":"A02:2021","description":"random module is not cryptographically secure.","fix":"Use the secrets module."},
    {"id":"pickle","title":"Insecure Deserialization (pickle)","pattern":r'\bpickle\.(loads?|Unpickler)\s*\(',"severity":"HIGH","cwe":"CWE-502","owasp":"A08:2021","description":"Pickle executes arbitrary code on load.","fix":"Use JSON or msgpack instead."},
    {"id":"yaml_unsafe","title":"Unsafe YAML Load","pattern":r'yaml\.load\s*\([^,)]+\)',"severity":"HIGH","cwe":"CWE-502","owasp":"A08:2021","description":"yaml.load() can execute arbitrary Python.","fix":"Use yaml.safe_load()."},
    {"id":"debug_mode","title":"Debug Mode in Production","pattern":r'(?i)DEBUG\s*=\s*True|app\.run\([^)]*debug\s*=\s*True',"severity":"MEDIUM","cwe":"CWE-215","owasp":"A05:2021","description":"Debug mode exposes internals.","fix":"Set DEBUG=False via env var."},
    {"id":"ssl_off","title":"SSL Verification Disabled","pattern":r'verify\s*=\s*False|check_hostname\s*=\s*False',"severity":"HIGH","cwe":"CWE-295","owasp":"A02:2021","description":"MITM attack possible.","fix":"Never disable SSL verification."},
    {"id":"cors_star","title":"CORS Wildcard","pattern":r'Access-Control-Allow-Origin["\s:]+\*|allow_origins\s*=\s*\[.*["\*].*\]',"severity":"MEDIUM","cwe":"CWE-942","owasp":"A05:2021","description":"Wildcard CORS allows any origin.","fix":"Restrict to specific trusted domains."},
    {"id":"no_timeout","title":"HTTP Request Without Timeout","pattern":r'requests\.(get|post|put|delete|patch)\s*\([^)]*\)(?!\s*\.|#)',"severity":"LOW","cwe":"CWE-400","owasp":"A04:2021","description":"No timeout causes potential DoS.","fix":"Add timeout=10 parameter."},
    {"id":"template_inj","title":"SSTI Risk","pattern":r'render_template_string\s*\(|Template\s*\([^)]*request\.',"severity":"HIGH","cwe":"CWE-94","owasp":"A03:2021","description":"User input in template engine.","fix":"Never pass user input to templates."},
    {"id":"sensitive_log","title":"Sensitive Data in Logs","pattern":r'(?i)log(?:ger)?\.(?:info|debug|warning|error)\s*\(.*(?:password|token|secret|key|credit)',"severity":"MEDIUM","cwe":"CWE-532","owasp":"A09:2021","description":"Secrets may appear in logs.","fix":"Mask sensitive values before logging."},
    {"id":"open_redir","title":"Open Redirect","pattern":r'redirect\s*\(\s*request\.(args|GET|POST|params)\[',"severity":"MEDIUM","cwe":"CWE-601","owasp":"A01:2021","description":"Unvalidated redirect URL.","fix":"Validate redirect URLs against allowlist."},
    {"id":"path_trav","title":"Path Traversal Risk","pattern":r'open\s*\(\s*(?:request\.|f["\'].*\{)',"severity":"HIGH","cwe":"CWE-22","owasp":"A01:2021","description":"File path from user input.","fix":"Sanitize with os.path.realpath()."},
    {"id":"hardcoded_iv","title":"Hardcoded Crypto IV","pattern":r'\biv\s*=\s*b["\'][^"\']{8,}["\']',"severity":"HIGH","cwe":"CWE-329","owasp":"A02:2021","description":"Hardcoded IV weakens encryption.","fix":"Generate IV with os.urandom(16)."},
]

# ── Compile all patterns ONCE at module load ───────────────────────
_COMPILED = [
    {**rule, "_re": re.compile(rule["pattern"], re.IGNORECASE | re.MULTILINE)}
    for rule in _RAW_PATTERNS
]

_SECRET_COMPILED = [
    (re.compile(p), t, s, c)
    for p, t, s, c in [
        (r'-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----', "Private Key Exposed",        "HIGH", "CWE-321"),
        (r'postgres(?:ql)?://[^:]+:[^@]+@',               "DB Connection String",        "HIGH", "CWE-522"),
        (r'mysql://[^:]+:[^@]+@',                          "MySQL Connection String",     "HIGH", "CWE-522"),
        (r'mongodb\+srv://[^:]+:[^@]+@',                   "MongoDB Connection String",   "HIGH", "CWE-522"),
        (r'sk-[a-zA-Z0-9]{20,}',                           "OpenAI API Key",              "HIGH", "CWE-798"),
        (r'ghp_[a-zA-Z0-9]{36}',                           "GitHub PAT",                  "HIGH", "CWE-798"),
        (r'xox[baprs]-[0-9A-Za-z\-]{10,}',                "Slack Token",                 "HIGH", "CWE-798"),
        (r'AIza[0-9A-Za-z\-_]{35}',                        "Google API Key",              "HIGH", "CWE-798"),
    ]
]


class SecurityAnalyzer:

    def analyze(self, files: List[RepoFile]) -> List[SecurityIssue]:
        issues: List[SecurityIssue] = []

        for f in files:
            if f.line_count < 5:
                continue
            for rule in _COMPILED:
                for i, line in enumerate(f.lines, 1):
                    if rule["_re"].search(line):
                        issues.append(SecurityIssue(
                            severity=rule["severity"], title=rule["title"],
                            description=rule["description"],
                            file_path=f.relative_path, line_number=i,
                            code_snippet=line.strip()[:120],
                            cwe=rule.get("cwe",""), owasp=rule.get("owasp",""),
                            fix_suggestion=rule.get("fix",""),
                        ))
            for pat, title, severity, cwe in _SECRET_COMPILED:
                for i, line in enumerate(f.lines, 1):
                    if pat.search(line):
                        issues.append(SecurityIssue(
                            severity=severity, title=title,
                            description="Potential secret credential detected.",
                            file_path=f.relative_path, line_number=i,
                            code_snippet="[REDACTED]", cwe=cwe, owasp="A07:2021",
                            fix_suggestion="Remove immediately, rotate, use env vars.",
                        ))

        issues.extend(self._bandit([f for f in files if f.language == "Python"]))

        # Deduplicate
        seen = set(); unique = []
        for i in issues:
            k = (i.file_path, i.line_number, i.title)
            if k not in seen:
                seen.add(k); unique.append(i)

        return sorted(unique, key=lambda x: {"HIGH":0,"MEDIUM":1,"LOW":2}[x.severity])

    def _bandit(self, python_files: List[RepoFile]) -> List[SecurityIssue]:
        issues = []
        paths = [f.path for f in python_files if os.path.exists(f.path)]
        if not paths:
            return issues
        try:
            base = os.path.commonpath(paths)
            if os.path.isfile(base):
                base = os.path.dirname(base)
            r = subprocess.run(
                ["bandit", "-r", base, "-f", "json", "-q",
                 "--exit-zero", "-l",
                 "--skip", "B101,B105,B106,B107"],   # Skip low-value tests
                capture_output=True, text=True, timeout=60,
            )
            if not r.stdout:
                return issues
            data = json.loads(r.stdout)
            path_map = {f.path: f.relative_path for f in python_files}
            SEV = {"HIGH":"HIGH","MEDIUM":"MEDIUM","LOW":"LOW"}
            for item in data.get("results", []):
                sev  = SEV.get(item.get("issue_severity","LOW").upper(), "LOW")
                conf = item.get("issue_confidence","LOW").upper()
                if sev == "LOW" and conf == "LOW":
                    continue
                cwe_d = item.get("issue_cwe",{})
                cwe   = f"CWE-{cwe_d.get('id','')}" if isinstance(cwe_d, dict) and cwe_d.get("id") else ""
                issues.append(SecurityIssue(
                    severity=sev, title=item.get("test_name","").replace("_"," ").title(),
                    description=item.get("issue_text",""),
                    file_path=path_map.get(item.get("filename",""), item.get("filename","")),
                    line_number=item.get("line_number",0),
                    code_snippet=item.get("code","").strip()[:120],
                    cwe=cwe, fix_suggestion=item.get("more_info",""),
                    confidence=conf,
                ))
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass
        return issues
