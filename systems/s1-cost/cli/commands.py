"""Slash-command handling for Nano CC."""

import os

from utils.config import MODELS
from cli.session import Session

HELP_TEXT = """Available commands:
  /model <name>  Switch model (sonnet | haiku)
  /file <path>   Read a file and inject as context
  /cost          Show session cost summary
  /clear         Clear conversation history
  /help          Show this help
  /quit /exit    Exit Nano CC"""


def handle_command(raw: str, session: Session) -> str | None:
    """Process a slash command. Returns display text, or None to quit."""
    parts = raw.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd in ("/quit", "/exit"):
        return None

    if cmd == "/help":
        return HELP_TEXT

    if cmd == "/model":
        return _cmd_model(arg, session)

    if cmd == "/file":
        return _cmd_file(arg, session)

    if cmd == "/cost":
        return _cmd_cost(session)

    if cmd == "/clear":
        session.clear()
        return "Conversation cleared."

    return f"Unknown command: {cmd}. Type /help for available commands."


def _cmd_model(arg: str, session: Session) -> str:
    name = arg.strip().lower()
    if name not in MODELS:
        return f"Unknown model '{name}'. Available: {', '.join(MODELS)}"
    session.model = name
    return f"Switched to {MODELS[name]['name']} ({MODELS[name]['id']})"


def _cmd_file(arg: str, session: Session) -> str:
    path = arg.strip()
    if not path:
        return "Usage: /file <path>"
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        return f"File not found: {path}"
    try:
        content = open(path, encoding="utf-8").read()
    except Exception as e:
        return f"Error reading file: {e}"
    session.add_user_message(f"<file path=\"{path}\">\n{content}\n</file>")
    return f"File loaded ({len(content)} chars). Ask a question about it."


def _cmd_cost(session: Session) -> str:
    s = session.stats
    lines = [
        f"Session: {s.calls} calls | {s.input_tokens} in / {s.output_tokens} out | ${s.cost_usd:.6f}",
        "",
    ]
    for name, m in s.per_model.items():
        if m["calls"] > 0:
            lines.append(
                f"  {name}: {m['calls']} calls | "
                f"{m['input_tokens']} in / {m['output_tokens']} out | "
                f"${m['cost']:.6f}"
            )
    return "\n".join(lines)
