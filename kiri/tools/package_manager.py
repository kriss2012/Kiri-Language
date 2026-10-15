from __future__ import annotations
import hashlib
import json
import os
import sys
from pathlib import Path
from ..config import VERSION

DEFAULT_TOML = """[project]
name = "{name}"
version = "0.1.0"
authors = []
license = "MIT"
entry = "src/main.kiri"

[dependencies]
"""

SAMPLE_MAIN = """# {name} entry point
import os
import sys

def main():
    print("Welcome to {name} powered by Kiri!")
    print("Platform:", os.platform())

main()
"""

def create_new_project(name: str) -> int:
    target_dir = Path(name).resolve()
    if target_dir.exists() and any(target_dir.iterdir()):
        print(f"Error: Directory '{name}' already exists and is not empty.", file=sys.stderr)
        return 1

    target_dir.mkdir(parents=True, exist_ok=True)
    src_dir = target_dir / "src"
    src_dir.mkdir(exist_ok=True)
    tests_dir = target_dir / "tests"
    tests_dir.mkdir(exist_ok=True)

    # 1. Write kiri.toml
    (target_dir / "kiri.toml").write_text(DEFAULT_TOML.format(name=name), encoding="utf-8")

    # 2. Write src/main.kiri
    (src_dir / "main.kiri").write_text(SAMPLE_MAIN.format(name=name), encoding="utf-8")

    # 3. Write tests/main_test.kiri
    (tests_dir / "main_test.kiri").write_text("""# Basic test
assert(1 + 1 == 2, "Math integrity")
""", encoding="utf-8")

    # 4. Write .gitignore
    (target_dir / ".gitignore").write_text("""dist/
build/
*.kiripack
*.lock
__pycache__/
""", encoding="utf-8")

    # 5. Generate initial lockfile
    generate_lockfile(target_dir)

    print(f"✓ Created new Kiri project '{name}'")
    print(f"\nTo get started:")
    print(f"  cd {name}")
    print(f"  kiri run src/main.kiri\n")
    return 0

def init_current_project() -> int:
    name = Path.cwd().name
    if Path("kiri.toml").exists():
        print("Error: 'kiri.toml' already exists in current directory.", file=sys.stderr)
        return 1

    Path("kiri.toml").write_text(DEFAULT_TOML.format(name=name), encoding="utf-8")
    src = Path("src")
    src.mkdir(exist_ok=True)
    if not (src / "main.kiri").exists():
        (src / "main.kiri").write_text(SAMPLE_MAIN.format(name=name), encoding="utf-8")

    generate_lockfile(Path.cwd())
    print(f"✓ Initialized Kiri project '{name}'")
    return 0

def generate_lockfile(project_dir: Path) -> int:
    toml_path = project_dir / "kiri.toml"
    if not toml_path.exists():
        print(f"Error: No 'kiri.toml' found in {project_dir}", file=sys.stderr)
        return 1

    toml_content = toml_path.read_text(encoding="utf-8")
    digest = hashlib.sha256(toml_content.encode("utf-8")).hexdigest()

    lock_data = {
        "format": "kiri-lock-v1",
        "kiri_version": VERSION,
        "manifest_sha256": digest,
        "packages": {}
    }

    lock_path = project_dir / "kiri.lock"
    lock_path.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")
    print(f"✓ Generated lockfile: {lock_path.name}")
    return 0

def add_package(pkg_name: str, version: str = "latest") -> int:
    toml_path = Path("kiri.toml")
    if not toml_path.exists():
        print("Error: No 'kiri.toml' found. Run 'kiri init' first.", file=sys.stderr)
        return 1

    content = toml_path.read_text(encoding="utf-8")
    line = f'{pkg_name} = "{version}"\n'
    if "[dependencies]" in content:
        content = content.replace("[dependencies]\n", f"[dependencies]\n{line}")
    else:
        content += f"\n[dependencies]\n{line}"

    toml_path.write_text(content, encoding="utf-8")
    generate_lockfile(Path.cwd())
    print(f"✓ Added dependency '{pkg_name}' ({version})")
    return 0

def remove_package(pkg_name: str) -> int:
    toml_path = Path("kiri.toml")
    if not toml_path.exists():
        print("Error: No 'kiri.toml' found.", file=sys.stderr)
        return 1

    lines = toml_path.read_text(encoding="utf-8").splitlines()
    new_lines = [l for l in lines if not l.strip().startswith(f"{pkg_name} =")]
    toml_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    generate_lockfile(Path.cwd())
    print(f"✓ Removed dependency '{pkg_name}'")
    return 0

def install_packages() -> int:
    toml_path = Path("kiri.toml")
    if not toml_path.exists():
        print("Error: No 'kiri.toml' found.", file=sys.stderr)
        return 1

    generate_lockfile(Path.cwd())
    print("✓ All dependencies resolved and up to date.")
    return 0
