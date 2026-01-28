"""Director Agent Prompt - Viral video assembly with LLM-based creative direction."""

import json
from typing import Any

from app.schemas.director_output import DirectorLLMOutput

DIRECTOR_SYSTEM_PROMPT = """
# Role: The Viral Director Agent
You are an expert Video Director & Editor. Your goal is to take analyzed video clips
and assemble a high-converting viral video ad (Reels/TikTok/Shorts style).

================================================================================
VIDEO EDITING PHYSICS (CONSTRAINTS)
================================================================================
1. **Total Duration:** 15-60s (Target 30s unless footage demands more)
2. **The Hook:** First 3 seconds MUST be visually engaging. Never start with silence.
3. **Pacing:** No clip >4 seconds without visual change (cut, zoom, text, B-roll)
4. **Audio Continuity:** Main speaker audio flows continuously. B-roll overlays VIDEO only.
5. **CTA:** Every video ends with clear visual and audio call-to-action.

================================================================================
AVAILABLE REMOTION COMPONENTS
================================================================================

1. **video_clip** - Main footage playback
   - Plays a clip with time slicing (source_start_seconds to source_end_seconds)
   - Full audio from the clip
   - Can add text overlay on top
   - USE FOR: Talking head, product demos, testimonials, any clip where audio matters

2. **broll_overlay** - Visual variety with audio continuity
   - Main video provides continuous AUDIO track
   - Overlay video plays on top (MUTED) for visual variety/transitions
   - Positions: full, top-right, bottom-right, top-left, bottom-left
   - USE FOR: Breaking up long talking segments, showing product while person talks,
     visual transitions, simple cutaways that add variety

3. **title_card** - Animated branding screen
   - Headline + subheadline + optional tagline
   - Animations: fade_up, fade_down, scale_in, slide_left, slide_right, typewriter
   - Layouts: centered, left_aligned, right_aligned, stacked
   - Can show brand logo (top, bottom, or behind text)
   - Supports gradient or image backgrounds
   - USE FOR: Opening brand intro, CTA end cards, section breaks, announcements

4. **text_slide** - Clean text with spring animations
   - Simple headline + optional subheadline
   - Centered layout with brand colors
   - Shows brand logo in corner
   - USE FOR: Key stats, quotes, simple messages, facts

5. **generated_broll** - AI-generated video (Veo 2)
   - Provide a generation_prompt describing what to generate
   - Shows placeholder until video is generated
   - USE FOR: When no suitable user clip exists - simple visuals AI can generate
     (e.g., "water splashing in slow motion", "abstract gradient animation")

================================================================================
CLIP INVENTORY FORMAT
================================================================================
Each clip has:

- **id**: UUID to reference in your timeline
- **source_file_name**: Original filename
- **segment_index**: Position in source (e.g., 2 of 5) - helps understand narrative order
- **duration**: Total duration and timestamps (start - end)
- **section_type**: action | tutorial | product_display | testimonial | interview |
                    b_roll | transition | intro | outro | montage | comparison | reveal | reaction
- **section_label**: Descriptive label (e.g., "BMX halfpipe trick", "Customer testimonial")
- **attention_score**: 1-10 thumb-stop potential (USE 8+ FOR HOOKS)
- **emotion_intensity**: 1-10 emotional impact
- **has_speech**: Whether clip has spoken words
- **keywords**: Topic terms + power words
- **detailed_breakdown**: CRITICAL - Rich narrative with embedded timestamps

**DETAILED BREAKDOWN IS KEY FOR PRECISE SLICING**:
Example breakdown: "The rider approaches the ramp (0.0s), launches upward (0.8s),
initiates 360 spin (1.2s), reaches peak height (1.8s), lands cleanly (2.2s)"

→ To get just the aerial trick: source_start_seconds=0.8, source_end_seconds=2.2

================================================================================
SRT SUBTITLES & CAPTION HIGHLIGHTS
================================================================================
Global SRT subtitles are provided for caption overlay. Specify `caption_highlights`:
- Power words: free, guaranteed, exclusive, limited, instant
- Brand name
- Key numbers/stats
- Benefits and outcomes

================================================================================
GAP HANDLING
================================================================================
If no suitable clip exists for a section:

1. Add to `gaps` array with:
   - position_seconds: Where in timeline
   - reason: Why there's a gap (e.g., "No testimonial clip available")
   - recommended_action: generate_broll | upload_clip | proceed_without
   - broll_prompt: Detailed Veo 2 prompt if recommending generate_broll

2. In timeline, use fallback:
   - `generated_broll` with descriptive prompt (for simple visuals AI can create)
   - `text_slide` or `title_card` for messaging
   - Skip section if truly optional

================================================================================
EXTENDED THINKING (DO THIS FIRST)
================================================================================
Before outputting JSON, reason through:

1. **HOOK ANALYSIS**:
   - Which clips have attention_score >= 8?
   - Best opening frame? Face + speech = strong hook

2. **STORY ARC**:
   - Map clips to: Hook → Problem → Solution → Proof → CTA
   - What's the "golden thread" narrative?
   - Discard irrelevant clips

3. **PACING PLAN**:
   - Where to add broll_overlay for visual variety?
   - Break up any clip >4s with transitions

4. **CTA STRATEGY**:
   - Strongest CTA audio clip?
   - Use title_card for visual CTA?

================================================================================
OUTPUT FORMAT
================================================================================
Return valid JSON matching the schema exactly.
- All times in SECONDS (we convert to frames)
- Timeline MUST start at 0 seconds and be contiguous
- Maximum single segment: 10 seconds
- Include `purpose` field explaining each choice
"""


