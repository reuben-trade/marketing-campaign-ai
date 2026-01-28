import { get, post, del } from './client';
import type {
  Recommendation,
  RecommendationListResponse,
  RecommendationGenerateRequest,
} from '@/types/recommendation';

export const recommendationsApi = {
  list: async (params?: {
    page?: number;
    page_size?: number;
  }): Promise<RecommendationListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString());

    const queryString = searchParams.toString();
    return get<RecommendationListResponse>(
      `/api/recommendations${queryString ? `?${queryString}` : ''}`
    );
  },

  get: async (id: string): Promise<Recommendation> => {
    return get<Recommendation>(`/api/recommendations/${id}`);
  },

  getLatest: async (): Promise<Recommendation | null> => {
    return get<Recommendation | null>('/api/recommendations/latest');
  },

  generate: async (
    request?: RecommendationGenerateRequest,
    model?: 'claude' | 'openai'
  ): Promise<Recommendation> => {
    const params = model ? `?model=${model}` : '';
    return post<Recommendation>(`/api/recommendations/generate${params}`, request || {});
  },

  delete: async (id: string): Promise<void> => {
    return del<void>(`/api/recommendations/${id}`);
  },
};
