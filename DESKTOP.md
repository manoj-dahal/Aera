# AERA Desktop Application – Build Report

## Built Artifacts (in `dist/`)

| File | Size | Type |
|------|------|------|
| `AERA.pyz` | 249 MB | Full self-contained GUI desktop app (includes PySide6 6.11, openai, psutil) – single file double-click |
| `AERA-cli.pyz` | 249 MB | Same but CLI entry point (`aera-cli`) – text mode |
| `AERA-light.pyz` | 244 KB | Lightweight zipapp (needs `pip install PySide6 openai psutil pyttsx3`) |
| `AERA-Desktop-App/` | 499 MB folder | Desktop folder with launcher scripts + icon + .desktop + wheel + README |
| `AERA-light-desktop.tar.gz` | 441 KB | Lightweight desktop tarball (small) |
| `aera_agent-0.0.1-py3-none-any.whl` | 121 KB | pip wheel |
| `aera_agent-0.0.1.tar.gz` | 104 KB | sdist |

## How to Run Desktop App

### Full bundle (no pip needed, just Python 3.10+)
```bash
chmod +x dist/AERA.pyz
./dist/AERA.pyz
# or use folder launcher
chmod +x dist/AERA-Desktop-App/AERA
./dist/AERA-Desktop-App/AERA
```

### Light bundle (small, needs deps)
```bash
pip install PySide6 openai psutil pyttsx3
chmod +x dist/AERA-light.pyz
./dist/AERA-light.pyz
```

### Desktop shortcut (Linux)
```bash
cp dist/AERA-Desktop-App/AERA.desktop ~/.local/share/applications/
# appears in app menu as "AERA Agent"
```

### Windows
- Double-click `AERA.bat` or `python AERA-full.pyz`

### macOS
- `./AERA` or `python3 AERA-full.pyz`

## Make targets added

Makefile now has:

- `make run` → `python -m aera_agent gui`
- `make cli` → terminal
- `make build` → PyInstaller bundle (needs libpython3.11-dev)
- `make desktop` → full 249MB self-contained pyz via shiv (works without dev headers)
- `make light-desktop` → lightweight pyz
- `make installer` → + AppImage/DMG/EXE if tools installed

## Fixes for deployment robustness

1. **Audio import fallback**: `speaker_id`, `stt_sensevoice`, `tts_piper`, `tts_omnivoice`, `studio.py` now catch `Exception` not just `ImportError`, so missing `PortAudio` (OSError) doesn't crash import – app falls back to text-only.

2. **PyAudio optional**: Removed `PyAudio` hard dependency from `pyproject.toml` core deps, moved to `[audio]` optional group:
   ```toml
   dependencies = [openai, pyttsx3, PySide6, psutil]
   [optional-dependencies]
   audio = [SpeechRecognition, PyAudio]
   ```
   This allows `pip install .` and `shiv` builds without needing `python3-dev` + `portaudio19-dev` headers.

3. **shiv zipapp**: Produces single-file executable that bundles all pure-python + binary wheels (PySide6). Tested:
   - `dist/AERA-cli.pyz` launches CLI, shows 46 tools, text mode (no mic/eSpeak in headless)
   - GUI pyz needs DISPLAY – not testable headless but same bootstrap.

## Known limitation

PyInstaller bundle (`build_tools/build.py`) still requires `libpython3.11-dev` (`libpython3.11.so`) which is not available in this sandbox without sudo apt. Use `make desktop` (shiv) as alternative, or build on GitHub Actions runner where `apt install libpython3.11-dev` works (see `.github/workflows/release.yml`).

Full PyInstaller flow will produce:
- `dist/AERA/AERA` folder bundle (Linux)
- `dist/AERA.app` (macOS)
- `dist/AERA/` + Setup.exe via Inno Setup (Windows)

## Next steps to publish

```bash
pip install build twine
python -m build
twine upload dist/aera_agent-0.0.1*

# Tag release to trigger 3-OS builds
python build_tools/release.py 0.1.0
git add -A && git commit -m "Release v0.1.0"
git tag v0.1.0 && git push --tags
```

