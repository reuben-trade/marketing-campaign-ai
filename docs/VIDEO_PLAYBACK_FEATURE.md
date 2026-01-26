# Video Playback Feature for Critique Page

This document describes the video playback feature implemented for the critique page, allowing users to watch their uploaded videos with synchronized beat-by-beat analysis.

## Overview

Users can now:
- Upload videos and watch them back during analysis
- See synchronized beat-by-beat timeline visualization
- Jump to specific beats by clicking on the timeline or beat cards
- Navigate between beats using skip forward/back buttons
- View saved critiques with their original videos stored in Supabase S3

## Features

### 1. Video Player with Timeline

When a video is uploaded and analyzed, the critique page displays:

- **Video Player**: A full-featured HTML5 video player showing the uploaded video
- **Visual Timeline**: A color-coded timeline showing all narrative beats
  - Each beat is represented as a colored bar (Hook = green, Problem = red, Solution = blue, etc.)
  - The current playhead position is shown with a white indicator
  - Clicking any beat jumps directly to that part of the video

### 2. Playback Controls

Users have full control over video playback:

- **Play/Pause Button**: Toggle video playback
- **Skip Back Button**: Jump to the previous beat
- **Skip Forward Button**: Jump to the next beat
- **Timeline Scrubbing**: Click anywhere on the timeline to seek
- **Timestamp Display**: Shows current time and total duration (e.g., "00:15 / 01:30")

### 3. Current Beat Indicator

While the video plays, a live indicator shows:

- **Beat Type Badge**: The current beat type (Hook, Problem, Solution, etc.)
- **Timestamp Range**: When the beat starts and ends
- **Beat Content**: Audio transcript or visual description of the current beat

### 4. Interactive Beat-by-Beat Section

Below the video player, users can see all beats in a scrollable list:

- Each beat card shows the beat type, timestamp, and content
- Clicking a beat card jumps the video to that section
- The currently playing beat is highlighted with a blue background
- Includes attention scores and improvement notes where available

### 5. Persistent Video Storage

Videos are now stored in Supabase S3 storage, which means:

- Videos persist even after the page is refreshed
- Users can access their videos when loading saved critiques from history
- Videos are automatically deleted when the critique is deleted
- Files are stored in the `critique-files` bucket with organized folder structure

## File Structure

### Backend

**New/Modified Files:**
- `app/config.py` - Added `critique_files_bucket` configuration
- `app/models/critique.py` - Added `file_storage_path` and `file_url` fields
- `app/schemas/critique.py` - Added `file_url` to response schemas
- `app/api/critique.py` - Updated to upload files to storage and return URLs
- `app/utils/supabase_storage.py` - Added `upload_critique_file()` method
- `alembic/versions/011_add_critique_file_storage.py` - Database migration

**Storage Structure:**
```
critique-files/
├── images/
│   └── {critique_id}.jpg
└── videos/
    └── {critique_id}.mp4
```

### Frontend

**Modified Files:**
- `frontend/src/app/critique/page.tsx` - Added video player, timeline, and controls
- `frontend/src/types/critique.ts` - Added `file_url` field to types
- `frontend/src/hooks/useVideoPlayer.ts` - (Already existed) Video player state management

**New Files:**
- `frontend/playwright.config.ts` - Playwright test configuration
- `frontend/tests/e2e/critique-video-playback.spec.ts` - Comprehensive E2E tests
- `frontend/tests/fixtures/README.md` - Instructions for test setup

## Usage

### For Users

1. **Upload a Video**:
   - Go to the critique page
   - Drag & drop or select a video file (MP4, MOV, WebM)
   - Optionally add context (brand name, industry, etc.)
   - Click "Analyze Creative"

2. **Watch During Analysis**:
   - Once analysis completes, the video player appears above the results
   - Use the timeline to see all beats at a glance
   - Click any beat to jump to that part of the video

3. **Review Saved Critiques**:
   - Click on any previous critique in the sidebar
   - The video will load from storage automatically
   - All playback features work the same way

### For Developers

#### Running Tests

```bash
# Navigate to frontend directory
cd frontend

# Install Playwright browsers (first time only)
npx playwright install

# Add a test video to tests/fixtures/test-video.mp4
# See tests/fixtures/README.md for instructions

# Run all E2E tests
npm run test:e2e

# Run tests in headed mode (see the browser)
npm run test:e2e:headed

# Run tests with UI
npm run test:e2e:ui

# Run only critique video playback tests
npm run test:e2e critique-video-playback
```

