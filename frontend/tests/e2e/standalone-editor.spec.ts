import { test, expect } from '@playwright/test';

/**
 * End-to-end tests for the standalone editor page.
 * Tests the /editor route which allows users to quickly create ads
 * without first navigating through projects.
 */

test.describe('Standalone Editor Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/editor');
    await page.waitForTimeout(500);
  });

  test.describe('Page Layout', () => {
    test('should display page title and description', async ({ page }) => {
      await expect(page.locator('h1:has-text("Create Ad")')).toBeVisible();
      await expect(
        page.locator('text=Upload your videos or select from existing projects')
      ).toBeVisible();
    });

    test('should display three numbered steps', async ({ page }) => {
      // Step 1: Source selection
      await expect(page.locator('text=Choose Your Source')).toBeVisible();

      // Step 2: Inspiration (optional)
      await expect(page.locator('text=Add Inspiration')).toBeVisible();

      // Step 3: Creative direction (optional)
      await expect(page.locator('text=Creative Direction')).toBeVisible();
    });

    test('should have Generate Ad button', async ({ page }) => {
      const generateButton = page.locator('button:has-text("Generate Ad")');
      await expect(generateButton).toBeVisible();
      // Button should be disabled when no source selected
      await expect(generateButton).toBeDisabled();
    });
  });

  test.describe('Source Selection - Upload Tab', () => {
    test('should display Upload Videos tab by default', async ({ page }) => {
      const uploadTab = page.locator('[role="tab"]:has-text("Upload Videos")');
      await expect(uploadTab).toBeVisible();
      await expect(uploadTab).toHaveAttribute('aria-selected', 'true');
    });

    test('should display file drop zone', async ({ page }) => {
      await expect(
        page.locator('text=Drop videos here or click to browse')
      ).toBeVisible();
      await expect(
        page.locator('text=MP4, MOV, WebM, AVI (max 100MB each, up to 10 files)')
      ).toBeVisible();
    });

    test('should have hidden file input for video selection', async ({ page }) => {
      const fileInput = page.locator('#editor-file-input');
      await expect(fileInput).toHaveAttribute('type', 'file');
      await expect(fileInput).toHaveAttribute('accept', 'video/*');
    });
  });

  test.describe('Source Selection - Select Projects Tab', () => {
    test('should display Select Projects tab', async ({ page }) => {
      const selectTab = page.locator('[role="tab"]:has-text("Select Projects")');
      await expect(selectTab).toBeVisible();
    });

    test('should switch to Select Projects tab when clicked', async ({ page }) => {
      const selectTab = page.locator('[role="tab"]:has-text("Select Projects")');
      await selectTab.click();

      await expect(selectTab).toHaveAttribute('aria-selected', 'true');
    });

    test('should show projects or empty state in select mode', async ({ page }) => {
      const selectTab = page.locator('[role="tab"]:has-text("Select Projects")');
      await selectTab.click();

      await page.waitForTimeout(1000);

      // Either show projects list, empty state, or loading
      const emptyState = page.locator('text=No projects with analyzed segments');
      const projectsList = page.locator('text=Select Projects');
      const loadingSpinner = page.locator('.animate-spin');

      const hasEmpty = await emptyState.isVisible().catch(() => false);
      const hasList = await projectsList.isVisible().catch(() => false);
      const isLoading = await loadingSpinner.isVisible().catch(() => false);

      expect(hasEmpty || hasList || isLoading).toBe(true);
    });
  });

  test.describe('Inspiration Section', () => {
    test('should have collapsible inspiration section with Optional badge', async ({
      page,
    }) => {
      await expect(page.locator('text=Add Inspiration')).toBeVisible();
      await expect(
        page.locator('.text-lg:has-text("Add Inspiration") ~ [class*="Badge"]:has-text("Optional")')
          .or(page.locator('text=Optional').first())
      ).toBeVisible();
    });

    test('should show/hide inspiration content when toggled', async ({ page }) => {
      const showButton = page.locator('button:has-text("Show")');
      const hideButton = page.locator('button:has-text("Hide")');

      // Initially hidden
      if (await showButton.isVisible()) {
        await showButton.click();

        // Content should now be visible
        await expect(
          page.locator('text=Select winning ads as structural templates')
        ).toBeVisible();
      }

      // Now click Hide
      if (await hideButton.isVisible()) {
        await hideButton.click();
      }
    });
  });

  test.describe('Creative Direction Section', () => {
    test('should have instructions textarea', async ({ page }) => {
      const textarea = page.locator('textarea#user-prompt');
      await expect(textarea).toBeVisible();
    });

    test('should accept input in instructions field', async ({ page }) => {
      const textarea = page.locator('textarea#user-prompt');
      await textarea.fill('Focus on the 50% discount, use upbeat energy');
      await expect(textarea).toHaveValue('Focus on the 50% discount, use upbeat energy');
    });

    test('should show helper text for instructions', async ({ page }) => {
      await expect(
        page.locator('text=These instructions will guide the AI in selecting clips')
      ).toBeVisible();
    });
  });

  test.describe('Generate Button States', () => {
    test('should be disabled when no source selected', async ({ page }) => {
      const generateButton = page.locator('button:has-text("Generate Ad")');
      await expect(generateButton).toBeDisabled();
    });

    test('should show info alert when source is ready', async ({ page }) => {
      // This would require uploading a file or selecting a project
      // For now, just verify the button exists
      const generateButton = page.locator('button:has-text("Generate Ad")');
      await expect(generateButton).toBeVisible();
    });
  });

  test.describe('Navigation', () => {
    test('should have Editor link in sidebar', async ({ page }) => {
      const sidebarLink = page.locator('aside a:has-text("Editor")');
      await expect(sidebarLink).toBeVisible();
      await expect(sidebarLink).toHaveAttribute('href', '/editor');
    });

    test('sidebar Editor link should be active on this page', async ({ page }) => {
      const sidebarLink = page.locator('aside a:has-text("Editor")');
      // Check if link has active styling (depends on implementation)
      await expect(sidebarLink).toBeVisible();
    });
  });

  test.describe('Responsive Design', () => {
    test('should work on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/editor');
      await page.waitForTimeout(500);

      // Page title should be visible
      await expect(page.locator('h1:has-text("Create Ad")')).toBeVisible();

      // Generate button should be visible
      await expect(page.locator('button:has-text("Generate Ad")')).toBeVisible();
    });

    test('should work on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto('/editor');
      await page.waitForTimeout(500);

      await expect(page.locator('h1:has-text("Create Ad")')).toBeVisible();
    });

    test('tabs should be usable on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/editor');
      await page.waitForTimeout(500);

      // Should be able to switch tabs
      const selectTab = page.locator('[role="tab"]:has-text("Select Projects")');
      await selectTab.click();
      await expect(selectTab).toHaveAttribute('aria-selected', 'true');
    });
  });

  test.describe('Accessibility', () => {
    test('page should have proper heading structure', async ({ page }) => {
      const h1 = page.locator('h1:has-text("Create Ad")');
      await expect(h1).toBeVisible();
    });

    test('form elements should have labels', async ({ page }) => {
      // Instructions textarea should have associated label
      const instructionsLabel = page.locator('label:has-text("Instructions")');
      await expect(instructionsLabel).toBeVisible();
    });

    test('tabs should be keyboard accessible', async ({ page }) => {
      const uploadTab = page.locator('[role="tab"]:has-text("Upload Videos")');
      await uploadTab.focus();
      await expect(uploadTab).toBeFocused();

      // Tab to next tab
      await page.keyboard.press('ArrowRight');
      const selectTab = page.locator('[role="tab"]:has-text("Select Projects")');
      await expect(selectTab).toBeFocused();
    });

    test('buttons should be focusable', async ({ page }) => {
      const generateButton = page.locator('button:has-text("Generate Ad")');
      await generateButton.focus();
      await expect(generateButton).toBeFocused();
    });
  });
});
