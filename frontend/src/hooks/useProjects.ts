'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { projectsApi } from '@/lib/api/projects';
import type { ProjectFilters, ProjectCreate, ProjectUpdate, AnalysisProgress, SegmentSearchRequest } from '@/types/project';
import type { UploadProgressCallback } from '@/lib/api/client';

export function useProjects(filters?: ProjectFilters) {
  return useQuery({
    queryKey: ['projects', filters],
    queryFn: () => projectsApi.list(filters),
    staleTime: 30000, // 30 seconds
  });
}

export function useProject(id: string) {
  return useQuery({
    queryKey: ['project', id],
    queryFn: () => projectsApi.get(id),
    enabled: !!id,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ProjectCreate) => projectsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

export function useUpdateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ProjectUpdate }) =>
      projectsApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['project', id] });
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => projectsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

export function useProjectFiles(projectId: string) {
  return useQuery({
    queryKey: ['project-files', projectId],
    queryFn: () => projectsApi.getFiles(projectId),
    enabled: !!projectId,
  });
}

export function useDeleteProjectFile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, fileId }: { projectId: string; fileId: string }) =>
      projectsApi.deleteFile(projectId, fileId),
    onSuccess: (_, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: ['project-files', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

export function useUploadProjectFiles() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      files,
      onUploadProgress,
    }: {
      projectId: string;
      files: File[];
      onUploadProgress?: UploadProgressCallback;
    }) => projectsApi.uploadFiles(projectId, files, onUploadProgress),
    onSuccess: (_, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: ['project-files', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

export function useProjectSegments(projectId: string) {
  return useQuery({
    queryKey: ['project-segments', projectId],
    queryFn: () => projectsApi.getSegments(projectId),
    enabled: !!projectId,
    staleTime: 30000,
  });
}

export function useAnalyzeProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      forceReanalyze = false,
    }: {
      projectId: string;
      forceReanalyze?: boolean;
    }) => projectsApi.analyzeProject(projectId, forceReanalyze),
    onSuccess: (data: AnalysisProgress) => {
      queryClient.invalidateQueries({ queryKey: ['project-segments', data.project_id] });
      queryClient.invalidateQueries({ queryKey: ['project', data.project_id] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

export function useAnalyzeFile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, fileId }: { projectId: string; fileId: string }) =>
      projectsApi.analyzeFile(projectId, fileId),
    onSuccess: (_, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: ['project-segments', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

/**
 * Hook to search for segments within a project using semantic similarity
 */
export function useSearchSegments() {
  return useMutation({
    mutationFn: ({
      projectId,
      request,
    }: {
      projectId: string;
      request: SegmentSearchRequest;
    }) => projectsApi.searchSegments(projectId, request),
  });
}
