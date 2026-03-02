import React from "react";

const API = import.meta.env.VITE_API_URL;

/**
 * SearchPane - Search interface for finding papers by title, author, year, citations, and clusters
 * 
 * @param {string} searchTitle - Current title search query
 * @param {string} searchAuthor - Current author search query
 * @param {string} searchYearMin - Minimum year filter
 * @param {string} searchYearMax - Maximum year filter
 * @param {string} searchMinCitations - Minimum citations filter
 * @param {Set} searchClusters - Selected clusters for filtering
 * @param {function} setSearchTitle - Update title query
 * @param {function} setSearchAuthor - Update author query
 * @param {function} setSearchYearMin - Update min year
 * @param {function} setSearchYearMax - Update max year
 * @param {function} setSearchMinCitations - Update min citations
 * @param {function} setSearchClusters - Update selected clusters
 * @param {function} handleSearchSubmit - Submit search form
 * @param {array} searchPapers - Search results
 * @param {boolean} loadingSearch - Whether search is in progress
 * @param {string|null} hoveredDoi - Currently hovered paper DOI
 * @param {function} handleResultMouseEnter - Mouse enter handler for results
 * @param {function} handleResultMouseLeave - Mouse leave handler for results
 * @param {function} handleResultClick - Click handler for results
 * @param {array} clusterList - List of all clusters
 * @param {function} clusterLabel - Get cluster label by ID
 */
