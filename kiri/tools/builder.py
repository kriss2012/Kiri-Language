from __future__ import annotations
import base64
import hashlib
import io
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path
from ..config import VERSION, RUNTIME_VERSION, get_target_triple, get_kiri_home, get_stdlib_dir

def build_kiripack(source_path: str, output_path: str | None = None) -> int:
    src_file = Path(source_path).resolve()
    if not src_file.exists():
        print(f"Error: Source file '{source_path}' does not exist.", file=sys.stderr)
        return 1

    app_name = src_file.stem
    out_file = Path(output_path).resolve() if output_path else src_file.with_suffix(".kiripack")

    source_code = src_file.read_text(encoding="utf-8")
    checksum = hashlib.sha256(source_code.encode("utf-8")).hexdigest()

    manifest = {
        "format": "kiripack-v1",
        "name": app_name,
        "version": "1.0.0",
        "entry": src_file.name,
        "target": get_target_triple(),
        "compiler_version": VERSION,
        "runtime_version": RUNTIME_VERSION,
        "sha256": checksum
    }

    with zipfile.ZipFile(out_file, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        zf.writestr(src_file.name, source_code)

    print(f"[OK] Built portable package: {out_file.name}")
    print(f"     Target:  {get_target_triple()}")
    print(f"     Payload: {out_file.stat().st_size} bytes")
    print(f"     Run with: kiri {out_file.name}")
    return 0

def build_standalone(source_path: str, release: bool = True, output_path: str | None = None) -> int:
    src_file = Path(source_path).resolve()
    if not src_file.exists():
        print(f"Error: Source file '{source_path}' does not exist.", file=sys.stderr)
        return 1

    app_name = src_file.stem
    source_code = src_file.read_text(encoding="utf-8")
    kiri_pkg_dir = Path(__file__).resolve().parent.parent

    # Build ZIP with forward slashes for zipimport compatibility
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("entry.kiri", source_code)
        
        # Include kiri modules with POSIX path separators
        for root, _, files in os.walk(kiri_pkg_dir):
            for file in files:
                if file.endswith(".py"):
                    full_p = Path(root) / file
                    rel_p = full_p.relative_to(kiri_pkg_dir.parent).as_posix()
                    zf.write(full_p, rel_p)

        # Include standard library
        stdlib_dir = get_stdlib_dir()
        if stdlib_dir.exists():
            for std_file in stdlib_dir.glob("*.kiri"):
                zf.write(std_file, f"stdlib/{std_file.name}")

    zip_bytes = zip_buffer.getvalue()
    b64_payload = base64.b64encode(zip_bytes).decode("ascii")

    dist_dir = src_file.parent / "dist"
    dist_dir.mkdir(exist_ok=True)

    if os.name == "nt":
        exe_file = dist_dir / f"{app_name}.cmd"
        runner_content = f"""@echo off & py -3 -x "%~f0" %* & exit /b %errorlevel%
# --- Kiri Standalone Executable: {app_name} ---
# Target: {get_target_triple()} | Runtime: {RUNTIME_VERSION}
import base64, io, os, sys, tempfile, zipfile

PAYLOAD = b"{b64_payload}"

with tempfile.TemporaryDirectory() as tmpdir:
    zip_path = os.path.join(tmpdir, "app.zip")
    with open(zip_path, "wb") as f:
        f.write(base64.b64decode(PAYLOAD))
    sys.path.insert(0, zip_path)
    from kiri.engine import KiriEngine
    with zipfile.ZipFile(zip_path) as zf:
        code = zf.read("entry.kiri").decode("utf-8")
    engine = KiriEngine()
    res = engine.execute(code, "entry.kiri")
    if not res.success:
        print(res.formatted_errors, file=sys.stderr)
        sys.exit(1)
"""
        exe_file.write_text(runner_content, encoding="utf-8")
    else:
        exe_file = dist_dir / app_name
        runner_content = f"""#!/bin/sh
exec py -3 -x "$0" "$@"
# --- Kiri Standalone Executable: {app_name} ---
import base64, io, os, sys, tempfile, zipfile

PAYLOAD = b"{b64_payload}"

with tempfile.TemporaryDirectory() as tmpdir:
    zip_path = os.path.join(tmpdir, "app.zip")
    with open(zip_path, "wb") as f:
        f.write(base64.b64decode(PAYLOAD))
    sys.path.insert(0, zip_path)
    from kiri.engine import KiriEngine
    with zipfile.ZipFile(zip_path) as zf:
        code = zf.read("entry.kiri").decode("utf-8")
    engine = KiriEngine()
    res = engine.execute(code, "entry.kiri")
    if not res.success:
        print(res.formatted_errors, file=sys.stderr)
        sys.exit(1)
"""
        exe_file.write_text(runner_content, encoding="utf-8")
        exe_file.chmod(0o755)

    print(f"[OK] Built standalone executable: {exe_file}")
    print(f"     Target:   {get_target_triple()}")
    print(f"     Release:  {release}")
    print(f"     Size:     {exe_file.stat().st_size} bytes")
    print(f"     Run directly: {exe_file.name}")
    return 0

def run_kiripack(pack_path: str) -> int:
    path = Path(pack_path).resolve()
    if not path.exists():
        print(f"Error: Kiripack file '{pack_path}' not found.", file=sys.stderr)
        return 1

    try:
        with zipfile.ZipFile(path, "r") as zf:
            manifest_data = zf.read("manifest.json").decode("utf-8")
            manifest = json.loads(manifest_data)
            entry = manifest.get("entry", "main.kiri")
            code = zf.read(entry).decode("utf-8")

        from ..engine import KiriEngine
        engine = KiriEngine()
        result = engine.execute(code, entry)
        if not result.success:
            print(result.formatted_errors, file=sys.stderr)
            return 1
        return 0
    except Exception as e:
        print(f"Error running {pack_path}: {e}", file=sys.stderr)
        return 1
