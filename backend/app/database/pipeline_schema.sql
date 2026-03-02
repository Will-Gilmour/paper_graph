-- Pipeline build tracking schema
-- Tracks every pipeline run for accountability and reproducibility

-- Pipeline runs table
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id SERIAL PRIMARY KEY,
    
    -- Identity
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Configuration (stored as JSON for full reproducibility)
    config JSONB NOT NULL,
    
    -- Seeds used
    seed_dois TEXT[] NOT NULL,
    
    -- Execution
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    -- Status: pending, running, completed, failed, cancelled
    
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Results
    output_path VARCHAR(500),
    error_message TEXT,
    
    -- Statistics
    nodes_count INT,
    edges_count INT,
    clusters_count INT,
    
    -- Active graph management
    is_active BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    
    -- Indexes
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'))
);

-- Index for finding active graph
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_active ON pipeline_runs(is_active) WHERE is_active = TRUE;

-- Index for status queries
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status, created_at DESC);

-- Only one active graph at a time
CREATE UNIQUE INDEX IF NOT EXISTS idx_pipeline_runs_only_one_active 
ON pipeline_runs(is_active) WHERE is_active = TRUE;

-- Comments
COMMENT ON TABLE pipeline_runs IS 'Tracks all data pipeline executions for accountability';
COMMENT ON COLUMN pipeline_runs.config IS 'Complete pipeline configuration as JSON for reproducibility';
COMMENT ON COLUMN pipeline_runs.is_active IS 'Only one graph can be active at a time (serves frontend)';

