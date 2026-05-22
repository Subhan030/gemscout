"""Checkpoint persistence helpers."""

import json
from pathlib import Path


def save_checkpoint(data: list[dict], path: str) -> None:
    """Atomically write checkpoint data to a JSON file."""
    checkpoint_path = Path(path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = checkpoint_path.with_suffix(f"{checkpoint_path.suffix}.tmp")
    temp_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(checkpoint_path)


def load_checkpoint(path: str) -> list[dict]:
    """Load checkpoint data, or return an empty list when absent."""
    checkpoint_path = Path(path)
    if not checkpoint_path.exists():
        return []
    with checkpoint_path.open("r", encoding="utf-8") as checkpoint_file:
        loaded = json.load(checkpoint_file)
    if not isinstance(loaded, list):
        raise ValueError(f"Checkpoint must contain a list: {path}")
    return loaded

