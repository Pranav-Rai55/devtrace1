"""
Phase 3 — Real AI Fix Engine
Uses Anthropic Claude API (or OpenAI) to generate actual working code fixes.
Falls back to smart template fixes if no API key is configured.
"""

import json
import urllib.request
import urllib.error
from typing import Optional
from dataclasses import dataclass
from app.config import settings


@dataclass
class CodeFix:
    original_issue: str
    fixed_code: str
    explanation: str
    confidence: float  # 0-1
    ai_generated: bool = False


# ── Template fixes for when no AI API is configured ───────────────
TEMPLATE_FIXES = {
    "SQL Injection": {
        "fixed_code": "# Use parameterized queries\ncursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
        "explanation": "Replace string formatting with parameterized queries to prevent SQL injection.",
    },
    "Hardcoded Password": {
        "fixed_code": "import os\npassword = os.environ.get('DB_PASSWORD')\nif not password:\n    raise ValueError('DB_PASSWORD environment variable not set')",
        "explanation": "Move secrets to environment variables. Never hardcode credentials.",
    },
    "Hardcoded API Key": {
        "fixed_code": "import os\napi_key = os.environ.get('API_KEY')\nif not api_key:\n    raise ValueError('API_KEY environment variable not set')",
        "explanation": "Store API keys in environment variables or a secrets manager.",
    },
    "Weak Hash Algorithm": {
        "fixed_code": "import hashlib\nhash = hashlib.sha256(data.encode()).hexdigest()\n# For passwords, use bcrypt:\nimport bcrypt\nhashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())",
        "explanation": "Replace MD5/SHA1 with SHA-256 or bcrypt for password hashing.",
    },
    "SSL Certificate Verification Disabled": {
        "fixed_code": "import requests\n# Always verify SSL certificates\nresponse = requests.get(url, verify=True, timeout=10)\n# Or with a custom CA bundle:\nresponse = requests.get(url, verify='/path/to/ca-bundle.crt')",
        "explanation": "Never disable SSL verification. Use proper certificates in production.",
    },
    "Blocking I/O in Async Function": {
        "fixed_code": "import asyncio\nimport aiofiles\nimport httpx\n\nasync def fetch_data():\n    # Use async sleep\n    await asyncio.sleep(1)\n    # Use async file I/O\n    async with aiofiles.open('file.txt') as f:\n        content = await f.read()\n    # Use async HTTP client\n    async with httpx.AsyncClient() as client:\n        response = await client.get(url)",
        "explanation": "Replace blocking I/O with async equivalents to avoid blocking the event loop.",
    },
    "N+1 Query Pattern": {
        "fixed_code": "# Bad: N+1\nfor user in users:\n    orders = Order.filter(user_id=user.id)  # N queries\n\n# Good: single query with JOIN or IN\nuser_ids = [u.id for u in users]\norders = Order.filter(user_id__in=user_ids)  # 1 query\n# Or use select_related / prefetch_related in Django:\nusers = User.objects.prefetch_related('order_set').all()",
        "explanation": "Batch database queries to avoid the N+1 problem. Use prefetch_related, select_related, or IN queries.",
    },
    "God Class": {
        "fixed_code": "# Split into focused, single-responsibility classes\nclass UserAuthentication:\n    def login(self): ...\n    def logout(self): ...\n    def validate_token(self): ...\n\nclass UserProfile:\n    def update_profile(self): ...\n    def get_avatar(self): ...\n\nclass UserNotifications:\n    def send_email(self): ...\n    def send_push(self): ...",
        "explanation": "Break the God Class into smaller classes following the Single Responsibility Principle.",
    },
    "eval": {
        "fixed_code": "import ast\n# Safe: only evaluates literals\nresult = ast.literal_eval(user_input)\n# If you need dynamic code, use a safe sandbox:\n# Consider using RestrictedPython or rewriting the logic",
        "explanation": "Replace eval() with ast.literal_eval() for safe literal evaluation. Never eval user input.",
    },
    "Use of eval": {
        "fixed_code": "import ast\nresult = ast.literal_eval(user_input)",
        "explanation": "Replace eval() with ast.literal_eval() for safe literal evaluation.",
    },
    "Insecure Deserialization": {
        "fixed_code": "import json\n# Safe: use JSON instead of pickle\ndata = json.loads(serialized_string)\n# Or use msgpack with strict schema validation\nimport msgpack\ndata = msgpack.unpackb(raw, raw=False)",
        "explanation": "Replace pickle with JSON or msgpack. Pickle can execute arbitrary code on deserialization.",
    },
    "HTTP Request Without Timeout": {
        "fixed_code": "import requests\n# Always set a timeout to prevent hanging\nresponse = requests.get(\n    url,\n    timeout=(3.05, 27)  # (connect timeout, read timeout)\n)\nresponse.raise_for_status()",
        "explanation": "Always set request timeouts to prevent indefinite hangs that cause resource exhaustion.",
    },
    "Long Function": {
        "fixed_code": "# Refactor using the Extract Method pattern:\ndef validate_input(data):\n    \"\"\"Single responsibility: input validation.\"\"\"\n    ...\n\ndef process_data(data):\n    \"\"\"Single responsibility: data processing.\"\"\"\n    ...\n\ndef save_result(result):\n    \"\"\"Single responsibility: persistence.\"\"\"\n    ...\n\ndef main_function(data):\n    validated = validate_input(data)\n    processed = process_data(validated)\n    return save_result(processed)",
        "explanation": "Apply the Extract Method refactoring pattern to break large functions into focused units.",
    },
    "Debug Mode": {
        "fixed_code": "import os\nDEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'\n# In production, ensure DEBUG=false in your environment",
        "explanation": "Control debug mode via environment variables. Never hardcode DEBUG=True.",
    },
    "Weak JWT": {
        "fixed_code": "import secrets\nimport os\n# Generate a cryptographically secure secret\nJWT_SECRET = os.environ.get('JWT_SECRET') or secrets.token_hex(32)\nif len(JWT_SECRET) < 32:\n    raise ValueError('JWT_SECRET must be at least 32 characters')\n# Use RS256 for asymmetric signing:\nfrom jose import jwt\ntoken = jwt.encode(payload, private_key, algorithm='RS256')",
        "explanation": "Use a cryptographically random JWT secret of at least 256 bits. Prefer RS256 over HS256.",
    },
}


