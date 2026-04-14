import json
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def shared_path(name: str) -> Path:
    return repo_root() / "shared" / name


def load_shared_json(name: str) -> Any:
    return json.loads(shared_path(name).read_text())


def load_shared_text(name: str) -> str:
    return shared_path(name).read_text().strip()
