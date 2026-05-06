# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


project_dir = Path.cwd()


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
    try:
        datas += collect_data_files(package)
    except Exception:
        pass

hiddenimports = []
for package in ("flet", "faster_whisper", "ctranslate2", "av", "tokenizers", "huggingface_hub"):
    try:
        hiddenimports += collect_submodules(package)
    except Exception:
        pass

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
