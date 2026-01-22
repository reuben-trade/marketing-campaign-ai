"""AI prompt templates for ad analysis and recommendations."""

IMAGE_ANALYSIS_PROMPT = """
You are an expert marketing analyst specializing in paid social advertising.

Analyze this ad creative with extreme attention to marketing effectiveness.

MARKETING CRITERIA (rate each 1-10):
1. Hook Strength: Does it grab attention immediately?
2. Message Clarity: Is the value proposition crystal clear?
3. Visual Impact: Production quality, brand consistency, design
4. CTA Effectiveness: Is the call-to-action compelling?
5. Overall Marketing Score: Weighted combination considering target market

STRATEGIC ANALYSIS:
- UVPs: What unique value propositions are highlighted?
- Target Audience: Who is this for? (be specific)
- Emotional Appeal: What emotion is triggered?
- Visual Themes: Colors, composition, style
- CTAs: Specific calls-to-action used
- Marketing Framework: What strategy is employed? (PAS, BAB, social proof, etc.)

COMPETITOR CONTEXT:
Company: {competitor_name}
Market Position: {market_position}
Follower Count: {follower_count}

AD ENGAGEMENT DATA:
Likes: {likes}
Comments: {comments}
Shares: {shares}

Provide your analysis in this exact JSON structure:
{{
  "summary": "2-3 sentence overview of the ad",
  "insights": ["insight 1", "insight 2", "insight 3"],
  "uvps": ["uvp 1", "uvp 2"],
  "ctas": ["cta 1"],
  "visual_themes": ["theme 1", "theme 2"],
  "target_audience": "detailed description",
  "emotional_appeal": "primary emotion",
  "marketing_effectiveness": {{
    "hook_strength": 8,
    "message_clarity": 9,
    "visual_impact": 7,
    "cta_effectiveness": 8,
    "overall_score": 8
  }},
  "strategic_insights": "What marketing strategy/framework is being used and why it works",
  "reasoning": "Detailed explanation of the scores and analysis"
}}

IMPORTANT: Return ONLY valid JSON, no additional text or markdown formatting.
"""

STRATEGY_EXTRACTION_PROMPT = """
You are an expert at extracting business strategy information from documents.

Analyze the following document content and extract structured business strategy information.

Document content:
{document_content}

Extract the following information if available:
1. Business Name
2. Business Description
3. Industry
4. Target Audience (demographics, psychographics, pain points)
5. Brand Voice (tone, personality traits, messaging guidelines)
6. Market Position (challenger, leader, niche)
7. Price Point (premium, mid-market, budget)
8. Business Life Stage (startup, growth, mature)
9. Unique Selling Points
10. Competitive Advantages
11. Marketing Objectives

Provide your extraction in this exact JSON structure:
{{
  "business_name": "Company Name",
  "business_description": "Description of the business",
  "industry": "Industry name",
  "target_audience": {{
    "demographics": "Age, gender, location, income level",
    "psychographics": "Values, interests, lifestyle",
    "pain_points": ["pain point 1", "pain point 2"]
  }},
  "brand_voice": {{
    "tone": "professional/casual/playful",
    "personality_traits": ["trait 1", "trait 2"],
    "messaging_guidelines": "Guidelines for messaging"
  }},
  "market_position": "challenger/leader/niche",
  "price_point": "premium/mid-market/budget",
  "business_life_stage": "startup/growth/mature",
  "unique_selling_points": ["USP 1", "USP 2"],
  "competitive_advantages": ["advantage 1", "advantage 2"],
  "marketing_objectives": ["objective 1", "objective 2"],
  "extraction_confidence": 0.85,
  "missing_fields": ["fields that couldn't be extracted"]
}}

IMPORTANT: Return ONLY valid JSON. Use null for fields that cannot be determined from the document.
"""

