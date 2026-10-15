from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

# Enable both package and direct script execution
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from kiri.engine import KiriEngine
    from kiri.config import VERSION, RUNTIME_VERSION, get_target_triple, get_kiri_home, get_stdlib_dir, get_cache_dir
    from kiri.runtime.values import KiriValueType
    from kiri.tools.doctor import run_doctor
    from kiri.tools.package_manager import create_new_project, init_current_project, add_package, remove_package, install_packages, generate_lockfile
    from kiri.tools.builder import build_kiripack, build_standalone, run_kiripack
    from kiri.tools.formatter import run_formatter
    from kiri.tools.linter import run_linter
else:
    from .engine import KiriEngine
    from .config import VERSION, RUNTIME_VERSION, get_target_triple, get_kiri_home, get_stdlib_dir, get_cache_dir
    from .runtime.values import KiriValueType
    from .tools.doctor import run_doctor
    from .tools.package_manager import create_new_project, init_current_project, add_package, remove_package, install_packages, generate_lockfile
    from .tools.builder import build_kiripack, build_standalone, run_kiripack
    from .tools.formatter import run_formatter
    from .tools.linter import run_linter

def print_help() -> None:
    print(f"""Kiri Programming Language - v{VERSION}
"Python-level simplicity with systems-language-level performance."

Usage:
    kiri <file.kiri | file.kiripack>     Execute a Kiri source or package
    kiri run <file.kiri>                 Execute a Kiri source file
    kiri build [--standalone] <file>     Build a portable .kiripack or standalone executable
    kiri new <project_name>              Create a new Kiri project
    kiri init                            Initialize a Kiri project in current directory
    kiri add <package>                   Add a project dependency
    kiri remove <package>                Remove a project dependency
    kiri install                         Resolve and install dependencies
    kiri lock                            Generate kiri.lock lockfile
    kiri doctor                          Diagnose installation, PATH, and system status
    kiri env                             Display environment and runtime configuration
    kiri fmt [path]                      Format Kiri source files
    kiri lint [path]                     Lint Kiri source files
    kiri test                            Run project test suite
    kiri repl                            Start interactive REPL
    kiri --version                       Display version information
    kiri --help                          Display this help message
""")

def run_file(path: str) -> int:
    if path.endswith(".kiripack"):
        return run_kiripack(path)

    if not os.path.exists(path):
        print(f"Error: Source file '{path}' does not exist.", file=sys.stderr)
        return 1

    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    engine = KiriEngine()
    result = engine.execute(source, os.path.basename(path))

    if not result.success:
        print(result.formatted_errors, file=sys.stderr)
        return 1
    return 0

def run_env() -> int:
    print(f"Kiri version:          {VERSION}")
    print(f"Runtime version:       {RUNTIME_VERSION}")
    print(f"Target architecture:   {get_target_triple()}")
    print(f"Kiri home:             {get_kiri_home()}")
    print(f"Standard library:      {get_stdlib_dir()}")
    print(f"Package cache:         {get_cache_dir()}")
    return 0

def run_repl() -> int:
    print(f"Kiri {VERSION} ({get_target_triple()})")
    print("Type ':quit' or ':exit' to exit, ':help' for commands.\n")

    engine = KiriEngine()

    while True:
        try:
            line = input(">>> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        trimmed = line.strip()
        if trimmed in (":quit", ":exit"):
            break
        if trimmed == ":help":
            print("REPL commands: :quit, :exit, :help, :clear")
            continue
        if trimmed == ":clear":
            os.system("cls" if os.name == "nt" else "clear")
            continue
        if not trimmed:
            continue

        if trimmed.endswith(":"):
            lines = [line]
            while True:
                try:
                    next_line = input("... ")
                except (EOFError, KeyboardInterrupt):
                    break
                if not next_line.strip():
                    break
                lines.append(next_line)
            line = "\n".join(lines)

        result = engine.execute(line, "<repl>")
        if not result.success:
            print(result.formatted_errors, file=sys.stderr)
        elif result.value.type != KiriValueType.NULL:
            print(result.value.to_repr())

    return 0

def main() -> int:
    args = sys.argv[1:]
    if not args:
        return run_repl()

    cmd = args[0]
    if cmd in ("--version", "-v"):
        print(f"Kiri {VERSION}")
        print(f"Runtime {RUNTIME_VERSION}")
        print(f"Target {get_target_triple()}")
        return 0
    if cmd in ("--help", "-h"):
        print_help()
        return 0
    if cmd == "doctor":
        return run_doctor()
    if cmd == "env":
        return run_env()
    if cmd == "repl":
        return run_repl()
    if cmd == "fmt":
        target = args[1] if len(args) > 1 else "."
        return run_formatter(target)
    if cmd == "lint":
        target = args[1] if len(args) > 1 else "."
        return run_linter(target)
    if cmd == "new":
        if len(args) < 2:
            print("Error: 'kiri new' requires a project name.", file=sys.stderr)
            return 1
        return create_new_project(args[1])
    if cmd == "init":
        return init_current_project()
    if cmd == "add":
        if len(args) < 2:
            print("Error: 'kiri add' requires a package name.", file=sys.stderr)
            return 1
        return add_package(args[1], args[2] if len(args) > 2 else "latest")
    if cmd == "remove":
        if len(args) < 2:
            print("Error: 'kiri remove' requires a package name.", file=sys.stderr)
            return 1
        return remove_package(args[1])
    if cmd == "install":
        return install_packages()
    if cmd == "lock":
        return generate_lockfile(Path.cwd())
    if cmd == "test":
        from tests import run_tests
        return run_tests.main()
    if cmd == "build":
        standalone = "--standalone" in args
        release = "--release" in args or True
        filtered = [a for a in args[1:] if not a.startswith("--")]
        if not filtered:
            print("Error: 'kiri build' requires a target .kiri source file.", file=sys.stderr)
            return 1
        target_file = filtered[0]
        if standalone:
            return build_standalone(target_file, release=release)
        else:
            return build_kiripack(target_file)
    if cmd == "run":
        if len(args) < 2:
            print("Error: 'kiri run' requires a target file.", file=sys.stderr)
            return 1
        return run_file(args[1])

    if cmd.endswith(".kiri") or cmd.endswith(".kiripack") or os.path.exists(cmd):
        return run_file(cmd)

    print(f"Error: Unknown command or file '{cmd}'.", file=sys.stderr)
    print_help()
    return 1

if __name__ == "__main__":
    sys.exit(main())
