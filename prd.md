# Product Requirements Document (PRD): Agentic Ad Engine MVP

## 1. Executive Summary

### Objective
Build an "Agentic Video Editor" that enables business owners to transform raw footage into high-performing video ads by leveraging AI-powered analysis and proven competitor ad structures.

### MVP Focus
A streamlined "Upload-to-Ad" pipeline where users:
1. Select a winning competitor ad as a structural template ("recipe")
2. Upload their own raw footage
3. Receive a fully edited video (rendered via Remotion) that they can manually refine

### Differentiation
Unlike generic AI video generators, this system uses the user's **actual footage**, structured by "proven viral recipes" extracted from high-performing ads in their specific niche.

---

## 2. Current State (What's Already Built)

The platform already has substantial infrastructure in place:

### Competitor Intelligence
- **Ad Library Scraper** (`app/services/ad_library_scraper.py`) - Fetches ads from Meta Ad Library
- **Creative Downloader** - Downloads images/videos to Supabase storage
- **Duplicate Detection** - Perceptual hash deduplication
- **Cross-Platform Tracking** - Facebook, TikTok, Google ad presence

### Video Analysis
- **Video Analyzer** (`app/services/video_analyzer.py`) - Gemini 2.0 Flash integration
  - Beat-by-beat narrative breakdown (Hook, Problem, Solution, CTA, etc.)
  - Creative DNA extraction (audience, messaging pillar, production style)
  - Cinematic analysis (camera, lighting, color grading, motion)
  - Rhetorical analysis (logos, pathos, ethos, persuasion techniques)
  - Engagement prediction (hook score, thumb-stop probability, CTR estimate)

### Semantic Search
- **Embedding Service** (`app/services/embedding_service.py`) - OpenAI embeddings (1536-dim)
- **Semantic Search** (`app/services/semantic_search_service.py`) - pgvector similarity search
- **Ad Elements Model** (`app/models/ad_element.py`) - Stores individual beats with timing

### User Upload & Critique
- **Critique System** (`app/api/critique.py`) - Upload video/image for AI analysis
- **Supabase Storage** - File storage with 4 buckets (ad-creatives, strategy-documents, screenshots, critique-files)

### Recommendation Engine
- **Recommendation Service** (`app/services/recommendation_engine.py`)
- Trend analysis, visual direction, script suggestions, A/B test recommendations

### Frontend
- **Next.js 14** with App Router
- **Video Playback** with synchronized beat timeline
- **Ads Library** with filtering and composite scoring
- **Critique Page** with drag-and-drop upload

### Database
- **PostgreSQL** via Supabase (async SQLAlchemy)
- **pgvector** for semantic search
- **12 migrations** tracking schema evolution

---

## 3. MVP Scope (What We're Building)

### Phase 1: Knowledge & Ingestion Enhancements

#### 1.1 User Onboarding Questionnaire
**Purpose:** Capture brand context to inform ad generation

**Implementation:**
- 3-step questionnaire flow:
  1. Industry/Niche selection
  2. Core Offer description
  3. Top 3 Known Competitors (with fallback to manual entry)

**Output:** Brand Profile JSON
```json
{
  "industry": "Home Services",
  "niche": "Plumbing",
  "core_offer": "24/7 Emergency Plumbing Repair",
  "competitors": ["competitor_id_1", "competitor_id_2", "competitor_id_3"],
  "keywords": ["emergency", "fast", "reliable", "affordable"],
  "tone": "professional_friendly",
  "forbidden_terms": ["cheap", "budget"]
}
```

**Files to Create:**
- `app/models/brand_profile.py`
- `app/schemas/brand_profile.py`
- `app/api/onboarding.py`
- `frontend/src/app/onboarding/page.tsx`

---

#### 1.2 Recipe Extraction
**Purpose:** Convert high-performing ads into abstract structural templates

**Logic:**
- Extract from existing analyzed ads (already have beat-by-beat data)
- Abstract the visual structure: timing, beat types, pacing, transitions
- Store as reusable "recipes"

**Recipe Schema:**
```json
{
  "id": "recipe_001",
  "source_ad_id": "ad_123",
  "name": "Fast Hook + Demo + CTA",
  "total_duration_seconds": 30,
  "structure": [
    {
      "beat_type": "hook",
      "duration_range": [1, 3],
      "characteristics": ["fast_cuts", "bold_text", "high_energy"],
      "purpose": "Stop the scroll"
    },
    {
      "beat_type": "problem",
      "duration_range": [3, 5],
      "characteristics": ["relatable_scenario", "pain_point"],
      "purpose": "Identify with viewer"
    },
    {
      "beat_type": "solution",
      "duration_range": [5, 10],
      "characteristics": ["product_demo", "before_after"],
      "purpose": "Show the fix"
    },
    {
      "beat_type": "cta",
      "duration_range": [2, 4],
      "characteristics": ["urgency", "clear_action"],
      "purpose": "Drive conversion"
    }
  ],
  "pacing": "fast",
  "style": "ugc",
  "composite_score": 0.85
}
```

