import { EnhancedAdAnalysisV2 } from './analysis';

export interface CritiqueRequest {
  file: File;
  brand_name?: string;
  industry?: string;
  target_audience?: string;
}

export interface CritiqueResponse {
  analysis: EnhancedAdAnalysisV2;
  processing_time_seconds: number;
  model_used: string;
  media_type: 'image' | 'video';
  file_size_bytes: number;
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
