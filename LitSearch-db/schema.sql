-- Enable extensions (must run as superuser)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS cube;

-- Paper metadata
CREATE TABLE papers (
    doi            TEXT PRIMARY KEY,
    title          TEXT,
    authors        TEXT[],     -- array of "Given Family"
    year           INT,
    cited_count    INT,
    references_count INT,      -- Fixed: was references_cnt
    cluster        INT,
    sub_cluster    INT,
    x              REAL,
    y              REAL,
    fncr           REAL        -- Added: FNCR field used by the API
);

-- Directed edges (renamed from citations to match API expectations)
CREATE TABLE edges (
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    PRIMARY KEY (src, dst)
);

-- Cluster metadata
CREATE TABLE clusters (
    id INT PRIMARY KEY,
    title TEXT,
    size INT,
    x REAL,
    y REAL
);

-- Search & spatial indexes
CREATE INDEX papers_title_fts  ON papers USING gin (to_tsvector('english', title));
CREATE INDEX papers_title_trgm ON papers USING gin (title gin_trgm_ops);
CREATE INDEX papers_doi_trgm   ON papers USING gin (doi gin_trgm_ops);
CREATE INDEX papers_xy_idx     ON papers USING gist (cube(array[x,y]));
CREATE INDEX edges_src_idx     ON edges (src);
CREATE INDEX edges_dst_idx     ON edges (dst);
