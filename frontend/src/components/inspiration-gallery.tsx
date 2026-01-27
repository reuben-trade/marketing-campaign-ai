'use client';

import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useAds } from '@/hooks/useAds';
import {
  Search,
  Loader2,
  Video,
  Image as ImageIcon,
  TrendingUp,
  Clock,
  AlertCircle,
  CheckCircle2,
  Film,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import type { Ad } from '@/types/ad';

interface InspirationGalleryProps {
  selectedAdIds: string[];
  onSelectionChange: (adIds: string[]) => void;
  maxSelections?: number;
}

export function InspirationGallery({
  selectedAdIds,
  onSelectionChange,
  maxSelections = 3,
}: InspirationGalleryProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [creativeType, setCreativeType] = useState<'all' | 'video' | 'image'>('video');
  const [sortBy, setSortBy] = useState<'score' | 'engagement' | 'date'>('score');

  // Fetch analyzed video ads with high scores
  const { data, isLoading, error } = useAds({
    analyzed: true,
    creative_type: creativeType === 'all' ? undefined : creativeType,
    min_composite_score: 0.3, // Only show ads with reasonable scores
    page_size: 50,
  });

  // Filter and sort ads
  const filteredAds = useMemo(() => {
    const ads = data?.items || [];
    let result = ads;

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (ad) =>
          ad.ad_copy?.toLowerCase().includes(query) ||
          ad.ad_headline?.toLowerCase().includes(query) ||
          ad.ad_summary?.toLowerCase().includes(query)
      );
    }

    // Sort
    result = [...result].sort((a, b) => {
      switch (sortBy) {
        case 'score':
          return (b.composite_score || 0) - (a.composite_score || 0);
        case 'engagement':
          return b.total_engagement - a.total_engagement;
        case 'date':
          return (
            new Date(b.publication_date || 0).getTime() -
            new Date(a.publication_date || 0).getTime()
          );
        default:
          return 0;
      }
    });

    return result;
  }, [data?.items, searchQuery, sortBy]);

  const toggleSelection = (adId: string) => {
    if (selectedAdIds.includes(adId)) {
      onSelectionChange(selectedAdIds.filter((id) => id !== adId));
    } else if (selectedAdIds.length < maxSelections) {
      onSelectionChange([...selectedAdIds, adId]);
    }
  };

  const isSelected = (adId: string) => selectedAdIds.includes(adId);
  const canSelectMore = selectedAdIds.length < maxSelections;

  if (error) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <AlertCircle className="h-12 w-12 text-red-400 mb-4" />
          <p className="text-muted-foreground">Failed to load inspiration gallery</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="space-y-4 pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Winning Ads Library</CardTitle>
          <Badge variant="secondary">
            {selectedAdIds.length}/{maxSelections} selected
          </Badge>
        </div>

        {/* Filters */}
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search ads..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select
            value={creativeType}
            onValueChange={(v) => setCreativeType(v as 'all' | 'video' | 'image')}
          >
            <SelectTrigger className="w-full sm:w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="video">Videos</SelectItem>
              <SelectItem value="image">Images</SelectItem>
            </SelectContent>
          </Select>
          <Select value={sortBy} onValueChange={(v) => setSortBy(v as typeof sortBy)}>
            <SelectTrigger className="w-full sm:w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="score">Highest Score</SelectItem>
              <SelectItem value="engagement">Most Engaged</SelectItem>
              <SelectItem value="date">Most Recent</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-hidden p-0">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
          </div>
        ) : filteredAds.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
            <Film className="h-12 w-12 mb-4 opacity-50" />
            <p>No analyzed ads found</p>
            <p className="text-sm mt-1">Try adjusting your filters</p>
          </div>
        ) : (
          <ScrollArea className="h-[500px] px-6 pb-6">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredAds.map((ad) => (
                <AdCard
                  key={ad.id}
                  ad={ad}
                  isSelected={isSelected(ad.id)}
                  onToggle={() => toggleSelection(ad.id)}
                  disabled={!isSelected(ad.id) && !canSelectMore}
                />
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}

interface AdCardProps {
  ad: Ad;
  isSelected: boolean;
  onToggle: () => void;
  disabled: boolean;
}

function AdCard({ ad, isSelected, onToggle, disabled }: AdCardProps) {
  const scorePercent = Math.round((ad.composite_score || 0) * 100);

  return (
    <Card
      className={`cursor-pointer transition-all overflow-hidden ${
        isSelected
          ? 'ring-2 ring-primary bg-primary/5'
          : disabled
            ? 'opacity-50'
            : 'hover:shadow-md hover:bg-muted/50'
      }`}
      onClick={() => !disabled && onToggle()}
    >
      {/* Thumbnail */}
      <div className="relative aspect-video bg-muted">
        {ad.creative_url ? (
          ad.creative_type === 'video' ? (
            <video
              src={ad.creative_url}
              className="w-full h-full object-cover"
              muted
              preload="metadata"
            />
          ) : (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={ad.creative_url} alt="" className="w-full h-full object-cover" />
          )
        ) : (
          <div className="flex items-center justify-center h-full">
            {ad.creative_type === 'video' ? (
              <Video className="h-8 w-8 text-muted-foreground" />
            ) : (
              <ImageIcon className="h-8 w-8 text-muted-foreground" />
            )}
          </div>
        )}

        {/* Selection overlay */}
        <div className="absolute top-2 right-2">
          <div
            className={`flex items-center justify-center w-6 h-6 rounded-full border-2 ${
              isSelected
                ? 'bg-primary border-primary text-primary-foreground'
                : 'bg-background/80 border-muted-foreground/50'
            }`}
          >
            {isSelected && <CheckCircle2 className="h-4 w-4" />}
          </div>
        </div>

        {/* Score badge */}
        {ad.composite_score !== undefined && ad.composite_score !== null && (
          <Badge
            className="absolute bottom-2 left-2"
            variant={scorePercent >= 70 ? 'default' : scorePercent >= 50 ? 'secondary' : 'outline'}
          >
            <TrendingUp className="h-3 w-3 mr-1" />
            {scorePercent}%
          </Badge>
        )}

        {/* Type badge */}
        <Badge variant="secondary" className="absolute bottom-2 right-2 capitalize">
          {ad.creative_type}
        </Badge>
      </div>

      <CardContent className="p-3 space-y-2">
        {/* Ad headline or summary */}
        <p className="text-sm font-medium line-clamp-2">
          {ad.ad_headline || ad.ad_summary || ad.ad_copy?.slice(0, 100) || 'Untitled Ad'}
        </p>

        {/* Meta info */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <TrendingUp className="h-3 w-3" />
            {ad.total_engagement.toLocaleString()} engagements
          </div>
          {ad.publication_date && (
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatDistanceToNow(new Date(ad.publication_date), { addSuffix: true })}
            </div>
          )}
        </div>

        {/* Hidden checkbox for accessibility */}
        <Checkbox
          checked={isSelected}
          onCheckedChange={() => onToggle()}
          disabled={disabled}
          className="sr-only"
        />
      </CardContent>
    </Card>
  );
}