**Files to Create:**
- `app/models/recipe.py`
- `app/schemas/recipe.py`
- `app/services/recipe_extractor.py`
- `app/api/recipes.py`

---

#### 1.3 Inspiration Selection UI
**Purpose:** Allow users to choose structural templates for their ad

**Three Source Options:**
1. **Existing Library** - Browse already-analyzed competitor ads
2. **Upload Reference** - Upload a reference ad (with processing time warning: "Analysis takes 2-3 minutes")
3. **URL Fetch** - Paste ad URL to fetch and analyze (with processing time warning)

**User Flow:**
1. User browses gallery of "Winning Ads" (sorted by composite score)
2. User selects up to 3 ads as "Structure Sources"
3. System extracts/uses existing recipes from selected ads
4. Recipes inform the Content Planning Agent

**Files to Create:**
- `frontend/src/components/inspiration-gallery.tsx`
- `frontend/src/components/inspiration-source-selector.tsx`

---

### Phase 2: User Asset Processing

#### 2.1 Project-Based Uploads
**Purpose:** Organize user's raw footage into discrete ad creation projects

**Project Model:**
```json
{
  "id": "project_001",
  "name": "Summer Sale Ad",
  "brand_profile_id": "brand_123",
  "status": "draft" | "processing" | "ready" | "rendered",
  "inspiration_ads": ["ad_123", "ad_456"],
  "user_prompt": "Focus on the 50% discount, show product in use",
  "created_at": "2026-01-26T...",
  "constraints": {
    "max_videos": 10,
    "max_total_size_mb": 500
  },
  "stats": {
    "videos_uploaded": 5,
    "total_size_mb": 234,
    "segments_extracted": 47
  }
}
```

**Upload Constraints (MVP):**
- Max 10 videos per project
- Max 500MB total per project
- Prevents context window overflow

**Files to Create:**
- `app/models/project.py`
- `app/schemas/project.py`
- `app/api/projects.py`
- `frontend/src/app/projects/page.tsx`
- `frontend/src/app/projects/[id]/page.tsx`

---

#### 2.2 User Content Analysis Pipeline
**Purpose:** Segment and vectorize user uploads for semantic retrieval

**Pipeline (mirrors competitor ad analysis):**
1. **Analysis** - Send full video to Gemini, which returns timestamped segments (no pre-splitting needed)
2. **Vectorization:**
   - Segment-level vector: Describes specific action (e.g., "pouring coffee") with timestamp references
   - Video-level vector: Describes overall theme (e.g., "morning routine")
3. **Storage** - Vectors stored with timestamp metadata (start/end times reference the original file)

**User Video Segment Schema:**
```json
{
  "id": "segment_001",
  "project_id": "project_001",
  "source_file_id": "upload_123",
  "source_file_name": "kitchen_demo.mp4",
  "timestamp_start": 12.5,
  "timestamp_end": 18.3,
  "duration_seconds": 5.8,
  "visual_description": "Close-up of hands installing faucet",
  "action_tags": ["installation", "hands", "faucet", "close-up"],
  "embedding": [0.123, ...],  // 1536-dim
  "thumbnail_url": "s3://...",
  "created_at": "2026-01-26T..."
}
```

**Files to Create:**
- `app/models/user_video_segment.py`
- `app/schemas/user_video_segment.py`
- `app/services/user_content_analyzer.py`

---

### Phase 3: Agentic Core

#### 3.1 Content Planning Agent ("Writer")
**Purpose:** Generate a visual script based on inspiration recipe and user content

**Inputs:**
- Selected inspiration ads/recipes (structural template)
- User's raw content summaries (text descriptions from analysis)
- User prompt (e.g., "Focus on the discount")
- Brand profile (tone, keywords, forbidden terms)

**Process:**
1. Analyze recipe structure (beat types, timing, characteristics)
2. Map user's available content to recipe slots
3. Draft search queries for each slot
4. Generate on-screen text (captions/headlines)
5. Identify hook candidates (can extract from middle of longer clips)

**Output:** Visual Script with Slots
```json
{
  "script_id": "script_001",
  "project_id": "project_001",
  "recipe_id": "recipe_001",
  "total_duration_seconds": 30,
  "slots": [
    {
      "id": "slot_01_hook",
      "beat_type": "hook",
      "target_duration": 3,
      "search_query": "energetic action, product reveal, surprised reaction",
      "overlay_text": "Stop Wasting Money!",
      "text_position": "center",
      "transition_in": null,
      "transition_out": "wipe_right",
      "notes": "Need high-energy opening, look for quick movement"
    },
    {
      "id": "slot_02_problem",
      "beat_type": "problem",
      "target_duration": 5,
      "search_query": "frustrated expression, broken item, leak, mess",
      "overlay_text": "Tired of leaky faucets?",
      "text_position": "bottom",
      "transition_in": "wipe_right",
      "transition_out": "cut",
      "notes": "Show the pain point"
    }
  ],
  "audio_suggestion": "upbeat_trending",
  "pacing_notes": "Fast cuts in hook, slower in demo section"
}
```