RECOMMENDATION_GENERATION_PROMPT = """
You are an expert marketing strategist specializing in creating actionable ad recommendations.

Based on the following analysis of top-performing competitor ads and the target business strategy, generate detailed content recommendations.

BUSINESS STRATEGY:
{business_strategy}

TOP PERFORMING ADS ANALYSIS:
{ads_analysis}

TREND SUMMARY:
- Total ads analyzed: {total_ads}
- Average engagement: {avg_engagement}
- Top visual themes: {visual_themes}
- Top messaging patterns: {messaging_patterns}
- Most effective CTAs: {top_ctas}

Generate comprehensive recommendations following this EXACT JSON structure:

{{
  "executive_summary": "2-3 paragraph summary of findings and recommendations",

  "trend_analysis": {{
    "visual_trends": [
      {{
        "trend": "trend name",
        "prevalence": "percentage of ads using this",
        "description": "what this trend looks like",
        "why_it_works": "psychological/marketing reason",
        "example_ad_ids": ["id1", "id2"]
      }}
    ],
    "messaging_trends": [
      {{
        "trend": "trend name",
        "prevalence": "percentage",
        "description": "description",
        "why_it_works": "reason",
        "example_ad_ids": ["id1"]
      }}
    ],
    "cta_trends": [
      {{
        "trend": "CTA pattern",
        "examples": ["CTA 1", "CTA 2"],
        "effectiveness": "assessment"
      }}
    ],
    "engagement_patterns": {{
      "best_performing_length": "duration for video",
      "optimal_posting_time": "best time",
      "hook_timing": "seconds to grab attention"
    }}
  }},

  "recommendations": [
    {{
      "recommendation_id": 1,
      "priority": "high/medium/low",
      "ad_format": "video/image",
      "duration": "for video only",
      "objective": "campaign objective",

      "concept": {{
        "title": "creative title",
        "description": "concept description",
        "marketing_framework": "PAS/BAB/etc"
      }},

      "visual_direction": {{
        "overall_style": "style description",
        "setting": "environment",
        "color_palette": {{
          "primary": "#hex",
          "secondary": "#hex",
          "accent": "#hex",
          "reasoning": "why these colors"
        }},
        "composition": "composition notes",
        "camera_work": "for video"
      }},

      "script_breakdown": {{
        "hook": {{
          "timing": "0-3 seconds",
          "visual_description": "what's shown",
          "action": "what happens",
          "audio": "sound",
          "on_screen_text": "text overlay",
          "text_style": "styling",
          "why_this_works": "explanation"
        }},
        "problem_agitation": {{ ... }},
        "solution_introduction": {{ ... }},
        "social_proof": {{ ... }},
        "cta": {{ ... }}
      }},

      "caption_strategy": {{
        "necessity": "importance",
        "font": "font choice",
        "size": "size",
        "placement": "where",
        "timing": "when",
        "animations": "motion",
        "emoji_usage": "strategy",
        "background": "text background"
      }},

      "filming_requirements": {{
        "shots_needed": [
          {{
            "shot_type": "wide/medium/close-up",
            "description": "what to capture",
            "duration": "length",
            "purpose": "why needed"
          }}
        ],
        "b_roll": ["item 1", "item 2"],
        "talent": "who's needed",
        "props": "what's needed"
      }},

      "audio_design": {{
        "music": {{
          "style": "genre/mood",
          "tempo": "BPM",
          "energy": "level",
          "when": "usage",
          "reference": "example"
        }},
        "sound_effects": ["sfx 1", "sfx 2"],
        "voiceover": {{
          "tone": "delivery style",
          "gender": "preference",
          "pace": "words per minute",
          "emphasis": "key points"
        }}
      }},

      "targeting_alignment": {{
        "audience": "who this targets",
        "pain_point_addressed": "which pain point",
        "brand_voice_alignment": "how it aligns",
        "price_point_justification": "value messaging"
      }},

      "testing_variants": [
        {{
          "variable": "what to test",
          "variant_a": "option A",
          "variant_b": "option B",
          "hypothesis": "expected outcome"
        }}
      ],

      "success_metrics": {{
        "primary": "main KPI",
        "secondary": ["other KPIs"],
        "optimization": "when to iterate"
      }}
    }}
  ],

  "implementation_roadmap": {{
    "phase_1_immediate": {{
      "action": "first priority",
      "rationale": "why first",
      "timeline": "week range",
      "budget_allocation": "percentage"
    }},
    "phase_2_support": {{
      "action": "second priority",
      "rationale": "why second",
      "timeline": "week range",
      "budget_allocation": "percentage"
    }},
    "testing_protocol": {{
      "duration": "test length",
      "kpis": ["KPI 1", "KPI 2"],
      "decision_criteria": "when to pivot"
    }}
  }}
}}

Generate 2-3 high-quality recommendations. For image ads, use content_breakdown, copywriting, design_specifications, and production_notes instead of video-specific fields.

IMPORTANT: Return ONLY valid JSON, no additional text or markdown formatting.
"""

