'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { competitorsApi } from '@/lib/api/competitors';
import type { CompetitorCreate, CompetitorDiscoverRequest, CompetitorUpdate } from '@/types/competitor';

export function useCompetitors(params?: {
  page?: number;
  page_size?: number;
  active_only?: boolean;
}) {
  return useQuery({
    queryKey: ['competitors', params],
    queryFn: () => competitorsApi.list(params),
  });
}

export function useCompetitor(id: string) {
  return useQuery({
    queryKey: ['competitor', id],
    queryFn: () => competitorsApi.get(id),
    enabled: !!id,
  });
}

export function useAddCompetitor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (competitor: CompetitorCreate) => competitorsApi.add(competitor),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] });
    },
  });
}

export function useUpdateCompetitor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, competitor }: { id: string; competitor: CompetitorUpdate }) =>
      competitorsApi.update(id, competitor),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] });
      queryClient.invalidateQueries({ queryKey: ['competitor', variables.id] });
    },
  });
}

export function useDeleteCompetitor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => competitorsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] });
    },
  });
}

export function useDiscoverCompetitors() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CompetitorDiscoverRequest) => competitorsApi.discover(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] });
    },
  });
}
