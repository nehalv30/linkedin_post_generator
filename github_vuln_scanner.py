#!/usr/bin/env python3
"""
GitHub Vulnerability Scanner
------------------------------
Finds real public repositories containing known vulnerable code, clones them
locally (shallow), runs pattern-based static analysis, and prints a report.

No API key required for basic use.  Optionally set GITHUB_TOKEN for enriched
advisory lookups.

Usage:
  python3 github_vuln_scanner.py [--repos REPO ...] [--limit N] [--token TOKEN]

Example:
  python3 github_vuln_scanner.py --repos nicowillis/Vulnerable-Flask-App appsecco/dvna
"""

import os
import re
import sys
import json
import time
import shutil
import argparse
import textwrap
import tempfile
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ---------------------------------------------------------------------------
# Well-known CVEs (offline fallback — no network required)
# ---------------------------------------------------------------------------

KNOWN_CVES = [
    {
        "id": "CVE-2022-42969",
        "package": "py (PyPI)",
        "cvss": 7.5,
        "summary": "ReDoS in py.path.svnwc.blame() via crafted SVN repository URL",
        "vuln_class": "ReDoS",
    },
    {
        "id": "CVE-2023-30861",
        "package": "flask (PyPI)",
        "cvss": 7.5,
        "summary": "Flask response cookie samesite attribute not enforced — session fixation risk",
        "vuln_class": "Session Fixation",
    },
    {
        "id": "CVE-2019-14234",
        "package": "django (PyPI)",
        "cvss": 9.8,
        "summary": "Django JSONField/HStoreField SQL injection via crafted key names",
        "vuln_class": "SQL Injection",
    },
    {
        "id": "CVE-2020-28493",
        "package": "Jinja2 (PyPI)",
        "cvss": 5.3,
        "summary": "Jinja2 ReDoS in urlize filter via crafted HTML with many spaces",
        "vuln_class": "ReDoS",
    },
    {
        "id": "CVE-2021-44228",
        "package": "log4j-core (Maven)",
        "cvss": 10.0,
        "summary": "Log4Shell — JNDI injection via attacker-controlled log message strings",
        "vuln_class": "Remote Code Execution",
    },
    {
        "id": "CVE-2021-42013",
        "package": "Apache HTTP Server",
        "cvss": 9.8,
        "summary": "Path traversal and RCE via mod_cgi when path normalisation is incomplete",
        "vuln_class": "Path Traversal / RCE",
    },
    {
        "id": "CVE-2020-14343",
        "package": "pyyaml (PyPI)",
        "cvss": 9.8,
        "summary": "yaml.load() with default Loader executes arbitrary Python via !!python/object",
        "vuln_class": "Insecure Deserialization",
    },
    {
        "id": "CVE-2021-23727",
        "package": "celery (PyPI)",
        "cvss": 8.8,
        "summary": "Celery task result backend exposes sensitive data via unauthenticated worker",
        "vuln_class": "Information Exposure",
    },
]

# ---------------------------------------------------------------------------
# Deliberately-vulnerable repos (educational, well-maintained)
# ---------------------------------------------------------------------------

SEED_REPOS = [
    ("https://github.com/nicowillis/Vulnerable-Flask-App", "nicowillis/Vulnerable-Flask-App"),
    ("https://github.com/we45/Vulnerable-Flask-App",       "we45/Vulnerable-Flask-App"),
    ("https://github.com/appsecco/dvna",                   "appsecco/dvna"),
    ("https://github.com/snoopysecurity/dvws-node",        "snoopysecurity/dvws-node"),
    ("https://github.com/digininja/DVWA",                  "digininja/DVWA"),
]

# ---------------------------------------------------------------------------
# Vulnerability patterns (regex → class, explanation, severity)
# ---------------------------------------------------------------------------

@dataclass
class Pattern:
    vuln_class: str
    regex: re.Pattern
    explanation: str
    severity: str       # critical / high / medium / low
    cwe: str


