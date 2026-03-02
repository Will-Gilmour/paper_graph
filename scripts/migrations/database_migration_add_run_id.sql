-- Migration: Add run_id to partition graph data
-- This allows multiple graphs to coexist in the database

BEGIN;

-- 1. Add run_id columns to all tables
ALTER TABLE papers ADD COLUMN run_id INT;
ALTER TABLE edges ADD COLUMN run_id INT;
ALTER TABLE clusters ADD COLUMN run_id INT;

-- 2. Set default run_id for existing data (the active MRgFUS graph)
-- Get the active run_id
DO $$
DECLARE
    active_run_id INT;
BEGIN
    SELECT id INTO active_run_id FROM pipeline_runs WHERE is_active = TRUE LIMIT 1;
    
    IF active_run_id IS NOT NULL THEN
        UPDATE papers SET run_id = active_run_id WHERE run_id IS NULL;
        UPDATE edges SET run_id = active_run_id WHERE run_id IS NULL;
        UPDATE clusters SET run_id = active_run_id WHERE run_id IS NULL;
    END IF;
END $$;

-- 3. Make run_id NOT NULL
ALTER TABLE papers ALTER COLUMN run_id SET NOT NULL;
ALTER TABLE edges ALTER COLUMN run_id SET NOT NULL;
ALTER TABLE clusters ALTER COLUMN run_id SET NOT NULL;

-- 4. Drop old primary keys
ALTER TABLE papers DROP CONSTRAINT IF EXISTS papers_pkey;
ALTER TABLE edges DROP CONSTRAINT IF EXISTS edges_pkey;
ALTER TABLE clusters DROP CONSTRAINT IF EXISTS clusters_pkey;

-- 5. Create new composite primary keys
ALTER TABLE papers ADD PRIMARY KEY (run_id, doi);
ALTER TABLE edges ADD PRIMARY KEY (run_id, src, dst);
ALTER TABLE clusters ADD PRIMARY KEY (run_id, id);

-- 6. Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_papers_run_id ON papers(run_id);
CREATE INDEX IF NOT EXISTS idx_edges_run_id ON edges(run_id);
CREATE INDEX IF NOT EXISTS idx_clusters_run_id ON clusters(run_id);

-- 7. Create index on cluster + run_id for common queries
CREATE INDEX IF NOT EXISTS idx_papers_run_cluster ON papers(run_id, cluster);

COMMIT;

-- Verify migration
SELECT 
    'papers' AS table_name, 
    COUNT(*) AS total_rows,
    COUNT(DISTINCT run_id) AS distinct_graphs
FROM papers
UNION ALL
SELECT 
    'edges' AS table_name, 
    COUNT(*) AS total_rows,
    COUNT(DISTINCT run_id) AS distinct_graphs
FROM edges
UNION ALL
SELECT 
    'clusters' AS table_name, 
    COUNT(*) AS total_rows,
    COUNT(DISTINCT run_id) AS distinct_graphs
FROM clusters;

