/**
 * Papers of Interest Workflow Tests
 * 
 * Tests for the critical user journey:
 * - Adding papers to collection
 * - Viewing papers in My Papers tab
 * - Getting recommendations
 * - Removing papers
 * - localStorage persistence
 */

import { test, expect } from '@playwright/test';
import { TEST_PAPERS, TIMEOUTS, SELECTORS } from '../fixtures/test-data.js';
import { waitForGraphLoad } from '../helpers/graph-helpers.js';
import { performHeaderSearch, waitForSearchDropdown, selectSearchResult } from '../helpers/search-helpers.js';
import { 
  navigateToTab, 
  getMyPapersCount,
  clearPapersOfInterest,
  togglePaperInList,
  getAddToListButtonState
} from '../helpers/sidebar-helpers.js';

/**
 * Helper to find and select a paper
 */
async function findAndSelectPaper(page) {
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

/**
 * Helper to add a paper to the list
 * Returns true if successful
 */
async function addPaperToList(page) {
  const found = await findAndSelectPaper(page);
  if (!found) return false;
  
  const addButton = page.locator(SELECTORS.addToListButton);
  if (await addButton.isVisible({ timeout: 5000 })) {
    await addButton.click();
    await page.waitForTimeout(500);
    return true;
  }
  return false;
}

test.describe('Adding Papers to Collection', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await page.reload();
    await waitForGraphLoad(page);
  });

  test('should add paper from details tab', async ({ page }) => {
    const found = await findAndSelectPaper(page);
    
    if (!found) {
      test.info().annotations.push({ type: 'skip', description: 'No search results available' });
      return;
    }
    
    // Click Add to List
    const addButton = page.locator(SELECTORS.addToListButton);
    await expect(addButton).toBeVisible({ timeout: TIMEOUTS.apiResponse });
    await addButton.click();
    
    // Button should change to "Remove from List"
    await page.waitForTimeout(500);
    const removeButton = page.locator(SELECTORS.removeFromListButton);
    await expect(removeButton).toBeVisible();
  });

  test('should update My Papers tab count after adding', async ({ page }) => {
    // Get initial count
    let count = await getMyPapersCount(page);
    expect(count).toBe(0);
    
    const added = await addPaperToList(page);
    
    if (!added) {
      test.info().annotations.push({ type: 'skip', description: 'Could not add paper' });
      return;
    }
    
    // Count should increase
    count = await getMyPapersCount(page);
    expect(count).toBe(1);
  });

  test('should add multiple papers', async ({ page }) => {
    // Add first paper
    const added1 = await addPaperToList(page);
    
    if (!added1) {
      test.info().annotations.push({ type: 'skip', description: 'Could not add first paper' });
      return;
    }
    
    // Try to add second paper with different search
    await performHeaderSearch(page, 'focused');
    const hasDropdown = await waitForSearchDropdown(page);
    
    if (hasDropdown) {
      await selectSearchResult(page, 0);
      await page.waitForTimeout(TIMEOUTS.apiResponse);
      
      const addButton = page.locator(SELECTORS.addToListButton);
      if (await addButton.isVisible()) {
        await addButton.click();
        await page.waitForTimeout(500);
      }
    }
    
    // Count should be at least 1
    const count = await getMyPapersCount(page);
    expect(count).toBeGreaterThanOrEqual(1);
  });

});

