#!/usr/bin/env python3
"""
Cross-platform build orchestrator for AERA Agent – now with full OS installer support.

Run from project root:
    python build_tools/build.py
    python build_tools/build.py --onefile
    python build_tools/build.py --installer
    python build_tools/build.py --all  (onedir + onefile + all installers for current OS)

What it does:
  1. Verifies Python ≥ 3.10
  2. Installs build deps (pyinstaller, pillow, cairosvg, shiv)
  3. Rasterizes assets/aera_icon.svg → .ico (Windows), .icns (macOS), .png
  4. Runs PyInstaller:
     - onedir:  build_tools/aera.spec       -> dist/AERA/ (or AERA.app on macOS)
     - onefile: build_tools/aera_onefile.spec -> dist/AERA.exe / dist/AERA (single file)
  5. Optionally builds OS-specific installers:
     Windows → AERA-Setup.exe (Inno Setup) + AERA.msi (WiX if available) + portable ZIP
     macOS   → AERA.dmg (create-dmg) + AERA.pkg (pkgbuild) + ZIP
     Linux   → AERA-x86_64.AppImage + AERA.deb (dpkg-deb) + tar.gz + ZIP

Designed to fail gracefully: if a tool is missing, prints a friendly skip message
instead of crashing, so you always get at least the PyInstaller bundle.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
DIST = ROOT / "dist"
BUILD = ROOT / "build"

# ------------------------------------------------------------------- #
# Helpers
# ------------------------------------------------------------------- #
def run(cmd, **kw):
    print(f"\n▶ {' '.join(map(str, cmd))}")
    return subprocess.run(cmd, check=True, **kw)

def have(executable: str) -> bool:
    return shutil.which(executable) is not None

def get_version() -> str:
    try:
        import tomllib
        data = tomllib.loads((ROOT / "pyproject.toml").read_text())
        return data.get("project", {}).get("version", "0.0.1")
    except Exception:
        try:
            pyproj = (ROOT / "pyproject.toml").read_text()
            import re
            m = re.search(r'version\s*=\s*"([^"]+)"', pyproj)
            if m:
                return m.group(1)
        except Exception:
            pass
    return "0.0.1"

VERSION = get_version()

# ------------------------------------------------------------------- #
# Steps
# ------------------------------------------------------------------- #
def step_python_check():
    v = sys.version_info
    print(f"Python {v.major}.{v.minor}.{v.micro} – version {VERSION}")
    if v < (3, 10):
        sys.exit("AERA needs Python 3.10 or newer.")

def step_install_build_deps():
    print("\n=== Installing build dependencies ===")
    run([sys.executable, "-m", "pip", "install", "--upgrade",
         "pip", "pyinstaller>=6.0", "pillow>=10", "cairosvg>=2.7", "shiv>=1.0"])

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
        print("  cairosvg/Pillow not installed – skipping rasterize (icons already exist?)")
        return

    raw = svg.read_bytes()

    def render(size):
        png = cairosvg.svg2png(bytestring=raw, output_width=size, output_height=size)
        return Image.open(io.BytesIO(png)).convert("RGBA")

    if not (ASSETS / "aera_icon.png").exists() or True:
        try:
            render(512).save(ASSETS / "aera_icon.png")
            print(f"  ✓ aera_icon.png")
        except Exception as e:
            print(f"  (png failed: {e})")

    try:
        sizes = [16, 24, 32, 48, 64, 128, 256]
        imgs = [render(s) for s in sizes]
        imgs[0].save(ASSETS / "aera_icon.ico", format="ICO",
                     sizes=[(s, s) for s in sizes])
        print(f"  ✓ aera_icon.ico (multi-res)")
    except Exception as e:
        print(f"  (ico failed: {e})")

    # macOS .icns — assemble via iconutil if available (mac only)
    try:
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
    except Exception as e:
        print(f"  (icns failed: {e})")

def step_pyinstaller(spec_name: str = "aera.spec", clean: bool = True):
    spec_path = ROOT / "build_tools" / spec_name
    if not spec_path.exists():
        print(f"  Spec {spec_name} not found, skipping")
        return
    print(f"\n=== Running PyInstaller ({spec_name}) ===")
    if clean and BUILD.exists():
        shutil.rmtree(BUILD)
        # DIST is cleaned only once for first spec; keep for second
        if spec_name == "aera.spec" and DIST.exists():
            shutil.rmtree(DIST)
    run([sys.executable, "-m", "PyInstaller",
         "--noconfirm",
         "--workpath", str(BUILD),
         "--distpath", str(DIST),
         str(spec_path)])
    # summarize
    if (DIST / "AERA").exists():
        size_mb = sum(p.stat().st_size for p in (DIST / "AERA").rglob("*")) / 1e6
        print(f"\n✓ Built dist/AERA/  ({size_mb:.1f} MB)")
    if (DIST / "AERA.exe").exists():
        size_mb = (DIST / "AERA.exe").stat().st_size / 1e6
        print(f"✓ Built dist/AERA.exe (onefile, {size_mb:.1f} MB)")
    if (DIST / "AERA.app").exists():
        print("✓ Built dist/AERA.app  (macOS bundle)")
    if (DIST / "AERA").exists() and (DIST / "AERA").is_file():
        size_mb = (DIST / "AERA").stat().st_size / 1e6
        print(f"✓ Built dist/AERA (onefile binary, {size_mb:.1f} MB)")

def step_pyinstaller_all():
    step_pyinstaller("aera.spec", clean=True)
    # second spec builds onefile, reuse build dir but not dist wipe
    step_pyinstaller("aera_onefile.spec", clean=False)

def step_shiv_bundles():
    print("\n=== Building shiv zipapp bundles (fallback, no libpython needed) ===")
    try:
        # full bundle includes PySide6
        if not (DIST / "AERA.pyz").exists():
            run([sys.executable, "-m", "shiv", "-c", "aera-gui",
                 "-o", str(DIST / "AERA.pyz"), str(ROOT),
                 "--reproducible", "--compressed"])
            print(f"✓ Built {DIST / 'AERA.pyz'}")
        if not (DIST / "AERA-cli.pyz").exists():
            run([sys.executable, "-m", "shiv", "-c", "aera-cli",
                 "-o", str(DIST / "AERA-cli.pyz"), str(ROOT),
                 "--reproducible", "--compressed"])
            print(f"✓ Built {DIST / 'AERA-cli.pyz'}")
    except Exception as e:
        print(f"  (shiv failed: {e})")

def step_portable_zips():
    print("\n=== Building portable zips/tarballs ===")
    try:
        if (DIST / "AERA").is_dir():
            # Linux/macOS tar.gz
            tar_path = DIST / f"AERA-{platform.system().lower()}-{platform.machine()}-{VERSION}.tar.gz"
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(DIST / "AERA", arcname="AERA")
            print(f"✓ Built {tar_path.name}")
            # ZIP for Windows
            zip_path = DIST / f"AERA-{platform.system().lower()}-{VERSION}.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                for f in (DIST / "AERA").rglob("*"):
                    z.write(f, f.relative_to(DIST))
            print(f"✓ Built {zip_path.name}")
        if (DIST / "AERA.app").exists():
            zip_path = DIST / f"AERA-macos-{VERSION}.zip"
            run(["zip", "-r", "-y", str(zip_path), "AERA.app"], cwd=DIST)
            print(f"✓ Built {zip_path.name}")
    except Exception as e:
        print(f"  (portable zip failed: {e})")

# ------------------------------------------------------------------- #
# OS-specific installers
# ------------------------------------------------------------------- #
def step_installer():
    sysname = platform.system()
    print(f"\n=== Building installer for {sysname} ===")
    if sysname == "Windows":
        _windows_installer()
        _windows_msi()
        _windows_portable()
    elif sysname == "Darwin":
        _macos_dmg()
        _macos_pkg()
    else:
        _linux_appimage()
        _linux_deb()
        _linux_tarball()
        _linux_rpm()

# ---------- Windows ---------- #
def _windows_installer():
    iss = ROOT / "build_tools" / "aera_installer.iss"
    if not iss.exists():
        iss.write_text(_INNO_SETUP_SCRIPT, encoding="utf-8")
        print(f"  Created {iss}")
    if have("iscc"):
        run(["iscc", str(iss)])
        print("\n✓ Built Windows installer in dist/ (AERA-Setup.exe)")
    else:
        print("\n(Skipped Windows Setup.exe – install Inno Setup from https://jrsoftware.org/isdl.php)")

def _windows_msi():
    # Try WiX Toolset
    wxs_path = ROOT / "build_tools" / "wix" / "aera.wxs"
    wxs_path.parent.mkdir(exist_ok=True)
    if not wxs_path.exists():
        wxs_path.write_text(_WIX_WXS_TEMPLATE.format(version=VERSION), encoding="utf-8")
        print(f"  Created {wxs_path}")

    if have("candle") and have("light"):
        try:
            # Candle compiles wxs -> wixobj, light links -> msi
            build_dir = BUILD / "wix"
            build_dir.mkdir(parents=True, exist_ok=True)
            run(["candle", str(wxs_path), "-out", str(build_dir / "aera.wixobj"),
                 f"-dVersion={VERSION}", f"-dSourceDir={DIST / 'AERA'}"])
            run(["light", str(build_dir / "aera.wixobj"), "-out", str(DIST / f"AERA-{VERSION}.msi")])
            print(f"\n✓ Built {DIST / f'AERA-{VERSION}.msi'}")
            return
        except Exception as e:
            print(f"  WiX build failed: {e}")

    # Fallback: try msilib (Windows-only stdlib) to create simple MSI
    if platform.system() == "Windows":
        try:
            _build_msi_msilib()
            return
        except Exception as e:
            print(f"  msilib MSI build failed: {e}")

    print("  (Skipped MSI – install WiX Toolset from https://wixtoolset.org/)")

def _build_msi_msilib():
    # Very small MSI that just installs the folder bundle – only works on Windows Python
    import msilib
    from msilib import Directory, Feature, CAB, File
    from pathlib import Path
    msi_path = DIST / f"AERA-{VERSION}.msi"
    print(f"  Building MSI via msilib -> {msi_path}")
    # Minimal – real implementation would enumerate files
    # For brevity, we just document; full impl is ~200 lines
    # We create an empty MSI placeholder if needed
    raise NotImplementedError("msilib full impl skipped – use WiX for production")

def _windows_portable():
    # Already handled by step_portable_zips
    pass

# ---------- macOS ---------- #
def _macos_dmg():
    app = DIST / "AERA.app"
    if not app.exists():
        print("  No .app to package for DMG."); return
    if have("create-dmg"):
        dmg = DIST / f"AERA-{VERSION}.dmg"
        if dmg.exists(): dmg.unlink()
        run(["create-dmg", "--volname", "AERA Agent",
             "--window-size", "540", "340",
             "--app-drop-link", "400", "180",
             str(dmg), str(app)])
        print(f"\n✓ Built {dmg}")
    else:
        print("\n(Skipped DMG — install create-dmg via `brew install create-dmg`)")

def _macos_pkg():
    app = DIST / "AERA.app"
    if not app.exists():
        print("  No .app to package for PKG."); return
    if have("pkgbuild") and have("productbuild"):
        try:
            # pkgbuild stage
            pkg_root = BUILD / "pkgroot"
            if pkg_root.exists():
                shutil.rmtree(pkg_root)
            pkg_root.mkdir(parents=True)
            shutil.copytree(app, pkg_root / "AERA.app", dirs_exist_ok=True)
            pkg_path = DIST / f"AERA-{VERSION}.pkg"
            run(["pkgbuild", "--root", str(pkg_root),
                 "--identifier", "com.aera.agent",
                 "--version", VERSION,
                 "--install-location", "/Applications",
                 str(pkg_path)])
            print(f"\n✓ Built {pkg_path}")
        except Exception as e:
            print(f"  PKG build failed: {e}")
    else:
        print("  (Skipped PKG – pkgbuild/productbuild only on macOS, Xcode tools needed)")

# ---------- Linux ---------- #
def _linux_appimage():
    if not have("appimagetool"):
        print("\n(Skipped AppImage — install appimagetool from https://github.com/AppImage/AppImageKit/releases)")
        return
    if not (DIST / "AERA").is_dir():
        print("  No dist/AERA to package as AppImage"); return
    appdir = DIST / "AERA.AppDir"
    if appdir.exists(): shutil.rmtree(appdir)
    appdir.mkdir(parents=True)
    shutil.copytree(DIST / "AERA", appdir / "usr", dirs_exist_ok=True)
    (appdir / "AppRun").write_text(
        '#!/bin/sh\nexec "$(dirname "$(readlink -f "$0")")/usr/AERA" "$@"\n')
    (appdir / "AppRun").chmod(0o755)
    (appdir / "aera.desktop").write_text(
        "[Desktop Entry]\nName=AERA Agent\nExec=AERA\n"
        "Icon=aera_icon\nType=Application\nCategories=Utility;AudioVideo;\n")
    shutil.copy(ASSETS / "aera_icon.png", appdir / "aera_icon.png")
    run(["appimagetool", str(appdir), str(DIST / f"AERA-{VERSION}-x86_64.AppImage")])
    print(f"\n✓ Built dist/AERA-{VERSION}-x86_64.AppImage")

def _linux_deb():
    # Build .deb via dpkg-deb (works on Debian/Ubuntu)
    if not (DIST / "AERA").is_dir():
        print("  No dist/AERA to package as DEB"); return
    if not have("dpkg-deb"):
        print("  (Skipped DEB – dpkg-deb not found)")
        return
    try:
        deb_root = BUILD / "deb" / f"aera_{VERSION}_amd64"
        if deb_root.exists():
            shutil.rmtree(deb_root)
        # DEBIAN control
        (deb_root / "DEBIAN").mkdir(parents=True)
        (deb_root / "DEBIAN" / "control").write_text(f"""Package: aera-agent
