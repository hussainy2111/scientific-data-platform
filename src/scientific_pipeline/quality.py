from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from .common import get_logger, utc_now, write_json


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--sql", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)

    args = parser.parse_args()

    logger = get_logger()

    connection = duckdb.connect(
        str(args.database),
        read_only=True,
    )

    try:
        result = connection.execute(
            args.sql.read_text(encoding="utf-8")
        )

        columns = [
            column[0]
            for column in result.description
        ]

        rows = result.fetchall()

    finally:
        connection.close()

    checks = [
        dict(zip(columns, row, strict=True))
        for row in rows
    ]

    failed = [
        check
        for check in checks
        if check["status"] != "PASS"
    ]

    output = {
        "checked_at": utc_now(),
        "check_count": len(checks),
        "failed_count": len(failed),
        "status": "FAIL" if failed else "PASS",
        "checks": checks,
    }

    write_json(args.out, output)

    if failed:
        logger.error(
            "Quality checks failed count=%d",
            len(failed),
        )
        raise SystemExit(1)

    logger.info(
        "Quality checks passed count=%d",
        len(checks),
    )


if __name__ == "__main__":
    main()
