// frontend/src/App.jsx
import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import Split from 'react-split';
import SideBar from './components/Sidebar';
import GraphCanvas from './components/GraphCanvas';
import SearchBar from './components/SearchBar';
import FilterPanel from './components/FilterPanel';
import GraphSwitcher from './components/GraphSwitcher';
import PipelineBuildPage from './pages/PipelineBuildPage';
import usePapersOfInterest from './hooks/usePapersOfInterest.js';
import './App.css';

function MainVisualization() {
  const [selectedDoi, setSelectedDoi] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [clusterFilter, setClusterFilter] = useState([]);
  const [highlightedNode, setHighlightedNode] = useState(null);
  const [filters, setFilters] = useState({
    yearMin: null,
    yearMax: null,
    minCitations: null,
    decayFactor: 1.0,
  });
  
  // Papers of Interest hook
  const papersOfInterestHook = usePapersOfInterest();
  
  // Recommendations state (passed from Sidebar)
  const [recommendations, setRecommendations] = useState([]);
  
  // Hover state for Papers of Interest visualization
  const [hoveredPoiPaper, setHoveredPoiPaper] = useState(null);

  // Called when you submit the SearchBar (free-text or selected DOI)
  const handleSearch = async (queryOrDoi) => {
    try {
      // Build query string with filters
      const params = new URLSearchParams({
        query: queryOrDoi,
      });
      
      if (filters.yearMin) params.append('year_min', filters.yearMin);
      if (filters.yearMax) params.append('year_max', filters.yearMax);
      if (filters.minCitations) params.append('min_citations', filters.minCitations);
      
      const res = await fetch(
        `${import.meta.env.VITE_API_URL}/find?${params.toString()}`
      );
      const { results } = await res.json();

      // Normalize results into an array of DOIs
      // results may be strings or objects {doi, title}
      const doiList = results.map(item => {
        if (typeof item === 'object' && item.doi) return item.doi;
        return item;
      });

      setSearchResults(doiList);           // store DOIs for GraphCanvas and Sidebar
      if (doiList.length) {
        setSelectedDoi(doiList[0]);        // auto-focus the first hit
      }
    } catch (err) {
      console.error('Search failed:', err);
    }
  };

  const location = useLocation();
  const isAdminPage = location.pathname.startsWith('/admin');

  return (
    <div className="app">
      <header>
        <div style={{ display: 'flex', alignItems: 'center', gap: '2rem', flex: 1 }}>
          <h1 className="logo">
            Dr W Gilmour Literature Search Tool
          </h1>
          
          {!isAdminPage && (
            <>
              <GraphSwitcher />
              <Link 
                to="/admin/build" 
                style={{ 
                  padding: '0.5rem 1rem', 
                  background: '#3b82f6', 
                  color: 'white', 
                  textDecoration: 'none', 
                  borderRadius: '4px',
                  fontSize: '0.9rem',
                  fontWeight: '600'
                }}
              >
                Build New Graph
              </Link>
            </>
          )}
          {isAdminPage && (
            <Link 
              to="/" 
              style={{ 
                padding: '0.5rem 1.5rem', 
                background: '#10b981', 
                color: 'white', 
                textDecoration: 'none', 
                borderRadius: '6px',
                fontSize: '1rem',
                fontWeight: '700',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => e.target.style.background = '#059669'}
              onMouseLeave={(e) => e.target.style.background = '#10b981'}
            >
              ← Back to Graph
            </Link>
          )}
        </div>
        {!isAdminPage && (
          <SearchBar
            onSearch={handleSearch}
            searchResults={searchResults}
          />
        )}
      </header>

      <Split className="content" sizes={[25, 75]} minSize={320} gutterSize={8}>
        <aside className="sidebar">
          <FilterPanel 
            onFilterChange={setFilters}
            initialFilters={filters}
          />
          <SideBar
              doi={selectedDoi}
              onClusterFilterChange={setClusterFilter}
              searchResults={searchResults}
              onResultHover={setHighlightedNode}
              onResultClick={setSelectedDoi}
              papersOfInterest={papersOfInterestHook}
              onRecommendationsChange={setRecommendations}
              onPoiPaperHover={setHoveredPoiPaper}
          />
        </aside>
        <main className="main">
          <GraphCanvas
            onNodeClick={setSelectedDoi}
            searchResults={searchResults}
            clusterFilter={clusterFilter}
            filters={filters}
            highlightedNode={highlightedNode}
            papersOfInterest={papersOfInterestHook.papersOfInterest}
            recommendations={recommendations}
            hoveredPoiPaper={hoveredPoiPaper}
          />
        </main>
      </Split>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainVisualization />} />
        <Route path="/admin/build" element={<PipelineBuildPage />} />
      </Routes>
    </BrowserRouter>
  );
}
