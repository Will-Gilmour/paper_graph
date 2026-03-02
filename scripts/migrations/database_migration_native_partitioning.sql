-- Migration: Convert to PostgreSQL Native Partitioning (Fresh Start)
-- Drops all existing data and creates clean partitioned structure

BEGIN;

-- Step 1: Drop existing tables and pipeline_runs except run_id=1
DELETE FROM pipeline_runs WHERE id != 1;
DROP TABLE IF EXISTS papers CASCADE;
DROP TABLE IF EXISTS edges CASCADE;
DROP TABLE IF EXISTS clusters CASCADE;

-- Step 2: Create partitioned parent tables
CREATE TABLE papers (
    run_id INT NOT NULL,
    doi TEXT NOT NULL,
    title TEXT,
    authors TEXT[],
    year INT,
    cited_count INT,
    references_count INT,
    cluster INT,
    sub_cluster INT,
    x REAL,
    y REAL,
    fncr REAL,
    PRIMARY KEY (run_id, doi)
) PARTITION BY LIST (run_id);

CREATE TABLE edges (
    run_id INT NOT NULL,
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    PRIMARY KEY (run_id, src, dst)
) PARTITION BY LIST (run_id);

CREATE TABLE clusters (
    run_id INT NOT NULL,
    id INT NOT NULL,
    title TEXT,
    size INT,
    x REAL,
    y REAL,
    PRIMARY KEY (run_id, id)
) PARTITION BY LIST (run_id);

-- New table for sub-cluster labels
CREATE TABLE sub_clusters (
    run_id INT NOT NULL,
    cluster_id INT NOT NULL,
    sub_cluster_id INT NOT NULL,
    title TEXT,
    PRIMARY KEY (run_id, cluster_id, sub_cluster_id)
) PARTITION BY LIST (run_id);

-- Step 3: Create partition for run_id=1 (will be loaded from PKL)
CREATE TABLE papers_run_1 PARTITION OF papers FOR VALUES IN (1);
CREATE TABLE edges_run_1 PARTITION OF edges FOR VALUES IN (1);
CREATE TABLE clusters_run_1 PARTITION OF clusters FOR VALUES IN (1);
CREATE TABLE sub_clusters_run_1 PARTITION OF sub_clusters FOR VALUES IN (1);

-- Step 4: Create indexes for common queries
CREATE INDEX idx_papers_cluster ON papers(run_id, cluster);
CREATE INDEX idx_papers_year ON papers(run_id, year);
CREATE INDEX idx_edges_src ON edges(run_id, src);
CREATE INDEX idx_edges_dst ON edges(run_id, dst);

-- Step 5: Reset pipeline_runs metadata for run_id=1 (will be updated after PKL load)
UPDATE pipeline_runs 
SET nodes_count = 0, edges_count = 0, clusters_count = 0
WHERE id = 1;

COMMIT;

-- Verification
SELECT 
    'Migration complete - ready for PKL load' AS status,
    (SELECT COUNT(*) FROM pg_tables WHERE tablename LIKE '%_run_1') AS partitions_created;
