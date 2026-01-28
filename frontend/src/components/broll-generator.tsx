'use client';

import { useState, useCallback, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Slider } from '@/components/ui/slider';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Loader2,
  Wand2,
  Sparkles,
  RefreshCw,
  Check,
  Play,
  Clock,
  AlertCircle,
  Video,
  ChevronDown,
  ChevronUp,
  Lightbulb,
} from 'lucide-react';
import {
  useGenerateBroll,
  useRegenerateBroll,
  useBrollStatus,
  useEnhancePrompt,
  useSelectBrollClip,
} from '@/hooks/useBroll';
import type {
  VeoAspectRatio,
  VeoStyle,
  VeoGeneratedClip,
} from '@/types/broll';
import {
  ASPECT_RATIO_LABELS,
  STYLE_LABELS,
  STATUS_INFO,
} from '@/types/broll';

export interface BRollGeneratorProps {
  projectId?: string;
  slotId?: string;
  initialPrompt?: string;
  aspectRatio?: VeoAspectRatio;
  onClipSelected?: (clip: VeoGeneratedClip, storageUrl: string) => void;
  onClose?: () => void;
  compact?: boolean;
}

/**
 * BRollGenerator component for generating B-Roll clips using Veo 2.
 *
 * Features:
 * - Prompt input with AI enhancement suggestions
 * - Style, aspect ratio, and duration controls
 * - Generation progress tracking with polling
 * - Clip variant preview and selection
 * - Regeneration with modified prompts
 */
