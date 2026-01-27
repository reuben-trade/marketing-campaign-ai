'use client';

import { useState, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAds, useAd } from '@/hooks/useAds';
import { useCompetitors } from '@/hooks/useCompetitors';
import { useVideoPlayer } from '@/hooks/useVideoPlayer';
import {
  Video,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Lightbulb,
} from 'lucide-react';
import type { Ad } from '@/types/ad';
import type { EnhancedNarrativeBeat, BeatType, StrengthItem, WeaknessItem } from '@/types/analysis';

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

const BEAT_TYPES: BeatType[] = [
  'Hook',
  'Problem',
  'Solution',
  'Product Showcase',
  'Social Proof',
  'Benefit Stack',
  'Objection Handling',
  'CTA',
  'Transition',
];

export default function AnalysisPage() {
  const [selectedAdId, setSelectedAdId] = useState<string | null>(null);
  const [selectedCompetitorId, setSelectedCompetitorId] = useState<string>('all');
  const [beatTypeFilter, setBeatTypeFilter] = useState<string>('all');

  const { data: competitorsData } = useCompetitors({ page_size: 100 });
  const competitors = competitorsData?.items ?? [];

  const { data: adsData, isLoading: adsLoading } = useAds({
    page_size: 100,
    analyzed: true,
    creative_type: 'video',
    competitor_id: selectedCompetitorId !== 'all' ? selectedCompetitorId : undefined,
  });

  const analyzedVideos = adsData?.items ?? [];

  const { data: selectedAd, isLoading: adLoading } = useAd(selectedAdId || '');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Video Analysis</h1>
        <p className="text-gray-500 mt-1">
          Deep dive into video ad content with beat-by-beat breakdown
        </p>
      </div>

      <div className="flex flex-wrap gap-4">
        <Select value={selectedCompetitorId} onValueChange={setSelectedCompetitorId}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="All Competitors" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Competitors</SelectItem>
            {competitors.map((c) => (
              <SelectItem key={c.id} value={c.id}>
                {c.company_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={beatTypeFilter} onValueChange={setBeatTypeFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All Beat Types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Beat Types</SelectItem>
            {BEAT_TYPES.map((type) => (
              <SelectItem key={type} value={type}>
                {type}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Video List */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">Analyzed Videos</CardTitle>
            <CardDescription>{analyzedVideos.length} videos available</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[600px]">
              {adsLoading ? (
                <div className="flex items-center justify-center h-32">
                  <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                </div>
              ) : analyzedVideos.length === 0 ? (
                <div className="text-center py-8 px-4">
                  <Video className="h-10 w-10 mx-auto text-gray-300 mb-2" />
                  <p className="text-sm text-gray-500">No analyzed videos found</p>
                </div>
              ) : (
                <div className="divide-y">
                  {analyzedVideos.map((ad) => (
                    <VideoListItem
                      key={ad.id}
                      ad={ad}
                      isSelected={selectedAdId === ad.id}
                      onClick={() => setSelectedAdId(ad.id)}
                      competitors={competitors}
                    />
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Video Player & Analysis */}
        <div className="lg:col-span-2 space-y-4">
          {selectedAdId && selectedAd ? (
            <VideoAnalysisPanel
              ad={selectedAd}
              isLoading={adLoading}
              beatTypeFilter={beatTypeFilter}
            />
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center h-[600px]">
                <Video className="h-16 w-16 text-gray-300 mb-4" />
                <p className="text-gray-500">Select a video to view analysis</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function VideoListItem({
  ad,
  isSelected,
  onClick,
  competitors,
}: {
  ad: Ad;
  isSelected: boolean;
  onClick: () => void;
  competitors: Array<{ id: string; company_name: string }>;
}) {
  const competitor = competitors.find((c) => c.id === ad.competitor_id);
  const grade = ad.video_intelligence?.critique?.overall_grade;
  const beatCount = ad.video_intelligence?.timeline?.length ?? 0;

  return (
    <button
      className={`w-full text-left p-4 hover:bg-gray-50 transition-colors ${
        isSelected ? 'bg-blue-50 border-l-4 border-blue-500' : ''
      }`}
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        <div className="w-16 h-16 bg-gray-100 rounded overflow-hidden flex-shrink-0">
          {ad.creative_url ? (
            <video src={ad.creative_url} className="w-full h-full object-cover" muted />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <Video className="h-6 w-6 text-gray-400" />
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm truncate">{competitor?.company_name || 'Unknown'}</p>
          <div className="flex items-center gap-2 mt-1">
            {grade && (
              <Badge
                variant="secondary"
                className={`text-xs ${
                  grade.startsWith('A')
                    ? 'bg-green-100 text-green-800'
                    : grade.startsWith('B')
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                {grade}
              </Badge>
            )}
            <span className="text-xs text-gray-500">{beatCount} beats</span>
          </div>
        </div>
      </div>
    </button>
  );
}

function VideoAnalysisPanel({
  ad,
  isLoading,
  beatTypeFilter,
}: {
  ad: Ad;
  isLoading: boolean;
  beatTypeFilter: string;
}) {
  const timeline = ad.video_intelligence?.timeline ?? [];
  const critique = ad.video_intelligence?.critique;

  const filteredTimeline =
    beatTypeFilter === 'all' ? timeline : timeline.filter((b) => b.beat_type === beatTypeFilter);

  const handleBeatChange = useCallback(() => {
    // Beat change handler for video player
  }, []);

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
    onBeatChange: handleBeatChange,
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-[600px]">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Video Player */}
      <Card>
        <CardContent className="p-4">
          <div className="aspect-video bg-black rounded-lg overflow-hidden mb-4">
            {ad.creative_url ? (
              <video
                ref={videoRef}
                src={ad.creative_url}
                className="w-full h-full object-contain"
                {...videoEventHandlers}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-white">
                <Video className="h-16 w-16 opacity-50" />
              </div>
            )}
          </div>

          {/* Timeline with beats */}
          {timeline.length > 0 && duration > 0 && (
            <div className="mb-4">
              <div className="relative h-6 bg-gray-200 rounded overflow-hidden">
                {timeline.map((beat: EnhancedNarrativeBeat, index: number) => {
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
                {/* Playhead */}
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

          {/* Controls */}
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

          {/* Current Beat Indicator */}
          {currentBeat && (
            <div className="mt-4 p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Badge className={BEAT_COLORS[currentBeat.beat_type]}>{currentBeat.beat_type}</Badge>
                <span className="text-sm text-gray-500">
                  {currentBeat.start_time} - {currentBeat.end_time}
                </span>
              </div>
              <p className="text-sm text-gray-700">{currentBeat.audio_transcript || currentBeat.visual_description}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Analysis Tabs */}
      <Tabs defaultValue="beats" className="w-full">
        <TabsList>
          <TabsTrigger value="beats">Timeline Beats</TabsTrigger>
          <TabsTrigger value="critique">Critique</TabsTrigger>
        </TabsList>

        <TabsContent value="beats" className="mt-4">
          <Card>
            <CardContent className="p-0">
              <ScrollArea className="h-[300px]">
                <div className="divide-y">
                  {filteredTimeline.map((beat: EnhancedNarrativeBeat, index: number) => (
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

        <TabsContent value="critique" className="mt-4">
          {critique ? (
            <div className="space-y-4">
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
                    <div>
                      <p className="font-medium">Overall Grade</p>
                      <p className="text-sm text-gray-500 line-clamp-2">
                        {critique.overall_assessment}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Strengths */}
              {critique.strengths.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <CheckCircle2 className="h-5 w-5 text-green-500" />
                      Strengths
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <ul className="space-y-3">
                      {critique.strengths.map((s: StrengthItem, i: number) => (
                        <li key={i} className="flex gap-2">
                          <span className="text-green-500 mt-1">+</span>
                          <div>
                            <p className="font-medium text-sm">{s.strength}</p>
                            <p className="text-xs text-gray-500">{s.evidence}</p>
                            {s.timestamp && (
                              <Badge variant="outline" className="mt-1 text-xs">
                                {s.timestamp}
                              </Badge>
                            )}
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
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <AlertCircle className="h-5 w-5 text-yellow-500" />
                      Weaknesses
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <ul className="space-y-3">
                      {critique.weaknesses.map((w: WeaknessItem, i: number) => (
                        <li key={i} className="flex gap-2">
                          <span className="text-yellow-500 mt-1">!</span>
                          <div>
                            <p className="font-medium text-sm">{w.weakness}</p>
                            <p className="text-xs text-gray-500">{w.evidence}</p>
                            {w.suggested_fix && (
                              <p className="text-xs text-blue-600 mt-1">Fix: {w.suggested_fix}</p>
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
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Lightbulb className="h-5 w-5 text-yellow-400" />
                      Quick Wins
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <ul className="space-y-2">
                      {critique.quick_wins.map((win: string, i: number) => (
                        <li key={i} className="flex gap-2 text-sm">
                          <span className="text-yellow-400">*</span>
                          {win}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <Card>
              <CardContent className="text-center py-8">
                <p className="text-gray-500">No critique available for this ad</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
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
