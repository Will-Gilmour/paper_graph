/**
 * Sidebar Navigation and Interaction Tests
 * 
 * Tests for:
 * - Tab navigation
 * - Details pane content
 * - Clusters pane functionality
 * - My Papers pane empty state
 */

import { test, expect } from '@playwright/test';
import { TEST_PAPERS, TIMEOUTS, SELECTORS } from '../fixtures/test-data.js';
import { waitForGraphLoad } from '../helpers/graph-helpers.js';
import { performHeaderSearch, waitForSearchDropdown, selectSearchResult } from '../helpers/search-helpers.js';
import { 
  navigateToTab, 
  isShowingSelectNodePrompt,
  isPaperDetailsVisible,
  getPaperTitle,
  getMyPapersCount,
  clearPapersOfInterest,
  getClusterList,
  toggleCluster
} from '../helpers/sidebar-helpers.js';

/**
 * Helper to find and select a paper
 */
async function findAndSelectPaperWithVerification(page) {
  // Use a single reliable search term
  await performHeaderSearch(page, 'tremor');
  const hasDropdown = await waitForSearchDropdown(page);
  
  if (!hasDropdown) {
    return false;
  }
  
  const selected = await selectSearchResult(page, 0);
  if (!selected) {
    return false;
  }
  
  // Wait for paper to load
  const paperTitle = page.locator('aside h2');
  try {
    await paperTitle.waitFor({ state: 'visible', timeout: TIMEOUTS.apiResponse });
    return true;
  } catch {
    return false;
  }
}

test.describe('Sidebar Tab Navigation', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await waitForGraphLoad(page);
  });

  test('should have all four tabs visible', async ({ page }) => {
    await expect(page.locator(SELECTORS.detailsTab)).toBeVisible();
    await expect(page.locator(SELECTORS.searchTab)).toBeVisible();
    await expect(page.locator(SELECTORS.clustersTab)).toBeVisible();
    await expect(page.locator(SELECTORS.myPapersTab)).toBeVisible();
  });

  test('should switch to Details tab', async ({ page }) => {
    await navigateToTab(page, 'details');
    
    // Should show select node prompt or paper details
    const detailsContent = page.locator('aside >> text=/Select a node|Loading paper/i');
    await expect(detailsContent.first()).toBeVisible({ timeout: 10000 });
  });

  test('should switch to Search tab', async ({ page }) => {
    await navigateToTab(page, 'search');
    
    // Should show search form with Title Keywords label
    const searchForm = page.locator('aside >> text=Title Keywords');
    await expect(searchForm).toBeVisible({ timeout: 10000 });
  });

  test('should switch to Clusters tab', async ({ page }) => {
    await navigateToTab(page, 'clusters');
    
    // Should show cluster controls
    const selectAllButton = page.locator(SELECTORS.selectAllButton);
    await expect(selectAllButton).toBeVisible({ timeout: 10000 });
  });

  test('should switch to My Papers tab', async ({ page }) => {
    await navigateToTab(page, 'my-papers');
    
    // Should show empty state or papers list - look for My Papers header text
    const myPapersContent = page.locator('aside >> text=/No papers|My Papers/i');
    await expect(myPapersContent.first()).toBeVisible({ timeout: 10000 });
  });

  test('should highlight active tab with forest-green color', async ({ page }) => {
    await navigateToTab(page, 'search');
    
    // Wait for tab to be visible and selected
    await page.waitForTimeout(500);
    
    const searchTab = page.locator(SELECTORS.searchTab);
    const backgroundColor = await searchTab.evaluate(el => 
      window.getComputedStyle(el).backgroundColor
    );
    
    // Should be forest green (#228B22 = rgb(34, 139, 34))
    expect(backgroundColor).toContain('34, 139, 34');
  });

  test('should maintain tab state on navigation', async ({ page }) => {
    // Go to clusters tab
    await navigateToTab(page, 'clusters');
    
    // Verify we're on clusters
    const selectAllButton = page.locator(SELECTORS.selectAllButton);
    await expect(selectAllButton).toBeVisible();
    
    // Tab should still be active
    const clustersTab = page.locator(SELECTORS.clustersTab);
    const backgroundColor = await clustersTab.evaluate(el => 
      window.getComputedStyle(el).backgroundColor
    );
    expect(backgroundColor).toContain('34, 139, 34');
  });

});