COMPETITOR_DISCOVERY_PROMPT = """
You are a market research expert. Based on the following business information, identify potential competitors that should be analyzed.

BUSINESS INFORMATION:
Business Name: {business_name}
Industry: {industry}
Business Description: {business_description}
Market Position: {market_position}

Find competitors that:
1. Operate in the same industry
2. Target similar audiences
3. Include both market leaders and direct competitors
4. Are actively advertising on Meta platforms

For each competitor, provide:
- Company name
- Why they're a relevant competitor
- Their likely market position
- Estimated size/follower count range
- Facebook Page ID (numeric ID if you know it - this is critical for accessing their ads)
- Facebook page URL (e.g., facebook.com/CompanyName)

Return your findings in this JSON structure:
{{
  "competitors": [
    {{
      "company_name": "Competitor Name",
      "relevance_reason": "Why they're a competitor",
      "market_position": "leader/challenger/niche",
      "estimated_follower_range": "10K-50K",
      "facebook_page_id": "123456789",
      "facebook_page_url": "https://www.facebook.com/CompanyName"
    }}
  ],
  "research_notes": "Additional context about the competitive landscape"
}}

IMPORTANT:
- Return ONLY valid JSON.
- The facebook_page_id should be a numeric string (e.g., "123456789") if known, or null if unknown.
- The facebook_page_url should be the company's Facebook page URL if known.
"""

# =============================================================================
# V2 PROMPTS - ENHANCED ANALYSIS WITH FULL CREATIVE DNA
# =============================================================================

