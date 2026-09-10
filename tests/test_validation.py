from pathlib import Path

from scientific_pipeline.validate import validate_counts


def test_small_valid_dataset(tmp_path: Path) -> None:
    counts = tmp_path / "counts.txt"
    samples = tmp_path / "samples.txt"
    config = tmp_path / "config.yml"

    counts.write_text(
        "EntrezGeneID\tLength\tMCL1-DG_run\tMCL1-DH_run\n"
        "101\t1000\t4\t7\n"
        "102\t800\t2\t3\n",
        encoding="utf-8",
    )

    samples.write_text(
        "FileName\tSampleName\tCellType\tStatus\n"
        "MCL1.DG_run\tMCL1.DG\tbasal\tvirgin\n"
        "MCL1.DH_run\tMCL1.DH\tbasal\tvirgin\n",
        encoding="utf-8",
    )

    config.write_text(
        "quality:\n"
        "  max_metadata_null_fraction: 0.0\n",
        encoding="utf-8",
    )

    result = validate_counts(
        counts,
        samples,
        config,
    )

    assert result["status"] == "PASS"
    assert result["gene_count"] == 2
    assert result["sample_count"] == 2
    assert result["expression_value_count"] == 4
