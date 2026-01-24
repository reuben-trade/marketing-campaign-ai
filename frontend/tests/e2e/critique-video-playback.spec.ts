import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('Critique Video Playback', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/critique');
  });

  test('should display video player with timeline after uploading a video', async ({ page }) => {
    // Create a test video file path
    const videoPath = path.join(__dirname, '../fixtures/test-video.mp4');

    // Check if file upload dropzone exists
    const dropzone = page.locator('input[type="file"]');
    await expect(dropzone).toBeAttached();

    // Upload a video file
    await dropzone.setInputFiles(videoPath);

    // Fill in optional context (optional but good practice)
    await page.fill('#brand_name', 'Test Brand');
    await page.fill('#industry', 'Technology');

    // Click analyze button
    await page.click('button:has-text("Analyze Creative")');

    // Wait for analysis to complete (may take time)
    await page.waitForSelector('text=Overall Grade', { timeout: 60000 });

    // Check that video player is visible
    const videoPlayer = page.locator('video');
    await expect(videoPlayer).toBeVisible();

    // Check that video source is set
    const videoSrc = await videoPlayer.getAttribute('src');
    expect(videoSrc).toBeTruthy();
    expect(videoSrc).toContain('blob:');

    // Check that timeline visualization exists
    const timeline = page.locator('.relative.h-6.bg-gray-200');
    await expect(timeline).toBeVisible();

    // Check that beat segments are present
    const beatSegments = page.locator('button[title*="Hook"]').or(
      page.locator('button[title*="Problem"]')
    );
    const beatCount = await beatSegments.count();
    expect(beatCount).toBeGreaterThan(0);
  });

  test('should have functional video controls', async ({ page }) => {
    const videoPath = path.join(__dirname, '../fixtures/test-video.mp4');

    // Upload and analyze
    await page.locator('input[type="file"]').setInputFiles(videoPath);
    await page.click('button:has-text("Analyze Creative")');
    await page.waitForSelector('video', { timeout: 60000 });

    // Check play/pause button exists
    const playPauseButton = page.locator('button:has(svg.lucide-play)').or(
      page.locator('button:has(svg.lucide-pause)')
    );
    await expect(playPauseButton).toBeVisible();

    // Check skip back button exists
    const skipBackButton = page.locator('button:has(svg.lucide-skip-back)');
    await expect(skipBackButton).toBeVisible();

    // Check skip forward button exists
    const skipForwardButton = page.locator('button:has(svg.lucide-skip-forward)');
    await expect(skipForwardButton).toBeVisible();

    // Click play button
    await playPauseButton.click();

    // Wait a bit and check if video is playing
    await page.waitForTimeout(500);
    const video = page.locator('video');
    const isPaused = await video.evaluate((v: HTMLVideoElement) => v.paused);
    expect(isPaused).toBe(false);

    // Click pause button
    await playPauseButton.click();
    await page.waitForTimeout(200);
    const isPausedAfter = await video.evaluate((v: HTMLVideoElement) => v.paused);
    expect(isPausedAfter).toBe(true);
  });

  test('should display current beat indicator while video plays', async ({ page }) => {
    const videoPath = path.join(__dirname, '../fixtures/test-video.mp4');

    // Upload and analyze
    await page.locator('input[type="file"]').setInputFiles(videoPath);
    await page.click('button:has-text("Analyze Creative")');
    await page.waitForSelector('video', { timeout: 60000 });

    // Start playing the video
    const playButton = page.locator('button:has(svg.lucide-play)').first();
    await playButton.click();

    // Wait for current beat indicator to appear
    await page.waitForSelector('.bg-gray-50.rounded-lg:has-text("Hook")', { timeout: 5000 });

    // Check that current beat indicator is visible
    const beatIndicator = page.locator('.bg-gray-50.rounded-lg').filter({ hasText: /Hook|Problem|Solution/ });
    await expect(beatIndicator).toBeVisible();

    // Check that beat type badge is displayed
    const beatBadge = beatIndicator.locator('.badge, [class*="badge"]');
    await expect(beatBadge).toBeVisible();

    // Check that timestamp is displayed
    const timestamp = beatIndicator.locator('text=/\\d{2}:\\d{2}/');
    await expect(timestamp).toBeVisible();
  });

  test('should navigate to beat when clicking on timeline segment', async ({ page }) => {
    const videoPath = path.join(__dirname, '../fixtures/test-video.mp4');

    // Upload and analyze
    await page.locator('input[type="file"]').setInputFiles(videoPath);
    await page.click('button:has-text("Analyze Creative")');
    await page.waitForSelector('video', { timeout: 60000 });

    // Find a beat segment in the timeline
    const beatSegment = page.locator('button[title*=":"]').first();
    await expect(beatSegment).toBeVisible();

    // Get the beat's start time from the title
    const title = await beatSegment.getAttribute('title');
    expect(title).toBeTruthy();

    // Click on the beat segment
    await beatSegment.click();

    // Wait a bit for video to seek
    await page.waitForTimeout(500);

    // Check that video is playing
    const video = page.locator('video');
    const isPaused = await video.evaluate((v: HTMLVideoElement) => v.paused);
    expect(isPaused).toBe(false);

    // Check that current beat indicator updates
    const beatIndicator = page.locator('.bg-gray-50.rounded-lg').filter({ hasText: /Hook|Problem|Solution/ });
    await expect(beatIndicator).toBeVisible();
  });

  test('should navigate beats using skip buttons', async ({ page }) => {
    const videoPath = path.join(__dirname, '../fixtures/test-video.mp4');

    // Upload and analyze
    await page.locator('input[type="file"]').setInputFiles(videoPath);
    await page.click('button:has-text("Analyze Creative")');
    await page.waitForSelector('video', { timeout: 60000 });

    // Click skip forward button
    const skipForwardButton = page.locator('button:has(svg.lucide-skip-forward)');
    await skipForwardButton.click();

    // Wait for beat change
    await page.waitForTimeout(500);

    // Check that video is playing
    const video = page.locator('video');
    const isPaused = await video.evaluate((v: HTMLVideoElement) => v.paused);
    expect(isPaused).toBe(false);

    // Check that current time has changed
    const currentTime = await video.evaluate((v: HTMLVideoElement) => v.currentTime);
    expect(currentTime).toBeGreaterThan(0);

    // Click skip back button
    const skipBackButton = page.locator('button:has(svg.lucide-skip-back)');
    await skipBackButton.click();

    // Wait for beat change
    await page.waitForTimeout(500);

    // Check that current time has changed back
    const newCurrentTime = await video.evaluate((v: HTMLVideoElement) => v.currentTime);
    expect(newCurrentTime).toBeLessThan(currentTime);
  });

  test('should display beat-by-beat analysis section for videos', async ({ page }) => {
    const videoPath = path.join(__dirname, '../fixtures/test-video.mp4');

    // Upload and analyze
    await page.locator('input[type="file"]').setInputFiles(videoPath);
    await page.click('button:has-text("Analyze Creative")');
    await page.waitForSelector('text=Overall Grade', { timeout: 60000 });

    // Scroll down to beat-by-beat section
    await page.locator('text=Beat-by-Beat Analysis').scrollIntoViewIfNeeded();

    // Check that beat-by-beat section is visible
    const beatSection = page.locator('text=Beat-by-Beat Analysis');
    await expect(beatSection).toBeVisible();

    // Check that description mentions clicking to jump
    const description = page.locator('text=Click on any beat to jump to that part of the video');
    await expect(description).toBeVisible();

    // Check that beats are displayed
    const beatCards = page.locator('button:has-text("Hook")').or(
      page.locator('button:has-text("Problem")')
    );
    const beatCount = await beatCards.count();
    expect(beatCount).toBeGreaterThan(0);
  });

  test('should click on beat card to jump to that section', async ({ page }) => {
    const videoPath = path.join(__dirname, '../fixtures/test-video.mp4');

    // Upload and analyze
    await page.locator('input[type="file"]').setInputFiles(videoPath);
    await page.click('button:has-text("Analyze Creative")');
    await page.waitForSelector('text=Beat-by-Beat Analysis', { timeout: 60000 });

    // Find a beat card in the beat-by-beat section
    const beatCard = page.locator('button').filter({ hasText: /\d{2}:\d{2} - \d{2}:\d{2}/ }).first();
    await beatCard.scrollIntoViewIfNeeded();

    // Click on the beat card
    await beatCard.click();

    // Wait for video to seek
    await page.waitForTimeout(500);

    // Check that video is playing
    const video = page.locator('video');
    const isPaused = await video.evaluate((v: HTMLVideoElement) => v.paused);
    expect(isPaused).toBe(false);

    // Check that the clicked beat card has active styling
    await expect(beatCard).toHaveClass(/bg-blue-50/);
  });

  test('should display timestamp progress during playback', async ({ page }) => {
    const videoPath = path.join(__dirname, '../fixtures/test-video.mp4');

    // Upload and analyze
    await page.locator('input[type="file"]').setInputFiles(videoPath);
    await page.click('button:has-text("Analyze Creative")');
    await page.waitForSelector('video', { timeout: 60000 });

    // Check that current time is displayed as 00:00 initially
    const currentTimeDisplay = page.locator('text=/^\\d{2}:\\d{2}$/').first();
    await expect(currentTimeDisplay).toHaveText('00:00');

    // Start playing
    const playButton = page.locator('button:has(svg.lucide-play)').first();
    await playButton.click();

    // Wait a bit for time to progress
    await page.waitForTimeout(2000);

    // Check that time has progressed
    const timeText = await currentTimeDisplay.textContent();
    expect(timeText).not.toBe('00:00');

    // Check that total duration is displayed
    const durationDisplay = page.locator('text=/^\\d{2}:\\d{2}$/').last();
    const durationText = await durationDisplay.textContent();
    expect(durationText).not.toBe('00:00');
  });
});
