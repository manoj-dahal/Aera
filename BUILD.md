# 🛠 Building AERA Agent – Cross-Platform Desktop Packages

Package AERA into a **standalone executable** for Windows (EXE/MSI), macOS (APP/DMG/PKG), Linux (AppImage/DEB/RPM/tar.gz) and a fallback single-file `pyz`.

---

## TL;DR — one command per OS

| OS | Build command | Primary Output | Installer Output |
|---|---|---|---|
| 🐧 Linux | `bash build_tools/build.sh` | `dist/AERA/AERA` | `dist/AERA-*.AppImage`, `*.deb`, `*.tar.gz`, `*.pyz` |
| 🍎 macOS | `bash build_tools/build.sh` | `dist/AERA.app` | `dist/AERA.dmg`, `dist/AERA.pkg` |
| 🪟 Windows | `build_tools\build.bat` | `dist\AERA\AERA.exe` | `dist\AERA-Setup.exe` (Inno), `dist\AERA.msi` (WiX) |

Add flags:
- `--onefile` → single-file binary `dist/AERA` / `dist/AERA.exe`
- `--installer` → also build OS-specific installer(s)
- `--all` → onedir + onefile + shiv pyz + portable zips/tars + installer

The first run automatically pops up the **setup wizard** so end-users paste their API key.

---

## Full Matrix of Supported Packages

| Platform | Package Type | Tool Needed | Output Example | How to Build |
|---|---|---|---|---|
| **Windows** | Folder bundle | PyInstaller | `dist/AERA/AERA.exe` | `build_tools\build.bat` |
| **Windows** | Single EXE | PyInstaller onefile spec | `dist/AERA.exe` | `build_tools\build.bat --onefile` |
| **Windows** | EXE Installer | Inno Setup `iscc` | `dist/AERA-Setup-0.0.1.exe` | `build_tools\build.bat --installer` |
| **Windows** | MSI Installer | WiX Toolset `candle+light` | `dist/AERA-0.0.1.msi` | `build_tools\build.bat --installer` (if WiX installed) |
| **Windows** | Portable ZIP | 7z / zip | `dist/AERA-windows-0.0.1.zip` | auto in `--all` |
| **Windows** | Self-contained PYZ | shiv | `dist/AERA.pyz` (249MB full) | `make pyz` or `shiv ...` |
| **macOS** | .app Bundle | PyInstaller | `dist/AERA.app` | `bash build_tools/build.sh` |
| **macOS** | DMG | `create-dmg` | `dist/AERA-0.0.1.dmg` | `bash build_tools/build.sh --installer` |
| **macOS** | PKG Installer | `pkgbuild` + `productbuild` (Xcode) | `dist/AERA-0.0.1.pkg` | `--installer` on macOS |
| **macOS** | ZIP | zip | `dist/AERA-macos-0.0.1.zip` | auto |
| **Linux** | Folder binary | PyInstaller | `dist/AERA/AERA` | `bash build_tools/build.sh` |
| **Linux** | AppImage | `appimagetool` | `dist/AERA-0.0.1-x86_64.AppImage` | `--installer` |
| **Linux** | DEB | `dpkg-deb` | `dist/AERA_0.0.1_amd64.deb` | `--installer` (Debian/Ubuntu) |
| **Linux** | RPM | `fpm` or `rpmbuild` | `dist/AERA-0.0.1.rpm` | `--installer` if fpm installed |
| **Linux** | tar.gz | tar | `dist/AERA-0.0.1-linux-x86_64.tar.gz` | auto |
| **Linux** | PYZ full | shiv | `dist/AERA.pyz` (249MB) | `make desktop` |
| **Linux** | PYZ light | zipapp | `dist/AERA-light.pyz` (244KB) | `make light-desktop` |

> PyInstaller bundles do **not** cross-compile – you must build Windows installers on Windows, macOS on macOS, Linux on Linux. Use the provided GitHub Actions release workflow to build all 3 in parallel.

---

## Prerequisites

