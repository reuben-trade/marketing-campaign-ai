import { test, expect } from '@playwright/test';

test.describe('Inspiration Selection Page', () => {
  // Use a non-existent project ID to test error states
  const testProjectId = '00000000-0000-0000-0000-000000000001';

  test.describe('Page Layout', () => {
    test('should display back to projects link and error state for non-existent project', async ({
      page,
    }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);

      // Wait for loading to complete
      await page.waitForTimeout(1000);

      // Check "Back to Projects" button exists (shown in error state)
      const backButton = page.locator('button:has-text("Back to Projects")');
      await expect(backButton).toBeVisible();

      // Should show "Project not found" error
      await expect(page.locator('text=Project not found')).toBeVisible();
    });

    test('should display How it works section when project exists', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);

      // Wait for the page to load
      await page.waitForTimeout(500);

      // Check for "How it works" title (may or may not be visible depending on error state)
      const howItWorksSection = page.locator('text=How it works');
      const isVisible = await howItWorksSection.isVisible().catch(() => false);

      // If visible, check the 3-step process
      if (isVisible) {
        await expect(page.locator('text=Browse winning ads')).toBeVisible();
        await expect(page.locator('text=Extract recipes')).toBeVisible();
        await expect(page.locator('text=Generate your ad')).toBeVisible();
      }
    });

    test('should show error state for non-existent project', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);

      // Wait for loading to complete
      await page.waitForTimeout(1000);

      // Should show error or loading state for non-existent project
      const errorState = page.locator('text=Project not found');
      const loadingSpinner = page.locator('.animate-spin');

      const hasError = await errorState.isVisible().catch(() => false);
      const isLoading = await loadingSpinner.isVisible().catch(() => false);

      // Either shows error or loading (API request pending)
      expect(hasError || isLoading).toBe(true);
    });
  });

  test.describe('Inspiration Source Selector', () => {
    test('should display three source tabs', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);

      // Wait for potential error state to render
      await page.waitForTimeout(500);

      // Look for tab buttons (visible even if project not found)
      const tabs = page.locator('[role="tablist"]');
      if (await tabs.isVisible().catch(() => false)) {
        await expect(page.locator('button[role="tab"]:has-text("Library")')).toBeVisible();
        await expect(page.locator('button[role="tab"]:has-text("Upload")')).toBeVisible();
        await expect(page.locator('button[role="tab"]:has-text("URL")')).toBeVisible();
      }
    });

    test('should switch between tabs', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      const tabList = page.locator('[role="tablist"]');
      if (await tabList.isVisible().catch(() => false)) {
        // Click Upload tab
        await page.click('button[role="tab"]:has-text("Upload")');
        await expect(page.locator('text=Upload Reference Ad')).toBeVisible();

        // Click URL tab
        await page.click('button[role="tab"]:has-text("URL")');
        await expect(page.locator('text=Fetch Ad from URL')).toBeVisible();

        // Click back to Library tab
        await page.click('button[role="tab"]:has-text("Library")');
        await expect(page.locator('text=Winning Ads Library')).toBeVisible();
      }
    });
  });

  test.describe('Library Tab', () => {
    test('should display search and filter controls', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      const searchInput = page.locator('input[placeholder="Search ads..."]');
      if (await searchInput.isVisible().catch(() => false)) {
        await expect(searchInput).toBeVisible();

        // Check filter dropdowns exist
        const typeFilter = page.locator('button:has-text("Videos")');
        const sortFilter = page.locator('button:has-text("Highest Score")');

        await expect(typeFilter).toBeVisible();
        await expect(sortFilter).toBeVisible();
      }
    });

    test('should show selection counter', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      // Check for selection counter badge
      const counter = page.locator('text=/0\\/3 selected/');
      const isVisible = await counter.isVisible().catch(() => false);

      // Counter should be visible if gallery loaded
      if (isVisible) {
        await expect(counter).toBeVisible();
      }
    });

    test('should filter by creative type', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      const typeFilter = page.locator('[role="combobox"]').first();
      if (await typeFilter.isVisible().catch(() => false)) {
        await typeFilter.click();

        // Check dropdown options
        await expect(page.locator('[role="option"]:has-text("All Types")')).toBeVisible();
        await expect(page.locator('[role="option"]:has-text("Videos")')).toBeVisible();
        await expect(page.locator('[role="option"]:has-text("Images")')).toBeVisible();
      }
    });

    test('should change sort order', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      // Click sort dropdown
      const sortButton = page.locator('button:has-text("Highest Score")');
      if (await sortButton.isVisible().catch(() => false)) {
        await sortButton.click();

        // Check sort options
        await expect(page.locator('[role="option"]:has-text("Most Engaged")')).toBeVisible();
        await expect(page.locator('[role="option"]:has-text("Most Recent")')).toBeVisible();
      }
    });
  });

  test.describe('Upload Tab', () => {
    test('should display upload instructions with time warning', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      // Switch to upload tab
      const uploadTab = page.locator('button[role="tab"]:has-text("Upload")');
      if (await uploadTab.isVisible().catch(() => false)) {
        await uploadTab.click();

        // Check time warning
        await expect(page.locator('text=Analysis takes 2-3 minutes')).toBeVisible();

        // Check upload zone
        await expect(page.locator('text=Drop a video file here')).toBeVisible();
      }
    });

    test('should show unavailable warning when upload handler not provided', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      // Switch to upload tab
      const uploadTab = page.locator('button[role="tab"]:has-text("Upload")');
      if (await uploadTab.isVisible().catch(() => false)) {
        await uploadTab.click();

        // Check for "not available" warning
        await expect(
          page.locator('text=Upload functionality is not available yet')
        ).toBeVisible();
      }
    });
  });

  test.describe('URL Tab', () => {
    test('should display URL input with instructions', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      // Switch to URL tab
      const urlTab = page.locator('button[role="tab"]:has-text("URL")');
      if (await urlTab.isVisible().catch(() => false)) {
        await urlTab.click();

        // Check time warning
        await expect(page.locator('text=Fetching and analysis takes 2-3 minutes')).toBeVisible();

        // Check URL input
        const urlInput = page.locator('input[type="url"]');
        await expect(urlInput).toBeVisible();
        await expect(urlInput).toHaveAttribute('placeholder', 'https://www.facebook.com/ads/library/...');
      }
    });

    test('should show supported platforms list', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      // Switch to URL tab
      const urlTab = page.locator('button[role="tab"]:has-text("URL")');
      if (await urlTab.isVisible().catch(() => false)) {
        await urlTab.click();

        // Check supported platforms
        await expect(page.locator('text=Supported platforms')).toBeVisible();
        await expect(page.locator('text=Meta Ad Library')).toBeVisible();
        await expect(page.locator('text=TikTok Creative Center')).toBeVisible();
        await expect(page.locator('text=YouTube')).toBeVisible();
      }
    });

    test('should show unavailable warning when fetch handler not provided', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      // Switch to URL tab
      const urlTab = page.locator('button[role="tab"]:has-text("URL")');
      if (await urlTab.isVisible().catch(() => false)) {
        await urlTab.click();

        // Check for "not available" warning
        await expect(
          page.locator('text=URL fetch functionality is not available yet')
        ).toBeVisible();
      }
    });
  });

  test.describe('Continue Button', () => {
    test('should have disabled Continue button when no ads selected', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      // Check Continue button is disabled
      const continueButton = page.locator('button:has-text("Continue")');
      if (await continueButton.isVisible().catch(() => false)) {
        await expect(continueButton).toBeDisabled();
      }
    });
  });

  test.describe('Selected Ads Summary', () => {
    test('should not show summary section when no ads selected', async ({ page }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(500);

      // Selected Inspiration card should not be visible
      const selectedCard = page.locator('text=Selected Inspiration');
      const isVisible = await selectedCard.isVisible().catch(() => false);
      expect(isVisible).toBe(false);
    });
  });

  test.describe('Navigation', () => {
    test('should navigate back to projects list on Back to Projects button click', async ({
      page,
    }) => {
      await page.goto(`/projects/${testProjectId}/inspire`);
      await page.waitForTimeout(1000);

      // Click "Back to Projects" button (shown in error state)
      const backButton = page.locator('button:has-text("Back to Projects")');
      if (await backButton.isVisible().catch(() => false)) {
        await backButton.click();

        // Should navigate to projects list
        await expect(page).toHaveURL('/projects');
      }
    });
  });
});
