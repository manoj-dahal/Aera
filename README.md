# 🎙️ Voice AI Assistant (Python) + Agent Tools

A customizable voice assistant that works with **any OpenAI-compatible API**
(Groq, Google Gemini, OpenAI, Ollama, LM Studio, OpenRouter, vLLM, …) and
can **call real-world tools** (weather, web search, timers, files, etc.).

You can change the **base URL, API key, and model name** at runtime or in
`config.json`.

---

## ✨ Features

- 🎤 Voice in (Google Web Speech, free)
- 🔊 Voice out — choice of **Piper neural TTS** (natural) or **pyttsx3** (robotic fallback)
- ⚡ Streaming replies — spoken sentence-by-sentence
- 🔌 Multi-provider with live switching (`/use groq`, `/use google`, …)
- 🧠 **Agent tools via OpenAI function-calling** — assistant decides when to use them
- 🕸️ **Graph-based long-term memory** — "remember that…", auto-recalled every session
- 💾 Persistent reminders, notes, history, config

---

## 🧰 Built-in Tools (40)

| Category | Tools |
|---|---|
| **🕒 Time** | `get_time`, `date_diff` |
| **🌦 Weather** | `get_weather` *(Open-Meteo, no key)* |
| **🔎 Web** | `web_search` *(DuckDuckGo)*, `fetch_url`, `wikipedia`, `news` *(BBC RSS)*, `open_search` |
| **⏰ Timers** | `set_timer`, `set_alarm`, `list_timers`, `cancel_timer` |
| **📝 Reminders** | `add_reminder`, `list_reminders`, `delete_reminder` |
| **🌐 Launchers** | `open_url`, `open_app` |
| **🧮 Math** | `calculate`, `convert_units`, `currency` *(open.er-api)* |
| **📋 Clipboard** | `clipboard_read`, `clipboard_write` |
| **📁 Files** *(sandboxed)* | `list_files`, `read_file`, `write_file` |
| **🖥 System** | `system_info`, `my_ip` |
| **🗒 Notes** | `add_note`, `read_notes` |
| **🎲 Fun** | `roll_dice`, `flip_coin`, `pick_random`, `password` |
| **🌍 Language** | `translate` *(MyMemory)* |
| **🧠 Long-term memory** | `remember`, `remember_note`, `recall`, `memory_search`, `forget`, `memory_stats` |

All tools that need internet use **free, no-API-key** endpoints by default.

### Example things you can now say

> "What's the weather in Tokyo?"
> "Set a timer for 5 minutes called pasta."
> "Search the web for the latest Python 3.13 release notes."
> "Convert 100 USD to EUR."
> "What's 14 percent of 320?"
> "Open YouTube."
> "Remind me to call mom tomorrow at 9 AM."
> "Roll 3d20."
> "Translate 'good morning' to Japanese."
> "What's the top news right now?"
> **"Remember that my name is Bibek and I live in Kathmandu."**
> **"My dog Rex is a Beagle."**
> **"What do you know about me?"**
> **"Forget my phone number."**

The model decides which tool(s) to call, runs them, then speaks the answer.

---

## 🧠 Long-term memory (graph)

The assistant has a **persistent knowledge graph** of facts it has learned
about you, stored in `memory.json`. At the start of every session a
compact snapshot is injected into the system prompt so the model "remembers
you" from turn 1.

**How it works** — facts are stored as `(subject, predicate, object)` triples:

```
user            --name-->         Bibek
user            --lives_in-->     Kathmandu
user            --has_dog-->      user.dog       ← sub-entity (note the dot)
user.dog        --name-->         Rex
user.dog        --breed-->        Beagle
```

Plus free-form notes (`"Allergic to peanuts"`, etc.) with optional tags.

**Tools the LLM uses automatically:**

| Tool | When the model calls it |
|---|---|
| `remember(subject, predicate, object)` | User says "my X is Y" / "remember that…" |
| `remember_note(text, tags)` | Free-form fact that isn't a clean triple |
| `recall(entity, depth)` | Before answering personal questions |
| `memory_search(query)` | "What did I tell you about…?" |
| `forget(query)` | "Forget that…" |
| `memory_stats()` | Diagnostics |

**Slash commands:**

```
/memory                    show stats
/memory show user          dump everything we know about you
/memory show user.dog 2    dump with 2 levels of link traversal
/memory search blue        search facts + notes
/memory forget phone       delete matching items
/memory clear              wipe all memory
```