PATTERNS: list[Pattern] = [
    Pattern(
        "SQL Injection",
        re.compile(
            # cursor.execute("... %s", ...) or .execute("... %d")
            r'(?:execute|query|cursor\.execute)\s*\(\s*["\'].*%[sd]'
            # f-string with SQL keyword
            r'|f["\'].*(?:SELECT|INSERT|UPDATE|DELETE|FROM|WHERE)\b.*\{'
            # string concat with SQL keyword — require realistic quote chars around keyword
            r'|["\'](?:SELECT|INSERT|UPDATE|DELETE|FROM|WHERE)\b[^"\']*["\'\s]*\+\s*\w',
            re.IGNORECASE,
        ),
        "User-controlled string interpolated directly into SQL query",
        "critical", "CWE-89",
    ),
    Pattern(
        "Command Injection",
        re.compile(
            r'os\.system\s*\('
            r'|subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True'
            r'|eval\s*\(.*(?:request|input|argv)'
            r'|exec\s*\(.*(?:request|input|argv)',
            re.IGNORECASE,
        ),
        "Unsanitised user input passed to shell or eval()",
        "critical", "CWE-78",
    ),
    Pattern(
        "Insecure Deserialization",
        re.compile(
            r'pickle\.loads?\s*\('
            r'|yaml\.load\s*\([^,)]+\)(?!\s*,\s*Loader\s*=\s*yaml\.Safe)'
            r'|jsonpickle\.decode\s*\(',
            re.IGNORECASE,
        ),
        "Deserialising untrusted data with an unsafe loader (RCE risk)",
        "critical", "CWE-502",
    ),
    Pattern(
        "Hardcoded Secret",
        re.compile(
            r'(?:password|passwd|secret|api_key|token|apikey|auth_token)\s*=\s*["\'][^"\']{6,}["\']',
            re.IGNORECASE,
        ),
        "Credential or secret literal committed to source code",
        "high", "CWE-798",
    ),
    Pattern(
        "Path Traversal",
        re.compile(
            # open() where the path includes user input (request.* or variable concat)
            r'open\s*\(\s*(?:request\.\w+|.*request\.\w+)'
            r'|send_file\s*\(.*(?:request\.\w+|input\s*\()'
            r'|render_template\s*\(.*(?:request\.\w+|input\s*\()',
            re.IGNORECASE,
        ),
        "Unsanitised user input used to construct a file path",
        "high", "CWE-22",
    ),
    Pattern(
        "XSS (Reflected)",
        re.compile(
            r'render_template_string\s*\(.*request\.'
            r'|Markup\s*\(.*request\.'
            r'|innerHTML\s*=.*(?:location\.|document\.)'
            r'|document\.write\s*\(.*(?:location\.|document\.)',
            re.IGNORECASE,
        ),
        "Unescaped user input reflected into HTML response",
        "high", "CWE-79",
    ),
    Pattern(
        "SSRF",
        re.compile(
            r'requests\.(?:get|post|put|delete)\s*\(.*(?:request\.|input\(|argv)'
            r'|urllib\.request\.urlopen\s*\(.*(?:request\.|input\()'
            r'|httpx\.(?:get|post)\s*\(.*(?:request\.|input\()',
            re.IGNORECASE,
        ),
        "Outbound HTTP request URL controlled by user input",
        "high", "CWE-918",
    ),
    Pattern(
        "Weak Cryptography",
        re.compile(
            r'hashlib\.(?:md5|sha1)\s*\('
            r'|Crypto\.Cipher\.DES\b'
            r'|random\.random\s*\(\)'
            r'|ECB\b.*mode',
            re.IGNORECASE,
        ),
        "Use of cryptographically weak algorithm or insecure mode",
        "medium", "CWE-327",
    ),
    Pattern(
        "Debug/Unsafe Config",
        re.compile(
            r'DEBUG\s*=\s*True'
            r'|app\.run\s*\([^)]*debug\s*=\s*True'
            r'|TESTING\s*=\s*True',
            re.IGNORECASE,
        ),
        "Application running in debug mode — exposes stack traces and Werkzeug console",
        "medium", "CWE-489",
    ),
]

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class VulnHit:
    file_path: str
    line_number: int
    line_content: str
    vuln_class: str
    severity: str
    explanation: str
    cwe: str


