/**
 * Filter Panel Tests
 * 
 * Tests for:
 * - Filter panel expand/collapse
 * - Year range filtering
 * - Citation count filtering
 * - Decay factor adjustment
 * - Node limit control
 * - Clear filters functionality
 */

import { test, expect } from '@playwright/test';
import { TIMEOUTS, SELECTORS } from '../fixtures/test-data.js';
import { waitForGraphLoad } from '../helpers/graph-helpers.js';
import { clearPapersOfInterest } from '../helpers/sidebar-helpers.js';

test.describe('Filter Panel Basic Functionality', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await waitForGraphLoad(page);
  });

  test('should display filter panel header', async ({ page }) => {
    const filterHeader = page.locator(SELECTORS.filterHeader);
    await expect(filterHeader).toBeVisible();
  });

  test('should show "Filters" label with icon', async ({ page }) => {
    const filterLabel = page.locator('text=🔍 Filters');
    await expect(filterLabel).toBeVisible();
  });

  test('should be collapsed by default', async ({ page }) => {
    // The expand arrow should show ▶ when collapsed
    const expandArrow = page.locator('.filter-header button');
    const arrowText = await expandArrow.textContent();
    expect(arrowText).toContain('▶');
  });

  test('should expand when clicking header', async ({ page }) => {
    const filterHeader = page.locator(SELECTORS.filterHeader);
    await filterHeader.click();
    
    await page.waitForTimeout(300);
    
    // Should now show filter controls
    const filterBody = page.locator('.filter-body');
    await expect(filterBody).toBeVisible();
    
    // Arrow should change to ▼
    const expandArrow = page.locator('.filter-header button');
    const arrowText = await expandArrow.textContent();
    expect(arrowText).toContain('▼');
  });

  test('should collapse when clicking header again', async ({ page }) => {
    const filterHeader = page.locator(SELECTORS.filterHeader);
    
    // Expand
    await filterHeader.click();
    await page.waitForTimeout(300);
    
    // Collapse
    await filterHeader.click();
    await page.waitForTimeout(300);
    
    // Should be collapsed
    const expandArrow = page.locator('.filter-header button');
    const arrowText = await expandArrow.textContent();
    expect(arrowText).toContain('▶');
  });

});

test.describe('Year Range Filter', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await waitForGraphLoad(page);
    
    // Expand filter panel
    await page.locator(SELECTORS.filterHeader).click();
    await page.waitForTimeout(300);
  });

  test('should display year range inputs', async ({ page }) => {
    const yearMinInput = page.locator('#yearMin');
    const yearMaxInput = page.locator('#yearMax');
    
    await expect(yearMinInput).toBeVisible();
    await expect(yearMaxInput).toBeVisible();
  });

  test('should show "Publication Date Range" label', async ({ page }) => {
    const label = page.locator('text=📅 Publication Date Range');
    await expect(label).toBeVisible();
  });

  test('should accept year input for minimum', async ({ page }) => {
    const yearMinInput = page.locator('#yearMin');
    
    await yearMinInput.fill('2015');
    await expect(yearMinInput).toHaveValue('2015');
  });

  test('should accept year input for maximum', async ({ page }) => {
    const yearMaxInput = page.locator('#yearMax');
    
    await yearMaxInput.fill('2020');
    await expect(yearMaxInput).toHaveValue('2020');
  });

  test('should show active badge when year filter applied', async ({ page }) => {
    const yearMinInput = page.locator('#yearMin');
    await yearMinInput.fill('2015');
    
    await page.waitForTimeout(500);
    
    // Active badge should appear
    const activeBadge = page.locator('.filter-badge');
    await expect(activeBadge).toBeVisible();
  });

  test('should update active filters summary', async ({ page }) => {
    const yearMinInput = page.locator('#yearMin');
    await yearMinInput.fill('2015');
    
    await page.waitForTimeout(500);
    
    // Should show in active filters
    const activeFilters = page.locator('text=From 2015');
    await expect(activeFilters).toBeVisible();
  });

});

