#!/usr/bin/env python3
"""
Cross-platform build orchestrator for AERA Agent.

Run from project root:
    python build_tools/build.py

What it does:
  1. Verifies Python ≥ 3.10
  2. Installs build deps  (pyinstaller, pillow, cairosvg)
  3. Rasterizes assets/aera_icon.svg → .ico (Windows), .icns (macOS), .png
  4. Runs PyInstaller with build_tools/aera.spec
  5. Optionally builds OS-specific installers:
       Windows → Inno Setup script
       macOS   → DMG via create-dmg (if installed)
       Linux   → AppImage (if appimagetool is on PATH)
"""

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
DIST = ROOT / "dist"
BUILD = ROOT / "build"


# ─── helpers ─── #
def run(cmd, **kw):
    print(f"\n▶ {' '.join(map(str, cmd))}")
    return subprocess.run(cmd, check=True, **kw)


def have(executable: str) -> bool:
    return shutil.which(executable) is not None


# ─── steps ─── #
def step_python_check():
    v = sys.version_info
    print(f"Python {v.major}.{v.minor}.{v.micro}")
    if v < (3, 10):
        sys.exit("AERA needs Python 3.10 or newer.")


def step_install_build_deps():
    print("\n=== Installing build dependencies ===")
    run([sys.executable, "-m", "pip", "install", "--upgrade",
         "pip", "pyinstaller>=6.0", "pillow>=10", "cairosvg>=2.7"])


def step_rasterize_icons():
    print("\n=== Rasterizing icons ===")
    svg = ASSETS / "aera_icon.svg"
    if not svg.exists():
        sys.exit(f"Missing {svg}")
    try:
        import cairosvg
        from PIL import Image
        import io
    except ImportError:
        sys.exit("install_build_deps must run first")

    raw = svg.read_bytes()

    def render(size):
        png = cairosvg.svg2png(bytestring=raw, output_width=size, output_height=size)
        return Image.open(io.BytesIO(png)).convert("RGBA")

    render(512).save(ASSETS / "aera_icon.png")
    print(f"  ✓ aera_icon.png")

    # Windows .ico
    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = [render(s) for s in sizes]
    imgs[0].save(ASSETS / "aera_icon.ico", format="ICO",
                 sizes=[(s, s) for s in sizes])
    print(f"  ✓ aera_icon.ico (multi-res)")

    # macOS .icns — assemble via iconutil if available (mac only)
    iconset = ASSETS / "aera.iconset"
    iconset.mkdir(exist_ok=True)
    mac_sizes = [
        (16,  "16x16"),  (32,  "16x16@2x"),
        (32,  "32x32"),  (64,  "32x32@2x"),
        (128, "128x128"), (256, "128x128@2x"),
        (256, "256x256"), (512, "256x256@2x"),
        (512, "512x512"), (1024,"512x512@2x"),
    ]
    for size, label in mac_sizes:
        render(size).save(iconset / f"icon_{label}.png")

    if platform.system() == "Darwin" and have("iconutil"):
        out = ASSETS / "aera_icon.icns"
        run(["iconutil", "-c", "icns", str(iconset), "-o", str(out)])
        print(f"  ✓ aera_icon.icns")
    else:
        print("  (skipped .icns — needs macOS + iconutil)")


def step_pyinstaller():
    print("\n=== Running PyInstaller ===")
    if BUILD.exists(): shutil.rmtree(BUILD)
    if DIST.exists():  shutil.rmtree(DIST)
    run([sys.executable, "-m", "PyInstaller",
         "--noconfirm",
         "--workpath", str(BUILD),
         "--distpath", str(DIST),
         str(ROOT / "build_tools" / "aera.spec")])
    out = DIST / "AERA"
    if out.exists():
        size_mb = sum(p.stat().st_size for p in out.rglob("*")) / 1e6
        print(f"\n✓ Built dist/AERA/  ({size_mb:.1f} MB)")
    if (DIST / "AERA.app").exists():
        print("✓ Built dist/AERA.app  (macOS bundle)")


# ─── OS-specific installers ─── #
def step_installer():
    sysname = platform.system()
    if sysname == "Windows":
        _windows_installer()
    elif sysname == "Darwin":
        _macos_dmg()
    else:
        _linux_appimage()