Version: {VERSION}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: AERA Agent <aera@example.com>
Description: AERA Agent – Voice AI assistant with 46 tools
 A customizable voice assistant with OpenAI-compatible LLM client,
 PySide6 GUI, voice cloning, long-term memory.
Depends: python3, python3-pyside6.qtcore, python3-pyside6.qtwidgets
""")
        # payload: /opt/aera and /usr/bin/aera
        opt_dir = deb_root / "opt" / "aera"
        bin_dir = deb_root / "usr" / "bin"
        apps_dir = deb_root / "usr" / "share" / "applications"
        icons_dir = deb_root / "usr" / "share" / "icons" / "hicolor" / "512x512" / "apps"
        for d in (opt_dir, bin_dir, apps_dir, icons_dir):
            d.mkdir(parents=True, exist_ok=True)
        shutil.copytree(DIST / "AERA", opt_dir, dirs_exist_ok=True)
        # wrapper script
        (bin_dir / "aera").write_text("#!/bin/sh\nexec /opt/aera/AERA \"$@\"\n")
        (bin_dir / "aera").chmod(0o755)
        shutil.copy(ASSETS / "aera_icon.png", icons_dir / "aera-agent.png")
        (apps_dir / "aera-agent.desktop").write_text(
            "[Desktop Entry]\nName=AERA Agent\nExec=/opt/aera/AERA\nIcon=aera-agent\nType=Application\nCategories=Utility;\n")
        deb_path = DIST / f"AERA_{VERSION}_amd64.deb"
        run(["dpkg-deb", "--build", str(deb_root), str(deb_path)])
        print(f"\n✓ Built {deb_path}")
    except Exception as e:
        print(f"  DEB build failed: {e}")

def _linux_tarball():
    if not (DIST / "AERA").is_dir():
        return
    try:
        tar_path = DIST / f"AERA-{VERSION}-linux-x86_64.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(DIST / "AERA", arcname="AERA")
        print(f"\n✓ Built {tar_path.name}")
    except Exception as e:
        print(f"  Tarball failed: {e}")

def _linux_rpm():
    if not have("rpmbuild") and not have("fpm"):
        print("  (Skipped RPM – rpmbuild or fpm not found)")
        return
    try:
        if have("fpm"):
            rpm_path = DIST / f"AERA-{VERSION}.rpm"
            run(["fpm", "-s", "dir", "-t", "rpm",
                 "-n", "aera-agent", "-v", VERSION,
                 "--prefix", "/opt/aera",
                 "--after-install", "/dev/null",
                 "-p", str(rpm_path),
                 f"{DIST / 'AERA'}/=/opt/aera/"])
            print(f"\n✓ Built {rpm_path}")
        else:
            print("  (RPM via rpmbuild not yet implemented, use fpm: gem install fpm)")
    except Exception as e:
        print(f"  RPM build failed: {e}")

# ------------------------------------------------------------------- #
# Templates
# ------------------------------------------------------------------- #
_INNO_SETUP_SCRIPT = r"""
; Inno Setup script for AERA Agent – Windows EXE installer.
; Compile with: iscc build_tools\aera_installer.iss
[Setup]
AppName=AERA Agent
AppVersion=0.0.1
AppPublisher=AERA
AppPublisherURL=https://github.com/manoj-dahal/Aera
DefaultDirName={autopf}\AERA Agent
DefaultGroupName=AERA Agent
OutputDir=..\dist
OutputBaseFilename=AERA-Setup-0.0.1
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\aera_icon.ico
UninstallDisplayIcon={app}\AERA.exe
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\AERA\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\assets\aera_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\AERA Agent"; Filename: "{app}\AERA.exe"; IconFilename: "{app}\aera_icon.ico"
Name: "{group}\Uninstall AERA Agent"; Filename: "{uninstallexe}"
Name: "{commondesktop}\AERA Agent"; Filename: "{app}\AERA.exe"; IconFilename: "{app}\aera_icon.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\AERA.exe"; Description: "Launch AERA Agent"; Flags: nowait postinstall skipifsilent
"""

_WIX_WXS_TEMPLATE = r"""<?xml version="1.0" encoding="UTF-8"?>
<!-- WiX Toolset source for AERA Agent MSI – Windows Installer -->
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*" Name="AERA Agent" Language="1033" Version="{version}" Manufacturer="AERA" UpgradeCode="A1B2C3D4-E5F6-47G8-H9I0-J1K2L3M4N5O6">
    <Package InstallerVersion="200" Compressed="yes" InstallScope="perMachine" Description="AERA Agent Voice Assistant" Comments="Voice AI Assistant" />
    <MajorUpgrade DowngradeErrorMessage="A newer version is already installed." />
    <MediaTemplate EmbedCab="yes" />
    <Feature Id="ProductFeature" Title="AERA Agent" Level="1">
      <ComponentGroupRef Id="AeraFiles" />
    </Feature>
    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="ProgramFilesFolder">
        <Directory Id="AERADIR" Name="AERA Agent">
          <Directory Id="INSTALLFOLDER" Name="AERA" />
        </Directory>
      </Directory>
      <Directory Id="ProgramMenuFolder">
        <Directory Id="ApplicationProgramsFolder" Name="AERA Agent"/>
      </Directory>
      <Directory Id="DesktopFolder" Name="Desktop" />
    </Directory>
    <DirectoryRef Id="INSTALLFOLDER">
      <Component Id="AeraExecutable" Guid="*">
        <File Id="AeraExe" Source="$(var.SourceDir)/AERA.exe" KeyPath="yes">
          <Shortcut Id="StartMenuShortcut" Directory="ApplicationProgramsFolder" Name="AERA Agent" WorkingDirectory="INSTALLFOLDER" Icon="AeraIcon.exe" />
          <Shortcut Id="DesktopShortcut" Directory="DesktopFolder" Name="AERA Agent" WorkingDirectory="INSTALLFOLDER" Icon="AeraIcon.exe" />
        </File>
      </Component>
    </DirectoryRef>
    <DirectoryRef Id="AERADIR">
      <ComponentGroup Id="AeraFiles" Directory="INSTALLFOLDER">
        <!-- Note: In production you would use heat.exe to harvest files: heat dir $(var.SourceDir) -cg AeraFiles -dr INSTALLFOLDER -gg -srd -out files.wxs -->
        <Component Id="CMP_AeraFolder" Guid="*">
          <File Id="Dummy" Source="$(var.SourceDir)/AERA.exe" />
        </Component>
      </ComponentGroup>
    </DirectoryRef>
    <Icon Id="AeraIcon.exe" SourceFile="..\\assets\\aera_icon.ico" />
  </Product>
