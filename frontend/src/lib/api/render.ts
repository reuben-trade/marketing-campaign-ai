import { get, post, put, del } from './client';
import type {
  RenderRequest,
  RenderResponse,
  RenderStatusResponse,
  RenderListResponse,
  RenderQueueStats,
  RemotionPayload,
} from '@/types/render';

export const renderApi = {
  /**
   * Create a new render job
   */
  create: async (request: RenderRequest): Promise<RenderResponse> => {
    return post<RenderResponse>('/api/render', request);
  },

  /**
   * Get the status of a render job
   */
  getStatus: async (renderId: string): Promise<RenderStatusResponse> => {
    return get<RenderStatusResponse>(`/api/render/${renderId}`);
  },

  /**
   * Update the payload for a pending render job
   */
  updatePayload: async (renderId: string, payload: RemotionPayload): Promise<RenderResponse> => {
    return put<RenderResponse>(`/api/render/${renderId}/payload`, { payload });
  },

  /**
   * List all renders for a project
   */
  listByProject: async (
    projectId: string,
    page: number = 1,
    pageSize: number = 20
  ): Promise<RenderListResponse> => {
    const params = new URLSearchParams();
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());
    return get<RenderListResponse>(`/api/render/project/${projectId}?${params.toString()}`);
  },

  /**
   * Cancel a pending or rendering job
   */
  cancel: async (renderId: string): Promise<RenderResponse> => {
    return post<RenderResponse>(`/api/render/${renderId}/cancel`);
  },

  /**
   * Delete a render job and its output files
   */
  delete: async (renderId: string): Promise<void> => {
    return del<void>(`/api/render/${renderId}`);
  },

  /**
   * Get render queue statistics
   */
  getQueueStats: async (): Promise<RenderQueueStats> => {
    return get<RenderQueueStats>('/api/render/stats/queue');
  },
};
