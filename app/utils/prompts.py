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

VIDEO_ANALYSIS_PROMPT = """
You are a Professional Creative Director analyzing video advertisements.

YOUR MISSION: Create a detailed "Creative DNA" analysis that allows another analyst to fully understand, visualize, and feel this ad WITHOUT watching it. Your narrative descriptions must be vivid enough to reconstruct the ad experience.

CRITICAL INSTRUCTION - NATURAL BEAT SEGMENTATION:
Do NOT use fixed 3-5 second intervals. Instead, identify "Natural Beats" where the creative shifts occur:
- Camera angle changes
- Speaker or subject changes
- Messaging intent shifts (problem → solution, feature → benefit)
- Emotional tone transitions
- Scene or location changes

Each beat should represent a cohesive narrative moment, regardless of duration.

COMPETITOR CONTEXT:
Company: {competitor_name}
Market Position: {market_position}
Follower Count: {follower_count}

ENGAGEMENT DATA:
Likes: {likes}
Comments: {comments}
Shares: {shares}

ANALYSIS REQUIREMENTS:

1. RHETORICAL ANALYSIS - For each beat, identify the persuasion mode:
   - Logos: Facts, statistics, features, logical arguments
   - Pathos: Emotional appeals, pain points, aspirations, fear, joy
   - Ethos: Credibility signals, testimonials, authority, trust markers
   - Kairos: Urgency, timing, limited offers, seasonal relevance

2. CINEMATIC ANALYSIS - For each beat, document:
   - Camera angle (Low-angle, POV, Close-up, Wide-shot, Dolly-in, Over-the-shoulder, etc.)
   - Lighting style (High-contrast, Natural/UGC, Studio-soft, Golden-hour, Ring-light)
   - Cinematic features (Slow-mo, Rapid-cuts, Text-overlay, Split-screen, B-roll, Jump-cuts)

3. PRODUCTION STYLE CLASSIFICATION:
   - "High-production Studio": Professional lighting, scripted, polished editing
   - "Authentic UGC": Raw footage, handheld, natural lighting, unscripted feel
   - "Hybrid": Mix of professional and authentic elements
   - "Animation": Motion graphics, animated characters, kinetic typography

4. VIVID NARRATION - Your visual_description and audio_transcript must be detailed enough that someone could:
   - Sketch storyboards from your descriptions
   - Understand the emotional journey
   - Identify the target demographic from context clues
   - Recreate the ad's structure

Provide analysis in this exact JSON structure:
{{
  "inferred_audience": "Detailed target audience profile based on visual/audio cues (age range, lifestyle, income level, pain points, aspirations)",
  "primary_messaging_pillar": "Core message theme (e.g., 'Cost Savings', 'Premium Quality', 'Convenience', 'Health Benefits', 'Social Status')",
  "overall_pacing_score": 8,
  "production_style": "High-production Studio | Authentic UGC | Hybrid | Animation",
  "hook_score": 9,
  "overall_narrative_summary": "2-3 sentences capturing the ad's complete story arc and emotional journey - written so vividly that the reader can feel the ad's impact",
  "timeline": [
    {{
      "start_time": "00:00",
      "end_time": "00:03",
      "beat_type": "Hook | Problem | Solution | Social Proof | CTA | Transition | Feature Demo",
      "cinematics": {{
        "camera_angle": "Close-up on product",
        "lighting_style": "High-contrast with dramatic shadows",
        "cinematic_features": ["Slow-mo", "Text-overlay"]
      }},
      "tone_of_voice": "Urgent | Empathetic | ASMR | High-energy | Conversational | Authoritative",
      "rhetorical_appeal": {{
        "mode": "Pathos | Logos | Ethos | Kairos",
        "description": "Detailed explanation of how this persuasion technique is executed - what specific words, visuals, or audio create this effect"
      }},
      "target_audience_cues": "Visual/audio signals identifying the demographic (e.g., 'Young professional shown in modern apartment, wearing athleisure, checking phone - targets 25-35 urban millennials')",
      "visual_description": "DETAILED scene description: Who appears? What are they doing? What's the setting? What colors dominate? What text appears on screen? What products are shown and how? Be specific enough to sketch a storyboard.",
      "audio_transcript": "Exact spoken words in quotes, plus [music: upbeat electronic], [SFX: whoosh], [silence], etc. Include tone and delivery notes."
    }}
  ]
}}

BEAT TYPE DEFINITIONS:
- Hook: Opening attention-grabber (first 1-5 seconds typically)
- Problem: Pain point agitation, showing the struggle
- Solution: Product/service introduction as the answer
- Social Proof: Testimonials, reviews, authority signals
- CTA: Call-to-action, what viewer should do next
- Transition: Bridge between major narrative moments
- Feature Demo: Product features or benefits showcase

IMPORTANT:
- Return ONLY valid JSON, no additional text or markdown formatting.
- The hook_score should be derived from the effectiveness of the first beat.
- Be EXHAUSTIVE in your visual_description - this is the most critical field.
- Include ALL text overlays verbatim in visual_description.
- Include ALL spoken words verbatim in audio_transcript.
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
