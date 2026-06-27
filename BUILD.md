# 🛠 Building AERA Agent

Package AERA into a **standalone executable** that anyone can run without
installing Python. Works on Windows, macOS, and Linux from the same codebase.

---

## TL;DR — one command per OS

| OS | Build command | Output |
|---|---|---|
| 🐧 Linux | `bash build_tools/build.sh` | `dist/AERA/AERA` |
| 🍎 macOS | `bash build_tools/build.sh` | `dist/AERA.app` |
| 🪟 Windows | `build_tools\build.bat` | `dist\AERA\AERA.exe` |

Add `installer` at the end to also build a `.dmg` / `.exe` installer / `.AppImage`.

The first run automatically pops up the **setup wizard** so end-users paste
their API key in a GUI instead of editing `config.json`.

---

## Prerequisites

| | |
|---|---|
| Python | **3.10 or newer** on the *build* machine |
| Disk   | ~500 MB free for the build artifacts |
| RAM    | 2 GB free during PyInstaller analysis |

The build script auto-installs the rest (`pyinstaller`, `pillow`, `cairosvg`).

---

## Step-by-step

### 1. Clone the repo
```bash
git clone <your-repo>  aera-agent
cd aera-agent
```

### 2. Install runtime deps once
```bash
python -m pip install -r requirements.txt
```

### 3. Test it runs from source before packaging
```bash
python -m aera_agent gui          # GUI
python -m aera_agent cli          # terminal mode
```

### 4. Package
```bash
# Linux / macOS
bash build_tools/build.sh

# Windows
build_tools\build.bat
```

What this does:
1. Verifies Python ≥ 3.10
2. Installs build dependencies (PyInstaller, Pillow, cairosvg)
3. Rasterizes `assets/aera_icon.svg` → `.ico` / `.icns` / `.png`
4. Runs PyInstaller with `build_tools/aera.spec`
5. Produces `dist/AERA/` (folder bundle) or `dist/AERA.app` on macOS

### 5. (Optional) Build an OS-native installer

```bash
bash build_tools/build.sh installer        # Linux/macOS
build_tools\build.bat installer            # Windows
```

| OS | Additional tool needed | Output |
|---|---|---|
| 🪟 Windows | [Inno Setup](https://jrsoftware.org/isdl.php) | `dist\AERA-Setup.exe` |
| 🍎 macOS | `brew install create-dmg` | `dist/AERA.dmg` |
| 🐧 Linux | [`appimagetool`](https://github.com/AppImage/AppImageKit/releases) | `dist/AERA-x86_64.AppImage` |

---

## Distributing

### Windows
Send users **`dist\AERA-Setup.exe`** (installer) — they double-click,
follow the wizard, get a Start Menu entry + Desktop shortcut. First launch
asks for their API key.

### macOS
Send users **`dist/AERA.dmg`** — they open it, drag `AERA.app` into
Applications. macOS will ask "AERA wants to use the microphone" on first
voice use (the spec includes the `NSMicrophoneUsageDescription` plist key).

You'll likely want to [code-sign and notarize](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
before distributing outside your machine.

### Linux
Send users **`dist/AERA-x86_64.AppImage`** — they `chmod +x` it and
double-click. No install, runs from anywhere.

---

## What's bundled / what's not

**Bundled (always works)**
- Python interpreter
- All AERA code (`aera_agent/`, `omnivoice/` source)
- PySide6 GUI framework
- `pyttsx3` TTS (basic)
- `SpeechRecognition` STT
- All icons & default config

**NOT bundled (too heavy — install separately into the same Python if needed)**
- PyTorch / Transformers (for OmniVoice TTS — 2 GB)
- FunASR (for SenseVoice STT — 1.5 GB)
- SpeechBrain (for speaker biometric — 600 MB)
- Piper voice models (downloaded on first use into `voices/`)

Excluding these keeps the bundle around **80–120 MB** instead of multiple GB.
Power users who want them install separately: the audio backends will
auto-detect availability and the engine selector in Settings → Voice will
light up the corresponding options.

---

## Customizing the build

Edit `build_tools/aera.spec`:
- `datas` — add more files to bundle
- `hiddenimports` — include modules PyInstaller misses
- `excludes` — remove modules you don't need (smaller bundle)
- `console=True` — show a console window for debugging
- `BUNDLE info_plist` — macOS-specific metadata

---

## Troubleshooting

| Problem | Fix |
|---|---|
| "Failed to execute script" on launch | Edit `aera.spec`, set `console=True`, rebuild, run from terminal to see the real error |
| Huge bundle (>500 MB) | Check `excludes` list — torch/cv2/etc. may have slipped in |
| Missing icon on Linux | Make sure `assets/aera_icon.png` exists (run `python build_tools/build.py --no-install-deps` first) |
| macOS "app is damaged" | App isn't signed — right-click → Open the first time, or run `xattr -cr dist/AERA.app` |
| Windows SmartScreen warning | Exe isn't signed — users click "More info" → "Run anyway" |
| Black/white window on first launch | Restart once — Qt creates its config on first run |

---

## CI / automation

Each platform builds need to run on **that platform** (PyInstaller doesn't
cross-compile). Use a GitHub Actions matrix:

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
runs-on: ${{ matrix.os }}
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with: { python-version: "3.12" }
  - run: pip install -r requirements.txt
  - run: python build_tools/build.py --installer
  - uses: actions/upload-artifact@v4
    with: { name: AERA-${{ matrix.os }}, path: dist/ }
```
