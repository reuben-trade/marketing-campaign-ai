'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import {
  useRecommendations,
  useLatestRecommendation,
  useGenerateRecommendation,
} from '@/hooks/useRecommendations';
import {
  Lightbulb,
  Loader2,
  Sparkles,
  TrendingUp,
  Video,
  ImageIcon,
  MapPin,
  Clock,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import type { Recommendation, AdRecommendation } from '@/types/recommendation';

export default function IdeasPage() {
  const [topNAds, setTopNAds] = useState(10);
  const [focusAreas, setFocusAreas] = useState<string[]>(['video', 'engagement']);

  const { data: recommendationsData } = useRecommendations({ page_size: 10 });
  const { data: latestRecommendation, isLoading: latestLoading } = useLatestRecommendation();
  const generateRecommendation = useGenerateRecommendation();

  const recommendations = recommendationsData?.items ?? [];

  const toggleFocusArea = (area: string) => {
    setFocusAreas((prev) =>
      prev.includes(area) ? prev.filter((a) => a !== area) : [...prev, area]
    );
  };

  const onGenerate = async () => {
    await generateRecommendation.mutateAsync({
      request: {
        top_n_ads: topNAds,
        focus_areas: focusAreas,
      },
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Content Ideas</h1>
        <p className="text-gray-500 mt-1">
          AI-powered recommendations based on competitor ad analysis
        </p>
      </div>

      {/* Generate Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-yellow-500" />
            Generate New Recommendations
          </CardTitle>
          <CardDescription>
            Analyze top-performing competitor ads to generate content ideas
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-6">
            <div className="space-y-2">
              <Label>Analyze top ads</Label>
              <Select value={topNAds.toString()} onValueChange={(v) => setTopNAds(parseInt(v))}>
                <SelectTrigger className="w-[120px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="5">5 ads</SelectItem>
                  <SelectItem value="10">10 ads</SelectItem>
                  <SelectItem value="20">20 ads</SelectItem>
                  <SelectItem value="50">50 ads</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Focus areas</Label>
              <div className="flex gap-3">
                <label className="flex items-center gap-2 cursor-pointer">
                  <Checkbox
                    checked={focusAreas.includes('video')}
                    onCheckedChange={() => toggleFocusArea('video')}
                  />
                  <span className="text-sm">Video</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <Checkbox
                    checked={focusAreas.includes('engagement')}
                    onCheckedChange={() => toggleFocusArea('engagement')}
                  />
                  <span className="text-sm">Engagement</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <Checkbox
                    checked={focusAreas.includes('brand_awareness')}
                    onCheckedChange={() => toggleFocusArea('brand_awareness')}
                  />
                  <span className="text-sm">Brand Awareness</span>
                </label>
              </div>
            </div>

            <Button onClick={onGenerate} disabled={generateRecommendation.isPending}>
              {generateRecommendation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating... (30-60s)
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Generate Recommendations
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Latest Recommendation */}
      {latestLoading ? (
        <Card>
          <CardContent className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
          </CardContent>
        </Card>
      ) : latestRecommendation ? (
        <RecommendationDisplay recommendation={latestRecommendation} />
      ) : (
        <Card>
          <CardContent className="text-center py-12">
            <Lightbulb className="h-12 w-12 mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500">No recommendations yet</p>
            <p className="text-sm text-gray-400 mt-1">
              Generate your first recommendation to get started
            </p>
          </CardContent>
        </Card>
      )}

      {/* Previous Recommendations */}
      {recommendations.length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Previous Recommendations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {recommendations.slice(1).map((rec) => (
                <div
                  key={rec.id}
                  className="flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50"
                >
                  <div>
                    <p className="font-medium text-sm">
                      {formatDistanceToNow(new Date(rec.generated_date), { addSuffix: true })}
                    </p>
                    <p className="text-xs text-gray-500">
                      {rec.recommendations.length} recommendations from {rec.ads_analyzed.length}{' '}
                      ads
                    </p>
                  </div>
                  <Badge variant="outline">{rec.model_used}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function RecommendationDisplay({ recommendation }: { recommendation: Recommendation }) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold">Latest Recommendations</h2>
              <p className="text-sm text-gray-500">
                Generated{' '}
                {formatDistanceToNow(new Date(recommendation.generated_date), { addSuffix: true })}{' '}
                using {recommendation.model_used}
              </p>
            </div>
            <div className="flex gap-2">
              <Badge>{recommendation.recommendations.length} recommendations</Badge>
              <Badge variant="outline">{recommendation.ads_analyzed.length} ads analyzed</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Executive Summary */}
      {recommendation.executive_summary && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-blue-500" />
              Executive Summary
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <p className="text-sm text-gray-700">{recommendation.executive_summary}</p>
          </CardContent>
        </Card>
      )}

      {/* Trend Analysis */}
      {recommendation.trend_analysis && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Trend Analysis</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {recommendation.trend_analysis.visual_trends &&
                recommendation.trend_analysis.visual_trends.length > 0 && (
                  <div>
                    <h4 className="font-medium text-sm mb-2">Visual Trends</h4>
                    <ul className="space-y-1">
                      {recommendation.trend_analysis.visual_trends.map((trend, i) => (
                        <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                          <span className="text-blue-500 mt-1">-</span>
                          {trend}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              {recommendation.trend_analysis.messaging_trends &&
                recommendation.trend_analysis.messaging_trends.length > 0 && (
                  <div>
                    <h4 className="font-medium text-sm mb-2">Messaging Trends</h4>
                    <ul className="space-y-1">
                      {recommendation.trend_analysis.messaging_trends.map((trend, i) => (
                        <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                          <span className="text-green-500 mt-1">-</span>
                          {trend}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              {recommendation.trend_analysis.cta_trends &&
                recommendation.trend_analysis.cta_trends.length > 0 && (
                  <div>
                    <h4 className="font-medium text-sm mb-2">CTA Trends</h4>
                    <ul className="space-y-1">
                      {recommendation.trend_analysis.cta_trends.map((trend, i) => (
                        <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                          <span className="text-purple-500 mt-1">-</span>
                          {trend}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-yellow-500" />
            Recommendations
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <Accordion type="single" collapsible className="w-full">
            {recommendation.recommendations.map((rec, index) => (
              <RecommendationCard key={index} recommendation={rec} index={index + 1} />
            ))}
          </Accordion>
        </CardContent>
      </Card>

      {/* Implementation Roadmap */}
      {recommendation.implementation_roadmap && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <MapPin className="h-5 w-5 text-green-500" />
              Implementation Roadmap
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="space-y-4">
              {recommendation.implementation_roadmap.phase_1_immediate &&
                recommendation.implementation_roadmap.phase_1_immediate.length > 0 && (
                  <div>
                    <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                      <Badge>Phase 1</Badge> Immediate Actions
                    </h4>
                    <ul className="space-y-1">
                      {recommendation.implementation_roadmap.phase_1_immediate.map((item, i) => (
                        <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                          <span className="text-green-500 mt-1">+</span>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              {recommendation.implementation_roadmap.phase_2_support &&
                recommendation.implementation_roadmap.phase_2_support.length > 0 && (
                  <div>
                    <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                      <Badge variant="outline">Phase 2</Badge> Support Actions
                    </h4>
                    <ul className="space-y-1">
                      {recommendation.implementation_roadmap.phase_2_support.map((item, i) => (
                        <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                          <span className="text-blue-500 mt-1">+</span>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function RecommendationCard({
  recommendation,
  index,
}: {
  recommendation: AdRecommendation;
  index: number;
}) {
  return (
    <AccordionItem value={`rec-${index}`}>
      <AccordionTrigger className="hover:no-underline">
        <div className="flex items-center gap-3">
          <Badge
            variant={recommendation.priority === 'high' ? 'destructive' : 'secondary'}
            className="shrink-0"
          >
            {recommendation.priority}
          </Badge>
          <div className="flex items-center gap-2 shrink-0">
            {recommendation.ad_format === 'video' ? (
              <Video className="h-4 w-4 text-gray-500" />
            ) : (
              <ImageIcon className="h-4 w-4 text-gray-500" />
            )}
          </div>
          <span className="text-left font-medium">{recommendation.concept.title}</span>
        </div>
      </AccordionTrigger>
      <AccordionContent>
        <div className="space-y-4 pt-4">
          <p className="text-sm text-gray-600">{recommendation.concept.description}</p>

          {recommendation.concept.marketing_framework && (
            <Badge variant="outline">{recommendation.concept.marketing_framework}</Badge>
          )}

          {recommendation.script_breakdown && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h5 className="font-medium text-sm mb-3">Script Breakdown</h5>
              <div className="space-y-3">
                {recommendation.script_breakdown.hook && (
                  <div className="flex gap-2">
                    <Badge className="bg-green-500 shrink-0">HOOK</Badge>
                    <div>
                      <p className="text-sm">{recommendation.script_breakdown.hook.opening_line}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        <Clock className="h-3 w-3 inline mr-1" />
                        {recommendation.script_breakdown.hook.timing}
                      </p>
                    </div>
                  </div>
                )}
                {recommendation.script_breakdown.problem_agitation && (
                  <div className="flex gap-2">
                    <Badge className="bg-red-400 shrink-0">PROBLEM</Badge>
                    <div>
                      <p className="text-sm">
                        {recommendation.script_breakdown.problem_agitation.pain_point}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        <Clock className="h-3 w-3 inline mr-1" />
                        {recommendation.script_breakdown.problem_agitation.timing}
                      </p>
                    </div>
                  </div>
                )}
                {recommendation.script_breakdown.solution_introduction && (
                  <div className="flex gap-2">
                    <Badge className="bg-blue-500 shrink-0">SOLUTION</Badge>
                    <div>
                      <p className="text-sm">
                        {recommendation.script_breakdown.solution_introduction.product_reveal}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        <Clock className="h-3 w-3 inline mr-1" />
                        {recommendation.script_breakdown.solution_introduction.timing}
                      </p>
                    </div>
                  </div>
                )}
                {recommendation.script_breakdown.cta && (
                  <div className="flex gap-2">
                    <Badge className="bg-pink-500 shrink-0">CTA</Badge>
                    <div>
                      <p className="text-sm">{recommendation.script_breakdown.cta.action}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        <Clock className="h-3 w-3 inline mr-1" />
                        {recommendation.script_breakdown.cta.timing}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {recommendation.testing_variants && recommendation.testing_variants.length > 0 && (
            <div>
              <h5 className="font-medium text-sm mb-2">Testing Variants</h5>
              <div className="flex flex-wrap gap-2">
                {recommendation.testing_variants.map((variant, i) => (
                  <Badge key={i} variant="outline">
                    {variant}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      </AccordionContent>
    </AccordionItem>
  );
}
