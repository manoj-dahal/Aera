# 📁 Project structure

After the package reorganization, the workspace is laid out as a proper
Python package, `pip install -e .`-able and runnable via
`python -m aera_agent`.

```
voice_assistant/                  ← project root
│
├── pyproject.toml                ← package metadata + dependency groups
├── requirements.txt              ← (legacy) flat dependency list
├── README.md                     ← user docs
├── STRUCTURE.md                  ← this file
├── config.json                   ← user-editable config (kept at root)
├── aera.py                       ← convenience launcher: `python aera.py gui`
│
├── aera_agent/                   ← main Python package
│   │
│   ├── __init__.py               ← version, package docstring
│   ├── __main__.py               ← `python -m aera_agent [cli|gui]`
│   ├── paths.py                  ← centralized filesystem paths
│   ├── theme.py                  ← colors + reusable QSS button styles
│   ├── config.py                 ← Config class (loads config.json)
│   ├── llm.py                    ← LLM (OpenAI-compat + tool loop + streaming)
│   ├── memory.py                 ← graph-based long-term memory
│   ├── cli.py                    ← terminal REPL entry point
│   │
│   ├── audio/                    ← all STT, TTS, wake, biometric
│   │   ├── __init__.py           ← build_speaker / build_listener factories
│   │   ├── tts_piper.py          ← Piper neural TTS
│   │   ├── tts_omnivoice.py      ← OmniVoice (voice cloning) TTS
│   │   ├── stt_sensevoice.py     ← SenseVoice multilingual STT
│   │   ├── wake.py               ← Porcupine + SR fallback wake-word
│   │   └── speaker_id.py         ← ECAPA-TDNN speaker biometric
│   │
│   ├── tools/                    ← 46 agent tools split by domain
│   │   ├── __init__.py           ← @tool decorator + registry + dispatch
│   │   ├── _http.py              ← shared HTTP helpers
│   │   ├── time_date.py          ← get_time, date_diff
│   │   ├── weather.py            ← get_weather (Open-Meteo)
│   │   ├── web.py                ← web_search, fetch_url, wikipedia, news
│   │   ├── timers.py             ← timers, alarms, reminders
│   │   ├── launchers.py          ← open_url, open_app, open_search
│   │   ├── math_units.py         ← calculate, convert_units, currency
│   │   ├── clipboard_fs.py       ← clipboard + sandboxed file ops
│   │   ├── system.py             ← system_info, my_ip
│   │   ├── notes_fun.py          ← notes, dice, password
│   │   ├── translate.py          ← MyMemory translation
│   │   ├── memory_tools.py       ← remember, recall, forget, …
│   │   └── speaker_tools.py      ← enroll_voice, verify_voice, …
│   │
│   └── gui/                      ← PySide6 desktop UI
│       ├── __init__.py
│       ├── app.py                ← AeraWindow main class
│       ├── style.py              ← global QSS
│       ├── widgets.py            ← ParticleOrb, TopBar, TranscriptPhone, …
│       ├── worker.py             ← AssistantWorker (background thread)
│       └── pages/                ← one file per top-nav page
│           ├── __init__.py
│           ├── common.py         ← Card / StatPill / Sparkline (shared)
│           ├── dashboard.py      ← live system stats + activity feed
│           ├── macros.py         ← one-tap phrases
│           ├── apps.py           ← app launchers
│           ├── gallery.py        ← image thumbnails
│           ├── phone.py          ← contacts + dial pad
│           ├── studio.py         ← Voice Studio (record/manage voices)
│           └── settings.py       ← provider / voice / speech / wake / memory
│
├── omnivoice/                    ← Xiaomi OmniVoice research code (Apache-2.0)
│   ├── __init__.py
│   ├── omnivoice_model.py        ← main OmniVoice PyTorch model class
│   ├── sensevoice_eval.py        ← Cantonese CER eval script
│   ├── speaker_sim_eval.py       ← SIM-o eval script
│   ├── sample_processor.py       ← training data processor
│   └── dataset.py                ← WebDataset training loader
│
├── data/                         ← runtime-generated JSON state
│   ├── memory.json               ← knowledge graph
│   ├── macros.json               ← saved macros
│   ├── apps.json                 ← app launcher list
│   ├── contacts.json             ← phone contacts
│   ├── reminders.json            ← persistent reminders
│   ├── speakers.json             ← enrolled voice biometrics
│   ├── history.json              ← saved conversations
│   └── notes.txt                 ← quick notes
│
├── voices/                       ← cached TTS voices + clones
│   ├── en_US-lessac-medium.onnx  ← Piper voice cache (after download)
│   ├── me.wav                    ← user-recorded clone reference
│   ├── me.txt                    ← transcript of me.wav
│   └── ecapa/                    ← SpeechBrain ECAPA-TDNN cache
│
└── workspace/                    ← sandbox for the file tools
    ├── Default/
    └── gallery/                  ← Gallery page reads from here
```

---

## How to run

```bash
# from project root
python -m aera_agent             # launches GUI (default)
python -m aera_agent gui         # explicit GUI
python -m aera_agent cli         # terminal REPL

# or via launcher script
python aera.py gui
python aera.py cli

# or after pip install
pip install -e .
aera                             # → GUI
aera-cli                         # → CLI
aera-gui                         # → GUI
```

## How to add a new tool

1. Open the matching file in `aera_agent/tools/` (or create a new one).
2. Write a function decorated with `@tool(...)`:
   ```python
   from . import tool

   @tool(
       description="Tell me a joke from a topic.",
       parameters={"type":"object",
                   "properties":{"topic":{"type":"string"}},
                   "required":["topic"]},
   )
   def tell_joke(topic: str) -> str:
       return f"Why did the {topic} cross the road? …"
   ```
3. If you created a new file, add its import to `aera_agent/tools/__init__.py`.
4. Restart — the LLM can now call it automatically.

## How to add a new GUI page

1. Create `aera_agent/gui/pages/myfeature.py` with a `class MyFeaturePage(QWidget)`.
2. Re-export it in `aera_agent/gui/pages/__init__.py`.
3. Add a button to `TopBar` in `aera_agent/gui/widgets.py`.
4. Wire it into `AeraWindow.pages` and `_NAV_INDEX` in `aera_agent/gui/app.py`.

## How to change theme colors

Edit `aera_agent/theme.py` — one place, all widgets pick up the change.