**Files to Create:**
- `app/services/content_planner.py`
- `app/schemas/visual_script.py`
- `app/utils/prompts.py` (add CONTENT_PLANNING_PROMPT)

---

#### 3.2 Semantic Retrieval
**Purpose:** Find the best user clips for each script slot

**Process:**
1. For each slot in the visual script, execute the search query
2. Search against user's vectorized segments (project-scoped)
3. Return top-N results per slot with similarity scores

**Search Response:**
```json
{
  "slot_id": "slot_01_hook",
  "results": [
    {
      "segment_id": "segment_023",
      "source_file": "kitchen_demo.mp4",
      "timestamp_start": 45.2,
      "timestamp_end": 48.1,
      "duration": 2.9,
      "visual_description": "Quick pan to shiny new faucet with water running",
      "similarity_score": 0.89,
      "thumbnail_url": "s3://..."
    },
    {
      "segment_id": "segment_007",
      "source_file": "testimonial.mp4",
      "timestamp_start": 0.0,
      "timestamp_end": 2.5,
      "duration": 2.5,
      "visual_description": "Person smiling and giving thumbs up",
      "similarity_score": 0.76,
      "thumbnail_url": "s3://..."
    }
  ]
}
```

**Files to Modify:**
- `app/services/semantic_search_service.py` - Add project-scoped search

---

#### 3.3 Director Agent ("Assembler")
**Purpose:** Select final clips and generate Remotion-compatible payload

**Inputs:**
- Visual Script (from Writer)
- Search Results (from Semantic Retrieval)

**Logic:**
1. **Selection:** Choose best clip for each slot based on:
   - Similarity score
   - Duration match (prefer clips close to target duration)
   - Visual quality indicators

2. **Gap Handling:** When no suitable clip found:
   - Option A: Generate B-Roll with Veo 2 (preferred)
   - Option B: Insert text slide with messaging
   - Store generation prompt for user to modify

3. **Adaptation:** If script asks for "jumping" but only "walking" exists:
   - Rewrite the slot description to match available visual
   - Adjust overlay text if needed

4. **Trend/Meta Mode:** If user selected a specific trend template:
   - Force strict timing adherence
   - Flag any gaps that break the pattern

**Output:** Remotion Payload (see Section 4)

**Files to Create:**
- `app/services/director_agent.py`
- `app/schemas/remotion_payload.py`

---

### Phase 4: Production & Delivery

#### 4.1 Remotion Integration
**Purpose:** Render the final video from the assembled payload

**Architecture:**

**Backend:**
- Receive Remotion payload from Director Agent
- Send to Remotion Lambda for cloud rendering
- Store rendered MP4 in Supabase
- Return video URL to frontend

**Frontend:**
- Embed Remotion Player for real-time preview
- Display timeline with clickable slots
- Enable basic editing:
  - Click slot → "Replace" modal showing other search results
  - Edit text fields directly
  - Adjust timing (within constraints)

**Remotion Composition:**
- `vertical_ad_v1` - 9:16 aspect ratio (Stories/Reels/TikTok)
- `horizontal_ad_v1` - 16:9 aspect ratio (YouTube/Facebook Feed)
- `square_ad_v1` - 1:1 aspect ratio (Instagram Feed)

**Files to Create:**
- `app/services/remotion_renderer.py`
- `app/api/render.py`
- `frontend/src/components/remotion-player.tsx`
- `frontend/src/components/timeline-editor.tsx`
- `frontend/src/app/projects/[id]/editor/page.tsx`

**Infrastructure:**
- Remotion Lambda deployment (AWS)
- IAM roles for S3 access
- API Gateway endpoint

---

#### 4.2 Veo 2 B-Roll Generation
**Purpose:** Generate video clips when no suitable user footage exists

**Trigger:** Director Agent determines no clip meets threshold (similarity < 0.5)

**Process:**
1. Director generates descriptive prompt based on slot requirements
2. Call Veo 2 API with prompt
3. Return generated clip options (2-3 variants)
4. User selects preferred option OR modifies prompt to regenerate

**User Controls (in editor):**
- "Regenerate" button - Generate new options with same prompt
- "Edit Prompt" - Modify the generation prompt
- "Use My Clip" - Override with manual clip selection

**Veo 2 Request:**
```json
{
  "prompt": "Close-up of water dripping from a leaky faucet, cinematic lighting, slow motion",
  "duration_seconds": 3,
  "aspect_ratio": "9:16",
  "style": "realistic"
}
```

**Files to Create:**
- `app/services/veo_generator.py`
- `app/schemas/veo_request.py`
- `frontend/src/components/broll-generator.tsx`

