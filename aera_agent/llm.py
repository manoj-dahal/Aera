"""LLM client with streaming + OpenAI-compatible tool-calling."""

import re
from typing import Iterable

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from .tools import openai_schemas, dispatch


class LLM:
    """OpenAI-compatible chat client with tool-loop and streaming."""

    def __init__(self, provider: dict, system_prompt: str, use_tools: bool = True):
        self.refresh(provider)
        self.system_prompt = system_prompt
        self.history: list[dict] = []
        self.use_tools = use_tools
        self.max_tool_loops = 5

    # --------------------------------------------------------------- #
    def refresh(self, provider: dict) -> None:
        if OpenAI is None:
            raise RuntimeError("openai package not installed. Run: pip install openai")
        self.provider = provider
        self.client = OpenAI(
            base_url=provider["base_url"],
            api_key=provider["api_key"],
        )
        self.model = provider["model"]

    def reset(self) -> None:
        self.history.clear()

    def _messages(self) -> list[dict]:
        return [{"role": "system", "content": self.system_prompt}] + self.history

    # --------------------------------------------------------------- #
    def stream_reply(self, user_text: str) -> Iterable[str]:
        """Yield text deltas, handling internal tool-call loops transparently."""
        self.history.append({"role": "user", "content": user_text})
        loops = 0

        while True:
            loops += 1
            if loops > self.max_tool_loops:
                yield "\n[stopped: too many tool loops]"
                return

            kwargs = {"model": self.model, "messages": self._messages()}
            if self.use_tools:
                kwargs["tools"] = openai_schemas()
                kwargs["tool_choice"] = "auto"

            try:
                resp = self.client.chat.completions.create(**kwargs)
            except Exception as e:
                yield f"[LLM error: {e}]"
                self.history.pop()
                return

            msg = resp.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None)

            if tool_calls:
                self.history.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {"id": tc.id, "type": "function",
                         "function": {"name": tc.function.name,
                                      "arguments": tc.function.arguments}}
                        for tc in tool_calls
                    ],
                })
                for tc in tool_calls:
                    name = tc.function.name
                    args = tc.function.arguments
                    print(f"\n  🔧 calling {name}({args})", flush=True)
                    result = dispatch(name, args)
                    print(f"  ↳ {result[:200]}{'…' if len(result) > 200 else ''}",
                          flush=True)
                    self.history.append({
                        "role": "tool", "tool_call_id": tc.id,
                        "name": name, "content": result,
                    })
                continue

            # final answer — chunk it out so the TTS sentence-splitter still works
            final = msg.content or ""
            self.history.append({"role": "assistant", "content": final})
            for chunk in re.findall(r".{1,80}(?:\s|$)", final, flags=re.S):
                yield chunk
            return


# --------------------------------------------------------------- #
#  Streaming TTS helpers (used by the CLI and GUI worker)
# --------------------------------------------------------------- #
_SENT_END = re.compile(r"(?<=[\.\!\?。！？])\s+|\n+")
_MD_CODE_BLOCK = re.compile(r"```.*?```", re.S)
_MD_INLINE     = re.compile(r"`([^`]+)`")
_MD_PUNCT      = re.compile(r"[*_#>]+")
_MD_LINK       = re.compile(r"\[(.*?)\]\(.*?\)")


class SentenceBuffer:
    """Accumulates token deltas, flushes complete sentences for TTS."""
    def __init__(self):
        self.buf = ""

    def feed(self, delta: str) -> list[str]:
        self.buf += delta
        out = []
        while True:
            m = _SENT_END.search(self.buf)
            if not m:
                if len(self.buf) > 160 and "," in self.buf:
                    cut = self.buf.rfind(",", 0, 160) + 1
                    out.append(self.buf[:cut].strip())
                    self.buf = self.buf[cut:].lstrip()
                    continue
                break
            sent = self.buf[:m.end()].strip()
            self.buf = self.buf[m.end():]
            if sent:
                out.append(sent)
        return out

    def flush(self) -> str:
        s = self.buf.strip()
        self.buf = ""
        return s


def strip_for_tts(text: str) -> str:
    """Remove markdown / code so the voice doesn't say 'asterisk asterisk'."""
    text = _MD_CODE_BLOCK.sub(" (code omitted) ", text)
    text = _MD_INLINE.sub(r"\1", text)
    text = _MD_PUNCT.sub("", text)
    text = _MD_LINK.sub(r"\1", text)
    return text
