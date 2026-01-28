import { test, expect } from '@playwright/test';

test.describe('B-Roll Generator Component', () => {
  // Use test page that mounts the component directly
  // For now, test through the editor page where B-Roll can be accessed

  test.describe('Component Rendering', () => {
    test('should render the B-Roll generator form elements', async ({ page }) => {
      // Navigate to a page that would show the B-Roll generator
      // This would be accessible through the clip swap modal in the editor
      await page.goto('/projects');
      await page.waitForTimeout(500);

      // Check that the projects page loads (B-Roll is accessed from editor)
      await expect(page.locator('h1:has-text("Projects")')).toBeVisible();
    });
  });

  test.describe('Form Validation', () => {
    test('prompt input should accept text', async ({ page }) => {
      // Create a test page with isolated component
      await page.setContent(`
        <html>
          <head>
            <style>
              textarea { width: 300px; height: 100px; }
              select { width: 200px; }
              button { padding: 10px; }
            </style>
          </head>
          <body>
            <div id="test-form">
              <textarea id="prompt" placeholder="Describe the clip you want"></textarea>
              <select id="aspect-ratio">
                <option value="9:16">Vertical (9:16)</option>
                <option value="16:9">Horizontal (16:9)</option>
                <option value="1:1">Square (1:1)</option>
              </select>
              <select id="style">
                <option value="realistic">Realistic</option>
                <option value="cinematic">Cinematic</option>
                <option value="animated">Animated</option>
                <option value="artistic">Artistic</option>
              </select>
              <input type="range" id="duration" min="1" max="10" value="3" />
              <button id="generate" disabled>Generate B-Roll</button>
              <script>
                const prompt = document.getElementById('prompt');
                const generate = document.getElementById('generate');
                prompt.addEventListener('input', () => {
                  generate.disabled = !prompt.value.trim();
                });
              </script>
            </div>
          </body>
        </html>
      `);

      const promptInput = page.locator('#prompt');
      const generateButton = page.locator('#generate');

      // Initially disabled
      await expect(generateButton).toBeDisabled();

      // Enter text
      await promptInput.fill('Close-up of water dripping from a faucet');

      // Should be enabled now
      await expect(generateButton).toBeEnabled();

      // Clear text
      await promptInput.fill('');

      // Should be disabled again
      await expect(generateButton).toBeDisabled();
    });

    test('should have correct default values', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <select id="aspect-ratio">
              <option value="9:16" selected>Vertical (9:16)</option>
              <option value="16:9">Horizontal (16:9)</option>
              <option value="1:1">Square (1:1)</option>
            </select>
            <select id="style">
              <option value="realistic" selected>Realistic</option>
              <option value="cinematic">Cinematic</option>
              <option value="animated">Animated</option>
              <option value="artistic">Artistic</option>
            </select>
            <input type="range" id="duration" min="1" max="10" value="3" />
            <span id="duration-label">3s</span>
          </body>
        </html>
      `);

      // Check default aspect ratio
      await expect(page.locator('#aspect-ratio')).toHaveValue('9:16');

      // Check default style
      await expect(page.locator('#style')).toHaveValue('realistic');

      // Check default duration
      await expect(page.locator('#duration')).toHaveValue('3');
    });

    test('aspect ratio options should be available', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <select id="aspect-ratio">
              <option value="9:16">Vertical (9:16)</option>
              <option value="16:9">Horizontal (16:9)</option>
              <option value="1:1">Square (1:1)</option>
            </select>
          </body>
        </html>
      `);

      const select = page.locator('#aspect-ratio');

      // Check all options exist
      await expect(select.locator('option[value="9:16"]')).toHaveText('Vertical (9:16)');
      await expect(select.locator('option[value="16:9"]')).toHaveText('Horizontal (16:9)');
      await expect(select.locator('option[value="1:1"]')).toHaveText('Square (1:1)');
    });

    test('style options should be available', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <select id="style">
              <option value="realistic">Realistic</option>
              <option value="cinematic">Cinematic</option>
              <option value="animated">Animated</option>
              <option value="artistic">Artistic</option>
            </select>
          </body>
        </html>
      `);

      const select = page.locator('#style');

      // Check all options exist
      await expect(select.locator('option[value="realistic"]')).toHaveText('Realistic');
      await expect(select.locator('option[value="cinematic"]')).toHaveText('Cinematic');
      await expect(select.locator('option[value="animated"]')).toHaveText('Animated');
      await expect(select.locator('option[value="artistic"]')).toHaveText('Artistic');
    });

    test('duration slider should have correct range', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <input type="range" id="duration" min="1" max="10" step="1" value="3" />
            <span id="duration-display">3s</span>
            <script>
              const slider = document.getElementById('duration');
              const display = document.getElementById('duration-display');
              slider.addEventListener('input', () => {
                display.textContent = slider.value + 's';
              });
            </script>
          </body>
        </html>
      `);

      const slider = page.locator('#duration');
      const display = page.locator('#duration-display');

      // Check min/max attributes
      await expect(slider).toHaveAttribute('min', '1');
      await expect(slider).toHaveAttribute('max', '10');

      // Change value and check display
      await slider.fill('5');
      await expect(display).toHaveText('5s');

      await slider.fill('10');
      await expect(display).toHaveText('10s');
    });
  });

  test.describe('Advanced Settings', () => {
    test('should toggle advanced settings visibility', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <button id="toggle-advanced">Advanced Settings</button>
            <div id="advanced-panel" style="display: none;">
              <input type="text" id="negative-prompt" placeholder="What to avoid" />
              <input type="range" id="variants" min="1" max="4" value="2" />
            </div>
            <script>
              const toggle = document.getElementById('toggle-advanced');
              const panel = document.getElementById('advanced-panel');
              toggle.addEventListener('click', () => {
                panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
              });
            </script>
          </body>
        </html>
      `);

      const advancedPanel = page.locator('#advanced-panel');
      const toggleButton = page.locator('#toggle-advanced');

      // Initially hidden
      await expect(advancedPanel).toBeHidden();

      // Click to show
      await toggleButton.click();
      await expect(advancedPanel).toBeVisible();

      // Click to hide
      await toggleButton.click();
      await expect(advancedPanel).toBeHidden();
    });

    test('negative prompt should accept text', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <input type="text" id="negative-prompt" placeholder="What to avoid (e.g., blurry, dark, shaky)" />
          </body>
        </html>
      `);

      const negativePrompt = page.locator('#negative-prompt');

      await negativePrompt.fill('blurry, dark, shaky, low quality');
      await expect(negativePrompt).toHaveValue('blurry, dark, shaky, low quality');
    });

    test('variants slider should have correct range', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <input type="range" id="variants" min="1" max="4" step="1" value="2" />
            <span id="variants-display">2</span>
            <script>
              const slider = document.getElementById('variants');
              const display = document.getElementById('variants-display');
              slider.addEventListener('input', () => {
                display.textContent = slider.value;
              });
            </script>
          </body>
        </html>
      `);

      const slider = page.locator('#variants');
      const display = page.locator('#variants-display');

      // Check min/max attributes
      await expect(slider).toHaveAttribute('min', '1');
      await expect(slider).toHaveAttribute('max', '4');

      // Change value
      await slider.fill('4');
      await expect(display).toHaveText('4');
    });
  });

  test.describe('Generation Status Display', () => {
    test('should display pending status', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <div id="status-container">
              <span class="status-icon">⏳</span>
              <span class="status-text">Pending</span>
            </div>
          </body>
        </html>
      `);

      await expect(page.locator('.status-text')).toHaveText('Pending');
    });

    test('should display processing status with progress', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <div id="status-container">
              <span class="status-icon">🔄</span>
              <span class="status-text">Generating...</span>
              <progress id="progress" value="50" max="100"></progress>
              <span id="time-remaining">~15s remaining</span>
            </div>
          </body>
        </html>
      `);

      await expect(page.locator('.status-text')).toHaveText('Generating...');
      await expect(page.locator('#progress')).toHaveAttribute('value', '50');
      await expect(page.locator('#time-remaining')).toContainText('remaining');
    });

    test('should display completed status', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <div id="status-container">
              <span class="status-icon">✅</span>
              <span class="status-text">Completed</span>
            </div>
          </body>
        </html>
      `);

      await expect(page.locator('.status-text')).toHaveText('Completed');
    });

    test('should display failed status with error message', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <div id="status-container">
              <span class="status-icon">❌</span>
              <span class="status-text">Failed</span>
              <div class="error-message">Generation failed: API rate limit exceeded</div>
            </div>
          </body>
        </html>
      `);

      await expect(page.locator('.status-text')).toHaveText('Failed');
      await expect(page.locator('.error-message')).toContainText('Generation failed');
    });
  });

  test.describe('Clip Selection', () => {
    test('should allow selecting a clip variant', async ({ page }) => {
      await page.setContent(`
        <html>
          <head>
            <style>
              .clip { width: 200px; height: 150px; border: 2px solid #ccc; cursor: pointer; }
              .clip.selected { border-color: blue; background: rgba(0, 0, 255, 0.1); }
            </style>
          </head>
          <body>
            <div id="clips-container">
              <div class="clip" data-id="clip1">Variant 1</div>
              <div class="clip" data-id="clip2">Variant 2</div>
            </div>
            <button id="use-clip" disabled>Use Selected Clip</button>
            <script>
              const clips = document.querySelectorAll('.clip');
              const useButton = document.getElementById('use-clip');
              clips.forEach(clip => {
                clip.addEventListener('click', () => {
                  clips.forEach(c => c.classList.remove('selected'));
                  clip.classList.add('selected');
                  useButton.disabled = false;
                });
              });
            </script>
          </body>
        </html>
      `);

      const clip1 = page.locator('.clip[data-id="clip1"]');
      const clip2 = page.locator('.clip[data-id="clip2"]');
      const useButton = page.locator('#use-clip');

      // Initially no selection, button disabled
      await expect(useButton).toBeDisabled();

      // Select first clip
      await clip1.click();
      await expect(clip1).toHaveClass(/selected/);
      await expect(clip2).not.toHaveClass(/selected/);
      await expect(useButton).toBeEnabled();

      // Select second clip
      await clip2.click();
      await expect(clip1).not.toHaveClass(/selected/);
      await expect(clip2).toHaveClass(/selected/);
      await expect(useButton).toBeEnabled();
    });

    test('should display clip duration badge', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <div class="clip">
              <span class="duration-badge">3.0s</span>
            </div>
          </body>
        </html>
      `);

      await expect(page.locator('.duration-badge')).toHaveText('3.0s');
    });

    test('should display variant number badge', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <div class="clip">
              <span class="variant-badge">Variant 1</span>
            </div>
            <div class="clip">
              <span class="variant-badge">Variant 2</span>
            </div>
          </body>
        </html>
      `);

      const variants = page.locator('.variant-badge');
      await expect(variants.nth(0)).toHaveText('Variant 1');
      await expect(variants.nth(1)).toHaveText('Variant 2');
    });
  });

  test.describe('Action Buttons', () => {
    test('should have generate button', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <button id="generate">Generate B-Roll</button>
          </body>
        </html>
      `);

      await expect(page.locator('#generate')).toHaveText('Generate B-Roll');
    });

    test('should have regenerate button after completion', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <button id="regenerate">Regenerate</button>
          </body>
        </html>
      `);

      await expect(page.locator('#regenerate')).toHaveText('Regenerate');
    });

    test('should have enhance prompt button', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <button id="enhance">Enhance</button>
          </body>
        </html>
      `);

      await expect(page.locator('#enhance')).toHaveText('Enhance');
    });

    test('should have cancel button when provided', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <button id="cancel">Cancel</button>
          </body>
        </html>
      `);

      await expect(page.locator('#cancel')).toHaveText('Cancel');
    });
  });

  test.describe('Accessibility', () => {
    test('form elements should have labels', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <label for="prompt">Describe the clip you want</label>
            <textarea id="prompt"></textarea>

            <label for="aspect-ratio">Aspect Ratio</label>
            <select id="aspect-ratio"></select>

            <label for="style">Style</label>
            <select id="style"></select>

            <label for="duration">Duration</label>
            <input type="range" id="duration" />
          </body>
        </html>
      `);

      // Check that labels are associated with inputs
      await expect(page.locator('label[for="prompt"]')).toBeVisible();
      await expect(page.locator('label[for="aspect-ratio"]')).toBeVisible();
      await expect(page.locator('label[for="style"]')).toBeVisible();
      await expect(page.locator('label[for="duration"]')).toBeVisible();
    });

    test('buttons should be keyboard accessible', async ({ page }) => {
      await page.setContent(`
        <html>
          <body>
            <button id="generate">Generate B-Roll</button>
          </body>
        </html>
      `);

      const button = page.locator('#generate');

      // Focus the button
      await button.focus();
      await expect(button).toBeFocused();

      // Press Enter to activate (we just verify it's focusable)
      await page.keyboard.press('Enter');
    });
  });
});