---

## 🔊 Piper TTS (natural neural voice)

Piper is a fast, **fully offline** neural TTS — no API key, much better
than pyttsx3.

**Install:**

```bash
pip install piper-tts sounddevice numpy
python -m piper.download_voices en_US-lessac-medium
```

**Switch to it:**

```
/tts piper
/tts voice en_GB-jenny_dioco-medium
```

Then restart the assistant. The voice will auto-download on first use if
not already cached.

**Recommended voices:**

| Lang | Model | Notes |
|---|---|---|
| 🇺🇸 | `en_US-lessac-medium` | Clear, neutral (default) |
| 🇺🇸 | `en_US-amy-medium` | Warm female |
| 🇺🇸 | `en_US-ryan-high` | High-quality male |
| 🇬🇧 | `en_GB-jenny_dioco-medium` | British female, very natural |
| 🇬🇧 | `en_GB-alan-medium` | British male |
| 🇪🇸 | `es_ES-davefx-medium` | Spanish |
| 🇫🇷 | `fr_FR-siwis-medium` | French |
| 🇩🇪 | `de_DE-thorsten-medium` | German |
| 🇯🇵 | `ja_JP-takumi-medium` | Japanese |
| 🇨🇳 | `zh_CN-huayan-medium` | Mandarin |

Full list: <https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md>

Tweak in `config.json` under `"voice"`:

```json
"voice": {
  "engine": "piper",
  "model": "en_US-lessac-medium",
  "rate": 180,           // words per minute → mapped to length_scale
  "volume": 1.0,
  "noise_scale": 0.667,  // higher = more variation in pitch/timbre
  "noise_w_scale": 0.8,  // higher = more variation in phoneme timing
  "use_cuda": false      // set true if you have onnxruntime-gpu installed
}
```

---

## 📦 Install

```bash
cd voice_assistant
pip install -r requirements.txt
```

PyAudio install tips:

| OS | Command |
|---|---|
| Windows | `pip install pyaudio` |
| macOS   | `brew install portaudio && pip install pyaudio` |
| Debian/Ubuntu | `sudo apt install portaudio19-dev python3-pyaudio && pip install pyaudio` |

(If PyAudio fails, the assistant still runs in text-only mode.)

---

## 🔑 Configure

Open `config.json`, replace `YOUR_..._API_KEY` for your provider.
Default active provider is **Groq** (fast + free tier).

Get keys:
- Groq — https://console.groq.com/keys
- Google Gemini — https://aistudio.google.com/apikey
- OpenAI — https://platform.openai.com/api-keys

---

## ▶️ Run

**Terminal mode:**
```bash
python assistant.py
```

**GUI mode (AERA Agent desktop app):**
```bash
pip install PySide6 psutil
python gui.py
```

Just talk. Say **"goodbye"** to exit.

### 🖥 GUI — AERA Agent

Top-nav switches between 7 fully-functional pages:

| Page | What it does |
|---|---|
| **Home** | Animated particle orb + 🎙 TAP TO SPEAK button (the mockup view) |
| **Dashboard** | Live CPU/RAM/Network stat pills, rolling sparkline charts, recent activity feed |
| **Macros** | Grid of one-tap phrases sent to the assistant — fully editable, persisted to `macros.json` |
| **Apps** | Quick-launch tiles for native apps & URLs (right-click to remove, ＋ to add) |
| **Gallery** | Thumbnail grid for images in `workspace/gallery/` — import dialog included |
| **Phone** | Contacts list + dial pad + Call/Message/Email buttons (routes to assistant) |
| **Studio** | 🎙 Record voice samples → save as OmniVoice clone OR enroll as biometric speaker. Live waveform meter, in-place Verify/Identify. |
| **Settings** | Provider · TTS · Speech · Wake word · Memory · About — all live-editable |

**Always-visible left column**: Hologram indicator (animated), live PC info card, Workspace file tree, red Status frame.
**Always-visible right column**: Sci-fi phone-shaped Transcript panel that scrolls every exchange.

### ⌨ Hotkeys

| Key | Action |
|---|---|
| **Space** | Trigger listen (same as TAP TO SPEAK) |
| **Esc** | Barge-in: interrupt assistant mid-sentence |
| **Ctrl+1/2/3** | Jump to Dashboard / Macros / Apps |
| **Ctrl+,** | Open Settings |

### 🎤 Wake word ("Hey AERA")

