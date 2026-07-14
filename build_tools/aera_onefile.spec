# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller one-file spec for AERA Agent – produces a single executable.

Produces:
  Windows -> dist/AERA.exe
  Linux   -> dist/AERA (single binary)
  macOS   -> dist/AERA (single binary, plus .app if needed)

Useful for quick distribution, but slower startup and larger memory than onedir.
For best UX use aera.spec (onedir) + installer (Setup.exe / DMG / AppImage).
"""

import sys
from pathlib import Path

HERE = Path(SPEC).resolve().parent
ROOT = HERE.parent

block_cipher = None
entry = str(ROOT / "aera.py")

datas = [
    (str(ROOT / "assets"),    "assets"),
    (str(ROOT / "config.json"), "."),
    (str(ROOT / "omnivoice"), "omnivoice"),
]

hiddenimports = [
    "openai",
    "PySide6.QtSvg",
    "speech_recognition",
    "pyttsx3",
    "psutil",
]

excludes = [
    "torch", "torchaudio", "transformers",
    "funasr", "piper", "speechbrain",
    "cv2", "matplotlib", "pandas", "scipy", "sklearn", "tensorflow",
    "jupyter", "notebook", "IPython",
]

ICONS = {
    "win32":  str(ROOT / "assets" / "aera_icon.ico"),
    "darwin": str(ROOT / "assets" / "aera_icon.icns"),
}
icon_file = ICONS.get(sys.platform, str(ROOT / "assets" / "aera_icon.png"))

a = Analysis(
    [entry],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="AERA",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # compress for onefile
    console=False,
    icon=icon_file,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="AERA.app",
        icon=icon_file,
        bundle_identifier="com.aera.agent",
        info_plist={
            "CFBundleDisplayName": "AERA Agent",
            "CFBundleShortVersionString": "0.0.1",
            "NSHighResolutionCapable": True,
            "NSMicrophoneUsageDescription": "AERA needs the microphone to hear your voice commands.",
        },
    )