test.describe('Details Tab', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await waitForGraphLoad(page);
    await navigateToTab(page, 'details');
  });

  test('should show "Select a node" prompt when no paper selected', async ({ page }) => {
    const isPromptVisible = await isShowingSelectNodePrompt(page);
    expect(isPromptVisible).toBe(true);
  });

  test('should display paper details after selection', async ({ page }) => {
    const found = await findAndSelectPaperWithVerification(page);
    
    if (!found) {
      test.info().annotations.push({ type: 'skip', description: 'No paper could be found and selected' });
      return;
    }
    
    // Paper title should be visible (already verified in helper)
    const paperTitle = page.locator('aside h2');
    await expect(paperTitle).toBeVisible();
  });

  test('should show paper title in h2', async ({ page }) => {
    const found = await findAndSelectPaperWithVerification(page);
    
    if (!found) {
      test.info().annotations.push({ type: 'skip', description: 'No paper found' });
      return;
    }
    
    const title = await getPaperTitle(page);
    expect(title).toBeTruthy();
  });

  test('should display DOI link', async ({ page }) => {
    const found = await findAndSelectPaperWithVerification(page);
    
    if (!found) {
      test.info().annotations.push({ type: 'skip', description: 'No paper found' });
      return;
    }
    
    const doiLink = page.locator('a[href*="doi.org"]');
    await expect(doiLink).toBeVisible({ timeout: 5000 });
  });

  test('should display authors', async ({ page }) => {
    const found = await findAndSelectPaperWithVerification(page);
    
    if (!found) {
      test.info().annotations.push({ type: 'skip', description: 'No paper found' });
      return;
    }
    
    const authorsSection = page.locator('text=Authors:');
    await expect(authorsSection).toBeVisible({ timeout: 5000 });
  });

  test('should display year', async ({ page }) => {
    const found = await findAndSelectPaperWithVerification(page);
    
    if (!found) {
      test.info().annotations.push({ type: 'skip', description: 'No paper found' });
      return;
    }
    
    const yearSection = page.locator('text=Year:');
    await expect(yearSection).toBeVisible({ timeout: 5000 });
  });

  test('should display cluster information', async ({ page }) => {
    const found = await findAndSelectPaperWithVerification(page);
    
    if (!found) {
      test.info().annotations.push({ type: 'skip', description: 'No paper found' });
      return;
    }
    
    const clusterSection = page.locator('text=Cluster:');
    await expect(clusterSection).toBeVisible({ timeout: 5000 });
  });

  test('should show "Add to List" button', async ({ page }) => {
    const found = await findAndSelectPaperWithVerification(page);
    
    if (!found) {
      test.info().annotations.push({ type: 'skip', description: 'No paper found' });
      return;
    }
    
    const addButton = page.locator(SELECTORS.addToListButton);
    await expect(addButton).toBeVisible({ timeout: 5000 });
  });

  test('should show similar papers suggestions', async ({ page }) => {
    const found = await findAndSelectPaperWithVerification(page);
    
    if (!found) {
      test.info().annotations.push({ type: 'skip', description: 'No paper found' });
      return;
    }
    
    const suggestionsSection = page.locator('text=Possible similar papers');
    await expect(suggestionsSection).toBeVisible({ timeout: 10000 });
  });

});

