# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import importlib.util

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


project_dir = Path.cwd()
required_packages = ("flet", "faster_whisper")

missing_packages = [
    package
    for package in required_packages
    if importlib.util.find_spec(package) is None
]
if missing_packages:
    raise SystemExit(
        "Missing build dependencies: "
        + ", ".join(missing_packages)
        + "\nActivate the project virtual environment and run:\n"
        + "  python -m pip install -r requirements.txt\n"
        + "Then rebuild with:\n"
        + "  python -m PyInstaller --noconfirm .\\video2text.spec"
    )


def add_optional_tree(datas, source_root: Path, destination_root: Path) -> None:
    if not source_root.exists():
        return

    for source in source_root.rglob("*"):
        if not source.is_file():
            continue
        if source.name.upper() == "README.MD":
            continue
        destination = destination_root / source.relative_to(source_root).parent
        datas.append((str(source), str(destination)))


datas = [(str(project_dir / "images" / "logo.png"), "images")]

add_optional_tree(datas, project_dir / "vendor" / "ffmpeg", Path("vendor") / "ffmpeg")
add_optional_tree(datas, project_dir / "models", Path("models"))

for package in ("flet", "faster_whisper", "ctranslate2", "av"):
    datas += collect_data_files(package)

hiddenimports = []
for package in ("flet", "faster_whisper", "ctranslate2", "av", "tokenizers", "huggingface_hub"):
    hiddenimports += collect_submodules(package)

icon_file = project_dir / "images" / "logo.ico"
icon = str(icon_file) if icon_file.exists() else None

a = Analysis(
    ["main.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Video2Text",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Video2Text",
)
