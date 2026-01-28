'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { InspirationSourceSelector } from '@/components/inspiration-source-selector';
import { useProject, useUpdateProject } from '@/hooks/useProjects';
import { useAds } from '@/hooks/useAds';
import { useExtractRecipe, useUploadReferenceAd, useFetchReferenceAd } from '@/hooks/useRecipes';
import { toast } from 'sonner';
import {
  ArrowLeft,
  ArrowRight,
  Loader2,
  AlertCircle,
  Sparkles,
  CheckCircle2,
  X,
  Video,
  Clock,
  TrendingUp,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import type { Ad } from '@/types/ad';

interface PageProps {
  params: { id: string };
}

export default function InspirePage({ params }: PageProps) {
  const { id: projectId } = params;
  const router = useRouter();

  const { data: project, isLoading: projectLoading, error: projectError } = useProject(projectId);
  const updateProject = useUpdateProject();
  const extractRecipe = useExtractRecipe();
  const uploadReference = useUploadReferenceAd();
  const fetchReference = useFetchReferenceAd();

  // Local state for selected ads
  const [selectedAdIds, setSelectedAdIds] = useState<string[]>([]);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isFetching, setIsFetching] = useState(false);

  // Fetch details of selected ads for display
  const { data: adsData } = useAds({
    page_size: 50,
    analyzed: true,
  });

  // Initialize selection from project's existing inspiration_ads
  useEffect(() => {
    if (project?.inspiration_ads) {
      setSelectedAdIds(project.inspiration_ads);
    }
  }, [project?.inspiration_ads]);

  // Get selected ad objects for display
  const selectedAds = (adsData?.items || []).filter((ad) => selectedAdIds.includes(ad.id));

  const handleContinue = async () => {
    if (selectedAdIds.length === 0) {
      toast.error('Please select at least one inspiration ad');
      return;
    }

    setIsExtracting(true);
    try {
      // Extract recipes for all selected ads
      const extractionPromises = selectedAdIds.map((adId) =>
        extractRecipe.mutateAsync({ ad_id: adId }).catch((error) => {
          console.error(`Failed to extract recipe for ad ${adId}:`, error);
          return null;
        })
      );

      const results = await Promise.all(extractionPromises);
      const failures = results.filter((r) => r === null).length;

      // Update project with selected inspiration ads
      await updateProject.mutateAsync({
        id: projectId,
        data: { inspiration_ads: selectedAdIds },
      });

      if (failures === selectedAdIds.length) {
        toast.error('Failed to extract recipes from selected ads');
      } else if (failures > 0) {
        toast.warning(`Inspiration saved. ${failures} recipe(s) failed to extract.`);
      } else {
        toast.success('Inspiration selected! Recipes extracted.');
      }

      // Navigate to the generation page (or back to project for now)
      router.push(`/projects/${projectId}`);
    } catch {
      toast.error('Failed to save inspiration selection');
    } finally {
      setIsExtracting(false);
    }
  };

  const removeSelection = (adId: string) => {
    setSelectedAdIds(selectedAdIds.filter((id) => id !== adId));
  };

  const handleUploadReference = async (file: File) => {
    setIsUploading(true);
    try {
      const result = await uploadReference.mutateAsync({ file });
      if (result.status === 'success' || result.status === 'partial') {
        // Add the new ad to selection
        setSelectedAdIds((prev) => {
          if (prev.length >= 3) {
            toast.warning('Maximum 3 ads selected. Replacing oldest selection.');
            return [...prev.slice(1), result.ad_id];
          }
          return [...prev, result.ad_id];
        });
        if (result.recipe) {
          toast.success('Reference ad analyzed and recipe extracted!');
        } else {
          toast.warning('Ad uploaded but recipe extraction failed. You can still use it.');
        }
      } else {
        toast.error(result.message);
      }
    } catch (error) {
      console.error('Upload failed:', error);
      toast.error('Failed to upload reference ad');
      throw error;
    } finally {
      setIsUploading(false);
    }
  };

  const handleFetchUrl = async (url: string) => {
    setIsFetching(true);
    try {
      const result = await fetchReference.mutateAsync({ url });
      if (result.status === 'success' || result.status === 'partial') {
        // Add the new ad to selection
        setSelectedAdIds((prev) => {
          if (prev.length >= 3) {
            toast.warning('Maximum 3 ads selected. Replacing oldest selection.');
            return [...prev.slice(1), result.ad_id];
          }
          return [...prev, result.ad_id];
        });
        if (result.recipe) {
          toast.success('Reference ad fetched and recipe extracted!');
        } else {
          toast.warning('Ad fetched but recipe extraction failed. You can still use it.');
        }
      } else {
        toast.error(result.message);
      }
    } catch (error) {
      console.error('Fetch failed:', error);
      toast.error('Failed to fetch ad from URL');
      throw error;
    } finally {
      setIsFetching(false);
    }
  };

  if (projectLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (projectError || !project) {
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

  const hasSegments = (project.stats?.segments_extracted || 0) > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Link href={`/projects/${projectId}`}>
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">Select Inspiration</h1>
            <p className="text-sm text-muted-foreground">{project.name}</p>
          </div>
        </div>
        <Button
          onClick={handleContinue}
          disabled={selectedAdIds.length === 0 || isExtracting || !hasSegments}
        >
          {isExtracting ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Extracting Recipes...
            </>
          ) : (
            <>
              Continue
              <ArrowRight className="ml-2 h-4 w-4" />
            </>
          )}
        </Button>
      </div>

      {/* Warning if no segments */}
      {!hasSegments && (
        <Card className="border-yellow-500 bg-yellow-50 dark:bg-yellow-950">
          <CardContent className="flex items-center gap-4 py-4">
            <AlertCircle className="h-5 w-5 text-yellow-600 flex-shrink-0" />
            <div>
              <p className="font-medium text-yellow-800 dark:text-yellow-200">
                No video segments found
              </p>
              <p className="text-sm text-yellow-700 dark:text-yellow-300">
                Please upload and analyze your raw footage before selecting inspiration.{' '}
                <Link
                  href={`/projects/${projectId}`}
                  className="underline hover:no-underline font-medium"
                >
                  Go to project
                </Link>
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Instructions */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">How it works</CardTitle>
          </div>
          <CardDescription>
            Select up to 3 winning ads as structural templates. We&apos;ll extract their &quot;recipes&quot;
            (timing, pacing, beat structure) and use them to generate your ad.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="flex gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary font-semibold text-sm flex-shrink-0">
                1
              </div>
              <div>
                <p className="font-medium">Browse winning ads</p>
                <p className="text-sm text-muted-foreground">
                  Choose from analyzed competitor ads or upload your own reference
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary font-semibold text-sm flex-shrink-0">
                2
              </div>
              <div>
                <p className="font-medium">Extract recipes</p>
                <p className="text-sm text-muted-foreground">
                  We analyze the structure: hooks, beats, transitions, timing
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary font-semibold text-sm flex-shrink-0">
                3
              </div>
              <div>
                <p className="font-medium">Generate your ad</p>
                <p className="text-sm text-muted-foreground">
                  Your footage is matched to the recipe structure
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Selected Ads Summary */}
      {selectedAdIds.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Selected Inspiration</CardTitle>
              <Badge variant="secondary">{selectedAdIds.length}/3</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {selectedAds.map((ad) => (
                <SelectedAdChip key={ad.id} ad={ad} onRemove={() => removeSelection(ad.id)} />
              ))}
              {/* Show placeholder chips for selected ads not yet loaded */}
              {selectedAdIds
                .filter((id) => !selectedAds.find((a) => a.id === id))
                .map((id) => (
                  <Badge key={id} variant="outline" className="py-1.5 px-3 gap-2">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Loading...
                    <button
                      onClick={() => removeSelection(id)}
                      className="ml-1 hover:text-destructive"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Separator />

      {/* Source Selector */}
      <InspirationSourceSelector
        selectedAdIds={selectedAdIds}
        onSelectionChange={setSelectedAdIds}
        maxSelections={3}
        onUploadReference={handleUploadReference}
        onFetchUrl={handleFetchUrl}
        isUploading={isUploading}
        isFetching={isFetching}
      />
    </div>
  );
}

interface SelectedAdChipProps {
  ad: Ad;
  onRemove: () => void;
}

function SelectedAdChip({ ad, onRemove }: SelectedAdChipProps) {
  const scorePercent = Math.round((ad.composite_score || 0) * 100);

  return (
    <div className="flex items-center gap-2 rounded-lg border bg-muted/50 p-2 pr-3">
      {/* Mini thumbnail */}
      <div className="relative h-10 w-14 rounded overflow-hidden bg-muted flex-shrink-0">
        {ad.creative_url ? (
          ad.creative_type === 'video' ? (
            <video src={ad.creative_url} className="h-full w-full object-cover" muted />
          ) : (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={ad.creative_url} alt="" className="h-full w-full object-cover" />
          )
        ) : (
          <div className="flex items-center justify-center h-full">
            <Video className="h-4 w-4 text-muted-foreground" />
          </div>
        )}
        <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-[10px] text-white text-center">
          {scorePercent}%
        </div>
      </div>

      {/* Info */}
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium truncate max-w-[150px]">
          {ad.ad_headline || ad.ad_summary?.slice(0, 30) || 'Untitled'}
        </p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <TrendingUp className="h-3 w-3" />
            {ad.total_engagement.toLocaleString()}
          </span>
          {ad.publication_date && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatDistanceToNow(new Date(ad.publication_date), { addSuffix: true })}
            </span>
          )}
        </div>
      </div>

      {/* Selected indicator */}
      <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0" />

      {/* Remove button */}
      <button
        onClick={onRemove}
        className="p-1 rounded-full hover:bg-destructive/10 hover:text-destructive transition-colors flex-shrink-0"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
