"""
Graph-based long-term memory for the Voice Assistant.

Stores facts as a knowledge graph of (subject, predicate, object) triples
plus free-form notes. Persisted to memory.json. Designed for an LLM to
read and write via tool calls — but also queryable from Python.

Why a graph instead of just a list of notes?
  • Facts about the same entity stay linked ("user" → "dog name" → "Rex",
    "user" → "city" → "Kathmandu", "user.dog" → "breed" → "Beagle").
  • Easy retrieval: get everything we know about <entity> in one call.
  • Easy traversal: follow links to related entities.
  • Easy editing: forget one fact without nuking the rest.
  • Small, no DB dependency — pure JSON + dict-of-dicts.

Schema (in-memory & on disk):
{
  "nodes": {
      "user":      {"type": "person", "name": "user", "created": "..."},
      "user.dog":  {"type": "pet",    "name": "Rex"}
  },
  "edges": [
      {"s": "user", "p": "has_dog", "o": "user.dog", "ts": "...", "src": "remember"},
      {"s": "user", "p": "lives_in", "o": "Kathmandu", "ts": "...", "src": "remember"}
  ],
  "notes": [
      {"text": "Likes coffee black", "ts": "...", "tags": ["preference"]}
  ]
}

Object values can be either:
  * a string literal ("Kathmandu", "Rex", "2026-12-25")
  * a node id that exists in "nodes"  (creating a sub-entity)
"""

import datetime as dt
import json
import re
from pathlib import Path

from .paths import MEMORY_FILE as MEM_FILE

# Pre-compiled regexes used in _slug() — module-level for speed
_SLUG_WHITESPACE = re.compile(r"\s+")
_SLUG_FORBIDDEN  = re.compile(r"[^\w.\-]")


# ============================================================ #
#  STORE
# ============================================================ #
class MemoryGraph:
    def __init__(self, path: Path = MEM_FILE):
        self.path = path
        if path.exists():
            try:
                self.data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                self.data = self._empty()
        else:
            self.data = self._empty()
        # ensure root user node always exists
        self.data.setdefault("nodes", {})
        self.data.setdefault("edges", [])
        self.data.setdefault("notes", [])
        if "user" not in self.data["nodes"]:
            self.data["nodes"]["user"] = {
                "type": "person", "name": "user",
                "created": _now(),
            }
            self._save()

    @staticmethod
    def _empty() -> dict:
        return {"nodes": {}, "edges": [], "notes": []}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    # ---------------- writes ---------------- #
    def add_fact(self, subject: str, predicate: str, obj: str, src: str = "user") -> str:
        subject = _slug(subject)
        predicate = _slug(predicate)
        # auto-create subject node
        self.data["nodes"].setdefault(subject, {"type": "entity", "name": subject, "created": _now()})
        # if obj looks like a sub-entity reference, create node; else literal
        is_node = obj.startswith(":") or "." in obj and not any(c.isspace() for c in obj)
        o_value = obj.lstrip(":")
        if is_node:
            self.data["nodes"].setdefault(o_value, {"type": "entity", "name": o_value, "created": _now()})
        # dedupe identical triple
        for e in self.data["edges"]:
            if e["s"] == subject and e["p"] == predicate and e["o"] == o_value:
                e["ts"] = _now()
                self._save()
                return f"(updated) {subject} --{predicate}--> {o_value}"
        self.data["edges"].append({
            "s": subject, "p": predicate, "o": o_value,
            "ts": _now(), "src": src,
        })
        self._save()
        return f"remembered: {subject} --{predicate}--> {o_value}"

    def add_note(self, text: str, tags: list[str] | None = None) -> str:
        self.data["notes"].append({
            "text": text, "ts": _now(), "tags": tags or [],
        })
        self._save()
        return f"noted ({len(self.data['notes'])} total)."

    def forget(self, query: str) -> str:
        """Remove edges/notes whose text matches the query (case-insensitive substring)."""
        q = query.lower()
        removed = 0
        kept_edges = []
        for e in self.data["edges"]:
            blob = f"{e['s']} {e['p']} {e['o']}".lower()
            if q in blob:
                removed += 1
            else:
                kept_edges.append(e)
        self.data["edges"] = kept_edges

        kept_notes = []
        for n in self.data["notes"]:
            if q in n["text"].lower():
                removed += 1
            else:
                kept_notes.append(n)
        self.data["notes"] = kept_notes
        self._save()
        return f"forgot {removed} item(s) matching '{query}'."

    def clear(self) -> str:
        self.data = self._empty()
        self.data["nodes"]["user"] = {"type": "person", "name": "user", "created": _now()}
        self._save()
        return "memory cleared."

    # ---------------- reads ---------------- #
    def about(self, entity: str, depth: int = 1) -> str:
        """Return everything we know about <entity>, optionally following links."""
        entity = _slug(entity)
        if entity not in self.data["nodes"] and \
           not any(e["s"] == entity for e in self.data["edges"]):
            return f"(nothing known about '{entity}')"

        lines: list[str] = [f"# {entity}"]
        seen = {entity}

        def walk(node: str, d: int, indent: str = "  "):
            for e in self.data["edges"]:
                if e["s"] == node:
                    lines.append(f"{indent}- {e['p']}: {e['o']}")
                    if d > 0 and e["o"] in self.data["nodes"] and e["o"] not in seen:
                        seen.add(e["o"])
                        lines.append(f"{indent}  (about {e['o']})")
                        walk(e["o"], d - 1, indent + "    ")
        walk(entity, max(0, depth - 1))
        return "\n".join(lines)

    def search(self, query: str, limit: int = 10) -> str:
        q = query.lower()
        hits = []
        for e in self.data["edges"]:
            blob = f"{e['s']} {e['p']} {e['o']}"
            if q in blob.lower():
                hits.append(f"• {e['s']} --{e['p']}--> {e['o']}")
        for n in self.data["notes"]:
            if q in n["text"].lower():
                hits.append(f"• note: {n['text']}")
        if not hits:
            return f"(no matches for '{query}')"
        return "\n".join(hits[:limit])

    def all_notes(self, limit: int = 50) -> str:
        if not self.data["notes"]:
            return "(no notes)"
        out = []
        for n in self.data["notes"][-limit:]:
            tags = f" [{', '.join(n['tags'])}]" if n["tags"] else ""
            out.append(f"• {n['text']}{tags}  ({n['ts'][:10]})")
        return "\n".join(out)

    def stats(self) -> str:
        return (f"{len(self.data['nodes'])} entities, "
                f"{len(self.data['edges'])} facts, "
                f"{len(self.data['notes'])} notes")

    def snapshot_for_prompt(self, max_facts: int = 40) -> str:
        """Compact summary to inject into the system prompt at startup."""
        if not self.data["edges"] and not self.data["notes"]:
            return ""
        lines = ["Known facts about the user:"]
        for e in self.data["edges"][-max_facts:]:
            lines.append(f"- {e['s']} {e['p']} {e['o']}")
        if self.data["notes"]:
            lines.append("Recent notes:")
            for n in self.data["notes"][-10:]:
                lines.append(f"- {n['text']}")
        return "\n".join(lines)


# ============================================================ #
#  helpers
# ============================================================ #
def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _slug(s: str) -> str:
    s = _SLUG_WHITESPACE.sub("_", s.strip())
    s = _SLUG_FORBIDDEN.sub("", s)
    return s.lower() or "unknown"


# ============================================================ #
#  Module-level singleton + tool registration helpers
#  (imported by tools.py)
# ============================================================ #
_GRAPH: MemoryGraph | None = None

def graph() -> MemoryGraph:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = MemoryGraph()
    return _GRAPH
