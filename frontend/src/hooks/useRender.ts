'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { renderApi } from '@/lib/api/render';
import type { RenderRequest, RemotionPayload } from '@/types/render';

/**
 * Hook to get render status with optional polling
 */
export function useRenderStatus(renderId: string | null, options?: { poll?: boolean }) {
  return useQuery({
    queryKey: ['render-status', renderId],
    queryFn: () => renderApi.getStatus(renderId!),
    enabled: !!renderId,
    refetchInterval: options?.poll ? 2000 : false, // Poll every 2 seconds if enabled
    staleTime: 1000,
  });
}

/**
 * Hook to list renders for a project
 */
export function useProjectRenders(projectId: string, page: number = 1, pageSize: number = 20) {
  return useQuery({
    queryKey: ['project-renders', projectId, page, pageSize],
    queryFn: () => renderApi.listByProject(projectId, page, pageSize),
    enabled: !!projectId,
    staleTime: 10000,
  });
}

/**
 * Hook to get render queue statistics
 */
export function useRenderQueueStats() {
  return useQuery({
    queryKey: ['render-queue-stats'],
    queryFn: () => renderApi.getQueueStats(),
    staleTime: 5000,
    refetchInterval: 10000, // Refresh every 10 seconds
  });
}

/**
 * Hook to create a new render job
 */
export function useCreateRender() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: RenderRequest) => renderApi.create(request),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['project-renders', data.project_id] });
      queryClient.invalidateQueries({ queryKey: ['render-queue-stats'] });
    },
  });
}

/**
 * Hook to update a render's payload
 */
export function useUpdateRenderPayload() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ renderId, payload }: { renderId: string; payload: RemotionPayload }) =>
      renderApi.updatePayload(renderId, payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['render-status', data.id] });
      queryClient.invalidateQueries({ queryKey: ['project-renders', data.project_id] });
    },
  });
}

/**
 * Hook to cancel a render job
 */
export function useCancelRender() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (renderId: string) => renderApi.cancel(renderId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['render-status', data.id] });
      queryClient.invalidateQueries({ queryKey: ['project-renders', data.project_id] });
      queryClient.invalidateQueries({ queryKey: ['render-queue-stats'] });
    },
  });
}

/**
 * Hook to delete a render job
 */
export function useDeleteRender() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ renderId, projectId }: { renderId: string; projectId: string }) =>
      renderApi.delete(renderId).then(() => projectId),
    onSuccess: (projectId) => {
      queryClient.invalidateQueries({ queryKey: ['project-renders', projectId] });
      queryClient.invalidateQueries({ queryKey: ['render-queue-stats'] });
    },
  });
}
