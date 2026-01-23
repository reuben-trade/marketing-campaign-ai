'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { useUploadCritique, useCritiques, useCritique, useDeleteCritique } from '@/hooks/useCritique';
import {
  Upload,
  X,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  Wrench,
  Target,
  TrendingUp,
  Video,
  ImageIcon,
  Clock,
  Zap,
  History,
  Trash2,
} from 'lucide-react';
import type { CritiqueResponse, CritiqueListItem } from '@/types/critique';
import type { StrengthItem, WeaknessItem, RemakeSuggestion } from '@/types/analysis';

export default function CritiquePage() {
  const [uploadProgress, setUploadProgress] = useState(0);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [context, setContext] = useState({
    brand_name: '',
    industry: '',
    target_audience: '',
    platform_cta: '',
  });
  const [result, setResult] = useState<CritiqueResponse | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedCritiqueId, setSelectedCritiqueId] = useState<string | null>(null);

  const uploadCritique = useUploadCritique();
  const deleteCritique = useDeleteCritique();
  const { data: critiquesData } = useCritiques({ page_size: 50 });
  const { data: loadedCritique } = useCritique(selectedCritiqueId);

  // When a saved critique is loaded, show it as result
  const displayResult = selectedCritiqueId && loadedCritique ? loadedCritique : result;

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      setSelectedFile(file);
      setResult(null);
      setSelectedCritiqueId(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpg', '.jpeg', '.png', '.webp', '.gif'],
      'video/*': ['.mp4', '.mov', '.webm'],
    },
    maxSize: 100 * 1024 * 1024, // 100MB max
    multiple: false,
  });

  const handleUpload = async () => {
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append('file', selectedFile);
    if (context.brand_name) formData.append('brand_name', context.brand_name);
    if (context.industry) formData.append('industry', context.industry);
    if (context.target_audience) formData.append('target_audience', context.target_audience);
    if (context.platform_cta) formData.append('platform_cta', context.platform_cta);

    setUploadProgress(0);
    setAnalysisProgress(0);
    setSelectedCritiqueId(null);

    try {
      const response = await uploadCritique.mutateAsync({
        formData,
        onUploadProgress: (progressEvent) => {
          const percent = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1));
          setUploadProgress(percent);
          if (percent === 100) {
            // Start simulating analysis progress
            const interval = setInterval(() => {
              setAnalysisProgress((prev) => {
                if (prev >= 90) {
                  clearInterval(interval);
                  return prev;
                }
                return prev + Math.random() * 10;
              });
            }, 1000);
          }
        },
      });

      setAnalysisProgress(100);
      setResult(response);
    } catch {
      setUploadProgress(0);
      setAnalysisProgress(0);
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
    setResult(null);
    setUploadProgress(0);
    setAnalysisProgress(0);
  };

  const handleSelectCritique = (critique: CritiqueListItem) => {
    setSelectedCritiqueId(critique.id);
    setResult(null);
    setSelectedFile(null);
    setUploadProgress(0);
    setAnalysisProgress(0);
  };

  const handleDeleteCritique = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await deleteCritique.mutateAsync(id);
    if (selectedCritiqueId === id) {
      setSelectedCritiqueId(null);
    }
  };

  const handleNewAnalysis = () => {
    setSelectedCritiqueId(null);
    setResult(null);
    setSelectedFile(null);
  };

  const isVideo = selectedFile?.type.startsWith('video/');

  return (
    <div className="flex gap-6">
      {/* Main Content */}
      <div className="flex-1 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Get Feedback</h1>
          <p className="text-gray-500 mt-1">
            Upload your ad creative for AI-powered analysis and improvement suggestions
          </p>
        </div>

        {/* Upload Section */}
        {!displayResult && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5 text-blue-500" />
                Upload Your Creative
              </CardTitle>
              <CardDescription>
                Supported formats: Images (JPG, PNG, WebP, GIF - max 20MB) | Videos (MP4, MOV, WebM -
                max 100MB)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Dropzone */}
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                  isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
                }`}
              >
                <input {...getInputProps()} />
                {selectedFile ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-center gap-2">
                      {isVideo ? (
                        <Video className="h-10 w-10 text-purple-500" />
                      ) : (
                        <ImageIcon className="h-10 w-10 text-blue-500" />
                      )}
                    </div>
                    <div className="flex items-center justify-center gap-2">
                      <Badge variant="secondary">{selectedFile.name}</Badge>
                      <span className="text-sm text-gray-500">
                        ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                      </span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={(e) => {
                          e.stopPropagation();
                          clearFile();
                        }}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <Upload className="h-10 w-10 mx-auto text-gray-400 mb-3" />
                    <p className="text-gray-600">
                      {isDragActive
                        ? 'Drop your file here...'
                        : 'Drag & drop your ad creative here, or click to browse'}
                    </p>
                    <p className="text-sm text-gray-400 mt-2">
                      Images up to 20MB | Videos up to 100MB
                    </p>
                  </>
                )}
              </div>

              {/* Optional Context */}
              <div className="space-y-4">
                <h4 className="font-medium text-sm">Optional Context (improves analysis)</h4>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  <div className="space-y-2">
                    <Label htmlFor="brand_name">Brand Name</Label>
                    <Input
                      id="brand_name"
                      placeholder="Your brand"
                      value={context.brand_name}
                      onChange={(e) => setContext((prev) => ({ ...prev, brand_name: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="industry">Industry</Label>
                    <Input
                      id="industry"
                      placeholder="e.g., SaaS, E-commerce"
                      value={context.industry}
                      onChange={(e) => setContext((prev) => ({ ...prev, industry: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="target_audience">Target Audience</Label>
                    <Input
                      id="target_audience"
                      placeholder="e.g., Millennials, B2B"
                      value={context.target_audience}
                      onChange={(e) =>
                        setContext((prev) => ({ ...prev, target_audience: e.target.value }))
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="platform_cta">Platform CTA Button</Label>
                    <Input
                      id="platform_cta"
                      placeholder="e.g., Learn More, Shop Now"
                      value={context.platform_cta}
                      onChange={(e) =>
                        setContext((prev) => ({ ...prev, platform_cta: e.target.value }))
                      }
                    />
                  </div>
                </div>
              </div>

              {/* Upload Progress */}
              {uploadCritique.isPending && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                    <span className="text-sm text-gray-600">
                      {uploadProgress < 100 ? 'Uploading...' : 'Analyzing your creative...'}
                    </span>
                  </div>
                  <Progress value={uploadProgress < 100 ? uploadProgress : analysisProgress} />
                  {uploadProgress === 100 && (
                    <p className="text-xs text-gray-500">
                      {isVideo
                        ? 'Video analysis typically takes 20-45 seconds'
                        : 'Image analysis typically takes 10-20 seconds'}
                    </p>
                  )}
                </div>
              )}

              {/* Upload Button */}
              <Button
                onClick={handleUpload}
                disabled={!selectedFile || uploadCritique.isPending}
                className="w-full"
              >
                {uploadCritique.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Zap className="mr-2 h-4 w-4" />
                    Analyze Creative
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Results Section */}
        {displayResult && (
          <>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {displayResult.file_name && (
                  <Badge variant="outline">{displayResult.file_name}</Badge>
                )}
                {displayResult.created_at && (
                  <span className="text-sm text-gray-500">
                    {new Date(displayResult.created_at).toLocaleDateString(undefined, {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                )}
              </div>
              <Button variant="outline" size="sm" onClick={handleNewAnalysis}>
                <Upload className="mr-2 h-4 w-4" />
                New Analysis
              </Button>
            </div>
            <CritiqueResults result={displayResult} />
          </>
        )}
      </div>

      {/* History Sidebar */}
      {critiquesData && critiquesData.critiques.length > 0 && (
        <div className="w-72 flex-shrink-0">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <History className="h-4 w-4" />
                Previous Feedback ({critiquesData.total})
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <ScrollArea className="h-[600px]">
                <div className="space-y-1 p-3 pt-0">
                  {critiquesData.critiques.map((critique) => (
                    <CritiqueHistoryItem
                      key={critique.id}
                      critique={critique}
                      isSelected={selectedCritiqueId === critique.id}
                      onSelect={() => handleSelectCritique(critique)}
                      onDelete={(e) => handleDeleteCritique(critique.id, e)}
                    />
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

function CritiqueHistoryItem({
  critique,
  isSelected,
  onSelect,
  onDelete,
}: {
  critique: CritiqueListItem;
  isSelected: boolean;
  onSelect: () => void;
  onDelete: (e: React.MouseEvent) => void;
}) {
  const getGradeColor = (grade: string) => {
    const letter = grade.charAt(0).toUpperCase();
    switch (letter) {
      case 'A': return 'bg-green-500 text-white';
      case 'B': return 'bg-blue-500 text-white';
      case 'C': return 'bg-yellow-500 text-white';
      case 'D': return 'bg-orange-500 text-white';
      case 'F': return 'bg-red-500 text-white';
      default: return 'bg-gray-500 text-white';
    }
  };

  return (
    <div
      className={`p-3 rounded-lg cursor-pointer transition-colors group ${
        isSelected ? 'bg-blue-50 border border-blue-200' : 'hover:bg-gray-50 border border-transparent'
      }`}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {critique.media_type === 'video' ? (
              <Video className="h-3 w-3 text-purple-500 flex-shrink-0" />
            ) : (
              <ImageIcon className="h-3 w-3 text-blue-500 flex-shrink-0" />
            )}
            <span className="text-xs font-medium truncate">{critique.file_name}</span>
          </div>
          <div className="flex items-center gap-2">
            {critique.overall_grade && (
              <Badge className={`text-[10px] px-1.5 py-0 ${getGradeColor(critique.overall_grade)}`}>
                {critique.overall_grade}
              </Badge>
            )}
            <span className="text-[10px] text-gray-400">
              {new Date(critique.created_at).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
              })}
            </span>
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={onDelete}
        >
          <Trash2 className="h-3 w-3 text-gray-400 hover:text-red-500" />
        </Button>
      </div>
    </div>
  );
}

function CritiqueResults({ result }: { result: CritiqueResponse }) {
  const { analysis } = result;
  const { critique } = analysis;

  const getGradeColor = (grade: string) => {
    const letter = grade.charAt(0).toUpperCase();
    switch (letter) {
      case 'A':
        return 'bg-green-500';
      case 'B':
        return 'bg-blue-500';
      case 'C':
        return 'bg-yellow-500';
      case 'D':
        return 'bg-orange-500';
      case 'F':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <div className="space-y-6">
      {/* Grade Overview */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row items-center gap-6">
            {/* Overall Grade */}
            <div className="flex flex-col items-center">
              <div
                className={`w-24 h-24 rounded-full ${getGradeColor(
                  critique.overall_grade
                )} flex items-center justify-center`}
              >
                <span className="text-4xl font-bold text-white">{critique.overall_grade}</span>
              </div>
              <span className="text-sm text-gray-500 mt-2">Overall Grade</span>
            </div>

            {/* Score Cards */}
            <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-4">
              <ScoreCard
                label="Hook Score"
                value={analysis.hook_score}
                icon={<Target className="h-4 w-4" />}
              />
              <ScoreCard
                label="Pacing Score"
                value={analysis.overall_pacing_score}
                icon={<Clock className="h-4 w-4" />}
              />
              <ScoreCard
                label="Thumb Stop"
                value={analysis.thumb_stop_score || analysis.engagement_predictors?.thumb_stop_score || 0}
                icon={<TrendingUp className="h-4 w-4" />}
              />
              <ScoreCard
                label="Confidence"
                value={Math.round(analysis.analysis_confidence * 100)}
                icon={<CheckCircle2 className="h-4 w-4" />}
                suffix="%"
              />
            </div>
          </div>

          {/* Overall Assessment */}
          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-700">{critique.overall_assessment}</p>
          </div>

          {/* Meta Info */}
          <div className="mt-4 flex flex-wrap gap-2">
            <Badge variant="outline">
              {result.media_type === 'video' ? 'Video' : 'Image'}
            </Badge>
            <Badge variant="outline">{result.model_used}</Badge>
            <Badge variant="outline">
              Analyzed in {result.processing_time_seconds.toFixed(1)}s
            </Badge>
            <Badge variant="outline">
              {(result.file_size_bytes / 1024 / 1024).toFixed(2)} MB
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Detailed Analysis Tabs */}
      <Tabs defaultValue="strengths" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="strengths" className="flex items-center gap-1">
            <CheckCircle2 className="h-4 w-4" />
            <span className="hidden sm:inline">Strengths</span>
          </TabsTrigger>
          <TabsTrigger value="weaknesses" className="flex items-center gap-1">
            <AlertTriangle className="h-4 w-4" />
            <span className="hidden sm:inline">Weaknesses</span>
          </TabsTrigger>
          <TabsTrigger value="remakes" className="flex items-center gap-1">
            <Wrench className="h-4 w-4" />
            <span className="hidden sm:inline">Remakes</span>
          </TabsTrigger>
          <TabsTrigger value="quickwins" className="flex items-center gap-1">
            <Lightbulb className="h-4 w-4" />
            <span className="hidden sm:inline">Quick Wins</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="strengths" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-500" />
                Strengths ({critique.strengths.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <div className="space-y-4">
                  {critique.strengths.map((strength, index) => (
                    <StrengthCard key={index} strength={strength} />
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="weaknesses" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-yellow-500" />
                Weaknesses ({critique.weaknesses.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <div className="space-y-4">
                  {critique.weaknesses.map((weakness, index) => (
                    <WeaknessCard key={index} weakness={weakness} />
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="remakes" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Wrench className="h-5 w-5 text-purple-500" />
                Remake Suggestions ({critique.remake_suggestions.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Accordion type="single" collapsible className="w-full">
                {critique.remake_suggestions.map((suggestion, index) => (
                  <RemakeSuggestionCard key={index} suggestion={suggestion} index={index} />
                ))}
              </Accordion>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="quickwins" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Lightbulb className="h-5 w-5 text-yellow-500" />
                Quick Wins ({critique.quick_wins.length})
              </CardTitle>
              <CardDescription>
                Low-effort improvements you can implement right away
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {critique.quick_wins.map((win, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-6 h-6 rounded-full bg-yellow-100 flex items-center justify-center">
                      <Zap className="h-3 w-3 text-yellow-600" />
                    </div>
                    <span className="text-sm text-gray-700">{win}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Timeline Section for Videos */}
      {analysis.media_type === 'video' && analysis.timeline && analysis.timeline.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Beat-by-Beat Analysis</CardTitle>
            <CardDescription>
              Detailed breakdown of your video&apos;s narrative structure
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {analysis.timeline.map((beat, index) => (
                <div
                  key={index}
                  className="flex items-start gap-4 p-3 rounded-lg border hover:bg-gray-50"
                >
                  <div className="flex-shrink-0">
                    <Badge variant="outline" className="font-mono text-xs">
                      {beat.start_time} - {beat.end_time}
                    </Badge>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge
                        className={getBeatTypeColor(beat.beat_type)}
                      >
                        {beat.beat_type}
                      </Badge>
                      {beat.attention_score && (
                        <span className="text-xs text-gray-500">
                          Attention: {beat.attention_score}/10
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-600">{beat.visual_description}</p>
                    {beat.improvement_note && (
                      <p className="text-xs text-orange-600 mt-1">
                        <Lightbulb className="h-3 w-3 inline mr-1" />
                        {beat.improvement_note}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function ScoreCard({
  label,
  value,
  icon,
  suffix = '/10',
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  suffix?: string;
}) {
  const getScoreColor = (score: number, max: number = 10) => {
    const normalized = max === 100 ? score / 10 : score;
    if (normalized >= 8) return 'text-green-600';
    if (normalized >= 6) return 'text-blue-600';
    if (normalized >= 4) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="bg-gray-50 rounded-lg p-3 text-center">
      <div className="flex items-center justify-center gap-1 text-gray-500 mb-1">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <div className={`text-2xl font-bold ${getScoreColor(value, suffix === '%' ? 100 : 10)}`}>
        {value}
        <span className="text-sm font-normal text-gray-500">{suffix}</span>
      </div>
    </div>
  );
}

function StrengthCard({ strength }: { strength: StrengthItem }) {
  return (
    <div className="p-4 rounded-lg border border-green-200 bg-green-50">
      <div className="flex items-start gap-3">
        <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
        <div className="space-y-2">
          <h4 className="font-medium text-green-900">{strength.strength}</h4>
          <p className="text-sm text-green-700">{strength.evidence}</p>
          {strength.timestamp && (
            <Badge variant="outline" className="text-xs">
              <Clock className="h-3 w-3 mr-1" />
              {strength.timestamp}
            </Badge>
          )}
          <p className="text-xs text-green-600">
            <strong>Impact:</strong> {strength.impact}
          </p>
        </div>
      </div>
    </div>
  );
}

function WeaknessCard({ weakness }: { weakness: WeaknessItem }) {
  return (
    <div className="p-4 rounded-lg border border-yellow-200 bg-yellow-50">
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
        <div className="space-y-2">
          <h4 className="font-medium text-yellow-900">{weakness.weakness}</h4>
          <p className="text-sm text-yellow-700">{weakness.evidence}</p>
          {weakness.timestamp && (
            <Badge variant="outline" className="text-xs">
              <Clock className="h-3 w-3 mr-1" />
              {weakness.timestamp}
            </Badge>
          )}
          <p className="text-xs text-yellow-600">
            <strong>Impact:</strong> {weakness.impact}
          </p>
          <div className="mt-2 p-2 bg-white rounded border border-yellow-300">
            <p className="text-sm text-gray-700">
              <strong>Suggested Fix:</strong> {weakness.suggested_fix}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function RemakeSuggestionCard({
  suggestion,
  index,
}: {
  suggestion: RemakeSuggestion;
  index: number;
}) {
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'destructive';
      case 'medium':
        return 'default';
      case 'low':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  const getEffortColor = (effort: string) => {
    switch (effort) {
      case 'minor tweak':
        return 'bg-green-100 text-green-700';
      case 'moderate edit':
        return 'bg-yellow-100 text-yellow-700';
      case 'full reshoot':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <AccordionItem value={`remake-${index}`}>
      <AccordionTrigger className="hover:no-underline">
        <div className="flex items-center gap-3">
          <Badge variant={getPriorityColor(suggestion.priority)}>{suggestion.priority}</Badge>
          <span className="text-left font-medium">{suggestion.section_to_remake}</span>
          <Badge className={getEffortColor(suggestion.effort_level)}>{suggestion.effort_level}</Badge>
        </div>
      </AccordionTrigger>
      <AccordionContent>
        <div className="space-y-4 pt-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="p-3 bg-red-50 rounded-lg border border-red-200">
              <h5 className="font-medium text-sm text-red-800 mb-2">Current Approach</h5>
              <p className="text-sm text-red-700">{suggestion.current_approach}</p>
            </div>
            <div className="p-3 bg-green-50 rounded-lg border border-green-200">
              <h5 className="font-medium text-sm text-green-800 mb-2">Suggested Approach</h5>
              <p className="text-sm text-green-700">{suggestion.suggested_approach}</p>
            </div>
          </div>
          <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
            <h5 className="font-medium text-sm text-blue-800 mb-2">Expected Improvement</h5>
            <p className="text-sm text-blue-700">{suggestion.expected_improvement}</p>
          </div>
        </div>
      </AccordionContent>
    </AccordionItem>
  );
}

function getBeatTypeColor(beatType: string): string {
  switch (beatType) {
    case 'Hook':
      return 'bg-green-500';
    case 'Problem':
      return 'bg-red-500';
    case 'Solution':
      return 'bg-blue-500';
    case 'Product Showcase':
      return 'bg-purple-500';
    case 'Social Proof':
      return 'bg-yellow-500';
    case 'Benefit Stack':
      return 'bg-cyan-500';
    case 'Objection Handling':
      return 'bg-orange-500';
    case 'CTA':
      return 'bg-pink-500';
    case 'Transition':
      return 'bg-gray-500';
    default:
      return 'bg-gray-400';
  }
}
