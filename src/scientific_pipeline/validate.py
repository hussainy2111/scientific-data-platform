from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .common import (
    get_logger,
    read_yaml,
    sample_id_from_library,
    sha256_file,
    utc_now,
    write_json,
)

REQUIRED_METADATA_COLUMNS = {
    "FileName",
    "SampleName",
    "CellType",
    "Status",
}


def validate_counts(
    counts_path: Path,
    samples_path: Path,
    config_path: Path,
) -> dict:
    config = read_yaml(config_path)

    counts = pd.read_csv(counts_path, sep="\t")
    samples = pd.read_csv(samples_path, sep="\t")

    if list(counts.columns[:2]) != ["EntrezGeneID", "Length"]:
        raise ValueError(
            "Unexpected count matrix columns. "
            "Expected EntrezGeneID and Length first."
        )

    missing_metadata = REQUIRED_METADATA_COLUMNS - set(samples.columns)

    if missing_metadata:
        raise ValueError(
            f"Metadata is missing columns: {sorted(missing_metadata)}"
        )

    if counts.empty:
        raise ValueError("Count matrix is empty.")

    if samples.empty:
        raise ValueError("Sample metadata is empty.")

    if counts["EntrezGeneID"].isna().any():
        raise ValueError("EntrezGeneID contains missing values.")

    if counts["EntrezGeneID"].duplicated().any():
        raise ValueError("EntrezGeneID contains duplicates.")

    if counts["Length"].isna().any():
        raise ValueError("Gene length contains missing values.")

    if (counts["Length"] <= 0).any():
        raise ValueError("Gene length must be greater than zero.")

    library_columns = list(counts.columns[2:])

    if not library_columns:
        raise ValueError("No sample columns were found in the count matrix.")

    sample_ids = [
        sample_id_from_library(name)
        for name in library_columns
    ]

    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("Library names map to duplicate sample IDs.")

    metadata_ids = samples["SampleName"].astype(str).str.strip().tolist()

    if len(metadata_ids) != len(set(metadata_ids)):
        raise ValueError("SampleName contains duplicate values.")

    if set(sample_ids) != set(metadata_ids):
        missing = sorted(set(sample_ids) - set(metadata_ids))
        extra = sorted(set(metadata_ids) - set(sample_ids))

        raise ValueError(
            f"Count matrix and metadata do not match. "
            f"Missing metadata={missing}; extra metadata={extra}"
        )

    for column in library_columns:
        values = counts[column]

        if values.isna().any():
            raise ValueError(f"{column} contains missing counts.")

        if (values < 0).any():
            raise ValueError(f"{column} contains negative counts.")

        if not ((values % 1) == 0).all():
            raise ValueError(f"{column} contains non-integer counts.")

    required_metadata = samples[
        ["FileName", "SampleName", "CellType", "Status"]
    ]

    null_fraction = float(required_metadata.isna().mean().mean())

    allowed_null_fraction = float(
        config["quality"]["max_metadata_null_fraction"]
    )

    if null_fraction > allowed_null_fraction:
        raise ValueError(
            f"Metadata null fraction {null_fraction:.6f} exceeds "
            f"{allowed_null_fraction:.6f}."
        )

    return {
        "checked_at": utc_now(),
        "status": "PASS",
        "gene_count": int(len(counts)),
        "sample_count": int(len(library_columns)),
        "expression_value_count": int(
            len(counts) * len(library_columns)
        ),
        "metadata_null_fraction": null_fraction,
        "counts_sha256": sha256_file(counts_path),
        "samples_sha256": sha256_file(samples_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--counts", type=Path, required=True)
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)

    args = parser.parse_args()

    logger = get_logger()

    result = validate_counts(
        args.counts,
        args.samples,
        args.config,
    )

    write_json(args.out, result)

    logger.info(
        "Validation passed genes=%d samples=%d",
        result["gene_count"],
        result["sample_count"],
    )


if __name__ == "__main__":
    main()
