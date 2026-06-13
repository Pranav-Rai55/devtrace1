"""
Repository Cloning & File Traversal — Speed-Optimized
Key optimisations:
  • Parallel file reading with ThreadPoolExecutor
  • chardet only on files that fail UTF-8 decode (not every file)
  • File-size check via stat, not read
  • Single os.walk with compiled extension set lookup
"""

import os
import shutil
import socket
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional
from git import Repo, GitCommandError
from app.config import settings

SUPPORTED_EXT = frozenset({
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go",
    ".rb", ".php", ".cs", ".cpp", ".c", ".h", ".rs",
    ".swift", ".kt", ".scala", ".sh", ".yaml", ".yml",
    ".json", ".toml", ".md",
})

IGNORED_DIRS = frozenset({
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "env", "dist", "build", ".next", ".nuxt", "coverage",
    ".pytest_cache", ".mypy_cache", "vendor", "target",
    ".tox", "eggs", ".eggs", "htmlcov", ".cache",
})

LANG_MAP: Dict[str, str] = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".jsx": "JavaScript", ".tsx": "TypeScript", ".java": "Java",
    ".go": "Go", ".rb": "Ruby", ".php": "PHP", ".cs": "C#",
    ".cpp": "C++", ".c": "C", ".h": "C/C++ Header",
    ".rs": "Rust", ".swift": "Swift", ".kt": "Kotlin",
    ".scala": "Scala", ".sh": "Shell",
    ".yaml": "YAML", ".yml": "YAML",
    ".json": "JSON", ".toml": "TOML", ".md": "Markdown",
}

MAX_FILE_BYTES = settings.MAX_FILE_SIZE_KB * 1024

# Clone timeout in seconds — enforced via socket default timeout
CLONE_TIMEOUT_SECONDS = 120


class RepoFile:
    __slots__ = ("path", "relative_path", "content", "language", "lines", "line_count")

    def __init__(self, path: str, relative_path: str, content: str, language: str):
        self.path          = path
        self.relative_path = relative_path
        self.content       = content
        self.language      = language
        self.lines         = content.splitlines()
        self.line_count    = len(self.lines)


def _read_file(args) -> Optional[RepoFile]:
    """Read a single file. Returns None on error or oversized file."""
    filepath, relative_path, ext = args
    try:
        size = os.stat(filepath).st_size
        if size == 0 or size > MAX_FILE_BYTES:
            return None
        raw = open(filepath, "rb").read()
        # Fast path: try UTF-8 first (covers ~95 % of code files)
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            # Slow path: use chardet only when UTF-8 fails
            try:
                import chardet
                enc = chardet.detect(raw).get("encoding") or "latin-1"
            except ImportError:
                enc = "latin-1"
            content = raw.decode(enc, errors="replace")
        return RepoFile(filepath, relative_path, content, LANG_MAP.get(ext, "Unknown"))
    except Exception:
        return None


class RepositoryCloner:

    def __init__(self, repo_url: str, task_id: str):
        self.repo_url  = repo_url
        self.task_id   = task_id
        self.clone_dir = os.path.join(settings.CLONE_BASE_DIR, task_id)
        self.repo: Optional[Repo] = None
        self.source_kind = "local" if self._looks_like_local_path(repo_url) else "remote"

    def _looks_like_local_path(self, value: str) -> bool:
        return Path(value).expanduser().exists()

    def _local_repo_path(self) -> Path:
        return Path(self.repo_url).expanduser().resolve()

    def clone(self) -> str:
        # Always start clean
        if os.path.exists(self.clone_dir):
            shutil.rmtree(self.clone_dir, ignore_errors=True)

        if self.source_kind == "local":
            return self._clone_local_repository()

        clone_url = self.repo_url
        if settings.GITHUB_TOKEN and "https://github.com/" in self.repo_url:
            clone_url = self.repo_url.replace(
                "https://github.com/",
                f"https://{settings.GITHUB_TOKEN}@github.com/",
            )

        # Disable interactive prompts (e.g. for private repos without a token)
        os.environ["GIT_TERMINAL_PROMPT"] = "0"

        # Set a socket-level timeout so the clone doesn't hang forever.
        # GitPython's Repo.clone_from() does NOT support a --timeout flag —
        # that flag doesn't exist in git. We use socket.setdefaulttimeout()
        # instead, which applies to all network I/O in this thread.
        old_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(CLONE_TIMEOUT_SECONDS)
            self.repo = Repo.clone_from(
                clone_url,
                self.clone_dir,
                depth=5,       # shallow clone — only last 5 commits
                single_branch=True,  # skip fetching all remote branches
            )
            return self.clone_dir
        except GitCommandError as e:
            raise ValueError(f"Failed to clone repository: {e}")
        except socket.timeout:
            raise ValueError(
                f"Clone timed out after {CLONE_TIMEOUT_SECONDS}s. "
                "The repository may be too large or the network too slow."
            )
        except Exception as e:
            raise ValueError(f"Clone error: {e}")
        finally:
            socket.setdefaulttimeout(old_timeout)

    def _clone_local_repository(self) -> str:
        src = self._local_repo_path()
        if not src.exists():
            raise ValueError(f"Local repository path not found: {src}")
        if not src.is_dir():
            raise ValueError("Local repository input must be a directory.")

        try:
            self.repo = Repo(src)
            self.repo = Repo.clone_from(str(src), self.clone_dir, depth=10)
            return self.clone_dir
        except Exception:
            pass

        shutil.copytree(
            src,
            self.clone_dir,
            ignore=shutil.ignore_patterns(*IGNORED_DIRS),
            dirs_exist_ok=True,
        )
        self.repo = None
        return self.clone_dir

    def get_all_files(self) -> List[RepoFile]:
        """Walk repo and read all supported files in parallel."""
        tasks = []
        base  = Path(self.clone_dir)

        for root, dirs, filenames in os.walk(self.clone_dir):
            # Prune in-place to avoid descending into ignored dirs
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for name in filenames:
                ext = Path(name).suffix.lower()
                if ext not in SUPPORTED_EXT:
                    continue
                fp  = os.path.join(root, name)
                rel = str(Path(fp).relative_to(base)).replace("\\", "/")
                tasks.append((fp, rel, ext))

        files: List[RepoFile] = []
        worker_count = min(32, max(4, (os.cpu_count() or 4) * 2))
        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            for result in pool.map(_read_file, tasks):
                if result is not None:
                    files.append(result)

        return files

    def get_commit_history(self, limit: int = 10) -> List[Dict]:
        if not self.repo:
            return []
        commits = []
        try:
            for commit in list(self.repo.iter_commits(max_count=limit)):
                commits.append({
                    "sha":           commit.hexsha[:8],
                    "message":       commit.message.strip()[:80],
                    "author":        commit.author.name,
                    "date":          commit.committed_datetime.isoformat(),
                    "files_changed": len(commit.stats.files),
                })
        except Exception:
            pass
        return commits

    def cleanup(self):
        if os.path.exists(self.clone_dir):
            shutil.rmtree(self.clone_dir, ignore_errors=True)

    @property
    def repo_name(self) -> str:
        if self.source_kind == "local":
            return self._local_repo_path().name
        parts = self.repo_url.rstrip("/").split("/")
        return f"{parts[-2]}/{parts[-1]}" if len(parts) >= 2 else parts[-1]
