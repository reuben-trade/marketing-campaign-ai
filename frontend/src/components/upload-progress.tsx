'use client';

import { useCallback, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useUploadProjectFiles } from '@/hooks/useProjects';
import { formatFileSize } from '@/lib/utils';
import { toast } from 'sonner';
import {
  Upload,
  X,
  CheckCircle2,
  AlertCircle,
  FileVideo,
  Loader2,
} from 'lucide-react';
import type { FileUploadProgress } from '@/types/project';

interface UploadProgressProps {
  projectId: string;
  maxFiles: number;
  maxTotalSizeMb: number;
  currentFileCount: number;
  currentTotalSizeMb: number;
  onUploadComplete?: () => void;
}

const ALLOWED_VIDEO_TYPES = [
  'video/mp4',
  'video/quicktime',
  'video/webm',
  'video/x-msvideo',
  'video/x-m4v',
  'video/x-matroska',
];

const MAX_FILE_SIZE_MB = 100;

export function UploadProgress({
  projectId,
  maxFiles,
  maxTotalSizeMb,
  currentFileCount,
  currentTotalSizeMb,
  onUploadComplete,
}: UploadProgressProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileUploadProgress[]>([]);
  const [uploadProgress, setUploadProgress] = useState(0);

  const uploadMutation = useUploadProjectFiles();

  const remainingFileSlots = maxFiles - currentFileCount;
  const remainingSizeMb = maxTotalSizeMb - currentTotalSizeMb;

  const validateFiles = useCallback(
    (files: File[]): { valid: File[]; errors: string[] } => {
      const errors: string[] = [];
      const valid: File[] = [];

      for (const file of files) {
        // Check file type
        if (!ALLOWED_VIDEO_TYPES.includes(file.type)) {
          errors.push(`${file.name}: Invalid file type. Supported: mp4, mov, webm, avi, m4v, mkv`);
          continue;
        }

        // Check individual file size
        const fileSizeMb = file.size / (1024 * 1024);
        if (fileSizeMb > MAX_FILE_SIZE_MB) {
          errors.push(`${file.name}: File too large (max ${MAX_FILE_SIZE_MB}MB)`);
          continue;
        }

        valid.push(file);
      }

      // Check total count
      if (valid.length + currentFileCount > maxFiles) {
        const allowed = maxFiles - currentFileCount;
        errors.push(`Can only upload ${allowed} more file(s). Selected ${valid.length}.`);
        return { valid: valid.slice(0, allowed), errors };
      }

      // Check total size
      const totalSelectedSize = valid.reduce((sum, f) => sum + f.size / (1024 * 1024), 0);
      if (totalSelectedSize > remainingSizeMb) {
        errors.push(
          `Total size (${totalSelectedSize.toFixed(1)}MB) exceeds remaining space (${remainingSizeMb.toFixed(1)}MB)`
        );
      }

      return { valid, errors };
    },
    [currentFileCount, maxFiles, remainingSizeMb]
  );

  const handleFilesSelected = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return;

      const fileArray = Array.from(files);
      const { valid, errors } = validateFiles(fileArray);

      if (errors.length > 0) {
        errors.forEach((error) => toast.error(error));
      }

      if (valid.length > 0) {
        const newFiles: FileUploadProgress[] = valid.map((file) => ({
          file,
          progress: 0,
          status: 'pending',
        }));
        setSelectedFiles((prev) => [...prev, ...newFiles]);
      }
    },
    [validateFiles]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      handleFilesSelected(e.dataTransfer.files);
    },
    [handleFilesSelected]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const removeFile = useCallback((index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const clearFiles = useCallback(() => {
    setSelectedFiles([]);
    setUploadProgress(0);
  }, []);

  const handleUpload = useCallback(async () => {
    if (selectedFiles.length === 0) return;

    const filesToUpload = selectedFiles
      .filter((f) => f.status === 'pending')
      .map((f) => f.file);

    if (filesToUpload.length === 0) return;

    // Update status to uploading
    setSelectedFiles((prev) =>
      prev.map((f) => (f.status === 'pending' ? { ...f, status: 'uploading' } : f))
    );

    try {
      const result = await uploadMutation.mutateAsync({
        projectId,
        files: filesToUpload,
        onUploadProgress: (progressEvent) => {
          const percentCompleted = progressEvent.total
            ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
            : 0;
          setUploadProgress(percentCompleted);
        },
      });

      // Update statuses based on result
      setSelectedFiles((prev) =>
        prev.map((f) => {
          const uploaded = result.uploaded_files.find(
            (uf) => uf.original_filename === f.file.name
          );
          const failed = result.failed_files.find((ff) => ff.filename === f.file.name);

          if (uploaded) {
            return { ...f, status: 'completed', progress: 100 };
          } else if (failed) {
            return { ...f, status: 'failed', error: failed.error };
          }
          return f;
        })
      );

      if (result.uploaded_files.length > 0) {
        toast.success(`${result.uploaded_files.length} file(s) uploaded successfully`);
        onUploadComplete?.();
      }

      if (result.failed_files.length > 0) {
        result.failed_files.forEach((f) => {
          toast.error(`${f.filename}: ${f.error}`);
        });
      }
    } catch {
      setSelectedFiles((prev) =>
        prev.map((f) =>
          f.status === 'uploading'
            ? { ...f, status: 'failed', error: 'Upload failed' }
            : f
        )
      );
      toast.error('Upload failed. Please try again.');
    }
  }, [selectedFiles, projectId, uploadMutation, onUploadComplete]);

  const pendingFiles = selectedFiles.filter((f) => f.status === 'pending');
  const isUploading = uploadMutation.isPending;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center justify-between">
          <span>Upload Videos</span>
          <span className="text-sm font-normal text-muted-foreground">
            {currentFileCount}/{maxFiles} files ({currentTotalSizeMb.toFixed(1)}/{maxTotalSizeMb}MB)
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Drop Zone */}
        <div
          className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
            isDragOver
              ? 'border-primary bg-primary/5'
              : 'border-muted-foreground/25 hover:border-muted-foreground/50'
          } ${remainingFileSlots === 0 ? 'opacity-50 pointer-events-none' : ''}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          <Upload className="h-8 w-8 mx-auto text-muted-foreground mb-3" />
          <p className="text-sm text-muted-foreground mb-2">
            {remainingFileSlots > 0
              ? 'Drag and drop video files here, or click to browse'
              : 'Maximum file limit reached'}
          </p>
          <p className="text-xs text-muted-foreground mb-3">
            Supported: MP4, MOV, WebM, AVI, M4V, MKV (max {MAX_FILE_SIZE_MB}MB each)
          </p>
          <input
            type="file"
            multiple
            accept="video/*"
            className="hidden"
            id="file-upload"
            onChange={(e) => handleFilesSelected(e.target.files)}
            disabled={remainingFileSlots === 0}
          />
          <Button variant="outline" size="sm" asChild disabled={remainingFileSlots === 0}>
            <label htmlFor="file-upload" className="cursor-pointer">
              Browse Files
            </label>
          </Button>
        </div>

        {/* Selected Files List */}
        {selectedFiles.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">
                Selected Files ({selectedFiles.length})
              </span>
              {!isUploading && (
                <Button variant="ghost" size="sm" onClick={clearFiles}>
                  Clear All
                </Button>
              )}
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {selectedFiles.map((fileProgress, index) => (
                <div
                  key={`${fileProgress.file.name}-${index}`}
                  className="flex items-center gap-3 p-2 rounded-lg border bg-muted/30"
                >
                  <div className="flex-shrink-0">
                    {fileProgress.status === 'completed' ? (
                      <CheckCircle2 className="h-5 w-5 text-green-500" />
                    ) : fileProgress.status === 'failed' ? (
                      <AlertCircle className="h-5 w-5 text-destructive" />
                    ) : fileProgress.status === 'uploading' ? (
                      <Loader2 className="h-5 w-5 animate-spin text-primary" />
                    ) : (
                      <FileVideo className="h-5 w-5 text-muted-foreground" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{fileProgress.file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatFileSize(fileProgress.file.size)}
                      {fileProgress.error && (
                        <span className="text-destructive ml-2">{fileProgress.error}</span>
                      )}
                    </p>
                  </div>
                  {fileProgress.status === 'pending' && !isUploading && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 flex-shrink-0"
                      onClick={() => removeFile(index)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Upload Progress Bar */}
        {isUploading && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span>Uploading...</span>
              <span>{uploadProgress}%</span>
            </div>
            <Progress value={uploadProgress} />
          </div>
        )}

        {/* Upload Button */}
        {pendingFiles.length > 0 && (
          <Button
            onClick={handleUpload}
            disabled={isUploading}
            className="w-full"
          >
            {isUploading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="mr-2 h-4 w-4" />
                Upload {pendingFiles.length} File{pendingFiles.length > 1 ? 's' : ''}
              </>
            )}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
