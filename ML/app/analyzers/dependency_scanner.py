"""
Dependency Vulnerability Scanner — Speed-Optimized
Key optimisations:
  • Concurrent OSV API calls with ThreadPoolExecutor (was sequential)
  • Cap total packages to 40 to limit network calls
  • Per-request timeout of 5 s (was 8 s)
  • Skip packages with no version (nothing to query)
"""

import os
import json
import re
import urllib.request
import urllib.error
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

OSV_API = "https://api.osv.dev/v1/query"
SEVERITY_MAP = {"CRITICAL":"HIGH","HIGH":"HIGH","MODERATE":"MEDIUM",
                "MEDIUM":"MEDIUM","LOW":"LOW","NONE":"LOW"}
# Cache OSV lookups during the process to make repeated scans much faster.
_OSV_CACHE: Dict[str, List[Dict[str, Any]]] = {}


class DependencyScanner:

    def scan(self, repo_dir: str) -> List[Dict[str, Any]]:
        packages = self._collect(repo_dir)
        if not packages:
            return []

        # Query OSV concurrently — big speedup on large dependency lists
        vulns: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(self._query, p): p for p in packages}
            for future in as_completed(futures):
                try:
                    for v in future.result():
                        v["source_file"] = futures[future].get("source_file", "")
                        vulns.append(v)
                except Exception:
                    pass

        order = {"HIGH":0,"MEDIUM":1,"LOW":2}
        return sorted(vulns, key=lambda x: order.get(x.get("severity","LOW"), 2))

    # ── Collection ────────────────────────────────────────────────

    def _collect(self, repo_dir: str) -> List[Dict]:
        packages = []
        for root, dirs, files in os.walk(repo_dir):
            dirs[:] = [d for d in dirs if d not in {".git","node_modules","__pycache__",".venv","venv","dist","build"}]
            for name in files:
                fp  = os.path.join(root, name)
                rel = os.path.relpath(fp, repo_dir)
                if name == "requirements.txt":       packages.extend(self._req_txt(fp, rel))
                elif name == "Pipfile":              packages.extend(self._pipfile(fp, rel))
                elif name == "pyproject.toml":       packages.extend(self._pyproject(fp, rel))
                elif name == "package.json":         packages.extend(self._pkg_json(fp, rel))
                elif name == "go.mod":               packages.extend(self._go_mod(fp, rel))

        # Deduplicate and cap
        seen, unique = set(), []
        for p in packages:
            if not p.get("version"):          # Skip unversioned packages
                continue
            key = (p["name"].lower(), p["ecosystem"])
            if key not in seen:
                seen.add(key)
                unique.append(p)
        return unique[:40]

    def _req_txt(self, fp, rel):
        pkgs = []
        try:
            for line in open(fp, encoding="utf-8", errors="replace"):
                line = line.strip()
                if not line or line.startswith(("#","-","git+")):
                    continue
                m = re.match(r'^([A-Za-z0-9_\-\.]+)\s*(?:[=~><!\^]+\s*([\d\.]+\w*))?', line)
                if m:
                    pkgs.append({"name":m.group(1),"version":m.group(2) or "","ecosystem":"PyPI","source_file":rel})
        except Exception:
            pass
        return pkgs

    def _pipfile(self, fp, rel):
        pkgs = []
        try:
            in_pkg = False
            for line in open(fp, encoding="utf-8", errors="replace"):
                line = line.strip()
                if "[packages]" in line or "[dev-packages]" in line:
                    in_pkg = True; continue
                if line.startswith("[") and "packages" not in line:
                    in_pkg = False
                if in_pkg and "=" in line:
                    k, _, v = line.partition("=")
                    m = re.search(r'[\d\.]+', v)
                    pkgs.append({"name":k.strip().strip('"'),"version":m.group() if m else "","ecosystem":"PyPI","source_file":rel})
        except Exception:
            pass
        return pkgs

    def _pyproject(self, fp, rel):
        pkgs = []
        try:
            content = open(fp, encoding="utf-8", errors="replace").read()
            for m in re.finditer(r'"([A-Za-z0-9_\-]+)\s*(?:[>=<!~^]+\s*([\d\.]+))?', content):
                if m.group(1) and len(m.group(1)) > 1:
                    pkgs.append({"name":m.group(1),"version":m.group(2) or "","ecosystem":"PyPI","source_file":rel})
        except Exception:
            pass
        return pkgs

    def _pkg_json(self, fp, rel):
        pkgs = []
        try:
            data = json.load(open(fp, encoding="utf-8", errors="replace"))
            for section in ("dependencies","devDependencies","peerDependencies"):
                for name, ver_raw in data.get(section, {}).items():
                    m = re.search(r'[\d\.]+', str(ver_raw))
                    pkgs.append({"name":name,"version":m.group() if m else "","ecosystem":"npm","source_file":rel})
        except Exception:
            pass
        return pkgs

    def _go_mod(self, fp, rel):
        pkgs = []
        try:
            for line in open(fp, encoding="utf-8", errors="replace"):
                m = re.match(r'\s*([\w\.\/\-]+)\s+v([\d\.]+[\w\-]*)', line.strip())
                if m:
                    pkgs.append({"name":m.group(1),"version":m.group(2),"ecosystem":"Go","source_file":rel})
        except Exception:
            pass
        return pkgs

    # ── OSV query ─────────────────────────────────────────────────

    def _query(self, pkg: Dict) -> List[Dict[str, Any]]:
        cache_key = f"{pkg['ecosystem'].upper()}|{pkg['name'].lower()}|{pkg.get('version','') or ''}"
        if cache_key in _OSV_CACHE:
            return _OSV_CACHE[cache_key]

        payload = {"package": {"name": pkg["name"], "ecosystem": pkg["ecosystem"]}}
        if pkg.get("version"):
            payload["version"] = pkg["version"]
        try:
            body = json.dumps(payload).encode()
            req  = urllib.request.Request(
                OSV_API, data=body,
                headers={"Content-Type": "application/json"}, method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
            results = []
            for item in data.get("vulns", []):
                sev   = self._severity(item)
                fixed = self._fixed(item)
                cve   = next((a for a in item.get("aliases",[]) if a.startswith("CVE")), item.get("id",""))
                results.append({
                    "package":           pkg["name"],
                    "ecosystem":         pkg["ecosystem"],
                    "installed_version": pkg.get("version",""),
                    "fixed_version":     fixed,
                    "severity":          sev,
                    "summary":           item.get("summary","Known vulnerability")[:200],
                    "cve":               cve,
                    "osv_id":            item.get("id",""),
                    "source_file":       "",
                })
            _OSV_CACHE[cache_key] = results
            return results
        except Exception:
            _OSV_CACHE[cache_key] = []
            return []

    def _severity(self, vuln):
        db = vuln.get("database_specific",{}).get("severity","") or \
             vuln.get("ecosystem_specific",{}).get("severity","")
        m = SEVERITY_MAP.get(str(db).upper())
        if m: return m
        return "HIGH" if len(vuln.get("affected",[])) > 3 else "MEDIUM"

    def _fixed(self, vuln):
        try:
            for af in vuln.get("affected",[]):
                for rng in af.get("ranges",[]):
                    for ev in rng.get("events",[]):
                        if "fixed" in ev:
                            return ev["fixed"]
        except Exception:
            pass
        return "latest"
