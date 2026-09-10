from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

from .common import get_logger, utc_now, write_json

SCHEMA = """
CREATE TABLE pipeline_run (
    run_id VARCHAR PRIMARY KEY,
    dataset VARCHAR NOT NULL,
    pipeline_version VARCHAR NOT NULL,
    counts_sha256 VARCHAR NOT NULL,
    samples_sha256 VARCHAR NOT NULL,
    loaded_at TIMESTAMP NOT NULL
);

CREATE TABLE dim_gene (
    gene_id BIGINT PRIMARY KEY,
    gene_length BIGINT NOT NULL
);

CREATE TABLE dim_sample (
    sample_id VARCHAR PRIMARY KEY,
    file_name VARCHAR NOT NULL,
    cell_type VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    group_name VARCHAR NOT NULL
);

CREATE TABLE fact_expression (
    run_id VARCHAR NOT NULL,
    gene_id BIGINT NOT NULL,
    sample_id VARCHAR NOT NULL,
    library_name VARCHAR NOT NULL,
    expression_value BIGINT NOT NULL,

    PRIMARY KEY (
        run_id,
        gene_id,
        sample_id
    ),

    FOREIGN KEY (run_id)
        REFERENCES pipeline_run(run_id),

    FOREIGN KEY (gene_id)
        REFERENCES dim_gene(gene_id),

    FOREIGN KEY (sample_id)
        REFERENCES dim_sample(sample_id)
);
"""


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--expression", type=Path, required=True)
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--genes", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)

    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)

    args = parser.parse_args()

    logger = get_logger()

    manifest = json.loads(
        args.manifest.read_text(encoding="utf-8")
    )

    run_id = manifest["run_id"]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    if args.out.exists():
        args.out.unlink()

    connection = duckdb.connect(str(args.out))

    try:
        connection.execute("BEGIN TRANSACTION")
        connection.execute(SCHEMA)

        connection.execute(
            """
            INSERT INTO pipeline_run
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                manifest["dataset"],
                manifest["pipeline_version"],
                manifest["sources"]["counts"]["sha256"],
                manifest["sources"]["samples"]["sha256"],
                utc_now(),
            ],
        )

        connection.execute(
            """
            INSERT INTO dim_gene
            SELECT
                gene_id,
                gene_length
            FROM read_parquet(?)
            """,
            [str(args.genes)],
        )

        connection.execute(
            """
            INSERT INTO dim_sample
            SELECT
                sample_id,
                file_name,
                cell_type,
                status,
                group_name
            FROM read_parquet(?)
            """,
            [str(args.samples)],
        )

        connection.execute(
            """
            INSERT INTO fact_expression
            SELECT
                ? AS run_id,
                gene_id,
                sample_id,
                library_name,
                expression_value
            FROM read_parquet(?)
            """,
            [
                run_id,
                str(args.expression),
            ],
        )

        connection.execute("COMMIT")

        gene_count = connection.execute(
            "SELECT COUNT(*) FROM dim_gene"
        ).fetchone()[0]

        sample_count = connection.execute(
            "SELECT COUNT(*) FROM dim_sample"
        ).fetchone()[0]

        expression_count = connection.execute(
            "SELECT COUNT(*) FROM fact_expression"
        ).fetchone()[0]

    except Exception:
        connection.execute("ROLLBACK")
        raise

    finally:
        connection.close()

    report = {
        "run_id": run_id,
        "loaded_at": utc_now(),
        "status": "PASS",
        "tables": {
            "dim_gene": int(gene_count),
            "dim_sample": int(sample_count),
            "fact_expression": int(expression_count),
        },
    }

    write_json(args.report, report)

    logger.info(
        "Warehouse loaded genes=%d samples=%d expression_rows=%d",
        gene_count,
        sample_count,
        expression_count,
    )


if __name__ == "__main__":
    main()
