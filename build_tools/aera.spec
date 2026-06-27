# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for AERA Agent.

Run from the project root:
    pyinstaller build_tools/aera.spec

Produces dist/AERA/  (folder bundle with everything needed to run).
The same spec works on Windows, macOS, and Linux — platform-specific
icons and binary suffixes are picked automatically.
"""

import sys
from pathlib import Path

# Resolve the project root from the spec file's location.
HERE = Path(SPEC).resolve().parent          # build_tools/
ROOT = HERE.parent                          # project root

block_cipher = None

# Entry-point script — we use the launcher so PyInstaller doesn't need to
# treat aera_agent as a package on the command line.
entry = str(ROOT / "aera.py")

# Resource data files baked into the bundle. Format: (src, dest_in_bundle).
datas = [
    (str(ROOT / "assets"),    "assets"),
    (str(ROOT / "config.json"), "."),
    # Bundle the omnivoice research code so users who later install torch
    # can switch to the OmniVoice TTS engine without re-downloading.
    (str(ROOT / "omnivoice"), "omnivoice"),
]

# Hidden imports PyInstaller's static analysis won't catch.
# Anything imported inside try/except needs to be listed here, otherwise
# the bundle ships without it.
hiddenimports = [
    # Core LLM client
    "openai",
    # PySide6 plugins
    "PySide6.QtSvg",
    # Speech / audio backends — wrapped in try/except in our code, so we
    # have to list the ones we *do* want bundled here.
    "speech_recognition", "pyttsx3",
    # Tool deps that are imported lazily inside @tool functions
    "psutil",
]

# Heavy / optional packages we deliberately EXCLUDE so the bundle stays small.
# Users who want OmniVoice / SenseVoice install them separately into the same
# Python and re-run, or use the pip-install path instead of the bundle.
excludes = [
    "torch", "torchaudio", "transformers",
    "funasr", "piper", "speechbrain",
    "cv2", "matplotlib", "pandas", "scipy", "sklearn", "tensorflow",
    "jupyter", "notebook", "IPython",
]


# ── Platform icon ── #
ICONS = {
    "win32":  str(ROOT / "assets" / "aera_icon.ico"),
    "darwin": str(ROOT / "assets" / "aera_icon.icns"),
}
icon_file = ICONS.get(sys.platform, str(ROOT / "assets" / "aera_icon.png"))


# ─────────────────────────────────────────────────────────────── #
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
    [],
    exclude_binaries=True,
    name="AERA",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,        # set True for verbose debugging
    icon=icon_file,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, upx_exclude=[],
    name="AERA",
)


# ── macOS .app bundle (only emitted when building on darwin) ── #
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="AERA.app",
        icon=icon_file,
        bundle_identifier="com.aera.agent",
        info_plist={
            "CFBundleDisplayName": "AERA Agent",
            "CFBundleShortVersionString": "0.0.1",
            "NSHighResolutionCapable": True,
            "NSMicrophoneUsageDescription":
                "AERA needs the microphone to hear your voice commands.",
        },
    )
