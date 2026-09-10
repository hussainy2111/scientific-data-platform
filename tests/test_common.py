from pathlib import Path

from scientific_pipeline.common import (
    md5_file,
    sample_id_from_library,
    sha256_file,
)


def test_sample_id_from_library() -> None:
    library = "MCL1-DG_BC2CTUACXX_ACTTGA_L002_R1"

    assert sample_id_from_library(library) == "MCL1.DG"


def test_md5_file(tmp_path: Path) -> None:
    path = tmp_path / "value.txt"
    path.write_text("abc", encoding="utf-8")

    assert md5_file(path) == "900150983cd24fb0d6963f7d28e17f72"


def test_sha256_file(tmp_path: Path) -> None:
    path = tmp_path / "value.txt"
    path.write_text("abc", encoding="utf-8")

    assert sha256_file(path) == (
        "ba7816bf8f01cfea414140de5dae2223"
        "b00361a396177a9cb410ff61f20015ad"
    )