---

### Phase 5: Video Generation Quality Overhaul (Sprint 5)

#### 5.1 Async File Processing
**Purpose:** Files auto-processed by Gemini on upload (no "Analyze" button needed)

- Background Celery task triggers automatically on file upload
- UI shows processing status with polling
- Users see real-time progress without manual intervention

#### 5.2 Enhanced Video Analysis
**Purpose:** Richer clip metadata for intelligent director decisions

**Clip Ordering (Doubly-Linked List):**
```json
{
  "previous_segment_id": "uuid",
  "next_segment_id": "uuid",
  "segment_index": 2,
  "total_segments_in_source": 8
}
```
Director understands inherent ordering to maintain narrative flow.

**Full Transcript Extraction:**
```json
{
  "transcript_text": "Hey guys, today we're going to...",
  "transcript_words": [
    {"word": "Hey", "start": 0.0, "end": 0.3},
    {"word": "guys", "start": 0.35, "end": 0.6}
  ],
  "speaker_label": "speaker_1"
}
```

**V2 Analysis Fields (shared with competitor analysis):**
- `beat_type`: hook, problem, solution, showcase, cta, testimonial
- `attention_score`: 1-10 thumb-stop potential
- `emotion_intensity`: 1-10
- `color_grading`, `lighting_style`
- `has_speech`: boolean
- `power_words_detected`: ["free", "guaranteed", "exclusive"]

#### 5.3 Director Agent Refactor
**Purpose:** Clips-first approach where Director works with available material

**Inputs to Director:**
1. **Available Remotion Components** (with descriptions/capabilities)
2. **Clip Inventory** (analyzed clips with all metadata)
3. **Competitor Inspiration** (pacing, style breakdown from recipe)
4. **User Instructions** (free-text creative direction)
5. **Brand Profile** (colors, tone, keywords, forbidden terms)

**Director JSON Output Schema:**
```json
{
  "video_settings": {
    "aspect_ratio": "9:16",
    "background_music_mood": "upbeat | lo-fi | corporate",
    "primary_color": "#FF5733",
    "font_family": "modern_sans | bold_serif | handwriting"
  },
  "timeline": [
    {
      "type": "main_clip | b_roll_overlay | title_card | text_slide",
      "start_time_in_video": "00:00",
      "duration_seconds": 3.5,
      "source_clip_id": "segment_uuid",
      "segment_start": 12.5,
      "segment_end": 16.0,
      "actions": {
        "audio_volume": 1.0,
        "caption_text": "Stop Wasting Money!",
        "visual_zoom": "none | slow_zoom_in | sudden_zoom",
        "transition_out": "none | fade | slide_left | whip_pan"
      }
    }
  ],
  "captions": [
    {
      "text": "Stop wasting money",
      "start_time": 0.5,
      "end_time": 2.0,
      "highlight_words": ["wasting", "money"]
    }
  ]
}
```

#### 5.3.1 Director Agent Prompt

```
# Role: The Viral Director Agent
You are an expert Video Ad Director & Editor. Your goal is to take raw video analysis,
user constraints, and competitor inspiration to architect a high-converting, viral video ad.

# Available Remotion Components
1. **main_clip** - Primary video footage with preserved audio
2. **b_roll_overlay** - Overlay video while main audio continues (J-Cut/L-Cut)
3. **title_card** - Animated text screen with branding
4. **text_slide** - Full-screen text with background

# Inputs Provided
1. **Clip Inventory:** Chronological clips with transcripts, beat types, emotions, sequence context
2. **User Context:** Business name, core offer, target audience, "Must Haves"
3. **User Instructions:** Specific direction (e.g., "Focus on the discount")
4. **Competitor Inspiration:** Winning ad style breakdown (pacing, tone)
5. **Style Preferences:** Brand colors, fonts, mood

# Video Editing "Physics" (Constraints)
1. **Total Duration:** 15-60s (Target 30s)
2. **The Hook:** First 3 seconds MUST be visually engaging. Never start with silence.
3. **Pacing:** No clip >4 seconds without visual change (cut, zoom, text, B-roll)
4. **Audio Continuity:** Main speaker audio flows continuously. B-roll overlays video only.
5. **CTA:** Every video ends with clear visual and audio call-to-action.
6. **Captions:** Generate captions using transcript_words. Highlight power words.

# Task: Extended Thinking & Script Generation

## Step 1: Creative Reasoning
* Identify the Hook: Which clip has strongest opening?
* Select "Golden Thread": Which clips tell coherent story?
* Inspiration Matching: Mimic competitor pacing with user's footage
* Engagement Hacks: Where to place text overlays? Where to use B-roll?
* User Intent: How does instruction influence direction?

## Step 2: Generate JSON Script
Output JSON matching the schema exactly.
```

#### 5.4 Standalone Editor Route
**Purpose:** Easy access to video generation without navigating through projects

