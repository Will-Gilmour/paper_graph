/**
 * Custom hook for managing Papers of Interest collection
 * Persists data in localStorage
 */
import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'litsearch_papers_of_interest';

export default function usePapersOfInterest() {
  const [papersOfInterest, setPapersOfInterest] = useState(() => {
    // Initialize from localStorage
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? new Set(JSON.parse(stored)) : new Set();
    } catch (e) {
      console.warn('Failed to load Papers of Interest from localStorage', e);
      return new Set();
    }
  });

  // Persist to localStorage whenever the set changes
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(papersOfInterest)));
    } catch (e) {
      console.warn('Failed to save Papers of Interest to localStorage', e);
    }
  }, [papersOfInterest]);

  const addPaper = useCallback((doi) => {
    setPapersOfInterest(prev => {
      const next = new Set(prev);
      next.add(doi);
      return next;
    });
  }, []);

  const removePaper = useCallback((doi) => {
    setPapersOfInterest(prev => {
      const next = new Set(prev);
      next.delete(doi);
      return next;
    });
  }, []);

  const togglePaper = useCallback((doi) => {
    setPapersOfInterest(prev => {
      const next = new Set(prev);
      if (next.has(doi)) {
        next.delete(doi);
      } else {
        next.add(doi);
      }
      return next;
    });
  }, []);

  const clearAll = useCallback(() => {
    setPapersOfInterest(new Set());
  }, []);

  const hasPaper = useCallback((doi) => {
    return papersOfInterest.has(doi);
  }, [papersOfInterest]);

  return {
    papersOfInterest,
    addPaper,
    removePaper,
    togglePaper,
    clearAll,
    hasPaper,
    count: papersOfInterest.size,
  };
}