test.describe('Citation Count Filter', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await waitForGraphLoad(page);
    
    // Expand filter panel
    await page.locator(SELECTORS.filterHeader).click();
    await page.waitForTimeout(300);
  });

  test('should display minimum citations input', async ({ page }) => {
    const citationsInput = page.locator('#minCitations');
    await expect(citationsInput).toBeVisible();
  });

  test('should show "Minimum Citations" label', async ({ page }) => {
    const label = page.locator('text=📊 Minimum Citations');
    await expect(label).toBeVisible();
  });

  test('should accept citation count input', async ({ page }) => {
    const citationsInput = page.locator('#minCitations');
    
    await citationsInput.fill('50');
    await expect(citationsInput).toHaveValue('50');
  });

  test('should show help text', async ({ page }) => {
    const hint = page.locator('text=Only show papers with at least this many citations');
    await expect(hint).toBeVisible();
  });

  test('should update active filters when citation filter applied', async ({ page }) => {
    const citationsInput = page.locator('#minCitations');
    await citationsInput.fill('100');
    
    await page.waitForTimeout(500);
    
    const activeFilters = page.locator('text=≥ 100 citations');
    await expect(activeFilters).toBeVisible();
  });

});

test.describe('Decay Factor Slider', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await waitForGraphLoad(page);
    
    // Expand filter panel
    await page.locator(SELECTORS.filterHeader).click();
    await page.waitForTimeout(300);
  });

  test('should display decay factor slider', async ({ page }) => {
    const slider = page.locator('#decayFactor');
    await expect(slider).toBeVisible();
  });

  test('should show decay factor label with value', async ({ page }) => {
    const label = page.locator('text=⚖️ Scoring Decay Factor:');
    await expect(label).toBeVisible();
    
    // Should show current value
    const value = page.locator('.filter-label strong');
    await expect(value.first()).toBeVisible();
  });

  test('should have min/max labels', async ({ page }) => {
    const favorRecent = page.locator('text=Favor Recent');
    const balanced = page.locator('text=Balanced');
    const favorOld = page.locator('text=Favor Old');
    
    await expect(favorRecent).toBeVisible();
    await expect(balanced).toBeVisible();
    await expect(favorOld).toBeVisible();
  });

  test('should default to 1.0', async ({ page }) => {
    const slider = page.locator('#decayFactor');
    const value = await slider.inputValue();
    expect(parseFloat(value)).toBe(1.0);
  });

  test('should update value when slider moved', async ({ page }) => {
    const slider = page.locator('#decayFactor');
    
    // Move slider using evaluate (range inputs can't use fill)
    await slider.evaluate(el => el.value = '2.0');
    await slider.dispatchEvent('input');
    await slider.dispatchEvent('change');
    
    await page.waitForTimeout(300);
    
    // Value should update
    const newValue = await slider.inputValue();
    expect(parseFloat(newValue)).toBe(2.0);
  });

  test('should show help text', async ({ page }) => {
    const hint = page.locator('text=Controls how paper age affects importance score');
    await expect(hint).toBeVisible();
  });

});

test.describe('Node Limit Control', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await waitForGraphLoad(page);
    
    // Expand filter panel
    await page.locator(SELECTORS.filterHeader).click();
    await page.waitForTimeout(300);
  });

  test('should display node limit input', async ({ page }) => {
    const nodeLimitInput = page.locator('#nodeLimit');
    await expect(nodeLimitInput).toBeVisible();
  });

  test('should show warning about page refresh', async ({ page }) => {
    const warning = page.locator('text=Requires page refresh');
    await expect(warning).toBeVisible();
  });

  test('should accept node limit value', async ({ page }) => {
    const nodeLimitInput = page.locator('#nodeLimit');
    
    await nodeLimitInput.fill('5000');
    await expect(nodeLimitInput).toHaveValue('5000');
  });

  test('should show reset button when value set', async ({ page }) => {
    const nodeLimitInput = page.locator('#nodeLimit');
    await nodeLimitInput.fill('5000');
    
    await page.waitForTimeout(300);
    
    const resetButton = page.locator('button:has-text("Reset to Default")');
    await expect(resetButton).toBeVisible();
  });

});

