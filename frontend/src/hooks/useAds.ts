'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adsApi } from '@/lib/api/ads';
import type { AdFilters, AdRetrieveRequest } from '@/types/ad';

export function useAds(filters?: AdFilters) {
  return useQuery({
    queryKey: ['ads', filters],
    queryFn: () => adsApi.list(filters),
    staleTime: 30000, // 30 seconds
  });
}

export function useAd(id: string) {
  return useQuery({
    queryKey: ['ad', id],
    queryFn: () => adsApi.get(id),
    enabled: !!id,
  });
}

export function useAdStats(competitorId?: string) {
  return useQuery({
    queryKey: ['adStats', competitorId],
    queryFn: () => adsApi.getStats(competitorId),
  });
}

export function useRetrieveAds() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: AdRetrieveRequest) => adsApi.retrieve(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ads'] });
      queryClient.invalidateQueries({ queryKey: ['adStats'] });
      queryClient.invalidateQueries({ queryKey: ['competitors'] });
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}

export function useAnalyzeAds() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (limit: number) => adsApi.analyzeRun(limit),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ads'] });
      queryClient.invalidateQueries({ queryKey: ['adStats'] });
    },
  });
}

export function useAnalyzeAd() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (adId: string) => adsApi.analyze(adId),
    onSuccess: (_, adId) => {
      queryClient.invalidateQueries({ queryKey: ['ads'] });
      queryClient.invalidateQueries({ queryKey: ['ad', adId] });
      queryClient.invalidateQueries({ queryKey: ['adStats'] });
    },
  });
}
