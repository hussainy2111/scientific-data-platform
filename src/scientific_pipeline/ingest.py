from __future__ import annotations

import argparse
import gzip
import shutil
import uuid
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .common import get_logger, md5_file, sha256_file, utc_now, write_json

PIPELINE_VERSION = "0.1.0"


def build_session() -> requests.Session:
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )

    session = requests.Session()

    adapter = HTTPAdapter(
        max_retries=retry,
    )

    session.mount(
        "https://",
        adapter,
    )

    session.mount(
        "http://",
        adapter,
    )

    return session


def download(
    url: str,
    destination: Path,
) -> None:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    partial_path = destination.with_suffix(
        destination.suffix + ".part"
    )

    if partial_path.exists():
        partial_path.unlink()

    session = build_session()

    try:
        with session.get(
            url,
            stream=True,
            timeout=(30, 300),
        ) as response:
            response.raise_for_status()

            with partial_path.open("wb") as handle:
                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):
                    if chunk:
                        handle.write(chunk)

        partial_path.replace(destination)

    finally:
        session.close()

        if partial_path.exists():
            partial_path.unlink()


def decompress_gzip(
    source: Path,
    destination: Path,
) -> None:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with gzip.open(source, "rb") as source_handle:
        with destination.open("wb") as destination_handle:
            shutil.copyfileobj(
                source_handle,
                destination_handle,
            )


def verify_md5(
    path: Path,
    expected: str,
) -> str:
    observed = md5_file(path)

    if observed.lower() != expected.lower():
        raise ValueError(
            f"Checksum mismatch for {path.name}: "
            f"expected {expected}, observed {observed}"
        )

    return observed


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--counts-url",
        required=True,
    )

    parser.add_argument(
        "--samples-url",
        required=True,
    )

    parser.add_argument(
        "--counts-md5",
        required=True,
    )

    parser.add_argument(
        "--samples-md5",
        required=True,
    )

    parser.add_argument(
        "--counts-out",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--samples-out",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--manifest-out",
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    logger = get_logger()

    compressed_counts = Path(
        str(args.counts_out) + ".gz"
    )

    logger.info(
        "Downloading compressed count matrix"
    )

    download(
        args.counts_url,
        compressed_counts,
    )

    compressed_sha256 = sha256_file(
        compressed_counts
    )

    compressed_size = compressed_counts.stat().st_size

    logger.info(
        "Decompressing count matrix"
    )

    decompress_gzip(
        compressed_counts,
        args.counts_out,
    )

    logger.info(
        "Downloading sample metadata"
    )

    download(
        args.samples_url,
        args.samples_out,
    )

    logger.info(
        "Verifying count matrix checksum"
    )

    counts_md5 = verify_md5(
        args.counts_out,
        args.counts_md5,
    )

    logger.info(
        "Verifying metadata checksum"
    )

    samples_md5 = verify_md5(
        args.samples_out,
        args.samples_md5,
    )

    manifest = {
        "run_id": str(uuid.uuid4()),
        "pipeline_version": PIPELINE_VERSION,
        "retrieved_at": utc_now(),
        "dataset": "GSE60450",
        "sources": {
            "counts": {
                "url": args.counts_url,
                "source_format": "gzip",
                "compressed_bytes": compressed_size,
                "compressed_sha256": compressed_sha256,
                "output_filename": args.counts_out.name,
                "output_bytes": args.counts_out.stat().st_size,
                "md5": counts_md5,
                "sha256": sha256_file(
                    args.counts_out
                ),
            },
            "samples": {
                "url": args.samples_url,
                "filename": args.samples_out.name,
                "bytes": args.samples_out.stat().st_size,
                "md5": samples_md5,
                "sha256": sha256_file(
                    args.samples_out
                ),
            },
        },
    }

    write_json(
        args.manifest_out,
        manifest,
    )

    compressed_counts.unlink()

    logger.info(
        "Ingestion complete counts_bytes=%d samples_bytes=%d",
        args.counts_out.stat().st_size,
        args.samples_out.stat().st_size,
    )


if __name__ == "__main__":
    main()
