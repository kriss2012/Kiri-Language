from __future__ import annotations
import os
import platform
import sys
from pathlib import Path

VERSION = "1.0.0"
RUNTIME_VERSION = "1.0.0"

def get_target_triple() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()

    os_name = {
        "windows": "windows",
        "linux": "linux",
        "darwin": "macos"
    }.get(system, system)

    arch_name = {
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "arm64": "arm64",
        "aarch64": "arm64"
    }.get(machine, machine)

    return f"{arch_name}-{os_name}"

def get_kiri_home() -> Path:
    if "KIRI_HOME" in os.environ and os.environ["KIRI_HOME"]:
        home = Path(os.environ["KIRI_HOME"]).resolve()
        if home.exists():
            return home

    # 1. Check parent of current executable / entrypoint
    entry_dir = Path(__file__).resolve().parent.parent
    if (entry_dir / "stdlib").exists() or (entry_dir / "bin").exists():
        return entry_dir

    # 2. Check standard user installation locations
    if os.name == "nt":
        appdata = os.environ.get("LOCALAPPDATA")
        if appdata:
            user_inst = Path(appdata) / "Kiri"
            if user_inst.exists():
                return user_inst
    else:
        user_inst = Path.home() / ".kiri"
        if user_inst.exists():
            return user_inst

    return entry_dir

def get_stdlib_dir() -> Path:
    home = get_kiri_home()
    stdlib = home / "stdlib"
    if stdlib.exists():
        return stdlib
    return home / "stdlib"

def get_cache_dir() -> Path:
    if os.name == "nt":
        appdata = os.environ.get("LOCALAPPDATA", str(Path.home()))
        cache = Path(appdata) / "Kiri" / "cache"
    else:
        cache = Path.home() / ".kiri" / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    return cache
