'use client';

import Link from 'next/link';
import { useCallback, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useProject, useProjectFiles, useDeleteProjectFile } from '@/hooks/useProjects';
import { UploadProgress } from '@/components/upload-progress';
import { VideoSegmentList } from '@/components/video-segment-list';
import { formatFileSize } from '@/lib/utils';
import { toast } from 'sonner';
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  Video,
  HardDrive,
  Layers,
  Trash2,
  FileVideo,
  Clock,
  Sparkles,
  ArrowRight,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import type { ProjectFile } from '@/types/project';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

const statusConfig: Record<
  string,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  draft: { label: 'Draft', variant: 'secondary' },
  processing: { label: 'Processing', variant: 'default' },
  ready: { label: 'Ready', variant: 'outline' },
  rendered: { label: 'Rendered', variant: 'default' },
};

interface PageProps {
  params: { id: string };
}

export default function ProjectDetailPage({ params }: PageProps) {
  const { id } = params;
  const { data: project, isLoading, error, refetch: refetchProject } = useProject(id);
  const { data: filesData, isLoading: filesLoading, refetch: refetchFiles } = useProjectFiles(id);
  const deleteFileMutation = useDeleteProjectFile();

  const [fileToDelete, setFileToDelete] = useState<ProjectFile | null>(null);
  const [activeTab, setActiveTab] = useState('upload');

  const handleDeleteFile = async () => {
    if (!fileToDelete) return;
    try {
      await deleteFileMutation.mutateAsync({
        projectId: id,
        fileId: fileToDelete.file_id,
      });
      setFileToDelete(null);
      toast.success('File deleted successfully');
    } catch {
      toast.error('Failed to delete file');
    }
  };

  const handleUploadComplete = useCallback(() => {
    refetchProject();
    refetchFiles();
  }, [refetchProject, refetchFiles]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="space-y-6">
        <Link href="/projects">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Projects
          </Button>
        </Link>
        <Card>
          <CardContent className="flex flex-col items-center justify-center h-64">
            <AlertCircle className="h-12 w-12 text-red-400 mb-4" />
            <p className="text-gray-500">Project not found</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const status = statusConfig[project.status] || statusConfig.draft;
  const stats = project.stats || { videos_uploaded: 0, total_size_mb: 0, segments_extracted: 0 };
  const files = filesData?.files || [];
  const hasFiles = files.length > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Link href="/projects">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">{project.name}</h1>
            <div className="flex items-center gap-3 mt-1">
              <Badge variant={status.variant}>{status.label}</Badge>
              <span className="text-sm text-muted-foreground flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                Updated {formatDistanceToNow(new Date(project.updated_at), { addSuffix: true })}
              </span>
            </div>
          </div>
        </div>
        {stats.segments_extracted > 0 && (
          <Button asChild>
            <Link href={`/projects/${id}/inspire`}>
              <Sparkles className="mr-2 h-4 w-4" />
              Select Inspiration
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        )}
      </div>

      {/* Project Description */}
      {project.user_prompt && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Description</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">{project.user_prompt}</p>
          </CardContent>
        </Card>
      )}

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Videos Uploaded</CardTitle>
            <Video className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.videos_uploaded}
              <span className="text-sm font-normal text-muted-foreground">
                /{project.max_videos}
              </span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Size</CardTitle>
            <HardDrive className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.total_size_mb.toFixed(1)}
              <span className="text-sm font-normal text-muted-foreground">
                /{project.max_total_size_mb} MB
              </span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Segments Extracted</CardTitle>
            <Layers className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.segments_extracted}</div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-3 lg:w-auto lg:grid-cols-none lg:inline-grid">
          <TabsTrigger value="upload" className="gap-2">
            <Video className="h-4 w-4" />
            <span className="hidden sm:inline">Upload</span>
          </TabsTrigger>
          <TabsTrigger value="files" className="gap-2">
            <FileVideo className="h-4 w-4" />
            <span className="hidden sm:inline">Files</span>
            {files.length > 0 && (
              <Badge variant="secondary" className="ml-1 hidden sm:inline">
                {files.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="segments" className="gap-2">
            <Layers className="h-4 w-4" />
            <span className="hidden sm:inline">Segments</span>
            {stats.segments_extracted > 0 && (
              <Badge variant="secondary" className="ml-1 hidden sm:inline">
                {stats.segments_extracted}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        {/* Upload Tab */}
        <TabsContent value="upload" className="space-y-4">
          <UploadProgress
            projectId={id}
            maxFiles={project.max_videos}
            maxTotalSizeMb={project.max_total_size_mb}
            currentFileCount={stats.videos_uploaded}
            currentTotalSizeMb={stats.total_size_mb}
            onUploadComplete={handleUploadComplete}
          />
        </TabsContent>

        {/* Files Tab */}
        <TabsContent value="files" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Uploaded Files</CardTitle>
            </CardHeader>
            <CardContent>
              {filesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                </div>
              ) : files.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                  <FileVideo className="h-12 w-12 mb-2 opacity-50" />
                  <p>No files uploaded yet</p>
                  <Button
                    variant="link"
                    className="mt-2"
                    onClick={() => setActiveTab('upload')}
                  >
                    Upload your first video
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  {files.map((file) => (
                    <div
                      key={file.file_id}
                      className="flex items-center justify-between p-3 rounded-lg border bg-muted/50"
                    >
                      <div className="flex items-center gap-3">
                        <FileVideo className="h-5 w-5 text-muted-foreground" />
                        <div>
                          <p className="font-medium text-sm">{file.original_filename}</p>
                          <p className="text-xs text-muted-foreground">
                            {formatFileSize(file.file_size_bytes)} •{' '}
                            <Badge
                              variant={file.status === 'uploaded' ? 'secondary' : 'outline'}
                              className="text-xs"
                            >
                              {file.status}
                            </Badge>
                          </p>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-destructive"
                        onClick={() => setFileToDelete(file)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Segments Tab */}
        <TabsContent value="segments" className="space-y-4">
          <VideoSegmentList projectId={id} hasFiles={hasFiles} />
        </TabsContent>
      </Tabs>

      {/* Delete File Confirmation */}
      <AlertDialog open={!!fileToDelete} onOpenChange={(open) => !open && setFileToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete File</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{fileToDelete?.original_filename}&quot;? This
              action cannot be undone and will also remove all extracted segments from this file.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteFile}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteFileMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
