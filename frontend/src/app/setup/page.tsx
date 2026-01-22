'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useStrategies, useCreateStrategy, useUploadStrategyPDF } from '@/hooks/useStrategy';
import { Upload, FileText, X, CheckCircle2, Loader2 } from 'lucide-react';
import type { BusinessStrategyCreate } from '@/types/strategy';

const strategySchema = z.object({
  business_name: z.string().min(1, 'Business name is required'),
  business_description: z.string().optional(),
  industry: z.string().optional(),
  target_demographics: z.string().optional(),
  target_psychographics: z.string().optional(),
  target_pain_points: z.string().optional(),
  brand_tone: z.string().optional(),
  brand_personality: z.string().optional(),
  market_position: z.enum(['leader', 'challenger', 'niche']).optional(),
  price_point: z.enum(['premium', 'mid-market', 'budget']).optional(),
  unique_selling_points: z.string().optional(),
});

type StrategyFormData = z.infer<typeof strategySchema>;

export default function SetupPage() {
  const { data: strategies, isLoading: strategiesLoading } = useStrategies();
  const createStrategy = useCreateStrategy();
  const uploadPDF = useUploadStrategyPDF();
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedPDF, setSelectedPDF] = useState<File | null>(null);

  const existingStrategy = strategies?.[0];

  const form = useForm<StrategyFormData>({
    resolver: zodResolver(strategySchema),
    defaultValues: {
      business_name: existingStrategy?.business_name || '',
      business_description: existingStrategy?.business_description || '',
      industry: existingStrategy?.industry || '',
      target_demographics: existingStrategy?.target_audience?.demographics || '',
      target_psychographics: existingStrategy?.target_audience?.psychographics || '',
      target_pain_points: existingStrategy?.target_audience?.pain_points?.join(', ') || '',
      brand_tone: existingStrategy?.brand_voice?.tone || '',
      brand_personality: existingStrategy?.brand_voice?.personality_traits?.join(', ') || '',
      market_position: existingStrategy?.market_position || undefined,
      price_point: existingStrategy?.price_point || undefined,
      unique_selling_points: existingStrategy?.unique_selling_points?.join('\n') || '',
    },
  });

  const onSubmit = async (data: StrategyFormData) => {
    const strategy: BusinessStrategyCreate = {
      business_name: data.business_name,
      business_description: data.business_description,
      industry: data.industry,
      target_audience: {
        demographics: data.target_demographics,
        psychographics: data.target_psychographics,
        pain_points: data.target_pain_points?.split(',').map((p) => p.trim()).filter(Boolean),
      },
      brand_voice: {
        tone: data.brand_tone,
        personality_traits: data.brand_personality?.split(',').map((p) => p.trim()).filter(Boolean),
      },
      market_position: data.market_position,
      price_point: data.price_point,
      unique_selling_points: data.unique_selling_points?.split('\n').map((p) => p.trim()).filter(Boolean),
    };

    try {
      await createStrategy.mutateAsync(strategy);
      toast.success('Business strategy saved successfully');
    } catch {
      toast.error('Failed to save business strategy');
    }
  };

  const onDrop = useCallback(
    async (droppedFiles: File[]) => {
      const file = droppedFiles[0];
      if (!file) return;

      setSelectedPDF(file);

      const formData = new FormData();
      formData.append('file', file);

      try {
        setUploadProgress(0);
        await uploadPDF.mutateAsync(formData);
        setUploadProgress(100);
        toast.success('Strategy extracted from PDF successfully');
      } catch {
        toast.error('Failed to extract strategy from PDF');
        setUploadProgress(0);
      }
    },
    [uploadPDF]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxSize: 10 * 1024 * 1024,
    multiple: false,
  });

  if (strategiesLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Business Setup</h1>
        <p className="text-gray-500 mt-1">Configure your business strategy for better competitor analysis</p>
      </div>

      {existingStrategy && (
        <Card className="border-green-200 bg-green-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              <div>
                <p className="font-medium text-green-800">Strategy Configured</p>
                <p className="text-sm text-green-600">
                  {existingStrategy.business_name} - Last updated{' '}
                  {existingStrategy.last_updated
                    ? new Date(existingStrategy.last_updated).toLocaleDateString()
                    : 'N/A'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="manual" className="w-full">
        <TabsList>
          <TabsTrigger value="manual">Manual Entry</TabsTrigger>
          <TabsTrigger value="upload">Upload PDF</TabsTrigger>
        </TabsList>

        <TabsContent value="manual" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Business Information</CardTitle>
              <CardDescription>
                Enter your business details to help us provide better analysis and recommendations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="business_name">Business Name *</Label>
                    <Input
                      id="business_name"
                      {...form.register('business_name')}
                      placeholder="Your Company Name"
                    />
                    {form.formState.errors.business_name && (
                      <p className="text-sm text-red-500">
                        {form.formState.errors.business_name.message}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="industry">Industry</Label>
                    <Input
                      id="industry"
                      {...form.register('industry')}
                      placeholder="e.g., SaaS, E-commerce, Healthcare"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="business_description">Business Description</Label>
                  <Textarea
                    id="business_description"
                    {...form.register('business_description')}
                    placeholder="Describe what your business does..."
                    rows={3}
                  />
                </div>

                <div className="border-t pt-6">
                  <h3 className="font-medium mb-4">Target Audience</h3>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="target_demographics">Demographics</Label>
                      <Input
                        id="target_demographics"
                        {...form.register('target_demographics')}
                        placeholder="Age, location, income level..."
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="target_psychographics">Psychographics</Label>
                      <Input
                        id="target_psychographics"
                        {...form.register('target_psychographics')}
                        placeholder="Interests, values, lifestyle..."
                      />
                    </div>
                  </div>

                  <div className="space-y-2 mt-4">
                    <Label htmlFor="target_pain_points">Pain Points (comma-separated)</Label>
                    <Input
                      id="target_pain_points"
                      {...form.register('target_pain_points')}
                      placeholder="Problem 1, Problem 2, Problem 3..."
                    />
                  </div>
                </div>

                <div className="border-t pt-6">
                  <h3 className="font-medium mb-4">Brand Voice</h3>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="brand_tone">Tone</Label>
                      <Input
                        id="brand_tone"
                        {...form.register('brand_tone')}
                        placeholder="e.g., Professional, Friendly, Bold"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="brand_personality">Personality Traits (comma-separated)</Label>
                      <Input
                        id="brand_personality"
                        {...form.register('brand_personality')}
                        placeholder="Innovative, Trustworthy, Fun..."
                      />
                    </div>
                  </div>
                </div>

                <div className="border-t pt-6">
                  <h3 className="font-medium mb-4">Market Position</h3>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="market_position">Market Position</Label>
                      <Select
                        value={form.watch('market_position')}
                        onValueChange={(value) =>
                          form.setValue('market_position', value as 'leader' | 'challenger' | 'niche')
                        }
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select position" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="leader">Market Leader</SelectItem>
                          <SelectItem value="challenger">Challenger</SelectItem>
                          <SelectItem value="niche">Niche Player</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="price_point">Price Point</Label>
                      <Select
                        value={form.watch('price_point')}
                        onValueChange={(value) =>
                          form.setValue('price_point', value as 'premium' | 'mid-market' | 'budget')
                        }
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select price point" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="premium">Premium</SelectItem>
                          <SelectItem value="mid-market">Mid-Market</SelectItem>
                          <SelectItem value="budget">Budget</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="unique_selling_points">Unique Selling Points (one per line)</Label>
                  <Textarea
                    id="unique_selling_points"
                    {...form.register('unique_selling_points')}
                    placeholder="What makes your business unique..."
                    rows={3}
                  />
                </div>

                <Button type="submit" disabled={createStrategy.isPending}>
                  {createStrategy.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    'Save Strategy'
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="upload" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Upload Strategy Document</CardTitle>
              <CardDescription>
                Upload a PDF document about your business and we&apos;ll extract the strategy information
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
                  isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
                }`}
              >
                <input {...getInputProps()} />
                {uploadPDF.isPending ? (
                  <div className="space-y-4">
                    <Loader2 className="h-12 w-12 mx-auto animate-spin text-blue-500" />
                    <p className="text-gray-600">Extracting strategy from PDF...</p>
                    <Progress value={uploadProgress} className="w-48 mx-auto" />
                  </div>
                ) : selectedPDF ? (
                  <div className="space-y-4">
                    <FileText className="h-12 w-12 mx-auto text-green-500" />
                    <div className="flex items-center justify-center gap-2">
                      <Badge variant="secondary">{selectedPDF.name}</Badge>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedPDF(null);
                        }}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                    {uploadPDF.isSuccess && (
                      <p className="text-green-600 flex items-center justify-center gap-2">
                        <CheckCircle2 className="h-4 w-4" />
                        Strategy extracted successfully
                      </p>
                    )}
                  </div>
                ) : (
                  <>
                    <Upload className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                    <p className="text-gray-600">
                      {isDragActive
                        ? 'Drop the PDF here...'
                        : 'Drag & drop your strategy PDF here, or click to browse'}
                    </p>
                    <p className="text-sm text-gray-400 mt-2">Max 10MB - PDF only</p>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
