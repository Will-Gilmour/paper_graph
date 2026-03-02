/**
 * Graph Canvas Helper Utilities
 * 
 * Helper functions for interacting with the Sigma.js graph canvas
 */

import { TIMEOUTS, SELECTORS } from '../fixtures/test-data.js';

/**
 * Wait for the graph to finish loading
 * Waits for the loading overlay to disappear
 */
export async function waitForGraphLoad(page) {
  // Wait for the graph container to exist
  await page.waitForSelector(SELECTORS.graphContainer, { 
    state: 'visible',
    timeout: TIMEOUTS.graphLoad 
  });
  
  // Wait for the loading overlay to disappear (if present)
  // The loading overlay contains "Nodes:" text
  try {
    await page.waitForSelector('text=Nodes:', { 
      state: 'hidden',
      timeout: TIMEOUTS.graphLoad 
    });
  } catch {
    // Loading overlay might already be gone, that's fine
  }
  
  // Additional wait for graph to stabilize
  await page.waitForTimeout(1000);
}

/**
 * Wait for graph to be interactive
 * Ensures nodes are rendered and clickable
 */
export async function waitForGraphInteractive(page) {
  await waitForGraphLoad(page);
  
  // Wait for the Sigma nodes canvas element (specific canvas, not all)
  await page.waitForSelector(`${SELECTORS.graphContainer} canvas.sigma-nodes`, {
    state: 'visible',
    timeout: TIMEOUTS.graphLoad
  });
}

/**
 * Click on the graph canvas at specific coordinates
 * Useful for clicking nodes if you know their approximate position
 */
export async function clickGraphAt(page, x, y) {
  const container = page.locator(SELECTORS.graphContainer);
  await container.click({ position: { x, y } });
}

/**
 * Click on the center of the graph canvas
 * Useful for clearing selections
 */
export async function clickGraphCenter(page) {
  const container = page.locator(SELECTORS.graphContainer);
  const box = await container.boundingBox();
  if (box) {
    await container.click({ 
      position: { x: box.width / 2, y: box.height / 2 } 
    });
  }
}

/**
 * Check if the graph canvas is visible and has content
 */
export async function isGraphVisible(page) {
  const container = page.locator(SELECTORS.graphContainer);
  const isVisible = await container.isVisible();
  
  if (!isVisible) return false;
  
  // Check for Sigma's nodes canvas (specific one to avoid multiple element issues)
  const canvas = page.locator(`${SELECTORS.graphContainer} canvas.sigma-nodes`);
  return await canvas.isVisible();
}

/**
 * Get the graph loading progress (if visible)
 */
export async function getLoadingProgress(page) {
  try {
    const loadingText = await page.textContent('text=Nodes:', { timeout: 1000 });
    if (loadingText) {
      const match = loadingText.match(/Nodes:\s*(\d+)\s*\/\s*(\d+)/);
      if (match) {
        return {
          loaded: parseInt(match[1]),
          total: parseInt(match[2]),
          percent: Math.round((parseInt(match[1]) / parseInt(match[2])) * 100)
        };
      }
    }
  } catch {
    // Loading complete or not started
  }
  return null;
}

/**
 * Check if cluster labels are visible on the canvas
 */
export async function areClusterLabelsVisible(page) {
  // Cluster labels are in spans with class containing 'label'
  const labels = page.locator('span[class*="label"]');
  const count = await labels.count();
  return count > 0;
}

/**
 * Hover over graph canvas at coordinates
 */
export async function hoverGraphAt(page, x, y) {
  const container = page.locator(SELECTORS.graphContainer);
  await container.hover({ position: { x, y } });
}

/**
 * Check if tooltip is visible
 */
export async function isTooltipVisible(page) {
  // Tooltip is a div with specific styling
  const tooltip = page.locator('div[style*="position:absolute"][style*="z-index:100"]');
  return await tooltip.isVisible();
}

/**
 * Get tooltip content
 */
export async function getTooltipContent(page) {
  const tooltip = page.locator('div[style*="position:absolute"][style*="z-index:100"]');
  if (await tooltip.isVisible()) {
    return await tooltip.textContent();
  }
  return null;
}

