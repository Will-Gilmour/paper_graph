// frontend/src/components/SearchBar.jsx

import React, { useState, useRef, useEffect } from 'react';

const API = import.meta.env.VITE_API_URL;

export default function SearchBar({ onSearch }) {
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dropdown, setDropdown] = useState([]);
  const wrapperRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setDropdown([]);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    const query = q.trim();
    if (!query) return;

    setError(null);
    setLoading(true);

    try {
      const response = await fetch(
        `${API}/find?query=${encodeURIComponent(query)}&field=auto&top_k=20`
      );
      if (!response.ok) throw new Error(`Status ${response.status}`);

      const json = await response.json();
      // json.results is now [{doi, title}, …]
      const hits = Array.isArray(json.results) ? json.results : [];
      if (hits.length === 0) {
        setError('No matching papers found');
      }
      setDropdown(hits);
    } catch (err) {
      console.error('Search failed', err);
      setError('Search failed. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (doi) => {
    onSearch(doi);
    setDropdown([]);
    setQ('');
  };

  return (
    <div ref={wrapperRef} style={{ position: 'relative', marginLeft: 'auto' }}>
      <form onSubmit={submit} style={{ display: 'flex', alignItems: 'center' }}>
        <input
          type="text"
          value={q}
          placeholder="Search DOI or keyword…"
          onChange={(e) => setQ(e.target.value)}
          disabled={loading}
          style={{
            padding: '6px 8px',
            borderRadius: '4px',
            border: '1px solid #ccc',
            marginRight: '8px',
            fontSize: '0.9rem',
          }}
        />
        <button
          type="submit"
          disabled={loading}
          style={{
            padding: '6px 12px',
            borderRadius: '4px',
            border: 'none',
            background: '#007bff',
            color: 'white',
            fontSize: '0.9rem',
            cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? 'Searching…' : 'Search'}
        </button>
      </form>
      {error && (
        <div style={{ color: 'red', fontSize: '0.85rem', marginTop: '4px' }}>{error}</div>
      )}

      {dropdown.length > 0 && (
        <ul
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            background: 'white',
            border: '1px solid #ccc',
            borderRadius: '4px',
            maxHeight: '200px',
            overflowY: 'auto',
            zIndex: 10,
            listStyle: 'none',
            padding: 0,
            margin: '4px 0 0 0',
          }}
        >
          {dropdown.map((hit) => (
            <li
                key={hit.doi}
                onMouseDown={(e) => { e.preventDefault(); handleSelect(hit.doi); }}
                style={{
                padding: '8px',
                cursor: 'pointer',
                borderBottom: '1px solid #eee',
                userSelect: 'none',
                }}   >
                <strong>{hit.title}</strong><br/>
                <small style={{ color: '#666' }}>{hit.doi}</small>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