- New `/editor` route prominent in navigation
- Can upload files OR select from existing projects
- Optional inspiration selection from analyzed ads
- Optional instruction field for creative direction
- Auto-creates project when "Generate" clicked

#### 5.5 Navigation Updates
- Add `/editor` to sidebar (prominent position, second item)
- Add `/onboarding` to sidebar (visible after Dashboard)

#### 5.6 Rendering Fixes
- Add verbose logging to `remotion_renderer.py` (command, payload preview, errors)
- Fix empty URL handling in `VideoClipSegment.tsx` (show placeholder)
- Add error boundaries for missing video sources

---

## 4. Data Schemas

### 4.1 Remotion Payload Schema
The critical data structure passed from Director Agent to Remotion renderer:

```json
{
  "composition_id": "vertical_ad_v1",
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "duration_in_frames": 900,
  "props": {
    "project_id": "project_001",
    "brand_profile": {
      "primary_color": "#FF5733",
      "font_family": "Inter",
      "logo_url": "s3://..."
    },
    "audio_track": {
      "url": "s3://audio/trending_upbeat_04.mp3",
      "volume": 0.8,
      "fade_in_frames": 15,
      "fade_out_frames": 30
    },
    "timeline": [
      {
        "id": "segment_01_hook",
        "type": "video_clip",
        "start_frame": 0,
        "duration_frames": 90,
        "source": {
          "url": "s3://user_uploads/video_A.mp4",
          "start_time": 12.5,
          "end_time": 15.5
        },
        "overlay": {
          "text": "Stop Wasting Money!",
          "position": "center",
          "font_size": 48,
          "font_weight": "bold",
          "color": "#FFFFFF",
          "background": "rgba(0,0,0,0.5)",
          "animation": "pop_in"
        },
        "transition_out": {
          "type": "wipe_right",
          "duration_frames": 10
        }
      },
      {
        "id": "segment_02_problem",
        "type": "video_clip",
        "start_frame": 90,
        "duration_frames": 150,
        "source": {
          "url": "s3://user_uploads/video_B.mp4",
          "start_time": 0.0,
          "end_time": 5.0
        },
        "overlay": {
          "text": "Is your sink leaking?",
          "position": "bottom",
          "font_size": 36,
          "color": "#FFFFFF"
        },
        "transition_out": {
          "type": "cut",
          "duration_frames": 0
        }
      },
      {
        "id": "segment_03_broll",
        "type": "generated_broll",
        "start_frame": 240,
        "duration_frames": 90,
        "source": {
          "url": "s3://generated/veo_clip_001.mp4",
          "generation_prompt": "Water dripping from faucet, slow motion",
          "regenerate_available": true
        },
        "overlay": null,
        "transition_out": {
          "type": "fade",
          "duration_frames": 15
        }
      },
      {
        "id": "segment_04_text_slide",
        "type": "text_slide",
        "start_frame": 330,
        "duration_frames": 60,
        "content": {
          "headline": "50% OFF Today Only!",
          "subheadline": "Use code SUMMER50",
          "background_color": "#FF5733",
          "text_color": "#FFFFFF"
        },
        "transition_out": {
          "type": "slide_up",
          "duration_frames": 10
        }
      }
    ]
  }
}
```

### 4.2 Database Schema Additions

#### brand_profiles table
```sql
CREATE TABLE brand_profiles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  industry VARCHAR(100) NOT NULL,
  niche VARCHAR(200),
  core_offer TEXT,
  competitors JSONB,  -- Array of competitor IDs
  keywords JSONB,     -- Array of keywords
  tone VARCHAR(50),
  forbidden_terms JSONB,
  logo_url TEXT,
  primary_color VARCHAR(7),
  font_family VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

#### recipes table
```sql
CREATE TABLE recipes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_ad_id UUID REFERENCES ads(id),
  name VARCHAR(200) NOT NULL,
  total_duration_seconds INTEGER,
  structure JSONB NOT NULL,  -- Array of beat definitions
  pacing VARCHAR(50),
  style VARCHAR(50),
  composite_score FLOAT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

#### projects table
```sql
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name VARCHAR(200) NOT NULL,
  brand_profile_id UUID REFERENCES brand_profiles(id),
  status VARCHAR(50) DEFAULT 'draft',
  inspiration_ads JSONB,     -- Array of ad IDs
  user_prompt TEXT,
  max_videos INTEGER DEFAULT 10,
  max_total_size_mb INTEGER DEFAULT 500,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

#### user_video_segments table
```sql
CREATE TABLE user_video_segments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  source_file_id UUID NOT NULL,
  source_file_name VARCHAR(500),
  source_file_url TEXT,
  timestamp_start FLOAT NOT NULL,
  timestamp_end FLOAT NOT NULL,
  duration_seconds FLOAT,
  visual_description TEXT,
  action_tags JSONB,
  embedding vector(1536),
  thumbnail_url TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_segments_embedding ON user_video_segments
  USING hnsw (embedding vector_cosine_ops);
