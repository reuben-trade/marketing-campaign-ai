'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { InspirationGallery } from './inspiration-gallery';
import {
  Library,
  Upload,
  Link as LinkIcon,
  Clock,
  AlertCircle,
  Loader2,
  FileVideo,
} from 'lucide-react';
import { toast } from 'sonner';

export type InspirationSource = 'library' | 'upload' | 'url';

interface InspirationSourceSelectorProps {
  selectedAdIds: string[];
  onSelectionChange: (adIds: string[]) => void;
  onUploadReference?: (file: File) => Promise<void>;
  onFetchUrl?: (url: string) => Promise<void>;
  isUploading?: boolean;
  isFetching?: boolean;
  maxSelections?: number;
}

export function InspirationSourceSelector({
  selectedAdIds,
  onSelectionChange,
  onUploadReference,
  onFetchUrl,
  isUploading = false,
  isFetching = false,
  maxSelections = 3,
}: InspirationSourceSelectorProps) {
  const [activeSource, setActiveSource] = useState<InspirationSource>('library');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [urlInput, setUrlInput] = useState('');
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type.startsWith('video/')) {
        setUploadFile(file);
      } else {
        toast.error('Please upload a video file');
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.type.startsWith('video/')) {
        setUploadFile(file);
      } else {
        toast.error('Please upload a video file');
      }
    }
  };

  const handleUpload = async () => {
    if (!uploadFile || !onUploadReference) return;
    try {
      await onUploadReference(uploadFile);
      setUploadFile(null);
      toast.success('Reference ad uploaded for analysis');
    } catch {
      toast.error('Failed to upload reference ad');
    }
  };

  const handleFetchUrl = async () => {
    if (!urlInput.trim() || !onFetchUrl) return;

    // Basic URL validation
    try {
      new URL(urlInput);
    } catch {
      toast.error('Please enter a valid URL');
      return;
    }

    try {
      await onFetchUrl(urlInput);
      setUrlInput('');
      toast.success('Fetching ad from URL...');
    } catch {
      toast.error('Failed to fetch ad from URL');
    }
  };

  return (
    <div className="space-y-4">
      <Tabs
        value={activeSource}
        onValueChange={(v) => setActiveSource(v as InspirationSource)}
        className="space-y-4"
      >
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="library" className="gap-2">
            <Library className="h-4 w-4" />
            <span className="hidden sm:inline">Library</span>
          </TabsTrigger>
          <TabsTrigger value="upload" className="gap-2">
            <Upload className="h-4 w-4" />
            <span className="hidden sm:inline">Upload</span>
          </TabsTrigger>
          <TabsTrigger value="url" className="gap-2">
            <LinkIcon className="h-4 w-4" />
            <span className="hidden sm:inline">URL</span>
          </TabsTrigger>
        </TabsList>

        {/* Library Tab */}
        <TabsContent value="library" className="mt-4">
          <InspirationGallery
            selectedAdIds={selectedAdIds}
            onSelectionChange={onSelectionChange}
            maxSelections={maxSelections}
          />
        </TabsContent>

        {/* Upload Tab */}
        <TabsContent value="upload" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Upload Reference Ad</CardTitle>
              <CardDescription>
                Upload a reference video ad that you want to use as structural inspiration
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Alert>
                <Clock className="h-4 w-4" />
                <AlertDescription>
                  Analysis takes 2-3 minutes. We&apos;ll extract the ad structure and add it to your
                  inspiration sources.
                </AlertDescription>
              </Alert>

              {/* Drag and drop zone */}
              <div
                className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  dragActive
                    ? 'border-primary bg-primary/5'
                    : uploadFile
                      ? 'border-green-500 bg-green-50 dark:bg-green-950'
                      : 'border-muted-foreground/25 hover:border-muted-foreground/50'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  accept="video/*"
                  onChange={handleFileSelect}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                <div className="space-y-2">
                  {uploadFile ? (
                    <>
                      <FileVideo className="h-12 w-12 mx-auto text-green-600" />
                      <p className="font-medium">{uploadFile.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {(uploadFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </>
                  ) : (
                    <>
                      <Upload className="h-12 w-12 mx-auto text-muted-foreground" />
                      <p className="font-medium">Drop a video file here</p>
                      <p className="text-sm text-muted-foreground">or click to browse</p>
                    </>
                  )}
                </div>
              </div>

              {uploadFile && (
                <div className="flex gap-2 justify-end">
                  <Button variant="outline" onClick={() => setUploadFile(null)}>
                    Clear
                  </Button>
                  <Button onClick={handleUpload} disabled={isUploading || !onUploadReference}>
                    {isUploading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Upload & Analyze
                  </Button>
                </div>
              )}

              {!onUploadReference && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Upload functionality is not available yet. Please select from the library.
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* URL Tab */}
        <TabsContent value="url" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Fetch Ad from URL</CardTitle>
              <CardDescription>
                Paste a link to a video ad on Facebook, Instagram, TikTok, or YouTube
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Alert>
                <Clock className="h-4 w-4" />
                <AlertDescription>
                  Fetching and analysis takes 2-3 minutes. We&apos;ll download, analyze, and extract
                  the ad structure.
                </AlertDescription>
              </Alert>

              <div className="space-y-2">
                <Label htmlFor="ad-url">Ad URL</Label>
                <div className="flex gap-2">
                  <Input
                    id="ad-url"
                    type="url"
                    placeholder="https://www.facebook.com/ads/library/..."
                    value={urlInput}
                    onChange={(e) => setUrlInput(e.target.value)}
                  />
                  <Button onClick={handleFetchUrl} disabled={isFetching || !urlInput.trim()}>
                    {isFetching && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Fetch
                  </Button>
                </div>
              </div>

              <div className="text-sm text-muted-foreground">
                <p className="font-medium mb-1">Supported platforms:</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>Meta Ad Library (Facebook/Instagram)</li>
                  <li>TikTok Creative Center</li>
                  <li>YouTube</li>
                </ul>
              </div>

              {!onFetchUrl && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    URL fetch functionality is not available yet. Please select from the library.
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
