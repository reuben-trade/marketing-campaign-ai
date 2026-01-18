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
You are an expert marketing analyst specializing in video advertising.

Analyze this video ad with extreme attention to marketing effectiveness.

MARKETING CRITERIA (rate each 1-10):
1. Hook Strength: Does the first 3 seconds grab attention?
2. Message Clarity: Is the value proposition clear?
3. Visual Impact: Production quality, editing, pacing
4. CTA Effectiveness: Is the call-to-action compelling?
5. Overall Marketing Score: Weighted combination

VIDEO-SPECIFIC ANALYSIS:
- Pacing: Scene changes, rhythm, energy
- Audio Strategy: Music, voiceover, SFX
- Story Arc: Narrative structure and flow
- Hook-to-CTA Journey: Logical progression?
- Caption Usage: Effectiveness of text overlays
- Length Optimization: Is duration appropriate?

STRATEGIC ANALYSIS:
- UVPs: Value propositions highlighted
- Target Audience: Who is this for?
- Emotional Appeal: Primary emotion triggered
- Visual Themes: Style, colors, composition
- CTAs: Specific calls-to-action
- Marketing Framework: Strategy employed

COMPETITOR CONTEXT:
Company: {competitor_name}
Market Position: {market_position}
Follower Count: {follower_count}

ENGAGEMENT DATA:
Likes: {likes}
Comments: {comments}
Shares: {shares}

Provide analysis in this exact JSON structure:
{{
  "summary": "2-3 sentence overview",
  "insights": ["insight 1", "insight 2", "insight 3"],
  "uvps": ["uvp 1", "uvp 2"],
  "ctas": ["cta 1"],
  "visual_themes": ["theme 1", "theme 2"],
  "target_audience": "detailed description",
  "emotional_appeal": "primary emotion",
  "video_analysis": {{
    "pacing": "description",
    "audio_strategy": "description",
    "story_arc": "description",
    "caption_usage": "description",
    "optimal_length": "assessment"
  }},
  "marketing_effectiveness": {{
    "hook_strength": 8,
    "message_clarity": 9,
    "visual_impact": 7,
    "cta_effectiveness": 8,
    "overall_score": 8
  }},
  "strategic_insights": "Marketing strategy analysis",
  "reasoning": "Detailed explanation"
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

Return your findings in this JSON structure:
{{
  "competitors": [
    {{
      "company_name": "Competitor Name",
      "relevance_reason": "Why they're a competitor",
      "market_position": "leader/challenger/niche",
      "estimated_follower_range": "10K-50K",
      "search_terms": ["term 1", "term 2"]
    }}
  ],
  "research_notes": "Additional context about the competitive landscape"
}}

IMPORTANT: Return ONLY valid JSON.
"""