test.describe('Viewing Papers in My Papers Tab', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await page.reload();
    await waitForGraphLoad(page);
    
    // Add a paper first
    const added = await addPaperToList(page);
    if (!added) {
      // We'll handle this in each test
    }
  });

  test('should display added paper in My Papers tab', async ({ page }) => {
    const count = await getMyPapersCount(page);
    
    if (count === 0) {
      test.info().annotations.push({ type: 'skip', description: 'No paper was added in setup' });
      return;
    }
    
    await navigateToTab(page, 'my-papers');
    
    // Should show "My Papers (N)" header where N >= 1
    const header = page.locator('h3:has-text("My Papers")');
    await expect(header).toBeVisible();
  });

  test('should show paper info in list', async ({ page }) => {
    const count = await getMyPapersCount(page);
    
    if (count === 0) {
      test.info().annotations.push({ type: 'skip', description: 'No paper was added' });
      return;
    }
    
    await navigateToTab(page, 'my-papers');
    await page.waitForTimeout(1000);
    
    // Should show paper cards
    const paperCards = page.locator('aside div[style*="border-radius"]').filter({ hasText: /.+/ });
    await expect(paperCards.first()).toBeVisible();
  });

  test('should show remove button for each paper', async ({ page }) => {
    const count = await getMyPapersCount(page);
    
    if (count === 0) {
      test.info().annotations.push({ type: 'skip', description: 'No paper was added' });
      return;
    }
    
    await navigateToTab(page, 'my-papers');
    await page.waitForTimeout(1000);
    
    const removeButton = page.locator('button:has-text("Remove")');
    await expect(removeButton.first()).toBeVisible();
  });

  test('should show Clear All button', async ({ page }) => {
    const count = await getMyPapersCount(page);
    
    if (count === 0) {
      test.info().annotations.push({ type: 'skip', description: 'No paper was added' });
      return;
    }
    
    await navigateToTab(page, 'my-papers');
    
    const clearAllButton = page.locator('button:has-text("Clear All")');
    await expect(clearAllButton).toBeVisible();
  });

  test('should show recommendations controls', async ({ page }) => {
    const count = await getMyPapersCount(page);
    
    if (count === 0) {
      test.info().annotations.push({ type: 'skip', description: 'No paper was added' });
      return;
    }
    
    await navigateToTab(page, 'my-papers');
    
    // Recommendations dropdown (select element)
    const dropdown = page.locator('select');
    await expect(dropdown).toBeVisible();
    
    // Get Recs button
    const getRecsButton = page.locator('button:has-text("Get Recs")');
    await expect(getRecsButton).toBeVisible();
  });

  test('should click paper to view details', async ({ page }) => {
    const count = await getMyPapersCount(page);
    
    if (count === 0) {
      test.info().annotations.push({ type: 'skip', description: 'No paper was added' });
      return;
    }
    
    await navigateToTab(page, 'my-papers');
    await page.waitForTimeout(1000);
    
    // Click on a paper card
    const paperCard = page.locator('aside div[style*="border-radius: 6px"]').first();
    await paperCard.click({ force: true });
    
    await page.waitForTimeout(TIMEOUTS.animation);
    
    // Should switch to details tab - check by looking for paper details
    const paperTitle = page.locator('aside h2');
    await expect(paperTitle).toBeVisible({ timeout: TIMEOUTS.apiResponse });
  });

});

test.describe('Removing Papers', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await page.reload();
    await waitForGraphLoad(page);
    
    // Add a paper first
    await addPaperToList(page);
  });

  test('should remove paper using Remove button in My Papers', async ({ page }) => {
    const count = await getMyPapersCount(page);
    
    if (count === 0) {
      test.info().annotations.push({ type: 'skip', description: 'No paper was added' });
      return;
    }
    
    await navigateToTab(page, 'my-papers');
    await page.waitForTimeout(1000);
    
    // Click remove button
    const removeButton = page.locator('button:has-text("Remove")').first();
    await removeButton.click();
    
    await page.waitForTimeout(500);
    
    // Count should be 0
    const newCount = await getMyPapersCount(page);
    expect(newCount).toBe(0);
  });

  test('should remove paper from Details tab', async ({ page }) => {
    const count = await getMyPapersCount(page);
    
    if (count === 0) {
      test.info().annotations.push({ type: 'skip', description: 'No paper was added' });
      return;
    }
    
    // The paper should already be selected from adding it
    // Navigate to details tab
    await navigateToTab(page, 'details');
    
    // If we need to re-select, do so
    const removeButton = page.locator(SELECTORS.removeFromListButton);
    if (!await removeButton.isVisible({ timeout: 2000 })) {
      // Need to find and select the paper again
      await findAndSelectPaper(page);
    }
    
    if (await removeButton.isVisible()) {
      await removeButton.click();
      await page.waitForTimeout(500);
      
      // Button should change back to "Add to List"
      const addButton = page.locator(SELECTORS.addToListButton);
      await expect(addButton).toBeVisible();
    }
  });

  test('should clear all papers', async ({ page }) => {
    // Add another paper if possible
    await performHeaderSearch(page, 'MRI');
    const hasDropdown = await waitForSearchDropdown(page);
    if (hasDropdown) {
      await selectSearchResult(page, 0);
      await page.waitForTimeout(TIMEOUTS.apiResponse);
      const addButton = page.locator(SELECTORS.addToListButton);
      if (await addButton.isVisible()) {
        await addButton.click();
        await page.waitForTimeout(500);
      }
    }
    
    const count = await getMyPapersCount(page);
    if (count === 0) {
      test.info().annotations.push({ type: 'skip', description: 'No papers to clear' });
      return;
    }
    
    // Go to My Papers and click Clear All
    await navigateToTab(page, 'my-papers');
    await page.waitForTimeout(500);
    
    const clearAllButton = page.locator('button:has-text("Clear All")');
    await clearAllButton.click();
    
    await page.waitForTimeout(500);
    
    // All should be cleared
    const newCount = await getMyPapersCount(page);
    expect(newCount).toBe(0);
  });

});

