// **************************************************************
// Sidebar.jsx – forest‑green tabs + expandable sub‑clusters (July 2025)
// -------------------------------------------------------------------
// ‣ Keeps all existing details‑pane logic.
// ‣ Active tab buttons = forest‑green (#228B22) + white text.
// ‣ Clusters pane now groups parent clusters with collapsible
//   sub‑cluster lists and multi‑select checkboxes.
//   • Selecting a parent toggles all its children.
//   • Parent checkbox shows an indeterminate state when some but
//     not all of its branch is selected.
//   • `onClusterFilterChange(selectedIds)` still emits *all* checked IDs.
// -------------------------------------------------------------------

import React, { useEffect, useState, useCallback, useRef, useMemo } from "react";
import PaperActions from "./PaperActions";
import DetailsPane from "./sidebar/DetailsPane";
import SearchPane from "./sidebar/SearchPane";

const API = import.meta.env.VITE_API_URL;

export default function SideBar({
  doi,
  onClusterFilterChange = () => {}, // optional callback from parent
  searchResults = [],
  onResultHover = () => {},
  onResultClick = () => {},
  papersOfInterest, // {papersOfInterest: Set, addPaper, removePaper, togglePaper, clearAll, hasPaper, count}
  onRecommendationsChange = () => {}, // callback to pass recommendations to parent
  onPoiPaperHover = () => {}, // callback for hovering Papers of Interest
}) {
  /* ────────────────────────── tab state ───────────────────────── */
  const [activeTab, setActiveTab] = useState("details"); // "details" | "clusters" | "search" | "list"

  /* ────────────────────────── details pane state ─────────────── */
  const [paper, setPaper] = useState(null);
  const [error, setError] = useState(null);

  const [candidates, setCandidates] = useState([]);
  const [candError, setCandError] = useState(null);
  const [loadingCand, setLoadingCand] = useState(false);

  const [perPage, setPerPage] = useState(10);
  const [visibleCount, setVisibleCount] = useState(0);

  /* cluster‑label helpers (re‑used by both panes) */
  const [parentById, setParentById] = useState(new Map());
  const [subById, setSubById] = useState(new Map());

  /* ────────────────────────── search pane state ──────────────── */
  const [searchPapers, setSearchPapers] = useState([]);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [hoveredDoi, setHoveredDoi] = useState(null);
  const [searchTitle, setSearchTitle] = useState("");
  const [searchAuthor, setSearchAuthor] = useState("");
  const [searchYearMin, setSearchYearMin] = useState("");
  const [searchYearMax, setSearchYearMax] = useState("");
  const [searchMinCitations, setSearchMinCitations] = useState("");
  const [searchClusters, setSearchClusters] = useState(new Set());

  /* ────────────────────────── clusters pane state ────────────── */
  const [clusterList, setClusterList] = useState([]); // raw list from API
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [clustError, setClustError] = useState(null);
  const [collapsedParents, setCollapsedParents] = useState(new Set());

  /* build a {parentId: [children]} lookup on every clusterList change */
  const [childrenByParent, setChildrenByParent] = useState(new Map());  // filled in 0-d

  /* ---------------- 0) load parent + sub-cluster titles ONCE --- */
  useEffect(() => {
    Promise.all([
      fetch(`${API}/clusters`).then((r) => r.ok ? r.json() : Promise.reject(r)),
      fetch(`${API}/labels/parent`).then((r) => r.ok ? r.json() : Promise.reject(r)),
      fetch(`${API}/labels/sub`).then((r) => r.ok ? r.json() : Promise.reject(r)),
    ])
      .then(([clusters, labelsParent, labelsSub]) => {
        /* 0-a  parent & sub-label maps */
        setParentById(new Map(Object.entries(labelsParent).map(([id, t]) => [+id, t])));
        setSubById(new Map(
          Object.entries(labelsSub).map(([key, t]) => {
            const [, sid] = key.split(":" );            // \"123:7\" → 7
            return [+sid, t];
          }),
        ));

        /* 0-b  parent cluster list for the UI */
        clusters.sort((a, b) => (b.size ?? 0) - (a.size ?? 0));
        setClusterList(clusters);

        /* 0-c  initial selection = everything */
        const allIds = clusters.map((c) => c.id);
        setSelectedIds(new Set(allIds));
        onClusterFilterChange(allIds);

        /* 0-d  build children lookup from LABELS_SUB keys */
        const map = new Map();                // pid → [{id,label}]
        Object.keys(labelsSub).forEach((k) => {
          const [pid, sid] = k.split(":" ).map(Number);
          if (!map.has(pid)) map.set(pid, []);
          map.get(pid).push(sid);
        });
        setChildrenByParent(map);             // <-- new state, see §2
      })
      .catch((err) => {
        console.error("cluster/label fetch failed", err);
        setClustError("Could not load cluster list");
      });
  }, []);

  /* helper: label lookup with graceful fallback */
  const clusterLabel = (id) => parentById.get(id) ?? id;
  const subClusterLabel = (id) => subById.get(id) ?? id;

  /* ---------------- search‑pane effects ---------------------- */
  useEffect(() => {
    if (!searchResults || searchResults.length === 0) {
      setSearchPapers([]);
      return;
    }

    // Switch to search tab when results arrive
    setActiveTab("search");
    setLoadingSearch(true);

    // Fetch details for all results (limit to first 50)
    Promise.all(
      searchResults.slice(0, 50).map(async (doi) => {
        try {
          const res = await fetch(`${API}/paper/${encodeURIComponent(doi)}`);
          if (res.ok) {
            return await res.json();
          }
          return { doi, title: doi, error: true };
        } catch (err) {
          console.warn(`Failed to fetch ${doi}:`, err);
          return { doi, title: doi, error: true };
        }
      })
    ).then((results) => {
      setSearchPapers(results);
      setLoadingSearch(false);
    });
  }, [searchResults]);

  /* ---------------- details‑pane effects (unchanged) ----------- */
  useEffect(() => {
    if (!doi) {
      setPaper(null);
      setCandidates([]);
      setVisibleCount(0);
      return;
    }
    setError(null);
    setPaper(null);

    fetch(`${API}/paper/${encodeURIComponent(doi)}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(setPaper)
      .catch((err) => {
        console.error("Failed to load paper:", err);
        setError("Could not fetch paper details");
      });
  }, [doi]);


  /* reading‑list suggestions (unchanged logic) */
  useEffect(() => {
    if (!paper) return;
    setLoadingCand(true);
    setCandError(null);

    const params = new URLSearchParams({
      center: doi,
      k_region: "1000",
      depth_refs: "1",
      min_cites: "4",
      weight_distance: "0.5",
      top_n: "1000",
    }).toString();

    fetch(`${API}/reading_list?${params}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((json) => {
        const list = Array.isArray(json.reading_list) ? json.reading_list : [];
        setCandidates(list);
        setVisibleCount(Math.min(perPage, list.length));
      })
      .catch((err) => {
        console.error("Failed to load reading list:", err);
        setCandError("Could not fetch similar papers");
      })
      .finally(() => setLoadingCand(false));
  }, [paper, doi, perPage]);

  const loadMore = () => setVisibleCount((c) => Math.min(c + perPage, candidates.length));

  /* ---------------- clusters pane helpers ---------------------- */
  const toggleIds = preserveScroll(useCallback(
    (ids) => {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        const allSelected = ids.every((id) => next.has(id));
        if (allSelected) ids.forEach((id) => next.delete(id));
        else ids.forEach((id) => next.add(id));
        onClusterFilterChange(Array.from(next));
        return next;
      });
    },
    [onClusterFilterChange]
  ));

  const toggleSingleId = (id) => toggleIds([id]);

  const selectAll = () => {
  // parent IDs …
  const allIds = clusterList.map((c) => c.id);
  // … plus every sub-cluster id from childrenByParent
  childrenByParent.forEach((kids) => allIds.push(...kids));
  setSelectedIds(new Set(allIds));
  onClusterFilterChange(allIds);
  };

  const clearAll = () => {
    setSelectedIds(new Set());
    onClusterFilterChange([]);
  };

  const toggleCollapse = preserveScroll((pid) => {
    setCollapsedParents((prev) => {
      const next = new Set(prev);
      if (next.has(pid)) next.delete(pid);
      else next.add(pid);
      return next;
    });
  });

  /* checkbox indeterminate management */
  const ParentCheckbox = ({ parent, childrenIds }) => {
    const ref = useRef();
    // Only toggle the parent ID, not children (children are independent)
    const parentSelected = selectedIds.has(parent.id);
    const childrenSelected = childrenIds.filter(id => selectedIds.has(id)).length;
    const allChildrenSelected = childrenIds.length > 0 && childrenSelected === childrenIds.length;

    useEffect(() => {
      // Indeterminate if parent selected but not all children, or vice versa
      if (ref.current) {
        ref.current.indeterminate = (parentSelected && !allChildrenSelected) || 
                                    (!parentSelected && childrenSelected > 0);
      }
    });

    return (
      <input
        ref={ref}
        type="checkbox"
        checked={parentSelected}
        onChange={() => toggleSingleId(parent.id)}
      />
    );
  };

  /* ─────────────────────────── search pane component ──────────── */
  const handleSearchSubmit = useCallback(async (e) => {
    e?.preventDefault();
    if (!searchTitle.trim() && !searchAuthor.trim()) return;

    setLoadingSearch(true);

    try {
      // Build query string with new combined search
      const params = new URLSearchParams();
      
      if (searchTitle.trim()) params.append('title', searchTitle.trim());
      if (searchAuthor.trim()) params.append('author', searchAuthor.trim());
      if (searchYearMin) params.append('year_min', searchYearMin);
      if (searchYearMax) params.append('year_max', searchYearMax);
      if (searchMinCitations) params.append('min_citations', searchMinCitations);
      if (searchClusters.size > 0) {
        params.append('clusters', Array.from(searchClusters).join(','));
      }
      
      const res = await fetch(`${API}/find?${params.toString()}`);
      const { results } = await res.json();

      const doiList = results.map(item => {
        if (typeof item === 'object' && item.doi) return item.doi;
        return item;
      });

      // Fetch details for all results (limit to first 50)
      const papers = await Promise.all(
        doiList.slice(0, 50).map(async (doi) => {
          try {
            const res = await fetch(`${API}/paper/${encodeURIComponent(doi)}`);
            if (res.ok) {
              return await res.json();
            }
            return { doi, title: doi, error: true };
          } catch (err) {
            console.warn(`Failed to fetch ${doi}:`, err);
            return { doi, title: doi, error: true };
          }
        })
      );

      setSearchPapers(papers);
    } catch (err) {
      console.error('Search failed:', err);
      setSearchPapers([]);
    } finally {
      setLoadingSearch(false);
    }
  }, [searchTitle, searchAuthor, searchYearMin, searchYearMax, searchMinCitations, searchClusters]);

  // Search result handlers (outside SearchPane to prevent recreation)
  const handleResultMouseEnter = useCallback((doi) => {
    setHoveredDoi(doi);
    onResultHover?.(doi);
  }, [onResultHover]);

  const handleResultMouseLeave = useCallback(() => {
    setHoveredDoi(null);
    onResultHover?.(null);
  }, [onResultHover]);

  const handleResultClick = useCallback((doi) => {
    onResultClick?.(doi);
    setActiveTab("details"); // Switch to details tab after selection
  }, [onResultClick]);

  // SearchPane is now imported from ./sidebar/SearchPane

  /* ─────────────────────────── render helpers ─────────────────── */
  /* keeps the user's scroll position inside the clusters pane */
  const scrollBoxRef = useRef(null);

  function preserveScroll(fn) {
    return (...args) => {
      const y = scrollBoxRef.current?.scrollTop ?? 0;
      fn(...args);
      requestAnimationFrame(() => {          // run *after* re-render
        if (scrollBoxRef.current) scrollBoxRef.current.scrollTop = y;
      });
    };
  }

  // DetailsPane is now imported from ./sidebar/DetailsPane

  const ClustersPane = () => {
    if (clustError) return <div style={{ padding: "1rem" }}>{clustError}</div>;
    if (clusterList.length === 0) return <div style={{ padding: "1rem" }}>Loading clusters…</div>;

    // parent clusters are ones WITHOUT parent_id
    const parents = clusterList.filter((c) => !c.parent_id);

    // start with every parent collapsed once, only when the lookup is ready
    useEffect(() => {
    if (parents.length && collapsedParents.size === 0) {
     setCollapsedParents(new Set(parents.map((p) => p.id)));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [parents.length]);

    return (
      <div style={{ padding: "1rem", height: "100%", display: "flex", flexDirection: "column" }}>
        <div style={{ marginBottom: "0.5rem" }}>
          <button onClick={selectAll} style={{ marginRight: "0.5rem" }}>
            Select all
          </button>
          <button onClick={clearAll}>Clear</button>
        </div>
        <div ref={scrollBoxRef} style={{ flex: 1, overflowY: "auto" }}>
            <ul style={{ listStyle: "none", padding: 0 }}>
            {parents.map((p) => {
              const children = childrenByParent.get(p.id) || [];
              const isCollapsed = collapsedParents.has(p.id);
              return (
                <li key={p.id} style={{ marginBottom: "0.3rem", marginLeft: 0 }}>
                  <div style={{ display: "flex", alignItems: "center" }}>
                    {children.length > 0 && (
                      <button
                        onClick={() => toggleCollapse(p.id)}
                        style={{
                          border: "none",
                          background: "transparent",
                          cursor: "pointer",
                          fontSize: "2rem",
                            width: "1rem",
                            height: "1rem",
                            padding:"0",
                            display: "inline-flex",
                            alignItems:"center",
                            justifyContent:"center",
                          marginRight: "0.2rem",
                          color: "#228B22",          // forest-green
                          lineHeight: 1
                        }}
                        aria-label={isCollapsed ? "Expand" : "Collapse"}
                      >
                        {isCollapsed ? "▸" : "▾"}
                      </button>
                    )}
                    <label style={{ cursor: "pointer" }}>
                      <ParentCheckbox parent={p} childrenIds={children} /> {" "}
                      {clusterLabel(p.id)} ({(p.size ?? 0).toLocaleString()})
                    </label>
                  </div>

                  {/* children list */}
                  {!isCollapsed && children.length > 0 && (
                    <ul style={{ listStyle: "none", paddingLeft: "1.6rem", marginTop: "0.2rem" }}>
                      {children.map((cid) => (
                        <li key={cid} style={{ marginBottom: "0.25rem" }}>
                          <label style={{ cursor: "pointer" }}>
                            <input
                              type="checkbox"
                              checked={selectedIds.has(cid)}
                              onChange={() => toggleSingleId(cid)}
                            />{" "}
                            {subClusterLabel(cid)}
                          </label>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    );
  };

  /* ─────────────────────────── Papers of Interest pane ──────────── */
  const [poiPapers, setPoiPapers] = useState([]);
  const [poiLoading, setPoiLoading] = useState(false);
  const [poiHoveredDoi, setPoiHoveredDoi] = useState(null);
  
  // Recommendations state
  const [recommendations, setRecommendations] = useState([]);
  const [recLoading, setRecLoading] = useState(false);
  const [recError, setRecError] = useState(null);
  const [recMode, setRecMode] = useState('spatial'); // 'spatial' or 'bridges'
  const [showingRecs, setShowingRecs] = useState(false);

  // Fetch full paper details for Papers of Interest
  useEffect(() => {
    if (!papersOfInterest || papersOfInterest.count === 0) {
      setPoiPapers([]);
      setRecommendations([]);
      setShowingRecs(false);
      return;
    }

    const fetchPaperDetails = async () => {
      setPoiLoading(true);
      const papers = Array.from(papersOfInterest.papersOfInterest);
      
      try {
        const results = await Promise.all(
          papers.map(async (doi) => {
            try {
              const res = await fetch(`${API}/paper/${encodeURIComponent(doi)}`);
              if (!res.ok) return { doi, error: "Not in current graph", notInGraph: true };
              return await res.json();
            } catch (e) {
              return { doi, error: e.message, notInGraph: true };
            }
          })
        );
        setPoiPapers(results);
      } catch (e) {
        console.error("Failed to fetch papers of interest:", e);
      } finally {
        setPoiLoading(false);
      }
    };

    fetchPaperDetails();
  }, [papersOfInterest?.count]);
  
  // Helper to remove papers not in current graph
  const clearInvalidPapers = useCallback(() => {
    poiPapers.forEach(paper => {
      if (paper.notInGraph) {
        papersOfInterest.removePaper(paper.doi);
      }
    });
  }, [poiPapers, papersOfInterest]);

  // Fetch recommendations
  const handleGetRecommendations = useCallback(async () => {
    if (!papersOfInterest || papersOfInterest.count === 0) return;
    
    setRecLoading(true);
    setRecError(null);
    
    try {
      const dois = Array.from(papersOfInterest.papersOfInterest);
      const endpoint = recMode === 'spatial' ? '/recommendations/spatial' : '/recommendations/bridges';
      
      const response = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dois,
          top_n: 20,
          min_citations: 5,
        }),
      });
      
      if (!response.ok) throw new Error('Failed to fetch recommendations');
      
      const data = await response.json();
      const recs = data.recommendations || [];
      setRecommendations(recs);
      setShowingRecs(true);
      
      // Pass recommendations to parent (for graph visualization)
      onRecommendationsChange(recs);
    } catch (e) {
      console.error("Failed to fetch recommendations:", e);
      setRecError(e.message);
    } finally {
      setRecLoading(false);
    }
  }, [papersOfInterest, recMode, onRecommendationsChange]);

  const PapersOfInterestPane = () => {
    if (!papersOfInterest || papersOfInterest.count === 0) {
      return (
        <div style={{ padding: "1rem", textAlign: "center" }}>
          <p style={{ color: "#666", marginTop: "2rem" }}>
            No papers in your collection yet.
          </p>
          <p style={{ fontSize: "0.9rem", color: "#999" }}>
            Click papers in the graph or search results, then use "Add to List" to build your collection.
          </p>
        </div>
      );
    }

    const invalidCount = poiPapers.filter(p => p.notInGraph).length;

    return (
      <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
        <div style={{ padding: "1rem", borderBottom: "1px solid #e0e0e0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <h3 style={{ margin: 0 }}>My Papers ({papersOfInterest.count})</h3>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              {invalidCount > 0 && (
                <button
                  onClick={clearInvalidPapers}
                  style={{
                    padding: "6px 12px",
                    background: "#ffc107",
                    color: "#000",
                    border: "none",
                    borderRadius: "4px",
                    cursor: "pointer",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                  }}
                  title="Remove papers not in current graph"
                >
                  Clear Invalid ({invalidCount})
                </button>
              )}
              <button
                onClick={papersOfInterest.clearAll}
                style={{
                  padding: "6px 12px",
                  background: "#dc3545",
                  color: "#fff",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "0.85rem",
                  fontWeight: 600,
                }}
              >
                Clear All
              </button>
            </div>
          </div>

          {/* Recommendations controls */}
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <select
              value={recMode}
              onChange={(e) => setRecMode(e.target.value)}
              style={{
                padding: "6px 10px",
                border: "1px solid #ddd",
                borderRadius: "4px",
                fontSize: "0.85rem",
                flex: 1,
              }}
            >
              <option value="spatial">📍 Spatial (Nearby Papers)</option>
              <option value="bridges">🌉 Bridges (Connecting Papers)</option>
            </select>
            <button
              onClick={handleGetRecommendations}
              disabled={recLoading}
              style={{
                padding: "6px 12px",
                background: recLoading ? "#ccc" : "#17a2b8",
                color: "#fff",
                border: "none",
                borderRadius: "4px",
                cursor: recLoading ? "not-allowed" : "pointer",
                fontSize: "0.85rem",
                fontWeight: 600,
                whiteSpace: "nowrap",
              }}
            >
              {recLoading ? "..." : "Get Recs"}
            </button>
          </div>
        </div>
        
        <div style={{ flex: 1, overflowY: "auto", padding: "1rem" }}>
          {poiLoading && (
            <div style={{ padding: "2rem", textAlign: "center", color: "#666" }}>
              Loading paper details...
            </div>
          )}

          {!poiLoading && poiPapers
            .sort((a, b) => {
              // Sort by cluster first, then by citations
              if (a.cluster !== b.cluster) {
                return (a.cluster || 999) - (b.cluster || 999);
              }
              return (b.cited_count || 0) - (a.cited_count || 0);
            })
            .map((paper, idx, arr) => {
              // Show cluster header if this is a new cluster
              const prevPaper = idx > 0 ? arr[idx - 1] : null;
              const isNewCluster = !prevPaper || prevPaper.cluster !== paper.cluster;
              
              return (
                <React.Fragment key={paper.doi}>
                  {isNewCluster && (
                    <div style={{
                      background: "#f0f8ff",
                      padding: "0.5rem 0.75rem",
                      marginBottom: "0.5rem",
                      marginTop: idx > 0 ? "1rem" : "0",
                      borderRadius: "4px",
                      fontSize: "0.85rem",
                      fontWeight: 600,
                      color: "#17a2b8",
                      border: "1px solid #17a2b8",
                    }}>
                      📁 {clusterLabel(paper.cluster)}
                    </div>
                  )}
                  
            <div
              key={paper.doi}
              onMouseEnter={() => {
                setPoiHoveredDoi(paper.doi);
                onPoiPaperHover(paper.doi);
                console.log('POI hover:', paper.doi);
              }}
              onMouseLeave={() => {
                setPoiHoveredDoi(null);
                onPoiPaperHover(null);
                console.log('POI hover cleared');
              }}
              onClick={() => handleResultClick(paper.doi)}
              style={{
                background: paper.notInGraph ? "#ffe6e6" : (poiHoveredDoi === paper.doi ? "#fff8dc" : "#fff"),
                border: paper.notInGraph ? "1px solid #dc3545" : (poiHoveredDoi === paper.doi ? "1px solid #FFD700" : "1px solid #e0e0e0"),
                borderRadius: "6px",
                padding: "0.75rem",
                marginBottom: "0.75rem",
                cursor: "pointer",
                transition: "all 0.2s ease",
                boxShadow: poiHoveredDoi === paper.doi ? "0 2px 8px rgba(255, 215, 0, 0.3)" : "none",
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
                {paper.notInGraph && (
                  <span style={{
                    marginLeft: "0.5rem",
                    fontSize: "0.75rem",
                    color: "#dc3545",
                    fontWeight: 600,
                  }}>
                    ⚠️ Not in current graph
                  </span>
                )}
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

                  <div style={{ marginTop: "0.5rem" }}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        papersOfInterest.removePaper(paper.doi);
                      }}
                      style={{
                        padding: "4px 10px",
                        background: "#6c757d",
                        color: "#fff",
                        border: "none",
                        borderRadius: "3px",
                        cursor: "pointer",
                        fontSize: "0.75rem",
                        fontWeight: 600,
                      }}
                    >
                      ✕ Remove
                    </button>
                  </div>
                </>
              )}
            </div>
                </React.Fragment>
              );
            })}

          {/* Recommendations Section */}
          {showingRecs && (
            <div style={{ marginTop: "2rem", borderTop: "2px solid #17a2b8", paddingTop: "1rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <h4 style={{ margin: 0, color: "#17a2b8" }}>
                  {recMode === 'spatial' ? '📍 Nearby Papers' : '🌉 Bridge Papers'} 
                  ({recommendations.length})
                </h4>
                <button
                  onClick={() => setShowingRecs(false)}
                  style={{
                    padding: "4px 8px",
                    background: "transparent",
                    color: "#666",
                    border: "1px solid #ddd",
                    borderRadius: "3px",
                    cursor: "pointer",
                    fontSize: "0.75rem",
                  }}
                >
                  Hide
                </button>
              </div>

              {recError && (
                <div style={{ padding: "1rem", background: "#fff3cd", borderRadius: "4px", marginBottom: "1rem", color: "#856404" }}>
                  {recError}
                </div>
              )}

              {recommendations.map((rec) => (
                <div
                  key={rec.doi}
                  onClick={() => handleResultClick(rec.doi)}
                  style={{
                    background: "#e7f7ff",
                    border: "1px solid #17a2b8",
                    borderRadius: "6px",
                    padding: "0.75rem",
                    marginBottom: "0.75rem",
                    cursor: "pointer",
                    transition: "all 0.2s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "#d0f0ff";
                    e.currentTarget.style.boxShadow = "0 2px 8px rgba(23, 162, 184, 0.3)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "#e7f7ff";
                    e.currentTarget.style.boxShadow = "none";
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: "0.95rem", marginBottom: "0.5rem", color: "#222" }}>
                    {rec.title || rec.doi}
                  </div>

                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", fontSize: "0.8rem", marginBottom: "0.5rem" }}>
                    {rec.year && (
                      <span style={{ background: "#fff", padding: "2px 6px", borderRadius: "3px", color: "#555" }}>
                        📅 {rec.year}
                      </span>
                    )}
                    {rec.cited_count != null && (
                      <span style={{ background: "#fff", padding: "2px 6px", borderRadius: "3px", color: "#555" }}>
                        📊 {rec.cited_count} cites
                      </span>
                    )}
                    {rec.cluster != null && (
                      <span style={{ background: "#fff", padding: "2px 6px", borderRadius: "3px", color: "#555" }}>
                        🏷️ {clusterLabel(rec.cluster)}
                      </span>
                    )}
                  </div>

                  <div style={{ fontSize: "0.75rem", color: "#17a2b8", fontWeight: 600 }}>
                    {recMode === 'spatial' && rec.distance != null && `Distance: ${rec.distance.toFixed(1)} • Score: ${rec.score.toFixed(2)}`}
                    {recMode === 'bridges' && rec.connection_count != null && `Connects ${rec.connection_count} papers • Score: ${rec.score}`}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  /* ────────────────────────── main render ─────────────────────── */
  const tabBtnStyle = (isActive) => ({
    flex: 1,
    padding: "0.5rem",
    background: isActive ? "#228B22" : "#fafafa", // forest‑green active
    color: isActive ? "#fff" : "#000",
    border: "none",
    borderBottom: isActive ? "2px solid #228B22" : "2px solid transparent",
    cursor: "pointer",
    fontWeight: 600,
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Tab header */}
      <div style={{ display: "flex", borderBottom: "1px solid #ccc" }}>
        <button onClick={() => setActiveTab("details")} style={tabBtnStyle(activeTab === "details")}>
          Details
        </button>
        <button onClick={() => setActiveTab("search")} style={tabBtnStyle(activeTab === "search")}>
          Search
        </button>
        <button onClick={() => setActiveTab("clusters")} style={tabBtnStyle(activeTab === "clusters")}>
          Clusters
        </button>
        <button onClick={() => setActiveTab("list")} style={tabBtnStyle(activeTab === "list")}>
          My Papers {papersOfInterest && papersOfInterest.count > 0 && `(${papersOfInterest.count})`}
        </button>
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflow: "hidden" }}>
        {activeTab === "details" && (
          <DetailsPane
            doi={doi}
            paper={paper}
            error={error}
            candidates={candidates}
            candError={candError}
            loadingCand={loadingCand}
            perPage={perPage}
            visibleCount={visibleCount}
            setPerPage={setPerPage}
            setVisibleCount={setVisibleCount}
            loadMore={loadMore}
            clusterLabel={clusterLabel}
            subClusterLabel={subClusterLabel}
            papersOfInterest={papersOfInterest}
          />
        )}
        {activeTab === "search" && (
          <SearchPane
            searchTitle={searchTitle}
            searchAuthor={searchAuthor}
            searchYearMin={searchYearMin}
            searchYearMax={searchYearMax}
            searchMinCitations={searchMinCitations}
            searchClusters={searchClusters}
            setSearchTitle={setSearchTitle}
            setSearchAuthor={setSearchAuthor}
            setSearchYearMin={setSearchYearMin}
            setSearchYearMax={setSearchYearMax}
            setSearchMinCitations={setSearchMinCitations}
            setSearchClusters={setSearchClusters}
            handleSearchSubmit={handleSearchSubmit}
            searchPapers={searchPapers}
            loadingSearch={loadingSearch}
            hoveredDoi={hoveredDoi}
            handleResultMouseEnter={handleResultMouseEnter}
            handleResultMouseLeave={handleResultMouseLeave}
            handleResultClick={handleResultClick}
            clusterList={clusterList}
            clusterLabel={clusterLabel}
          />
        )}
        {activeTab === "clusters" && <ClustersPane />}
        {activeTab === "list" && <PapersOfInterestPane />}
      </div>
    </div>
  );
}
