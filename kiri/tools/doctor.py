from __future__ import annotations
import os
import shutil
import sys
from pathlib import Path
from ..config import VERSION, RUNTIME_VERSION, get_target_triple, get_kiri_home, get_stdlib_dir, get_cache_dir

def run_doctor() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("Kiri Doctor — System & Installation Diagnostics\n")
    issues = 0

    ok_mark = "[OK]"
    fail_mark = "[FAIL]"
    info_mark = "[INFO]"

    # 1. Compiler check
    print(f"{ok_mark} Kiri compiler: v{VERSION}")

    # 2. Runtime check
    print(f"{ok_mark} Kiri runtime: v{RUNTIME_VERSION}")

    # 3. Target architecture
    print(f"{ok_mark} Target: {get_target_triple()}")

    # 4. Installation root
    home = get_kiri_home()
    if home.exists():
        print(f"{ok_mark} Kiri home: {home}")
    else:
        print(f"{fail_mark} Kiri home: Not found at {home}")
        issues += 1

    # 5. Standard library check
    stdlib = get_stdlib_dir()
    if stdlib.exists():
        modules = list(stdlib.glob("*.kiri"))
        print(f"{ok_mark} Standard library: {stdlib} ({len(modules)} modules found)")
    else:
        print(f"{fail_mark} Standard library: Missing at {stdlib}")
        issues += 1

    # 6. Package cache check
    cache = get_cache_dir()
    print(f"{ok_mark} Package cache: {cache}")

    # 7. PATH resolution check
    kiri_bin = shutil.which("kiri")
    if kiri_bin:
        print(f"{ok_mark} PATH integration: Resolved to '{kiri_bin}'")
    else:
        path_env = os.environ.get("PATH", "")
        home_bin = str(home / "bin")
        if home_bin in path_env or str(home) in path_env:
            print(f"{ok_mark} PATH integration: Configured for '{home}'")
        else:
            print(f"{info_mark} PATH integration: 'kiri' not in current PATH (run installer to register globally)")

    # 8. File association check (Windows)
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.kiri") as key:
                prog_id, _ = winreg.QueryValueEx(key, "")
                print(f"{ok_mark} File association: .kiri -> {prog_id}")
        except Exception:
            print(f"{info_mark} File association: .kiri not registered in Windows Registry (run installer to register)")

    print()
    if issues == 0:
        print("Everything looks good! Your Kiri installation is ready for production.")
        return 0
    else:
        print(f"Kiri Doctor found {issues} issue(s). Consider running the installer.")
        return 1
