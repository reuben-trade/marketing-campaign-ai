'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { brollApi } from '@/lib/api/broll';
import type {
  VeoGenerateRequest,
  VeoRegenerateRequest,
  VeoSelectClipRequest,
  PromptEnhancementRequest,
  VeoGenerationStatus,
} from '@/types/broll';

/**
 * Hook to get generation status with optional polling
 */
export function useBrollStatus(generationId: string | null, options?: { poll?: boolean }) {
  return useQuery({
    queryKey: ['broll-status', generationId],
    queryFn: () => brollApi.getStatus(generationId!),
    enabled: !!generationId,
    refetchInterval: (query) => {
      // Poll every 2 seconds if enabled and status is pending/processing
      if (!options?.poll) return false;
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') return false;
      return 2000;
    },
    staleTime: 1000,
  });
}

/**
 * Hook to list B-Roll generations with optional filtering
 */
export function useBrollList(options?: {
  projectId?: string;
  status?: VeoGenerationStatus;
  page?: number;
  pageSize?: number;
}) {
  return useQuery({
    queryKey: ['broll-list', options?.projectId, options?.status, options?.page, options?.pageSize],
    queryFn: () => brollApi.list(options),
    staleTime: 10000,
  });
}

/**
 * Hook to list B-Roll generations for a specific project
 */
export function useProjectBrollList(
  projectId: string,
  page: number = 1,
  pageSize: number = 20
) {
  return useQuery({
    queryKey: ['broll-list', projectId, null, page, pageSize],
    queryFn: () => brollApi.list({ projectId, page, pageSize }),
    enabled: !!projectId,
    staleTime: 10000,
  });
}

/**
 * Hook to generate B-Roll clips
 */
export function useGenerateBroll() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: VeoGenerateRequest) => brollApi.generate(request),
    onSuccess: (data) => {
      // Invalidate list queries
      queryClient.invalidateQueries({ queryKey: ['broll-list'] });
      // Set initial status in cache
      queryClient.setQueryData(['broll-status', data.id], {
        id: data.id,
        status: data.status,
        progress: 0,
        clips: data.clips,
        error_message: data.error_message,
        estimated_time_remaining_seconds: 30,
      });
    },
  });
}

/**
 * Hook to regenerate B-Roll clips
 */
export function useRegenerateBroll() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: VeoRegenerateRequest) => brollApi.regenerate(request),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['broll-list'] });
      queryClient.setQueryData(['broll-status', data.id], {
        id: data.id,
        status: data.status,
        progress: 0,
        clips: data.clips,
        error_message: data.error_message,
        estimated_time_remaining_seconds: 30,
      });
    },
  });
}

/**
 * Hook to delete a B-Roll generation
 */
export function useDeleteBroll() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (generationId: string) => brollApi.delete(generationId),
    onSuccess: (_, generationId) => {
      queryClient.invalidateQueries({ queryKey: ['broll-list'] });
      queryClient.removeQueries({ queryKey: ['broll-status', generationId] });
    },
  });
}

/**
 * Hook to enhance a B-Roll prompt
 */
export function useEnhancePrompt() {
  return useMutation({
    mutationFn: (request: PromptEnhancementRequest) => brollApi.enhancePrompt(request),
  });
}

/**
 * Hook to select a clip for use in the timeline
 */
export function useSelectBrollClip() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ generationId, request }: { generationId: string; request: VeoSelectClipRequest }) =>
      brollApi.selectClip(generationId, request),
    onSuccess: (_, { generationId }) => {
      queryClient.invalidateQueries({ queryKey: ['broll-status', generationId] });
    },
  });
}
