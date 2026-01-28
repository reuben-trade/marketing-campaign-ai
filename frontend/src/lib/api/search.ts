import { post } from './client';
import type { Ad, AdFilters } from '@/types/ad';

export interface SearchResults {
  items: Ad[];
  total: number;
  query: string;
}

export interface SemanticSearchRequest {
  query: string;
  limit?: number;
  filters?: Partial<AdFilters>;
}

export const searchApi = {
  semanticSearch: async (request: SemanticSearchRequest): Promise<SearchResults> => {
    return post<SearchResults>('/api/search/semantic', request);
  },
};