@dataclass
class RepoResult:
    repo_name: str
    repo_url: str
    language: str
    hits: list[VulnHit] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def hit_count(self) -> int:
        return len(self.hits)

    def classes(self) -> list[str]:
        return sorted({h.vuln_class for h in self.hits})


# ---------------------------------------------------------------------------
# Clone & walk
# ---------------------------------------------------------------------------

SCAN_EXTENSIONS = {".py", ".js", ".ts", ".php", ".java", ".rb", ".go", ".cs"}
MAX_FILE_SIZE = 200_000  # bytes


def clone_repo(url: str, dest: Path) -> bool:
    """Shallow-clone *url* into *dest*. Returns True on success."""
    try:
        result = subprocess.run(
            ["git", "clone", "--depth=1", "--quiet", url, str(dest)],
            capture_output=True, text=True, timeout=120,
        )
        return result.returncode == 0
    except Exception as exc:
        print(f"    [clone error] {exc}")
        return False


def walk_source_files(root: Path) -> list[Path]:
    files = []
    skip_dirs = {".git", "node_modules", "__pycache__", "vendor", "dist", "build", ".venv"}
    for path in root.rglob("*"):
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.is_file() and path.suffix in SCAN_EXTENSIONS:
            if path.stat().st_size < MAX_FILE_SIZE:
                files.append(path)
    return files


# ---------------------------------------------------------------------------
# Static analysis
# ---------------------------------------------------------------------------

def scan_file(path: Path, repo_root: Path) -> list[VulnHit]:
    hits: list[VulnHit] = []
    rel = str(path.relative_to(repo_root))
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return hits

    for lineno, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        # Skip blank lines and pure comment lines
        if not stripped or stripped.startswith(("#", "//", "*", "<!--", "/*")):
            continue
        for p in PATTERNS:
            if p.regex.search(line):
                hits.append(VulnHit(
                    file_path=rel,
                    line_number=lineno,
                    line_content=line.rstrip()[:200],
                    vuln_class=p.vuln_class,
                    severity=p.severity,
                    explanation=p.explanation,
                    cwe=p.cwe,
                ))
    return hits


def scan_directory(root: Path, repo_name: str, repo_url: str) -> RepoResult:
    files = walk_source_files(root)
    result = RepoResult(
        repo_name=repo_name,
        repo_url=repo_url,
        language=_detect_language(files),
    )
    for f in files:
        result.hits.extend(scan_file(f, root))
    return result


def _detect_language(files: list[Path]) -> str:
    counts: dict[str, int] = {}
    for f in files:
        counts[f.suffix] = counts.get(f.suffix, 0) + 1
    if not counts:
        return "Unknown"
    ext = max(counts, key=lambda k: counts[k])
    mapping = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
               ".php": "PHP", ".java": "Java", ".rb": "Ruby", ".go": "Go", ".cs": "C#"}
    return mapping.get(ext, ext.lstrip(".").upper())


# ---------------------------------------------------------------------------
# Optional: enrich with GitHub advisory API
# ---------------------------------------------------------------------------

def fetch_osv_advisories(packages: list[tuple[str, str]], limit: int = 6) -> list[dict]:
    """Fetch real CVEs from OSV.dev. Falls back to empty list on error."""
    if not HAS_REQUESTS:
        return []
    results = []
    for ecosystem, pkg in packages:
        if len(results) >= limit:
            break
        try:
            r = requests.post(
                "https://api.osv.dev/v1/query",
                json={"package": {"name": pkg, "ecosystem": ecosystem}},
                timeout=10,
            )
            r.raise_for_status()
            for v in r.json().get("vulns", [])[:2]:
                results.append({
                    "id": v.get("id", ""),
                    "package": pkg,
                    "summary": v.get("summary", "")[:120],
                    "aliases": v.get("aliases", []),
                    "cvss": next((s.get("score") for s in v.get("severity", [])
                                  if s.get("type") == "CVSS_V3"), None),
                })
                if len(results) >= limit:
                    break
        except Exception:
            pass   # silently fall back to offline list
    return results


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