</Wix>
"""

# ------------------------------------------------------------------- #
# Entrypoint
# ------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="Build AERA into a standalone app with installers.")
    parser.add_argument("--no-install-deps", action="store_true", help="Skip installing pyinstaller/pillow/cairosvg/shiv")
    parser.add_argument("--no-icons", action="store_true", help="Skip icon rasterization")
    parser.add_argument("--installer", action="store_true", help="Also build OS-specific installer (exe/dmg/AppImage/deb)")
    parser.add_argument("--onefile", action="store_true", help="Build one-file executable (dist/AERA.exe / dist/AERA)")
    parser.add_argument("--all", action="store_true", help="Build both onedir + onefile + shiv pyz + portable zips + installer")
    args = parser.parse_args()

    print(f"== Building AERA {VERSION} on {platform.system()} {platform.release()} == {platform.machine()} ==")
    step_python_check()
    if not args.no_install_deps:
        step_install_build_deps()
    if not args.no_icons:
        step_rasterize_icons()

    if args.onefile:
        step_pyinstaller("aera_onefile.spec", clean=True)
    elif args.all:
        step_pyinstaller_all()
        step_shiv_bundles()
        step_portable_zips()
        step_installer()
    else:
        step_pyinstaller("aera.spec", clean=True)
        if args.installer:
            step_shiv_bundles()
            step_portable_zips()
            step_installer()

    print("\n========================================")
    print(" ✓ BUILD COMPLETE")
    print(f" Output dir: {DIST} – version {VERSION}")
    if DIST.exists():
        for f in sorted(DIST.iterdir()):
            size = f.stat().st_size / 1e6 if f.is_file() else sum(p.stat().st_size for p in f.rglob("*")) / 1e6
            print(f"  - {f.name} ({size:.1f} MB)" if f.is_file() else f"  - {f.name}/ ({size:.1f} MB)")
    print("========================================\n")
    print("Installers built per OS:")
    print("  Windows: AERA/ (folder) + AERA.exe (onefile) + AERA-Setup.exe (Inno) + AERA.msi (WiX if available) + ZIP")
    print("  macOS:   AERA.app + AERA.dmg (create-dmg) + AERA.pkg (pkgbuild) + ZIP")
    print("  Linux:   AERA/ + AERA-x86_64.AppImage + AERA_amd64.deb + tar.gz + ZIP + pyz shiv bundles")
    print("\nTo make lightweight desktop tar: make light-desktop or see DESKTOP.md")

if __name__ == "__main__":
    main()
