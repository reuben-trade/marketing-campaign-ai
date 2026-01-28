'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useOnboardingStatus, useCompleteOnboarding } from '@/hooks/useOnboarding';
import { toast } from 'sonner';
import {
  Building2,
  Briefcase,
  Users,
  ChevronRight,
  ChevronLeft,
  Check,
  Loader2,
  Sparkles,
  X,
} from 'lucide-react';
import {
  INDUSTRY_OPTIONS,
  TONE_OPTIONS,
  DEFAULT_ONBOARDING_FORM_DATA,
  type OnboardingFormData,
} from '@/types/onboarding';

const STEPS = [
  {
    id: 1,
    title: 'Industry',
    description: 'Tell us about your business sector',
    icon: Building2,
  },
  {
    id: 2,
    title: 'Core Offer',
    description: 'Describe your main product or service',
    icon: Briefcase,
  },
  {
    id: 3,
    title: 'Brand Voice',
    description: 'Define your brand personality',
    icon: Users,
  },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<OnboardingFormData>(DEFAULT_ONBOARDING_FORM_DATA);
  const [keywordInput, setKeywordInput] = useState('');
  const [forbiddenTermInput, setForbiddenTermInput] = useState('');

  const { data: status, isLoading: statusLoading } = useOnboardingStatus();
  const completeMutation = useCompleteOnboarding();

  // Redirect if already completed onboarding
  useEffect(() => {
    if (status?.has_brand_profile && status?.completed_steps === 3) {
      router.push('/projects');
    }
  }, [status, router]);

  const updateFormData = (field: keyof OnboardingFormData, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const addKeyword = () => {
    if (keywordInput.trim() && formData.keywords.length < 10) {
      updateFormData('keywords', [...formData.keywords, keywordInput.trim()]);
      setKeywordInput('');
    }
  };

  const removeKeyword = (keyword: string) => {
    updateFormData(
      'keywords',
      formData.keywords.filter((k) => k !== keyword)
    );
  };

  const addForbiddenTerm = () => {
    if (forbiddenTermInput.trim() && formData.forbidden_terms.length < 20) {
      updateFormData('forbidden_terms', [...formData.forbidden_terms, forbiddenTermInput.trim()]);
      setForbiddenTermInput('');
    }
  };

  const removeForbiddenTerm = (term: string) => {
    updateFormData(
      'forbidden_terms',
      formData.forbidden_terms.filter((t) => t !== term)
    );
  };

  const isStepValid = (step: number): boolean => {
    switch (step) {
      case 1:
        return formData.industry.length > 0;
      case 2:
        return formData.core_offer.length >= 10;
      case 3:
        return true; // Step 3 is optional
      default:
        return false;
    }
  };

  const handleNext = () => {
    if (currentStep < 3 && isStepValid(currentStep)) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleComplete = async () => {
    try {
      await completeMutation.mutateAsync({
        industry: formData.industry,
        niche: formData.niche || undefined,
        core_offer: formData.core_offer,
        keywords: formData.keywords.length > 0 ? formData.keywords : undefined,
        tone: formData.tone || undefined,
        forbidden_terms: formData.forbidden_terms.length > 0 ? formData.forbidden_terms : undefined,
        primary_color: formData.primary_color || undefined,
        font_family: formData.font_family || undefined,
      });
      toast.success('Onboarding completed! Redirecting to projects...');
      router.push('/projects');
    } catch {
      toast.error('Failed to complete onboarding. Please try again.');
    }
  };

  if (statusLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="container max-w-3xl mx-auto py-8">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
          <Sparkles className="h-8 w-8 text-primary" />
        </div>
        <h1 className="text-3xl font-bold tracking-tight">Welcome to Ad Engine</h1>
        <p className="text-muted-foreground mt-2">
          Let&apos;s set up your brand profile to create personalized ads
        </p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center justify-center mb-8">
        {STEPS.map((step, index) => (
          <div key={step.id} className="flex items-center">
            <div
              className={`flex items-center justify-center w-10 h-10 rounded-full border-2 transition-colors ${
                currentStep > step.id
                  ? 'bg-primary border-primary text-primary-foreground'
                  : currentStep === step.id
                    ? 'border-primary text-primary'
                    : 'border-muted text-muted-foreground'
              }`}
            >
              {currentStep > step.id ? (
                <Check className="h-5 w-5" />
              ) : (
                <step.icon className="h-5 w-5" />
              )}
            </div>
            <div className="ml-2 mr-4 hidden sm:block">
              <p
                className={`text-sm font-medium ${
                  currentStep >= step.id ? 'text-foreground' : 'text-muted-foreground'
                }`}
              >
                {step.title}
              </p>
            </div>
            {index < STEPS.length - 1 && (
              <div
                className={`w-12 h-0.5 mx-2 ${
                  currentStep > step.id ? 'bg-primary' : 'bg-muted'
                }`}
              />
            )}
          </div>
        ))}
      </div>

      {/* Form Card */}
      <Card>
        <CardHeader>
          <CardTitle>{STEPS[currentStep - 1].title}</CardTitle>
          <CardDescription>{STEPS[currentStep - 1].description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Step 1: Industry */}
          {currentStep === 1 && (
            <>
              <div className="space-y-2">
                <Label htmlFor="industry">Industry *</Label>
                <Select value={formData.industry} onValueChange={(v) => updateFormData('industry', v)}>
                  <SelectTrigger id="industry">
                    <SelectValue placeholder="Select your industry" />
                  </SelectTrigger>
                  <SelectContent>
                    {INDUSTRY_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="niche">Niche (Optional)</Label>
                <Input
                  id="niche"
                  placeholder="e.g., Sustainable Fashion, B2B SaaS"
                  value={formData.niche}
                  onChange={(e) => updateFormData('niche', e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Be more specific about your market segment
                </p>
              </div>
            </>
          )}

          {/* Step 2: Core Offer */}
          {currentStep === 2 && (
            <>
              <div className="space-y-2">
                <Label htmlFor="core_offer">Core Offer *</Label>
                <Textarea
                  id="core_offer"
                  placeholder="Describe your main product or service in 1-2 sentences..."
                  value={formData.core_offer}
                  onChange={(e) => updateFormData('core_offer', e.target.value)}
                  rows={4}
                />
                <p className="text-xs text-muted-foreground">
                  {formData.core_offer.length}/1000 characters (min 10)
                </p>
              </div>
              <div className="space-y-2">
                <Label>Keywords</Label>
                <div className="flex gap-2">
                  <Input
                    placeholder="Add a keyword..."
                    value={keywordInput}
                    onChange={(e) => setKeywordInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addKeyword();
                      }
                    }}
                  />
                  <Button type="button" variant="outline" onClick={addKeyword}>
                    Add
                  </Button>
                </div>
                {formData.keywords.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {formData.keywords.map((keyword) => (
                      <Badge key={keyword} variant="secondary" className="gap-1">
                        {keyword}
                        <button
                          type="button"
                          onClick={() => removeKeyword(keyword)}
                          className="ml-1 hover:text-destructive"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
                <p className="text-xs text-muted-foreground">
                  Add keywords that define your brand (max 10)
                </p>
              </div>
            </>
          )}

          {/* Step 3: Brand Voice */}
          {currentStep === 3 && (
            <>
              <div className="space-y-2">
                <Label htmlFor="tone">Brand Tone</Label>
                <Select value={formData.tone} onValueChange={(v) => updateFormData('tone', v)}>
                  <SelectTrigger id="tone">
                    <SelectValue placeholder="Select your brand tone" />
                  </SelectTrigger>
                  <SelectContent>
                    {TONE_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  This helps us match your brand voice in generated content
                </p>
              </div>
              <div className="space-y-2">
                <Label>Forbidden Terms (Optional)</Label>
                <div className="flex gap-2">
                  <Input
                    placeholder="Add terms to avoid..."
                    value={forbiddenTermInput}
                    onChange={(e) => setForbiddenTermInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addForbiddenTerm();
                      }
                    }}
                  />
                  <Button type="button" variant="outline" onClick={addForbiddenTerm}>
                    Add
                  </Button>
                </div>
                {formData.forbidden_terms.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {formData.forbidden_terms.map((term) => (
                      <Badge key={term} variant="destructive" className="gap-1">
                        {term}
                        <button
                          type="button"
                          onClick={() => removeForbiddenTerm(term)}
                          className="ml-1 hover:text-foreground"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
                <p className="text-xs text-muted-foreground">
                  Words or phrases that should never appear in your ads
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="primary_color">Brand Color</Label>
                <div className="flex gap-2 items-center">
                  <Input
                    id="primary_color"
                    type="color"
                    value={formData.primary_color}
                    onChange={(e) => updateFormData('primary_color', e.target.value)}
                    className="w-16 h-10 p-1 cursor-pointer"
                  />
                  <Input
                    value={formData.primary_color}
                    onChange={(e) => updateFormData('primary_color', e.target.value)}
                    placeholder="#3B82F6"
                    className="flex-1"
                  />
                </div>
              </div>
            </>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between pt-4">
            <Button
              variant="outline"
              onClick={handleBack}
              disabled={currentStep === 1}
            >
              <ChevronLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            {currentStep < 3 ? (
              <Button onClick={handleNext} disabled={!isStepValid(currentStep)}>
                Next
                <ChevronRight className="h-4 w-4 ml-2" />
              </Button>
            ) : (
              <Button
                onClick={handleComplete}
                disabled={!isStepValid(1) || !isStepValid(2) || completeMutation.isPending}
              >
                {completeMutation.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Check className="h-4 w-4 mr-2" />
                )}
                Complete Setup
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Skip Option */}
      <div className="text-center mt-4">
        <Button variant="link" onClick={() => router.push('/projects')} className="text-muted-foreground">
          Skip for now
        </Button>
      </div>
    </div>
  );
}
