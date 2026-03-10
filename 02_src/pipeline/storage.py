"""
Storage layer: read/write JSON results and state files.
"""
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


def ensure_dir(path: Path) -> None:
    """Create directory (and parents) if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)


def save_json(path: Path, data: Any, indent: int = 2) -> None:
    """Write data as JSON to path, creating parent dirs as needed."""
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def load_json(path: Path) -> Any:
    """Load JSON from path. Returns None if file does not exist."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_text_as_json(path: Path, framework: str, content: str) -> dict:
    """
    Wrap a plain-text research result in standard envelope and save.
    Returns the saved dict.
    """
    data = {
        "framework": framework,
        "content": content,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    save_json(path, data)
    return data


def save_raw_query(path: Path, jurisdiction: str, query: str, content: str) -> dict:
    """
    Wrap raw text query result in standard envelope and save.
    Returns the saved dict.
    """
    data = {
        "jurisdiction": jurisdiction,
        "query": query,
        "content": content,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    save_json(path, data)
    return data


def save_prompt(prompts_dir: Path, name: str, prompt: str) -> None:
    """Save a prompt string for reproducibility."""
    ensure_dir(prompts_dir)
    path = prompts_dir / f"{name}.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(prompt)


def now_iso() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()