export function BRollGenerator({
  projectId,
  slotId,
  initialPrompt = '',
  aspectRatio: initialAspectRatio = '9:16',
  onClipSelected,
  onClose,
  compact = false,
}: BRollGeneratorProps) {
  // Form state
  const [prompt, setPrompt] = useState(initialPrompt);
  const [negativePrompt, setNegativePrompt] = useState('');
  const [duration, setDuration] = useState(3);
  const [aspectRatio, setAspectRatio] = useState<VeoAspectRatio>(initialAspectRatio);
  const [style, setStyle] = useState<VeoStyle>('realistic');
  const [numVariants, setNumVariants] = useState(2);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Generation state
  const [currentGenerationId, setCurrentGenerationId] = useState<string | null>(null);
  const [selectedClipId, setSelectedClipId] = useState<string | null>(null);

  // Hooks
  const generateMutation = useGenerateBroll();
  const regenerateMutation = useRegenerateBroll();
  const enhancePromptMutation = useEnhancePrompt();
  const selectClipMutation = useSelectBrollClip();

  // Poll for status when we have a generation in progress
  const { data: statusData } = useBrollStatus(
    currentGenerationId,
    { poll: true }
  );

  // Update generation ID when mutation succeeds
  useEffect(() => {
    if (generateMutation.data?.id) {
      setCurrentGenerationId(generateMutation.data.id);
    }
  }, [generateMutation.data?.id]);

  useEffect(() => {
    if (regenerateMutation.data?.id) {
      setCurrentGenerationId(regenerateMutation.data.id);
    }
  }, [regenerateMutation.data?.id]);

  // Handle generation
  const handleGenerate = useCallback(() => {
    if (!prompt.trim()) return;

    generateMutation.mutate({
      prompt: prompt.trim(),
      duration_seconds: duration,
      aspect_ratio: aspectRatio,
      style,
      num_variants: numVariants,
      project_id: projectId,
      slot_id: slotId,
      negative_prompt: negativePrompt.trim() || null,
    });
  }, [prompt, duration, aspectRatio, style, numVariants, projectId, slotId, negativePrompt, generateMutation]);

  // Handle regeneration
  const handleRegenerate = useCallback((newPrompt?: string) => {
    if (!currentGenerationId) return;

    regenerateMutation.mutate({
      original_generation_id: currentGenerationId,
      prompt: newPrompt || null,
      duration_seconds: duration,
      style,
      num_variants: numVariants,
      negative_prompt: negativePrompt.trim() || null,
    });
  }, [currentGenerationId, duration, style, numVariants, negativePrompt, regenerateMutation]);

  // Handle prompt enhancement
  const handleEnhancePrompt = useCallback(() => {
    if (!prompt.trim()) return;

    enhancePromptMutation.mutate(
      {
        original_prompt: prompt.trim(),
        context: slotId ? `For use as B-Roll in slot: ${slotId}` : undefined,
        style_hints: [style],
      },
      {
        onSuccess: (data) => {
          // Use the first enhanced prompt
          if (data.enhanced_prompts.length > 0) {
            setPrompt(data.enhanced_prompts[0]);
          }
          // Apply recommended style if available
          if (data.style_recommendations.length > 0) {
            setStyle(data.style_recommendations[0]);
          }
        },
      }
    );
  }, [prompt, slotId, style, enhancePromptMutation]);

  // Handle clip selection
  const handleSelectClip = useCallback((clip: VeoGeneratedClip) => {
    setSelectedClipId(clip.id);
  }, []);

  // Handle confirm selection
  const handleConfirmSelection = useCallback(() => {
    if (!currentGenerationId || !selectedClipId) return;

    selectClipMutation.mutate(
      {
        generationId: currentGenerationId,
        request: {
          generation_id: currentGenerationId,
          clip_id: selectedClipId,
        },
      },
      {
        onSuccess: (data) => {
          onClipSelected?.(data.clip, data.storage_url);
        },
      }
    );
  }, [currentGenerationId, selectedClipId, selectClipMutation, onClipSelected]);

  // Determine current state
  const isGenerating = generateMutation.isPending || regenerateMutation.isPending;
  const isProcessing = statusData?.status === 'pending' || statusData?.status === 'processing';
  const isCompleted = statusData?.status === 'completed';
  const isFailed = statusData?.status === 'failed';
  const hasClips = (statusData?.clips?.length ?? 0) > 0;

  return (
    <Card className={compact ? 'border-0 shadow-none' : ''}>
      <CardHeader className={compact ? 'px-0 pt-0' : ''}>
        <CardTitle className="flex items-center gap-2">
          <Wand2 className="h-5 w-5" />
          Generate B-Roll
        </CardTitle>
        <CardDescription>
          Create AI-generated video clips using Veo 2
        </CardDescription>
      </CardHeader>

      <CardContent className={compact ? 'px-0' : ''}>
        <div className="space-y-4">
          {/* Prompt Input */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="broll-prompt">Describe the clip you want</Label>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleEnhancePrompt}
                      disabled={!prompt.trim() || enhancePromptMutation.isPending}
                    >
                      {enhancePromptMutation.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Lightbulb className="h-4 w-4" />
                      )}
                      <span className="ml-1">Enhance</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Use AI to improve your prompt</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <Textarea
              id="broll-prompt"
              placeholder="e.g., Close-up of water dripping from a faucet, cinematic lighting, slow motion"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={3}
              className="resize-none"
            />
            <p className="text-xs text-muted-foreground">
              Be specific about the scene, lighting, camera angle, and motion
            </p>
          </div>

          {/* Quick Settings */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="aspect-ratio">Aspect Ratio</Label>
              <Select value={aspectRatio} onValueChange={(v) => setAspectRatio(v as VeoAspectRatio)}>
                <SelectTrigger id="aspect-ratio">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(ASPECT_RATIO_LABELS) as VeoAspectRatio[]).map((ratio) => (
                    <SelectItem key={ratio} value={ratio}>
                      {ASPECT_RATIO_LABELS[ratio]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="style">Style</Label>
              <Select value={style} onValueChange={(v) => setStyle(v as VeoStyle)}>
                <SelectTrigger id="style">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(STYLE_LABELS) as VeoStyle[]).map((s) => (
                    <SelectItem key={s} value={s}>
                      {STYLE_LABELS[s]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Duration Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Duration</Label>
              <span className="text-sm font-medium">{duration}s</span>
            </div>
            <Slider
              value={[duration]}
              min={1}
              max={10}
              step={1}
              onValueChange={(v) => setDuration(v[0])}
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>1s</span>
              <span>10s</span>
            </div>
          </div>

          {/* Advanced Settings */}
          <div>
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-between"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              <span>Advanced Settings</span>
              {showAdvanced ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>

            {showAdvanced && (
              <div className="mt-3 space-y-4 rounded-lg border p-3">
                <div className="space-y-2">
                  <Label htmlFor="negative-prompt">Negative Prompt</Label>
                  <Input
                    id="negative-prompt"
                    placeholder="What to avoid (e.g., blurry, dark, shaky)"
                    value={negativePrompt}
                    onChange={(e) => setNegativePrompt(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Variants</Label>
                    <span className="text-sm font-medium">{numVariants}</span>
                  </div>
                  <Slider
                    value={[numVariants]}
                    min={1}
                    max={4}
                    step={1}
                    onValueChange={(v) => setNumVariants(v[0])}
                  />
                  <p className="text-xs text-muted-foreground">
                    Generate multiple variations to choose from
                  </p>
                </div>
              </div>
            )}
          </div>

          <Separator />

          {/* Generation Status */}
          {(isGenerating || isProcessing || isCompleted || isFailed) && (
            <div className="space-y-3">
              {/* Status Badge */}
              <div className="flex items-center gap-2">
                {isGenerating || isProcessing ? (
                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                ) : isCompleted ? (
                  <Check className="h-4 w-4 text-green-500" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-red-500" />
                )}
                <span className="text-sm font-medium">
                  {isGenerating
                    ? 'Starting generation...'
                    : statusData
                    ? STATUS_INFO[statusData.status].label
                    : 'Unknown'}
                </span>
                {statusData?.estimated_time_remaining_seconds && isProcessing && (
                  <Badge variant="secondary" className="ml-auto">
                    <Clock className="h-3 w-3 mr-1" />
                    ~{Math.round(statusData.estimated_time_remaining_seconds)}s remaining
                  </Badge>
                )}
              </div>

              {/* Progress Bar */}
              {isProcessing && statusData && (
                <Progress value={statusData.progress} className="h-2" />
              )}

              {/* Error Message */}
              {isFailed && statusData?.error_message && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  {statusData.error_message}
                </div>
              )}

              {/* Generated Clips */}
              {hasClips && (
                <div className="space-y-2">
                  <Label>Generated Clips</Label>
                  <ScrollArea className="h-[200px]">
                    <div className="grid grid-cols-2 gap-2 pr-2">
                      {statusData?.clips.map((clip) => (
                        <div
                          key={clip.id}
                          className={`relative rounded-lg border-2 cursor-pointer transition-all overflow-hidden ${
                            selectedClipId === clip.id
                              ? 'border-primary ring-2 ring-primary/20'
                              : 'border-transparent hover:border-muted-foreground/30'
                          }`}
                          onClick={() => handleSelectClip(clip)}
                        >
                          {/* Thumbnail */}
                          <div className="relative aspect-video bg-black">
                            {clip.thumbnail_url ? (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img
                                src={clip.thumbnail_url}
                                alt={`Variant ${clip.variant_index + 1}`}
                                className="w-full h-full object-cover"
                              />
                            ) : clip.url ? (
                              <video
                                src={clip.url}
                                className="w-full h-full object-cover"
                                muted
                                loop
                                onMouseEnter={(e) => e.currentTarget.play()}
                                onMouseLeave={(e) => {
                                  e.currentTarget.pause();
                                  e.currentTarget.currentTime = 0;
                                }}
                              />
                            ) : (
                              <div className="w-full h-full flex items-center justify-center">
                                <Video className="h-8 w-8 text-muted-foreground" />
                              </div>
                            )}

                            {/* Selection indicator */}
                            {selectedClipId === clip.id && (
                              <div className="absolute inset-0 bg-primary/20 flex items-center justify-center">
                                <Check className="h-8 w-8 text-primary" />
                              </div>
                            )}

                            {/* Play hint */}
                            {clip.url && selectedClipId !== clip.id && (
                              <div className="absolute inset-0 bg-black/40 opacity-0 hover:opacity-100 transition-opacity flex items-center justify-center">
                                <Play className="h-8 w-8 text-white" />
                              </div>
                            )}

                            {/* Variant badge */}
                            <Badge className="absolute top-2 left-2" variant="secondary">
                              Variant {clip.variant_index + 1}
                            </Badge>

                            {/* Duration badge */}
                            <Badge className="absolute bottom-2 right-2" variant="secondary">
                              <Clock className="h-3 w-3 mr-1" />
                              {clip.duration_seconds.toFixed(1)}s
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </div>
              )}
            </div>
          )}
        </div>
      </CardContent>

      <CardFooter className={`flex gap-2 ${compact ? 'px-0 pb-0' : ''}`}>
        {onClose && (
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
        )}

        <div className="flex-1" />

        {isCompleted && hasClips && (
          <>
            <Button
              variant="outline"
              onClick={() => handleRegenerate()}
              disabled={regenerateMutation.isPending}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Regenerate
            </Button>

            {onClipSelected && (
              <Button
                onClick={handleConfirmSelection}
                disabled={!selectedClipId || selectClipMutation.isPending}
              >
                {selectClipMutation.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Check className="h-4 w-4 mr-2" />
                )}
                Use Selected Clip
              </Button>
            )}
          </>
        )}

        {!isCompleted && !isProcessing && (
          <Button
            onClick={handleGenerate}
            disabled={!prompt.trim() || isGenerating || isProcessing}
          >
            {isGenerating ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4 mr-2" />
            )}
            Generate B-Roll
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}

export default BRollGenerator;
