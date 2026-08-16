# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for Tvorec Cover.

A spec file (rather than long OS-specific CLI flags) keeps the packaged
data files -- theme, translations, ICC profiles, bundled assets and the
in-app manual -- in one place, and PyInstaller's own `datas` tuples don't
need the `;` vs `:` separator juggling the CLI `--add-data` flag requires
between Windows and macOS/Linux.

Run from the project root with:

    uv run pyinstaller packaging/tvorec-cover.spec

PyInstaller does not cross-compile: run this on each OS you want a binary
for. See the `build-release` skill in `.claude/skills/` for the full
workflow.
"""

import sys
from pathlib import Path

project_root = Path(SPECPATH).parent  # noqa: F821 -- SPECPATH is injected by PyInstaller
src = project_root / "src" / "cover_generator"

datas = [
    (str(src / "gui" / "theme.qss"), "cover_generator/gui"),
    (str(src / "i18n" / "cover_generator_bg.qm"), "cover_generator/i18n"),
    (str(src / "resources" / "icc_profiles"), "cover_generator/resources/icc_profiles"),
    (str(src / "resources" / "assets"), "cover_generator/resources/assets"),
    (str(src / "resources" / "docs"), "cover_generator/resources/docs"),
]

if sys.platform == "win32":
    icon = str(src / "resources" / "assets" / "icon.ico")
elif sys.platform == "darwin":
    icon = str(src / "resources" / "assets" / "icon.icns")
else:
    icon = None

a = Analysis(  # noqa: F821 -- Analysis/PYZ/EXE are injected by PyInstaller
    [str(src / "__main__.py")],
    pathex=[str(project_root / "src")],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="tvorec-cover",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    icon=icon,
)
