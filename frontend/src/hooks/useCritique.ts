'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { critiqueApi } from '@/lib/api/critique';
import type { UploadProgressCallback } from '@/lib/api/client';

export function useSupportedFormats() {
  return useQuery({
    queryKey: ['critique', 'supported-formats'],
    queryFn: critiqueApi.getSupportedFormats,
    staleTime: Infinity, // This data doesn't change
  });
}

export function useCritiques(params?: {
  page?: number;
  page_size?: number;
  media_type?: string;
}) {
  return useQuery({
    queryKey: ['critiques', params],
    queryFn: () => critiqueApi.list(params),
    staleTime: 30000,
  });
}

export function useCritique(id: string | null) {
  return useQuery({
    queryKey: ['critique', id],
    queryFn: () => critiqueApi.get(id!),
    enabled: !!id,
  });
}

export function useUploadCritique() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      formData,
      onUploadProgress,
    }: {
      formData: FormData;
      onUploadProgress?: UploadProgressCallback;
    }) => critiqueApi.upload(formData, { onUploadProgress }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['critiques'] });
    },
  });
}

export function useDeleteCritique() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => critiqueApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['critiques'] });
    },
  });
}
