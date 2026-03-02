/**
 * API Endpoints - All backend API calls organized by domain
 */

import { get, streamNDJSON } from './client.js';

/**
 * Cluster API endpoints
 */
export const clusters = {
  /**
   * Get all clusters with metadata
   * @returns {Promise<Array>} List of clusters
   */
  getAll: () => get('/clusters'),
  
  /**
   * Get cluster detail with nodes and edges
   * @param {number} clusterId - Cluster ID
   * @returns {Promise<Object>} Cluster detail
   */
  getDetail: (clusterId) => get(`/cluster/${clusterId}`),
  
  /**
   * Get parent cluster labels
   * @returns {Promise<Object>} Parent labels map
   */
  getParentLabels: () => get('/labels/parent'),
  
  /**
   * Get sub-cluster labels
   * @returns {Promise<Object>} Sub-cluster labels map
   */
  getSubLabels: () => get('/labels/sub'),
};

/**
 * Paper API endpoints
 */
export const papers = {
  /**
   * Get paper by DOI
   * @param {string} doi - Paper DOI
   * @returns {Promise<Object>} Paper metadata
   */
  getByDoi: (doi) => get(`/paper/${encodeURIComponent(doi)}`),
  
  /**
   * Get ego network around a paper
   * @param {string} doi - Center paper DOI
   * @param {number} depth - Network depth (1 or 2)
   * @returns {Promise<Object>} Ego network with nodes and edges
   */
  getEgoNetwork: (doi, depth = 1) => get('/ego', { doi, depth }),
};

/**
 * Search API endpoints
 */
export const search = {
  /**
   * Search for papers
   * @param {string} query - Search query
   * @param {string} field - Field to search ('auto', 'title', or 'doi')
   * @param {number} topK - Number of results
   * @returns {Promise<Object>} Search results
   */
  findPapers: (query, field = 'auto', topK = 20) => 
    get('/find', { query, field, top_k: topK }),
  
  /**
   * Find papers nearby a query paper
   * @param {string} query - Paper DOI or title
   * @param {number} k - Number of nearby papers
   * @returns {Promise<Object>} Nearby papers
   */
  findNearby: (query, k = 20) => 
    get('/find/nearby', { query, k }),
};

/**
 * Export API endpoints
 */
export const exports = {
  /**
   * Get initial NDJSON metadata
   * @returns {Promise<Object>} Metadata with counts
   */
  getInitialMeta: () => get('/export/ndjson/initial/meta'),
  
  /**
   * Stream initial NDJSON data
   * @returns {AsyncGenerator<Object>} Stream of nodes and edges
   */
  streamInitial: () => streamNDJSON('/export/initial.ndjson'),
  
  /**
   * Get paginated JSON export
   * @param {Object} params - Pagination parameters
   * @returns {Promise<Object>} Paginated data
   */
  getJsonExport: ({ nodesOffset = 0, nodesLimit = 1000, edgesOffset = 0, edgesLimit = 1000 } = {}) =>
    get('/export/json', {
      nodes_offset: nodesOffset,
      nodes_limit: nodesLimit,
      edges_offset: edgesOffset,
      edges_limit: edgesLimit,
    }),
};

/**
 * Graph API endpoints
 */
export const graph = {
  /**
   * Generate reading list
   * @param {Object} params - Reading list parameters
   * @returns {Promise<Object>} Reading list
   */
  getReadingList: ({
    center,
    kRegion = 1000,
    depthRefs = 1,
    yearFrom = null,
    minCites = 4,
    weightDistance = 0.5,
    topN = 100,
  }) => {
    const params = {
      center,
      k_region: kRegion,
      depth_refs: depthRefs,
      min_cites: minCites,
      weight_distance: weightDistance,
      top_n: topN,
    };
    
    if (yearFrom !== null) {
      params.year_from = yearFrom;
    }
    
    return get('/reading_list', params);
  },
};

/**
 * Health check endpoint
 */
export const health = {
  /**
   * Check API health
   * @returns {Promise<Object>} Health status
   */
  check: () => get('/health'),
};

// Default export with all endpoints
export default {
  clusters,
  papers,
  search,
  exports,
  graph,
  health,
};

