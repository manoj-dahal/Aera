"""
AERA Agent CLI — voice + text chat in your terminal.

Run:
    python -m aera_agent              # launches GUI (default)
    python -m aera_agent cli          # text/voice REPL in terminal
    python -m aera_agent gui          # explicit GUI launch
"""

import json
import sys

from .audio import build_speaker, build_listener
from .audio import pyttsx3  # for /voices listing
from .config import Config
from .llm import LLM, OpenAI, SentenceBuffer, strip_for_tts
from .memory import graph as memory_graph
from .paths import HISTORY_FILE
from . import tools as agent_tools


# ─────────────────────────────────────────────────────────────── #
HELP = """
Commands:
  /help                     show help
  /providers                list configured providers
  /use <name>               switch active provider
  /set base_url <url>       update base URL
  /set api_key <key>        update API key
  /set model <name>         update model
  /add <name>               add new provider preset
  /system <prompt>          change system prompt
  /tools [on|off]           list / toggle agent tools
  /memory                   show memory stats
  /memory show [entity]     dump known facts (default: user)
  /memory search <q>        search memory
  /memory forget <q>        delete matching items
  /memory clear             wipe all memory
  /tts piper|pyttsx3|omnivoice    switch TTS engine
  /tts voice <name>         set Piper voice model
  /reset                    clear chat history
  /save  /load              persist conversation
  /voice                    toggle voice / text mode
  /voices                   list installed pyttsx3 voices
  /quit                     exit
"""


# ─────────────────────────────────────────────────────────────── #
#  Individual command handlers
# ─────────────────────────────────────────────────────────────── #
def _cmd_help(*_):    print(HELP)
def _cmd_quit(_p, _cfg, _llm, _spk, state): state["running"] = False


def _cmd_providers(_p, cfg, *_):
    for name, p in cfg.data["providers"].items():
        mark = "*" if name == cfg.data["active_provider"] else " "
        print(f" {mark} {name:15s}  model={p['model']:30s}  url={p['base_url']}")


def _cmd_use(parts, cfg, llm, *_):
    if len(parts) < 2: print("usage: /use <provider>"); return
    try:
        cfg.set_active(parts[1]); llm.refresh(cfg.active)
        print(f"Switched to {parts[1]} ({cfg.active['model']})")
    except KeyError as e:
        print(e)


def _cmd_set(parts, cfg, llm, *_):
    if len(parts) != 3 or parts[1] not in ("base_url", "api_key", "model"):
        print("usage: /set base_url|api_key|model <value>"); return
    cfg.active[parts[1]] = parts[2]; cfg.save(); llm.refresh(cfg.active)
    print(f"Updated {parts[1]}.")


def _cmd_add(parts, cfg, *_):
    if len(parts) < 2: print("usage: /add <name>"); return
    cfg.data["providers"].setdefault(parts[1], {
        "base_url": "https://api.example.com/v1",
        "api_key": "YOUR_KEY", "model": "model-name",
    })
    cfg.save()
    print(f"Added '{parts[1]}'. Use /set to configure, /use {parts[1]} to activate.")


def _cmd_system(parts, cfg, llm, *_):
    if len(parts) < 2: print("usage: /system <prompt>"); return
    cfg.data["system_prompt"] = parts[1]; cfg.save()
    llm.system_prompt = parts[1]
    print("System prompt updated.")


def _cmd_tools(parts, _cfg, llm, *_):
    if len(parts) >= 2 and parts[1].lower() in ("on", "off"):
        llm.use_tools = parts[1].lower() == "on"
        print(f"Tools {'enabled' if llm.use_tools else 'disabled'}.")
    else:
        print(agent_tools.summary())
        print(f"Currently: {'ON' if llm.use_tools else 'OFF'}")


def _cmd_memory(parts, *_):
    g = memory_graph()
    if len(parts) == 1:
        print(g.stats()); return
    sub = parts[1].lower()
    arg = parts[2] if len(parts) > 2 else ""
    actions = {
        "show":   lambda: g.about(arg or "user", depth=2),
        "search": lambda: g.search(arg) if arg else "usage: /memory search <q>",
        "forget": lambda: g.forget(arg) if arg else "usage: /memory forget <q>",
        "clear":  lambda: g.clear(),
    }
    if sub in actions:
        print(actions[sub]())
    else:
        print("usage: /memory [show <entity> | search <q> | forget <q> | clear]")


