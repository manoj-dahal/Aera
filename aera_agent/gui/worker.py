"""
AssistantWorker — runs the voice pipeline (STT + LLM + tools + TTS) in
a background thread so the UI stays responsive.

Emits Qt signals that the main window connects to widgets:
    user_said(text)
    assistant_said(text)
    state_changed(int)    # 0 idle, 1 listening, 2 speaking
    status(head, sub)
    ready()
"""

import threading
import traceback

from PySide6.QtCore import QObject, Signal

from ..config import Config
from ..llm import LLM, SentenceBuffer, strip_for_tts
from ..memory import graph as memory_graph
from ..audio import build_speaker, build_listener
from .. import tools as agent_tools


class AssistantWorker(QObject):
    user_said      = Signal(str)
    assistant_said = Signal(str)
    state_changed  = Signal(int)
    status         = Signal(str, str)
    tool_called    = Signal(str, str)
    ready          = Signal()

    def __init__(self):
        super().__init__()
        self._busy = threading.Lock()
        self.cfg: Config | None = None
        self.llm: LLM | None = None
        self.listener = None
        self.speaker = None
        self._ready = False
        self.wake = None

    # --------------------------------------------------------------- #
    def init_backend(self):
        try:
            self.cfg = Config.load()
            self.speaker = build_speaker(self.cfg.data["voice"])
            self.listener = build_listener(self.cfg.data["speech"])
            prompt = self.cfg.data["system_prompt"]
            snap = memory_graph().snapshot_for_prompt()
            self.llm = LLM(self.cfg.active,
                           prompt + ("\n\n" + snap if snap else ""),
                           use_tools=True)
            self._ready = True
            self.status.emit("● READY",
                             f"{self.cfg.data['active_provider']} · {self.llm.model}")

            wake_cfg = self.cfg.data.get("wake", {})
            if wake_cfg.get("enabled"):
                try:
                    from ..audio.wake import WakeWordDetector
                    self.wake = WakeWordDetector(wake_cfg)
                    self.wake.on_detected = self.trigger_listen
                    if self.wake.start():
                        self.status.emit("● WAKE ARMED",
                                         f"say '{wake_cfg.get('phrase')}'")
                except Exception as e:
                    print(f"[wake] failed: {e}")
            self.ready.emit()
        except Exception as e:
            traceback.print_exc()
            self.status.emit("● ERROR", str(e)[:60])

    # --------------------------------------------------------------- #
    def trigger_listen(self):
        if not self._ready or self._busy.locked():
            return
        threading.Thread(target=self._cycle, daemon=True).start()

    def trigger_text(self, text: str):
        if not self._ready or self._busy.locked() or not text:
            return
        threading.Thread(target=self._cycle_text, args=(text,), daemon=True).start()

    def stop_speaking(self):
        if self.speaker and hasattr(self.speaker, "stop"):
            self.speaker.stop()
            self.state_changed.emit(0)
            self.status.emit("● INTERRUPTED", "")

    # --------------------------------------------------------------- #
    def _cycle(self):
        with self._busy:
            self.state_changed.emit(1)
            self.status.emit("● LISTENING", "speak now…")
            user = self.listener.listen() if self.listener.enabled else None
            if not user:
                self.state_changed.emit(0)
                self.status.emit("● IDLE", "no speech detected"); return
            self.user_said.emit(user)
            self._respond(user)

    def _cycle_text(self, user: str):
        with self._busy:
            self.user_said.emit(user)
            self._respond(user)

    def _respond(self, user: str):
        self.state_changed.emit(2)
        self.status.emit("● THINKING", self.llm.model)
        full: list[str] = []
        sb = SentenceBuffer()
        for delta in self.llm.stream_reply(user):
            full.append(delta)
            for sent in sb.feed(strip_for_tts(delta)):
                self.speaker.say(sent)
        tail = strip_for_tts(sb.flush())
        if tail:
            self.speaker.say(tail)
        self.assistant_said.emit("".join(full).strip())
        self.state_changed.emit(0)
        self.status.emit("● IDLE", "ready")

    def reload_config(self):
        try:
            self.cfg = Config.load()
            if self.llm:
                self.llm.refresh(self.cfg.active)
            self.status.emit("● RELOADED",
                             f"{self.cfg.data['active_provider']} · {self.llm.model}")
        except Exception as e:
            self.status.emit("● ERROR", str(e)[:60])

    def shutdown(self):
        if self.wake:
            self.wake.stop()
        if self.speaker:
            try: self.speaker.shutdown()
            except Exception: pass
