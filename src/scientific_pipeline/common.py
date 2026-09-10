from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def file_hash(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def md5_file(path: Path) -> str:
    return file_hash(path, "md5")


def sha256_file(path: Path) -> str:
    return file_hash(path, "sha256")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def sample_id_from_library(library_name: str) -> str:
    prefix = library_name.split("_", maxsplit=1)[0]
    return prefix.replace("-", ".")


def get_logger() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return logging.getLogger("scientific_pipeline")
