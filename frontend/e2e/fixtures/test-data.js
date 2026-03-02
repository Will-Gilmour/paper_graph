/**
 * Test Data for E2E Tests
 * 
 * Known papers from the MRgFUS Thalamotomy Papers graph
 * These papers are guaranteed to exist in the test dataset
 */

export const TEST_PAPERS = {
  // Primary test paper - highly cited, well-known paper
  primary: {
    doi: '10.1056/nejmoa1600159',
    title: 'A Randomized Trial of Focused Ultrasound Thalamotomy for Essential Tremor',
    // Partial match for flexible assertions
    titleContains: 'Randomized Trial of Focused Ultrasound',
  },
  
  // Secondary test paper - systematic review
  secondary: {
    doi: '10.1002/mds.30188',
    title: 'Efficacy and Safety of Magnetic Resonance-Guided Focused Ultrasound Thalamotomy in Essential Tremor: A Systematic Review and Metanalysis',
    titleContains: 'Systematic Review and Metanalysis',
  },
};

// Search terms that should return results
export const SEARCH_TERMS = {
  keyword: 'tremor',
  author: 'Elias',
  broad: 'ultrasound thalamotomy',
};

// Expected graph name for verification
export const EXPECTED_GRAPH_NAME = 'MRgFUS Thalamotomy Papers';

// Timeouts for various operations
export const TIMEOUTS = {
  graphLoad: 30000,      // Graph can take a while to load
  search: 10000,         // Search operations
  navigation: 5000,      // Tab switches and navigation
  animation: 2000,       // UI animations
  apiResponse: 15000,    // API response waiting
};

// Selectors used across tests
export const SELECTORS = {
  // Header
  headerSearchInput: 'input[placeholder="Search DOI or keyword…"]',
  headerSearchButton: 'header button[type="submit"]',
  searchDropdown: 'ul[style*="position: absolute"]',
  
  // Sidebar tabs (more specific to avoid header/graph-switcher conflicts)
  detailsTab: 'aside >> button:text-is("Details")',
  searchTab: 'aside >> button:text-is("Search")',
  clustersTab: 'aside >> button:text-is("Clusters")',
  myPapersTab: 'aside >> button:text-matches("My Papers")',
  
  // Graph
  graphContainer: '.graph-container',
  graphCanvas: '.graph-container canvas.sigma-nodes', // Sigma's node canvas
  loadingOverlay: 'text=Nodes:',
  
  // Filter panel
  filterHeader: '.filter-header',
  filterPanel: '.filter-panel',
  
  // Details pane
  paperTitle: 'h2',
  addToListButton: 'button:has-text("Add to List")',
  removeFromListButton: 'button:has-text("Remove from List")',
  
  // Search pane
  titleSearchInput: 'input[placeholder*="tremor"]',
  authorSearchInput: 'input[placeholder*="Smith"]',
  searchPapersButton: 'button:has-text("Search Papers")',
  
  // Clusters pane
  selectAllButton: 'button:has-text("Select all")',
  clearButton: 'aside button:has-text("Clear"):not(:has-text("All"))',
  
  // My Papers pane
  clearAllButton: 'button:has-text("Clear All")',
  getRecsButton: 'button:has-text("Get Recs")',
  
  // Graph switcher
  graphSwitcher: '.graph-switcher',
  switcherButton: '.switcher-button',
};

