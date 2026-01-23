'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
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
  Palette,
  Camera,
  Music,
  Target,
  BarChart3,
  FileText,
  Mic,
  Film,
  Eye,
  Zap,
  Calendar,
  DollarSign,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import type {
  Recommendation,
  AdRecommendation,
  ScriptSection,
  VisualDirection,
  CaptionStrategy,
  FilmingRequirements,
  AudioDesign,
  TargetingAlignment,
  SuccessMetrics,
} from '@/types/recommendation';

export default function IdeasPage() {
  const [topNAds, setTopNAds] = useState(10);
  const [focusAreas, setFocusAreas] = useState<string[]>(['video', 'engagement']);
  const [numVideoIdeas, setNumVideoIdeas] = useState(2);
  const [numImageIdeas, setNumImageIdeas] = useState(1);

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
        num_video_ideas: numVideoIdeas,
        num_image_ideas: numImageIdeas,
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
          <div className="space-y-6">
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
            </div>

            <div className="flex flex-wrap items-end gap-6">
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Video className="h-4 w-4 text-blue-500" />
                  Video Ideas
                </Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    min={0}
                    max={10}
                    value={numVideoIdeas}
                    onChange={(e) => setNumVideoIdeas(Math.max(0, Math.min(10, parseInt(e.target.value) || 0)))}
                    className="w-[80px]"
                  />
                  <span className="text-sm text-gray-500">concepts</span>
                </div>
              </div>

              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <ImageIcon className="h-4 w-4 text-green-500" />
                  Image Ideas
                </Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    min={0}
                    max={10}
                    value={numImageIdeas}
                    onChange={(e) => setNumImageIdeas(Math.max(0, Math.min(10, parseInt(e.target.value) || 0)))}
                    className="w-[80px]"
                  />
                  <span className="text-sm text-gray-500">concepts</span>
                </div>
              </div>

              <div className="flex-1" />

              <Button
                onClick={onGenerate}
                disabled={generateRecommendation.isPending || (numVideoIdeas === 0 && numImageIdeas === 0)}
                size="lg"
              >
                {generateRecommendation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Generating... (30-60s)
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2 h-4 w-4" />
                    Generate {numVideoIdeas + numImageIdeas} Idea{numVideoIdeas + numImageIdeas !== 1 ? 's' : ''}
                  </>
                )}
              </Button>
            </div>

            {numVideoIdeas === 0 && numImageIdeas === 0 && (
              <p className="text-sm text-amber-600">
                Please specify at least one video or image idea to generate.
              </p>
            )}
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
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {/* Visual Trends */}
              {recommendation.trend_analysis.visual_trends &&
                recommendation.trend_analysis.visual_trends.length > 0 && (
                  <div>
                    <h4 className="font-medium text-sm mb-3">Visual Trends</h4>
                    <div className="space-y-3">
                      {recommendation.trend_analysis.visual_trends.map((trend, i) => (
                        <div key={i} className="border rounded-lg p-3 bg-blue-50/50">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium text-sm">{trend.trend}</span>
                            {trend.prevalence && (
                              <Badge variant="secondary" className="text-xs">{trend.prevalence}</Badge>
                            )}
                          </div>
                          <p className="text-sm text-gray-600">{trend.description}</p>
                          {trend.why_it_works && (
                            <p className="text-xs text-gray-500 mt-2 italic">
                              Why it works: {trend.why_it_works}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              {/* Messaging Trends */}
              {recommendation.trend_analysis.messaging_trends &&
                recommendation.trend_analysis.messaging_trends.length > 0 && (
                  <div>
                    <h4 className="font-medium text-sm mb-3">Messaging Trends</h4>
                    <div className="space-y-3">
                      {recommendation.trend_analysis.messaging_trends.map((trend, i) => (
                        <div key={i} className="border rounded-lg p-3 bg-green-50/50">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium text-sm">{trend.trend}</span>
                            {trend.prevalence && (
                              <Badge variant="secondary" className="text-xs">{trend.prevalence}</Badge>
                            )}
                          </div>
                          <p className="text-sm text-gray-600">{trend.description}</p>
                          {trend.why_it_works && (
                            <p className="text-xs text-gray-500 mt-2 italic">
                              Why it works: {trend.why_it_works}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              {/* CTA Trends */}
              {recommendation.trend_analysis.cta_trends &&
                recommendation.trend_analysis.cta_trends.length > 0 && (
                  <div>
                    <h4 className="font-medium text-sm mb-3">CTA Trends</h4>
                    <div className="space-y-3">
                      {recommendation.trend_analysis.cta_trends.map((trend, i) => (
                        <div key={i} className="border rounded-lg p-3 bg-purple-50/50">
                          <span className="font-medium text-sm">{trend.trend}</span>
                          <p className="text-sm text-gray-600 mt-1">{trend.effectiveness}</p>
                          {trend.examples && trend.examples.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-2">
                              {trend.examples.map((example, j) => (
                                <Badge key={j} variant="outline" className="text-xs">
                                  &ldquo;{example}&rdquo;
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
            </div>

            {/* Engagement Patterns */}
            {recommendation.trend_analysis.engagement_patterns && (
              <div className="mt-6 border-t pt-4">
                <h4 className="font-medium text-sm mb-3 flex items-center gap-2">
                  <Zap className="h-4 w-4 text-yellow-500" />
                  Engagement Patterns
                </h4>
                <div className="flex flex-wrap gap-4">
                  {recommendation.trend_analysis.engagement_patterns.best_performing_length && (
                    <div className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2">
                      <Clock className="h-4 w-4 text-gray-500" />
                      <span className="text-sm">
                        <span className="text-gray-500">Best length:</span>{' '}
                        <strong>{recommendation.trend_analysis.engagement_patterns.best_performing_length}</strong>
                      </span>
                    </div>
                  )}
                  {recommendation.trend_analysis.engagement_patterns.optimal_posting_time && (
                    <div className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2">
                      <Calendar className="h-4 w-4 text-gray-500" />
                      <span className="text-sm">
                        <span className="text-gray-500">Best time:</span>{' '}
                        <strong>{recommendation.trend_analysis.engagement_patterns.optimal_posting_time}</strong>
                      </span>
                    </div>
                  )}
                  {recommendation.trend_analysis.engagement_patterns.hook_timing && (
                    <div className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2">
                      <Eye className="h-4 w-4 text-gray-500" />
                      <span className="text-sm">
                        <span className="text-gray-500">Hook timing:</span>{' '}
                        <strong>{recommendation.trend_analysis.engagement_patterns.hook_timing}</strong>
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
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
              {/* Phase 1 */}
              {recommendation.implementation_roadmap.phase_1_immediate && (
                <div className="border rounded-lg p-4 bg-green-50/50">
                  <div className="flex items-center gap-2 mb-3">
                    <Badge className="bg-green-500">Phase 1</Badge>
                    <span className="font-medium text-sm">Immediate Actions</span>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm">
                      <strong>Action:</strong> {recommendation.implementation_roadmap.phase_1_immediate.action}
                    </p>
                    <p className="text-sm text-gray-600">
                      <strong>Rationale:</strong> {recommendation.implementation_roadmap.phase_1_immediate.rationale}
                    </p>
                    <div className="flex gap-4 mt-2">
                      <span className="text-xs flex items-center gap-1 text-gray-500">
                        <Calendar className="h-3 w-3" />
                        {recommendation.implementation_roadmap.phase_1_immediate.timeline}
                      </span>
                      <span className="text-xs flex items-center gap-1 text-gray-500">
                        <DollarSign className="h-3 w-3" />
                        {recommendation.implementation_roadmap.phase_1_immediate.budget_allocation}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Phase 2 */}
              {recommendation.implementation_roadmap.phase_2_support && (
                <div className="border rounded-lg p-4 bg-blue-50/50">
                  <div className="flex items-center gap-2 mb-3">
                    <Badge variant="outline">Phase 2</Badge>
                    <span className="font-medium text-sm">Support Actions</span>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm">
                      <strong>Action:</strong> {recommendation.implementation_roadmap.phase_2_support.action}
                    </p>
                    <p className="text-sm text-gray-600">
                      <strong>Rationale:</strong> {recommendation.implementation_roadmap.phase_2_support.rationale}
                    </p>
                    <div className="flex gap-4 mt-2">
                      <span className="text-xs flex items-center gap-1 text-gray-500">
                        <Calendar className="h-3 w-3" />
                        {recommendation.implementation_roadmap.phase_2_support.timeline}
                      </span>
                      <span className="text-xs flex items-center gap-1 text-gray-500">
                        <DollarSign className="h-3 w-3" />
                        {recommendation.implementation_roadmap.phase_2_support.budget_allocation}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Testing Protocol */}
              {recommendation.implementation_roadmap.testing_protocol && (
                <div className="border rounded-lg p-4 bg-purple-50/50">
                  <div className="flex items-center gap-2 mb-3">
                    <Badge variant="secondary">Testing Protocol</Badge>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm">
                      <strong>Duration:</strong> {recommendation.implementation_roadmap.testing_protocol.duration}
                    </p>
                    <div className="text-sm">
                      <strong>KPIs:</strong>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {recommendation.implementation_roadmap.testing_protocol.kpis.map((kpi, i) => (
                          <Badge key={i} variant="outline" className="text-xs">{kpi}</Badge>
                        ))}
                      </div>
                    </div>
                    <p className="text-sm text-gray-600">
                      <strong>Decision criteria:</strong> {recommendation.implementation_roadmap.testing_protocol.decision_criteria}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function ScriptSectionDisplay({
  section,
  label,
  badgeColor,
}: {
  section: ScriptSection;
  label: string;
  badgeColor: string;
}) {
  const displayText = section.visual_description || section.on_screen_text || section.action || section.opening_line || section.pain_point || section.product_reveal || '';

  return (
    <div className="flex gap-2">
      <Badge className={`${badgeColor} shrink-0`}>{label}</Badge>
      <div className="flex-1">
        {displayText && <p className="text-sm">{displayText}</p>}
        {section.action && section.action !== displayText && (
          <p className="text-xs text-gray-600 mt-1">Action: {section.action}</p>
        )}
        {section.timing && (
          <p className="text-xs text-gray-500 mt-1">
            <Clock className="h-3 w-3 inline mr-1" />
            {section.timing}
          </p>
        )}
        {section.why_this_works && (
          <p className="text-xs text-blue-600 mt-1 italic">
            {section.why_this_works}
          </p>
        )}
      </div>
    </div>
  );
}

function VisualDirectionDisplay({ direction }: { direction: VisualDirection }) {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <h5 className="font-medium text-sm mb-3 flex items-center gap-2">
        <Palette className="h-4 w-4 text-purple-500" />
        Visual Direction
      </h5>
      <div className="grid gap-3 md:grid-cols-2">
        {direction.overall_style && (
          <div>
            <span className="text-xs text-gray-500">Overall Style</span>
            <p className="text-sm">{direction.overall_style}</p>
          </div>
        )}
        {direction.setting && (
          <div>
            <span className="text-xs text-gray-500">Setting</span>
            <p className="text-sm">{direction.setting}</p>
          </div>
        )}
        {direction.composition && (
          <div>
            <span className="text-xs text-gray-500">Composition</span>
            <p className="text-sm">{direction.composition}</p>
          </div>
        )}
        {direction.camera_work && (
          <div>
            <span className="text-xs text-gray-500">Camera Work</span>
            <p className="text-sm">{direction.camera_work}</p>
          </div>
        )}
      </div>
      {direction.color_palette && (
        <div className="mt-3 pt-3 border-t">
          <span className="text-xs text-gray-500">Color Palette</span>
          <div className="flex gap-3 mt-2">
            <div className="flex items-center gap-1">
              <div
                className="w-6 h-6 rounded border"
                style={{ backgroundColor: direction.color_palette.primary }}
              />
              <span className="text-xs">Primary</span>
            </div>
            <div className="flex items-center gap-1">
              <div
                className="w-6 h-6 rounded border"
                style={{ backgroundColor: direction.color_palette.secondary }}
              />
              <span className="text-xs">Secondary</span>
            </div>
            <div className="flex items-center gap-1">
              <div
                className="w-6 h-6 rounded border"
                style={{ backgroundColor: direction.color_palette.accent }}
              />
              <span className="text-xs">Accent</span>
            </div>
          </div>
          {direction.color_palette.reasoning && (
            <p className="text-xs text-gray-500 mt-2 italic">{direction.color_palette.reasoning}</p>
          )}
        </div>
      )}
    </div>
  );
}

function CaptionStrategyDisplay({ strategy }: { strategy: CaptionStrategy }) {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <h5 className="font-medium text-sm mb-3 flex items-center gap-2">
        <FileText className="h-4 w-4 text-blue-500" />
        Caption Strategy
      </h5>
      <div className="grid gap-2 text-sm md:grid-cols-2">
        <div><span className="text-gray-500">Font:</span> {strategy.font}</div>
        <div><span className="text-gray-500">Size:</span> {strategy.size}</div>
        <div><span className="text-gray-500">Placement:</span> {strategy.placement}</div>
        <div><span className="text-gray-500">Animations:</span> {strategy.animations}</div>
        <div><span className="text-gray-500">Background:</span> {strategy.background}</div>
        <div><span className="text-gray-500">Emoji usage:</span> {strategy.emoji_usage}</div>
      </div>
      <p className="text-xs text-gray-600 mt-2">{strategy.necessity}</p>
    </div>
  );
}

function FilmingRequirementsDisplay({ requirements }: { requirements: FilmingRequirements }) {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <h5 className="font-medium text-sm mb-3 flex items-center gap-2">
        <Camera className="h-4 w-4 text-orange-500" />
        Filming Requirements
      </h5>
      {requirements.shots_needed && requirements.shots_needed.length > 0 && (
        <div className="mb-3">
          <span className="text-xs text-gray-500">Shots Needed</span>
          <div className="space-y-2 mt-1">
            {requirements.shots_needed.map((shot, i) => (
              <div key={i} className="border rounded p-2 bg-white">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">{shot.shot_type}</Badge>
                  <span className="text-xs text-gray-500">{shot.duration}</span>
                </div>
                <p className="text-sm mt-1">{shot.description}</p>
                <p className="text-xs text-gray-500">{shot.purpose}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {requirements.b_roll && requirements.b_roll.length > 0 && (
        <div className="mb-2">
          <span className="text-xs text-gray-500">B-Roll</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {requirements.b_roll.map((item, i) => (
              <Badge key={i} variant="secondary" className="text-xs">{item}</Badge>
            ))}
          </div>
        </div>
      )}
      <div className="flex gap-4 text-sm">
        {requirements.talent && <div><span className="text-gray-500">Talent:</span> {requirements.talent}</div>}
        {requirements.props && <div><span className="text-gray-500">Props:</span> {requirements.props}</div>}
      </div>
    </div>
  );
}

function AudioDesignDisplay({ audio }: { audio: AudioDesign }) {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <h5 className="font-medium text-sm mb-3 flex items-center gap-2">
        <Music className="h-4 w-4 text-pink-500" />
        Audio Design
      </h5>
      {audio.music && (
        <div className="mb-3">
          <span className="text-xs text-gray-500">Music</span>
          <div className="grid gap-1 text-sm mt-1 md:grid-cols-2">
            <div><span className="text-gray-500">Style:</span> {audio.music.style}</div>
            <div><span className="text-gray-500">Tempo:</span> {audio.music.tempo}</div>
            <div><span className="text-gray-500">Energy:</span> {audio.music.energy}</div>
            <div><span className="text-gray-500">When:</span> {audio.music.when}</div>
          </div>
          {audio.music.reference && (
            <p className="text-xs text-gray-600 mt-1">Reference: {audio.music.reference}</p>
          )}
        </div>
      )}
      {audio.sound_effects && audio.sound_effects.length > 0 && (
        <div className="mb-3">
          <span className="text-xs text-gray-500">Sound Effects</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {audio.sound_effects.map((effect, i) => (
              <Badge key={i} variant="outline" className="text-xs">{effect}</Badge>
            ))}
          </div>
        </div>
      )}
      {audio.voiceover && (
        <div>
          <span className="text-xs text-gray-500 flex items-center gap-1">
            <Mic className="h-3 w-3" /> Voiceover
          </span>
          <div className="grid gap-1 text-sm mt-1 md:grid-cols-2">
            <div><span className="text-gray-500">Tone:</span> {audio.voiceover.tone}</div>
            <div><span className="text-gray-500">Gender:</span> {audio.voiceover.gender}</div>
            <div><span className="text-gray-500">Pace:</span> {audio.voiceover.pace}</div>
            <div><span className="text-gray-500">Emphasis:</span> {audio.voiceover.emphasis}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function TargetingAlignmentDisplay({ targeting }: { targeting: TargetingAlignment }) {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <h5 className="font-medium text-sm mb-3 flex items-center gap-2">
        <Target className="h-4 w-4 text-red-500" />
        Targeting Alignment
      </h5>
      <div className="space-y-2 text-sm">
        <div>
          <span className="text-gray-500">Audience:</span>
          <p>{targeting.audience}</p>
        </div>
        <div>
          <span className="text-gray-500">Pain point addressed:</span>
          <p>{targeting.pain_point_addressed}</p>
        </div>
        <div>
          <span className="text-gray-500">Brand voice alignment:</span>
          <p>{targeting.brand_voice_alignment}</p>
        </div>
        <div>
          <span className="text-gray-500">Price point justification:</span>
          <p>{targeting.price_point_justification}</p>
        </div>
      </div>
    </div>
  );
}

function SuccessMetricsDisplay({ metrics }: { metrics: SuccessMetrics }) {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <h5 className="font-medium text-sm mb-3 flex items-center gap-2">
        <BarChart3 className="h-4 w-4 text-green-500" />
        Success Metrics
      </h5>
      <div className="space-y-2 text-sm">
        {metrics.primary && (
          <div>
            <span className="text-gray-500">Primary metric:</span>
            <p className="font-medium">{metrics.primary}</p>
          </div>
        )}
        {metrics.secondary && metrics.secondary.length > 0 && (
          <div>
            <span className="text-gray-500">Secondary metrics:</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {metrics.secondary.map((metric, i) => (
                <Badge key={i} variant="outline" className="text-xs">{metric}</Badge>
              ))}
            </div>
          </div>
        )}
        {metrics.optimization && (
          <div>
            <span className="text-gray-500">Optimization:</span>
            <p className="text-xs text-gray-600">{metrics.optimization}</p>
          </div>
        )}
      </div>
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
          <span className="text-left font-medium">{recommendation.concept?.title ?? 'Untitled Recommendation'}</span>
          {recommendation.duration && (
            <Badge variant="outline" className="text-xs ml-2">
              {recommendation.duration}
            </Badge>
          )}
        </div>
      </AccordionTrigger>
      <AccordionContent>
        <div className="space-y-4 pt-4">
          {/* Objective */}
          {recommendation.objective && (
            <div className="flex items-center gap-2 text-sm">
              <Target className="h-4 w-4 text-gray-400" />
              <span className="text-gray-500">Objective:</span>
              <span>{recommendation.objective}</span>
            </div>
          )}

          {/* Description */}
          <p className="text-sm text-gray-600">{recommendation.concept?.description ?? 'No description available'}</p>

          {recommendation.concept?.marketing_framework && (
            <Badge variant="outline">{recommendation.concept.marketing_framework}</Badge>
          )}

          {/* Visual Direction (for both video and image) */}
          {recommendation.visual_direction && (
            <VisualDirectionDisplay direction={recommendation.visual_direction} />
          )}

          {/* Video Ad: Script Breakdown */}
          {recommendation.ad_format === 'video' && recommendation.script_breakdown && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h5 className="font-medium text-sm mb-3 flex items-center gap-2">
                <Film className="h-4 w-4 text-blue-500" />
                Script Breakdown
              </h5>
              <div className="space-y-3">
                {recommendation.script_breakdown.hook && (
                  <ScriptSectionDisplay
                    section={recommendation.script_breakdown.hook}
                    label="HOOK"
                    badgeColor="bg-green-500"
                  />
                )}
                {recommendation.script_breakdown.problem_agitation && (
                  <ScriptSectionDisplay
                    section={recommendation.script_breakdown.problem_agitation}
                    label="PROBLEM"
                    badgeColor="bg-red-400"
                  />
                )}
                {recommendation.script_breakdown.solution_introduction && (
                  <ScriptSectionDisplay
                    section={recommendation.script_breakdown.solution_introduction}
                    label="SOLUTION"
                    badgeColor="bg-blue-500"
                  />
                )}
                {recommendation.script_breakdown.social_proof && (
                  <ScriptSectionDisplay
                    section={recommendation.script_breakdown.social_proof}
                    label="SOCIAL PROOF"
                    badgeColor="bg-yellow-500"
                  />
                )}
                {recommendation.script_breakdown.cta && (
                  <ScriptSectionDisplay
                    section={recommendation.script_breakdown.cta}
                    label="CTA"
                    badgeColor="bg-pink-500"
                  />
                )}
              </div>
            </div>
          )}

          {/* Video Ad: Caption Strategy */}
          {recommendation.ad_format === 'video' && recommendation.caption_strategy && (
            <CaptionStrategyDisplay strategy={recommendation.caption_strategy} />
          )}

          {/* Video Ad: Filming Requirements */}
          {recommendation.ad_format === 'video' && recommendation.filming_requirements && (
            <FilmingRequirementsDisplay requirements={recommendation.filming_requirements} />
          )}

          {/* Video Ad: Audio Design */}
          {recommendation.ad_format === 'video' && recommendation.audio_design && (
            <AudioDesignDisplay audio={recommendation.audio_design} />
          )}

          {/* Image Ad: Copywriting */}
          {recommendation.ad_format === 'image' && recommendation.copywriting && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h5 className="font-medium text-sm mb-3">Copywriting</h5>
              <div className="space-y-3">
                {recommendation.copywriting.headline && (
                  <div className="flex gap-2">
                    <Badge className="bg-blue-500 shrink-0">HEADLINE</Badge>
                    <div>
                      <p className="text-sm font-medium">{recommendation.copywriting.headline.text}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        Placement: {recommendation.copywriting.headline.placement}
                        {recommendation.copywriting.headline.font && ` | ${recommendation.copywriting.headline.font}`}
                      </p>
                    </div>
                  </div>
                )}
                {recommendation.copywriting.subheadline && (
                  <div className="flex gap-2">
                    <Badge className="bg-gray-500 shrink-0">SUBHEAD</Badge>
                    <div>
                      <p className="text-sm">{recommendation.copywriting.subheadline.text}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        Placement: {recommendation.copywriting.subheadline.placement}
                      </p>
                    </div>
                  </div>
                )}
                {recommendation.copywriting.body_copy && (
                  <div className="flex gap-2">
                    <Badge className="bg-gray-400 shrink-0">BODY</Badge>
                    <div>
                      <p className="text-sm">{recommendation.copywriting.body_copy.text}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        Placement: {recommendation.copywriting.body_copy.placement}
                      </p>
                    </div>
                  </div>
                )}
                {recommendation.copywriting.cta_button && (
                  <div className="flex gap-2">
                    <Badge className="bg-pink-500 shrink-0">CTA</Badge>
                    <div>
                      <p className="text-sm font-medium">{recommendation.copywriting.cta_button.text}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        Placement: {recommendation.copywriting.cta_button.placement}
                        {recommendation.copywriting.cta_button.color && ` | Color: ${recommendation.copywriting.cta_button.color}`}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Image Ad: Content Breakdown */}
          {recommendation.ad_format === 'image' && recommendation.content_breakdown && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h5 className="font-medium text-sm mb-3">Content Breakdown</h5>
              <div className="grid grid-cols-2 gap-4">
                {recommendation.content_breakdown.left_side_problem && (
                  <div className="border-r pr-4">
                    <Badge className="bg-red-400 mb-2">PROBLEM</Badge>
                    <p className="text-sm">{recommendation.content_breakdown.left_side_problem.visual}</p>
                    {recommendation.content_breakdown.left_side_problem.text && (
                      <p className="text-xs text-gray-600 mt-1">
                        {recommendation.content_breakdown.left_side_problem.text}
                      </p>
                    )}
                  </div>
                )}
                {recommendation.content_breakdown.right_side_solution && (
                  <div className="pl-4">
                    <Badge className="bg-green-500 mb-2">SOLUTION</Badge>
                    <p className="text-sm">{recommendation.content_breakdown.right_side_solution.visual}</p>
                    {recommendation.content_breakdown.right_side_solution.text && (
                      <p className="text-xs text-gray-600 mt-1">
                        {recommendation.content_breakdown.right_side_solution.text}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Image Ad: Design Specifications */}
          {recommendation.ad_format === 'image' && recommendation.design_specifications && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h5 className="font-medium text-sm mb-3">Design Specifications</h5>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
                {recommendation.design_specifications.dimensions && (
                  <div><span className="text-gray-500">Dimensions:</span> {recommendation.design_specifications.dimensions}</div>
                )}
                {recommendation.design_specifications.file_format && (
                  <div><span className="text-gray-500">Format:</span> {recommendation.design_specifications.file_format}</div>
                )}
                {recommendation.design_specifications.font && (
                  <div><span className="text-gray-500">Font:</span> {recommendation.design_specifications.font}</div>
                )}
                {recommendation.design_specifications.text_coverage && (
                  <div><span className="text-gray-500">Text coverage:</span> {recommendation.design_specifications.text_coverage}</div>
                )}
              </div>
              {recommendation.design_specifications.colors && (
                <div className="mt-3 flex gap-2 items-center">
                  <span className="text-sm text-gray-500">Colors:</span>
                  {Object.entries(recommendation.design_specifications.colors).map(([name, color]) => (
                    <div key={name} className="flex items-center gap-1">
                      <div
                        className="w-4 h-4 rounded border"
                        style={{ backgroundColor: color }}
                        title={`${name}: ${color}`}
                      />
                      <span className="text-xs text-gray-600">{color}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Image Ad: Production Notes */}
          {recommendation.ad_format === 'image' && recommendation.production_notes && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h5 className="font-medium text-sm mb-3">Production Notes</h5>
              <div className="space-y-2 text-sm">
                {recommendation.production_notes.tools && (
                  <div><span className="text-gray-500">Tools:</span> {recommendation.production_notes.tools}</div>
                )}
                {recommendation.production_notes.assets_needed && recommendation.production_notes.assets_needed.length > 0 && (
                  <div>
                    <span className="text-gray-500">Assets needed:</span>
                    <ul className="list-disc list-inside ml-2 mt-1">
                      {recommendation.production_notes.assets_needed.map((asset, i) => (
                        <li key={i} className="text-gray-600">{asset}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {recommendation.production_notes.notes && (
                  <div><span className="text-gray-500">Notes:</span> {recommendation.production_notes.notes}</div>
                )}
              </div>
            </div>
          )}

          {/* Targeting Alignment (common) */}
          {recommendation.targeting_alignment && (
            <TargetingAlignmentDisplay targeting={recommendation.targeting_alignment} />
          )}

          {/* Success Metrics (common) */}
          {recommendation.success_metrics && (
            <SuccessMetricsDisplay metrics={recommendation.success_metrics} />
          )}

          {/* Testing Variants */}
          {recommendation.testing_variants && recommendation.testing_variants.length > 0 && (
            <div>
              <h5 className="font-medium text-sm mb-2">Testing Variants</h5>
              <div className="space-y-2">
                {recommendation.testing_variants.map((variant, i) => (
                  <div key={i} className="border rounded-lg p-3 bg-gray-50">
                    <p className="font-medium text-sm">{variant.variable}</p>
                    <div className="flex gap-4 mt-1 text-xs text-gray-600">
                      <span><strong>A:</strong> {variant.variant_a}</span>
                      <span><strong>B:</strong> {variant.variant_b}</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{variant.hypothesis}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </AccordionContent>
    </AccordionItem>
  );
}