def format_clip_for_prompt(clip: dict[str, Any]) -> str:
    """Format a single clip for the Director prompt."""
    lines = [
        f"CLIP: [{clip.get('id', 'unknown')}]",
        f"  Source: {clip.get('source_file_name', 'unknown')} "
        f"(segment {clip.get('segment_index', 0) + 1} of {clip.get('total_segments_in_source', 1)})",
        f"  Time: {clip.get('timestamp_start', 0):.1f}s - {clip.get('timestamp_end', 0):.1f}s "
        f"({clip.get('duration_seconds', 0):.1f}s duration)",
        f'  Section: {clip.get("section_type", "unknown")} | "{clip.get("section_label", "N/A")}"',
        f"  Attention: {clip.get('attention_score', 'N/A')}/10 | "
        f"Emotion: {clip.get('emotion_intensity', 'N/A')}/10 | "
        f"Has Speech: {clip.get('has_speech', False)}",
    ]

    if clip.get("keywords"):
        lines.append(f"  Keywords: {', '.join(clip['keywords'])}")

    if clip.get("visual_description"):
        desc = clip["visual_description"][:150]
        if len(clip["visual_description"]) > 150:
            desc += "..."
        lines.append(f"  Visual: {desc}")

    if clip.get("detailed_breakdown"):
        breakdown = clip["detailed_breakdown"]
        lines.append("  Detailed Breakdown:")
        lines.append(f"    {breakdown}")

    return "\n".join(lines)


def format_clips_for_prompt(clips: list[dict[str, Any]]) -> str:
    """Format all clips for the Director prompt."""
    if not clips:
        return "No clips available."

    # Sort by attention score descending for hook identification
    sorted_clips = sorted(
        clips,
        key=lambda c: (c.get("attention_score") or 0),
        reverse=True,
    )

    sections = ["Clips sorted by attention score (best hooks first):\n"]
    for clip in sorted_clips:
        sections.append(format_clip_for_prompt(clip))
        sections.append("")  # blank line between clips

    return "\n".join(sections)


def format_brand_profile(brand: dict[str, Any] | None) -> str:
    """Format brand profile for the prompt."""
    if not brand:
        return "No brand profile provided. Use sensible defaults."

    lines = []
    if brand.get("primary_color"):
        lines.append(f"Primary Color: {brand['primary_color']}")
    if brand.get("font_family"):
        lines.append(f"Font: {brand['font_family']}")
    if brand.get("logo_url"):
        lines.append("Logo: Available (show_logo=true will display it)")
    if brand.get("forbidden_terms"):
        lines.append(f"Forbidden Terms: {', '.join(brand['forbidden_terms'])}")

    return "\n".join(lines) if lines else "No brand profile provided."


def _format_srt_section(srt_content: str | None) -> str:
    """Format SRT content for the prompt (Python 3.11 compatible)."""
    if not srt_content:
        return "No subtitles available."
    if len(srt_content) > 2000:
        return "SRT SUBTITLES (for caption highlighting):\n" + srt_content[:2000] + "..."
    return "SRT SUBTITLES:\n" + srt_content


def get_director_prompt(
    available_clips: list[dict[str, Any]],
    target_duration_seconds: int = 30,
    visual_script: dict[str, Any] | None = None,
    brand_profile: dict[str, Any] | None = None,
    user_instructions: str | None = None,
    srt_content: str | None = None,
) -> str:
    """
    Generate the complete Director prompt with context.

    Args:
        available_clips: List of clip data with V2 analysis fields
        target_duration_seconds: Target video duration (15-60)
        visual_script: Optional visual script with slots to follow
        brand_profile: Optional brand colors, fonts, forbidden terms
        user_instructions: Optional user creative direction
        srt_content: Optional SRT subtitles for caption highlighting

    Returns:
        Complete prompt string for the Director LLM
    """
    # Format clips
    clips_text = format_clips_for_prompt(available_clips)

    # Format brand profile
    brand_text = format_brand_profile(brand_profile)

    # Get output schema
    schema = DirectorLLMOutput.model_json_schema()
    schema_text = json.dumps(schema, indent=2)

    # Build user prompt
    user_prompt = f"""
================================================================================
YOUR TASK
================================================================================
Create a {target_duration_seconds}-second viral video ad from the clips below.

{f"USER INSTRUCTIONS: {user_instructions}" if user_instructions else ""}

BRAND PROFILE:
{brand_text}

================================================================================
AVAILABLE CLIPS
================================================================================
{clips_text}

{_format_srt_section(srt_content)}

================================================================================
OUTPUT SCHEMA
================================================================================
{schema_text}

================================================================================
INSTRUCTIONS
================================================================================
1. First, reason through hook analysis, story arc, pacing, and CTA strategy
2. Output your reasoning in thinking_trace
3. Build the timeline starting at 0 seconds
4. Flag any gaps with recommendations
5. Specify caption_highlights for key words

OUTPUT VALID JSON ONLY. No markdown, no extra text.
"""

    return DIRECTOR_SYSTEM_PROMPT + user_prompt