test.describe('Clear Filters', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await waitForGraphLoad(page);
    
    // Expand filter panel
    await page.locator(SELECTORS.filterHeader).click();
    await page.waitForTimeout(300);
  });

  test('should display Clear All Filters button', async ({ page }) => {
    const clearButton = page.locator('button.clear-filters-btn');
    await expect(clearButton).toBeVisible();
  });

  test('should be disabled when no filters active', async ({ page }) => {
    const clearButton = page.locator('button.clear-filters-btn');
    await expect(clearButton).toBeDisabled();
  });

  test('should be enabled when filters are active', async ({ page }) => {
    // Set a filter
    const yearMinInput = page.locator('#yearMin');
    await yearMinInput.fill('2015');
    
    await page.waitForTimeout(500);
    
    const clearButton = page.locator('button.clear-filters-btn');
    await expect(clearButton).toBeEnabled();
  });

  test('should clear all filters when clicked', async ({ page }) => {
    // Set multiple filters
    const yearMinInput = page.locator('#yearMin');
    const citationsInput = page.locator('#minCitations');
    const decaySlider = page.locator('#decayFactor');
    
    await yearMinInput.fill('2015');
    await citationsInput.fill('50');
    // Move slider using evaluate (range inputs can't use fill)
    await decaySlider.evaluate(el => el.value = '2.0');
    await decaySlider.dispatchEvent('input');
    await decaySlider.dispatchEvent('change');
    
    await page.waitForTimeout(500);
    
    // Click clear button
    const clearButton = page.locator('button.clear-filters-btn');
    await clearButton.click();
    
    await page.waitForTimeout(500);
    
    // All inputs should be cleared
    await expect(yearMinInput).toHaveValue('');
    await expect(citationsInput).toHaveValue('');
    
    // Decay should reset to 1.0
    const decayValue = await decaySlider.inputValue();
    expect(parseFloat(decayValue)).toBe(1.0);
  });

  test('should remove active badge after clearing', async ({ page }) => {
    // Set a filter
    const yearMinInput = page.locator('#yearMin');
    await yearMinInput.fill('2015');
    
    await page.waitForTimeout(500);
    
    // Clear filters
    const clearButton = page.locator('button.clear-filters-btn');
    await clearButton.click();
    
    await page.waitForTimeout(500);
    
    // Active badge should be hidden
    const activeBadge = page.locator('.filter-badge');
    await expect(activeBadge).not.toBeVisible();
  });

});

test.describe('Filter Effects on Graph', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await clearPapersOfInterest(page);
    await waitForGraphLoad(page);
    
    // Expand filter panel
    await page.locator(SELECTORS.filterHeader).click();
    await page.waitForTimeout(300);
  });

  test('should not break graph when applying year filter', async ({ page }) => {
    const yearMinInput = page.locator('#yearMin');
    await yearMinInput.fill('2010');
    
    await page.waitForTimeout(1000);
    
    // Graph should still be visible
    const graphContainer = page.locator(SELECTORS.graphContainer);
    await expect(graphContainer).toBeVisible();
  });

  test('should not break graph when applying citation filter', async ({ page }) => {
    const citationsInput = page.locator('#minCitations');
    await citationsInput.fill('100');
    
    await page.waitForTimeout(1000);
    
    // Graph should still be visible
    const graphContainer = page.locator(SELECTORS.graphContainer);
    await expect(graphContainer).toBeVisible();
  });

  test('should not break graph when adjusting decay factor', async ({ page }) => {
    const decaySlider = page.locator('#decayFactor');
    await decaySlider.evaluate(el => el.value = '0.5');
    await decaySlider.dispatchEvent('input');
    await decaySlider.dispatchEvent('change');
    
    await page.waitForTimeout(1000);
    
    // Graph should still be visible
    const graphContainer = page.locator(SELECTORS.graphContainer);
    await expect(graphContainer).toBeVisible();
  });

  test('should apply multiple filters simultaneously', async ({ page }) => {
    const yearMinInput = page.locator('#yearMin');
    const yearMaxInput = page.locator('#yearMax');
    const citationsInput = page.locator('#minCitations');
    
    await yearMinInput.fill('2010');
    await yearMaxInput.fill('2020');
    await citationsInput.fill('20');
    
    await page.waitForTimeout(1000);
    
    // Graph should still be visible and functional
    const graphContainer = page.locator(SELECTORS.graphContainer);
    await expect(graphContainer).toBeVisible();
    
    // Active filters should show all three
    const activeFilters = page.locator('.active-filters');
    await expect(activeFilters).toBeVisible();
  });

});

test.describe('Filter Persistence', () => {
  
  test('should clear year filters on page navigation', async ({ page }) => {
    await page.goto('/');
    await waitForGraphLoad(page);
    
    // Expand and set filter
    await page.locator(SELECTORS.filterHeader).click();
    await page.waitForTimeout(300);
    
    const yearMinInput = page.locator('#yearMin');
    await yearMinInput.fill('2015');
    
    // Navigate away and back
    await page.goto('/admin/build');
    await page.goto('/');
    await waitForGraphLoad(page);
    
    // Expand filter panel
    await page.locator(SELECTORS.filterHeader).click();
    await page.waitForTimeout(300);
    
    // Year filter should be cleared (component state reset)
    const yearMinAfter = page.locator('#yearMin');
    const value = await yearMinAfter.inputValue();
    expect(value).toBe('');
  });

});

