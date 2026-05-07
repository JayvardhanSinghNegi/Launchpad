import re
from pathlib import Path
from dataclasses import dataclass, field


PYTHON_DB_DEPS = {"psycopg2", "psycopg2-binary", "pymongo", "sqlalchemy", "SQLAlchemy"}
NODE_DB_DEPS   = {"mongoose", "pg", "mysql2"}

PYTHON_ENTRY_CANDIDATES = ["main.py", "app.py", "run.py", "wsgi.py", "asgi.py"]
NODE_ENTRY_CANDIDATES   = ["index.js", "server.js", "app.js", "main.js"]


@dataclass
class DetectionResult:
    language:    str
    entry_point: str
    port:        int
    secrets:     list[str]        = field(default_factory=list)
    db:          str | None       = None   # "postgres" | "mongo" | None
    raw_dir:     Path | None      = None


def detect(repo_dir: Path) -> DetectionResult:
    repo = Path(repo_dir)

    language    = _detect_language(repo)
    entry_point = _detect_entry(repo, language)
    port        = _detect_port(repo, language, entry_point)
    secrets     = _detect_secrets(repo)
    db          = _detect_db(repo, language)

    return DetectionResult(
        language=language,
        entry_point=entry_point,
        port=port,
        secrets=secrets,
        db=db,
        raw_dir=repo,
    )


# ── Language ─────────────────────────────────────────────────────────────────

def _detect_language(repo: Path) -> str:
    if (repo / "requirements.txt").exists():
        return "python"
    if (repo / "package.json").exists():
        return "node"
    raise RuntimeError(
        "Cannot detect language: neither requirements.txt nor package.json found."
    )


# ── Entry point ───────────────────────────────────────────────────────────────

def _detect_entry(repo: Path, language: str) -> str:
    candidates = PYTHON_ENTRY_CANDIDATES if language == "python" else NODE_ENTRY_CANDIDATES
    for name in candidates:
        if (repo / name).exists():
            return name
    return ""   # empty → caller must prompt


# ── Port ──────────────────────────────────────────────────────────────────────

def _detect_port(repo: Path, language: str, entry_point: str) -> int:
    patterns = [
        r"app\.run\(.*port\s*=\s*(\d+)",
        r"\.listen\(\s*(\d+)",
        r"PORT\s*=\s*['\"]?(\d+)",
        r"process\.env\.PORT\s*\|\|\s*(\d+)",
        r"os\.environ\.get\(['\"]PORT['\"],\s*(\d+)\)",
    ]

    search_files = []
    if entry_point and (repo / entry_point).exists():
        search_files.append(repo / entry_point)

    # also scan common config files
    for extra in ["config.py", "settings.py", "config.js", ".env.example"]:
        p = repo / extra
        if p.exists():
            search_files.append(p)

    for path in search_files:
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return int(m.group(1))

    return 0   # 0 → caller must prompt


# ── Secrets ───────────────────────────────────────────────────────────────────

def _detect_secrets(repo: Path) -> list[str]:
    env_example = repo / ".env.example"
    if not env_example.exists():
        return []

    keys = []
    for line in env_example.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key = line.split("=")[0].strip()
        if key:
            keys.append(key)
    return keys


# ── DB ────────────────────────────────────────────────────────────────────────

def _detect_db(repo: Path, language: str) -> str | None:
    if language == "python":
        req = repo / "requirements.txt"
        if not req.exists():
            return None
        text = req.read_text(errors="ignore").lower()
        deps = {line.split("=")[0].split(">")[0].split("<")[0].strip()
                for line in text.splitlines() if line.strip()}
        if deps & {"psycopg2", "psycopg2-binary", "sqlalchemy"}:
            return "postgres"
        if "pymongo" in deps:
            return "mongo"

    elif language == "node":
        import json
        pkg = repo / "package.json"
        if not pkg.exists():
            return None
        try:
            data = json.loads(pkg.read_text(errors="ignore"))
        except json.JSONDecodeError:
            return None
        all_deps = {
            **data.get("dependencies", {}),
            **data.get("devDependencies", {}),
        }
        if "pg" in all_deps or "mysql2" in all_deps:
            return "postgres"
        if "mongoose" in all_deps:
            return "mongo"

    return None