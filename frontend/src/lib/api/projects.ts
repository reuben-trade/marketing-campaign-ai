import { get, post, put, del, apiClient, UploadProgressCallback } from './client';
import type {
  Project,
  ProjectListResponse,
  ProjectCreate,
  ProjectUpdate,
  ProjectFilters,
  ProjectFilesListResponse,
  ProjectUploadResponse,
  ProjectSegmentsResponse,
  AnalysisProgress,
  SegmentSearchRequest,
  SegmentSearchResponse,
} from '@/types/project';

export const projectsApi = {
  list: async (filters?: ProjectFilters): Promise<ProjectListResponse> => {
    const params = new URLSearchParams();
    if (filters?.page) params.append('page', filters.page.toString());
    if (filters?.page_size) params.append('page_size', filters.page_size.toString());
    if (filters?.status) params.append('status', filters.status);

    const queryString = params.toString();
    return get<ProjectListResponse>(`/api/projects${queryString ? `?${queryString}` : ''}`);
  },

  get: async (id: string): Promise<Project> => {
    return get<Project>(`/api/projects/${id}`);
  },

  create: async (data: ProjectCreate): Promise<Project> => {
    return post<Project>('/api/projects', data);
  },

  update: async (id: string, data: ProjectUpdate): Promise<Project> => {
    return put<Project>(`/api/projects/${id}`, data);
  },

  delete: async (id: string): Promise<void> => {
    return del<void>(`/api/projects/${id}`);
  },

  getFiles: async (id: string): Promise<ProjectFilesListResponse> => {
    return get<ProjectFilesListResponse>(`/api/projects/${id}/files`);
  },

  deleteFile: async (projectId: string, fileId: string): Promise<void> => {
    return del<void>(`/api/projects/${projectId}/files/${fileId}`);
  },

  uploadFiles: async (
    projectId: string,
    files: File[],
    onUploadProgress?: UploadProgressCallback
  ): Promise<ProjectUploadResponse> => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await apiClient.post<ProjectUploadResponse>(
      `/api/projects/${projectId}/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: onUploadProgress
          ? (progressEvent) => {
              onUploadProgress({
                loaded: progressEvent.loaded,
                total: progressEvent.total,
              });
            }
          : undefined,
      }
    );
    return response.data;
  },

  getSegments: async (projectId: string): Promise<ProjectSegmentsResponse> => {
    return get<ProjectSegmentsResponse>(`/api/projects/${projectId}/segments`);
  },

  analyzeProject: async (
    projectId: string,
    forceReanalyze: boolean = false
  ): Promise<AnalysisProgress> => {
    return post<AnalysisProgress>(
      `/api/projects/${projectId}/analyze${forceReanalyze ? '?force_reanalyze=true' : ''}`
    );
  },

  analyzeFile: async (projectId: string, fileId: string): Promise<void> => {
    return post<void>(`/api/projects/${projectId}/files/${fileId}/analyze`);
  },

  searchSegments: async (
    projectId: string,
    request: SegmentSearchRequest
  ): Promise<SegmentSearchResponse> => {
    return post<SegmentSearchResponse>(`/api/projects/${projectId}/segments/search`, request);
  },
};
