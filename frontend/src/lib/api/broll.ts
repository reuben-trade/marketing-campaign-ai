import { get, post, del } from './client';
import type {
  VeoGenerateRequest,
  VeoGenerationResponse,
  VeoGenerationStatusResponse,
  VeoGenerationListResponse,
  VeoRegenerateRequest,
  VeoSelectClipRequest,
  VeoSelectClipResponse,
  PromptEnhancementRequest,
  PromptEnhancementResponse,
  VeoGenerationStatus,
} from '@/types/broll';

export const brollApi = {
  /**
   * Generate B-Roll clip(s) using Veo 2
   */
  generate: async (request: VeoGenerateRequest): Promise<VeoGenerationResponse> => {
    return post<VeoGenerationResponse>('/api/broll/generate', request);
  },

  /**
   * Regenerate B-Roll based on a previous generation
   */
  regenerate: async (request: VeoRegenerateRequest): Promise<VeoGenerationResponse> => {
    return post<VeoGenerationResponse>('/api/broll/regenerate', request);
  },

  /**
   * Get the status of a generation job
   */
  getStatus: async (generationId: string): Promise<VeoGenerationStatusResponse> => {
    return get<VeoGenerationStatusResponse>(`/api/broll/${generationId}`);
  },

  /**
   * List generation jobs with optional filtering
   */
  list: async (options?: {
    projectId?: string;
    status?: VeoGenerationStatus;
    page?: number;
    pageSize?: number;
  }): Promise<VeoGenerationListResponse> => {
    const params = new URLSearchParams();
    if (options?.projectId) params.append('project_id', options.projectId);
    if (options?.status) params.append('status', options.status);
    if (options?.page) params.append('page', options.page.toString());
    if (options?.pageSize) params.append('page_size', options.pageSize.toString());

    const queryString = params.toString();
    return get<VeoGenerationListResponse>(`/api/broll${queryString ? `?${queryString}` : ''}`);
  },

  /**
   * Delete a generation job and its clips
   */
  delete: async (generationId: string): Promise<void> => {
    return del<void>(`/api/broll/${generationId}`);
  },

  /**
   * Enhance a B-Roll prompt using AI
   */
  enhancePrompt: async (request: PromptEnhancementRequest): Promise<PromptEnhancementResponse> => {
    return post<PromptEnhancementResponse>('/api/broll/enhance-prompt', request);
  },

  /**
   * Select a generated clip for use in the timeline
   */
  selectClip: async (
    generationId: string,
    request: VeoSelectClipRequest
  ): Promise<VeoSelectClipResponse> => {
    return post<VeoSelectClipResponse>(`/api/broll/${generationId}/select`, request);
  },
};
