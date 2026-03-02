import { useState, useEffect } from 'react';
import './FilterPanel.css';

/**
 * FilterPanel Component
 * 
 * Provides UI controls for filtering papers by:
 * - Date range (year_min, year_max)
 * - Citation count (min_citations)
 * - Decay factor for importance scoring
 * - Node limit (top N by citations - requires page refresh)
 * 
 * Props:
 * - onFilterChange: callback(filters) - called when filters change
 * - initialFilters: object with initial filter values
 */
export default function FilterPanel({ onFilterChange, initialFilters = {} }) {
  const currentYear = new Date().getFullYear();
  
  // Load node limit from localStorage or use default
  const getStoredNodeLimit = () => {
    const stored = localStorage.getItem('graphNodeLimit');
    return stored ? parseInt(stored, 10) : null;
  };
  
  const [filters, setFilters] = useState({
    yearMin: initialFilters.yearMin || null,
    yearMax: initialFilters.yearMax || null,
    minCitations: initialFilters.minCitations || null,
    decayFactor: initialFilters.decayFactor || 1.0,
    nodeLimit: initialFilters.nodeLimit || getStoredNodeLimit(),
  });

  const [expanded, setExpanded] = useState(false);

  // Notify parent when filters change
  useEffect(() => {
    onFilterChange?.(filters);
  }, [filters, onFilterChange]);

  const handleYearMinChange = (e) => {
    const value = e.target.value ? parseInt(e.target.value) : null;
    setFilters(prev => ({ ...prev, yearMin: value }));
  };

  const handleYearMaxChange = (e) => {
    const value = e.target.value ? parseInt(e.target.value) : null;
    setFilters(prev => ({ ...prev, yearMax: value }));
  };

  const handleMinCitationsChange = (e) => {
    const value = e.target.value ? parseInt(e.target.value) : null;
    setFilters(prev => ({ ...prev, minCitations: value }));
  };

  const handleDecayFactorChange = (e) => {
    const value = parseFloat(e.target.value);
    setFilters(prev => ({ ...prev, decayFactor: value }));
  };

  const handleNodeLimitChange = (e) => {
    const value = e.target.value ? parseInt(e.target.value) : null;
    setFilters(prev => ({ ...prev, nodeLimit: value }));
    // Store in localStorage for persistence
    if (value) {
      localStorage.setItem('graphNodeLimit', value.toString());
    } else {
      localStorage.removeItem('graphNodeLimit');
    }
  };

  const handleClearFilters = () => {
    setFilters({
      yearMin: null,
      yearMax: null,
      minCitations: null,
      decayFactor: 1.0,
      nodeLimit: null,
    });
    localStorage.removeItem('graphNodeLimit');
  };

  const hasActiveFilters = filters.yearMin || filters.yearMax || filters.minCitations || filters.decayFactor !== 1.0 || filters.nodeLimit;

  return (
    <div className={`filter-panel ${expanded ? 'expanded' : 'collapsed'}`}>
      <div className="filter-header" onClick={() => setExpanded(!expanded)}>
        <h3>
          🔍 Filters
          {hasActiveFilters && <span className="filter-badge">Active</span>}
        </h3>
        <button className="toggle-btn" aria-label={expanded ? "Collapse" : "Expand"}>
          {expanded ? '▼' : '▶'}
        </button>
      </div>

      {expanded && (
        <div className="filter-body">
          {/* Date Range Filter */}
          <div className="filter-group">
            <label className="filter-label">📅 Publication Date Range</label>
            <div className="filter-row">
              <div className="filter-input-group">
                <label htmlFor="yearMin" className="input-label">From</label>
                <input
                  id="yearMin"
                  type="number"
                  min="1900"
                  max={currentYear}
                  value={filters.yearMin || ''}
                  onChange={handleYearMinChange}
                  placeholder="1900"
                  className="filter-input"
                />
              </div>
              <span className="filter-separator">—</span>
              <div className="filter-input-group">
                <label htmlFor="yearMax" className="input-label">To</label>
                <input
                  id="yearMax"
                  type="number"
                  min="1900"
                  max={currentYear}
                  value={filters.yearMax || ''}
                  onChange={handleYearMaxChange}
                  placeholder={currentYear.toString()}
                  className="filter-input"
                />
              </div>
            </div>
          </div>

          {/* Citation Count Filter */}
          <div className="filter-group">
            <label htmlFor="minCitations" className="filter-label">
              📊 Minimum Citations
            </label>
            <input
              id="minCitations"
              type="number"
              min="0"
              value={filters.minCitations || ''}
              onChange={handleMinCitationsChange}
              placeholder="No minimum"
              className="filter-input"
            />
            <small className="filter-hint">
              Only show papers with at least this many citations
            </small>
          </div>

          {/* Decay Factor Slider */}
          <div className="filter-group">
            <label htmlFor="decayFactor" className="filter-label">
              ⚖️ Scoring Decay Factor: <strong>{filters.decayFactor.toFixed(1)}</strong>
            </label>
            <input
              id="decayFactor"
              type="range"
              min="0.1"
              max="3.0"
              step="0.1"
              value={filters.decayFactor}
              onChange={handleDecayFactorChange}
              className="filter-slider"
            />
            <div className="slider-labels">
              <span>Favor Recent</span>
              <span>Balanced</span>
              <span>Favor Old</span>
            </div>
            <small className="filter-hint">
              Controls how paper age affects importance score
            </small>
          </div>

          {/* Node Limit Control */}
          <div className="filter-group" style={{ borderTop: '2px solid #e0e0e0', paddingTop: '1rem', marginTop: '1rem' }}>
            <label htmlFor="nodeLimit" className="filter-label">
              📈 Initial Node Limit (Top by Citations)
            </label>
            <input
              id="nodeLimit"
              type="number"
              min="100"
              max="50000"
              step="100"
              value={filters.nodeLimit || ''}
              onChange={handleNodeLimitChange}
              placeholder="Default (all highly-cited)"
              className="filter-input"
            />
            <small className="filter-hint" style={{ color: '#d97706', fontWeight: '600' }}>
              ⚠️ Requires page refresh to take effect. Loads top N papers by citation count.
            </small>
            {filters.nodeLimit && (
              <button
                onClick={() => {
                  setFilters(prev => ({ ...prev, nodeLimit: null }));
                  localStorage.removeItem('graphNodeLimit');
                }}
                style={{
                  marginTop: '0.5rem',
                  padding: '0.25rem 0.75rem',
                  fontSize: '0.85rem',
                  background: '#ef4444',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Reset to Default
              </button>
            )}
          </div>

          {/* Active Filters Summary */}
          {hasActiveFilters && (
            <div className="active-filters">
              <strong>Active Filters:</strong>
              <ul>
                {filters.yearMin && <li>From {filters.yearMin}</li>}
                {filters.yearMax && <li>Until {filters.yearMax}</li>}
                {filters.minCitations && <li>≥ {filters.minCitations} citations</li>}
                {filters.decayFactor !== 1.0 && <li>Decay: {filters.decayFactor.toFixed(1)}</li>}
                {filters.nodeLimit && <li>Top {filters.nodeLimit} nodes (refresh required)</li>}
              </ul>
            </div>
          )}

          {/* Clear Button */}
          <button
            className="clear-filters-btn"
            onClick={handleClearFilters}
            disabled={!hasActiveFilters}
          >
            Clear All Filters
          </button>
        </div>
      )}
    </div>
  );
}

