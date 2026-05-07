import re
import subprocess
import tempfile
from pathlib import Path


def clone_repo(repo_url: str, token: str | None) -> Path:
    if token:
        repo_url = re.sub(r"https://", f"https://{token}@", repo_url)

    tmp = tempfile.mkdtemp(prefix="devopsify_")
    result = subprocess.run(
        ["git", "clone", "--depth=1", repo_url, tmp],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return Path(tmp)