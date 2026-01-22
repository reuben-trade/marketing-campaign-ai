'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { strategyApi } from '@/lib/api/strategy';
import type { BusinessStrategyCreate } from '@/types/strategy';

export function useStrategies() {
  return useQuery({
    queryKey: ['strategies'],
    queryFn: strategyApi.list,
  });
}

export function useStrategy(id: string) {
  return useQuery({
    queryKey: ['strategy', id],
    queryFn: () => strategyApi.get(id),
    enabled: !!id,
  });
}

export function useCreateStrategy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (strategy: BusinessStrategyCreate) => strategyApi.create(strategy),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
  });
}

export function useUpdateStrategy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, strategy }: { id: string; strategy: Partial<BusinessStrategyCreate> }) =>
      strategyApi.update(id, strategy),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
      queryClient.invalidateQueries({ queryKey: ['strategy', variables.id] });
    },
  });
}

export function useUploadStrategyPDF() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (formData: FormData) => strategyApi.uploadPDF(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
  });
}