#### Database Migration

To apply the new database schema:

```bash
# Run from project root
alembic upgrade head
```

This will add the `file_storage_path` and `file_url` columns to the `critiques` table.

#### Setting Up Supabase Storage

1. Create the `critique-files` bucket in Supabase dashboard
2. Set the bucket to **Public** for file access
3. See `docs/SUPABASE_STORAGE_SETUP.md` for detailed instructions

## Technical Implementation

### Video URL Priority

The frontend uses the following logic to determine which video URL to display:

1. **Stored Video URL** (`displayResult.file_url`): If loading a saved critique, use the URL from Supabase storage
2. **Local Blob URL** (`fileUrl`): If analyzing a newly uploaded file, use the temporary blob URL

This ensures videos work both during upload and when loading saved critiques.

### Video Player State Management

The `useVideoPlayer` hook manages all video playback state:

- Tracks current time and duration
- Identifies which beat is currently playing
- Provides methods for play/pause, seeking, and beat navigation
- Handles video events (timeupdate, loadedmetadata, play, pause)

### Storage Upload Flow

When a video is uploaded:

1. File is read into memory as bytes
2. AI analysis is performed on the bytes
3. File is uploaded to Supabase S3 with path: `videos/{critique_id}.{extension}`
4. Public URL is generated for the uploaded file
5. Both storage path and URL are saved to the database
6. URL is returned in the API response for immediate playback

### Cleanup

When a critique is deleted:

1. The database record is deleted
2. The file is automatically removed from Supabase storage
3. This prevents orphaned files and manages storage costs

## Testing

The implementation includes comprehensive E2E tests covering:

- ✅ Video player display after upload
- ✅ Functional play/pause/skip controls
- ✅ Current beat indicator updates
- ✅ Timeline segment click navigation
- ✅ Beat card click navigation
- ✅ Skip forward/back button functionality
- ✅ Timestamp progress display
- ✅ Active beat styling

All tests are located in `frontend/tests/e2e/critique-video-playback.spec.ts`.

## Browser Compatibility

The video player uses standard HTML5 video elements and should work in:

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

Supported video formats:
- MP4 (H.264 + AAC)
- WebM (VP8/VP9 + Vorbis/Opus)
- MOV (QuickTime, may have limited support in some browsers)

## Future Enhancements

Potential improvements for the future:

- [ ] Video scrubbing with thumbnail previews
- [ ] Playback speed controls (0.5x, 1x, 1.5x, 2x)
- [ ] Fullscreen mode
- [ ] Keyboard shortcuts (Space = play/pause, Arrow keys = seek)
- [ ] Picture-in-picture mode
- [ ] Video quality selection
- [ ] Clip downloading for individual beats
- [ ] Side-by-side comparison with reference ads

## Troubleshooting

### Video Won't Play

- **Check video format**: Ensure the video is in a supported format (MP4 recommended)
- **Check file size**: Videos must be under 100MB
- **Check browser console**: Look for CORS or loading errors
- **Try a different browser**: Some formats may not be supported in all browsers

### Video URL Missing

- **Ensure Supabase bucket exists**: The `critique-files` bucket must be created
- **Check bucket permissions**: Bucket must be set to Public
- **Verify storage configuration**: Check `.env` has correct Supabase credentials
- **Check backend logs**: Look for storage upload errors

### Playback Issues

- **Clear browser cache**: Old blob URLs may be cached
- **Reload the page**: This will fetch a fresh video URL
- **Check network tab**: Verify the video file is loading correctly
- **Test with a different video**: The file may be corrupted

## Performance Considerations

### File Size Limits

- **Images**: Max 20MB
- **Videos**: Max 100MB

For larger videos, consider:
- Compressing the video before upload
- Using a lower resolution or bitrate
- Splitting into multiple segments

### Storage Costs

Each video is stored in Supabase S3. To manage costs:

- Monitor storage usage in Supabase dashboard
- Implement retention policies (e.g., delete critiques older than 90 days)
- Compress videos on upload
- Consider upgrading Supabase plan if needed

### Bandwidth

Videos are streamed directly from Supabase S3. For high-traffic applications:

- Enable CDN caching
- Consider using HLS or DASH for adaptive bitrate streaming
- Monitor bandwidth usage

## Support

For issues or questions:

1. Check this documentation
2. Review the test files for examples
3. Check backend logs for error details
4. Open an issue in the project repository