export default function SearchPane({
  searchTitle,
  searchAuthor,
  searchYearMin,
  searchYearMax,
  searchMinCitations,
  searchClusters,
  setSearchTitle,
  setSearchAuthor,
  setSearchYearMin,
  setSearchYearMax,
  setSearchMinCitations,
  setSearchClusters,
  handleSearchSubmit,
  searchPapers,
  loadingSearch,
  hoveredDoi,
  handleResultMouseEnter,
  handleResultMouseLeave,
  handleResultClick,
  clusterList,
  clusterLabel,
}) {
  return (
    <div style={{ padding: "1rem", height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Search Form */}
      <form onSubmit={handleSearchSubmit} style={{ marginBottom: "1rem", borderBottom: "2px solid #e0e0e0", paddingBottom: "1rem" }}>
        <div style={{ marginBottom: "0.75rem" }}>
          <label style={{ fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.25rem", display: "block" }}>
            Title Keywords:
          </label>
          <input
            key="search-title-input"
            type="text"
            value={searchTitle}
            onChange={(e) => setSearchTitle(e.target.value)}
            placeholder="e.g., tremor, ultrasound..."
            autoComplete="off"
            style={{
              width: "100%",
              padding: "0.5rem",
              border: "1px solid #ddd",
              borderRadius: "4px",
              fontSize: "0.9rem"
            }}
          />
        </div>

        <div style={{ marginBottom: "0.75rem" }}>
          <label style={{ fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.25rem", display: "block" }}>
            Author Name:
          </label>
          <input
            key="search-author-input"
            type="text"
            value={searchAuthor}
            onChange={(e) => setSearchAuthor(e.target.value)}
            placeholder="e.g., Smith, Johnson..."
            autoComplete="off"
            style={{
              width: "100%",
              padding: "0.5rem",
              border: "1px solid #ddd",
              borderRadius: "4px",
              fontSize: "0.9rem"
            }}
          />
        </div>

        <div style={{ marginBottom: "0.75rem" }}>
          <label style={{ fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.25rem", display: "block" }}>
            Filter by Clusters:
          </label>
          <div style={{ 
            maxHeight: "120px", 
            overflowY: "auto", 
            border: "1px solid #ddd", 
            borderRadius: "4px",
            padding: "0.5rem",
            background: "#fafafa"
          }}>
            {clusterList.filter(c => !c.parent_id).length === 0 ? (
              <small style={{ color: "#999" }}>Loading clusters...</small>
            ) : (
              clusterList.filter(c => !c.parent_id).map((cluster) => (
                <label 
                  key={cluster.id} 
                  style={{ 
                    display: "block", 
                    marginBottom: "0.25rem",
                    cursor: "pointer",
                    fontSize: "0.85rem"
                  }}
                >
                  <input
                    type="checkbox"
                    checked={searchClusters.has(cluster.id)}
                    onChange={(e) => {
                      const newClusters = new Set(searchClusters);
                      if (e.target.checked) {
                        newClusters.add(cluster.id);
                      } else {
                        newClusters.delete(cluster.id);
                      }
                      setSearchClusters(newClusters);
                    }}
                    style={{ marginRight: "0.5rem" }}
                  />
                  {clusterLabel(cluster.id)} ({(cluster.size ?? 0).toLocaleString()})
                </label>
              ))
            )}
          </div>
          <small style={{ fontSize: "0.75rem", color: "#666", display: "block", marginTop: "0.25rem" }}>
            {searchClusters.size === 0 ? "All clusters" : `${searchClusters.size} cluster(s) selected`}
          </small>
        </div>

        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: "0.75rem", color: "#666", marginBottom: "0.25rem", display: "block" }}>
              From Year
            </label>
            <input
              type="number"
              value={searchYearMin}
              onChange={(e) => setSearchYearMin(e.target.value)}
              placeholder="2000"
              min="1900"
              style={{
                width: "100%",
                padding: "0.4rem",
                border: "1px solid #ddd",
                borderRadius: "4px",
                fontSize: "0.85rem"
              }}
            />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: "0.75rem", color: "#666", marginBottom: "0.25rem", display: "block" }}>
              To Year
            </label>
            <input
              type="number"
              value={searchYearMax}
              onChange={(e) => setSearchYearMax(e.target.value)}
              placeholder="2025"
              min="1900"
              style={{
                width: "100%",
                padding: "0.4rem",
                border: "1px solid #ddd",
                borderRadius: "4px",
                fontSize: "0.85rem"
              }}
            />
          </div>
        </div>

        <div style={{ marginBottom: "0.75rem" }}>
          <label style={{ fontSize: "0.75rem", color: "#666", marginBottom: "0.25rem", display: "block" }}>
            Min Citations
          </label>
          <input
            type="number"
            value={searchMinCitations}
            onChange={(e) => setSearchMinCitations(e.target.value)}
            placeholder="0"
            min="0"
            style={{
              width: "100%",
              padding: "0.4rem",
              border: "1px solid #ddd",
              borderRadius: "4px",
              fontSize: "0.85rem"
            }}
          />
        </div>

        <button
          type="submit"
          disabled={(!searchTitle.trim() && !searchAuthor.trim()) || loadingSearch}
          style={{
            width: "100%",
            padding: "0.5rem",
            background: (searchTitle.trim() || searchAuthor.trim()) && !loadingSearch ? "#228B22" : "#ccc",
            color: "#fff",
            border: "none",
            borderRadius: "4px",
            fontSize: "0.9rem",
            fontWeight: 600,
            cursor: (searchTitle.trim() || searchAuthor.trim()) && !loadingSearch ? "pointer" : "not-allowed"
          }}
        >
          {loadingSearch ? "Searching..." : "Search Papers"}
        </button>
      </form>

      {/* Results */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {loadingSearch && (
          <div style={{ padding: "2rem", textAlign: "center" }}>
            Loading search results...
          </div>
        )}

        {!loadingSearch && searchPapers.length === 0 && (
          <div style={{ padding: "2rem", textAlign: "center", color: "#666" }}>
            <p>No results yet.</p>
            <small>Enter a search query above to find papers</small>
          </div>
        )}

        {!loadingSearch && searchPapers.length > 0 && (
          <>
            <div style={{ 
              fontSize: "0.9rem", 
              fontWeight: 600, 
              color: "#666", 
              marginBottom: "1rem",
              paddingBottom: "0.5rem",
              borderBottom: "1px solid #e0e0e0"
            }}>
              Found {searchPapers.length} paper{searchPapers.length !== 1 ? 's' : ''}
            </div>

            {searchPapers.map((paper) => (
              <div
                key={paper.doi}
                onMouseEnter={() => handleResultMouseEnter(paper.doi)}
                onMouseLeave={handleResultMouseLeave}
                onClick={() => handleResultClick(paper.doi)}
                style={{
                  background: hoveredDoi === paper.doi ? "#f0f8f0" : "#fff",
                  border: hoveredDoi === paper.doi ? "1px solid #4CAF50" : "1px solid #e0e0e0",
                  borderRadius: "6px",
                  padding: "0.75rem",
                  marginBottom: "0.75rem",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                  boxShadow: hoveredDoi === paper.doi ? "0 2px 8px rgba(76, 175, 80, 0.2)" : "none",
                }}
              >
                <div style={{ 
                  fontWeight: 600, 
                  fontSize: "0.95rem", 
                  marginBottom: "0.5rem",
                  lineHeight: 1.3,
                  color: "#222"
                }}>
                  {paper.title || paper.doi}
                </div>

                {!paper.error && (
                  <>
                    {paper.authors && paper.authors.length > 0 && (
                      <div style={{ 
                        fontSize: "0.85rem", 
                        color: "#666", 
                        marginBottom: "0.5rem",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap"
                      }}>
                        👤 {paper.authors.slice(0, 3).join(', ')}
                        {paper.authors.length > 3 && ` et al.`}
                      </div>
                    )}

                    <div style={{ 
                      display: "flex", 
                      flexWrap: "wrap", 
                      gap: "0.5rem", 
                      fontSize: "0.8rem",
                      marginBottom: "0.5rem"
                    }}>
                      {paper.year && (
                        <span style={{ 
                          background: "#f5f5f5", 
                          padding: "2px 6px", 
                          borderRadius: "3px",
                          color: "#555"
                        }}>
                          📅 {paper.year}
                        </span>
                      )}
                      {paper.cited_count != null && (
                        <span style={{ 
                          background: "#f5f5f5", 
                          padding: "2px 6px", 
                          borderRadius: "3px",
                          color: "#555"
                        }}>
                          📊 {paper.cited_count} cites
                        </span>
                      )}
                      {paper.cluster != null && (
                        <span style={{ 
                          background: "#f5f5f5", 
                          padding: "2px 6px", 
                          borderRadius: "3px",
                          color: "#555"
                        }}>
                          🏷️ {clusterLabel(paper.cluster)}
                        </span>
                      )}
                    </div>

                    {paper.abstract && (
                      <div style={{ 
                        fontSize: "0.8rem", 
                        color: "#777", 
                        fontStyle: "italic",
                        lineHeight: 1.4,
                        maxHeight: "3em",
                        overflow: "hidden",
                        textOverflow: "ellipsis"
                      }}>
                        {paper.abstract.slice(0, 120)}
                        {paper.abstract.length > 120 && '...'}
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

