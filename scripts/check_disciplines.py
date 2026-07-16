#!/usr/bin/env python3
"""AutoLabeler 强制纪律机器检查器。

实现 AGENTS.md 中可机器化的架构纪律：
    Rule 1: core/ 禁止 import PySide6/PyQt/fastapi/flask/uvicorn
    Rule 3: 禁止 os.environ / os.getcwd / os.chdir
    Rule 4: 路径必须用 pathlib.Path（不能用 os.path.*）
    Rule 5: mapping.json 必须经 MappingManager，禁止裸 json.load
    Rule 6: 异常必须继承 AutoLabelerError 且带 code 字段
    Rule 7: public 函数/类必须有 docstring（简化版，完整检查走 mypy + ruff）

未机器化的纪律（PR review 把关）：
    Rule 2: 入口只接受 dataclass（需上下文判断）
    Rule 8: 不恢复 CLI/JSON 或 runtime service 边界
    Rule 9: 耗时 > 1 秒任务必须 TaskHandle
    Rule 10: 不允许假设前置模块跑过

用法:
    python scripts/check_disciplines.py
    python scripts/check_disciplines.py --paths core utils gui
退出码:
    0 - 全部通过
    1 - 至少一条违规

仅使用标准库，无第三方依赖。
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 默认检查的严格区域
STRICT_DIRS = ["core", "utils"]

# 跳过的归档区域（即使被传入也跳过）
ARCHIVE_DIRS = ["legacy", "tests/fixtures", "__pycache__", ".venv", "venv"]


# ---------- 工具函数 ----------


def _rel(path: Path) -> str:
    """返回相对 ROOT 的 POSIX 风格路径（跨平台一致）。"""
    return path.relative_to(ROOT).as_posix()


def _is_archive(rel_path: str) -> bool:
    return any(seg in rel_path.split("/") for seg in ARCHIVE_DIRS)


def collect_python_files(paths: list[str]) -> list[Path]:
    """收集待检查的 .py 文件。"""
    files: list[Path] = []
    for p in paths:
        path = ROOT / p
        if not path.exists():
            continue
        for f in path.rglob("*.py"):
            if _is_archive(_rel(f)):
                continue
            files.append(f)
    return sorted(files)


def _line_of(text: str, offset: int) -> int:
    return text[:offset].count("\n") + 1


# ---------- Rule 1 ----------

_RULE1_PATTERN = re.compile(
    r"^\s*(?:from|import)\s+(PySide6|PyQt5|PyQt6|fastapi|flask|uvicorn|starlette)\b",
    re.MULTILINE,
)


def check_rule1_no_gui_http_in_core(files: list[Path]) -> list[str]:
    """core/ 禁止 import PySide6/PyQt/fastapi/flask/uvicorn/starlette。"""
    failures: list[str] = []
    for f in files:
        rel = _rel(f)
        if not rel.startswith("core/"):
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in _RULE1_PATTERN.finditer(text):
            failures.append(
                f"  {rel}:{_line_of(text, m.start())}: forbidden in core/: {m.group(0).strip()}"
            )
    return failures


# ---------- Rule 3 ----------

_RULE3_PATTERN = re.compile(r"\b(os\.environ|os\.getcwd|os\.chdir|os\.putenv)\b")


def check_rule3_no_implicit_env(files: list[Path]) -> list[str]:
    """禁止 os.environ / os.getcwd / os.chdir / os.putenv。"""
    failures: list[str] = []
    for f in files:
        rel = _rel(f)
        if not rel.startswith(("core/", "utils/")):
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in _RULE3_PATTERN.finditer(text):
            failures.append(
                f"  {rel}:{_line_of(text, m.start())}: forbidden: {m.group(0)}"
            )
    return failures


# ---------- Rule 4 ----------

_RULE4_PATTERN = re.compile(
    r"\bos\.path\.(join|exists|isfile|isdir|dirname|basename|abspath|splitext|getsize|getmtime)\b"
)


def check_rule4_use_pathlib(files: list[Path]) -> list[str]:
    """路径一律 pathlib.Path，禁止 os.path.*。"""
    failures: list[str] = []
    for f in files:
        rel = _rel(f)
        if not rel.startswith(("core/", "utils/")):
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in _RULE4_PATTERN.finditer(text):
            failures.append(
                f"  {rel}:{_line_of(text, m.start())}: forbidden: {m.group(0)} (use pathlib.Path)"
            )
    return failures


# ---------- Rule 5 ----------

_RULE5_PATTERN = re.compile(
    r"json\.(load|loads)\s*\([^)]{0,200}mapping",
    re.IGNORECASE | re.DOTALL,
)


def check_rule5_no_direct_mapping_json(files: list[Path]) -> list[str]:
    """mapping.json 必须经 MappingManager，禁止裸 json.load。"""
    failures: list[str] = []
    for f in files:
        rel = _rel(f)
        # MappingManager 自身允许
        if rel.endswith("/mapping_manager.py"):
            continue
        if not rel.startswith(("core/", "utils/", "gui/")):
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in _RULE5_PATTERN.finditer(text):
            failures.append(
                f"  {rel}:{_line_of(text, m.start())}: direct json.load(mapping.json) forbidden (use MappingManager)"
            )
    return failures


# ---------- Rule 6 ----------


def _is_exception_class(node: ast.ClassDef) -> bool:
    """简单启发式：类名以 Error/Exception 结尾，或继承名以 Error/Exception 结尾。"""
    if node.name.endswith("Error") or node.name.endswith("Exception"):
        return True
    for base in node.bases:
        name = _base_name(base)
        if name and (name.endswith("Error") or name.endswith("Exception")):
            return True
    return False


def _base_name(base: ast.expr) -> str | None:
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return None


def _has_code_field(node: ast.ClassDef) -> bool:
    for body_node in node.body:
        if isinstance(body_node, ast.AnnAssign) and isinstance(
            body_node.target, ast.Name
        ):
            if body_node.target.id == "code":
                return True
        elif isinstance(body_node, ast.Assign):
            for t in body_node.targets:
                if isinstance(t, ast.Name) and t.id == "code":
                    return True
    return False


def check_rule6_exception_inherits_base(files: list[Path]) -> list[str]:
    """异常必须继承 AutoLabelerError 且具体类带 code 字段。"""
    failures: list[str] = []
    for f in files:
        rel = _rel(f)
        if not rel.startswith(("core/", "utils/")):
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name == "AutoLabelerError":
                continue
            if not _is_exception_class(node):
                continue

            # 检查继承链：必须有一个 base 名字以 Error 或 Exception 结尾且不是内置的
            base_names = [_base_name(b) for b in node.bases]
            base_names = [n for n in base_names if n]
            inherits_app = any(
                (
                    n == "AutoLabelerError"
                    or (n.endswith("Error") and n not in {"Exception", "BaseException"})
                )
                for n in base_names
            )
            inherits_builtin_only = base_names and all(
                n
                in {
                    "Exception",
                    "BaseException",
                    "RuntimeError",
                    "ValueError",
                    "TypeError",
                    "OSError",
                }
                for n in base_names
            )
            if not inherits_app or inherits_builtin_only:
                failures.append(
                    f"  {rel}:{node.lineno}: exception `{node.name}` must inherit AutoLabelerError; "
                    f"currently inherits {base_names or '<none>'}"
                )
                continue

            # Concrete subclasses (CamelCase with 3+ caps) must have `code` field
            upper_count = sum(1 for c in node.name if c.isupper())
            if upper_count >= 3 and not _has_code_field(node):
                failures.append(
                    f"  {rel}:{node.lineno}: exception `{node.name}` missing `code` field"
                )
    return failures


# ---------- Rule 7（简化版） ----------


def check_rule7_public_docstring(files: list[Path]) -> list[str]:
    """public 函数/类必须有 docstring。"""
    failures: list[str] = []
    for f in files:
        rel = _rel(f)
        if not rel.startswith(("core/", "utils/")):
            continue
        if rel.endswith("/__init__.py"):
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                continue
            if node.name.startswith("_"):
                continue
            # dataclass 的字段定义本身不需要 docstring
            # 但 dataclass 类本身要有
            if ast.get_docstring(node):
                continue
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            failures.append(
                f"  {rel}:{node.lineno}: public {kind} `{node.name}` missing docstring"
            )
    return failures


# ---------- 主流程 ----------


CHECKS: list[tuple[str, object]] = [
    ("Rule 1: no GUI/HTTP import in core/", check_rule1_no_gui_http_in_core),
    (
        "Rule 3: no os.environ / os.getcwd / os.chdir / os.putenv",
        check_rule3_no_implicit_env,
    ),
    ("Rule 4: paths must use pathlib.Path (no os.path.*)", check_rule4_use_pathlib),
    (
        "Rule 5: mapping.json must go through MappingManager",
        check_rule5_no_direct_mapping_json,
    ),
    (
        "Rule 6: exceptions must inherit AutoLabelerError with code",
        check_rule6_exception_inherits_base,
    ),
    ("Rule 7: public funcs/classes must have docstrings", check_rule7_public_docstring),
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0] if __doc__ else ""
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        default=STRICT_DIRS,
        help=f"待检查的目录（相对仓库根），默认 {STRICT_DIRS}",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="仅打印失败项",
    )
    args = parser.parse_args()

    files = collect_python_files(args.paths)
    if not files:
        if not args.quiet:
            print(f"[WARN] No .py files under {args.paths}. Skip.")
        return 0

    if not args.quiet:
        print(f"[INFO] Checking {len(files)} Python files in: {', '.join(args.paths)}")
        print(f"[INFO] Archives skipped: {', '.join(ARCHIVE_DIRS)}")
        print()

    total_failures = 0
    for label, check_fn in CHECKS:
        failures = check_fn(files)  # type: ignore[operator]
        if failures:
            print(f"[FAIL] {label} ({len(failures)} violation(s)):")
            for fail in failures:
                print(fail)
            print()
            total_failures += len(failures)
        elif not args.quiet:
            print(f"[OK]   {label}")

    if not args.quiet:
        print()

    if total_failures:
        print(f"[STOP] {total_failures} discipline violation(s) found.")
        print("       Full rule list: AGENTS.md.")
        return 1

    print("[PASS] All mechanical discipline checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
