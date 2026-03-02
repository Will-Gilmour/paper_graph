/**
 * useApi - Custom React hook for API calls with loading and error states
 */

import { useState, useCallback } from 'react';
import { ApiError } from '../api/client.js';

/**
 * Hook for making API calls with built-in state management
 * @param {Function} apiFunction - API function to call
 * @returns {Object} - { data, loading, error, execute, reset }
 */
export function useApi(apiFunction) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const execute = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await apiFunction(...args);
      setData(result);
      return result;
    } catch (err) {
      const errorMessage = err instanceof ApiError 
        ? err.message 
        : 'An unexpected error occurred';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiFunction]);
  
  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);
  
  return { data, loading, error, execute, reset };
}

/**
 * Hook for streaming NDJSON data
 * @param {Function} streamFunction - Async generator function
 * @returns {Object} - { items, loading, error, stream, reset }
 */
export function useStream(streamFunction) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const stream = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    setItems([]);
    
    try {
      const generator = streamFunction(...args);
      
      for await (const item of generator) {
        setItems(prev => [...prev, item]);
      }
    } catch (err) {
      const errorMessage = err instanceof ApiError 
        ? err.message 
        : 'An unexpected error occurred';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [streamFunction]);
  
  const reset = useCallback(() => {
    setItems([]);
    setError(null);
    setLoading(false);
  }, []);
  
  return { items, loading, error, stream, reset };
}

/**
 * Hook for lazy API calls (don't execute immediately)
 * @param {Function} apiFunction - API function to call
 * @param {Object} options - { onSuccess, onError }
 * @returns {Array} - [execute, { data, loading, error }]
 */
export function useLazyApi(apiFunction, { onSuccess, onError } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const execute = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await apiFunction(...args);
      setData(result);
      
      if (onSuccess) {
        onSuccess(result);
      }
      
      return result;
    } catch (err) {
      const errorMessage = err instanceof ApiError 
        ? err.message 
        : 'An unexpected error occurred';
      setError(errorMessage);
      
      if (onError) {
        onError(err);
      }
      
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiFunction, onSuccess, onError]);
  
  return [execute, { data, loading, error }];
}

export default {
  useApi,
  useStream,
  useLazyApi,
};

