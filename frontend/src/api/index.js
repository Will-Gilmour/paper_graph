/**
 * API Index - Main export for all API functionality
 * 
 * Re-exports all endpoints and utilities for easy access
 */

// Export everything from the new modular structure
export * from './client.js';
export * from './endpoints.js';

// Default export
export { default } from './endpoints.js';

// Legacy compatibility exports
import { search, exports } from './endpoints.js';

/**
 * @deprecated Use search.findPapers instead
 */
export async function find(query, field = 'auto', top_k = 20) {
  const result = await search.findPapers(query, field, top_k);
  return result.results || [];
}

/**
 * @deprecated Use exports.getJsonExport instead
 */
export async function fetchGraphSlice(offset = 0, limit = 1000) {
  return exports.getJsonExport({
    nodesOffset: offset,
    nodesLimit: limit,
    edgesOffset: 0,
    edgesLimit: 0,
  });
}
