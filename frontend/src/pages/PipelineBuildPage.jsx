/**
 * Pipeline Build Page
 * 
 * Form to configure and launch new graph builds
 * Includes accountability tracking and status monitoring
 */

import { useState, useEffect } from 'react';
import HelpTooltip from '../components/HelpTooltip';
import './PipelineBuildPage.css';

export default function PipelineBuildPage() {
  // Recent builds state
  const [recentBuilds, setRecentBuilds] = useState([]);
  const [loadingBuilds, setLoadingBuilds] = useState(true);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    seedDois: '',
    maxDepth: 2,  // Changed from 1 to 2
    includeCiters: true,
    maxCiters: 50,
    useGpu: true,
    layoutIterations: 20000,  // Changed from 2000 to 20000
    clusteringResolution: 1.0,
    subClusteringResolution: 1.0,
    llmBatchSize: 8,
    autoExport: true,
    setActive: false,
    createdBy: 'admin', // TODO: Get from auth
    mailto: 'your-email@example.com',  // API email for Crossref/OpenAlex
    openalexPassword: '',  // Optional password for premium OpenAlex
  });

  const [runs, setRuns] = useState([]);
  const [activeRun, setActiveRun] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Load existing runs
  useEffect(() => {
    loadRuns();
    // Poll more frequently (every 2 seconds) to catch status changes faster
    const interval = setInterval(loadRuns, 2000);
    return () => clearInterval(interval);
  }, []);

  const loadRuns = async () => {
    try {
      const response = await fetch('/api/pipeline/builds');
      const data = await response.json();
      setRuns(data.runs);
      setActiveRun(data.active_run_id);
    } catch (err) {
      console.error('Failed to load runs:', err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      // Convert form data to API format
      const request = {
        name: formData.name,
        description: formData.description || null,
        seed_dois: formData.seedDois.split('\n').filter(doi => doi.trim()),
        max_depth: parseInt(formData.maxDepth),
        include_citers: formData.includeCiters,
        max_citers: parseInt(formData.maxCiters),
        use_gpu: formData.useGpu,
        layout_iterations: parseInt(formData.layoutIterations),
        clustering_resolution: parseFloat(formData.clusteringResolution),
        sub_clustering_resolution: parseFloat(formData.subClusteringResolution),
        llm_batch_size: parseInt(formData.llmBatchSize),
        auto_export: formData.autoExport,
        set_active: formData.setActive,
        created_by: formData.createdBy,
        mailto: formData.mailto || 'your-email@example.com',  // Include email for APIs
      };

      const response = await fetch('/api/pipeline/builds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error('Failed to start build');
      }

      const result = await response.json();
      
      // Don't reset form, just show success and scroll to history
      alert(`Build started! Run ID: ${result.id}\n\nCheck the Build History below to track progress.`);

      // Reload runs to show the new build
      loadRuns();
      
      // Scroll to build history
      setTimeout(() => {
        const historySection = document.querySelector('.build-history-section');
        if (historySection) {
          historySection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 500);

    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const activateGraph = async (runId) => {
    if (!confirm('Set this graph as active? This will switch the frontend to use this graph.')) {
      return;
    }

    try {
      const response = await fetch(`/api/pipeline/builds/${runId}/activate`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to activate graph');
      }

      alert('Graph activated successfully!');
      loadRuns();

    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const cancelBuild = async (runId, graphName) => {
    if (!confirm(`Cancel the build "${graphName}"?\n\nThis will stop the pipeline execution.`)) {
      return;
    }

    try {
      const response = await fetch(`/api/pipeline/builds/${runId}/cancel`, {
        method: 'POST',
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to cancel build');
      }

      loadRuns();
      
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const deleteGraph = async (runId, graphName) => {
    if (!confirm(`Are you sure you want to delete "${graphName}"?\n\nThis action cannot be undone.`)) {
      return;
    }

    try {
      const response = await fetch(`/api/pipeline/builds/${runId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to delete graph');
      }

      loadRuns();

    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: '#gray',
      running: '#3b82f6',
      completed: '#10b981',
      failed: '#ef4444',
      cancelled: '#6b7280',
    };
    return colors[status] || '#gray';
  };

  return (
    <div className="pipeline-build-page">
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h1>Build New Graph</h1>
            <p>Configure and launch a new citation graph build with full accountability tracking</p>
          </div>
          <button 
            onClick={() => window.location.href = '/'}
            style={{
              background: 'linear-gradient(135deg, #10b981, #059669)',
              color: 'white',
              border: 'none',
              padding: '12px 24px',
              fontSize: '16px',
              fontWeight: '600',
              borderRadius: '8px',
              cursor: 'pointer',
              boxShadow: '0 4px 6px rgba(16, 185, 129, 0.3)',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => {
              e.target.style.transform = 'translateY(-2px)';
              e.target.style.boxShadow = '0 6px 12px rgba(16, 185, 129, 0.4)';
            }}
            onMouseLeave={(e) => {
              e.target.style.transform = 'translateY(0)';
              e.target.style.boxShadow = '0 4px 6px rgba(16, 185, 129, 0.3)';
            }}
          >
            ← Back to Graph
          </button>
        </div>
      </div>

      <div className="build-container">
        {/* Build Form */}
        <div className="build-form-section">
          <h2>Configuration</h2>
          
          <form onSubmit={handleSubmit} className="build-form">
            {/* Basic Info */}
            <section className="form-section">
              <h3>Basic Information</h3>
              
              <div className="form-group">
                <label>Graph Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., MRgFUS Papers v6"
                  required
                />
              </div>

              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="What is this graph for?"
                  rows="3"
                />
              </div>

              <div className="form-group">
                <label>Seed DOIs * (one per line)</label>
                <textarea
                  value={formData.seedDois}
                  onChange={(e) => setFormData({ ...formData, seedDois: e.target.value })}
                  placeholder="10.1001/jama.2020.12345&#10;10.1002/example.67890"
                  rows="5"
                  required
                />
                <small>Enter DOIs or bibliographic citations, one per line</small>
              </div>
            </section>

            {/* Crawling Options */}
            <section className="form-section">
              <h3>Crawling Options</h3>
              
              <div className="form-group">
                <label>Max Crawl Depth</label>
                <input
                  type="number"
                  min="1"
                  max="3"
                  value={formData.maxDepth}
                  onChange={(e) => setFormData({ ...formData, maxDepth: e.target.value })}
                />
                <small>1 = direct citations only, 2 = 2-hop network, 3 = 3-hop (slow!)</small>
              </div>

              <div className="form-group checkbox">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.includeCiters}
                    onChange={(e) => setFormData({ ...formData, includeCiters: e.target.checked })}
                  />
                  Include citing papers (from OpenAlex)
                </label>
              </div>

              {formData.includeCiters && (
                <div className="form-group">
                  <label>
                    Max Citers per Paper
                    <HelpTooltip text="When building the graph, we also fetch papers that CITE your seeds (backward citations). This controls how many citing papers to include per paper. Higher = larger graph. For highly-cited papers (e.g. 1000+ citations), this prevents the graph from exploding in size. Recommended: 50-100 for focused graphs, 200 for comprehensive coverage." />
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="200"
                    value={formData.maxCiters}
                    onChange={(e) => setFormData({ ...formData, maxCiters: e.target.value })}
                  />
                  <small>Higher = more papers, but graph can get very large (default: 50)</small>
                </div>
              )}
            </section>

            {/* Layout Options */}
            <section className="form-section">
              <h3>Layout Options</h3>
              
              <div className="form-group checkbox">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.useGpu}
                    onChange={(e) => setFormData({ ...formData, useGpu: e.target.checked })}
                  />
                  Use GPU acceleration (recommended)
                </label>
              </div>

              <div className="form-group">
                <label>ForceAtlas2 Iterations</label>
                <input
                  type="number"
                  min="1000"
                  max="50000"
                  step="1000"
                  value={formData.layoutIterations}
                  onChange={(e) => setFormData({ ...formData, layoutIterations: e.target.value })}
                />
                <small>More iterations = better layout. Use fewer for denser graphs (more edges). Sparse graphs need more. (default: 20000)</small>
              </div>
            </section>

            {/* API Credentials */}
            <section className="form-section">
              <h3>API Credentials</h3>
              
              <div className="form-group">
                <label>Email for Crossref/OpenAlex</label>
                <input
                  type="email"
                  value={formData.mailto}
                  onChange={(e) => setFormData({ ...formData, mailto: e.target.value })}
                  placeholder="your-email@example.com"
                />
                <small>Used for Crossref polite pool and OpenAlex access. Verify at openalex.org to avoid 403 errors.</small>
              </div>

              <div className="form-group">
                <label>OpenAlex Password (Optional)</label>
                <input
                  type="password"
                  value={formData.openalexPassword || ''}
                  onChange={(e) => setFormData({ ...formData, openalexPassword: e.target.value })}
                  placeholder="Leave blank if using public API"
                />
                <small>Only needed if you have a premium OpenAlex account. Public API works without password.</small>
              </div>
            </section>

            {/* Clustering Options */}
            <section className="form-section">
              <h3>Clustering Options</h3>
              
              <div className="form-group">
                <label>Main Clustering Resolution</label>
                <input
                  type="number"
                  min="0.1"
                  max="5.0"
                  step="0.1"
                  value={formData.clusteringResolution}
                  onChange={(e) => setFormData({ ...formData, clusteringResolution: e.target.value })}
                />
                <small>Higher = more clusters (default: 1.0)</small>
              </div>

              <div className="form-group">
                <label>Sub-Clustering Resolution</label>
                <input
                  type="number"
                  min="0.1"
                  max="5.0"
                  step="0.1"
                  value={formData.subClusteringResolution}
                  onChange={(e) => setFormData({ ...formData, subClusteringResolution: e.target.value })}
                />
              </div>
            </section>

            {/* LLM Options */}
            <section className="form-section">
              <h3>LLM Labeling Options</h3>
              
              <div className="form-group">
                <label>LLM Batch Size</label>
                <input
                  type="number"
                  min="1"
                  max="32"
                  value={formData.llmBatchSize}
                  onChange={(e) => setFormData({ ...formData, llmBatchSize: e.target.value })}
                />
                <small>Lower = less GPU memory, slower (default: 8)</small>
              </div>
            </section>

            {/* Output Options */}
            <section className="form-section">
              <h3>Output Options</h3>
              
              <div className="form-group checkbox">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.autoExport}
                    onChange={(e) => setFormData({ ...formData, autoExport: e.target.checked })}
                  />
                  Auto-export to PostgreSQL
                </label>
              </div>

              <div className="form-group checkbox">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.setActive}
                    onChange={(e) => setFormData({ ...formData, setActive: e.target.checked })}
                  />
                  Set as active graph after completion
                </label>
                <small className="warning">⚠️ This will switch the frontend to use this graph!</small>
              </div>
            </section>

            {error && (
              <div className="error-message">
                {error}
              </div>
            )}

            <button type="submit" disabled={submitting} className="submit-button">
              {submitting ? 'Starting Build...' : 'Start Build'}
            </button>
          </form>
        </div>

        {/* Build History */}
        <div className="build-history-section">
          <h2>Build History</h2>
          
          <div className="runs-list">
            {runs.length === 0 ? (
              <p className="no-runs">No builds yet</p>
            ) : (
              runs.map(run => (
                <div key={run.id} className={`run-card ${run.is_active ? 'active' : ''} status-${run.status}`}>
                  <div className="run-header">
                    <h4>{run.name}</h4>
                    <span 
                      className="status-badge" 
                      style={{ backgroundColor: getStatusColor(run.status) }}
                    >
                      {run.status}
                    </span>
                  </div>
                  
                  {run.description && (
                    <p className="run-description">{run.description}</p>
                  )}
                  
                  <div className="run-stats">
                    {run.nodes_count && (
                      <span>{run.nodes_count.toLocaleString()} nodes</span>
                    )}
                    {run.edges_count && (
                      <span>{run.edges_count.toLocaleString()} edges</span>
                    )}
                    {run.clusters_count && (
                      <span>{run.clusters_count} clusters</span>
                    )}
                  </div>
                  
                  <div className="run-meta">
                    <small>Started: {run.started_at ? new Date(run.started_at).toLocaleString() : 'Not started'}</small>
                    {run.completed_at && (
                      <small>Completed: {new Date(run.completed_at).toLocaleString()}</small>
                    )}
                  </div>

                  {run.status === 'running' && (
                    <div className="progress-bar-container">
                      <div className="progress-bar">
                        <div className="progress-bar-fill"></div>
                      </div>
                      <div className="progress-text">
                        🔄 Building graph... This may take several minutes.
                      </div>
                    </div>
                  )}

                  {run.status === 'pending' && (
                    <div className="progress-text pending">
                      ⏳ Queued - waiting to start...
                    </div>
                  )}

                  {run.error_message && (
                    <div className="run-error">
                      ⚠️ Error: {run.error_message}
                    </div>
                  )}
                  
                  {!run.is_active && (
                    <div className="run-actions">
                      {run.status === 'completed' && (
                        <button 
                          className="activate-button"
                          onClick={() => activateGraph(run.id)}
                        >
                          Set as Active
                        </button>
                      )}
                      
                      {(run.status === 'running' || run.status === 'pending') && (
                        <button 
                          className="cancel-button"
                          onClick={() => cancelBuild(run.id, run.name)}
                        >
                          Cancel Build
                        </button>
                      )}
                      
                      {run.status !== 'running' && (
                        <button 
                          className="delete-button"
                          onClick={() => deleteGraph(run.id, run.name)}
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  )}
                  
                  {run.is_active && (
                    <div className="active-badge">✓ Active Graph (cannot delete)</div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

