# Changelog

All notable changes to **AERA Agent** are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/) and
this project adheres to [Semantic Versioning](https://semver.org/).

---

## [0.0.1] — 2026-06-27

🌱 **Initial preview release.** Snapshot of the AERA Agent codebase as it
stood after the first end-to-end build.

### ✨ What works

| Layer | Status |
|---|---|
| 🎤 Voice in — Google Web Speech | ✅ |
| 🔊 Voice out — pyttsx3 (always works) | ✅ |
| 🔊 Voice out — Piper neural TTS | ✅ (install `piper-tts`) |
| 🔊 Voice out — OmniVoice w/ voice cloning | ✅ (install `torch`) |
| 🎤 Voice in — SenseVoice (offline multilingual) | ✅ (install `funasr`) |
| 🧠 46 agent tools (weather, web, timers, files, math, …) | ✅ |
| 🕸️ Graph long-term memory | ✅ |
| 🎙 Voice biometric (enroll / verify / identify) | ✅ |
| 👂 Wake word — Porcupine + SR fallback | ✅ |
| 🌐 OpenAI-compatible LLM client | ✅ |
| 🖥 PySide6 GUI with 8 pages | ✅ |
| 🪄 First-run setup wizard | ✅ |

### 📦 Distribution

- 🐍 Run from source: `python -m aera_agent gui` or `cli`
- 📦 Standalone bundle: `python build_tools/build.py`
- 🪟🍎🐧 GitHub Actions release workflow ready (`.github/workflows/release.yml`)

### 🛠 Architecture

- 43 Python files, ~5,300 lines (excl. omnivoice research code)
- Proper package layout (`aera_agent/{audio,tools,gui}/…`)
- Centralized paths (`paths.py`) work both from source and inside a frozen bundle
- Graceful fallback chains for TTS / STT (heavy backends auto-skip if not installed)
- Per-domain tool files (`tools/weather.py`, `tools/web.py`, …) — adding a tool = one file

### 🐛 Known limitations (planned for v0.1.0)

- Windows/macOS bundles need to be built on those platforms (no cross-compile)
- OmniVoice TTS requires CUDA for realtime; CPU works but ~10× slower
- pyttsx3 needs `espeak-ng` on Linux (apt install)
- No code-signing on the macOS/Windows bundles yet

---

## [Unreleased]

Planned for **v0.1.0**:
- Polished release with binary downloads attached to GitHub Release
- Streaming OmniVoice TTS (speak as the model generates)
- Theme switcher (dark mode + sci-fi presets)
- Voice-gated sensitive tools (require speaker verification)
- Custom Porcupine `.ppn` files for a true "Hey AERA" wake word
- Continuous speaker identification (per-speaker memory)

Got an idea? Open an issue.

[0.0.1]: https://github.com/your-org/aera-agent/releases/tag/v0.0.1