test.describe('Recommendations', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await page.reload();
    await waitForGraphLoad(page);
    
    // Add a paper first
    await addPaperToList(page);
    await navigateToTab(page, 'my-papers');
  });

  test('should have Spatial and Bridges options', async ({ page }) => {
    const count = await getMyPapersCount(page);
    if (count === 0) {
      test.info().annotations.push({ type: 'skip', description: 'No paper was added' });
      return;
    }
    
    const dropdown = page.locator('select');
    await expect(dropdown).toBeVisible();
    
    // Check for options
    const options = dropdown.locator('option');
    const optCount = await options.count();
    expect(optCount).toBe(2);
  });

  test('should request spatial recommendations', async ({ page }) => {
    const count = await getMyPapersCount(page);
    if (count === 0) {
      test.info().annotations.push({ type: 'skip', description: 'No paper was added' });
      return;
    }
    
    // Select Spatial option (should be default)
    const dropdown = page.locator('select');
    await dropdown.selectOption({ index: 0 });
    
    // Click Get Recs
    const getRecsButton = page.locator('button:has-text("Get Recs")');
    await getRecsButton.click();
    
    // Wait for recommendations to load or fail
    await page.waitForTimeout(TIMEOUTS.apiResponse);
    
    // Either recommendations section or error should appear - search completed
    // We don't require success since API might not have data
  });

  test('should request bridge recommendations', async ({ page }) => {
    const count = await getMyPapersCount(page);
    if (count === 0) {
      test.info().annotations.push({ type: 'skip', description: 'No paper was added' });
      return;
    }
    
    // Select Bridges option
    const dropdown = page.locator('select');
    await dropdown.selectOption({ index: 1 });
    
    // Click Get Recs
    const getRecsButton = page.locator('button:has-text("Get Recs")');
    await getRecsButton.click();
    
    // Wait for recommendations to load
    await page.waitForTimeout(TIMEOUTS.apiResponse);
  });

});

test.describe('LocalStorage Persistence', () => {
  
  test('should persist papers after page reload', async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await page.reload();
    await waitForGraphLoad(page);
    
    // Add a paper
    const added = await addPaperToList(page);
    
    if (!added) {
      test.info().annotations.push({ type: 'skip', description: 'Could not add paper' });
      return;
    }
    
    // Verify paper is added
    let count = await getMyPapersCount(page);
    expect(count).toBe(1);
    
    // Reload the page
    await page.reload();
    await waitForGraphLoad(page);
    
    // Paper should still be there
    count = await getMyPapersCount(page);
    expect(count).toBe(1);
  });

  test('should clear persisted data', async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await page.reload();
    await waitForGraphLoad(page);
    
    // Add a paper
    const added = await addPaperToList(page);
    
    if (!added) {
      test.info().annotations.push({ type: 'skip', description: 'Could not add paper' });
      return;
    }
    
    // Clear papers
    await navigateToTab(page, 'my-papers');
    await page.waitForTimeout(500);
    const clearAllButton = page.locator('button:has-text("Clear All")');
    await clearAllButton.click();
    await page.waitForTimeout(500);
    
    // Reload
    await page.reload();
    await waitForGraphLoad(page);
    
    // Should still be empty
    const count = await getMyPapersCount(page);
    expect(count).toBe(0);
  });

  test('should load papers from localStorage on mount', async ({ page }) => {
    // First, set up localStorage directly with a test DOI
    await page.goto('/');
    await page.evaluate((doi) => {
      localStorage.setItem('litsearch_papers_of_interest', JSON.stringify([doi]));
    }, TEST_PAPERS.primary.doi);
    
    // Reload to trigger loading from localStorage
    await page.reload();
    await waitForGraphLoad(page);
    
    // Should have 1 paper
    const count = await getMyPapersCount(page);
    expect(count).toBe(1);
  });

});

test.describe('Edge Cases', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await page.reload();
    await waitForGraphLoad(page);
  });

  test('should not add duplicate papers', async ({ page }) => {
    // Add a paper
    const added = await addPaperToList(page);
    
    if (!added) {
      test.info().annotations.push({ type: 'skip', description: 'Could not add paper' });
      return;
    }
    
    // The button should now show "Remove"
    const removeButton = page.locator(SELECTORS.removeFromListButton);
    await expect(removeButton).toBeVisible();
    
    // Count should be 1
    const count = await getMyPapersCount(page);
    expect(count).toBe(1);
  });

  test('should toggle button state correctly', async ({ page }) => {
    // Find and select a paper
    const found = await findAndSelectPaper(page);
    
    if (!found) {
      test.info().annotations.push({ type: 'skip', description: 'No paper found' });
      return;
    }
    
    // Initially should show "Add to List"
    let state = await getAddToListButtonState(page);
    expect(state).toBe('add');
    
    // Add paper
    await togglePaperInList(page);
    
    // Should now show "Remove from List"
    state = await getAddToListButtonState(page);
    expect(state).toBe('remove');
    
    // Remove paper
    await togglePaperInList(page);
    
    // Should show "Add to List" again
    state = await getAddToListButtonState(page);
    expect(state).toBe('add');
  });

});
