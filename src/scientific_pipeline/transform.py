from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pandas as pd

from .common import get_logger, sample_id_from_library, utc_now, write_json


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--counts", type=Path, required=True)
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)

    parser.add_argument("--expression-out", type=Path, required=True)
    parser.add_argument("--samples-out", type=Path, required=True)
    parser.add_argument("--genes-out", type=Path, required=True)
    parser.add_argument("--manifest-out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path, required=True)

    args = parser.parse_args()

    logger = get_logger()

    counts = pd.read_csv(args.counts, sep="\t")
    metadata = pd.read_csv(args.samples, sep="\t")

    library_columns = list(counts.columns[2:])

    gene_table = (
        counts[["EntrezGeneID", "Length"]]
        .rename(
            columns={
                "EntrezGeneID": "gene_id",
                "Length": "gene_length",
            }
        )
        .copy()
    )

    gene_table["gene_id"] = gene_table["gene_id"].astype("int64")
    gene_table["gene_length"] = gene_table["gene_length"].astype("int64")

    expression = counts.melt(
        id_vars=["EntrezGeneID", "Length"],
        value_vars=library_columns,
        var_name="library_name",
        value_name="expression_value",
    )

    expression = expression.rename(
        columns={
            "EntrezGeneID": "gene_id",
        }
    )

    expression["sample_id"] = expression["library_name"].map(
        sample_id_from_library
    )

    expression = expression[
        [
            "gene_id",
            "sample_id",
            "library_name",
            "expression_value",
        ]
    ]

    expression["gene_id"] = expression["gene_id"].astype("int64")
    expression["expression_value"] = expression[
        "expression_value"
    ].astype("int64")

    sample_table = metadata[
        ["FileName", "SampleName", "CellType", "Status"]
    ].copy()

    sample_table = sample_table.rename(
        columns={
            "FileName": "file_name",
            "SampleName": "sample_id",
            "CellType": "cell_type",
            "Status": "status",
        }
    )

    sample_table["sample_id"] = (
        sample_table["sample_id"]
        .astype(str)
        .str.strip()
    )

    sample_table["cell_type"] = (
        sample_table["cell_type"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    sample_table["status"] = (
        sample_table["status"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    sample_table["group_name"] = (
        sample_table["cell_type"]
        + "."
        + sample_table["status"]
    )

    for path in [
        args.expression_out,
        args.samples_out,
        args.genes_out,
        args.manifest_out,
        args.summary_out,
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)

    expression.to_parquet(
        args.expression_out,
        index=False,
        compression="zstd",
    )

    sample_table.to_parquet(
        args.samples_out,
        index=False,
        compression="zstd",
    )

    gene_table.to_parquet(
        args.genes_out,
        index=False,
        compression="zstd",
    )

    shutil.copyfile(
        args.manifest,
        args.manifest_out,
    )

    manifest = json.loads(
        args.manifest.read_text(encoding="utf-8")
    )

    summary = {
        "run_id": manifest["run_id"],
        "transformed_at": utc_now(),
        "status": "PASS",
        "gene_rows": int(len(gene_table)),
        "sample_rows": int(len(sample_table)),
        "expression_rows": int(len(expression)),
    }

    write_json(args.summary_out, summary)

    logger.info(
        "Transformation complete expression_rows=%d",
        len(expression),
    )


if __name__ == "__main__":
    main()