| | |
|---|---|
| Python | **3.10 or newer** on the *build* machine |
| Disk | ~500 MB free for onedir, ~1 GB for onefile+installers |
| RAM | 2 GB free during PyInstaller analysis |
| Linux | `sudo apt install libxkbcommon0 libegl1 ... libcairo2-dev libpango1.0-dev portaudio19-dev libpython3.12-dev dpkg-dev` |
| macOS | `brew install cairo pango portaudio create-dmg` + Xcode CLI tools |
| Windows | [Inno Setup](https://jrsoftware.org/isdl.php) for Setup.exe, [WiX Toolset](https://wixtoolset.org/) for MSI |

The build script auto-installs Python deps (`pyinstaller`, `pillow`, `cairosvg`, `shiv`).

---

## Step-by-step

### 1. Clone
```bash
git clone https://github.com/manoj-dahal/Aera aera-agent
cd aera-agent
```

### 2. Install runtime deps once (optional, for testing)
```bash
pip install -e ".[audio]"
python -m aera_agent gui   # GUI
python -m aera_agent cli   # terminal
```

### 3. Package – choose your target

#### Onedir bundle (recommended – fastest startup)
```bash
# Linux / macOS
bash build_tools/build.sh
# Windows
build_tools\build.bat
# -> dist/AERA/AERA or dist/AERA.app or dist/AERA/AERA.exe
```

#### Single-file exe (easier to share, slower startup)
```bash
bash build_tools/build.sh --onefile
build_tools\build.bat --onefile
# -> dist/AERA or dist/AERA.exe (single 80-120MB file)
```

#### Fallback self-contained pyz (no libpython needed – works in this sandbox!)
```bash
pip install shiv
make pyz
# -> dist/AERA.pyz (249MB full, includes PySide6) and dist/AERA-cli.pyz
python3 dist/AERA.pyz   # runs GUI if DISPLAY set
```

#### Lightweight pyz (244KB, needs pip deps)
```bash
make light-desktop
# -> dist/AERA-light.pyz
pip install PySide6 openai psutil
python3 dist/AERA-light.pyz
```

#### OS-native installers
```bash
bash build_tools/build.sh --installer        # Linux/macOS: AppImage+DEB+DMG/PKG
build_tools\build.bat --installer            # Windows: Setup.exe+MSI (if tools installed)
bash build_tools/build.sh --all              # everything for current OS
```

### 4. Manual installer builds (if you want specific format)

**Windows:**
```bat
:: After building onedir
iscc build_tools\aera_installer.iss
:: -> dist\AERA-Setup-0.0.1.exe

:: MSI via WiX (Windows only, needs WiX)
candle build_tools\wix\aera.wxs -dVersion=0.0.1 -dSourceDir=dist\AERA -out build\wix\aera.wixobj
light build\wix\aera.wixobj -out dist\AERA-0.0.1.msi
```

**macOS:**
```bash
create-dmg --volname "AERA Agent" --window-size 540 340 --app-drop-link 400 180 dist/AERA-0.0.1.dmg dist/AERA.app
pkgbuild --root build/pkgroot --identifier com.aera.agent --version 0.0.1 --install-location /Applications dist/AERA-0.0.1.pkg
```

**Linux:**
```bash
# AppImage (needs appimagetool)
appimagetool dist/AERA.AppDir dist/AERA-0.0.1-x86_64.AppImage

# DEB (needs dpkg-deb) – already handled by build.py
dpkg-deb --build build/deb/aera_0.0.1_amd64 dist/AERA_0.0.1_amd64.deb
sudo dpkg -i dist/AERA_0.0.1_amd64.deb   # installs to /opt/aera + /usr/bin/aera

# RPM via fpm
gem install fpm
fpm -s dir -t rpm -n aera-agent -v 0.0.1 --prefix /opt/aera -p dist/AERA-0.0.1.rpm dist/AERA/=/opt/aera/
```

---

## Distributing

### Windows
- **`dist\AERA-Setup-0.0.1.exe`** – double-click, wizard, Start Menu + Desktop shortcut (Inno Setup)
- **`dist\AERA-0.0.1.msi`** – enterprise deploy via Group Policy / `msiexec /i AERA.msi`
- **`dist\AERA.exe`** (onefile) – portable single exe, no installer
- **`dist\AERA\AERA.exe`** (onedir) – folder bundle, fastest

First launch asks for API key (Groq free key recommended).

### macOS
- **`dist/AERA-0.0.1.dmg`** – open, drag `AERA.app` to Applications
- **`dist/AERA-0.0.1.pkg`** – double-click installer PKG
- macOS will ask “AERA wants to use microphone” on first voice use (spec includes `NSMicrophoneUsageDescription`)
- Code-sign & notarize for outside distribution: `codesign --deep --force --sign "Developer ID..." dist/AERA.app` + `xcrun notarytool submit ...`

### Linux
- **`dist/AERA-0.0.1-x86_64.AppImage`** – `chmod +x` + double-click, runs anywhere, no install
- **`dist/AERA_0.0.1_amd64.deb`** – `sudo dpkg -i ...` or `sudo apt install ./...` → binary at `/opt/aera/AERA` + `/usr/bin/aera` + desktop entry
- **`dist/AERA-0.0.1-linux-x86_64.tar.gz`** – extract and run `./AERA/AERA`
- **`dist/AERA.pyz`** (shiv) – fallback that works without libpython: `python3 AERA.pyz`

---

## What's bundled / what's not

**Bundled (always works, 80–120 MB)**
- Python interpreter (via PyInstaller)
- All AERA code (`aera_agent/`, `omnivoice/` source)
- PySide6 GUI, `pyttsx3` TTS (robotic), `SpeechRecognition`
- Icons + default `config.json`

**NOT bundled (too heavy – optional)**
- PyTorch / Transformers (OmniVoice voice cloning – 2 GB) → `pip install torch torchaudio transformers`
- FunASR (SenseVoice offline STT – 1.5 GB) → `pip install funasr soundfile webrtcvad`
- SpeechBrain (speaker biometric – 600 MB) → `pip install speechbrain torch torchaudio`
- Piper voice models (~30 MB each) → auto-download on first use into `voices/`
- PortAudio mic stack → `pip install aera-agent[audio]` + system `portaudio19-dev`

Excluding heavy deps keeps bundle small. Power users install them separately – Settings → Voice lights up extra engines.

---

## Customizing the build

Edit `build_tools/aera.spec` (onedir) and `aera_onefile.spec` (onefile):
- `datas` – add files to bundle
- `hiddenimports` – include modules PyInstaller misses (imported inside try/except)
- `excludes` – remove modules to shrink bundle
- `console=True` – show console for debugging
- `BUNDLE info_plist` – macOS metadata

Edit `build_tools/aera_installer.iss` (Inno Setup) and `build_tools/wix/aera.wxs` (WiX MSI) for Windows branding.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `libpython3.11.so not found` | Install `libpython3.11-dev` / `python3-dev` (`sudo apt install`) or use shiv pyz fallback (`make pyz`) |
| `Failed to execute script` | Edit spec, set `console=True`, rebuild, run from terminal to see real error |
| Huge bundle (>500 MB) | Check `excludes` – torch/cv2/torch slipped in? |
| Missing icon on Linux | `assets/aera_icon.png` must exist (run `python build_tools/build.py --no-install-deps` first) |
| macOS “app is damaged” | Not signed – right-click → Open first time, or `xattr -cr dist/AERA.app` |
| Windows SmartScreen warning | Exe not signed – users click “More info” → “Run anyway” or sign with EV cert |
| Black/white window on first launch | Restart once – Qt creates config |
| `PortAudio not found` on Linux sandbox | That's expected headless – app falls back to text mode; install `portaudio19-dev` + `pip install aera-agent[audio]` on real desktop |
| Inno Setup `iscc` not found | Install from https://jrsoftware.org/isdl.php and add to PATH |
| WiX `candle` not found | Install WiX Toolset from https://wixtoolset.org/ |

---

## CI / automation – building all 3 OS at once

Each platform must build on that platform (PyInstaller doesn't cross-compile). Use GitHub Actions matrix (see `.github/workflows/release.yml`):

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
runs-on: ${{ matrix.os }}
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with: { python-version: "3.12" }
  - run: pip install -e ".[audio]" pyinstaller pillow cairosvg shiv
  - run: python build_tools/build.py --all
  - uses: actions/upload-artifact@v4
    with: { name: AERA-${{ matrix.os }}, path: dist/ }
```

Trigger a release: `git tag v0.1.0 && git push --tags` – workflow builds EXE+MSI (Windows), APP+DMG+PKG (macOS), AppImage+DEB+RPM+tar.gz+pyz (Linux) and attaches to GitHub Release.

