# Marketing Campaign AI - Remotion Compositions

This package contains Remotion video compositions for rendering marketing ad videos.

## Compositions

| ID | Aspect Ratio | Resolution | Use Cases |
|----|--------------|------------|-----------|
| `vertical_ad_v1` | 9:16 | 1080x1920 | Stories, Reels, TikTok, YouTube Shorts |
| `horizontal_ad_v1` | 16:9 | 1920x1080 | YouTube, Facebook Feed, LinkedIn |
| `square_ad_v1` | 1:1 | 1080x1080 | Instagram Feed, Facebook Feed |

## Segment Types

- **video_clip** - User-uploaded video clips with trimming
- **generated_broll** - AI-generated B-Roll (Veo 2) with placeholder support
- **text_slide** - Text-based slides with brand styling

## Features

- Text overlays with animations (fade, pop, slide, typewriter)
- Transitions (cut, dissolve, fade, wipe, slide, zoom)
- Audio tracks with fade in/out
- Brand profile styling (colors, fonts, logo)
- Dynamic duration based on payload

## Development

```bash
# Start Remotion Studio
npm start

# Type check
npm run typecheck

# Build bundle
npm run build

# Render specific composition
npm run render:vertical
npm run render:horizontal
npm run render:square
```

## Payload Schema

The compositions accept a `RemotionPayload` object that matches the backend schema at `app/schemas/remotion_payload.py`.

Key fields:
- `composition_id` - Which composition to use
- `width`, `height`, `fps` - Video dimensions and frame rate
- `duration_in_frames` - Total video length
- `timeline` - Array of `TimelineSegment` objects
- `brand_profile` - Brand styling (colors, fonts, logo)
- `audio_track` - Background audio configuration

See `src/sample-payload.ts` for example payloads.

## Integration

The compositions are designed to receive payloads from the `DirectorAgent` service which assembles timelines from visual scripts and user content.

Rendering can be triggered via:
1. **Remotion CLI** - Local development/testing
2. **Remotion Lambda** - Production cloud rendering
3. **@remotion/renderer** - Programmatic Node.js rendering
