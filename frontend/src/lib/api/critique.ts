import { get, del, apiClient } from './client';
import type {
  CritiqueResponse,
  CritiqueListResponse,
  SupportedFormats,
} from '@/types/critique';

export interface UploadOptions {
  onUploadProgress?: (progress: { loaded: number; total?: number }) => void;
}

export const critiqueApi = {
  getSupportedFormats: async (): Promise<SupportedFormats> => {
    return get<SupportedFormats>('/api/critique/supported-formats');
  },

  list: async (params?: {
    page?: number;
    page_size?: number;
    media_type?: string;
  }): Promise<CritiqueListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString());
    if (params?.media_type) searchParams.append('media_type', params.media_type);

    const queryString = searchParams.toString();
    return get<CritiqueListResponse>(`/api/critique${queryString ? `?${queryString}` : ''}`);
  },

  get: async (id: string): Promise<CritiqueResponse> => {
    return get<CritiqueResponse>(`/api/critique/${id}`);
  },

  upload: async (formData: FormData, options?: UploadOptions): Promise<CritiqueResponse> => {
    const response = await apiClient.post<CritiqueResponse>('/api/critique/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: options?.onUploadProgress
        ? (progressEvent) => {
            options.onUploadProgress!({
              loaded: progressEvent.loaded,
              total: progressEvent.total,
            });
          }
        : undefined,
    });
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    return del<void>(`/api/critique/${id}`);
  },
};
