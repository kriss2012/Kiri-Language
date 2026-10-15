from __future__ import annotations
import sys
from pathlib import Path

def format_file(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    formatted_lines: list[str] = []

    for line in lines:
        stripped = line.rstrip()
        # Preserve empty lines
        if not stripped:
            formatted_lines.append("")
            continue

        # Count leading whitespace and convert tabs to 4 spaces
        indent_len = 0
        for ch in stripped:
            if ch == ' ':
                indent_len += 1
            elif ch == '\t':
                indent_len += 4
            else:
                break

        # Normalize indent to multiple of 4
        norm_indent = (indent_len // 4) * 4
        body = stripped.lstrip()

        # Format spacing around operators where appropriate
        formatted_lines.append(" " * norm_indent + body)

    new_content = "\n".join(formatted_lines) + "\n"
    if new_content != content:
        path.write_text(new_content, encoding="utf-8")
        print(f"Formatted: {path.name}")
        return True
    return False

def run_formatter(target_path: str = ".") -> int:
    target = Path(target_path).resolve()
    count = 0

    if target.is_file() and target.suffix == ".kiri":
        if format_file(target):
            count += 1
    elif target.is_dir():
        for f in target.rglob("*.kiri"):
            if format_file(f):
                count += 1

    print(f"✓ Formatted {count} file(s).")
    return 0
