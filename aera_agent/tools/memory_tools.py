"""LLM-callable wrappers around the graph long-term memory."""

from . import tool
from ..memory import graph as _mem


@tool(
    description=(
        "Save a long-term fact about the user (or any entity) to memory. "
        "Use when the user says 'remember that…', 'my X is Y', or shares "
        "personal info worth keeping. Subject is the entity (e.g. 'user', "
        "'user.dog', 'project_alpha'), predicate is the relation "
        "(e.g. 'name', 'lives_in', 'birthday', 'likes'), object is the value."
    ),
    parameters={
        "type": "object",
        "properties": {
            "subject":   {"type": "string"},
            "predicate": {"type": "string"},
            "object":    {"type": "string", "description": "Prefix with ':' to mark as sub-entity."},
        },
        "required": ["subject", "predicate", "object"],
    },
)
def remember(subject: str, predicate: str, object: str) -> str:
    return _mem().add_fact(subject, predicate, object, src="llm")


@tool(
    description="Save a free-form long-term note (anything not easily structured as a triple).",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}, "default": []},
        },
        "required": ["text"],
    },
)
def remember_note(text: str, tags: list[str] | None = None) -> str:
    return _mem().add_note(text, tags or [])


@tool(
    description="Recall everything known about an entity. Use when the user asks "
                "'what do you know about X' or before answering personal questions.",
    parameters={
        "type": "object",
        "properties": {
            "entity": {"type": "string", "default": "user"},
            "depth":  {"type": "integer", "default": 1, "minimum": 1, "maximum": 3},
        },
    },
)
def recall(entity: str = "user", depth: int = 1) -> str:
    return _mem().about(entity, depth)


@tool(
    description="Search long-term memory by free-text query.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
)
def memory_search(query: str) -> str:
    return _mem().search(query)


@tool(
    description="Delete memory items matching the query. Use when the user says 'forget that…'.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    confirm=True,
)
def forget(query: str) -> str:
    return _mem().forget(query)


@tool(description="Get statistics about long-term memory (entity / fact / note counts).",
      parameters={"type": "object", "properties": {}})
def memory_stats() -> str:
    return _mem().stats()