class AIFixEngine:
    """Generates code fixes using Anthropic Claude or OpenAI, falling back to templates."""

    def get_fix(self, issue_title: str, code_snippet: str, file_path: str) -> CodeFix:
        # Try Anthropic first
        if settings.ANTHROPIC_API_KEY:
            fix = self._anthropic_fix(issue_title, code_snippet, file_path)
            if fix:
                return fix

        # Try OpenAI
        if settings.OPENAI_API_KEY:
            fix = self._openai_fix(issue_title, code_snippet, file_path)
            if fix:
                return fix

        # Fall back to templates
        return self._template_fix(issue_title)

    def _anthropic_fix(self, issue: str, snippet: str, path: str) -> Optional[CodeFix]:
        """Call Anthropic Claude API for a real code fix."""
        prompt = self._build_prompt(issue, snippet, path)
        try:
            body = json.dumps({
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
                "system": (
                    "You are a senior software engineer. "
                    "Provide a concise, working code fix. "
                    "Respond in JSON: {\"fixed_code\": \"...\", \"explanation\": \"...\"}. "
                    "No markdown, no extra text."
                ),
            }).encode()
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=body,
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                text = data["content"][0]["text"].strip()
                text = text.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(text)
                return CodeFix(
                    original_issue=issue,
                    fixed_code=parsed.get("fixed_code", ""),
                    explanation=parsed.get("explanation", ""),
                    confidence=0.92,
                    ai_generated=True,
                )
        except Exception:
            return None

    def _openai_fix(self, issue: str, snippet: str, path: str) -> Optional[CodeFix]:
        """Call OpenAI API for a real code fix."""
        prompt = self._build_prompt(issue, snippet, path)
        try:
            body = json.dumps({
                "model": "gpt-4o-mini",
                "max_tokens": 512,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": "You are a senior software engineer. Provide a concise working code fix. Respond in JSON: {\"fixed_code\": \"...\", \"explanation\": \"...\"}"},
                    {"role": "user", "content": prompt},
                ],
            }).encode()
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=body,
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                text = data["choices"][0]["message"]["content"]
                parsed = json.loads(text)
                return CodeFix(
                    original_issue=issue,
                    fixed_code=parsed.get("fixed_code", ""),
                    explanation=parsed.get("explanation", ""),
                    confidence=0.88,
                    ai_generated=True,
                )
        except Exception:
            return None

    def _template_fix(self, issue_title: str) -> CodeFix:
        # Try fuzzy match on title keywords
        for key, fix in TEMPLATE_FIXES.items():
            if key.lower() in issue_title.lower() or issue_title.lower() in key.lower():
                return CodeFix(
                    original_issue=issue_title,
                    fixed_code=fix["fixed_code"],
                    explanation=fix["explanation"],
                    confidence=0.7,
                    ai_generated=False,
                )
        return CodeFix(
            original_issue=issue_title,
            fixed_code="# Review the issue and apply best practices for your specific context.",
            explanation=f"Manual review recommended for: {issue_title}",
            confidence=0.3,
            ai_generated=False,
        )

    def _build_prompt(self, issue: str, snippet: str, path: str) -> str:
        parts = [f"Security/quality issue: {issue}"]
        if path:
            parts.append(f"File: {path}")
        if snippet and len(snippet) < 500:
            parts.append(f"Code:\n{snippet}")
        parts.append("Provide a fixed version with a brief explanation.")
        return "\n".join(parts)


_engine: Optional[AIFixEngine] = None


def get_fix_engine() -> AIFixEngine:
    global _engine
    if _engine is None:
        _engine = AIFixEngine()
    return _engine
