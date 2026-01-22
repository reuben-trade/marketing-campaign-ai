'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { recommendationsApi } from '@/lib/api/recommendations';
import type { RecommendationGenerateRequest } from '@/types/recommendation';

export function useRecommendations(params?: { page?: number; page_size?: number }) {
  return useQuery({
    queryKey: ['recommendations', params],
    queryFn: () => recommendationsApi.list(params),
  });
}

export function useRecommendation(id: string) {
  return useQuery({
    queryKey: ['recommendation', id],
    queryFn: () => recommendationsApi.get(id),
    enabled: !!id,
  });
}

export function useLatestRecommendation() {
  return useQuery({
    queryKey: ['recommendation', 'latest'],
    queryFn: recommendationsApi.getLatest,
  });
}

export function useGenerateRecommendation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      request,
      model,
    }: {
      request?: RecommendationGenerateRequest;
      model?: 'claude' | 'openai';
    }) => recommendationsApi.generate(request, model),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      queryClient.invalidateQueries({ queryKey: ['recommendation', 'latest'] });
    },
  });
}

export function useDeleteRecommendation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => recommendationsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
    },
  });
}
