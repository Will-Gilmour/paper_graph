/**
 * Sidebar Navigation Helper Utilities
 * 
 * Helper functions for interacting with the sidebar tabs and panes
 */

import { TIMEOUTS, SELECTORS } from '../fixtures/test-data.js';

/**
 * Navigate to a specific sidebar tab
 */
export async function navigateToTab(page, tabName) {
  const tabMap = {
    'details': SELECTORS.detailsTab,
    'search': SELECTORS.searchTab,
    'clusters': SELECTORS.clustersTab,
    'my-papers': SELECTORS.myPapersTab,
    'mypapers': SELECTORS.myPapersTab,
  };
  
  const selector = tabMap[tabName.toLowerCase()];
  if (!selector) {
    throw new Error(`Unknown tab: ${tabName}`);
  }
  
  await page.click(selector);
  await page.waitForTimeout(300); // Wait for tab transition
}

/**
 * Check which tab is currently active
 */
export async function getActiveTab(page) {
  // Active tab has forest-green background (#228B22)
  const tabs = ['Details', 'Search', 'Clusters', 'My Papers'];
  
  for (const tab of tabs) {
    const button = page.locator(`button:has-text("${tab}")`);
    const style = await button.getAttribute('style');
    // Check if this tab has the active styling (green background)
    if (style && style.includes('rgb(34, 139, 34)')) {
      return tab.toLowerCase().replace(' ', '-');
    }
  }
  
  return null;
}

/**
 * Check if the details pane shows the "Select a node" prompt
 */
export async function isShowingSelectNodePrompt(page) {
  const prompt = page.locator('text=Select a node to see details');
  return await prompt.isVisible();
}

/**
 * Check if paper details are displayed
 */
export async function isPaperDetailsVisible(page) {
  // Paper details have an h2 with the title
  const title = page.locator('aside h2');
  return await title.isVisible();
}

/**
 * Get the currently displayed paper title
 */
export async function getPaperTitle(page) {
  const title = page.locator('aside h2');
  if (await title.isVisible()) {
    return await title.textContent();
  }
  return null;
}

/**
 * Get paper metadata from details pane
 */
export async function getPaperMetadata(page) {
  const metadata = {};
  
  // Try to get DOI
  const doiLink = page.locator('a[href*="doi.org"]');
  if (await doiLink.isVisible()) {
    const href = await doiLink.getAttribute('href');
    metadata.doi = href?.replace('https://doi.org/', '');
  }
  
  // Get title
  const title = page.locator('aside h2');
  if (await title.isVisible()) {
    metadata.title = await title.textContent();
  }
  
  return metadata;
}

/**
 * Check if "Add to List" button is visible and get its state
 */
export async function getAddToListButtonState(page) {
  const addButton = page.locator(SELECTORS.addToListButton);
  const removeButton = page.locator(SELECTORS.removeFromListButton);
  
  if (await addButton.isVisible()) {
    return 'add';
  } else if (await removeButton.isVisible()) {
    return 'remove';
  }
  return null;
}

/**
 * Click Add to List / Remove from List button
 */
export async function togglePaperInList(page) {
  const addButton = page.locator(SELECTORS.addToListButton);
  const removeButton = page.locator(SELECTORS.removeFromListButton);
  
  if (await addButton.isVisible()) {
    await addButton.click();
  } else if (await removeButton.isVisible()) {
    await removeButton.click();
  }
  
  await page.waitForTimeout(300); // Wait for state update
}

/**
 * Get the count from My Papers tab badge
 */
export async function getMyPapersCount(page) {
  // Use more specific selector for the sidebar My Papers tab
  const tab = page.locator('aside >> button:text-matches("My Papers")');
  const text = await tab.textContent();
  
  // Extract number from "My Papers (N)" format
  const match = text?.match(/\((\d+)\)/);
  if (match) {
    return parseInt(match[1]);
  }
  return 0;
}

/**
 * Clear localStorage to reset Papers of Interest
 */
export async function clearPapersOfInterest(page) {
  await page.evaluate(() => {
    localStorage.removeItem('litsearch_papers_of_interest');
  });
}

/**
 * Get cluster list from clusters pane
 */
export async function getClusterList(page) {
  await navigateToTab(page, 'clusters');
  
  // Get all cluster labels
  const labels = page.locator('aside label');
  const count = await labels.count();
  const clusters = [];
  
  for (let i = 0; i < count; i++) {
    const text = await labels.nth(i).textContent();
    clusters.push(text);
  }
  
  return clusters;
}

/**
 * Toggle cluster checkbox
 */
export async function toggleCluster(page, clusterName) {
  const label = page.locator(`label:has-text("${clusterName}")`);
  await label.click();
}

/**
 * Wait for search results to load in search pane
 */
export async function waitForSearchResults(page) {
  // Wait for "Found X papers" text
  await page.waitForSelector('text=/Found \\d+ paper/', { 
    timeout: TIMEOUTS.search 
  });
}

/**
 * Get search results count
 */
export async function getSearchResultsCount(page) {
  const countText = page.locator('text=/Found \\d+ paper/');
  if (await countText.isVisible()) {
    const text = await countText.textContent();
    const match = text?.match(/Found (\d+) paper/);
    if (match) {
      return parseInt(match[1]);
    }
  }
  return 0;
}