```

#### user_video_segments enhancements (Sprint 5)
```sql
-- Clip ordering (doubly-linked list)
ALTER TABLE user_video_segments ADD COLUMN previous_segment_id UUID REFERENCES user_video_segments(id);
ALTER TABLE user_video_segments ADD COLUMN next_segment_id UUID REFERENCES user_video_segments(id);
ALTER TABLE user_video_segments ADD COLUMN segment_index INTEGER DEFAULT 0;
ALTER TABLE user_video_segments ADD COLUMN total_segments_in_source INTEGER DEFAULT 1;

-- Transcript fields
ALTER TABLE user_video_segments ADD COLUMN transcript_text TEXT;
ALTER TABLE user_video_segments ADD COLUMN transcript_words JSONB;  -- [{word, start, end}, ...]
ALTER TABLE user_video_segments ADD COLUMN speaker_label VARCHAR(20);

-- V2 analysis fields
ALTER TABLE user_video_segments ADD COLUMN beat_type VARCHAR(30);
ALTER TABLE user_video_segments ADD COLUMN attention_score INTEGER;  -- 1-10
ALTER TABLE user_video_segments ADD COLUMN emotion_intensity INTEGER;  -- 1-10
ALTER TABLE user_video_segments ADD COLUMN color_grading VARCHAR(30);
ALTER TABLE user_video_segments ADD COLUMN lighting_style VARCHAR(30);
ALTER TABLE user_video_segments ADD COLUMN has_speech BOOLEAN DEFAULT false;
ALTER TABLE user_video_segments ADD COLUMN power_words_detected JSONB;

-- Index for ordering queries
CREATE INDEX idx_segments_ordering ON user_video_segments(source_file_id, segment_index);
```

#### visual_scripts table
```sql
CREATE TABLE visual_scripts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  recipe_id UUID REFERENCES recipes(id),
  total_duration_seconds INTEGER,
  slots JSONB NOT NULL,
  audio_suggestion VARCHAR(100),
  pacing_notes TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