Enable in **Settings → Wake word**. Two backends:

1. **Picovoice Porcupine** — preferred. `pip install pvporcupine pyaudio`, get a free
   access key at https://console.picovoice.ai, paste into `config.json → wake.access_key`.
   Built-in phrases include `computer`, `terminator`, `blueberry`, `picovoice`, etc.
   Note: "AERA" is **not** a Porcupine built-in keyword. For a true "Hey AERA"
   trigger, use the speech-recognition fallback below (slower but free and
   accepts any phrase).
2. **Speech-recognition fallback** — free, no key. Continuously transcribes
   short audio windows and matches your phrase. Slightly heavier on CPU.

When the wake phrase is heard, AERA automatically starts a listen cycle —
no button tap needed.

---

## 🛠 Slash commands

```
/help                              show help
/providers                         list configured providers
/use <name>                        switch active provider
/set base_url|api_key|model <v>    update active provider
/add <name>                        add new provider preset
/system <prompt>                   change system prompt
/tools [on|off]                    list / toggle agent tools
/memory                            show memory stats
/memory show [entity]              dump facts about entity (default: user)
/memory search <q>                 search memory
/memory forget <q>                 delete matching items
/memory clear                      wipe all memory
/tts piper|pyttsx3                 switch TTS engine (restart to apply)
/tts voice <name>                  set Piper voice model
/reset /save /load                 history mgmt
/voice                             toggle voice/text input
/voices                            list pyttsx3 voices
/quit                              exit
```

### Examples

```
/use google
/set model gemini-2.0-flash
/add mycloud
/set base_url https://my-llm.example.com/v1
/set api_key sk-...
/set model my-7b
/tools off          # disable tool-calling for this turn-style chat
```

---

## ➕ Adding your own tools

Open `tools.py` and add a function:

```python
@tool(
    description="Tell me a joke from a topic.",
    parameters={
        "type":"object",
        "properties":{"topic":{"type":"string"}},
        "required":["topic"],
    },
)
def tell_joke(topic: str) -> str:
    return f"Why did the {topic} cross the road? ..."
```

That's it — restart and the LLM can call it automatically.

For tools that do something destructive (delete files, send messages, etc.),
add `confirm=True` to the decorator and wire a confirmation step in the
main loop.

---

## 🗂 Files

