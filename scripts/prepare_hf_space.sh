#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Cách dùng: $0 <thư-mục-đích-ngoài-repo>" >&2
  exit 1
fi
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Only explicitly selected, tracked build inputs are opened/copied. In particular,
# never traverse local notes, source archives, environments or credential files.
python3 - "$repo_dir" "$1" <<'PY'
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2]).resolve()
if destination.is_relative_to(repo) or repo.is_relative_to(destination):
    raise SystemExit("Lỗi: thư mục đích phải nằm ngoài repo và không chứa repo.")
if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
    raise SystemExit("Lỗi: thư mục đích phải chưa tồn tại hoặc đang rỗng; không ghi đè dữ liệu.")

files = {
    "Dockerfile", ".dockerignore", "DEPLOY.md", "backend/requirements.txt",
    "backend/scripts/build_vector_db.py", "data/raw/ctt_et_conditions.json",
    "data/processed/curriculum_approvals.json",
    "data/raw/hust_undergraduate_programs.json",
    "data/raw/hust_program_curriculum_sources.json",
    "data/raw/hust_curriculum_candidates.json",
}
prefixes = (
    "backend/app/", "frontend/", "data/processed/curricula/", "data/documents/",
    "data/raw/official_curricula/", "data/raw/reviewed_curricula/",
)
tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=repo).decode().split("\0")
selected = []
for name in tracked:
    if not name or not (name in files or name.startswith(prefixes)):
        continue
    parts = Path(name).parts
    if any(part.startswith(".env") or part.endswith(".env") or part in {
        "node_modules", "dist", "__pycache__", ".pytest_cache",
    } or part.startswith(".venv") for part in parts):
        continue
    selected.append((name, name))
selected.append(("deploy/hf/README.md", "README.md"))
missing = files - {source for source, _ in selected}
if missing:
    raise SystemExit("Lỗi: thiếu file được git theo dõi: " + ", ".join(sorted(missing)))

# Reject symlinks and large files before copying; never follow a link to a secret.
oversized = []
for source, target in selected:
    path = repo / source
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise SystemExit(f"Lỗi: không đóng gói symlink: {source}")
    if not path.is_file():
        raise SystemExit(f"Lỗi: thiếu file: {source}")
    if path.stat().st_size > 10_000_000:
        oversized.append(f"{target} ({path.stat().st_size} bytes)")
if oversized:
    raise SystemExit("Lỗi: các file vượt 10 MB, không thể đẩy dạng file thường:\n" + "\n".join(oversized))

destination.mkdir(parents=True, exist_ok=True)
for source, target in selected:
    path = destination / target
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo / source, path)

# Verify the actual output as well, so no oversized file can slip into the package.
oversized = [str(path.relative_to(destination)) for path in destination.rglob("*")
             if path.is_file() and path.stat().st_size > 10_000_000]
if oversized:
    raise SystemExit("Lỗi: file đích vượt 10 MB:\n" + "\n".join(oversized))
print(f"Đã chuẩn bị {len(selected)} file tại {destination}; không có .env hoặc file > 10 MB.")
print("Script chưa tạo remote, commit hay push. Thay <user>/<space> trước khi chạy:")
print(f"cd {shlex.quote(os.fspath(destination))} && git init && "
      "git remote add space https://huggingface.co/spaces/<user>/<space> && "
      'git add -A && git commit -m "Deploy" && git push --force space HEAD:main')
PY
