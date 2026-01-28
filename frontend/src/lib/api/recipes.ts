import { get, post, del, apiClient } from './client';
import type {
  Recipe,
  RecipeListResponse,
  RecipeFilters,
  RecipeExtractRequest,
  RecipeExtractResponse,
  ReferenceAdFetchRequest,
  ReferenceAdResponse,
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

  uploadReference: async (
    file: File,
    name?: string,
    onProgress?: (progress: number) => void
  ): Promise<ReferenceAdResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    if (name) {
      formData.append('name', name);
    }

    const response = await apiClient.post<ReferenceAdResponse>(
      '/api/recipes/upload-reference',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress(percent);
          }
        },
      }
    );
    return response.data;
  },

  fetchFromUrl: async (request: ReferenceAdFetchRequest): Promise<ReferenceAdResponse> => {
    return post<ReferenceAdResponse>('/api/recipes/fetch-url', request);
  },
};
