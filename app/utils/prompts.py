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
      }},

      "content_breakdown": {{
        "left_side_problem": {{
          "visual": "visual description of problem side",
          "text": "text content",
          "style": "bold/regular/italic"
        }},
        "right_side_solution": {{
          "visual": "visual description of solution side",
          "text": "text content",
          "style": "bold/regular/italic"
        }},
        "center_divider": "divider description or null"
      }},

      "copywriting": {{
        "headline": {{
          "text": "headline text",
          "placement": "top/center/bottom",
          "font": "font name",
          "color": "#hex",
          "size": "large/medium/small",
          "style": "bold/regular"
        }},
        "subheadline": {{
          "text": "subheadline text",
          "placement": "below headline",
          "font": "font name",
          "color": "#hex",
          "size": "medium/small",
          "style": "regular"
        }},
        "body_copy": {{
          "text": "body text content",
          "placement": "center/bottom",
          "font": "font name",
          "color": "#hex",
          "size": "small",
          "style": "regular"
        }},
        "cta_button": {{
          "text": "CTA text",
          "placement": "bottom/center",
          "font": "font name",
          "color": "#hex",
          "size": "medium",
          "style": "bold"
        }}
      }},

      "design_specifications": {{
        "dimensions": "1080x1080 or 1080x1920",
        "file_format": "PNG/JPG",
        "file_size": "max size",
        "safe_zones": "margin requirements",
        "text_coverage": "percentage of image with text",
        "contrast_ratio": "minimum contrast",
        "mobile_optimization": "mobile-specific notes",
        "font": "primary font",
        "colors": {{
          "primary": "#hex",
          "secondary": "#hex",
          "accent": "#hex"
        }}
      }},

      "production_notes": {{
        "tools": "recommended design tools",
        "assets_needed": ["asset 1", "asset 2"],
        "time_estimate": "production time",
        "talent": "if models/actors needed",
        "notes": "additional production notes"
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

Generate recommendations based on the content requirements specified below.

FOR VIDEO ADS use: script_breakdown, caption_strategy, filming_requirements, audio_design
FOR IMAGE ADS use: content_breakdown, copywriting, design_specifications, production_notes

CRITICAL SCHEMA NOTES:
- For copywriting fields (headline, subheadline, body_copy, cta_button), ALWAYS use the object format with "text" and "placement" fields, NOT plain strings
- For content_breakdown fields (left_side_problem, right_side_solution), ALWAYS use the object format with "visual", "text", and "style" fields

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
You are an elite Ad Performance Analyst. Deconstruct this video into its core structural components with precise timestamps.

CONTEXT:
Company: {competitor_name} | Position: {market_position} | Followers: {follower_count}
Engagement: {likes} Likes, {comments} Comments, {shares} Shares
Brand: {brand_name} | Industry: {industry} | Audience: {target_audience}
Platform CTA Button: {platform_cta} (this button is OUTSIDE the creative — do NOT flag the ad as "missing a CTA" if no on-screen CTA exists, evaluate CTA strategy holistically)

BEAT TYPES (use exactly these labels for beat_type):
- Hook: First 1-5s scroll-stopper (describe the exact attention mechanism)
- Problem: Pain point identification/agitation
- Solution: Product/service revealed as the answer
- Product Showcase: Features/demos/before-after (describe EXACTLY which features are shown)
- Social Proof: Testimonials, reviews, ratings, UGC
- Benefit Stack: Multiple value propositions in sequence
- Objection Handling: Addressing doubts (price, trust, guarantee)
- CTA: Call to Action with urgency elements (include exact CTA text)
- Transition: Visual bridges between sections

CRITICAL INSTRUCTIONS:
- Segment by structural components, NOT arbitrary time intervals
- Timestamps must be precise MM:SS format (e.g., Hook: 00:00-00:03)
- visual_description must be EXHAUSTIVE — detailed enough to sketch a storyboard
- Include ALL on-screen text verbatim with precise timestamps in text_overlays_in_beat
- Include ALL spoken words verbatim in audio_transcript with [music: genre/mood] and [SFX: type] annotations
- Provide SPECIFIC, ACTIONABLE feedback in critique strengths/weaknesses/remake_suggestions
- Use null for fields that cannot be determined

RESPONSE STRUCTURE (return valid JSON with these exact top-level keys):
{{
  "media_type": "video",
  "analysis_version": "2.0",
  "analysis_confidence": float,
  "analysis_notes": [],
  "inferred_audience": "str",
  "primary_messaging_pillar": "str",
  "overall_pacing_score": int 1-10,
  "production_style": "str",
  "hook_score": int 1-10,
  "overall_narrative_summary": "str",
  "timeline": [{{
    "start_time": "MM:SS", "end_time": "MM:SS", "beat_type": "str",
    "cinematics": {{"camera_angle": "str", "lighting_style": "str", "cinematic_features": [], "color_grading": "str|null", "motion_type": "str|null", "transition_in": "str|null", "transition_out": "str|null"}},
    "tone_of_voice": "str",
    "rhetorical_appeal": {{"mode": "Logos|Pathos|Ethos|Kairos", "description": "str", "secondary_mode": "str|null", "persuasion_techniques": [], "objection_addressed": "str|null"}},
    "target_audience_cues": "str", "visual_description": "str", "audio_transcript": "str",
    "emotion": "str|null", "emotion_intensity": int|null,
    "text_overlays_in_beat": [{{"text": "str", "timestamp": "MM:SS", "duration_seconds": float, "position": "str", "typography": "str|null", "animation": "str|null", "emphasis_type": "str|null", "purpose": "str|null"}}],
    "key_visual_elements": [], "attention_score": int|null, "improvement_note": "str|null"
  }}],
  "copy_analysis": {{"all_text_overlays": [], "headline_text": "str|null", "body_copy": "str|null", "cta_text": "str|null", "copy_framework": "str|null", "framework_execution": "str|null", "reading_level": "str|null", "word_count": int|null, "power_words": [], "sensory_words": []}},
  "audio_analysis": {{"music": {{"has_music": bool, "genre": "str|null", "tempo": "str|null", "energy_level": "str|null", "mood": "str|null", "music_sync_moments": [], "drop_timestamps": []}}, "voice": {{"has_voiceover": bool, "has_dialogue": bool, "voice_gender": "str|null", "voice_age_range": "str|null", "voice_tone": "str|null", "estimated_wpm": int|null, "accent": "str|null"}}, "sound_effects": [{{"timestamp": "MM:SS", "sfx_type": "str", "purpose": "str|null"}}], "audio_visual_sync_score": int|null, "silence_moments": [], "sound_off_compatible": bool}},
  "brand_elements": {{"logo_appearances": [{{"timestamp": "MM:SS", "duration_seconds": float, "position": "str", "size": "str", "animation": "str|null"}}], "logo_visible": bool, "logo_position": "str|null", "brand_colors_detected": [], "brand_color_consistency": int|null, "product_appearances": [{{"timestamp": "MM:SS", "duration_seconds": float, "shot_type": "str", "prominence": "str", "context": "str|null"}}], "has_product_shot": bool, "product_visibility_seconds": float|null, "brand_mentions_audio": int, "brand_mentions_text": int}},
  "engagement_predictors": {{"thumb_stop": {{"thumb_stop_score": int, "first_frame_hook": "str", "pattern_interrupt_type": "str|null", "curiosity_gap": bool, "curiosity_gap_description": "str|null", "first_second_elements": [], "visual_contrast_score": int|null, "text_hook_present": bool, "face_in_first_frame": bool}}, "scene_change_frequency": float|null, "visual_variety_score": int, "uses_fear_of_missing_out": bool, "uses_social_proof_signals": bool, "uses_controversy_or_hot_take": bool, "uses_transformation_narrative": bool, "predicted_watch_through_rate": "str|null", "predicted_engagement_type": "str|null"}},
  "platform_optimization": {{"aspect_ratio": "str", "optimal_platforms": [], "sound_off_compatible": bool, "caption_dependency": "str", "native_feel_score": int, "native_elements": [], "duration_seconds": float|null, "ideal_duration_assessment": "str|null", "safe_zone_compliance": bool}},
  "emotional_arc": {{"emotional_beats": [{{"timestamp": "MM:SS", "primary_emotion": "str", "intensity": int, "trigger": "str"}}], "emotional_climax_timestamp": "str|null", "tension_build_pattern": "str|null", "resolution_type": "str|null", "dominant_emotional_tone": "str"}},
  "critique": {{"overall_grade": "A+ to F", "overall_assessment": "str", "strengths": [{{"strength": "str", "evidence": "str", "timestamp": "str|null", "impact": "str"}}], "weaknesses": [{{"weakness": "str", "evidence": "str", "timestamp": "str|null", "impact": "str", "suggested_fix": "str"}}], "remake_suggestions": [{{"section_to_remake": "str", "current_approach": "str", "suggested_approach": "str", "expected_improvement": "str", "effort_level": "str", "priority": "str"}}], "quick_wins": []}}
}}
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

PLATFORM CTA BUTTON: {platform_cta}
NOTE: The platform CTA button appears as a clickable button on the ad platform interface, OUTSIDE of the creative itself. 

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
