/**
 * Sample payload for testing Remotion compositions in the studio.
 * This demonstrates all segment types and features.
 */

import type { AdCompositionProps } from './types';

export const sampleVerticalPayload: AdCompositionProps = {
  composition_id: 'vertical_ad_v1',
  width: 1080,
  height: 1920,
  fps: 30,
  duration_in_frames: 450, // 15 seconds
  project_id: 'sample-project-123',
  visual_script_id: 'sample-script-456',
  brand_profile: {
    primary_color: '#FF5733',
    font_family: 'Inter',
    logo_url: null,
  },
  audio_track: undefined,
  timeline: [
    // Opening text slide (3 seconds)
    {
      id: 'segment-1',
      type: 'text_slide',
      start_frame: 0,
      duration_frames: 90,
      text_content: {
        headline: 'Transform Your Business',
        subheadline: 'With AI-Powered Marketing',
        background_color: '#FF5733',
        text_color: '#FFFFFF',
      },
      transition_out: {
        type: 'fade',
        duration_frames: 15,
      },
    },
    // Video clip (5 seconds)
    {
      id: 'segment-2',
      type: 'video_clip',
      start_frame: 90,
      duration_frames: 150,
      source: {
        url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
        start_time: 10,
        end_time: 15,
      },
      overlay: {
        text: 'See the difference',
        position: 'bottom',
        font_size: 36,
        animation: 'slide_up',
      },
      transition_in: {
        type: 'fade',
        duration_frames: 15,
      },
      transition_out: {
        type: 'dissolve',
        duration_frames: 15,
      },
      beat_type: 'hook',
      search_query: 'business growth visualization',
      similarity_score: 0.85,
    },
    // AI-generated B-Roll placeholder (3 seconds)
    {
      id: 'segment-3',
      type: 'generated_broll',
      start_frame: 240,
      duration_frames: 90,
      generated_source: {
        url: null, // Not yet generated
        generation_prompt: 'Modern office space with people collaborating, vibrant lighting, cinematic',
        regenerate_available: true,
      },
      overlay: {
        text: 'Collaborate Better',
        position: 'center',
        font_size: 48,
        animation: 'pop_in',
      },
      transition_in: {
        type: 'dissolve',
        duration_frames: 15,
      },
    },
    // Closing CTA text slide (4 seconds)
    {
      id: 'segment-4',
      type: 'text_slide',
      start_frame: 330,
      duration_frames: 120,
      text_content: {
        headline: 'Get Started Today',
        subheadline: 'Visit example.com',
        background_color: '#1a1a2e',
        text_color: '#FFFFFF',
      },
      transition_in: {
        type: 'slide_up',
        duration_frames: 20,
      },
    },
  ],
};

export const sampleHorizontalPayload: AdCompositionProps = {
  ...sampleVerticalPayload,
  composition_id: 'horizontal_ad_v1',
  width: 1920,
  height: 1080,
};

export const sampleSquarePayload: AdCompositionProps = {
  ...sampleVerticalPayload,
  composition_id: 'square_ad_v1',
  width: 1080,
  height: 1080,
};
