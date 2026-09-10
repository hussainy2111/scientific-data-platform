from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

from .common import get_logger


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--quality", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)

    args = parser.parse_args()

    logger = get_logger()

    quality = json.loads(
        args.quality.read_text(encoding="utf-8")
    )

    connection = duckdb.connect(
        str(args.database),
        read_only=True,
    )

    try:
        run = connection.execute(
            """
            SELECT
                run_id,
                dataset,
                pipeline_version,
                counts_sha256,
                samples_sha256,
                loaded_at
            FROM pipeline_run
            LIMIT 1
            """
        ).fetchone()

        gene_count = connection.execute(
            "SELECT COUNT(*) FROM dim_gene"
        ).fetchone()[0]

        sample_count = connection.execute(
            "SELECT COUNT(*) FROM dim_sample"
        ).fetchone()[0]

        expression_count = connection.execute(
            "SELECT COUNT(*) FROM fact_expression"
        ).fetchone()[0]

        groups = connection.execute(
            """
            SELECT
                group_name,
                COUNT(*) AS sample_count
            FROM dim_sample
            GROUP BY group_name
            ORDER BY group_name
            """
        ).fetchall()

    finally:
        connection.close()

    (
        run_id,
        dataset,
        pipeline_version,
        counts_sha256,
        samples_sha256,
        loaded_at,
    ) = run

    lines = [
        "# Pipeline run report",
        "",
        "## Run",
        "",
        f"- Run ID: `{run_id}`",
        f"- Dataset: `{dataset}`",
        f"- Pipeline version: `{pipeline_version}`",
        f"- Loaded at: `{loaded_at}`",
        f"- Count matrix SHA-256: `{counts_sha256}`",
        f"- Metadata SHA-256: `{samples_sha256}`",
        "",
        "## Warehouse",
        "",
        f"- Genes: **{gene_count:,}**",
        f"- Samples: **{sample_count:,}**",
        f"- Expression rows: **{expression_count:,}**",
        "",
        "## Sample groups",
        "",
        "| Group | Samples |",
        "| --- | ---: |",
    ]

    for group_name, count in groups:
        lines.append(
            f"| {group_name} | {count} |"
        )

    lines.extend(
        [
            "",
            "## Data quality",
            "",
            f"- Checks run: **{quality['check_count']}**",
            f"- Failed checks: **{quality['failed_count']}**",
            f"- Status: **{quality['status']}**",
            "",
        ]
    )

    args.out.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    logger.info(
        "Run report written path=%s",
        args.out,
    )


if __name__ == "__main__":
    main()
