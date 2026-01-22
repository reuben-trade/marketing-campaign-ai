'use client';

import { useQuery, useMutation } from '@tanstack/react-query';
import { critiqueApi } from '@/lib/api/critique';
import type { UploadProgressCallback } from '@/lib/api/client';

export function useSupportedFormats() {
  return useQuery({
    queryKey: ['critique', 'supported-formats'],
    queryFn: critiqueApi.getSupportedFormats,
    staleTime: Infinity, // This data doesn't change
  });
}

export function useUploadCritique() {
  return useMutation({
    mutationFn: ({
      formData,
      onUploadProgress,
    }: {
      formData: FormData;
      onUploadProgress?: UploadProgressCallback;
    }) => critiqueApi.upload(formData, { onUploadProgress }),
  });
}
