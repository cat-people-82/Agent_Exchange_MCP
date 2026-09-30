"""On-disk conversation storage: one JSON file per conversation."""

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

_ID_RE = re.compile(r"^[0-9a-f]{12}$")


@dataclass
class Conversation:
    system: str | None = None
    provider: str | None = None  # last provider used; default for the next turn
    messages: list[dict[str, str]] = field(default_factory=list)


class Store:
    def __init__(self, directory: Path):
        self.dir = directory

    def _path(self, cid: str) -> Path:
        if not _ID_RE.match(cid):  # also blocks path traversal
            raise ValueError(f"Invalid conversation_id '{cid}'")
        return self.dir / f"{cid}.json"

    def exists(self, cid: str) -> bool:
        return self._path(cid).is_file()

    def load(self, cid: str) -> Conversation:
        try:
            return Conversation(**json.loads(self._path(cid).read_text()))
        except FileNotFoundError:
            raise ValueError(f"Unknown conversation_id '{cid}'") from None

    def save(self, cid: str, convo: Conversation) -> None:
        path = self._path(cid)
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(convo), indent=2))
        os.replace(tmp, path)  # atomic: a crash never leaves a half-written file

    def delete(self, cid: str) -> None:
        try:
            self._path(cid).unlink()
        except FileNotFoundError:
            raise ValueError(f"Unknown conversation_id '{cid}'") from None

    def list_ids(self) -> list[str]:
        if not self.dir.is_dir():
            return []
        files = sorted(self.dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        return [p.stem for p in files if _ID_RE.match(p.stem)]
