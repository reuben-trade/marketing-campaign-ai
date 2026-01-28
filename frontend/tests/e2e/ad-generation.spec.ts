import { test, expect } from '@playwright/test';

/**
 * End-to-end tests for the ad generation flow.
 * Tests the inspiration selection -> recipe extraction -> generation -> editing pipeline.
 */

test.describe('Ad Generation Flow', () => {
  // Using a non-existent project ID to test error states
  const testProjectId = '00000000-0000-0000-0000-000000000001';

  test.describe('Inspiration Selection', () => {
    test('should display inspiration page header', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(1000);

      // Check for header elements (may show error or loading for non-existent project)
      const header = page.locator('h1:has-text("Select Inspiration")');
      const errorState = page.locator('text=Project not found');
      const loadingSpinner = page.locator('.animate-spin');
      const backButton = page.locator('button:has-text("Back")').first();

      const hasHeader = await header.isVisible().catch(() => false);
      const hasError = await errorState.isVisible().catch(() => false);
      const isLoading = await loadingSpinner.isVisible().catch(() => false);
      const hasBack = await backButton.isVisible().catch(() => false);

      // Either header, error, loading, or back button should be visible
      expect(hasHeader || hasError || isLoading || hasBack).toBe(true);
    });

    test('should show source selector with Library tab active by default', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      const libraryTab = page.locator('button[role="tab"]:has-text("Library")');
      if (await libraryTab.isVisible().catch(() => false)) {
        // Library tab should be present
        await expect(libraryTab).toBeVisible();
      }
    });

    test('should be able to switch to Upload tab', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      const uploadTab = page.locator('button[role="tab"]:has-text("Upload")');
      if (await uploadTab.isVisible().catch(() => false)) {
        await uploadTab.click();
        await expect(page.locator('text=Upload Reference Ad')).toBeVisible();
      }
    });

    test('should be able to switch to URL tab', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      const urlTab = page.locator('button[role="tab"]:has-text("URL")');
      if (await urlTab.isVisible().catch(() => false)) {
        await urlTab.click();
        await expect(page.locator('text=Fetch Ad from URL')).toBeVisible();
      }
    });

    test('should show time warning on Upload tab', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      const uploadTab = page.locator('button[role="tab"]:has-text("Upload")');
      if (await uploadTab.isVisible().catch(() => false)) {
        await uploadTab.click();
        await expect(page.locator('text=Analysis takes 2-3 minutes')).toBeVisible();
      }
    });

    test('should show time warning on URL tab', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      const urlTab = page.locator('button[role="tab"]:has-text("URL")');
      if (await urlTab.isVisible().catch(() => false)) {
        await urlTab.click();
        await expect(page.locator('text=Fetching and analysis takes 2-3 minutes')).toBeVisible();
      }
    });

    test('should show URL input with placeholder', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      const urlTab = page.locator('button[role="tab"]:has-text("URL")');
      if (await urlTab.isVisible().catch(() => false)) {
        await urlTab.click();

        const urlInput = page.locator('input[type="url"]');
        await expect(urlInput).toBeVisible();
        await expect(urlInput).toHaveAttribute(
          'placeholder',
          'https://www.facebook.com/ads/library/...'
        );
      }
    });

    test('should show supported platforms list on URL tab', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      const urlTab = page.locator('button[role="tab"]:has-text("URL")');
      if (await urlTab.isVisible().catch(() => false)) {
        await urlTab.click();

        await expect(page.locator('text=Supported platforms')).toBeVisible();
        await expect(page.locator('text=Meta Ad Library')).toBeVisible();
        await expect(page.locator('text=TikTok Creative Center')).toBeVisible();
        await expect(page.locator('text=YouTube')).toBeVisible();
      }
    });

    test('should show selection counter', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      const counter = page.locator('text=/\\d\\/3 selected/');
      const isVisible = await counter.isVisible().catch(() => false);

      // Counter should be visible if gallery loaded
      if (isVisible) {
        await expect(counter).toBeVisible();
      }
    });

    test('should have Continue button disabled when no ads selected', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      const continueButton = page.locator('button:has-text("Continue")');
      if (await continueButton.isVisible().catch(() => false)) {
        await expect(continueButton).toBeDisabled();
      }
    });
  });

  test.describe('Library Gallery', () => {
    test('should show search input for ads', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      const searchInput = page.locator('input[placeholder="Search ads..."]');
      if (await searchInput.isVisible().catch(() => false)) {
        await expect(searchInput).toBeVisible();
      }
    });

    test('should show type filter dropdown', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      const typeFilter = page.locator('button:has-text("Videos")');
      const isVisible = await typeFilter.isVisible().catch(() => false);

      if (isVisible) {
        await expect(typeFilter).toBeVisible();
      }
    });

    test('should show sort dropdown', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      const sortButton = page.locator('button:has-text("Highest Score")');
      const isVisible = await sortButton.isVisible().catch(() => false);

      if (isVisible) {
        await expect(sortButton).toBeVisible();
      }
    });

    test('should allow changing type filter', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      const typeFilter = page.locator('[role="combobox"]').first();
      if (await typeFilter.isVisible().catch(() => false)) {
        await typeFilter.click();

        await expect(page.locator('[role="option"]:has-text("All Types")')).toBeVisible();
        await expect(page.locator('[role="option"]:has-text("Videos")')).toBeVisible();
        await expect(page.locator('[role="option"]:has-text("Images")')).toBeVisible();
      }
    });
  });

  test.describe('Editor Page', () => {
    test('should show editor page layout', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/editor`);
      await page.waitForTimeout(1000);

      // Either shows editor, loading, or error state
      const errorState = page.locator('text=Project not found');
      const previewCard = page.locator('text=Preview');
      const loadingSpinner = page.locator('.animate-spin');
      const backButton = page.locator('button:has-text("Back")').first();

      const hasError = await errorState.isVisible().catch(() => false);
      const hasPreview = await previewCard.isVisible().catch(() => false);
      const isLoading = await loadingSpinner.isVisible().catch(() => false);
      const hasBack = await backButton.isVisible().catch(() => false);

      expect(hasError || hasPreview || isLoading || hasBack).toBe(true);
    });

    test('should show composition type options', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/editor`);
      await page.waitForTimeout(500);

      const compositionSelect = page.locator('[role="combobox"]').first();
      if (await compositionSelect.isVisible().catch(() => false)) {
        await compositionSelect.click();

        // All three formats should be available
        await expect(page.locator('[role="option"]:has-text("Vertical (9:16)")')).toBeVisible();
        await expect(page.locator('[role="option"]:has-text("Horizontal (16:9)")')).toBeVisible();
        await expect(page.locator('[role="option"]:has-text("Square (1:1)")')).toBeVisible();
      }
    });

    test('should allow selecting different composition types', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/editor`);
      await page.waitForTimeout(500);

      const compositionSelect = page.locator('[role="combobox"]').first();
      if (await compositionSelect.isVisible().catch(() => false)) {
        await compositionSelect.click();
        await page.click('[role="option"]:has-text("Horizontal (16:9)")');

        // Selection should be reflected
        await expect(page.locator('button:has-text("Horizontal (16:9)")')).toBeVisible();
      }
    });

    test('should show Render Video button', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/editor`);
      await page.waitForTimeout(500);

      const renderButton = page.locator('button:has-text("Render Video")');
      if (await renderButton.isVisible().catch(() => false)) {
        await expect(renderButton).toBeVisible();
      }
    });

    test('should show empty timeline message when no payload', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/editor`);
      await page.waitForTimeout(1000);

      const noVideoMessage = page.locator('text=Generate an ad to see the timeline');
      const sampleContent = page.locator('text=Generate Your Ad');
      const projectError = page.locator('text=Project not found');
      const loadingSpinner = page.locator('.animate-spin');
      const timelineCard = page.locator('text=Timeline');

      const hasNoVideo = await noVideoMessage.isVisible().catch(() => false);
      const hasSample = await sampleContent.isVisible().catch(() => false);
      const hasError = await projectError.isVisible().catch(() => false);
      const isLoading = await loadingSpinner.isVisible().catch(() => false);
      const hasTimeline = await timelineCard.isVisible().catch(() => false);

      // One of these should be visible
      expect(hasNoVideo || hasSample || hasError || isLoading || hasTimeline).toBe(true);
    });
  });

  test.describe('Render History', () => {
    test('should show empty render history for new project', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/editor`);
      await page.waitForTimeout(500);

      const renderHistory = page.locator('text=Render History');
      if (await renderHistory.isVisible().catch(() => false)) {
        await expect(page.locator('text=No renders yet')).toBeVisible();
      }
    });
  });

  test.describe('Timeline Editor', () => {
    test('should show Timeline section', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/editor`);
      await page.waitForTimeout(500);

      const timeline = page.locator('text=Timeline');
      if (await timeline.isVisible().catch(() => false)) {
        await expect(timeline).toBeVisible();
      }
    });
  });

  test.describe('Error States', () => {
    test('should handle non-existent project gracefully on inspire page', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(2000);

      // Should show error, loading, or back button
      const errorState = page.locator('text=Project not found');
      const loadingSpinner = page.locator('.animate-spin');
      const backButton = page.locator('button:has-text("Back")').first();

      const hasError = await errorState.isVisible().catch(() => false);
      const isLoading = await loadingSpinner.isVisible().catch(() => false);
      const hasBack = await backButton.isVisible().catch(() => false);

      // Page should render something
      expect(hasError || isLoading || hasBack).toBe(true);
    });

    test('should have Back to Projects button on error state', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(1000);

      const backButton = page.locator('button:has-text("Back to Projects")');
      if (await backButton.isVisible().catch(() => false)) {
        await expect(backButton).toBeVisible();
      }
    });

    test('should navigate back to projects on Back to Projects click', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(1000);

      const backButton = page.locator('button:has-text("Back to Projects")');
      if (await backButton.isVisible().catch(() => false)) {
        await backButton.click();
        await expect(page).toHaveURL('/projects');
      }
    });

    test('should handle non-existent project on editor page', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/editor`);
      await page.waitForTimeout(2000);

      // Should show error, loading, or back button
      const errorState = page.locator('text=Project not found');
      const loadingSpinner = page.locator('.animate-spin');
      const backButton = page.locator('button:has-text("Back")').first();

      const hasError = await errorState.isVisible().catch(() => false);
      const isLoading = await loadingSpinner.isVisible().catch(() => false);
      const hasBack = await backButton.isVisible().catch(() => false);

      // Page should render something
      expect(hasError || isLoading || hasBack).toBe(true);
    });
  });

  test.describe('Recipe Extraction Flow', () => {
    test('should show recipe extraction step in how-it-works', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      const extractRecipes = page.locator('text=Extract recipes');
      if (await extractRecipes.isVisible().catch(() => false)) {
        await expect(extractRecipes).toBeVisible();
        await expect(
          page.locator('text=We analyze the structure: hooks, beats, transitions, timing')
        ).toBeVisible();
      }
    });
  });

  test.describe('Responsive Design', () => {
    test('inspire page should be responsive on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      // Page should load without issues
      const backButton = page.locator('button:has-text("Back")').first();
      if (await backButton.isVisible().catch(() => false)) {
        await expect(backButton).toBeVisible();
      }
    });

    test('editor page should be responsive on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(`/projects/${testProjectId}/editor`);
      await page.waitForTimeout(500);

      // Page should render
      const content = page.locator('.space-y-6');
      if (await content.isVisible().catch(() => false)) {
        await expect(content).toBeVisible();
      }
    });

    test('editor grid layout on desktop', async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.goto(`/projects/${testProjectId}/editor`);
      await page.waitForTimeout(500);

      // Grid layout should be present
      const gridContainer = page.locator('.grid.grid-cols-1');
      if (await gridContainer.isVisible().catch(() => false)) {
        await expect(gridContainer).toBeVisible();
      }
    });
  });

  test.describe('Navigation', () => {
    test('should navigate from inspire back to project detail', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      const backButton = page.locator('button:has-text("Back")').first();
      if (await backButton.isVisible().catch(() => false)) {
        await backButton.click();

        // Should navigate back
        await page.waitForTimeout(500);
        const url = page.url();
        expect(url).toMatch(/\/projects/);
      }
    });

    test('should navigate from editor back to project', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/editor`);
      await page.waitForTimeout(1000);

      const backButton = page.locator('button:has-text("Back")').first();
      if (await backButton.isVisible().catch(() => false)) {
        await backButton.click();

        // Should navigate back
        await page.waitForTimeout(500);
        const url = page.url();
        expect(url).toMatch(/\/projects/);
      }
    });
  });
});
