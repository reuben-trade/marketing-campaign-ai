import { get, post, put, apiClient } from './client';
import type {
  BusinessStrategy,
  BusinessStrategyCreate,
  BusinessStrategyExtractResponse,
} from '@/types/strategy';

export const strategyApi = {
  list: async (): Promise<BusinessStrategy[]> => {
    return get<BusinessStrategy[]>('/api/strategy');
  },

  get: async (id: string): Promise<BusinessStrategy> => {
    return get<BusinessStrategy>(`/api/strategy/${id}`);
  },

  create: async (strategy: BusinessStrategyCreate): Promise<BusinessStrategy> => {
    return post<BusinessStrategy>('/api/strategy', strategy);
  },

  update: async (
    id: string,
    strategy: Partial<BusinessStrategyCreate>
  ): Promise<BusinessStrategy> => {
    return put<BusinessStrategy>(`/api/strategy/${id}`, strategy);
  },

  uploadPDF: async (formData: FormData): Promise<BusinessStrategyExtractResponse> => {
    const response = await apiClient.post<BusinessStrategyExtractResponse>(
      '/api/strategy/upload-pdf',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },
};