VIDEO_ANALYSIS_PROMPT_V2 = """
You are an elite Ad Performance Analyst. Your job is to deconstruct this video into its core structural components with precise timestamps.

CONTEXT:
Company: {competitor_name}
Market Position: {market_position}
Follower Count: {follower_count}
Engagement: {likes} Likes, {comments} Comments, {shares} Shares
Brand Name (if provided): {brand_name}
Industry: {industry}
Target Audience Context: {target_audience}

================================================================================
MANDATORY COMPONENT IDENTIFICATION
================================================================================
You MUST identify and timestamp the following "Key Components" if they appear in the ad.
Use the EXACT labels provided - these are the only valid beat_type values:

1. "Hook": The first 1-5 seconds. What specific visual/audio element stops the scroll?
   - Describe the exact attention-grabbing mechanism
   - Note any pattern interrupts or curiosity gaps created

2. "Problem": Where the ad identifies the user's pain point.
   - What problem is being agitated?
   - How is it visualized or verbalized?

3. "Solution": The moment the product/service is first revealed as the answer.
   - This is the "aha" moment - the product introduction

4. "Product Showcase": Specific segments demonstrating HOW the product works or looks.
   - Describe EXACTLY which features are shown
   - Note any before/after demonstrations
   - Detail the product in action

5. "Social Proof": Any user testimonials, 5-star graphics, reviews, or UGC.
   - Include quotes, ratings, or trust signals

6. "Benefit Stack": Sections listing value propositions or feature benefits.
   - Multiple benefits presented in sequence

7. "Objection Handling": Segments addressing potential doubts or concerns.
   - Price justification, guarantee mentions, trust markers

8. "CTA": The final Call to Action (e.g., "Shop Now", "Link in Bio", "Get Started").
   - Include the exact CTA text
   - Note urgency elements (limited time, scarcity)

9. "Transition": Visual bridges between sections that don't fit above categories.

================================================================================
CRITICAL INSTRUCTIONS
================================================================================
- SEGMENTATION: Break the video down by these structural components, not by arbitrary time intervals
- TIMESTAMPING: Be precise (e.g., Hook: 00:00-00:03, Problem: 00:03-00:12)
- DETAIL: For "Product Showcase", describe EXACTLY which features are shown
- For "Hook", describe the specific visual/audio trigger that grabs attention
- Do NOT use any beat_type labels other than those listed above

ANALYSIS REQUIREMENTS:

1. NARRATIVE TIMELINE - For each beat document:
   - Precise timestamps (MM:SS format)
   - Beat type classification
   - Detailed visual description (storyboard-quality)
   - Verbatim audio transcript with [music], [SFX] annotations
   - Emotion evoked and intensity (1-10)
   - Per-beat improvement suggestions

2. RHETORICAL ANALYSIS - For each beat:
   - Primary mode: Logos (facts/logic), Pathos (emotion), Ethos (credibility), Kairos (urgency)
   - Secondary mode if present
   - Specific persuasion techniques (scarcity, social proof, authority, etc.)
   - What objection this beat addresses (if any)

3. CINEMATIC ANALYSIS - For each beat:
   - Camera angle and movement
   - Lighting style
   - Color grading
   - Transitions in/out
   - Key visual elements present

4. TEXT/COPY EXTRACTION:
   - ALL on-screen text verbatim with timestamps
   - Typography and animation style
   - Position on screen
   - Purpose of each text element
   - Identify copywriting framework (PAS, AIDA, BAB, etc.)
   - Power words and sensory language used

5. AUDIO LAYER ANALYSIS:
   - Music: genre, tempo (slow/medium/fast), energy, mood
   - Voice: gender, age range, tone, estimated WPM, accent
   - Sound effects: timestamp each SFX and its purpose
   - Audio-visual sync quality (1-10)
   - Sound-off compatibility assessment

6. BRAND ELEMENT TRACKING:
   - Logo appearances with timestamps, duration, position, size
   - Product appearances with timestamps, shot type, prominence
   - Brand colors detected (hex codes if possible)
   - Brand name mentions (audio count, text count)

7. ENGAGEMENT PREDICTION:
   - Thumb-stop score (1-10) with justification
   - First-frame hook analysis
   - Pattern interrupt type (if any)
   - Curiosity gap assessment
   - Visual contrast score (1-10)
   - Predicted watch-through rate (low/medium/high)

8. PLATFORM OPTIMIZATION:
   - Aspect ratio detection
   - Optimal platforms for this format
   - Caption dependency level (none/low/medium/high)
   - Native feel score (1=polished ad, 10=organic content)
   - Duration assessment (too short/optimal/too long)

9. EMOTIONAL ARC:
   - Track emotion at each major beat
   - Identify emotional climax timestamp
   - Tension/release pattern (gradual/sudden/oscillating/flat)
   - Dominant emotional tone overall

10. ACTIONABLE CRITIQUE:
    - Overall letter grade (A+ to F)
    - 2-3 sentence overall assessment
    - 3-5 specific strengths with evidence and timestamps
    - 3-5 specific weaknesses with fix suggestions
    - 2-4 detailed remake suggestions with effort level
    - Quick wins list (easy fixes)

Return analysis in this EXACT JSON structure:
{{
  "media_type": "video",
  "analysis_version": "2.0",
  "analysis_confidence": 0.85,
  "analysis_notes": [],

  "inferred_audience": "Detailed profile: age, gender, income, lifestyle, pain points, aspirations",
  "primary_messaging_pillar": "Core theme: Cost Savings, Premium Quality, Convenience, Health, Status, etc.",
  "overall_pacing_score": 7,
  "production_style": "High-production Studio | Authentic UGC | Hybrid | Animation | Talking Head | Screen Recording | Stock Footage Mashup | Documentary Style | Influencer Native",
  "hook_score": 8,
  "overall_narrative_summary": "2-3 vivid sentences capturing the ad's story arc and emotional journey",

  "timeline": [
    {{
      "start_time": "00:00",
      "end_time": "00:03",
      "beat_type": "Hook | Problem | Solution | Product Showcase | Social Proof | Benefit Stack | Objection Handling | CTA | Transition",
      "cinematics": {{
        "camera_angle": "Close-up | Wide-shot | POV | Low-angle | Over-the-shoulder | etc.",
        "lighting_style": "High-contrast | Natural/UGC | Studio-soft | Golden-hour | Ring-light",
        "cinematic_features": ["Slow-mo", "Text-overlay", "Split-screen", "B-roll"],
        "color_grading": "warm | cool | desaturated | high-contrast | vintage | natural",
        "motion_type": "static | handheld | dolly | pan | zoom | tracking",
        "transition_in": "cut | dissolve | wipe | zoom | match-cut",
        "transition_out": "cut | dissolve | wipe | zoom | match-cut"
      }},
      "tone_of_voice": "Urgent | Empathetic | ASMR | High-energy | Conversational | Authoritative | Playful",
      "rhetorical_appeal": {{
        "mode": "Logos | Pathos | Ethos | Kairos",
        "description": "How this persuasion technique is executed",
        "secondary_mode": "Logos | Pathos | Ethos | Kairos | null",
        "persuasion_techniques": ["scarcity", "social proof", "authority"],
        "objection_addressed": "What objection this beat handles, or null"
      }},
      "target_audience_cues": "Visual/audio signals identifying the demographic",
      "visual_description": "DETAILED scene: Who appears, what they do, setting, colors, text on screen, products shown. Be specific enough to sketch a storyboard.",
      "audio_transcript": "Exact words in quotes. [music: genre/mood]. [SFX: type]. Include delivery notes.",
      "emotion": "fear | urgency | aspiration | curiosity | belonging | joy | trust | surprise | anticipation | pride | nostalgia | neutral",
      "emotion_intensity": 7,
      "text_overlays_in_beat": [
        {{
          "text": "Exact text verbatim",
          "timestamp": "00:01",
          "duration_seconds": 2.0,
          "position": "top | center | bottom | lower-third",
          "typography": "bold sans-serif | handwritten | serif | kinetic",
          "animation": "fade-in | pop | typewriter | slide | none",
          "emphasis_type": "highlighted word | underline | color change | null",
          "purpose": "hook | benefit | stat | testimonial | CTA"
        }}
      ],
      "key_visual_elements": ["face", "product", "hands", "lifestyle", "graphic", "animation"],
      "attention_score": 8,
      "improvement_note": "Specific suggestion for improving this beat"
    }}
  ],

  "copy_analysis": {{
    "all_text_overlays": [],
    "headline_text": "Primary hook text if present",
    "body_copy": null,
    "cta_text": "CTA text verbatim",
    "copy_framework": "PAS | AIDA | BAB | FAB | 4Ps | QUEST | PASTOR | Custom | Unknown",
    "framework_execution": "How well the framework is executed",
    "reading_level": "elementary | middle school | high school | college",
    "word_count": 50,
    "power_words": ["free", "guaranteed", "instant", "secret", "proven"],
    "sensory_words": ["feel", "imagine", "discover", "transform", "experience"]
  }},

  "audio_analysis": {{
    "music": {{
      "has_music": true,
      "genre": "electronic | acoustic | hip-hop | cinematic | lo-fi | pop | orchestral",
      "tempo": "slow (<80 BPM) | medium (80-120) | fast (>120) | variable",
      "energy_level": "calm | building | high-energy | dramatic | uplifting",
      "mood": "inspiring | urgent | relaxed | edgy | nostalgic | playful",
      "music_sync_moments": ["00:05", "00:12"],
      "drop_timestamps": ["00:08"]
    }},
    "voice": {{
      "has_voiceover": true,
      "has_dialogue": false,
      "voice_gender": "male | female | mixed | ambiguous",
      "voice_age_range": "young adult (20s) | middle-aged (30s-40s) | mature (50+)",
      "voice_tone": "conversational | authoritative | excited | calm | ASMR | energetic",
      "estimated_wpm": 150,
      "accent": "American | British | Australian | neutral | regional"
    }},
    "sound_effects": [
      {{
        "timestamp": "00:02",
        "sfx_type": "whoosh | ding | pop | click | notification | impact",
        "purpose": "transition | emphasis | UI feedback | attention grab"
      }}
    ],
    "audio_visual_sync_score": 8,
    "silence_moments": [],
    "sound_off_compatible": true
  }},

  "brand_elements": {{
    "logo_appearances": [
      {{
        "timestamp": "00:28",
        "duration_seconds": 2.0,
        "position": "corner watermark | center | end card | integrated",
        "size": "small | medium | large | full-screen",
        "animation": "fade-in | scale-up | reveal | static"
      }}
    ],
    "logo_visible": true,
    "logo_position": "end card",
    "brand_colors_detected": ["#FF5733", "#1DA1F2"],
    "brand_color_consistency": 7,
    "product_appearances": [
      {{
        "timestamp": "00:10",
        "duration_seconds": 5.0,
        "shot_type": "hero shot | in-use | unboxing | comparison | detail | lifestyle",
        "prominence": "primary focus | background | integrated",
        "context": "hands-on demo | before/after | result showcase"
      }}
    ],
    "has_product_shot": true,
    "product_visibility_seconds": 15.0,
    "brand_mentions_audio": 2,
    "brand_mentions_text": 3
  }},

  "engagement_predictors": {{
    "thumb_stop": {{
      "thumb_stop_score": 8,
      "first_frame_hook": "What makes first frame attention-grabbing or why it fails",
      "pattern_interrupt_type": "unexpected visual | bold text | face | motion | color | null",
      "curiosity_gap": true,
      "curiosity_gap_description": "How the curiosity gap works",
      "first_second_elements": ["face", "text", "product", "motion", "contrast"],
      "visual_contrast_score": 7,
      "text_hook_present": true,
      "face_in_first_frame": true
    }},
    "scene_change_frequency": 2.5,
    "visual_variety_score": 7,
    "uses_fear_of_missing_out": false,
    "uses_social_proof_signals": true,
    "uses_controversy_or_hot_take": false,
    "uses_transformation_narrative": true,
    "predicted_watch_through_rate": "low (<25%) | medium (25-50%) | high (>50%)",
    "predicted_engagement_type": "saves | shares | comments | clicks"
  }},

  "platform_optimization": {{
    "aspect_ratio": "9:16 | 16:9 | 1:1 | 4:5 | 4:3",
    "optimal_platforms": ["instagram_reels", "tiktok", "facebook_feed", "youtube_shorts"],
    "sound_off_compatible": true,
    "caption_dependency": "none | low | medium | high",
    "native_feel_score": 7,
    "native_elements": ["handheld camera", "casual tone", "trending audio"],
    "duration_seconds": 30.0,
    "ideal_duration_assessment": "too short | optimal | too long",
    "safe_zone_compliance": true
  }},

  "emotional_arc": {{
    "emotional_beats": [
      {{
        "timestamp": "00:00",
        "primary_emotion": "curiosity",
        "intensity": 6,
        "trigger": "Bold opening question"
      }},
      {{
        "timestamp": "00:15",
        "primary_emotion": "aspiration",
        "intensity": 8,
        "trigger": "Transformation reveal"
      }}
    ],
    "emotional_climax_timestamp": "00:22",
    "tension_build_pattern": "gradual | sudden | oscillating | flat",
    "resolution_type": "product reveal | transformation | CTA urgency",
    "dominant_emotional_tone": "aspiration"
  }},

  "critique": {{
    "overall_grade": "B+",
    "overall_assessment": "2-3 sentence assessment of the ad's effectiveness",
    "strengths": [
      {{
        "strength": "What the ad does well",
        "evidence": "Specific example from the ad",
        "timestamp": "00:05",
        "impact": "Why this matters for performance"
      }}
    ],
    "weaknesses": [
      {{
        "weakness": "What could be improved",
        "evidence": "Specific example from the ad",
        "timestamp": "00:12",
        "impact": "How this affects performance",
        "suggested_fix": "Actionable improvement"
      }}
    ],
    "remake_suggestions": [
      {{
        "section_to_remake": "hook | middle | CTA | overall pacing | audio",
        "current_approach": "What the ad currently does",
        "suggested_approach": "Detailed alternative",
        "expected_improvement": "CTR | watch time | conversions",
        "effort_level": "minor tweak | moderate edit | full reshoot",
        "priority": "high | medium | low"
      }}
    ],
    "quick_wins": ["Add captions", "Extend hook by 1 second", "Add end card CTA"]
  }}
}}

IMPORTANT:
- Return ONLY valid JSON, no markdown formatting or extra text
- Be EXHAUSTIVE in visual_description - this is the most critical field
- Include ALL text overlays verbatim with precise timestamps
- Include ALL spoken words verbatim in audio_transcript
- Provide SPECIFIC, ACTIONABLE feedback in critique section
- Use "Unknown" for fields that cannot be determined
"""

