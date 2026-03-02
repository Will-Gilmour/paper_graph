-- Function to create partitions for a new run_id
CREATE OR REPLACE FUNCTION create_partitions_for_run(p_run_id INT)
RETURNS VOID AS $$
BEGIN
    -- Create papers partition
    EXECUTE format('CREATE TABLE IF NOT EXISTS papers_run_%s PARTITION OF papers FOR VALUES IN (%s)', p_run_id, p_run_id);
    
    -- Create edges partition
    EXECUTE format('CREATE TABLE IF NOT EXISTS edges_run_%s PARTITION OF edges FOR VALUES IN (%s)', p_run_id, p_run_id);
    
    -- Create clusters partition
    EXECUTE format('CREATE TABLE IF NOT EXISTS clusters_run_%s PARTITION OF clusters FOR VALUES IN (%s)', p_run_id, p_run_id);
    
    -- Create sub_clusters partition
    EXECUTE format('CREATE TABLE IF NOT EXISTS sub_clusters_run_%s PARTITION OF sub_clusters FOR VALUES IN (%s)', p_run_id, p_run_id);
    
    RAISE NOTICE 'Created partitions for run_id=%', p_run_id;
END;
$$ LANGUAGE plpgsql;

-- Create partition for run_id=29
SELECT create_partitions_for_run(29);


