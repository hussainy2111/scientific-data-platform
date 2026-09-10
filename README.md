# scientific-data-platform
# Scientific Data Ingestion & Warehouse Pipeline

A reproducible scientific data engineering pipeline built around a real public RNA-seq dataset.

The project retrieves a published gene-count matrix and sample metadata, verifies source integrity, validates the scientific data, transforms it into typed Parquet datasets, loads a SQL analytical warehouse, runs data-quality checks, and generates a run report.

The workflow is orchestrated with Nextflow and includes retry handling, provenance tracking, automated tests, containerization, and continuous integration.

## Pipeline

```text
Public RNA-seq data
        |
        v
     INGEST
        |
        |-- download and retry handling
        |-- gzip decompression
        |-- checksum verification
        |-- provenance capture
        |
        v
    VALIDATE
        |
        |-- schema checks
        |-- sample matching
        |-- metadata checks
        |-- expression checks
        |
        v
   TRANSFORM
        |
        |-- genes.parquet
        |-- samples.parquet
        |-- expression.parquet
        |
        v
      LOAD
        |
        v
     DuckDB
        |
        |-- pipeline_run
        |-- dim_gene
        |-- dim_sample
        |-- fact_expression
        |
        v
    QUALITY
        |
        |-- SQL quality gates
        |-- relationship checks
        |-- completeness checks
        |
        v
     REPORT
```

## Technology

The project uses Python and SQL for data processing and modeling, Nextflow DSL2 for workflow orchestration, DuckDB for the analytical warehouse, and Apache Parquet for the curated data layer. Testing and code-quality checks use pytest and Ruff, while Docker provides a reproducible application environment and GitHub Actions runs automated CI checks.

## Dataset

The pipeline uses **GSE60450**, a public mouse mammary gland RNA-seq dataset containing 12 samples from basal and luminal cell populations across virgin, pregnant, and lactating biological states.

| Cell type | Status   | Samples |
| --------- | -------- | ------: |
| Basal     | Virgin   |       2 |
| Basal     | Pregnant |       2 |
| Basal     | Lactate  |       2 |
| Luminal   | Virgin   |       2 |
| Luminal   | Pregnant |       2 |
| Luminal   | Lactate  |       2 |

The processed gene-count matrix is retrieved from NCBI GEO. Starting from the published count matrix keeps the project focused on scientific data engineering rather than sequence alignment, allowing the workflow to concentrate on ingestion, provenance, validation, transformation, storage, data modeling, and quality control.

A complete run processes **27,179 genes, 12 samples, and 326,148 gene-sample expression observations**. Raw scientific data and generated pipeline outputs are excluded from version control.

## Ingestion and provenance

The pipeline begins by downloading the compressed count matrix and corrected sample metadata. HTTP retry handling is used for transient server errors, and downloads are written through temporary files to reduce the risk of treating an incomplete download as valid input.

The count matrix is decompressed before its expected MD5 checksum is verified. SHA-256 fingerprints are also calculated for provenance.

Each ingestion run generates a manifest containing the dataset identifier, source URLs, retrieval timestamp, pipeline version, file sizes, checksums, and a unique run ID. This information is carried into the curated layer and warehouse, providing a traceable relationship between the source files and processed analytical data.

## Validation

Scientific data is validated before transformation. The validation stage checks required count-matrix and metadata columns, missing or duplicate gene identifiers, invalid gene lengths, missing expression values, negative counts, non-integer counts, duplicate sample identifiers, metadata completeness, and agreement between sequencing-library identifiers and sample metadata.

The sample identifiers embedded in the count-matrix library names are normalized and matched against the sample metadata before downstream processing.

Validation failures stop the workflow rather than allowing invalid data to continue into the curated layer.

## Curated data

The original expression matrix is distributed in wide TSV format. The pipeline preserves this as the raw representation and creates a curated analytical layer using Parquet.

Three datasets are produced:

```text
genes.parquet
samples.parquet
expression.parquet
```

`genes.parquet` stores gene identifiers and gene lengths. `samples.parquet` stores normalized sample metadata and biological group information. `expression.parquet` converts the wide expression matrix into long relational form:

```text
gene_id
sample_id
library_name
expression_value
```

Parquet provides typed, columnar storage suited to analytical processing while maintaining a clear separation between raw and curated data.

## Analytical warehouse

The curated datasets are loaded into a persistent DuckDB database. DuckDB provides a relational SQL analytical layer without requiring a separate database server, which keeps the project lightweight and reproducible for the size of this dataset.

The warehouse contains four tables:

```text
pipeline_run
dim_gene
dim_sample
fact_expression
```

`pipeline_run` stores run-level provenance. `dim_gene` contains gene metadata, while `dim_sample` contains sample and biological-group metadata. `fact_expression` contains gene-by-sample expression measurements and references the corresponding run, gene, and sample records.

This structure separates scientific measurements from descriptive metadata and pipeline provenance while supporting direct SQL analysis.

## Data quality

After the warehouse is loaded, SQL quality gates check gene identifier completeness, positive gene lengths, sample metadata completeness, non-negative expression values, expression-key uniqueness, gene relationships, sample relationships, and expression-matrix completeness.

A failed check causes the quality stage to return a non-zero exit code rather than silently producing a successful run.

