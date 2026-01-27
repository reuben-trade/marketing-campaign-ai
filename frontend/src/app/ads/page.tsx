'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Slider } from '@/components/ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useAds, useAdStats, useAnalyzeAds, useRetrieveAds } from '@/hooks/useAds';
import { useCompetitors } from '@/hooks/useCompetitors';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { useFilterStore } from '@/stores/filterStore';
import { searchApi } from '@/lib/api/search';
import {
  ImageIcon,
  Video,
  Filter,
  X,
  Heart,
  MessageCircle,
  Share2,
  Loader2,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Download,
  Building2,
  Search,
} from 'lucide-react';
import type { Ad } from '@/types/ad';
import { formatDistanceToNow } from 'date-fns';

export default function AdsPage() {
  return (
    <Suspense fallback={<AdsPageLoading />}>
      <AdsPageContent />
    </Suspense>
  );
}

function AdsPageLoading() {
  return (
    <div className="flex items-center justify-center h-64">
      <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
    </div>
  );
}

function AdsPageContent() {
  const searchParams = useSearchParams();
  const initialCompetitorId = searchParams.get('competitor_id');

  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchMode, setIsSearchMode] = useState(false);
  const [searchResults, setSearchResults] = useState<Ad[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Retrieval section state
  const [retrieveCompetitorIds, setRetrieveCompetitorIds] = useState<string[]>([]);
  const [retrieveCount, setRetrieveCount] = useState(10);

  const {
    selectedCompetitorIds,
    creativeType,
    analyzedOnly,
    minEngagement,
    minOverallScore,
    minCompositeScore,
    setSelectedCompetitors,
    toggleCompetitor,
    setCreativeType,
    setAnalyzedOnly,
    setMinEngagement,
    setMinOverallScore,
    setMinCompositeScore,
    clearFilters,
  } = useFilterStore();

  // Set initial competitor from URL
  useEffect(() => {
    if (initialCompetitorId) {
      setSelectedCompetitors([initialCompetitorId]);
    }
  }, [initialCompetitorId, setSelectedCompetitors]);

  const { data: competitorsData } = useCompetitors({ page_size: 100 });
  const competitors = competitorsData?.items ?? [];

  const filters = {
    page,
    page_size: pageSize,
    competitor_id: selectedCompetitorIds.length === 1 ? selectedCompetitorIds[0] : undefined,
    creative_type: creativeType !== 'all' ? creativeType : undefined,
    analyzed: analyzedOnly ?? undefined,
    min_engagement: minEngagement > 0 ? minEngagement : undefined,
    min_overall_score: minOverallScore > 0 ? minOverallScore : undefined,
    min_composite_score: minCompositeScore > 0 ? minCompositeScore / 10 : undefined, // Convert 0-10 to 0-1
  };

  const { data: adsData, isLoading } = useAds(filters);
  const { data: stats } = useAdStats();
  const analyzeAds = useAnalyzeAds();
  const retrieveAds = useRetrieveAds();

  // Use search results if in search mode, otherwise use filtered ads
  const ads = isSearchMode ? searchResults : (adsData?.items ?? []);
  const totalAds = isSearchMode ? searchResults.length : (adsData?.total ?? 0);
  const totalPages = Math.ceil(totalAds / pageSize);

  const hasActiveFilters =
    selectedCompetitorIds.length > 0 ||
    creativeType !== 'all' ||
    analyzedOnly !== null ||
    minEngagement > 0 ||
    minOverallScore > 0 ||
    minCompositeScore > 0;

  const onAnalyze = async () => {
    await analyzeAds.mutateAsync(10);
  };

  const toggleRetrieveCompetitor = (competitorId: string) => {
    setRetrieveCompetitorIds((prev) =>
      prev.includes(competitorId)
        ? prev.filter((id) => id !== competitorId)
        : [...prev, competitorId]
    );
  };

  const selectAllCompetitors = () => {
    setRetrieveCompetitorIds(competitors.map((c) => c.id));
  };

  const clearRetrieveSelection = () => {
    setRetrieveCompetitorIds([]);
  };

  const onRetrieveAds = async () => {
    if (retrieveCompetitorIds.length === 0) {
      toast.error('Please select at least one competitor');
      return;
    }

    try {
      let totalRetrieved = 0;
      let totalSkipped = 0;
      let totalFailed = 0;

      // Process each competitor
      for (const competitorId of retrieveCompetitorIds) {
        const result = await retrieveAds.mutateAsync({
          competitor_id: competitorId,
          max_ads: retrieveCount,
        });
        totalRetrieved += result.retrieved;
        totalSkipped += result.skipped;
        totalFailed += result.failed;
      }

      toast.success(
        `Retrieved ${totalRetrieved} ads from ${retrieveCompetitorIds.length} competitor(s). ${totalSkipped} skipped, ${totalFailed} failed.`
      );
    } catch {
      toast.error('Failed to retrieve ads. Please try again.');
    }
  };

  const onSearch = async () => {
    if (!searchQuery.trim()) {
      toast.error('Please enter a search query');
      return;
    }

    setIsSearching(true);
    try {
      const data = await searchApi.semanticSearch({
        query: searchQuery,
        limit: 100,
        filters: {
          analyzed: true,
        },
      });

      setSearchResults(data.items);
      setIsSearchMode(true);
      toast.success(`Found ${data.items.length} relevant ads`);
    } catch (error) {
      toast.error('Search failed. Please try again.');
      console.error('Search error:', error);
    } finally {
      setIsSearching(false);
    }
  };

  const clearSearch = () => {
    setSearchQuery('');
    setIsSearchMode(false);
    setSearchResults([]);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Ads Browser</h1>
          <p className="text-gray-500 mt-1">
            {totalAds} ads {stats?.analyzed_ads ? `(${stats.analyzed_ads} analyzed)` : ''}
          </p>
        </div>
        <Button onClick={onAnalyze} disabled={analyzeAds.isPending}>
          {analyzeAds.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Sparkles className="mr-2 h-4 w-4" />
              Analyze Ads
            </>
          )}
        </Button>
      </div>

      {/* Semantic Search */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Search className="h-4 w-4" />
            Semantic Search
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="Search for ads by topic, theme, or concept (e.g., 'eco-friendly products', 'testimonials', 'problem-solution')"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !isSearching) {
                  onSearch();
                }
              }}
              className="flex-1"
            />
            {isSearchMode ? (
              <Button variant="outline" onClick={clearSearch}>
                <X className="mr-2 h-4 w-4" />
                Clear Search
              </Button>
            ) : (
              <Button onClick={onSearch} disabled={isSearching || !searchQuery.trim()}>
                {isSearching ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    <Search className="mr-2 h-4 w-4" />
                    Search
                  </>
                )}
              </Button>
            )}
          </div>
          {isSearchMode && (
            <div className="mt-2">
              <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                Showing {searchResults.length} search results for &quot;{searchQuery}&quot;
              </Badge>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Ad Retrieval Section */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Download className="h-4 w-4" />
            Retrieve Ads from Facebook Ad Library
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex flex-wrap gap-4 items-end">
              {/* Competitor Selection */}
              <div className="min-w-[250px] flex-1">
                <Label className="text-sm font-medium mb-2 block">Select Competitors</Label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button variant="outline" className="w-full justify-start">
                      <Building2 className="h-4 w-4 mr-2" />
                      {retrieveCompetitorIds.length === 0
                        ? 'Select competitors...'
                        : retrieveCompetitorIds.length === competitors.length
                        ? 'All competitors'
                        : `${retrieveCompetitorIds.length} competitor(s) selected`}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-72 p-0" align="start">
                    <div className="p-2 border-b flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="flex-1"
                        onClick={selectAllCompetitors}
                      >
                        Select All
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="flex-1"
                        onClick={clearRetrieveSelection}
                      >
                        Clear
                      </Button>
                    </div>
                    <ScrollArea className="h-64">
                      <div className="p-2 space-y-1">
                        {competitors.map((competitor) => (
                          <label
                            key={competitor.id}
                            className="flex items-center gap-2 p-2 rounded hover:bg-gray-100 cursor-pointer"
                          >
                            <Checkbox
                              checked={retrieveCompetitorIds.includes(competitor.id)}
                              onCheckedChange={() => toggleRetrieveCompetitor(competitor.id)}
                            />
                            <span className="text-sm truncate">{competitor.company_name}</span>
                            {competitor.ad_count !== undefined && (
                              <Badge variant="secondary" className="ml-auto text-xs">
                                {competitor.ad_count} ads
                              </Badge>
                            )}
                          </label>
                        ))}
                        {competitors.length === 0 && (
                          <p className="text-sm text-gray-500 text-center py-4">
                            No competitors found. Add competitors first.
                          </p>
                        )}
                      </div>
                    </ScrollArea>
                  </PopoverContent>
                </Popover>
              </div>

              {/* Ad Count Input */}
              <div className="w-[180px]">
                <Label htmlFor="retrieve-count" className="text-sm font-medium mb-2 block">
                  Number of Ads
                </Label>
                <Input
                  id="retrieve-count"
                  type="number"
                  min={1}
                  max={100}
                  value={retrieveCount}
                  onChange={(e) => setRetrieveCount(Math.max(1, Math.min(100, parseInt(e.target.value) || 1)))}
                  className="w-full"
                />
              </div>

              {/* Retrieve Button */}
              <Button
                onClick={onRetrieveAds}
                disabled={retrieveAds.isPending || retrieveCompetitorIds.length === 0}
                className="min-w-[140px]"
              >
                {retrieveAds.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Retrieving...
                  </>
                ) : (
                  <>
                    <Download className="mr-2 h-4 w-4" />
                    Retrieve Ads
                  </>
                )}
              </Button>
            </div>

            {/* Selected competitors preview */}
            {retrieveCompetitorIds.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {retrieveCompetitorIds.slice(0, 5).map((id) => {
                  const competitor = competitors.find((c) => c.id === id);
                  return competitor ? (
                    <Badge key={id} variant="secondary" className="flex items-center gap-1">
                      {competitor.company_name}
                      <button
                        onClick={() => toggleRetrieveCompetitor(id)}
                        className="ml-1 hover:bg-gray-300 rounded-full p-0.5"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ) : null;
                })}
                {retrieveCompetitorIds.length > 5 && (
                  <Badge variant="outline">+{retrieveCompetitorIds.length - 5} more</Badge>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Filter className="h-4 w-4" />
              Filters
            </CardTitle>
            {hasActiveFilters && (
              <Button variant="ghost" size="sm" onClick={clearFilters}>
                <X className="h-4 w-4 mr-1" />
                Clear All
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            {/* Competitor Filter */}
            <div className="min-w-[200px]">
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" className="w-full justify-start">
                    Competitors
                    {selectedCompetitorIds.length > 0 && (
                      <Badge variant="secondary" className="ml-2">
                        {selectedCompetitorIds.length}
                      </Badge>
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-64 p-0" align="start">
                  <ScrollArea className="h-64">
                    <div className="p-2 space-y-1">
                      {competitors.map((competitor) => (
                        <label
                          key={competitor.id}
                          className="flex items-center gap-2 p-2 rounded hover:bg-gray-100 cursor-pointer"
                        >
                          <Checkbox
                            checked={selectedCompetitorIds.includes(competitor.id)}
                            onCheckedChange={() => toggleCompetitor(competitor.id)}
                          />
                          <span className="text-sm truncate">{competitor.company_name}</span>
                        </label>
                      ))}
                    </div>
                  </ScrollArea>
                </PopoverContent>
              </Popover>
            </div>

            {/* Media Type Filter */}
            <div className="flex rounded-lg border overflow-hidden">
              <button
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  creativeType === 'all'
                    ? 'bg-gray-900 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
                onClick={() => setCreativeType('all')}
              >
                All
              </button>
              <button
                className={`px-4 py-2 text-sm font-medium transition-colors flex items-center gap-1 border-l ${
                  creativeType === 'image'
                    ? 'bg-gray-900 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
                onClick={() => setCreativeType('image')}
              >
                <ImageIcon className="h-4 w-4" />
                Image
              </button>
              <button
                className={`px-4 py-2 text-sm font-medium transition-colors flex items-center gap-1 border-l ${
                  creativeType === 'video'
                    ? 'bg-gray-900 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
                onClick={() => setCreativeType('video')}
              >
                <Video className="h-4 w-4" />
                Video
              </button>
            </div>

            {/* Analysis Status Filter */}
            <Select
              value={analyzedOnly === null ? 'all' : analyzedOnly ? 'analyzed' : 'pending'}
              onValueChange={(value) => {
                if (value === 'all') setAnalyzedOnly(null);
                else if (value === 'analyzed') setAnalyzedOnly(true);
                else setAnalyzedOnly(false);
              }}
            >
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Analysis status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="analyzed">Analyzed</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>

            {/* Engagement Filter */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Min Engagement:</span>
              <Slider
                value={[minEngagement]}
                onValueChange={([value]) => setMinEngagement(value)}
                max={1000}
                step={10}
                className="w-32"
              />
              <span className="text-sm font-medium w-12">{minEngagement}</span>
            </div>

            {/* Overall Score Filter */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Min Overall Score:</span>
              <Slider
                value={[minOverallScore]}
                onValueChange={([value]) => setMinOverallScore(value)}
                max={10}
                step={0.5}
                className="w-32"
              />
              <span className="text-sm font-medium w-12">{minOverallScore.toFixed(1)}</span>
            </div>

            {/* Composite Score Filter */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Min Composite Score:</span>
              <Slider
                value={[minCompositeScore]}
                onValueChange={([value]) => setMinCompositeScore(value)}
                max={10}
                step={0.5}
                className="w-32"
              />
              <span className="text-sm font-medium w-12">{minCompositeScore.toFixed(1)}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Ads Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : ads.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <p className="text-gray-500">No ads found matching your filters</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {ads.map((ad) => (
              <AdCard
                key={ad.id}
                ad={ad}
                competitors={competitors}
                showSimilarity={isSearchMode}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm text-gray-500">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function AdCard({
  ad,
  competitors,
  showSimilarity = false,
}: {
  ad: Ad & { similarity_score?: number };
  competitors: Array<{ id: string; company_name: string }>;
  showSimilarity?: boolean;
}) {
  const competitor = competitors.find((c) => c.id === ad.competitor_id);
  const gradeValue = ad.video_intelligence?.critique?.overall_grade || (ad.analysis?.grade as string | undefined);
  const grade = typeof gradeValue === 'string' ? gradeValue : undefined;

  // Helper to format scores for display
  const formatScore = (score: number | undefined, scale: number = 10): string | null => {
    if (score === undefined || score === null) return null;
    return (score * scale).toFixed(1);
  };

  const overallScoreDisplay = ad.overall_score ? ad.overall_score.toFixed(1) : null;
  const compositeScoreDisplay = formatScore(ad.composite_score, 10);
  const similarityDisplay = ad.similarity_score ? (ad.similarity_score * 100).toFixed(0) : null;

  return (
    <Link href={`/ads/${ad.id}`}>
      <Card className="overflow-hidden hover:shadow-lg transition-shadow cursor-pointer h-full">
        <div className="aspect-square relative bg-gray-100">
          {ad.creative_url ? (
            ad.creative_type === 'video' ? (
              <video
                src={ad.creative_url}
                className="w-full h-full object-cover"
                muted
                playsInline
              />
            ) : (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={ad.creative_url}
                alt="Ad creative"
                className="w-full h-full object-cover"
              />
            )
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-400">
              {ad.creative_type === 'video' ? (
                <Video className="h-12 w-12" />
              ) : (
                <ImageIcon className="h-12 w-12" />
              )}
            </div>
          )}

          {/* Media type badge */}
          <Badge
            variant="secondary"
            className="absolute top-2 left-2 bg-black/70 text-white border-0"
          >
            {ad.creative_type === 'video' ? (
              <Video className="h-3 w-3" />
            ) : (
              <ImageIcon className="h-3 w-3" />
            )}
          </Badge>

          {/* Grade badge */}
          {grade && (
            <Badge
              className={`absolute top-2 right-2 ${
                grade.startsWith('A')
                  ? 'bg-green-500'
                  : grade.startsWith('B')
                  ? 'bg-blue-500'
                  : grade.startsWith('C')
                  ? 'bg-yellow-500'
                  : 'bg-red-500'
              } text-white border-0`}
            >
              {grade}
            </Badge>
          )}

          {/* Rating badges at bottom */}
          <div className="absolute bottom-2 left-2 right-2 flex gap-1 flex-wrap">
            {showSimilarity && similarityDisplay && (
              <Badge
                variant="secondary"
                className="bg-green-500 text-white border-0 text-xs"
                title="Relevance to Search Query"
              >
                {similarityDisplay}% Match
              </Badge>
            )}
            {overallScoreDisplay && (
              <Badge
                variant="secondary"
                className="bg-purple-500 text-white border-0 text-xs"
                title="Overall Marketing Score"
              >
                Overall: {overallScoreDisplay}/10
              </Badge>
            )}
            {compositeScoreDisplay && (
              <Badge
                variant="secondary"
                className="bg-blue-500 text-white border-0 text-xs"
                title="Composite Score (AI Quality + Survivorship + Engagement)"
              >
                Score: {compositeScoreDisplay}/10
              </Badge>
            )}
          </div>
        </div>

        <CardContent className="p-3">
          <div className="flex items-center gap-3 text-sm text-gray-500 mb-2">
            <span className="flex items-center gap-1">
              <Heart className="h-3 w-3" />
              {ad.likes}
            </span>
            <span className="flex items-center gap-1">
              <MessageCircle className="h-3 w-3" />
              {ad.comments}
            </span>
            <span className="flex items-center gap-1">
              <Share2 className="h-3 w-3" />
              {ad.shares}
            </span>
          </div>

          <p className="text-sm font-medium truncate">{competitor?.company_name || 'Unknown'}</p>

          {ad.publication_date && (
            <p className="text-xs text-gray-400 mt-1">
              {formatDistanceToNow(new Date(ad.publication_date), { addSuffix: true })}
            </p>
          )}

          {!ad.analyzed && (
            <Badge variant="outline" className="mt-2 text-xs">
              Pending analysis
            </Badge>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
