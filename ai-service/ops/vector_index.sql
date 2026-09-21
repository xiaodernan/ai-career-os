-- Enable fast vector search once real vectors exist (V1 deliberately leaves the
-- embedding columns untyped/unnindexed). Run AFTER the first ingestion, with the
-- SAME dimension as EMBEDDING_DIM (default deployment: text-embedding-3-small=1536).
-- psql -v dim=1536 -f vector_index.sql   (CONCURRENTLY requires autocommit: use -c
-- per statement or this file via plain psql, never inside a transaction/Flyway).

ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(:dim);
ALTER TABLE jobs            ALTER COLUMN embedding TYPE vector(:dim);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chunks_hnsw
  ON document_chunks USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_hnsw
  ON jobs USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- Trigram support for fuzzy/experience search (store.trigram_search):
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chunks_text_trgm
  ON document_chunks USING gin (text gin_trgm_ops);

-- IMPORTANT: if you later switch embedding providers/dimensions, drop the
-- column type change and rebuild:
--   DELETE FROM document_chunks;  -- or re-embed
--   ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(NEW_DIM);
--   REINDEX CONCURRENTLY idx_chunks_hnsw;