def _windows_installer():
    iss = ROOT / "build_tools" / "aera_installer.iss"
    if not iss.exists():
        # Write a minimal Inno Setup script if missing
        iss.write_text(_INNO_SETUP_SCRIPT, encoding="utf-8")
    if have("iscc"):
        run(["iscc", str(iss)])
        print("\n✓ Built Windows installer in dist/")
    else:
        print("\n(Skipped Windows installer — install Inno Setup from "
              "https://jrsoftware.org/isdl.php and rerun with --installer)")


def _macos_dmg():
    app = DIST / "AERA.app"
    if not app.exists():
        print("  No .app to package."); return
    if have("create-dmg"):
        dmg = DIST / "AERA.dmg"
        if dmg.exists(): dmg.unlink()
        run(["create-dmg", "--volname", "AERA Agent",
             "--window-size", "540", "340",
             "--app-drop-link", "400", "180",
             str(dmg), str(app)])
        print(f"\n✓ Built {dmg}")
    else:
        print("\n(Skipped DMG — install create-dmg via `brew install create-dmg`)")


def _linux_appimage():
    if not have("appimagetool"):
        print("\n(Skipped AppImage — install appimagetool from "
              "https://github.com/AppImage/AppImageKit/releases)")
        return
    # tiny AppDir bootstrap
    appdir = DIST / "AERA.AppDir"
    if appdir.exists(): shutil.rmtree(appdir)
    appdir.mkdir(parents=True)
    shutil.copytree(DIST / "AERA", appdir / "usr", dirs_exist_ok=True)
    (appdir / "AppRun").write_text(
        '#!/bin/sh\nexec "$(dirname "$(readlink -f "$0")")/usr/AERA" "$@"\n')
    (appdir / "AppRun").chmod(0o755)
    (appdir / "aera.desktop").write_text(
        "[Desktop Entry]\nName=AERA Agent\nExec=AERA\n"
        "Icon=aera_icon\nType=Application\nCategories=Utility;\n")
    shutil.copy(ASSETS / "aera_icon.png", appdir / "aera_icon.png")
    run(["appimagetool", str(appdir), str(DIST / "AERA-x86_64.AppImage")])
    print("\n✓ Built dist/AERA-x86_64.AppImage")


# ─── Inno Setup template (saved on demand) ─── #
_INNO_SETUP_SCRIPT = r"""
; Inno Setup script for AERA Agent.
; Compile with: iscc build_tools\aera_installer.iss
[Setup]
AppName=AERA Agent
AppVersion=0.0.1
AppPublisher=AERA
DefaultDirName={autopf}\AERA
DefaultGroupName=AERA Agent
OutputDir=..\dist
OutputBaseFilename=AERA-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\aera_icon.ico
UninstallDisplayIcon={app}\AERA.exe

[Files]
Source: "..\dist\AERA\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\AERA Agent"; Filename: "{app}\AERA.exe"; IconFilename: "{app}\_internal\assets\aera_icon.ico"
Name: "{commondesktop}\AERA Agent"; Filename: "{app}\AERA.exe"; IconFilename: "{app}\_internal\assets\aera_icon.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\AERA.exe"; Description: "Launch AERA Agent"; Flags: nowait postinstall skipifsilent
"""


# ─── entrypoint ─── #
def main():
    parser = argparse.ArgumentParser(description="Build AERA into a standalone app.")
    parser.add_argument("--no-install-deps", action="store_true",
                        help="Skip installing pyinstaller/pillow/cairosvg")
    parser.add_argument("--no-icons", action="store_true",
                        help="Skip icon rasterization")
    parser.add_argument("--installer", action="store_true",
                        help="Also build OS-specific installer (exe/dmg/AppImage)")
    args = parser.parse_args()

    print(f"== Building AERA on {platform.system()} {platform.release()} ==")
    step_python_check()
    if not args.no_install_deps: step_install_build_deps()
    if not args.no_icons:        step_rasterize_icons()
    step_pyinstaller()
    if args.installer:           step_installer()

    print("\n========================================")
    print(" ✓ BUILD COMPLETE")
    print(f" Output: {DIST}")
    print("========================================")


if __name__ == "__main__":
    main()
