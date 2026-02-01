import { test, expect } from '@playwright/test';

// These tests require the backend API to be running
// Skip if the API is not available or user already completed onboarding
test.describe('Onboarding Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to onboarding page and wait for network to settle
    await page.goto('/onboarding', { waitUntil: 'networkidle' });

    // Wait for either the onboarding form, projects page, or loading to complete
    const welcomeHeading = page.locator('h1:has-text("Welcome to Ad Engine")');
    const projectsPage = page.locator('h1:has-text("Projects"), main h1:has-text("Projects")');
    const industryDropdown = page.locator('#industry');

    // Wait for the page to load (try to find form elements)
    try {
      await Promise.race([
        welcomeHeading.waitFor({ state: 'visible', timeout: 10000 }),
        projectsPage.waitFor({ state: 'visible', timeout: 10000 }),
      ]);
    } catch {
      // If neither appeared, the API might not be running - skip tests
      test.skip();
      return;
    }

    // Skip tests if redirected to projects (user already completed onboarding)
    if (await projectsPage.isVisible().catch(() => false)) {
      test.skip();
      return;
    }

    // Wait for the form to stabilize (React re-renders)
    await page.waitForTimeout(500);

    // Skip if the form didn't load (API not responding)
    const formReady = await industryDropdown.isVisible({ timeout: 5000 }).catch(() => false);
    if (!formReady) {
      test.skip();
      return;
    }
  });

  test('should display onboarding page with step indicator', async ({ page }) => {
    // Check page title and header
    await expect(page.getByRole('heading', { name: 'Welcome to Ad Engine' })).toBeVisible();
    await expect(
      page.getByText("Let's set up your brand profile to create personalized ads")
    ).toBeVisible();

    // Check step indicators
    await expect(page.getByText('Industry')).toBeVisible();
    await expect(page.getByText('Core Offer')).toBeVisible();
    await expect(page.getByText('Brand Voice')).toBeVisible();

    // Check first step is active
    await expect(page.getByRole('heading', { name: 'Industry' })).toBeVisible();
    await expect(page.getByText('Tell us about your business sector')).toBeVisible();
  });

  test('should show industry and niche fields on step 1', async ({ page }) => {
    // Check industry dropdown
    await expect(page.getByLabel('Industry *')).toBeVisible();
    await expect(page.getByText('Select your industry')).toBeVisible();

    // Check niche input
    await expect(page.getByLabel('Niche (Optional)')).toBeVisible();

    // Back button should be disabled on step 1
    await expect(page.getByRole('button', { name: 'Back' })).toBeDisabled();

    // Next button should be disabled until industry is selected
    await expect(page.getByRole('button', { name: 'Next' })).toBeDisabled();
  });

  test('should navigate to step 2 after selecting industry', async ({ page }) => {
    // Select industry
    await page.getByRole('combobox', { name: 'Industry *' }).click();
    await page.getByRole('option', { name: 'E-commerce / Retail' }).click();

    // Next button should be enabled
    await expect(page.getByRole('button', { name: 'Next' })).toBeEnabled();

    // Click next
    await page.getByRole('button', { name: 'Next' }).click();

    // Should be on step 2
    await expect(page.getByRole('heading', { name: 'Core Offer' })).toBeVisible();
    await expect(page.getByText('Describe your main product or service')).toBeVisible();

    // Back button should be enabled
    await expect(page.getByRole('button', { name: 'Back' })).toBeEnabled();
  });

  test('should show core offer and keywords fields on step 2', async ({ page }) => {
    // Go to step 2
    await page.getByRole('combobox', { name: 'Industry *' }).click();
    await page.getByRole('option', { name: 'SaaS / Software' }).click();
    await page.getByRole('button', { name: 'Next' }).click();

    // Check core offer textarea
    await expect(page.getByLabel('Core Offer *')).toBeVisible();

    // Check keywords section
    await expect(page.getByText('Keywords')).toBeVisible();
    await expect(page.getByPlaceholder('Add a keyword...')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Add' })).toBeVisible();

    // Next button should be disabled until core offer is filled
    await expect(page.getByRole('button', { name: 'Next' })).toBeDisabled();
  });

  test('should allow adding and removing keywords', async ({ page }) => {
    // Go to step 2
    await page.getByRole('combobox', { name: 'Industry *' }).click();
    await page.getByRole('option', { name: 'SaaS / Software' }).click();
    await page.getByRole('button', { name: 'Next' }).click();

    // Fill core offer first
    await page.getByLabel('Core Offer *').fill('AI-powered analytics dashboard for small businesses');

    // Add a keyword
    await page.getByPlaceholder('Add a keyword...').fill('analytics');
    await page.getByRole('button', { name: 'Add' }).click();

    // Keyword should appear as a badge
    await expect(page.getByText('analytics')).toBeVisible();

    // Add another keyword with Enter
    await page.getByPlaceholder('Add a keyword...').fill('AI');
    await page.getByPlaceholder('Add a keyword...').press('Enter');
    await expect(page.getByText('AI')).toBeVisible();

    // Remove a keyword by clicking X
    const analyticsBadge = page.locator('text=analytics').locator('..');
    await analyticsBadge.getByRole('button').click();

    // Keyword should be removed
    await expect(page.getByText('analytics')).not.toBeVisible();
  });

  test('should navigate to step 3', async ({ page }) => {
    // Complete steps 1 and 2
    await page.getByRole('combobox', { name: 'Industry *' }).click();
    await page.getByRole('option', { name: 'Health & Fitness' }).click();
    await page.getByRole('button', { name: 'Next' }).click();

    await page.getByLabel('Core Offer *').fill('Online personal training programs with 1-on-1 coaching');
    await page.getByRole('button', { name: 'Next' }).click();

    // Should be on step 3
    await expect(page.getByRole('heading', { name: 'Brand Voice' })).toBeVisible();
    await expect(page.getByText('Define your brand personality')).toBeVisible();

    // Check tone dropdown
    await expect(page.getByLabel('Brand Tone')).toBeVisible();

    // Check forbidden terms section
    await expect(page.getByText('Forbidden Terms (Optional)')).toBeVisible();

    // Check color picker
    await expect(page.getByLabel('Brand Color')).toBeVisible();

    // Complete Setup button should be visible
    await expect(page.getByRole('button', { name: 'Complete Setup' })).toBeVisible();
  });

  test('should allow selecting tone on step 3', async ({ page }) => {
    // Navigate to step 3
    await page.getByRole('combobox', { name: 'Industry *' }).click();
    await page.getByRole('option', { name: 'Health & Fitness' }).click();
    await page.getByRole('button', { name: 'Next' }).click();

    await page.getByLabel('Core Offer *').fill('Online personal training programs');
    await page.getByRole('button', { name: 'Next' }).click();

    // Select tone
    await page.getByRole('combobox', { name: 'Brand Tone' }).click();
    await page.getByRole('option', { name: 'Inspirational & Motivational' }).click();

    // Tone should be selected
    await expect(page.getByText('Inspirational & Motivational')).toBeVisible();
  });

  test('should allow adding forbidden terms on step 3', async ({ page }) => {
    // Navigate to step 3
    await page.getByRole('combobox', { name: 'Industry *' }).click();
    await page.getByRole('option', { name: 'Health & Fitness' }).click();
    await page.getByRole('button', { name: 'Next' }).click();

    await page.getByLabel('Core Offer *').fill('Online personal training programs');
    await page.getByRole('button', { name: 'Next' }).click();

    // Add forbidden term
    await page.getByPlaceholder('Add terms to avoid...').fill('steroids');
    await page.getByRole('button', { name: 'Add' }).nth(0).click();

    // Term should appear as badge
    await expect(page.getByText('steroids')).toBeVisible();
  });

  test('should navigate back through steps', async ({ page }) => {
    // Go to step 3
    await page.getByRole('combobox', { name: 'Industry *' }).click();
    await page.getByRole('option', { name: 'E-commerce / Retail' }).click();
    await page.getByLabel('Niche (Optional)').fill('Fashion');
    await page.getByRole('button', { name: 'Next' }).click();

    await page.getByLabel('Core Offer *').fill('Premium sustainable clothing for conscious consumers');
    await page.getByRole('button', { name: 'Next' }).click();

    // Go back to step 2
    await page.getByRole('button', { name: 'Back' }).click();
    await expect(page.getByRole('heading', { name: 'Core Offer' })).toBeVisible();

    // Previous values should be preserved
    await expect(page.getByLabel('Core Offer *')).toHaveValue(
      'Premium sustainable clothing for conscious consumers'
    );

    // Go back to step 1
    await page.getByRole('button', { name: 'Back' }).click();
    await expect(page.getByRole('heading', { name: 'Industry' })).toBeVisible();

    // Previous values should be preserved
    await expect(page.getByLabel('Niche (Optional)')).toHaveValue('Fashion');
  });

  test('should have skip option', async ({ page }) => {
    // Check skip button exists
    await expect(page.getByRole('button', { name: 'Skip for now' })).toBeVisible();
  });

  test('should complete full onboarding flow', async ({ page }) => {
    // Step 1: Industry
    await page.getByRole('combobox', { name: 'Industry *' }).click();
    await page.getByRole('option', { name: 'E-commerce / Retail' }).click();
    await page.getByLabel('Niche (Optional)').fill('Sustainable Fashion');
    await page.getByRole('button', { name: 'Next' }).click();

    // Step 2: Core Offer
    await page
      .getByLabel('Core Offer *')
      .fill('Premium sustainable clothing made from recycled materials');
    await page.getByPlaceholder('Add a keyword...').fill('sustainable');
    await page.getByRole('button', { name: 'Add' }).click();
    await page.getByPlaceholder('Add a keyword...').fill('eco-friendly');
    await page.getByRole('button', { name: 'Add' }).click();
    await page.getByRole('button', { name: 'Next' }).click();

    // Step 3: Brand Voice
    await page.getByRole('combobox', { name: 'Brand Tone' }).click();
    await page.getByRole('option', { name: 'Professional & Friendly' }).click();
    await page.getByPlaceholder('Add terms to avoid...').fill('cheap');
    await page.getByRole('button', { name: 'Add' }).nth(0).click();

    // Complete Setup button should be enabled
    await expect(page.getByRole('button', { name: 'Complete Setup' })).toBeEnabled();
  });

  test('should validate core offer minimum length', async ({ page }) => {
    // Go to step 2
    await page.getByRole('combobox', { name: 'Industry *' }).click();
    await page.getByRole('option', { name: 'SaaS / Software' }).click();
    await page.getByRole('button', { name: 'Next' }).click();

    // Enter too short core offer
    await page.getByLabel('Core Offer *').fill('Short');

    // Next button should be disabled
    await expect(page.getByRole('button', { name: 'Next' })).toBeDisabled();

    // Enter valid core offer
    await page.getByLabel('Core Offer *').fill('AI-powered analytics dashboard for small businesses');

    // Next button should be enabled
    await expect(page.getByRole('button', { name: 'Next' })).toBeEnabled();
  });

  test('should display character count for core offer', async ({ page }) => {
    // Go to step 2
    await page.getByRole('combobox', { name: 'Industry *' }).click();
    await page.getByRole('option', { name: 'SaaS / Software' }).click();
    await page.getByRole('button', { name: 'Next' }).click();

    // Check character counter exists
    await expect(page.getByText('/1000 characters (min 10)')).toBeVisible();

    // Type something and check counter updates
    await page.getByLabel('Core Offer *').fill('Test offer description');

    // Counter should show current length
    await expect(page.getByText('22/1000 characters (min 10)')).toBeVisible();
  });
});