#### rendered_videos table
```sql
CREATE TABLE rendered_videos (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  composition_id VARCHAR(100),
  remotion_payload JSONB,
  status VARCHAR(50) DEFAULT 'pending',
  video_url TEXT,
  thumbnail_url TEXT,
  duration_seconds FLOAT,
  file_size_bytes BIGINT,
  render_time_seconds FLOAT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 5. Technical Architecture

### Backend Additions

| File | Purpose |
|------|---------|
| `app/models/brand_profile.py` | Brand Profile SQLAlchemy model |
| `app/models/recipe.py` | Recipe SQLAlchemy model |
| `app/models/project.py` | Project SQLAlchemy model |
| `app/models/user_video_segment.py` | User video segment model |
| `app/models/visual_script.py` | Visual script model |
| `app/models/rendered_video.py` | Rendered video tracking |
| `app/schemas/brand_profile.py` | Pydantic schemas |
| `app/schemas/recipe.py` | Pydantic schemas |
| `app/schemas/project.py` | Pydantic schemas |
| `app/schemas/user_video_segment.py` | Pydantic schemas |
| `app/schemas/visual_script.py` | Pydantic schemas |
| `app/schemas/remotion_payload.py` | Remotion payload schema |
| `app/schemas/veo_request.py` | Veo 2 request/response schemas |
| `app/api/onboarding.py` | Onboarding endpoints |
| `app/api/recipes.py` | Recipe CRUD endpoints |
| `app/api/projects.py` | Project management endpoints |
| `app/api/render.py` | Rendering endpoints |
| `app/services/recipe_extractor.py` | Extract recipes from analyzed ads |
| `app/services/user_content_analyzer.py` | Analyze user uploads (Gemini returns timestamps) |
| `app/services/content_planner.py` | Writer Agent |
| `app/services/director_agent.py` | Assembler Agent |
| `app/services/remotion_renderer.py` | Remotion Lambda integration |
| `app/services/veo_generator.py` | Veo 2 API integration |

### Frontend Additions

| File | Purpose |
|------|---------|
| `frontend/src/app/onboarding/page.tsx` | Onboarding questionnaire |
| `frontend/src/app/projects/page.tsx` | Project list |
| `frontend/src/app/projects/[id]/page.tsx` | Project detail |
| `frontend/src/app/projects/[id]/upload/page.tsx` | Upload raw footage |
| `frontend/src/app/projects/[id]/inspire/page.tsx` | Select inspiration |
| `frontend/src/app/projects/[id]/create/page.tsx` | Ad creation flow |
| `frontend/src/app/projects/[id]/editor/page.tsx` | Video editor |
| `frontend/src/components/inspiration-gallery.tsx` | Inspiration browser |
| `frontend/src/components/inspiration-source-selector.tsx` | Source type selector |
| `frontend/src/components/remotion-player.tsx` | Embedded Remotion player |
| `frontend/src/components/timeline-editor.tsx` | Timeline with editable slots |
| `frontend/src/components/clip-swap-modal.tsx` | Replace clip modal |
| `frontend/src/components/broll-generator.tsx` | Veo 2 generation UI |
| `frontend/src/components/upload-progress.tsx` | Multi-file upload progress |

### Infrastructure

| Component | Technology | Notes |
|-----------|------------|-------|
| Remotion Lambda | AWS Lambda + S3 | Cloud video rendering |
| Veo 2 API | Google Cloud | B-Roll generation |
| Extended Storage | Supabase S3 | New buckets: `user-uploads`, `rendered-videos`, `generated-broll` |

---

## 6. Implementation Order

Following the "Full Pipeline First" priority:

### Sprint 1: Foundation (Project & Upload Infrastructure)
1. Create database migrations for new tables
2. Implement Project model + API endpoints
3. Build user upload pipeline:
   - Multi-file upload to Supabase
   - Gemini analysis (returns timestamped segments directly)
   - Embedding generation + storage
4. Extract recipes from existing analyzed ads
5. Frontend: Project creation + upload flow

### Sprint 2: Agentic Core (Writer & Director)
6. Implement Content Planning Agent (Writer)
   - Create planning prompt
   - Generate visual scripts with slots
7. Implement project-scoped semantic retrieval
8. Implement Director Agent (Assembler)
   - Clip selection logic
   - Gap detection
   - Remotion payload generation
9. Frontend: Inspiration selection UI

### Sprint 3: Rendering (Remotion Integration)
10. Set up Remotion Lambda infrastructure
11. Create Remotion compositions (vertical, horizontal, square)
12. Implement render service + API
13. Embed Remotion Player in frontend
14. Build timeline editor (slot selection, text editing)

### Sprint 4: Polish (B-Roll & Onboarding)
15. Integrate Veo 2 for B-Roll generation
16. Build regeneration/prompt editing UI
17. Implement user onboarding questionnaire
18. Add "Upload reference ad" and "Fetch from URL" options
19. End-to-end testing + bug fixes

### Sprint 5: Video Generation Quality Overhaul

**Architecture: "The Lego Method"**
Pre-build reliable Remotion components (Lego bricks), then have the Director Agent output a strict JSON Script that tells the rendering engine which bricks to place and where. This is model-agnostic (swap DeepSeek/Gemini/Claude) and prevents LLM syntax errors from breaking builds.

**Parallel Group A - Remotion Components (Frontend):**
20. Create BRollOverlay component (video-over-video with J-Cut/L-Cut audio continuity)
21. Create TitleCard component (animated title cards with branding)
22. Create CaptionOverlay component (timestamped captions synced to transcripts)
23. Create SplitScreen component (side-by-side comparisons)

**Parallel Group B - Enhanced Video Analysis (Backend):**
24. Add transcript extraction (full text + word-level timestamps for captions)
25. Add clip ordering (doubly-linked list: previous_segment_id, next_segment_id, segment_index)
26. Add V2 analysis fields (beat_type, attention_score, emotion_intensity, power_words)

**Parallel Group C - Director Schema (Backend):**
27. Create Director JSON output schema (strict Pydantic schema matching Remotion components)
28. Create Director prompt with viral constraints (3-second rule, Hook-Value-CTA, audio continuity)

**Parallel Group D - UI Updates (Frontend):**
29. Update navigation (add /editor prominent, add /onboarding)
30. Create quick-create project API for standalone editor

**Parallel Group E - Rendering Fixes:**
31. Add verbose logging to Remotion renderer
32. Fix empty URL handling in VideoClipSegment

**Phase 2 (After Groups A, B, C):**
33. Update BaseAdComposition for new segment types
34. Create JSON validation & repair pipeline
35. Create standalone /editor page (upload OR select projects, optional inspiration, instruction field)

**Phase 3 (After Phase 2):**
36. Refactor DirectorAgent to clips-first approach (receives components, clips, inspiration, instructions)
37. Add terminal debug output to Director

**Phase 4 - Async Processing (After Group B):**
38. Create Celery task for auto-analysis on upload
39. Trigger analysis automatically on file upload
40. Remove "Analyze" button, add status polling UI

---

## 7. Success Criteria

### Functional Requirements
- [ ] User can complete onboarding questionnaire and create Brand Profile
- [ ] User can create a project and upload raw footage (up to 10 videos / 500MB)
- [ ] System segments and vectorizes all uploaded videos
- [ ] User can browse inspiration ads from library, upload reference, or fetch URL
- [ ] Recipes are extracted from selected inspiration ads
- [ ] Writer Agent generates visual script with searchable slots
- [ ] Semantic retrieval finds relevant user clips for each slot
- [ ] Director Agent assembles clips into valid Remotion payload
- [ ] Video renders successfully via Remotion Lambda
- [ ] User can preview rendered video in embedded player
- [ ] User can swap clips by clicking slots in timeline
- [ ] User can edit overlay text directly
- [ ] Veo 2 generates B-Roll when no suitable clip is found
- [ ] User can regenerate or modify B-Roll prompt

### Performance Requirements
- [ ] Video analysis (Gemini) completes within 2 minutes per video
- [ ] Semantic search returns results within 500ms
- [ ] Remotion rendering completes within 3 minutes for 30-second ad
- [ ] Veo 2 generation returns clips within 30 seconds

### Quality Requirements
- [ ] Generated ads follow the structural pattern of inspiration
- [ ] Hook is always < 3 seconds and attention-grabbing
- [ ] Text overlays are readable and properly timed
- [ ] Transitions are smooth and professional
- [ ] Audio is properly synced and balanced

---

## 8. API Endpoints Summary

### Onboarding
- `POST /api/onboarding` - Submit questionnaire, create Brand Profile
- `GET /api/onboarding` - Get current Brand Profile
- `PUT /api/onboarding` - Update Brand Profile

### Recipes
- `GET /api/recipes` - List available recipes
- `GET /api/recipes/{id}` - Get recipe details
- `POST /api/recipes/extract` - Extract recipe from ad

### Projects
- `GET /api/projects` - List user's projects
- `POST /api/projects` - Create new project
- `GET /api/projects/{id}` - Get project details
- `PUT /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project
- `POST /api/projects/{id}/upload` - Upload video files
- `GET /api/projects/{id}/segments` - List video segments
- `POST /api/projects/{id}/inspire` - Set inspiration ads
- `POST /api/projects/{id}/generate` - Trigger ad generation

