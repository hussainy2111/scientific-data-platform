nextflow.enable.dsl = 2

process INGEST {

    tag 'GSE60450'

    publishDir "${params.outdir}/raw",
        mode: 'copy',
        overwrite: true

    errorStrategy 'retry'
    maxRetries 2

    input:
    val counts_url
    val samples_url
    val counts_md5
    val samples_md5

    output:
    tuple \
        path('counts.txt'),
        path('samples.txt'),
        path('manifest.json'),
        emit: source

    script:
    """
    python -m scientific_pipeline.ingest \
        --counts-url '${counts_url}' \
        --samples-url '${samples_url}' \
        --counts-md5 '${counts_md5}' \
        --samples-md5 '${samples_md5}' \
        --counts-out counts.txt \
        --samples-out samples.txt \
        --manifest-out manifest.json
    """
}


process VALIDATE {

    tag 'raw data'

    publishDir "${params.outdir}/validation",
        mode: 'copy',
        overwrite: true

    input:
    tuple \
        path(counts),
        path(samples),
        path(manifest)

    path config_file

    output:
    path 'validation.json',
        emit: validation

    script:
    """
    python -m scientific_pipeline.validate \
        --counts '${counts}' \
        --samples '${samples}' \
        --config '${config_file}' \
        --out validation.json
    """
}


process TRANSFORM {

    tag 'curated parquet'

    publishDir "${params.outdir}/curated",
        mode: 'copy',
        overwrite: true

    input:
    tuple \
        path(counts),
        path(samples),
        path(manifest)

    path validation

    output:
    path 'expression.parquet',
        emit: expression

    path 'samples.parquet',
        emit: samples

    path 'genes.parquet',
        emit: genes

    path 'run_manifest.json',
        emit: manifest

    path 'transform_summary.json',
        emit: summary

    script:
    """
    python -m scientific_pipeline.transform \
        --counts '${counts}' \
        --samples '${samples}' \
        --manifest '${manifest}' \
        --expression-out expression.parquet \
        --samples-out samples.parquet \
        --genes-out genes.parquet \
        --manifest-out run_manifest.json \
        --summary-out transform_summary.json
    """
}


process LOAD {

    tag 'DuckDB'

    publishDir "${params.outdir}/warehouse",
        mode: 'copy',
        overwrite: true

    input:
    path expression
    path samples
    path genes
    path manifest

    output:
    path 'warehouse.duckdb',
        emit: warehouse

    path 'load_report.json',
        emit: report

    script:
    """
    python -m scientific_pipeline.load \
        --expression '${expression}' \
        --samples '${samples}' \
        --genes '${genes}' \
        --manifest '${manifest}' \
        --out warehouse.duckdb \
        --report load_report.json
    """
}


process QUALITY {

    tag 'warehouse checks'

    publishDir "${params.outdir}/quality",
        mode: 'copy',
        overwrite: true

    input:
    path warehouse
    path sql_file

    output:
    path 'quality.json',
        emit: quality

    script:
    """
    python -m scientific_pipeline.quality \
        --database '${warehouse}' \
        --sql '${sql_file}' \
        --out quality.json
    """
}


process REPORT {

    tag 'run report'

    publishDir "${params.outdir}/report",
        mode: 'copy',
        overwrite: true

    input:
    path warehouse
    path quality

    output:
    path 'report.md',
        emit: report

    script:
    """
    python -m scientific_pipeline.report \
        --database '${warehouse}' \
        --quality '${quality}' \
        --out report.md
    """
}


workflow {

    config_file = file(
        "${projectDir}/config/pipeline.yml"
    )

    sql_file = file(
        "${projectDir}/sql/quality_checks.sql"
    )

    INGEST(
        params.counts_url,
        params.samples_url,
        params.counts_md5,
        params.samples_md5
    )

    VALIDATE(
        INGEST.out.source,
        config_file
    )

    TRANSFORM(
        INGEST.out.source,
        VALIDATE.out.validation
    )

    LOAD(
        TRANSFORM.out.expression,
        TRANSFORM.out.samples,
        TRANSFORM.out.genes,
        TRANSFORM.out.manifest
    )

    QUALITY(
        LOAD.out.warehouse,
        sql_file
    )

    REPORT(
        LOAD.out.warehouse,
        QUALITY.out.quality
    )
}
