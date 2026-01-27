'use client';

import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAd, useAnalyzeAd } from '@/hooks/useAds';
import { useCompetitors } from '@/hooks/useCompetitors';
import { useVideoPlayer } from '@/hooks/useVideoPlayer';
import {
  Video,
  ImageIcon,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Lightbulb,
  ArrowLeft,
  Heart,
  MessageCircle,
  Share2,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import type { EnhancedNarrativeBeat } from '@/types/analysis';

const BEAT_COLORS: Record<string, string> = {
  Hook: 'bg-green-500',
  Problem: 'bg-red-400',
  Solution: 'bg-blue-500',
  'Product Showcase': 'bg-purple-500',
  'Social Proof': 'bg-yellow-500',
  'Benefit Stack': 'bg-teal-500',
  'Objection Handling': 'bg-orange-400',
  CTA: 'bg-pink-500',
  Transition: 'bg-gray-400',
  Unknown: 'bg-gray-300',
};

interface PageProps {
  params: { id: string };
}

export default function AdDetailPage({ params }: PageProps) {
  const { id } = params;
  const { data: ad, isLoading, error } = useAd(id);
  const { data: competitorsData } = useCompetitors({ page_size: 100 });
  const analyzeAd = useAnalyzeAd();

  const competitors = competitorsData?.items ?? [];
  const competitor = competitors.find((c) => c.id === ad?.competitor_id);

  const timeline = ad?.video_intelligence?.timeline ?? [];
  const critique = ad?.video_intelligence?.critique;

  const {
    videoRef,
    currentBeat,
    isPlaying,
    currentTime,
    duration,
    playBeat,
    navigateBeat,
    togglePlayPause,
    parseTimestamp,
    formatTimestamp,
    videoEventHandlers,
  } = useVideoPlayer({
    timeline,
    onBeatChange: () => {},
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error || !ad) {
    return (
      <div className="space-y-6">
        <Link href="/ads">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Ads
          </Button>
        </Link>
        <Card>
          <CardContent className="flex flex-col items-center justify-center h-64">
            <AlertCircle className="h-12 w-12 text-red-400 mb-4" />
            <p className="text-gray-500">Ad not found</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const grade = ad.video_intelligence?.critique?.overall_grade;
  const isVideo = ad.creative_type === 'video';

  const handleAnalyze = async () => {
    await analyzeAd.mutateAsync(ad.id);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/ads">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {competitor?.company_name || 'Unknown Competitor'}
            </h1>
            <div className="flex items-center gap-3 mt-1">
              <Badge variant="secondary">
                {ad.creative_type === 'video' ? (
                  <Video className="h-3 w-3 mr-1" />
                ) : (
                  <ImageIcon className="h-3 w-3 mr-1" />
                )}
                {ad.creative_type}
              </Badge>
              {grade && (
                <Badge
                  className={`${
                    grade.startsWith('A')
                      ? 'bg-green-500'
                      : grade.startsWith('B')
                      ? 'bg-blue-500'
                      : grade.startsWith('C')
                      ? 'bg-yellow-500'
                      : 'bg-red-500'
                  } text-white`}
                >
                  Grade: {grade}
                </Badge>
              )}
              {ad.analyzed ? (
                <Badge variant="outline" className="text-green-600 border-green-600">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Analyzed
                </Badge>
              ) : (
                <Badge variant="outline">Pending Analysis</Badge>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {ad.ad_snapshot_url && (
            <a href={ad.ad_snapshot_url} target="_blank" rel="noopener noreferrer">
              <Button variant="outline" size="sm">
                <ExternalLink className="h-4 w-4 mr-2" />
                View in Ad Library
              </Button>
            </a>
          )}
          {!ad.analyzed && (
            <Button onClick={handleAnalyze} disabled={analyzeAd.isPending}>
              {analyzeAd.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Analyze
                </>
              )}
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Media & Stats Column */}
        <div className="lg:col-span-2 space-y-4">
          {/* Media Player */}
          <Card>
            <CardContent className="p-4">
              <div className="aspect-video bg-black rounded-lg overflow-hidden mb-4">
                {ad.creative_url ? (
                  isVideo ? (
                    <video
                      ref={videoRef}
                      src={ad.creative_url}
                      className="w-full h-full object-contain"
                      {...videoEventHandlers}
                    />
                  ) : (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={ad.creative_url}
                      alt="Ad creative"
                      className="w-full h-full object-contain"
                    />
                  )
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-white">
                    {isVideo ? (
                      <Video className="h-16 w-16 opacity-50" />
                    ) : (
                      <ImageIcon className="h-16 w-16 opacity-50" />
                    )}
                  </div>
                )}
              </div>

              {/* Video Timeline with beats */}
              {isVideo && timeline.length > 0 && duration > 0 && (
                <div className="mb-4">
                  <div className="relative h-6 bg-gray-200 rounded overflow-hidden">
                    {timeline.map((beat, index) => {
                      const startPercent = (parseTimestamp(beat.start_time) / duration) * 100;
                      const endPercent = (parseTimestamp(beat.end_time) / duration) * 100;
                      const widthPercent = endPercent - startPercent;

                      return (
                        <button
                          key={index}
                          className={`absolute h-full transition-opacity hover:opacity-100 ${
                            BEAT_COLORS[beat.beat_type] || BEAT_COLORS.Unknown
                          } ${currentBeat === beat ? 'opacity-100' : 'opacity-70'}`}
                          style={{
                            left: `${startPercent}%`,
                            width: `${widthPercent}%`,
                          }}
                          onClick={() => playBeat(beat)}
                          title={`${beat.beat_type}: ${beat.start_time} - ${beat.end_time}`}
                        />
                      );
                    })}
                    <div
                      className="absolute top-0 w-0.5 h-full bg-white shadow-md"
                      style={{ left: `${(currentTime / duration) * 100}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>{formatTimestamp(currentTime)}</span>
                    <span>{formatTimestamp(duration)}</span>
                  </div>
                </div>
              )}

              {/* Video Controls */}
              {isVideo && (
                <div className="flex items-center justify-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => navigateBeat('prev')}>
                    <SkipBack className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" size="icon" onClick={togglePlayPause}>
                    {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => navigateBeat('next')}>
                    <SkipForward className="h-4 w-4" />
                  </Button>
                </div>
              )}

              {/* Current Beat Indicator */}
              {isVideo && currentBeat && (
                <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge className={BEAT_COLORS[currentBeat.beat_type]}>{currentBeat.beat_type}</Badge>
                    <span className="text-sm text-gray-500">
                      {currentBeat.start_time} - {currentBeat.end_time}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700">
                    {currentBeat.audio_transcript || currentBeat.visual_description}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Engagement Stats */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Engagement</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <Heart className="h-5 w-5 mx-auto mb-2 text-red-500" />
                  <p className="text-2xl font-bold">{ad.likes.toLocaleString()}</p>
                  <p className="text-sm text-gray-500">Likes</p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <MessageCircle className="h-5 w-5 mx-auto mb-2 text-blue-500" />
                  <p className="text-2xl font-bold">{ad.comments.toLocaleString()}</p>
                  <p className="text-sm text-gray-500">Comments</p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <Share2 className="h-5 w-5 mx-auto mb-2 text-green-500" />
                  <p className="text-2xl font-bold">{ad.shares.toLocaleString()}</p>
                  <p className="text-sm text-gray-500">Shares</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Ad Copy */}
          {(ad.ad_copy || ad.ad_headline) && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Ad Copy</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {ad.ad_headline && (
                  <div>
                    <p className="text-sm font-medium text-gray-500">Headline</p>
                    <p className="font-medium">{ad.ad_headline}</p>
                  </div>
                )}
                {ad.ad_copy && (
                  <div>
                    <p className="text-sm font-medium text-gray-500">Primary Text</p>
                    <p className="whitespace-pre-wrap">{ad.ad_copy}</p>
                  </div>
                )}
                {ad.cta_text && (
                  <div>
                    <p className="text-sm font-medium text-gray-500">CTA</p>
                    <Badge>{ad.cta_text}</Badge>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Analysis Column */}
        <div className="space-y-4">
          {/* Ad Info */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {ad.publication_date && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Published</span>
                  <span>
                    {formatDistanceToNow(new Date(ad.publication_date), { addSuffix: true })}
                  </span>
                </div>
              )}
              {ad.platforms && ad.platforms.length > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Platforms</span>
                  <span>{ad.platforms.join(', ')}</span>
                </div>
              )}
              {ad.total_active_time && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Active Time</span>
                  <span>{ad.total_active_time}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-gray-500">Total Engagement</span>
                <span className="font-medium">{ad.total_engagement.toLocaleString()}</span>
              </div>
            </CardContent>
          </Card>

          {/* Video Analysis Tabs */}
          {ad.analyzed && ad.video_intelligence && (
            <Tabs defaultValue="critique" className="w-full">
              <TabsList className="w-full">
                <TabsTrigger value="critique" className="flex-1">
                  Critique
                </TabsTrigger>
                {isVideo && (
                  <TabsTrigger value="beats" className="flex-1">
                    Beats
                  </TabsTrigger>
                )}
              </TabsList>

              <TabsContent value="critique" className="mt-4 space-y-4">
                {critique ? (
                  <>
                    {/* Grade */}
                    <Card>
                      <CardContent className="pt-6">
                        <div className="flex items-center gap-4">
                          <div
                            className={`text-4xl font-bold ${
                              critique.overall_grade.startsWith('A')
                                ? 'text-green-600'
                                : critique.overall_grade.startsWith('B')
                                ? 'text-blue-600'
                                : critique.overall_grade.startsWith('C')
                                ? 'text-yellow-600'
                                : 'text-red-600'
                            }`}
                          >
                            {critique.overall_grade}
                          </div>
                          <div className="flex-1">
                            <p className="font-medium">Overall Grade</p>
                            <p className="text-sm text-gray-500 line-clamp-3">
                              {critique.overall_assessment}
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* Strengths */}
                    {critique.strengths.length > 0 && (
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-base flex items-center gap-2">
                            <CheckCircle2 className="h-5 w-5 text-green-500" />
                            Strengths
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <ul className="space-y-3">
                            {critique.strengths.map((s, i) => (
                              <li key={i} className="flex gap-2">
                                <span className="text-green-500 mt-1">+</span>
                                <div>
                                  <p className="font-medium text-sm">{s.strength}</p>
                                  <p className="text-xs text-gray-500">{s.evidence}</p>
                                </div>
                              </li>
                            ))}
                          </ul>
                        </CardContent>
                      </Card>
                    )}

                    {/* Weaknesses */}
                    {critique.weaknesses.length > 0 && (
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-base flex items-center gap-2">
                            <AlertCircle className="h-5 w-5 text-yellow-500" />
                            Weaknesses
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <ul className="space-y-3">
                            {critique.weaknesses.map((w, i) => (
                              <li key={i} className="flex gap-2">
                                <span className="text-yellow-500 mt-1">!</span>
                                <div>
                                  <p className="font-medium text-sm">{w.weakness}</p>
                                  <p className="text-xs text-gray-500">{w.evidence}</p>
                                  {w.suggested_fix && (
                                    <p className="text-xs text-blue-600 mt-1">
                                      Fix: {w.suggested_fix}
                                    </p>
                                  )}
                                </div>
                              </li>
                            ))}
                          </ul>
                        </CardContent>
                      </Card>
                    )}

                    {/* Quick Wins */}
                    {critique.quick_wins.length > 0 && (
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-base flex items-center gap-2">
                            <Lightbulb className="h-5 w-5 text-yellow-400" />
                            Quick Wins
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <ul className="space-y-2">
                            {critique.quick_wins.map((win, i) => (
                              <li key={i} className="flex gap-2 text-sm">
                                <span className="text-yellow-400">*</span>
                                {win}
                              </li>
                            ))}
                          </ul>
                        </CardContent>
                      </Card>
                    )}
                  </>
                ) : (
                  <Card>
                    <CardContent className="text-center py-8">
                      <p className="text-gray-500">No critique available</p>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              {isVideo && (
                <TabsContent value="beats" className="mt-4">
                  <Card>
                    <CardContent className="p-0">
                      <ScrollArea className="h-[400px]">
                        <div className="divide-y">
                          {timeline.map((beat, index) => (
                            <BeatCard
                              key={index}
                              beat={beat}
                              isActive={currentBeat === beat}
                              onClick={() => playBeat(beat)}
                            />
                          ))}
                        </div>
                      </ScrollArea>
                    </CardContent>
                  </Card>
                </TabsContent>
              )}
            </Tabs>
          )}

          {/* Not Analyzed Message */}
          {!ad.analyzed && (
            <Card>
              <CardContent className="text-center py-8">
                <Sparkles className="h-10 w-10 mx-auto text-gray-300 mb-2" />
                <p className="text-gray-500">This ad hasn&apos;t been analyzed yet</p>
                <Button onClick={handleAnalyze} disabled={analyzeAd.isPending} className="mt-4">
                  {analyzeAd.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4 mr-2" />
                      Analyze Now
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function BeatCard({
  beat,
  isActive,
  onClick,
}: {
  beat: EnhancedNarrativeBeat;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={`w-full text-left p-4 hover:bg-gray-50 transition-colors ${
        isActive ? 'bg-blue-50 border-l-4 border-blue-500' : ''
      }`}
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        <Badge className={`${BEAT_COLORS[beat.beat_type]} text-white text-xs shrink-0`}>
          {beat.beat_type}
        </Badge>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-gray-500">
              {beat.start_time} - {beat.end_time}
            </span>
            {beat.attention_score && (
              <span className="text-xs text-gray-400">Attention: {beat.attention_score}/10</span>
            )}
          </div>
          <p className="text-sm text-gray-700 line-clamp-2">
            {beat.audio_transcript || beat.visual_description}
          </p>
          {beat.emotion && (
            <Badge variant="outline" className="mt-2 text-xs">
              {beat.emotion} {beat.emotion_intensity && `(${beat.emotion_intensity}/10)`}
            </Badge>
          )}
        </div>
      </div>
    </button>
  );
}