IMAGE_ANALYSIS_PROMPT_V2 = """
You are an elite Creative Director and Ad Performance Analyst with expertise in direct response advertising.

YOUR MISSION: Create comprehensive "Creative DNA" analysis of this static image ad that enables:
1. Full understanding of the ad's strategy without seeing it
2. Actionable critique with specific improvement suggestions
3. Performance prediction based on visual elements
4. Detailed breakdown of all creative components

CONTEXT:
Company: {competitor_name}
Market Position: {market_position}
Follower Count: {follower_count}
Engagement: {likes} Likes, {comments} Comments, {shares} Shares
Brand Name (if provided): {brand_name}
Industry: {industry}
Target Audience Context: {target_audience}

ANALYSIS REQUIREMENTS:

1. VISUAL COMPOSITION:
   - Overall layout and visual hierarchy
   - Color palette and contrast
   - Typography choices
   - Focal points and eye flow
   - Negative space usage

2. TEXT/COPY ANALYSIS:
   - ALL text verbatim (headlines, body, CTA)
   - Typography style and positioning
   - Copywriting framework used (PAS, AIDA, BAB, etc.)
   - Power words and sensory language
   - Reading level

3. BRAND ELEMENTS:
   - Logo presence and positioning
   - Brand colors detected
   - Product visibility and presentation
   - Brand name mentions in text

4. ENGAGEMENT PREDICTION:
   - Thumb-stop score (1-10) with justification
   - Pattern interrupt analysis
   - Curiosity gap assessment
   - Visual contrast vs typical feed content

5. PLATFORM OPTIMIZATION:
   - Aspect ratio detection
   - Optimal platforms for this format
   - Text-to-image ratio
   - Safe zone compliance

6. ACTIONABLE CRITIQUE:
   - Overall letter grade (A+ to F)
   - 3-5 specific strengths with evidence
   - 3-5 specific weaknesses with fix suggestions
   - 2-4 remake suggestions
   - Quick wins list

Return analysis in this EXACT JSON structure:
{{
  "media_type": "image",
  "analysis_version": "2.0",
  "analysis_confidence": 0.85,
  "analysis_notes": [],

  "inferred_audience": "Detailed profile: age, gender, income, lifestyle, pain points, aspirations",
  "primary_messaging_pillar": "Core theme: Cost Savings, Premium Quality, Convenience, Health, Status, etc.",
  "overall_pacing_score": 5,
  "production_style": "High-production Studio | Authentic UGC | Hybrid | Animation | Stock Footage Mashup",
  "hook_score": 7,
  "overall_narrative_summary": "2-3 sentences describing the ad's message and visual story",

  "timeline": [],

  "copy_analysis": {{
    "all_text_overlays": [
      {{
        "text": "Exact text verbatim",
        "timestamp": "00:00",
        "duration_seconds": 0,
        "position": "top | center | bottom | lower-third | full-screen",
        "typography": "bold sans-serif | handwritten | serif | kinetic",
        "animation": "none",
        "emphasis_type": "highlighted word | underline | color change | null",
        "purpose": "hook | benefit | stat | testimonial | CTA"
      }}
    ],
    "headline_text": "Primary headline text",
    "body_copy": "Body text if present",
    "cta_text": "CTA text verbatim",
    "copy_framework": "PAS | AIDA | BAB | FAB | 4Ps | QUEST | PASTOR | Custom | Unknown",
    "framework_execution": "How well the framework is executed",
    "reading_level": "elementary | middle school | high school | college",
    "word_count": 25,
    "power_words": ["free", "guaranteed", "instant"],
    "sensory_words": ["feel", "imagine", "discover"]
  }},

  "audio_analysis": null,

  "brand_elements": {{
    "logo_appearances": [],
    "logo_visible": true,
    "logo_position": "corner | center | bottom | integrated",
    "brand_colors_detected": ["#FF5733", "#1DA1F2"],
    "brand_color_consistency": 8,
    "product_appearances": [],
    "has_product_shot": true,
    "product_visibility_seconds": null,
    "brand_mentions_audio": 0,
    "brand_mentions_text": 2
  }},

  "engagement_predictors": {{
    "thumb_stop": {{
      "thumb_stop_score": 7,
      "first_frame_hook": "What makes this image attention-grabbing or why it fails",
      "pattern_interrupt_type": "unexpected visual | bold text | face | color | null",
      "curiosity_gap": true,
      "curiosity_gap_description": "How the curiosity gap works",
      "first_second_elements": ["face", "text", "product", "contrast"],
      "visual_contrast_score": 6,
      "text_hook_present": true,
      "face_in_first_frame": false
    }},
    "scene_change_frequency": null,
    "visual_variety_score": 5,
    "uses_fear_of_missing_out": false,
    "uses_social_proof_signals": true,
    "uses_controversy_or_hot_take": false,
    "uses_transformation_narrative": false,
    "predicted_watch_through_rate": null,
    "predicted_engagement_type": "saves | shares | comments | clicks"
  }},

  "platform_optimization": {{
    "aspect_ratio": "1:1 | 4:5 | 9:16 | 16:9",
    "optimal_platforms": ["instagram_feed", "facebook_feed", "instagram_stories"],
    "sound_off_compatible": true,
    "caption_dependency": "none",
    "native_feel_score": 5,
    "native_elements": [],
    "duration_seconds": null,
    "ideal_duration_assessment": null,
    "safe_zone_compliance": true
  }},

  "emotional_arc": null,

  "critique": {{
    "overall_grade": "B",
    "overall_assessment": "2-3 sentence assessment of the ad's effectiveness",
    "strengths": [
      {{
        "strength": "What the ad does well",
        "evidence": "Specific example from the ad",
        "timestamp": null,
        "impact": "Why this matters for performance"
      }}
    ],
    "weaknesses": [
      {{
        "weakness": "What could be improved",
        "evidence": "Specific example from the ad",
        "timestamp": null,
        "impact": "How this affects performance",
        "suggested_fix": "Actionable improvement"
      }}
    ],
    "remake_suggestions": [
      {{
        "section_to_remake": "headline | visual | CTA | layout | color",
        "current_approach": "What the ad currently does",
        "suggested_approach": "Detailed alternative",
        "expected_improvement": "CTR | engagement | conversions",
        "effort_level": "minor tweak | moderate edit | full redesign",
        "priority": "high | medium | low"
      }}
    ],
    "quick_wins": ["Increase text contrast", "Add social proof", "Make CTA more prominent"]
  }}
}}

IMPORTANT:
- Return ONLY valid JSON, no markdown formatting or extra text
- For image ads: timeline=[], audio_analysis=null, emotional_arc=null
- Be detailed in visual descriptions
- Extract ALL text verbatim
- Provide SPECIFIC, ACTIONABLE feedback in critique
- Use "Unknown" for fields that cannot be determined
"""
