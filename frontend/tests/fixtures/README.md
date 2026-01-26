# Test Fixtures

This directory contains test files used by Playwright end-to-end tests.

## Required Test Files

### test-video.mp4

A sample video file is required for testing video playback functionality in the critique page.

**Requirements:**
- Format: MP4
- Duration: 10-30 seconds
- Size: Under 20MB
- Content: Any simple video (e.g., a screen recording, stock footage, or generated test video)

**How to create a test video:**

1. **Using FFmpeg** (recommended for creating a simple test video):
   ```bash
   # Create a 10-second test video with a color gradient
   ffmpeg -f lavfi -i testsrc=duration=10:size=1280x720:rate=30 -pix_fmt yuv420p test-video.mp4
   ```

2. **Using a screen recording tool:**
   - Record a 10-second screen recording
   - Save as test-video.mp4

3. **Download a sample video:**
   - Find any short video clip (royalty-free)
   - Convert to MP4 if needed
   - Save as test-video.mp4

**Placement:**
Place the `test-video.mp4` file in this directory (`frontend/tests/fixtures/`).

## Running the Tests

Once you have the test video in place, run the Playwright tests:

```bash
# Install Playwright browsers (first time only)
npx playwright install

# Run all tests
npm run test:e2e

# Run tests in headed mode (see the browser)
npm run test:e2e -- --headed

# Run only the critique video playback tests
npm run test:e2e critique-video-playback
```

## Note

The test files in this directory should **not** be committed to the repository if they are large. Consider adding them to `.gitignore` if they exceed a reasonable size.
