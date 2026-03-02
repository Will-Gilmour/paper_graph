/**
 * Search Helper Utilities
 * 
 * Helper functions for search operations
 */

import { TIMEOUTS, SELECTORS } from '../fixtures/test-data.js';

/**
 * Perform a search using the header search bar
 */
export async function performHeaderSearch(page, query) {
  const searchInput = page.locator(SELECTORS.headerSearchInput);
  
  // Clear and type
  await searchInput.fill(query);
  
  // Submit the form
  await page.click(SELECTORS.headerSearchButton);
  
  // Wait for results dropdown
  await page.waitForTimeout(500);
}

/**
 * Wait for header search dropdown to appear
 * Returns true if dropdown appeared, false if "No matching" message appeared
 */
export async function waitForSearchDropdown(page) {
  try {
    // Wait for either dropdown or "no results" message
    const result = await Promise.race([
      page.waitForSelector(SELECTORS.searchDropdown, { state: 'visible', timeout: TIMEOUTS.search }).then(() => 'dropdown'),
      page.waitForSelector('text=No matching papers found', { state: 'visible', timeout: TIMEOUTS.search }).then(() => 'no-results'),
    ]);
    return result === 'dropdown';
  } catch {
    // Neither appeared - might still be loading or error
    return false;
  }
}

/**
 * Get search dropdown results
 */
export async function getSearchDropdownResults(page) {
  const dropdown = page.locator(SELECTORS.searchDropdown);
  
  if (!await dropdown.isVisible()) {
    return [];
  }
  
  const items = dropdown.locator('li');
  const count = await items.count();
  const results = [];
  
  for (let i = 0; i < count; i++) {
    const item = items.nth(i);
    const strong = item.locator('strong');
    const small = item.locator('small');
    
    results.push({
      title: await strong.textContent(),
      doi: await small.textContent()
    });
  }
  
  return results;
}

/**
 * Select a result from the search dropdown by index
 * Returns true if selection was successful, false if no results
 */
export async function selectSearchResult(page, index) {
  const dropdown = page.locator(SELECTORS.searchDropdown);
  
  // Check if dropdown is visible
  if (!await dropdown.isVisible()) {
    console.log('No search results found - skipping result selection');
    return false;
  }
  
  const items = dropdown.locator('li');
  const count = await items.count();
  
  if (count === 0 || index >= count) {
    console.log(`Requested index ${index} but only ${count} results available`);
    return false;
  }
  
  await items.nth(index).click();
  
  // Wait for paper to load
  await page.waitForTimeout(TIMEOUTS.animation);
  return true;
}

/**
 * Select a result from the search dropdown by DOI
 */
export async function selectSearchResultByDoi(page, doi) {
  const item = page.locator(`li:has(small:has-text("${doi}"))`);
  await item.click();
  
  // Wait for paper to load
  await page.waitForTimeout(TIMEOUTS.animation);
}

/**
 * Perform a search in the sidebar search pane
 */
export async function performSidebarSearch(page, { title, author, yearMin, yearMax, minCitations }) {
  // Make sure we're on the search tab
  const searchTab = page.locator(SELECTORS.searchTab);
  await searchTab.click();
  await page.waitForTimeout(300);
  
  // Fill in title if provided
  if (title) {
    const titleInput = page.locator('input[placeholder*="tremor"]');
    await titleInput.fill(title);
  }
  
  // Fill in author if provided
  if (author) {
    const authorInput = page.locator('input[placeholder*="Smith"]');
    await authorInput.fill(author);
  }
  
  // Fill in year range if provided
  if (yearMin) {
    const yearMinInput = page.locator('input[placeholder="2000"]');
    await yearMinInput.fill(String(yearMin));
  }
  
  if (yearMax) {
    const yearMaxInput = page.locator('input[placeholder="2025"]');
    await yearMaxInput.fill(String(yearMax));
  }
  
  // Fill in min citations if provided
  if (minCitations) {
    const citationsInput = page.locator('input[placeholder="0"]');
    await citationsInput.fill(String(minCitations));
  }
  
  // Submit search
  const searchButton = page.locator(SELECTORS.searchPapersButton);
  await searchButton.click();
}

/**
 * Clear sidebar search form
 */
export async function clearSidebarSearch(page) {
  const searchTab = page.locator(SELECTORS.searchTab);
  await searchTab.click();
  await page.waitForTimeout(300);
  
  // Clear all inputs
  const inputs = page.locator('aside input[type="text"], aside input[type="number"]');
  const count = await inputs.count();
  
  for (let i = 0; i < count; i++) {
    await inputs.nth(i).fill('');
  }
}

/**
 * Click on a search result in the sidebar
 */
export async function clickSidebarSearchResult(page, index) {
  const results = page.locator('aside div[style*="cursor: pointer"]');
  await results.nth(index).click();
  
  // Wait for details to load
  await page.waitForTimeout(TIMEOUTS.animation);
}

/**
 * Check if search is loading
 */
export async function isSearchLoading(page) {
  const loadingText = page.locator('text=Searching…');
  return await loadingText.isVisible();
}

/**
 * Check for search error message
 */
export async function hasSearchError(page) {
  const errorText = page.locator('text=No matching papers found');
  return await errorText.isVisible();
}