### Rendering
- `POST /api/render` - Start rendering
- `GET /api/render/{id}` - Get render status
- `GET /api/render/{id}/download` - Download rendered video
- `PUT /api/render/{id}/payload` - Update payload (for edits)
- `POST /api/render/{id}/regenerate` - Re-render with changes

### B-Roll
- `POST /api/broll/generate` - Generate B-Roll with Veo 2
- `POST /api/broll/regenerate` - Regenerate with new prompt

---

## 9. User Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ONBOARDING                                     │
│  Industry → Core Offer → Competitors → Brand Profile Created            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         CREATE PROJECT                                   │
│  Name project → Upload raw footage (10 max) → Processing...             │
│  [Segmentation → Analysis → Embedding]                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      SELECT INSPIRATION                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                     │
│  │ From Library │ │ Upload Ad    │ │ Paste URL    │                     │
│  │   (Fast)     │ │ (2-3 min)    │ │ (2-3 min)    │                     │
│  └──────────────┘ └──────────────┘ └──────────────┘                     │
│  Select up to 3 inspiration ads → Recipes extracted                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         AGENTIC CORE                                     │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │ WRITER AGENT                                                 │        │
│  │ Recipe + User Content + Prompt → Visual Script with Slots   │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                              │                                           │
│                              ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │ SEMANTIC RETRIEVAL                                           │        │
│  │ Search queries → Best matching user clips per slot          │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                              │                                           │
│                              ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │ DIRECTOR AGENT                                               │        │
│  │ Select clips → Handle gaps (Veo 2 / Text) → Remotion JSON   │        │
│  └─────────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           EDITOR                                         │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │ [Remotion Player - Preview]                                  │        │
│  │                                                              │        │
│  └─────────────────────────────────────────────────────────────┘        │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │ Timeline: [Hook][Problem][Solution][Demo][CTA]              │        │
│  │           Click to swap clips, edit text                    │        │
│  └─────────────────────────────────────────────────────────────┘        │
│  [Regenerate B-Roll] [Edit Text] [Re-render] [Download]                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Remotion Lambda cold starts | Pre-warm functions, use provisioned concurrency |
| Veo 2 API rate limits | Implement retry with backoff, cache generated clips |
| Large video uploads | Chunk uploads, progress indicators, size validation |
| Poor clip matching | Show multiple options, allow manual override |
| Recipe extraction quality | Start with manual curation, improve over time |
| Context window overflow | Strict upload limits, summarize long descriptions |

---

## 11. Future Enhancements (Post-MVP)

- **Bulk Upload Mode** - "Turn your camera roll into ads"
- **Bucket Logic** - Group footage by location/time/event
- **AI Command Editing** - "Make it pop more" → AI adjusts grading/music
- **Multi-Platform Export** - Auto-resize for TikTok, YouTube, Instagram
- **Voiceover Generation** - AI-generated narration
- **Music Library** - Licensed trending audio tracks
- **Team Collaboration** - Multi-user projects
- **A/B Testing Integration** - Direct publishing to ad platforms
- **Performance Tracking** - Connect ad performance back to recipes

---

*Document Version: 1.0*
*Last Updated: 2026-01-26*
*Status: MVP Specification*
