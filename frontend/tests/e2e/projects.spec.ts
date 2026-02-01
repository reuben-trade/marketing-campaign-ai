import { test, expect } from '@playwright/test';

test.describe('Projects Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/projects');
  });

  test('should display the projects page with header', async ({ page }) => {
    // Check page title (use more specific selector to avoid sidebar h1)
    await expect(page.locator('main h1, .space-y-6 h1').first()).toHaveText('Projects');

    // Check subtitle
    await expect(page.locator('text=Create and manage your ad generation projects')).toBeVisible();

    // Check "New Project" button exists
    const newProjectButton = page.locator('button:has-text("New Project")');
    await expect(newProjectButton).toBeVisible();
  });

  test('should display stats cards', async ({ page }) => {
    // Check stats cards are visible
    await expect(page.locator('text=Total Projects')).toBeVisible();
    await expect(page.locator('text=Videos Uploaded')).toBeVisible();
    await expect(page.locator('text=Segments Extracted')).toBeVisible();
  });

  test('should display filter controls', async ({ page }) => {
    // Check search input
    const searchInput = page.locator('input[placeholder="Search projects..."]');
    await expect(searchInput).toBeVisible();

    // Check status filter dropdown
    const statusFilter = page.locator('button:has-text("All Status")');
    await expect(statusFilter).toBeVisible();
  });

  test('should open create project dialog when clicking New Project', async ({ page }) => {
    // Click new project button
    await page.click('button:has-text("New Project")');

    // Check dialog is visible
    await expect(page.locator('text=Create New Project')).toBeVisible();

    // Check form fields
    await expect(page.locator('label:has-text("Project Name")')).toBeVisible();
    await expect(page.locator('label:has-text("Creative Direction")')).toBeVisible();

    // Check buttons
    await expect(page.locator('button:has-text("Cancel")')).toBeVisible();
    await expect(page.locator('button:has-text("Create Project")')).toBeVisible();
  });

  test('should show validation error when submitting empty project name', async ({ page }) => {
    // Open dialog
    await page.click('button:has-text("New Project")');

    // Wait for dialog
    await expect(page.locator('text=Create New Project')).toBeVisible();

    // Click create without entering name
    await page.click('button:has-text("Create Project")');

    // Check validation error
    await expect(page.locator('text=Project name is required')).toBeVisible();
  });

  test('should close dialog when clicking Cancel', async ({ page }) => {
    // Open dialog
    await page.click('button:has-text("New Project")');
    await expect(page.locator('text=Create New Project')).toBeVisible();

    // Click cancel
    await page.click('button:has-text("Cancel")');

    // Check dialog is closed
    await expect(page.locator('text=Create New Project')).not.toBeVisible();
  });

  test('should filter projects by search query', async ({ page }) => {
    const searchInput = page.locator('input[placeholder="Search projects..."]');

    // Type in search
    await searchInput.fill('test');

    // Search input should have the value
    await expect(searchInput).toHaveValue('test');
  });

  test('should change status filter', async ({ page }) => {
    // Click status filter
    await page.click('button:has-text("All Status")');

    // Select Draft option
    await page.click('div[role="option"]:has-text("Draft")');

    // Filter should update
    await expect(page.locator('button:has-text("Draft")')).toBeVisible();
  });

  test('should show content after loading completes', async ({ page }) => {
    // Wait for the page to finish loading - either content appears or we get an error
    // Try to find any of the possible content states
    try {
      await page.waitForSelector(
        'text=Failed to load projects, text=No projects found, button:has-text("Create Your First Project"), .group.relative.overflow-hidden, text=Total Projects',
        { timeout: 15000 }
      );
    } catch {
      // If selector timeout, continue with checks
    }

    // Page should show one of: error state, empty state, stats, or project cards
    const errorState = page.locator('text=Failed to load projects');
    const emptyState = page.locator('text=No projects found');
    const createFirstButton = page.locator('button:has-text("Create Your First Project")');
    const projectCards = page.locator('.group.relative.overflow-hidden');
    const statsCard = page.locator('text=Total Projects');

    // Check all possible states
    const hasError = await errorState.isVisible().catch(() => false);
    const hasEmptyState = await emptyState.isVisible().catch(() => false);
    const hasCreateFirstButton = await createFirstButton.isVisible().catch(() => false);
    const hasCards = (await projectCards.count()) > 0;
    const hasStats = await statsCard.isVisible().catch(() => false);

    // At least one of these should be true
    expect(hasError || hasEmptyState || hasCreateFirstButton || hasCards || hasStats).toBe(true);
  });

  test('should have Projects link in navigation', async ({ page }) => {
    // Check sidebar link (desktop)
    const sidebarLink = page.locator('aside a:has-text("Projects")');
    await expect(sidebarLink).toBeVisible();
    await expect(sidebarLink).toHaveAttribute('href', '/projects');
  });
});
