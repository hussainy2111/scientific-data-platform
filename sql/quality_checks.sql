WITH checks AS (

    SELECT
        'gene_id_not_null' AS check_name,
        COUNT(*) AS records_checked,
        COUNT(*) FILTER (
            WHERE gene_id IS NULL
        ) AS records_failed
    FROM dim_gene

    UNION ALL

    SELECT
        'gene_length_positive',
        COUNT(*),
        COUNT(*) FILTER (
            WHERE gene_length <= 0
        )
    FROM dim_gene

    UNION ALL

    SELECT
        'sample_metadata_complete',
        COUNT(*),
        COUNT(*) FILTER (
            WHERE sample_id IS NULL
               OR file_name IS NULL
               OR cell_type IS NULL
               OR status IS NULL
               OR group_name IS NULL
        )
    FROM dim_sample

    UNION ALL

    SELECT
        'expression_non_negative',
        COUNT(*),
        COUNT(*) FILTER (
            WHERE expression_value < 0
        )
    FROM fact_expression

    UNION ALL

    SELECT
        'expression_key_unique',
        COUNT(*),
        COUNT(*) - COUNT(
            DISTINCT
            run_id || '|' ||
            CAST(gene_id AS VARCHAR) || '|' ||
            sample_id
        )
    FROM fact_expression

    UNION ALL

    SELECT
        'gene_relationship_valid',
        COUNT(*),
        COUNT(*) FILTER (
            WHERE g.gene_id IS NULL
        )
    FROM fact_expression AS f
    LEFT JOIN dim_gene AS g
        ON f.gene_id = g.gene_id

    UNION ALL

    SELECT
        'sample_relationship_valid',
        COUNT(*),
        COUNT(*) FILTER (
            WHERE s.sample_id IS NULL
        )
    FROM fact_expression AS f
    LEFT JOIN dim_sample AS s
        ON f.sample_id = s.sample_id

    UNION ALL

    SELECT
        'expression_matrix_complete',
        1,
        CASE
            WHEN
                (
                    SELECT COUNT(*)
                    FROM fact_expression
                )
                =
                (
                    SELECT COUNT(*)
                    FROM dim_gene
                )
                *
                (
                    SELECT COUNT(*)
                    FROM dim_sample
                )
            THEN 0
            ELSE 1
        END
)

SELECT
    check_name,
    records_checked,
    records_failed,
    CASE
        WHEN records_failed = 0 THEN 'PASS'
        ELSE 'FAIL'
    END AS status
FROM checks
ORDER BY check_name;
