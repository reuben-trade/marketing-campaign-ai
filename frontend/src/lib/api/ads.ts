import { get, post } from './client';
import type {
  Ad,
  AdListResponse,
  AdStats,
  AdFilters,
  AdRetrieveRequest,
  AdRetrieveResponse,
  AdAnalyzeResponse,
} from '@/types/ad';

export const adsApi = {
  list: async (filters?: AdFilters): Promise<AdListResponse> => {
    const params = new URLSearchParams();
    if (filters?.page) params.append('page', filters.page.toString());
    if (filters?.page_size) params.append('page_size', filters.page_size.toString());
    if (filters?.competitor_id) params.append('competitor_id', filters.competitor_id);
    if (filters?.analyzed !== undefined) params.append('analyzed', filters.analyzed.toString());
    if (filters?.creative_type) params.append('creative_type', filters.creative_type);
    if (filters?.min_engagement) params.append('min_engagement', filters.min_engagement.toString());
    if (filters?.min_overall_score)
      params.append('min_overall_score', filters.min_overall_score.toString());
    if (filters?.min_composite_score)
      params.append('min_composite_score', filters.min_composite_score.toString());

    const queryString = params.toString();
    return get<AdListResponse>(`/api/ads${queryString ? `?${queryString}` : ''}`);
  },

  get: async (id: string): Promise<Ad> => {
    return get<Ad>(`/api/ads/${id}`);
  },

  getStats: async (competitorId?: string): Promise<AdStats> => {
    const params = competitorId ? `?competitor_id=${competitorId}` : '';
    return get<AdStats>(`/api/ads/stats${params}`);
  },

  retrieve: async (request: AdRetrieveRequest): Promise<AdRetrieveResponse> => {
    return post<AdRetrieveResponse>('/api/ads/retrieve', request);
  },

  analyzeRun: async (limit: number): Promise<AdAnalyzeResponse> => {
    return post<AdAnalyzeResponse>('/api/ads/analyze/run', { limit });
  },

  analyze: async (adId: string): Promise<Ad> => {
    return post<Ad>(`/api/ads/${adId}/analyze`);
  },
};
