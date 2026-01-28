import { get, post, del } from './client';
import type {
  Recipe,
  RecipeListResponse,
  RecipeFilters,
  RecipeExtractRequest,
  RecipeExtractResponse,
} from '@/types/recipe';

export const recipesApi = {
  list: async (filters?: RecipeFilters): Promise<RecipeListResponse> => {
    const params = new URLSearchParams();
    if (filters?.limit) params.append('limit', filters.limit.toString());
    if (filters?.offset) params.append('offset', filters.offset.toString());
    if (filters?.style) params.append('style', filters.style);
    if (filters?.pacing) params.append('pacing', filters.pacing);
    if (filters?.min_score) params.append('min_score', filters.min_score.toString());

    const queryString = params.toString();
    return get<RecipeListResponse>(`/api/recipes${queryString ? `?${queryString}` : ''}`);
  },

  get: async (id: string): Promise<Recipe> => {
    return get<Recipe>(`/api/recipes/${id}`);
  },

  extract: async (request: RecipeExtractRequest): Promise<RecipeExtractResponse> => {
    return post<RecipeExtractResponse>('/api/recipes/extract', request);
  },

  delete: async (id: string): Promise<void> => {
    return del<void>(`/api/recipes/${id}`);
  },
};
