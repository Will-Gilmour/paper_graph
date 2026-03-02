import React from "react";
import PaperActions from "../PaperActions";

const API = import.meta.env.VITE_API_URL;

/**
 * DetailsPane - Displays detailed information about a selected paper
 * 
 * @param {string} doi - DOI of the selected paper
 * @param {object} paper - Full paper metadata
 * @param {string|null} error - Error message if paper failed to load
 * @param {array} candidates - List of similar/related papers
 * @param {string|null} candError - Error message for candidates
 * @param {boolean} loadingCand - Whether candidates are loading
 * @param {number} perPage - Number of candidates to show per page
 * @param {number} visibleCount - Current number of visible candidates
 * @param {function} setPerPage - Update perPage state
 * @param {function} setVisibleCount - Update visibleCount state
 * @param {function} loadMore - Load more candidates
 * @param {function} clusterLabel - Get cluster label by ID
 * @param {function} subClusterLabel - Get sub-cluster label by ID
 * @param {object} papersOfInterest - Papers of interest hook object
 */
export default function DetailsPane({
  doi,
  paper,
  error,
  candidates,
  candError,
  loadingCand,
  perPage,
  visibleCount,
  setPerPage,
  setVisibleCount,
  loadMore,
  clusterLabel,
  subClusterLabel,
  papersOfInterest,
}) {
  if (!doi) {
    return <div style={{ padding: "1rem" }}>Select a node to see details.</div>;
  }

  if (error) {
    return <div className="error" style={{ padding: "1rem" }}>{error}</div>;
  }

  if (!paper) {
    return <div style={{ padding: "1rem" }}>Loading paper details…</div>;
  }

  const mainCl = clusterLabel(paper.cluster);
  const subCl = paper.sub_cluster !== undefined ? subClusterLabel(paper.sub_cluster) : null;

  return (
    <div style={{ padding: "1rem", height: "100%", overflowY: "auto" }}>
      <h2 style={{ marginTop: 0 }}>{paper.title}</h2>

      <p>
        <strong>DOI:</strong>{" "}
        <a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noopener noreferrer">
          {paper.doi}
        </a>
      </p>

      <p>
        <strong>Authors:</strong> {paper.authors.join(", ")}
      </p>
      <p>
        <strong>Year:</strong> {paper.year}
      </p>
      <p>
        <strong>Journal:</strong> {paper.container_title}
      </p>
      <p>
        <strong>Publisher:</strong> {paper.publisher}
      </p>
      <p>
        <strong>Cluster:</strong> {mainCl}
        {subCl && (
          <>
            &nbsp;›&nbsp;{subCl}
          </>
        )}
        &nbsp;|&nbsp; <strong>FNCR:</strong> {paper.fncr_count?.toFixed(2) ?? "-"}
        &nbsp;|&nbsp; <strong>Internal&nbsp;Cites:</strong> {paper.cited_count}
        &nbsp;|&nbsp; <strong>Refs:</strong> {paper.references_count}
      </p>

      {/* Papers of Interest action button */}
      {papersOfInterest && (
        <div style={{ marginTop: "1rem", marginBottom: "1rem" }}>
          <PaperActions
            doi={doi}
            isInList={papersOfInterest.hasPaper(doi)}
            onToggle={papersOfInterest.togglePaper}
          />
        </div>
      )}

      {paper.abstract && (
        <section>
          <h3>Abstract</h3>
          <div
            style={{
              maxHeight: "200px",
              overflowY: "auto",
              whiteSpace: "pre-wrap",
              background: "#fafafa",
              padding: "0.5rem",
              borderRadius: "4px",
              fontSize: "0.9rem",
              lineHeight: 1.4,
            }}
            dangerouslySetInnerHTML={{ __html: paper.abstract }}
          />
        </section>
      )}

      {/* Reading list suggestions */}
      <section style={{ marginTop: "2rem" }}>
        <h3>Possible similar papers</h3>
        {loadingCand && <div>Loading suggestions…</div>}
        {candError && <div className="error">{candError}</div>}
        {!loadingCand && !candError && visibleCount === 0 && <div>No suggestions found.</div>}

        <ul style={{ paddingLeft: "1rem" }}>
          {candidates.slice(0, visibleCount).map((item) => {
            const pCl = clusterLabel(item.cluster);
            const sCl = item.sub_cluster !== undefined ? subClusterLabel(item.sub_cluster) : null;
            return (
              <li key={item.doi} style={{ marginBottom: "0.4rem" }}>
                <a
                  href={`https://doi.org/${item.doi}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {item.title || item.doi}
                </a>{" "}
                <span style={{ fontSize: "0.85rem", color: "#666" }}>
                  ({item.year}, cites: {item.citations}, fncr: {item.fncr?.toFixed(2)}) {" • "} {pCl}
                  {sCl && ` › ${sCl}`}
                </span>
              </li>
            );
          })}
        </ul>

        {/* Pagination controls */}
        {visibleCount < candidates.length && (
          <div style={{ marginTop: "1rem" }}>
            <label style={{ fontSize: "0.9rem", marginRight: "0.5rem" }}>
              Show&nbsp;
              <select
                value={perPage}
                onChange={(e) => {
                  const newPer = +e.target.value;
                  setPerPage(newPer);
                  setVisibleCount(Math.min(newPer, candidates.length));
                }}
              >
                {[10, 50, 100].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
              &nbsp;more
            </label>
            <button onClick={loadMore}>
              Load next {Math.min(perPage, candidates.length - visibleCount)}
            </button>
          </div>
        )}

        {visibleCount >= candidates.length && candidates.length > 0 && (
          <div style={{ fontSize: "1rem", color: "#666", marginTop: "1rem" }}>
            Showing all {candidates.length} suggestions.
          </div>
        )}
      </section>
    </div>
  );
}