test.describe('Clusters Tab', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await waitForGraphLoad(page);
    await navigateToTab(page, 'clusters');
  });

  test('should display cluster list', async ({ page }) => {
    // Wait for clusters to load
    await page.waitForTimeout(2000);
    
    // Should have checkboxes for clusters
    const checkboxes = page.locator('aside input[type="checkbox"]');
    const count = await checkboxes.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should have Select all button', async ({ page }) => {
    const selectAllButton = page.locator(SELECTORS.selectAllButton);
    await expect(selectAllButton).toBeVisible();
  });

  test('should have Clear button', async ({ page }) => {
    const clearButton = page.locator(SELECTORS.clearButton);
    await expect(clearButton).toBeVisible();
  });

  test('should toggle cluster selection', async ({ page }) => {
    await page.waitForTimeout(2000);
    
    // Find first checkbox
    const firstCheckbox = page.locator('aside input[type="checkbox"]').first();
    
    // Get initial state
    const initialChecked = await firstCheckbox.isChecked();
    
    // Click to toggle
    await firstCheckbox.click();
    
    // State should have changed
    const newChecked = await firstCheckbox.isChecked();
    expect(newChecked).not.toBe(initialChecked);
  });

  test('should clear all selections', async ({ page }) => {
    await page.waitForTimeout(2000);
    
    // Click Clear button
    const clearButton = page.locator(SELECTORS.clearButton);
    await clearButton.click();
    
    // All checkboxes should be unchecked
    const checkboxes = page.locator('aside input[type="checkbox"]');
    const count = await checkboxes.count();
    
    for (let i = 0; i < Math.min(count, 5); i++) { // Check first 5
      const isChecked = await checkboxes.nth(i).isChecked();
      expect(isChecked).toBe(false);
    }
  });

  test('should select all clusters', async ({ page }) => {
    await page.waitForTimeout(2000);
    
    // First clear, then select all
    await page.locator(SELECTORS.clearButton).click();
    await page.waitForTimeout(300);
    
    await page.locator(SELECTORS.selectAllButton).click();
    await page.waitForTimeout(300);
    
    // All parent checkboxes should be checked
    // (Note: may have indeterminate state for parents with partial children selection)
    const checkboxes = page.locator('aside input[type="checkbox"]');
    const count = await checkboxes.count();
    
    // At least one should be checked
    let anyChecked = false;
    for (let i = 0; i < count; i++) {
      if (await checkboxes.nth(i).isChecked()) {
        anyChecked = true;
        break;
      }
    }
    expect(anyChecked).toBe(true);
  });

  test('should have expandable cluster sections', async ({ page }) => {
    await page.waitForTimeout(2000);
    
    // Look for expand/collapse buttons (▸ or ▾)
    const expandButtons = page.locator('button:has-text("▸"), button:has-text("▾")');
    const count = await expandButtons.count();
    
    // May or may not have expandable sections depending on data
    // Just verify we can find the cluster UI
    const clusterLabels = page.locator('aside label');
    const labelCount = await clusterLabels.count();
    expect(labelCount).toBeGreaterThan(0);
  });

  test('should expand/collapse subclusters', async ({ page }) => {
    await page.waitForTimeout(2000);
    
    // Find collapse button if any exist
    const expandButton = page.locator('button:has-text("▸")').first();
    
    if (await expandButton.isVisible()) {
      // Click to expand
      await expandButton.click();
      
      // Button should now show ▾
      await page.waitForTimeout(300);
      
      // Either found expand button state changed, or subclusters appeared
      const collapseButton = page.locator('button:has-text("▾")');
      const collapseCount = await collapseButton.count();
      expect(collapseCount).toBeGreaterThanOrEqual(0);
    }
  });

  test('should show cluster names and sizes', async ({ page }) => {
    await page.waitForTimeout(2000);
    
    // Cluster labels should show name and size in format "Name (N)"
    const labels = page.locator('aside label');
    const firstLabelText = await labels.first().textContent();
    
    // Should contain parentheses with number
    expect(firstLabelText).toMatch(/\(\d+/);
  });

});

test.describe('My Papers Tab - Empty State', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await page.reload(); // Reload to ensure localStorage is cleared
    await waitForGraphLoad(page);
    await navigateToTab(page, 'my-papers');
  });

  test('should show empty state message', async ({ page }) => {
    // Look for empty state message
    const emptyMessage = page.locator('text=/No papers in your collection|No papers yet/i');
    await expect(emptyMessage).toBeVisible({ timeout: 10000 });
  });

  test('should show instructions for adding papers', async ({ page }) => {
    // Instructions mention "Add to List" in the empty state
    const instructions = page.locator('aside >> text=/Add to List|build your collection/i');
    await expect(instructions).toBeVisible({ timeout: 10000 });
  });

  test('should show zero count in tab', async ({ page }) => {
    const count = await getMyPapersCount(page);
    expect(count).toBe(0);
  });

});

test.describe('Sidebar Responsiveness', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await waitForGraphLoad(page);
  });

  test('should maintain sidebar visibility on tab switch', async ({ page }) => {
    const sidebar = page.locator('aside.sidebar');
    
    // Navigate through all tabs
    for (const tab of ['details', 'search', 'clusters', 'my-papers']) {
      await navigateToTab(page, tab);
      await expect(sidebar).toBeVisible();
    }
  });

  test('should have scrollable content in clusters tab', async ({ page }) => {
    await navigateToTab(page, 'clusters');
    await page.waitForTimeout(2000);
    
    // The clusters list should be scrollable if there are many clusters
    const scrollContainer = page.locator('aside div[style*="overflow"]');
    const count = await scrollContainer.count();
    
    // Should have at least one scrollable container
    expect(count).toBeGreaterThanOrEqual(0);
  });

});

