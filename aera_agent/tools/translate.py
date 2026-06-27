"""Free machine translation via MyMemory."""

import urllib.parse

from . import tool
from ._http import http_json


@tool(
    description="Translate text between languages using free MyMemory API. "
                "Use ISO codes like 'en', 'es', 'fr', 'ne', 'ja'.",
    parameters={
        "type": "object",
        "properties": {
            "text":   {"type": "string"},
            "source": {"type": "string", "default": "auto"},
            "target": {"type": "string"},
        },
        "required": ["text", "target"],
    },
)
def translate(text: str, target: str, source: str = "auto") -> str:
    src = source if source != "auto" else "en"
    url = "https://api.mymemory.translated.net/get?" + urllib.parse.urlencode({
        "q": text, "langpair": f"{src}|{target}"
    })
    try:
        data = http_json(url)
        return data["responseData"]["translatedText"]
    except Exception as e:
        return f"Translate error: {e}"
