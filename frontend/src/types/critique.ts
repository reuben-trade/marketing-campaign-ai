import { EnhancedAdAnalysisV2 } from './analysis';

export interface CritiqueRequest {
  file: File;
  brand_name?: string;
  industry?: string;
  target_audience?: string;
  platform_cta?: string;
}

export interface CritiqueResponse {
  id?: string;
  analysis: EnhancedAdAnalysisV2;
  processing_time_seconds: number;
  model_used: string;
  media_type: 'image' | 'video';
  file_size_bytes: number;
  file_name?: string;
  file_url?: string;
  created_at?: string;
}

export interface CritiqueListItem {
  id: string;
  file_name: string;
  file_size_bytes: number;
  media_type: 'image' | 'video';
  file_url?: string;
  brand_name?: string;
  industry?: string;
  overall_grade?: string;
  hook_score?: number;
  pacing_score?: number;
  thumb_stop_score?: number;
  model_used?: string;
  processing_time_seconds?: number;
  created_at: string;
}

export interface CritiqueListResponse {
  critiques: CritiqueListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface SupportedFormats {
  images: {
    extensions: string[];
    max_size_mb: number;
  };
  videos: {
    extensions: string[];
    max_size_mb: number;
  };
}
