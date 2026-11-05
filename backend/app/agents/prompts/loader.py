"""Load versioned agent prompts from Markdown files.

Every prompt starts with a ``version:`` line so a run can record which prompt
produced an output. The version line is metadata and is not sent to the model.
"""

import re
from pathlib import Path
from typing import Final, NamedTuple

_PROMPTS_DIR: Final[Path] = Path(__file__).resolve().parent
_SAFE_NAME: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9_]{1,32}$")
_VERSION_LINE: Final[re.Pattern[str]] = re.compile(
    r"version:\s*(?P<version>\S+)\s*$",
    re.IGNORECASE,
)


class LoadedPrompt(NamedTuple):
    """Prompt body and the version declared on its first line."""

    text: str
    version: str


def load_prompt(agent_name: str, *, prompts_dir: Path | None = None) -> LoadedPrompt:
    """Read an agent prompt, rejecting unsafe names and unversioned files.

    ``prompts_dir`` exists for tests; production callers should use the
    default package directory so prompts stay alongside the agents.
    """
    if not _SAFE_NAME.fullmatch(agent_name):
        raise ValueError(f"invalid agent name for a prompt: {agent_name!r}")

    root = prompts_dir if prompts_dir is not None else _PROMPTS_DIR
    path = root / f"{agent_name}.md"
    raw = _read(path)
    first_line, separator, body = raw.partition("\n")
    match = _VERSION_LINE.fullmatch(first_line.strip())
    if match is None:
        raise ValueError(f"prompt {path} must start with a 'version:' line")

    text = body.strip() if separator else ""
    if not text:
        raise ValueError(f"prompt {path} has no body after its version line")
    return LoadedPrompt(text=text, version=match.group("version"))


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"prompt file not found: {path}") from exc
