import { get, post, put, del } from './client';
import type {
  Competitor,
  CompetitorCreate,
  CompetitorUpdate,
  CompetitorListResponse,
  CompetitorDiscoverRequest,
  CompetitorDiscoverResponse,
} from '@/types/competitor';

export const competitorsApi = {
  list: async (params?: {
    page?: number;
    page_size?: number;
    active_only?: boolean;
  }): Promise<CompetitorListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString());
    if (params?.active_only) searchParams.append('active_only', 'true');

    const queryString = searchParams.toString();
    return get<CompetitorListResponse>(`/api/competitors${queryString ? `?${queryString}` : ''}`);
  },

  get: async (id: string): Promise<Competitor> => {
    return get<Competitor>(`/api/competitors/${id}`);
  },

  add: async (competitor: CompetitorCreate): Promise<Competitor> => {
    return post<Competitor>('/api/competitors', competitor);
  },

  update: async (id: string, competitor: CompetitorUpdate): Promise<Competitor> => {
    return put<Competitor>(`/api/competitors/${id}`, competitor);
  },

  delete: async (id: string): Promise<void> => {
    return del<void>(`/api/competitors/${id}`);
  },

  discover: async (request: CompetitorDiscoverRequest): Promise<CompetitorDiscoverResponse> => {
    return post<CompetitorDiscoverResponse>('/api/competitors/discover', request);
  },
};