SEV_ICON = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
LINE = "─" * 72


def print_report(results: list[RepoResult], advisories: list[dict]) -> None:
    print(f"\n{'═' * 72}")
    print("  GITHUB VULNERABILITY SCANNER — REPORT")
    print(f"{'═' * 72}\n")

    # ── CVE advisory block ──────────────────────────────────────────────────
    cve_list = advisories if advisories else KNOWN_CVES
    print(f"┌─ CVE / ADVISORY REFERENCE ({len(cve_list)} entries)")
    for a in cve_list:
        cvss = f"  CVSS {a['cvss']:.1f}" if a.get("cvss") else ""
        aliases = ", ".join(a.get("aliases", [])) or ""
        alias_str = f"  [{aliases}]" if aliases else ""
        print(f"│  {a['id']}{alias_str}{cvss}")
        print(f"│    Package : {a['package']}")
        print(f"│    Summary : {a['summary']}")
        vuln_cls = a.get("vuln_class", "")
        if vuln_cls:
            print(f"│    Class   : {vuln_cls}")
        print("│")
    print(f"└{'─' * 70}\n")

    # ── per-repo results ────────────────────────────────────────────────────
    total_hits = sum(r.hit_count for r in results)
    repos_with_hits = [r for r in results if r.hit_count > 0]

    print(f"Scanned {len(results)} repo(s)  ·  {total_hits} vulnerability hit(s)  "
          f"·  {len(repos_with_hits)} repo(s) with findings\n")

    for res in results:
        print(LINE)
        status = f"{res.hit_count} hit(s)" if res.hit_count else "CLEAN / no patterns matched"
        print(f"REPO  : {res.repo_url}")
        print(f"LANG  : {res.language}   STATUS: {status}")
        if res.error:
            print(f"ERROR : {res.error}")
        if not res.hits:
            print()
            continue

        # Deduplicate (same file+line can match multiple patterns)
        seen: set[tuple[str, int, str]] = set()
        unique: list[VulnHit] = []
        for h in res.hits:
            key = (h.file_path, h.line_number, h.vuln_class)
            if key not in seen:
                seen.add(key)
                unique.append(h)

        # Group by severity then class
        by_class: dict[str, list[VulnHit]] = {}
        for h in unique:
            by_class.setdefault(h.vuln_class, []).append(h)

        for cls, hits in sorted(by_class.items(), key=lambda kv: SEV_ORDER.get(kv[1][0].severity, 9)):
            sev = hits[0].severity
            icon = SEV_ICON.get(sev, "⚪")
            print(f"\n  {icon}  {cls}  ({len(hits)} hit{'s' if len(hits) != 1 else ''})  "
                  f"[{sev.upper()}  {hits[0].cwe}]")
            print(f"     {hits[0].explanation}")
            for h in hits[:5]:
                print(f"     {h.file_path}:{h.line_number}")
                print(f"       ▸ {textwrap.shorten(h.line_content.strip(), 88)}")
            if len(hits) > 5:
                print(f"     … and {len(hits) - 5} more hit(s) in this category")
        print()

    # ── summary table ───────────────────────────────────────────────────────
    print(LINE)
    print(f"  {'REPO':<35} {'HITS':>5}  {'SEVERITY BREAKDOWN'}")
    print(f"  {'-'*35}  {'-'*5}  {'-'*30}")
    for res in results:
        sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for h in res.hits:
            sev_counts[h.severity] = sev_counts.get(h.severity, 0) + 1
        sev_str = "  ".join(
            f"{SEV_ICON[s]} {sev_counts[s]}" for s in ["critical", "high", "medium"]
            if sev_counts[s] > 0
        ) or "—"
        short = res.repo_name.split("/")[-1][:35]
        print(f"  {short:<35} {res.hit_count:>5}  {sev_str}")

    print(f"\n  Legend: {SEV_ICON['critical']} Critical  {SEV_ICON['high']} High  "
          f"{SEV_ICON['medium']} Medium  {SEV_ICON['low']} Low")
    print(f"  Note  : Pattern matching — results require manual confirmation.")
    print(f"  These repos are intentionally vulnerable apps for education/CTF use.")
    print(f"{'═' * 72}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

DEFAULT_REPOS = SEED_REPOS[:3]   # scan first 3 seeds by default


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan GitHub repos for vulnerability patterns (educational)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
        Examples:
          # scan default set of known-vulnerable repos
          python3 github_vuln_scanner.py

          # scan specific repos
          python3 github_vuln_scanner.py --repos nicowillis/Vulnerable-Flask-App we45/Vulnerable-Flask-App

          # use more repos, skip OSV network call
          python3 github_vuln_scanner.py --limit 4 --no-osv
        """),
    )
    parser.add_argument("--repos", nargs="+", metavar="OWNER/REPO",
                        help="Repos to scan (e.g. nicowillis/Vulnerable-Flask-App)")
    parser.add_argument("--limit", type=int, default=3,
                        help="Number of repos to scan from the default seed list (default 3)")
    parser.add_argument("--no-osv", action="store_true",
                        help="Skip live OSV.dev advisory fetch, use built-in CVE list")
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"),
                        help="GitHub PAT for higher rate limits (optional)")
    args = parser.parse_args()

    # ── 1. CVE advisories ────────────────────────────────────────────────────
    print("[1/3] Loading CVE / advisory data …")
    advisories: list[dict] = []
    if not args.no_osv:
        print("      Trying OSV.dev …", end=" ", flush=True)
        packages = [("PyPI", "flask"), ("PyPI", "django"), ("PyPI", "pyyaml"),
                    ("npm", "lodash"), ("npm", "express")]
        advisories = fetch_osv_advisories(packages, limit=6)
        if advisories:
            print(f"got {len(advisories)} advisories")
        else:
            print("unreachable — using built-in CVE list")
    else:
        print("      Using built-in CVE list (--no-osv)")

    # ── 2. Resolve target repos ──────────────────────────────────────────────
    print("\n[2/3] Resolving target repositories …")
    if args.repos:
        targets = [(f"https://github.com/{r}", r) for r in args.repos]
    else:
        targets = SEED_REPOS[: args.limit]
    print(f"      Targets: {[t[1] for t in targets]}\n")

    # ── 3. Clone + scan ──────────────────────────────────────────────────────
    print("[3/3] Cloning and scanning …")
    results: list[RepoResult] = []
    workdir = Path(tempfile.mkdtemp(prefix="vuln_scan_"))

    try:
        for url, name in targets:
            dest = workdir / name.replace("/", "__")
            print(f"\n  ┌ {name}")
            print(f"  │ Cloning {url} …", end=" ", flush=True)

            ok = clone_repo(url, dest)
            if not ok:
                print("FAILED")
                results.append(RepoResult(
                    repo_name=name,
                    repo_url=url,
                    language="Unknown",
                    error="Clone failed — repo may be private or unavailable",
                ))
                continue

            print("done")
            files = walk_source_files(dest)
            print(f"  │ Found {len(files)} source files to scan …", end=" ", flush=True)
            res = scan_directory(dest, name, url)
            print(f"{res.hit_count} hit(s)")

            # Show classes immediately
            if res.classes():
                print(f"  └ Vuln classes: {', '.join(res.classes())}")
            else:
                print(f"  └ No patterns matched")

            results.append(res)

    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    # ── 4. Report ─────────────────────────────────────────────────────────────
    print_report(results, advisories)


if __name__ == "__main__":
    main()
