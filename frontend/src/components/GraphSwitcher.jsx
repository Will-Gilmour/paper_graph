/**
 * Graph Switcher Component
 * Shows available graphs and allows switching between them
 */

import { useState, useEffect } from 'react';
import './GraphSwitcher.css';

export default function GraphSwitcher() {
  const [graphs, setGraphs] = useState([]);
  const [activeGraphId, setActiveGraphId] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadGraphs();
    // Refresh every 10 seconds
    const interval = setInterval(loadGraphs, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadGraphs = async () => {
    try {
      const response = await fetch('/api/pipeline/builds?status=completed');
      const data = await response.json();
      setGraphs(data.runs);
      setActiveGraphId(data.active_run_id);
    } catch (err) {
      console.error('Failed to load graphs:', err);
    }
  };

  const switchGraph = async (graphId) => {
    if (graphId === activeGraphId) {
      setShowDropdown(false);
      return;
    }

    if (!confirm('Switch to this graph? The visualization will reload.')) {
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`/api/pipeline/builds/${graphId}/activate`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to activate graph');
      }

      setActiveGraphId(graphId);
      setShowDropdown(false);
      
      // Reload page to show new graph
      window.location.reload();

    } catch (err) {
      alert(`Error switching graph: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const activeGraph = graphs.find(g => g.id === activeGraphId);

  if (graphs.length === 0) {
    return null; // No graphs yet
  }

  return (
    <div className="graph-switcher">
      <button 
        className="switcher-button"
        onClick={() => setShowDropdown(!showDropdown)}
        disabled={loading}
      >
        <span className="active-indicator">●</span>
        <span className="graph-name">
          {activeGraph ? activeGraph.name : 'No Active Graph'}
        </span>
        <span className="dropdown-arrow">{showDropdown ? '▲' : '▼'}</span>
      </button>

      {showDropdown && (
        <div className="dropdown-menu">
          <div className="dropdown-header">
            Available Graphs ({graphs.length})
          </div>
          {graphs.map(graph => (
            <div
              key={graph.id}
              className={`dropdown-item ${graph.id === activeGraphId ? 'active' : ''}`}
              onClick={() => switchGraph(graph.id)}
            >
              <div className="item-header">
                <span className="item-name">{graph.name}</span>
                {graph.id === activeGraphId && (
                  <span className="active-badge">Active</span>
                )}
              </div>
              <div className="item-stats">
                {graph.nodes_count && (
                  <span>{graph.nodes_count.toLocaleString()} nodes</span>
                )}
                {graph.clusters_count && (
                  <span>{graph.clusters_count} clusters</span>
                )}
              </div>
              <div className="item-date">
                {new Date(graph.created_at).toLocaleDateString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