def _cmd_tts(parts, cfg, *_):
    if len(parts) < 2:
        print("usage: /tts piper|pyttsx3|omnivoice   or   /tts voice <model_name>"); return
    sub = parts[1].lower()
    if sub in ("piper", "pyttsx3", "omnivoice"):
        cfg.data["voice"]["engine"] = sub; cfg.save()
        print(f"TTS engine set to {sub}. Restart to apply.")
    elif sub == "voice" and len(parts) == 3:
        cfg.data["voice"]["model"] = parts[2]; cfg.save()
        print(f"Piper voice set to {parts[2]}. Restart to apply.")
    else:
        print("usage: /tts piper|pyttsx3|omnivoice   or   /tts voice <model_name>")


def _cmd_reset(_p, _cfg, llm, *_):
    llm.reset(); print("History cleared.")


def _cmd_save(_p, _cfg, llm, *_):
    HISTORY_FILE.write_text(json.dumps(llm.history, indent=2), encoding="utf-8")
    print(f"Saved {len(llm.history)} messages.")


def _cmd_load(_p, _cfg, llm, *_):
    if not HISTORY_FILE.exists():
        print("No history.json found."); return
    llm.history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    print(f"Loaded {len(llm.history)} messages.")


def _cmd_voice(_p, _cfg, _llm, _spk, state):
    state["voice_mode"] = not state["voice_mode"]
    print(f"Voice mode: {'ON' if state['voice_mode'] else 'OFF (text only)'}")


def _cmd_voices(*_):
    if not pyttsx3:
        print("pyttsx3 not installed."); return
    eng = pyttsx3.init()
    for i, v in enumerate(eng.getProperty("voices")):
        print(f"  [{i}] {v.name}  ({v.id})")


_COMMANDS = {
    "help": _cmd_help, "h": _cmd_help, "?": _cmd_help,
    "providers": _cmd_providers,
    "use": _cmd_use, "set": _cmd_set, "add": _cmd_add,
    "system": _cmd_system, "tools": _cmd_tools, "memory": _cmd_memory,
    "tts": _cmd_tts, "reset": _cmd_reset, "save": _cmd_save, "load": _cmd_load,
    "voice": _cmd_voice, "voices": _cmd_voices,
    "quit": _cmd_quit, "exit": _cmd_quit, "q": _cmd_quit,
}


def handle_command(line: str, cfg: Config, llm: LLM, speaker, state: dict) -> bool:
    if not line.startswith("/"):
        return False
    parts = line.strip().split(maxsplit=2)
    cmd = parts[0][1:].lower()
    handler = _COMMANDS.get(cmd)
    if handler is None:
        print(f"Unknown command: {cmd}.  Type /help"); return True
    if cmd == "system" and len(parts) > 1:
        parts = ["system", line.split(maxsplit=1)[1]]
    handler(parts, cfg, llm, speaker, state)
    return True


# ─────────────────────────────────────────────────────────────── #
#  Main loop
# ─────────────────────────────────────────────────────────────── #
def main() -> None:
    print("=" * 60)
    print("  AERA Agent CLI  —  /help for commands")
    print("=" * 60)

    if OpenAI is None:
        sys.exit("Missing dependency: pip install openai")

    cfg = Config.load()
    speaker = build_speaker(cfg.data["voice"])
    listener = build_listener(cfg.data["speech"])

    # Inject long-term memory snapshot into the system prompt
    base_prompt = cfg.data["system_prompt"]
    mem_snapshot = memory_graph().snapshot_for_prompt()
    full_prompt = base_prompt + ("\n\n" + mem_snapshot if mem_snapshot else "")

    llm = LLM(cfg.active, full_prompt, use_tools=True)
    state = {"running": True, "voice_mode": listener.enabled}

    print(f"Provider : {cfg.data['active_provider']}  |  Model: {llm.model}")
    print(f"Base URL : {llm.provider['base_url']}")
    print(f"Mode     : {'VOICE' if state['voice_mode'] else 'TEXT'} (toggle with /voice)")
    print(f"Tools    : {agent_tools.summary()}")
    print(f"Memory   : {memory_graph().stats()}\n")

    exit_phrases = [p.lower() for p in cfg.data.get("exit_phrases", [])]

    while state["running"]:
        # flush any background timer notifications
        for note in agent_tools.pop_notifications():
            speaker.say(note)

        if state["voice_mode"]:
            user = listener.listen()
            if user is None: continue
        else:
            try:
                user = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print(); break
            if not user: continue

        if user.lower().strip(" .!?") in exit_phrases:
            speaker.say("Goodbye!"); break

        if user.startswith("/"):
            handle_command(user, cfg, llm, speaker, state); continue

        print("🤖 ", end="", flush=True)
        sb = SentenceBuffer()
        for delta in llm.stream_reply(user):
            print(delta, end="", flush=True)
            for sent in sb.feed(strip_for_tts(delta)):
                speaker.say(sent)
        tail = strip_for_tts(sb.flush())
        if tail: speaker.say(tail)
        print()

    speaker.shutdown()
    print("Bye.")


if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\nInterrupted.")