```
voice_assistant/
├── assistant.py        # CLI main program (STT + LLM + TTS + tool loop)
├── gui.py              # AERA Agent PySide6 desktop window (shell)
├── pages.py            # Dashboard / Macros / Apps / Gallery / Phone / Settings pages
├── wake.py             # Wake-word detector (Porcupine + SpeechRecognition)
├── tools.py            # 40 agent tools + registry
├── memory.py           # graph long-term memory store
├── tts_piper.py        # Piper neural TTS backend
├── tts_omnivoice.py    # OmniVoice neural TTS backend (voice cloning, multilingual)
├── stt_sensevoice.py   # SenseVoice STT backend (offline, multilingual)
├── speaker_id.py       # Voice biometric — enroll, verify, identify (ECAPA-TDNN)
├── voice_studio.py     # Voice Studio page (record/manage clone voices + speakers)
├── theme.py            # Shared palette + button stylesheets (single source of truth)
├── omnivoice/          # Xiaomi OmniVoice source files (Apache-2.0)
│   ├── omnivoice_model.py    # main OmniVoice model class
│   ├── sensevoice_eval.py    # CER eval script (Cantonese)
│   ├── speaker_sim_eval.py   # SIM-o speaker similarity eval
│   ├── sample_processor.py   # training data processor
│   └── dataset.py            # WebDataset training loader
├── config.json         # providers, voice, STT, wake, memory settings
├── requirements.txt
├── memory.json         # auto-created: knowledge graph
├── macros.json         # auto-created: saved macro phrases
├── apps.json           # auto-created: app launchers
├── contacts.json       # auto-created: phone contacts
├── reminders.json      # auto-created
├── notes.txt           # auto-created
├── voices/             # cached Piper .onnx voices
├── workspace/          # sandbox for file tools (gallery/, Default/)
├── history.json        # created by /save
└── README.md

---

## 🎙️ STT engines

| Engine | Languages | Hardware | Notes |
|---|---|---|---|
| **google** (default) | depends on `language` code | any | Free, needs internet. Uses Google Web Speech via `SpeechRecognition` |
| **sensevoice** | en, zh, ja, ko, yue (auto-detect) | GPU recommended; CPU OK | Offline after ~1 GB download. Much more accurate. Install: `pip install funasr soundfile webrtcvad` |

Switch in **Settings → Speech → Engine**, or edit `config.json` → `"speech": {"engine": "sensevoice"}`.

## 🔊 TTS engines

| Engine | Quality | Hardware | Notes |
|---|---|---|---|
| **pyttsx3** (default) | robotic | any | Always works, offline, no download |
| **piper** | natural neural | CPU fine | ~30 MB voice models, 40+ languages. `pip install piper-tts` |
| **omnivoice** | high-quality, voice cloning | CUDA strongly recommended | ~3-5 GB model, can clone any voice from a 5-15 s sample |

Switch in **Settings → Voice → Engine**.

### Voice cloning with OmniVoice

1. Record a 5-15 s wav of any voice (or use a sample like `voices/me.wav`).
2. Type the **exact transcript** of what's said in that wav.
3. In Settings → Voice, set:
   - **Engine:** omnivoice
   - **Clone ref audio (wav):** `voices/me.wav`
   - **Clone ref transcript:** *exact words spoken*
4. Save & restart. AERA will now speak everything in that voice.

Alternatively, leave the clone fields blank and use **Voice design** — a text description like *"warm female voice, mid-30s, slight British accent"* — and OmniVoice will synthesize a matching voice.

### About the `omnivoice/` folder

These are the original source files from Xiaomi's [OmniVoice](https://github.com/k2-fsa/omnivoice) (Apache-2.0).
The integration shim (`tts_omnivoice.py`) wraps them in our `Speaker` interface.
Files included for completeness:

- `omnivoice_model.py` — the `OmniVoice` PyTorch model (loaded by the TTS backend)
- `sensevoice_eval.py` — research script: CER evaluation for Cantonese
- `speaker_sim_eval.py` — research script: SIM-o speaker similarity scoring
- `sample_processor.py`, `dataset.py` — training-time data pipeline (not used at inference)

You can use the eval scripts standalone for benchmarking, e.g.:
```bash
python -m omnivoice.sensevoice_eval --wav-path ./audio --test-list test.jsonl --model-dir ./eval_models
```

---

## 🔐 Speaker verification (voice biometric)

Built on **ECAPA-TDNN** speaker embeddings (via SpeechBrain). Uses the same
math as `omnivoice/speaker_sim_eval.py` but exposed as an interactive feature.

### Install
```bash
pip install speechbrain torch torchaudio
# ~80 MB model downloads on first use
```

### Use it in the GUI

Open **Studio**, press `● Record` (3-5 seconds), then:

- **Save as clone voice** → asks for a name and exact transcript → activates that
  voice as the OmniVoice clone reference
- **Enroll as speaker** → asks for a profile name → stores a speaker embedding

Then in the right column:

- **Verify (4 s)** → records you and checks if you match the selected enrolled speaker
- **Identify (4 s)** → records and finds the best match among all enrolled

### Use it from the assistant (voice commands)

Six new agent tools (the LLM picks them automatically):

| Tool | Triggered by saying… |
|---|---|
| `enroll_voice(name)` | "Enroll my voice as owner" |
| `verify_voice(name)` | "Verify I'm the owner" |
| `identify_speaker()` | "Who's talking?" |
| `list_speakers()` | "Show enrolled speakers" |
| `delete_speaker(name)` | "Delete the alice profile" |
| `voice_similarity(a, b)` | "Compare voices/me.wav and voices/clone_output.wav" |

### Cosine similarity scale
- `> 0.85` very high (same speaker, clean audio)
- `> 0.70` high
- `> 0.55` probable match — default threshold
- `< 0.55` reject

### Use case: guard sensitive tools
Add a check at the top of `tools.dispatch()` for tools you mark as sensitive:
```python
if _REGISTRY[name].requires_confirm and not is_owner_verified:
    return "denied: voice verification required"
```
```

---

## 🩺 Notes

- **Tool calls require a model that supports function-calling.** Groq's Llama
  3.3 70B and Gemini 2.0 Flash both do. Older models or pure-completion
  models will simply ignore tools.
- Web tools use stdlib `urllib` — no extra deps.
- File tools are **sandboxed** to `voice_assistant/workspace/`.
- `open_app` is OS-dependent and tagged `confirm=True`.

Enjoy! 🎉
