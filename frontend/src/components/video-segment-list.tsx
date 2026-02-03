'use client';

import { useState, useEffect, useRef } from 'react';
import Image from 'next/image';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { useProjectSegments, useFilesStatus } from '@/hooks/useProjects';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Loader2,
  Play,
  Search,
  Layers,
  Clock,
  Video,
  AlertCircle,
  CheckCircle2,
  FileVideo,
  XCircle,
  Hourglass,
} from 'lucide-react';
import type { UserVideoSegment, FileStatusResponse } from '@/types/project';

interface VideoSegmentListProps {
  projectId: string;
  hasFiles: boolean;
}

export function VideoSegmentList({ projectId, hasFiles }: VideoSegmentListProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const queryClient = useQueryClient();
  const previousCompletedRef = useRef(0);

  const { data: segmentsData, isLoading: segmentsLoading } = useProjectSegments(projectId);
  const { data: statusData, isLoading: statusLoading } = useFilesStatus(projectId, hasFiles);

  const segments = segmentsData?.segments || [];
  const totalSegments = segmentsData?.total_segments || 0;

  // Track when files complete and refresh segments
  useEffect(() => {
    if (statusData) {
      const currentCompleted = statusData.completed_count;
      if (currentCompleted > previousCompletedRef.current && previousCompletedRef.current > 0) {
        // A file just completed - refresh segments
        queryClient.invalidateQueries({ queryKey: ['project-segments', projectId] });
        queryClient.invalidateQueries({ queryKey: ['project-files', projectId] });
        toast.success('File analysis complete!');
      }
      previousCompletedRef.current = currentCompleted;
    }
  }, [statusData, projectId, queryClient]);

  // Group segments by source file
  const segmentsByFile = segments.reduce(
    (acc, segment) => {
      const fileName = segment.source_file_name || 'Unknown File';
      if (!acc[fileName]) {
        acc[fileName] = [];
      }
      acc[fileName].push(segment);
      return acc;
    },
    {} as Record<string, UserVideoSegment[]>
  );

  // Filter segments by search query
  const filteredSegmentsByFile = Object.entries(segmentsByFile).reduce(
    (acc, [fileName, fileSegments]) => {
      if (!searchQuery) {
        acc[fileName] = fileSegments;
        return acc;
      }

      const query = searchQuery.toLowerCase();
      const filtered = fileSegments.filter(
        (segment) =>
          segment.visual_description?.toLowerCase().includes(query) ||
          segment.action_tags?.some((tag) => tag.toLowerCase().includes(query))
      );

      if (filtered.length > 0) {
        acc[fileName] = filtered;
      }
      return acc;
    },
    {} as Record<string, UserVideoSegment[]>
  );

  const filteredTotalSegments = Object.values(filteredSegmentsByFile).reduce(
    (sum, segs) => sum + segs.length,
    0
  );

  const isLoading = segmentsLoading || statusLoading;
  const hasProcessingFiles = statusData && (statusData.pending_count > 0 || statusData.processing_count > 0);
  const hasFailedFiles = statusData && statusData.failed_count > 0;
  const allFilesCompleted = statusData && statusData.total_files > 0 &&
    statusData.completed_count === statusData.total_files;

  if (isLoading && !statusData && !segmentsData) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-base">Video Segments</CardTitle>
            <Badge variant="secondary">{totalSegments}</Badge>
          </div>
          {/* Status indicators */}
          <div className="flex items-center gap-2">
            {hasProcessingFiles && (
              <Badge variant="outline" className="gap-1">
                <Loader2 className="h-3 w-3 animate-spin" />
                Analyzing...
              </Badge>
            )}
            {hasFailedFiles && (
              <Badge variant="destructive" className="gap-1">
                <XCircle className="h-3 w-3" />
                {statusData.failed_count} failed
              </Badge>
            )}
            {allFilesCompleted && totalSegments > 0 && (
              <Badge variant="default" className="gap-1 bg-green-600">
                <CheckCircle2 className="h-3 w-3" />
                Complete
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Processing Progress */}
        {hasFiles && statusData && hasProcessingFiles && (
          <ProcessingProgress statusData={statusData} />
        )}

        {/* Empty State */}
        {totalSegments === 0 && !hasProcessingFiles && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Layers className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Segments Yet</h3>
            <p className="text-muted-foreground mb-4 max-w-sm">
              {hasFiles
                ? 'Videos are automatically analyzed after upload. New segments will appear here once analysis completes.'
                : 'Upload some videos to get started. They will be automatically analyzed to extract segments.'}
            </p>
          </div>
        )}

        {/* Search */}
        {totalSegments > 0 && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search segments by description or tags..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        )}

        {/* File Status List (when processing) */}
        {hasFiles && statusData && statusData.total_files > 0 && (
          <FileStatusList files={statusData.files} />
        )}

        {/* Segments by File */}
        {Object.keys(filteredSegmentsByFile).length > 0 && (
          <Accordion type="multiple" className="space-y-2">
            {Object.entries(filteredSegmentsByFile).map(([fileName, fileSegments]) => (
              <AccordionItem key={fileName} value={fileName} className="border rounded-lg px-4">
                <AccordionTrigger className="hover:no-underline py-3">
                  <div className="flex items-center gap-3">
                    <FileVideo className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">{fileName}</span>
                    <Badge variant="outline" className="ml-2">
                      {fileSegments.length} segment{fileSegments.length !== 1 ? 's' : ''}
                    </Badge>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="pb-4">
                  <div className="space-y-3">
                    {fileSegments
                      .sort((a, b) => a.timestamp_start - b.timestamp_start)
                      .map((segment) => (
                        <SegmentCard key={segment.id} segment={segment} />
                      ))}
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        )}

        {/* No results */}
        {searchQuery && filteredTotalSegments === 0 && totalSegments > 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <AlertCircle className="h-8 w-8 text-muted-foreground/50 mb-2" />
            <p className="text-muted-foreground">
              No segments match &quot;{searchQuery}&quot;
            </p>
            <Button variant="link" onClick={() => setSearchQuery('')}>
              Clear search
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface ProcessingProgressProps {
  statusData: {
    total_files: number;
    pending_count: number;
    processing_count: number;
    completed_count: number;
    failed_count: number;
    total_segments: number;
  };
}

function ProcessingProgress({ statusData }: ProcessingProgressProps) {
  const completedOrFailed = statusData.completed_count + statusData.failed_count;
  const progressPercent = (completedOrFailed / statusData.total_files) * 100;

  return (
    <div className="p-4 rounded-lg border bg-muted/30 space-y-3">
      <div className="flex items-center gap-2">
        <Loader2 className="h-4 w-4 animate-spin text-primary" />
        <span className="text-sm font-medium">Analyzing videos...</span>
      </div>
      <Progress value={progressPercent} />
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {statusData.completed_count} of {statusData.total_files} files completed
        </span>
        {statusData.processing_count > 0 && (
          <span>{statusData.processing_count} processing</span>
        )}
      </div>
      {statusData.total_segments > 0 && (
        <p className="text-xs text-muted-foreground">
          {statusData.total_segments} segments extracted so far
        </p>
      )}
    </div>
  );
}

interface FileStatusListProps {
  files: FileStatusResponse[];
}

function FileStatusList({ files }: FileStatusListProps) {
  // Only show if there are files that aren't completed
  const activeFiles = files.filter(f => f.status !== 'completed');

  if (activeFiles.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-muted-foreground">File Status</p>
      <div className="space-y-1">
        {files.map((file) => (
          <div
            key={file.file_id}
            className="flex items-center justify-between py-2 px-3 rounded-md bg-muted/30 text-sm"
          >
            <div className="flex items-center gap-2 min-w-0">
              <FileStatusIcon status={file.status} />
              <span className="truncate">{file.original_filename}</span>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {file.segments_count > 0 && (
                <Badge variant="secondary" className="text-xs">
                  {file.segments_count} segments
                </Badge>
              )}
              <FileStatusBadge status={file.status} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function FileStatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'pending':
      return <Hourglass className="h-4 w-4 text-muted-foreground" />;
    case 'processing':
      return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
    case 'completed':
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case 'failed':
      return <XCircle className="h-4 w-4 text-destructive" />;
    default:
      return <FileVideo className="h-4 w-4 text-muted-foreground" />;
  }
}

function FileStatusBadge({ status }: { status: string }) {
  switch (status) {
    case 'pending':
      return <Badge variant="outline" className="text-xs">Pending</Badge>;
    case 'processing':
      return <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">Processing</Badge>;
    case 'completed':
      return <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-200">Complete</Badge>;
    case 'failed':
      return <Badge variant="destructive" className="text-xs">Failed</Badge>;
    default:
      return <Badge variant="outline" className="text-xs">{status}</Badge>;
  }
}

interface SegmentCardProps {
  segment: UserVideoSegment;
}

function SegmentCard({ segment }: SegmentCardProps) {
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex gap-4 p-3 rounded-lg border bg-card hover:bg-muted/30 transition-colors">
      {/* Thumbnail or placeholder */}
      <div className="flex-shrink-0 w-24 h-16 rounded bg-muted flex items-center justify-center overflow-hidden relative">
        {segment.thumbnail_url ? (
          <Image
            src={segment.thumbnail_url}
            alt="Segment thumbnail"
            fill
            className="object-cover"
            unoptimized
          />
        ) : (
          <Video className="h-6 w-6 text-muted-foreground" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium line-clamp-2 mb-1">
          {segment.visual_description || 'No description'}
        </p>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          {/* Timestamp */}
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span>
              {formatTime(segment.timestamp_start)} - {formatTime(segment.timestamp_end)}
            </span>
          </div>

          {/* Duration */}
          {segment.duration_seconds && (
            <div className="flex items-center gap-1">
              <Play className="h-3 w-3" />
              <span>{segment.duration_seconds.toFixed(1)}s</span>
            </div>
          )}
        </div>

        {/* Tags */}
        {segment.action_tags && segment.action_tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {segment.action_tags.slice(0, 5).map((tag, index) => (
              <Badge key={index} variant="secondary" className="text-xs px-1.5 py-0">
                {tag}
              </Badge>
            ))}
            {segment.action_tags.length > 5 && (
              <Badge variant="outline" className="text-xs px-1.5 py-0">
                +{segment.action_tags.length - 5}
              </Badge>
            )}
          </div>
        )}
      </div>

      {/* Status indicator */}
      <div className="flex-shrink-0">
        <CheckCircle2 className="h-4 w-4 text-green-500" />
      </div>
    </div>
  );
}
