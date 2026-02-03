export interface ProjectStats {
  videos_uploaded: number;
  total_size_mb: number;
  segments_extracted: number;
}

export interface Project {
  id: string;
  name: string;
  brand_profile_id: string | null;
  status: 'draft' | 'processing' | 'ready' | 'rendered';
  inspiration_ads: string[] | null;
  user_prompt: string | null;
  max_videos: number;
  max_total_size_mb: number;
  created_at: string;
  updated_at: string;
  stats: ProjectStats | null;
}

export interface ProjectListResponse {
  items: Project[];
  total: number;
  page: number;
  page_size: number;
}

export interface ProjectCreate {
  name: string;
  brand_profile_id?: string;
  user_prompt?: string;
  inspiration_ads?: string[];
  max_videos?: number;
  max_total_size_mb?: number;
}

export interface ProjectUpdate {
  name?: string;
  brand_profile_id?: string;
  status?: 'draft' | 'processing' | 'ready' | 'rendered';
  inspiration_ads?: string[];
  user_prompt?: string;
  max_videos?: number;
  max_total_size_mb?: number;
}

export interface ProjectFilters {
  page?: number;
  page_size?: number;
  status?: 'draft' | 'processing' | 'ready' | 'rendered';
}

export interface ProjectFile {
  file_id: string;
  filename: string;
  original_filename: string;
  file_size_bytes: number;
  file_url: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
}

// File status types for polling during auto-analysis
export interface FileStatusResponse {
  file_id: string;
  project_id: string;
  filename: string;
  original_filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  segments_count: number;
}

export interface ProjectFilesStatusResponse {
  project_id: string;
  files: FileStatusResponse[];
  total_files: number;
  pending_count: number;
  processing_count: number;
  completed_count: number;
  failed_count: number;
  total_segments: number;
}

export interface ProjectUploadResponse {
  project_id: string;
  uploaded_files: ProjectFile[];
  total_files: number;
  total_size_bytes: number;
  total_size_mb: number;
  failed_files: Array<{ filename: string; error: string }>;
}

export interface ProjectFilesListResponse {
  project_id: string;
  files: ProjectFile[];
  total: number;
  total_size_bytes: number;
  total_size_mb: number;
}

// Video segment types
export interface UserVideoSegment {
  id: string;
  project_id: string;
  source_file_id: string;
  source_file_name: string | null;
  source_file_url: string | null;
  timestamp_start: number;
  timestamp_end: number;
  duration_seconds: number | null;
  visual_description: string | null;
  action_tags: string[] | null;
  thumbnail_url: string | null;
  created_at: string;
}

export interface ProjectSegmentsResponse {
  project_id: string;
  total_segments: number;
  segments: UserVideoSegment[];
}

export interface AnalysisProgress {
  project_id: string;
  total_files: number;
  completed_files: number;
  current_file: string | null;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message: string | null;
  segments_extracted: number;
}

// Upload progress tracking
export interface FileUploadProgress {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  error?: string;
}

// Segment search types
export interface UserVideoSegmentWithSimilarity extends UserVideoSegment {
  similarity_score: number;
}

export interface SegmentSearchRequest {
  query: string;
  limit?: number;
  min_similarity?: number;
}

export interface SegmentSearchResponse {
  project_id: string;
  query: string;
  total_results: number;
  results: UserVideoSegmentWithSimilarity[];
}

// Quick-create project types (for standalone editor)
export interface QuickCreateRequest {
  inspiration_ad_ids?: string[];
  source_project_ids?: string[];
  user_prompt?: string;
  brand_profile_id?: string;
}

// Direct generation types (clips-first Director - no recipe needed)
export interface DirectGenerateRequest {
  composition_type?: 'vertical_ad_v1' | 'horizontal_ad_v1' | 'square_ad_v1';
  user_prompt?: string;
  audio_url?: string;
}

export interface GenerationStats {
  total_slots: number;
  clips_selected: number;
  gaps_detected: number;
  coverage_percentage: number;
  average_similarity: number;
  total_duration_seconds: number;
}

export interface DirectGenerateResponse {
  project_id: string;
  payload: import('@/types/render').RemotionPayload;
  stats: GenerationStats;
  gaps: Array<Record<string, unknown>> | null;
  warnings: string[] | null;
  success: boolean;
}