The failure path was tested by creating a disposable copy of the warehouse and deliberately introducing a negative expression value. The quality layer detected the invalid value through the `expression_non_negative` check and returned a failure.

This verifies that the quality layer handles both valid and invalid data rather than testing only the successful path.

## Workflow orchestration

Nextflow DSL2 controls the dependencies between ingestion, validation, transformation, warehouse loading, quality checks, and reporting.

```text
INGEST
   |
VALIDATE
   |
TRANSFORM
   |
 LOAD
   |
QUALITY
   |
REPORT
```

The individual data operations remain in Python modules, while Nextflow manages workflow execution. This keeps transformation logic separate from orchestration and allows individual components to be tested independently.

The workflow also uses retry handling and Nextflow caching. Completed stages can be reused when their inputs and process definitions have not changed:

```bash
make resume
```

This allows interrupted or repeated executions to avoid unnecessary recomputation.

## Reporting

A successful run generates a Markdown report containing the run ID, dataset identifier, pipeline version, source fingerprints, gene count, sample count, expression-row count, biological sample groups, and data-quality result.

Nextflow also generates execution metadata including a trace, timeline, DAG, and execution report.

## Repository structure

```text
scientific-data-platform/
├── .github/
│   └── workflows/
│       └── ci.yml
├── config/
│   └── pipeline.yml
├── scripts/
│   └── bootstrap.sh
├── sql/
│   └── quality_checks.sql
├── src/
│   └── scientific_pipeline/
│       ├── __init__.py
│       ├── common.py
│       ├── ingest.py
│       ├── validate.py
│       ├── transform.py
│       ├── load.py
│       ├── quality.py
│       └── report.py
├── tests/
│   ├── test_common.py
│   └── test_validation.py
├── Dockerfile
├── Makefile
├── main.nf
├── nextflow.config
├── pyproject.toml
├── requirements.txt
└── requirements.lock.txt
```

## Setup

The project requires Python 3.10 or newer, Java 17 or newer, and Nextflow. Docker is required only for building or running the container image.

Create and activate a Python environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the dependencies and project:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

If Nextflow is not installed:

```bash
mkdir -p "$HOME/.local/bin"

curl -fsSL https://get.nextflow.io | bash

chmod +x nextflow
mv nextflow "$HOME/.local/bin/nextflow"

export PATH="$HOME/.local/bin:$PATH"
```

Confirm the installation:

```bash
nextflow -version
```

## Running the pipeline

Run the tests first:

```bash
pytest
```

Run the lint checks:

```bash
ruff check src tests
```

Execute the complete workflow:

```bash
make pipeline
```

The workflow runs:

```text
INGEST -> VALIDATE -> TRANSFORM -> LOAD -> QUALITY -> REPORT
```

A successful run produces:

```text
results/
├── raw/
│   ├── counts.txt
│   ├── samples.txt
│   └── manifest.json
├── validation/
│   └── validation.json
├── curated/
│   ├── genes.parquet
│   ├── samples.parquet
│   ├── expression.parquet
│   ├── run_manifest.json
│   └── transform_summary.json
├── warehouse/
│   ├── warehouse.duckdb
│   └── load_report.json
├── quality/
│   └── quality.json
├── report/
│   └── report.md
├── execution_report.html
├── execution_timeline.html
├── execution_trace.txt
└── execution_dag.html
```

The `results/` directory is excluded from version control.

## Querying the warehouse

The completed DuckDB warehouse can be queried directly with SQL.

```python
import duckdb

con = duckdb.connect(
    "results/warehouse/warehouse.duckdb",
    read_only=True,
)

con.sql("""
    SELECT
        (SELECT COUNT(*) FROM dim_gene) AS genes,
        (SELECT COUNT(*) FROM dim_sample) AS samples,
        (SELECT COUNT(*) FROM fact_expression) AS expression_rows
""").show()

con.close()
```

For GSE60450, the resulting warehouse contains:

```text
genes:             27179
samples:              12
expression_rows:  326148
```

The biological groups can also be queried directly:

```sql
SELECT
    group_name,
    COUNT(*) AS sample_count
FROM dim_sample
GROUP BY group_name
ORDER BY group_name;
```

This returns the six basal and luminal biological groups, with two samples in each group.

## Docker

Build the project image with:

```bash
docker build -t scientific-data-platform:0.1.0 .
```

Run it with:

```bash
docker run --rm scientific-data-platform:0.1.0
```

## Continuous integration

GitHub Actions runs automated checks on pushes and pull requests. The workflow installs the project dependencies, runs Ruff, executes the pytest test suite, checks Python module compilation, and builds the Docker image.

The complete external-data pipeline is intentionally not executed during routine CI. Keeping external data retrieval outside CI prevents routine code checks from depending on the availability of external scientific-data services such as GEO.

## Scope

This repository is a portfolio-scale implementation of production-style scientific data engineering practices. It is not presented as an enterprise production platform.

The project demonstrates an end-to-end path from public scientific data to a validated analytical warehouse, including source verification, provenance tracking, metadata harmonization, workflow orchestration, columnar storage, SQL data modeling, data-quality gates, automated testing, containerization, and continuous integration.

Future extensions could include fixture-based end-to-end integration testing, incremental loading based on source fingerprints, additional validation scenarios, and larger scientific datasets.

