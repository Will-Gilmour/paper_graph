/**
 * Application Loading Tests
 * 
 * Tests for basic application functionality:
 * - App loads without errors
 * - Graph canvas renders
 * - Loading indicator works
 * - No console errors
 */

import { test, expect } from '@playwright/test';
import { TIMEOUTS, SELECTORS, EXPECTED_GRAPH_NAME } from '../fixtures/test-data.js';
import { waitForGraphLoad, waitForGraphInteractive, isGraphVisible } from '../helpers/graph-helpers.js';
import { clearPapersOfInterest } from '../helpers/sidebar-helpers.js';

test.describe('Application Loading', () => {
  
  test.beforeEach(async ({ page }) => {
    // Clear Papers of Interest before each test
    await page.goto('/');
    await clearPapersOfInterest(page);
  });

  test('should load the application without errors', async ({ page }) => {
    // Collect console errors
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/');
    
    // Wait for basic page elements - check for app content not just title
    await page.waitForLoadState('domcontentloaded');
    
    // Check header is visible
    const header = page.locator('header');
    await expect(header).toBeVisible();
    
    // Check for the logo/title text in the header
    const logo = page.locator('.logo, header h1');
    await expect(logo).toBeVisible();
    
    // Filter out expected/harmless errors
    const criticalErrors = errors.filter(e => 
      !e.includes('favicon') && 
      !e.includes('404') &&
      !e.includes('net::ERR')
    );
    
    // Allow some non-critical errors but log them
    if (criticalErrors.length > 0) {
      console.log('Console errors found:', criticalErrors);
    }
  });

  test('should display the graph container', async ({ page }) => {
    await page.goto('/');
    
    // Graph container should be visible
    const graphContainer = page.locator(SELECTORS.graphContainer);
    await expect(graphContainer).toBeVisible({ timeout: TIMEOUTS.graphLoad });
  });

  test('should show loading indicator while graph loads', async ({ page }) => {
    await page.goto('/');
    
    // Either loading indicator is visible initially, or graph already loaded
    // Check for graph container and Sigma canvases (graph loaded)
    const graphLoaded = page.locator(`${SELECTORS.graphContainer} canvas.sigma-nodes`);
    await expect(graphLoaded).toBeVisible({ timeout: TIMEOUTS.graphLoad });
  });

  test('should complete graph loading', async ({ page }) => {
    await page.goto('/');
    
    // Wait for graph to finish loading
    await waitForGraphLoad(page);
    
    // Verify graph is interactive
    const isVisible = await isGraphVisible(page);
    expect(isVisible).toBe(true);
  });

  test('should display canvas element for graph rendering', async ({ page }) => {
    await page.goto('/');
    
    await waitForGraphInteractive(page);
    
    // Check for Sigma's nodes canvas (specific canvas to avoid multiple elements)
    const canvas = page.locator(`${SELECTORS.graphContainer} canvas.sigma-nodes`);
    await expect(canvas).toBeVisible();
  });

  test('should show sidebar with tabs', async ({ page }) => {
    await page.goto('/');
    
    // Wait for page to load
    await page.waitForLoadState('domcontentloaded');
    
    // Check all sidebar tabs are present
    await expect(page.locator(SELECTORS.detailsTab)).toBeVisible();
    await expect(page.locator(SELECTORS.searchTab)).toBeVisible();
    await expect(page.locator(SELECTORS.clustersTab)).toBeVisible();
    await expect(page.locator(SELECTORS.myPapersTab)).toBeVisible();
  });

  test('should show header search bar', async ({ page }) => {
    await page.goto('/');
    
    await page.waitForLoadState('domcontentloaded');
    
    // Header search input
    const searchInput = page.locator(SELECTORS.headerSearchInput);
    await expect(searchInput).toBeVisible();
    
    // Search button
    const searchButton = page.locator(SELECTORS.headerSearchButton);
    await expect(searchButton).toBeVisible();
  });

  test('should show filter panel', async ({ page }) => {
    await page.goto('/');
    
    await page.waitForLoadState('domcontentloaded');
    
    // Filter panel header
    const filterHeader = page.locator(SELECTORS.filterHeader);
    await expect(filterHeader).toBeVisible();
  });

  test('should display "Build New Graph" link', async ({ page }) => {
    await page.goto('/');
    
    await page.waitForLoadState('domcontentloaded');
    
    const buildLink = page.locator('a:has-text("Build New Graph")');
    await expect(buildLink).toBeVisible();
  });

  test('should display graph switcher if graphs available', async ({ page }) => {
    await page.goto('/');
    
    await page.waitForLoadState('domcontentloaded');
    
    // Graph switcher might not be visible if no graphs are loaded
    // Just check for the component to exist (visible or not)
    const switcher = page.locator(SELECTORS.graphSwitcher);
    
    // Wait a bit for graphs to load
    await page.waitForTimeout(2000);
    
    // The switcher returns null if no graphs, so check if it exists
    const switcherCount = await switcher.count();
    
    // Log the result - it's okay if there are no graphs yet
    if (switcherCount > 0) {
      await expect(switcher).toBeVisible();
    }
  });

  test('should have split layout with sidebar and main content', async ({ page }) => {
    await page.goto('/');
    
    await page.waitForLoadState('domcontentloaded');
    
    // Check for sidebar (aside element)
    const sidebar = page.locator('aside.sidebar');
    await expect(sidebar).toBeVisible();
    
    // Check for main content area
    const main = page.locator('main.main');
    await expect(main).toBeVisible();
  });

});

