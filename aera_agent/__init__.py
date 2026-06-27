"""AERA Agent — voice AI assistant.

A modular voice assistant with:
  • OpenAI-compatible LLM client (Groq / Gemini / OpenAI / Ollama / …)
  • Multiple STT engines (Google, SenseVoice)
  • Multiple TTS engines (pyttsx3, Piper, OmniVoice w/ voice cloning)
  • 40+ agent tools via function-calling
  • Graph-based long-term memory
  • Wake-word detection + barge-in
  • PySide6 desktop UI with 8 pages

Run:
    python -m aera_agent           # GUI (default)
    python -m aera_agent gui       # GUI
    python -m aera_agent cli       # terminal REPL
"""

__version__ = "0.0.1"
