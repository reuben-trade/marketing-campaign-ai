'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { InspirationSourceSelector } from '@/components/inspiration-source-selector';
import {
  useProjects,
  useQuickCreateProject,
  useUploadProjectFiles,
  useAnalyzeProject,
} from '@/hooks/useProjects';
import { useUploadReferenceAd, useFetchReferenceAd } from '@/hooks/useRecipes';
import { toast } from 'sonner';
import {
  Wand2,
  FolderOpen,
  Upload,
  Sparkles,
  Video,
  Loader2,
  CheckCircle2,
  ChevronRight,
  FileVideo,
  Clock,
  X,
} from 'lucide-react';
import type { Project } from '@/types/project';

type SourceMode = 'upload' | 'select';

export default function StandaloneEditorPage() {
  const router = useRouter();

  // Source mode state
  const [sourceMode, setSourceMode] = useState<SourceMode>('upload');

  // Upload mode state
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Select mode state
  const [selectedProjectIds, setSelectedProjectIds] = useState<string[]>([]);

  // Inspiration state
  const [showInspiration, setShowInspiration] = useState(false);
  const [selectedInspirationIds, setSelectedInspirationIds] = useState<string[]>([]);
  const [isUploadingRef, setIsUploadingRef] = useState(false);
  const [isFetchingRef, setIsFetchingRef] = useState(false);

  // Instructions state
  const [userPrompt, setUserPrompt] = useState('');

  // Generating state
  const [isGenerating, setIsGenerating] = useState(false);

  // Queries and mutations
  const { data: projectsData, isLoading: projectsLoading } = useProjects({ page_size: 50 });
  const quickCreateMutation = useQuickCreateProject();
  const uploadFilesMutation = useUploadProjectFiles();
  const analyzeProjectMutation = useAnalyzeProject();
  const uploadReferenceMutation = useUploadReferenceAd();
  const fetchReferenceMutation = useFetchReferenceAd();

  // Filter projects with segments for selection
  const projectsWithSegments = (projectsData?.items || []).filter(
    (p) => (p.stats?.segments_extracted || 0) > 0
  );

  const toggleProjectSelection = (projectId: string) => {
    setSelectedProjectIds((prev) =>
      prev.includes(projectId)
        ? prev.filter((id) => id !== projectId)
        : [...prev, projectId]
    );
  };

  // File handling for upload mode
  const handleFilesSelected = useCallback((files: FileList | null) => {
    if (!files) return;

    const fileArray = Array.from(files);
    const validFiles = fileArray.filter((file) => {
      const validTypes = ['video/mp4', 'video/quicktime', 'video/webm', 'video/x-msvideo', 'video/x-m4v', 'video/x-matroska'];
      const maxSize = 100 * 1024 * 1024; // 100MB

      if (!validTypes.includes(file.type)) {
        toast.error(`${file.name}: Invalid file type`);
        return false;
      }
      if (file.size > maxSize) {
        toast.error(`${file.name}: File too large (max 100MB)`);
        return false;
      }
      return true;
    });

    if (validFiles.length > 10) {
      toast.warning('Maximum 10 files allowed. Only first 10 will be used.');
      setUploadFiles((prev) => [...prev, ...validFiles.slice(0, 10 - prev.length)]);
    } else {
      setUploadFiles((prev) => [...prev, ...validFiles].slice(0, 10));
    }
  }, []);

  const removeFile = (index: number) => {
    setUploadFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      handleFilesSelected(e.dataTransfer.files);
    },
    [handleFilesSelected]
  );

  // Reference ad handlers
  const handleUploadReference = async (file: File) => {
    setIsUploadingRef(true);
    try {
      const result = await uploadReferenceMutation.mutateAsync({ file });
      if (result.status === 'success' || result.status === 'partial') {
        setSelectedInspirationIds((prev) => {
          if (prev.length >= 3) {
            toast.warning('Maximum 3 inspirations. Replacing oldest.');
            return [...prev.slice(1), result.ad_id];
          }
          return [...prev, result.ad_id];
        });
        toast.success('Reference ad analyzed!');
      } else {
        toast.error(result.message);
      }
    } catch {
      toast.error('Failed to upload reference');
      throw new Error('Upload failed');
    } finally {
      setIsUploadingRef(false);
    }
  };

  const handleFetchUrl = async (url: string) => {
    setIsFetchingRef(true);
    try {
      const result = await fetchReferenceMutation.mutateAsync({ url });
      if (result.status === 'success' || result.status === 'partial') {
        setSelectedInspirationIds((prev) => {
          if (prev.length >= 3) {
            toast.warning('Maximum 3 inspirations. Replacing oldest.');
            return [...prev.slice(1), result.ad_id];
          }
          return [...prev, result.ad_id];
        });
        toast.success('Reference ad fetched!');
      } else {
        toast.error(result.message);
      }
    } catch {
      toast.error('Failed to fetch from URL');
      throw new Error('Fetch failed');
    } finally {
      setIsFetchingRef(false);
    }
  };

  // Check if we can generate
  const canGenerate =
    (sourceMode === 'upload' && uploadFiles.length > 0) ||
    (sourceMode === 'select' && selectedProjectIds.length > 0);

  // Main generate flow
  const handleGenerate = async () => {
    if (!canGenerate) return;

    setIsGenerating(true);

    try {
      let projectId: string;

      if (sourceMode === 'upload') {
        // Step 1: Create a quick project for uploading
        const quickProject = await quickCreateMutation.mutateAsync({
          user_prompt: userPrompt || undefined,
          inspiration_ad_ids: selectedInspirationIds.length > 0 ? selectedInspirationIds : undefined,
        });
        projectId = quickProject.id;

        // Step 2: Upload files to the project
        setIsUploading(true);
        await uploadFilesMutation.mutateAsync({
          projectId,
          files: uploadFiles,
          onUploadProgress: (event) => {
            if (event.total) {
              setUploadProgress(Math.round((event.loaded * 100) / event.total));
            }
          },
        });
        setIsUploading(false);

        // Step 3: Analyze the uploaded files
        setIsAnalyzing(true);
        await analyzeProjectMutation.mutateAsync({ projectId });
        setIsAnalyzing(false);

        toast.success('Project created and analyzed!');
      } else {
        // Select mode: create quick project with source projects
        const quickProject = await quickCreateMutation.mutateAsync({
          source_project_ids: selectedProjectIds,
          user_prompt: userPrompt || undefined,
          inspiration_ad_ids: selectedInspirationIds.length > 0 ? selectedInspirationIds : undefined,
        });
        projectId = quickProject.id;
        toast.success('Project created with copied segments!');
      }

      // Navigate to the project editor
      router.push(`/projects/${projectId}/editor`);
    } catch (error) {
      console.error('Generation failed:', error);
      toast.error('Failed to create project. Please try again.');
      setIsUploading(false);
      setIsAnalyzing(false);
    } finally {
      setIsGenerating(false);
    }
  };

  const getTotalSelectedSegments = () => {
    return selectedProjectIds.reduce((total, id) => {
      const project = projectsWithSegments.find((p) => p.id === id);
      return total + (project?.stats?.segments_extracted || 0);
    }, 0);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <Wand2 className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold">Create Ad</h1>
        </div>
        <p className="text-muted-foreground">
          Upload your videos or select from existing projects, then generate your ad.
        </p>
      </div>

      {/* Progress indicator when generating */}
      {isGenerating && (
        <Alert>
          <Loader2 className="h-4 w-4 animate-spin" />
          <AlertDescription className="ml-2">
            {isUploading
              ? `Uploading files... ${uploadProgress}%`
              : isAnalyzing
                ? 'Analyzing videos with AI...'
                : 'Creating project...'}
          </AlertDescription>
        </Alert>
      )}

      {/* Step 1: Source Selection */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-semibold">
              1
            </div>
            <CardTitle className="text-lg">Choose Your Source</CardTitle>
          </div>
          <CardDescription>
            Upload new videos or select clips from existing projects
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Tabs value={sourceMode} onValueChange={(v) => setSourceMode(v as SourceMode)}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="upload" className="gap-2">
                <Upload className="h-4 w-4" />
                Upload Videos
              </TabsTrigger>
              <TabsTrigger value="select" className="gap-2">
                <FolderOpen className="h-4 w-4" />
                Select Projects
              </TabsTrigger>
            </TabsList>

            {/* Upload Tab */}
            <TabsContent value="upload" className="mt-4 space-y-4">
              {/* Drop zone */}
              <div
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  uploadFiles.length >= 10
                    ? 'opacity-50 pointer-events-none border-muted'
                    : 'border-muted-foreground/25 hover:border-primary/50 cursor-pointer'
                }`}
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                onClick={() => document.getElementById('editor-file-input')?.click()}
              >
                <input
                  id="editor-file-input"
                  type="file"
                  multiple
                  accept="video/*"
                  className="hidden"
                  onChange={(e) => handleFilesSelected(e.target.files)}
                  disabled={uploadFiles.length >= 10}
                />
                <Upload className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
                <p className="font-medium">
                  {uploadFiles.length >= 10
                    ? 'Maximum files reached'
                    : 'Drop videos here or click to browse'}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  MP4, MOV, WebM, AVI, MKV (max 100MB each, up to 10 files)
                </p>
              </div>

              {/* Selected files list */}
              {uploadFiles.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Selected Files ({uploadFiles.length}/10)</Label>
                    <Button variant="ghost" size="sm" onClick={() => setUploadFiles([])}>
                      Clear All
                    </Button>
                  </div>
                  <ScrollArea className="h-40">
                    <div className="space-y-2 pr-4">
                      {uploadFiles.map((file, index) => (
                        <div
                          key={`${file.name}-${index}`}
                          className="flex items-center gap-3 p-2 rounded-lg border bg-muted/30"
                        >
                          <FileVideo className="h-5 w-5 text-muted-foreground flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{file.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {(file.size / 1024 / 1024).toFixed(1)} MB
                            </p>
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 flex-shrink-0"
                            onClick={() => removeFile(index)}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </div>
              )}
            </TabsContent>

            {/* Select Projects Tab */}
            <TabsContent value="select" className="mt-4 space-y-4">
              {projectsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : projectsWithSegments.length === 0 ? (
                <div className="text-center py-8">
                  <FolderOpen className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
                  <p className="text-muted-foreground">No projects with analyzed segments</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Upload videos to get started
                  </p>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between">
                    <Label>Select Projects ({selectedProjectIds.length} selected)</Label>
                    {selectedProjectIds.length > 0 && (
                      <Badge variant="secondary">
                        {getTotalSelectedSegments()} total segments
                      </Badge>
                    )}
                  </div>
                  <ScrollArea className="h-60">
                    <div className="space-y-2 pr-4">
                      {projectsWithSegments.map((project) => (
                        <ProjectSelectCard
                          key={project.id}
                          project={project}
                          selected={selectedProjectIds.includes(project.id)}
                          onToggle={() => toggleProjectSelection(project.id)}
                        />
                      ))}
                    </div>
                  </ScrollArea>
                </>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Step 2: Inspiration (Optional) */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/20 text-primary text-sm font-semibold">
                2
              </div>
              <CardTitle className="text-lg">Add Inspiration</CardTitle>
              <Badge variant="outline">Optional</Badge>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowInspiration(!showInspiration)}
            >
              {showInspiration ? 'Hide' : 'Show'}
              <ChevronRight
                className={`ml-1 h-4 w-4 transition-transform ${showInspiration ? 'rotate-90' : ''}`}
              />
            </Button>
          </div>
          <CardDescription>
            Select winning ads as structural templates for your video
          </CardDescription>
        </CardHeader>
        {showInspiration && (
          <CardContent className="space-y-4">
            {/* Selected inspirations summary */}
            {selectedInspirationIds.length > 0 && (
              <div className="flex flex-wrap gap-2 pb-2">
                {selectedInspirationIds.map((id) => (
                  <Badge
                    key={id}
                    variant="secondary"
                    className="gap-1 pr-1"
                  >
                    <Sparkles className="h-3 w-3" />
                    Inspiration
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-4 w-4 ml-1 hover:bg-destructive/20"
                      onClick={() =>
                        setSelectedInspirationIds((prev) => prev.filter((i) => i !== id))
                      }
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </Badge>
                ))}
              </div>
            )}

            <InspirationSourceSelector
              selectedAdIds={selectedInspirationIds}
              onSelectionChange={setSelectedInspirationIds}
              maxSelections={3}
              onUploadReference={handleUploadReference}
              onFetchUrl={handleFetchUrl}
              isUploading={isUploadingRef}
              isFetching={isFetchingRef}
            />
          </CardContent>
        )}
      </Card>

      {/* Step 3: Instructions (Optional) */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/20 text-primary text-sm font-semibold">
              3
            </div>
            <CardTitle className="text-lg">Creative Direction</CardTitle>
            <Badge variant="outline">Optional</Badge>
          </div>
          <CardDescription>
            Provide specific instructions for how you want your ad to look and feel
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label htmlFor="user-prompt">Instructions</Label>
            <Textarea
              id="user-prompt"
              placeholder="E.g., Focus on the 50% discount, use upbeat energy, highlight the product demo..."
              value={userPrompt}
              onChange={(e) => setUserPrompt(e.target.value)}
              rows={3}
            />
            <p className="text-xs text-muted-foreground">
              These instructions will guide the AI in selecting clips and generating your ad.
            </p>
          </div>
        </CardContent>
      </Card>

      <Separator />

      {/* Generate Button */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          {sourceMode === 'upload' && uploadFiles.length > 0 && (
            <span className="flex items-center gap-1">
              <Video className="h-4 w-4" />
              {uploadFiles.length} video{uploadFiles.length !== 1 ? 's' : ''} ready
            </span>
          )}
          {sourceMode === 'select' && selectedProjectIds.length > 0 && (
            <span className="flex items-center gap-1">
              <FolderOpen className="h-4 w-4" />
              {selectedProjectIds.length} project{selectedProjectIds.length !== 1 ? 's' : ''} selected
              ({getTotalSelectedSegments()} segments)
            </span>
          )}
        </div>
        <Button
          size="lg"
          onClick={handleGenerate}
          disabled={!canGenerate || isGenerating}
        >
          {isGenerating ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {isUploading ? 'Uploading...' : isAnalyzing ? 'Analyzing...' : 'Creating...'}
            </>
          ) : (
            <>
              <Wand2 className="mr-2 h-4 w-4" />
              Generate Ad
            </>
          )}
        </Button>
      </div>

      {/* Info about what happens next */}
      {canGenerate && (
        <Alert>
          <Clock className="h-4 w-4" />
          <AlertDescription>
            {sourceMode === 'upload'
              ? 'After clicking Generate, your videos will be uploaded and analyzed (2-3 minutes), then you\'ll be taken to the editor.'
              : 'After clicking Generate, your clips will be combined into a new project and you\'ll be taken to the editor.'}
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}

interface ProjectSelectCardProps {
  project: Project;
  selected: boolean;
  onToggle: () => void;
}

function ProjectSelectCard({ project, selected, onToggle }: ProjectSelectCardProps) {
  const segmentCount = project.stats?.segments_extracted || 0;
  const videoCount = project.stats?.videos_uploaded || 0;

  return (
    <div
      className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
        selected
          ? 'border-primary bg-primary/5'
          : 'border-border hover:bg-muted/50'
      }`}
      onClick={onToggle}
    >
      <Checkbox checked={selected} />
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{project.name}</p>
        <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
          <span className="flex items-center gap-1">
            <Video className="h-3 w-3" />
            {videoCount} video{videoCount !== 1 ? 's' : ''}
          </span>
          <span className="flex items-center gap-1">
            <FileVideo className="h-3 w-3" />
            {segmentCount} segment{segmentCount !== 1 ? 's' : ''}
          </span>
        </div>
      </div>
      {selected && (
        <CheckCircle2 className="h-5 w-5 text-primary flex-shrink-0" />
      )}
    </div>
  );
}
