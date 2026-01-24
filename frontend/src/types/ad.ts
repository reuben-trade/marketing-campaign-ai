import { EnhancedAdAnalysisV2 } from './analysis';

export interface Ad {
  id: string;
  competitor_id: string;
  ad_library_id: string;
  ad_snapshot_url?: string;
  creative_type: 'image' | 'video' | 'carousel';
  creative_storage_path?: string;
  creative_url?: string;
  ad_copy?: string;
  ad_headline?: string;
  ad_description?: string;
  cta_text?: string;
  likes: number;
  comments: number;
  shares: number;
  impressions?: number;
  publication_date?: string;
  started_running_date?: string;
  total_active_time?: string;
  platforms?: string[];
  link_headline?: string;
  link_description?: string;
  additional_links?: string[];
  form_fields?: Record<string, unknown>;
  analysis?: Record<string, unknown>;
  video_intelligence?: EnhancedAdAnalysisV2;
  retrieved_date?: string;
  analyzed_date?: string;
  analyzed: boolean;
  download_status: 'pending' | 'completed' | 'failed';
  analysis_status: 'pending' | 'completed' | 'failed';
  total_engagement: number;
  overall_score?: number;

  // Composite scoring fields
  composite_score?: number; // 0-1 scale
  engagement_rate_percentile?: number; // 0-1 scale
  survivorship_score?: number; // 0.2/0.5/0.8/1.0
  ad_summary?: string;

  original_ad_id?: string;
  duplicate_count?: number;
  is_carousel?: boolean;
  carousel_item_count?: number;
  carousel_items?: Array<{
    url: string;
    type: string;
    storage_path?: string;
  }>;
}

export interface AdListResponse {
  items: Ad[];
  total: number;
  page: number;
  page_size: number;
}

export interface AdStats {
  total_ads: number;
  analyzed_ads: number;
  pending_analysis: number;
  failed_analysis: number;
  by_type: Record<string, number>;
  avg_engagement: number;
  avg_score?: number;
  top_performer_id?: string;
}

export interface AdRetrieveRequest {
  competitor_id?: string;
  competitor_ids?: string[];
  max_ads?: number;
  since_days?: number;
  scrape_details?: boolean;
}

export interface AdRetrieveResponse {
  retrieved: number;
  skipped: number;
  failed: number;
  competitor_id: string;
}

export interface AdAnalyzeResponse {
  processed: number;
  failed: number;
  duplicates_updated: number;
  total_attempted: number;
}

export interface AdFilters {
  page?: number;
  page_size?: number;
  competitor_id?: string;
  analyzed?: boolean;
  creative_type?: 'image' | 'video';
  min_engagement?: number;
  min_overall_score?: number; // 0-10 scale
  min_composite_score?: number; // 0-1 scale
}
