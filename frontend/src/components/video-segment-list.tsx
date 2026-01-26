'use client';

import { useState } from 'react';
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
import { useProjectSegments, useAnalyzeProject } from '@/hooks/useProjects';
import { toast } from 'sonner';
import {
  Loader2,
  Play,
  Search,
  Layers,
  Clock,
  Video,
  Sparkles,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  FileVideo,
} from 'lucide-react';
import type { UserVideoSegment, AnalysisProgress } from '@/types/project';

interface VideoSegmentListProps {
  projectId: string;
  hasFiles: boolean;
}

export function VideoSegmentList({ projectId, hasFiles }: VideoSegmentListProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [analysisProgress, setAnalysisProgress] = useState<AnalysisProgress | null>(null);

  const { data: segmentsData, isLoading, refetch } = useProjectSegments(projectId);
  const analyzeMutation = useAnalyzeProject();

  const segments = segmentsData?.segments || [];
  const totalSegments = segmentsData?.total_segments || 0;

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

  const handleAnalyze = async (forceReanalyze: boolean = false) => {
    try {
      const progress = await analyzeMutation.mutateAsync({
        projectId,
        forceReanalyze,
      });
      setAnalysisProgress(progress);

      if (progress.status === 'completed') {
        toast.success(`Analysis complete! ${progress.segments_extracted} segments extracted.`);
        refetch();
      } else if (progress.status === 'failed') {
        toast.error(progress.error_message || 'Analysis failed');
      } else {
        toast.success('Analysis started. This may take a few minutes.');
        // Poll for updates
        pollAnalysisStatus();
      }
    } catch {
      toast.error('Failed to start analysis');
    }
  };

  const pollAnalysisStatus = async () => {
    // In a real implementation, you'd poll an endpoint for status updates
    // For now, just refetch segments periodically
    const interval = setInterval(async () => {
      const result = await refetch();
      if (result.data && result.data.total_segments > 0) {
        clearInterval(interval);
        setAnalysisProgress(null);
        toast.success('Analysis complete!');
      }
    }, 5000);

    // Stop polling after 5 minutes
    setTimeout(() => clearInterval(interval), 300000);
  };

  if (isLoading) {
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
          <div className="flex items-center gap-2">
            {hasFiles && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleAnalyze(totalSegments > 0)}
                disabled={analyzeMutation.isPending}
              >
                {analyzeMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : totalSegments > 0 ? (
                  <RefreshCw className="mr-2 h-4 w-4" />
                ) : (
                  <Sparkles className="mr-2 h-4 w-4" />
                )}
                {totalSegments > 0 ? 'Re-analyze' : 'Analyze Videos'}
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Analysis Progress */}
        {analysisProgress && analysisProgress.status === 'processing' && (
          <div className="p-4 rounded-lg border bg-muted/30 space-y-3">
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span className="text-sm font-medium">Analyzing videos...</span>
            </div>
            <Progress
              value={(analysisProgress.completed_files / analysisProgress.total_files) * 100}
            />
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>
                {analysisProgress.completed_files} of {analysisProgress.total_files} files
              </span>
              {analysisProgress.current_file && (
                <span>Processing: {analysisProgress.current_file}</span>
              )}
            </div>
          </div>
        )}

        {/* Empty State */}
        {totalSegments === 0 && !analyzeMutation.isPending && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Layers className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Segments Yet</h3>
            <p className="text-muted-foreground mb-4 max-w-sm">
              {hasFiles
                ? 'Click "Analyze Videos" to extract segments from your uploaded videos. This process uses AI to identify and describe each scene.'
                : 'Upload some videos first, then analyze them to extract segments.'}
            </p>
            {hasFiles && (
              <Button onClick={() => handleAnalyze(false)}>
                <Sparkles className="mr-2 h-4 w-4" />
                Analyze Videos
              </Button>
            )}
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
