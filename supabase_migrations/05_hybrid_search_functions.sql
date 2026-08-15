-- ═══════════════════════════════════════════════════════════════════════════════
-- CampusMind Migration 05: Hybrid RRF Search & Vector Search Stored Procedures
-- ═══════════════════════════════════════════════════════════════════════════════

-- 1. Legacy Vector Match Procedure
CREATE OR REPLACE FUNCTION match_documents (
    query_embedding VECTOR(1536),
    match_count INT DEFAULT NULL,
    filter JSONB DEFAULT '{}'
)
RETURNS TABLE (
    id BIGINT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
#variable_conflict use_column
BEGIN
    RETURN QUERY
    SELECT
        id,
        content,
        metadata,
        1 - (documents.embedding <=> query_embedding) AS similarity
    FROM public.documents
    WHERE metadata @> filter
    ORDER BY documents.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 2. Hybrid RRF Search Procedure (Reciprocal Rank Fusion)
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding VECTOR(1536),
    match_count INT,
    filter JSONB DEFAULT '{}',
    full_text_weight FLOAT DEFAULT 1.0,
    semantic_weight FLOAT DEFAULT 1.0,
    rrf_k INT DEFAULT 50
)
RETURNS TABLE (
    id BIGINT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE sql
AS $$
WITH full_text AS (
    SELECT
        d.id,
        row_number() OVER (ORDER BY ts_rank_cd(d.fts, websearch_to_tsquery('english', query_text)) DESC) AS rank_ix
    FROM
        public.documents d
    WHERE
        d.fts @@ websearch_to_tsquery('english', query_text)
        AND d.metadata @> filter
),
semantic AS (
    SELECT
        d.id,
        row_number() OVER (ORDER BY d.embedding <=> query_embedding) AS rank_ix
    FROM
        public.documents d
    WHERE
        d.metadata @> filter
)
SELECT
    documents.id,
    documents.content,
    documents.metadata,
    (COALESCE(1.0 / (rrf_k + full_text.rank_ix), 0.0) * full_text_weight +
     COALESCE(1.0 / (rrf_k + semantic.rank_ix), 0.0) * semantic_weight) AS similarity
FROM
    full_text
    FULL OUTER JOIN semantic
        ON full_text.id = semantic.id
    JOIN public.documents
        ON COALESCE(full_text.id, semantic.id) = documents.id
ORDER BY similarity DESC
LIMIT match_count;
$$;
