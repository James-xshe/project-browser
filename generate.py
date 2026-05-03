#!/usr/bin/env python3
"""扫描 ~/projects/ 生成 data.json 供 dashboard 使用。"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECTS_DIR = Path.home() / "projects"
OUTPUT_FILE = Path(__file__).parent / "data.json"
MAX_DEPTH = 3  # 文件树递归深度
IGNORE = {".git", "node_modules", "__pycache__", ".venv", "venv", ".cache", ".next", "dist", "build"}

# 技术栈检测规则
STACK_SIGNALS = {
    "python":    ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"],
    "node":      ["package.json", "yarn.lock", "pnpm-lock.yaml"],
    "go":        ["go.mod", "go.sum"],
    "rust":      ["Cargo.toml"],
    "java":      ["pom.xml", "build.gradle"],
    "docker":    ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
    "react":     [],  # 从 package.json dependencies 检测
    "vue":       [],
    "fastapi":   [],
    "flask":     [],
    "express":   [],
}

EXTENSION_LANG = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".go": "go", ".rs": "rust", ".java": "java",
    ".vue": "vue", ".jsx": "react", ".tsx": "react",
    ".rb": "ruby", ".php": "php", ".c": "c", ".cpp": "cpp",
    ".sh": "shell", ".sql": "sql",
}


def detect_stack(project_path: Path) -> list[str]:
    """检测项目技术栈。"""
    stack = set()
    # 基于文件存在性
    for tech, signals in STACK_SIGNALS.items():
        for sig in signals:
            if (project_path / sig).exists():
                stack.add(tech)
                break
    # 从 package.json 检测框架
    pkg_json = project_path / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "react" in deps or "react-dom" in deps:
                stack.add("react")
            if "vue" in deps:
                stack.add("vue")
            if "express" in deps:
                stack.add("express")
            if "fastapi" in deps or "uvicorn" in deps:
                stack.add("fastapi")
        except (json.JSONDecodeError, OSError):
            pass
    # 从 requirements.txt 检测
    req_txt = project_path / "requirements.txt"
    if req_txt.exists():
        try:
            content = req_txt.read_text().lower()
            if "fastapi" in content:
                stack.add("fastapi")
            if "flask" in content:
                stack.add("flask")
            if "django" in content:
                stack.add("django")
        except OSError:
            pass
    # 基于文件扩展名统计
    ext_counts: dict[str, int] = {}
    try:
        for f in project_path.rglob("*"):
            if f.is_file() and not any(part in IGNORE for part in f.parts):
                ext = f.suffix.lower()
                if ext in EXTENSION_LANG:
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1
    except PermissionError:
        pass
    for ext, lang in EXTENSION_LANG.items():
        if ext_counts.get(ext, 0) > 3:
            stack.add(lang)
    return sorted(stack)


def get_description(project_path: Path) -> str:
    """从 .project.json 或 README 提取描述。"""
    # 优先 .project.json
    meta_file = project_path / ".project.json"
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text())
            return meta.get("description", "")
        except (json.JSONDecodeError, OSError):
            pass
    # 回退 README
    for name in ["README.md", "README.rst", "README.txt", "README"]:
        readme = project_path / name
        if readme.exists():
            try:
                lines = readme.read_text(errors="ignore").splitlines()
                # 跳过标题行，取第一个非空段落
                desc_lines = []
                started = False
                for line in lines:
                    stripped = line.strip()
                    if not started:
                        if stripped and not stripped.startswith("#"):
                            started = True
                            desc_lines.append(stripped)
                        continue
                    if stripped:
                        desc_lines.append(stripped)
                    elif desc_lines:
                        break
                    if len(" ".join(desc_lines)) > 200:
                        break
                return " ".join(desc_lines)[:200]
            except OSError:
                pass
    return ""


def get_file_stats(project_path: Path) -> tuple[int, int]:
    """返回 (文件数, 总大小 bytes)。"""
    count = 0
    total_size = 0
    try:
        for f in project_path.rglob("*"):
            if f.is_file() and not any(part in IGNORE for part in f.parts):
                count += 1
                try:
                    total_size += f.stat().st_size
                except OSError:
                    pass
    except PermissionError:
        pass
    return count, total_size


def build_tree(project_path: Path, current: Path, depth: int) -> list[dict]:
    """递归构建文件树。"""
    if depth >= MAX_DEPTH:
        return []
    items = []
    try:
        entries = sorted(current.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return []
    for entry in entries:
        if entry.name.startswith(".") or entry.name in IGNORE:
            continue
        rel = entry.relative_to(project_path)
        if entry.is_dir():
            children = build_tree(project_path, entry, depth + 1)
            items.append({
                "name": entry.name,
                "path": str(rel),
                "type": "dir",
                "children": children,
            })
        else:
            try:
                size = entry.stat().st_size
            except OSError:
                size = 0
            items.append({
                "name": entry.name,
                "path": str(rel),
                "type": "file",
                "size": size,
            })
    return items


def scan_project(project_path: Path) -> dict:
    """扫描单个项目。"""
    # 读 .project.json 中的自定义字段
    meta = {}
    meta_file = project_path / ".project.json"
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    file_count, total_size = get_file_stats(project_path)

    # 最后修改时间（取目录 mtime）
    try:
        mtime = datetime.fromtimestamp(project_path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        mtime = None

    # 顶层文件树
    tree = build_tree(project_path, project_path, 0)

    return {
        "name": meta.get("name", project_path.name),
        "dir_name": project_path.name,
        "path": str(project_path),
        "description": meta.get("description", get_description(project_path)),
        "stack": meta.get("stack", detect_stack(project_path)),
        "created": meta.get("created", ""),
        "last_modified": mtime.isoformat() if mtime else "",
        "file_count": file_count,
        "size_kb": round(total_size / 1024),
        "has_git": (project_path / ".git").exists(),
        "has_readme": any((project_path / n).exists() for n in ["README.md", "README.rst", "README.txt", "README"]),
        "tree": tree,
    }


def main():
    if not PROJECTS_DIR.is_dir():
        print(f"Error: {PROJECTS_DIR} not found", file=sys.stderr)
        sys.exit(1)

    projects = []
    for entry in sorted(PROJECTS_DIR.iterdir(), key=lambda e: e.name.lower()):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in IGNORE:
            continue
        projects.append(scan_project(entry))

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "projects_dir": str(PROJECTS_DIR),
        "project_count": len(projects),
        "projects": projects,
    }

    OUTPUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"Generated {OUTPUT_FILE} — {len(projects)} projects scanned")


if __name__ == "__main__":
    main()
