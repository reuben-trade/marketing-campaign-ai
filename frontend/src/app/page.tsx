'use client';

import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useStrategies } from '@/hooks/useStrategy';
import { useCompetitors } from '@/hooks/useCompetitors';
import { useAdStats } from '@/hooks/useAds';
import { useLatestRecommendation } from '@/hooks/useRecommendations';
import {
  Building2,
  Users,
  MonitorPlay,
  ImageIcon,
  Video,
  Lightbulb,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
} from 'lucide-react';

export default function DashboardPage() {
  const { data: strategies } = useStrategies();
  const { data: competitors, isLoading: competitorsLoading } = useCompetitors({ page_size: 100 });
  const { data: adStats, isLoading: adStatsLoading } = useAdStats();
  const { data: latestRecommendation } = useLatestRecommendation();

  const hasStrategy = strategies && strategies.length > 0;
  const competitorCount = competitors?.total ?? 0;
  const totalAds = adStats?.total_ads ?? 0;
  const analyzedAds = adStats?.analyzed_ads ?? 0;
  const imageCount = adStats?.by_type?.image ?? 0;
  const videoCount = adStats?.by_type?.video ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">Overview of your competitor analysis</p>
      </div>

      {/* Quick Setup Status */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Getting Started</CardTitle>
          <CardDescription>Complete these steps to start analyzing competitor ads</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {hasStrategy ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-yellow-500" />
                )}
                <div>
                  <p className="font-medium">Business Strategy</p>
                  <p className="text-sm text-gray-500">
                    {hasStrategy ? 'Strategy configured' : 'Add your business details'}
                  </p>
                </div>
              </div>
              <Button variant={hasStrategy ? 'outline' : 'default'} size="sm" asChild>
                <Link href="/setup">{hasStrategy ? 'View' : 'Setup'}</Link>
              </Button>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {competitorCount > 0 ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-yellow-500" />
                )}
                <div>
                  <p className="font-medium">Competitors</p>
                  <p className="text-sm text-gray-500">
                    {competitorCount > 0
                      ? `${competitorCount} competitors tracked`
                      : 'Add competitors to track'}
                  </p>
                </div>
              </div>
              <Button variant={competitorCount > 0 ? 'outline' : 'default'} size="sm" asChild>
                <Link href="/competitors">{competitorCount > 0 ? 'Manage' : 'Add'}</Link>
              </Button>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {totalAds > 0 ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-yellow-500" />
                )}
                <div>
                  <p className="font-medium">Competitor Ads</p>
                  <p className="text-sm text-gray-500">
                    {totalAds > 0 ? `${totalAds} ads downloaded` : 'Download competitor ads'}
                  </p>
                </div>
              </div>
              <Button variant={totalAds > 0 ? 'outline' : 'default'} size="sm" asChild>
                <Link href="/competitors">{totalAds > 0 ? 'View' : 'Download'}</Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Competitors</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {competitorsLoading ? '...' : competitorCount}
            </div>
            <p className="text-xs text-muted-foreground">
              {competitorCount === 1 ? 'competitor' : 'competitors'} being tracked
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Ads</CardTitle>
            <MonitorPlay className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{adStatsLoading ? '...' : totalAds}</div>
            <div className="flex gap-2 mt-1">
              <Badge variant="secondary" className="text-xs">
                <ImageIcon className="h-3 w-3 mr-1" />
                {imageCount}
              </Badge>
              <Badge variant="secondary" className="text-xs">
                <Video className="h-3 w-3 mr-1" />
                {videoCount}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Analyzed</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{adStatsLoading ? '...' : analyzedAds}</div>
            <p className="text-xs text-muted-foreground">
              {totalAds > 0 ? `${Math.round((analyzedAds / totalAds) * 100)}%` : '0%'} of ads
              analyzed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Engagement</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {adStatsLoading ? '...' : Math.round(adStats?.avg_engagement ?? 0)}
            </div>
            <p className="text-xs text-muted-foreground">likes + comments + shares</p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Link href="/ads">
          <Card className="hover:border-gray-400 transition-colors cursor-pointer h-full">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Browse Ads
                <ArrowRight className="h-4 w-4" />
              </CardTitle>
              <CardDescription>View and filter competitor ads</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-500">
                {totalAds} ads available to browse with filters by competitor, media type, and
                engagement.
              </p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/analysis">
          <Card className="hover:border-gray-400 transition-colors cursor-pointer h-full">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Video Analysis
                <ArrowRight className="h-4 w-4" />
              </CardTitle>
              <CardDescription>Deep dive into video content</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-500">
                Analyze hooks, CTAs, testimonials and more with beat-by-beat video breakdown.
              </p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/ideas">
          <Card className="hover:border-gray-400 transition-colors cursor-pointer h-full">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  Content Ideas
                  {latestRecommendation && <Badge variant="outline">New</Badge>}
                </span>
                <ArrowRight className="h-4 w-4" />
              </CardTitle>
              <CardDescription>Get AI-powered recommendations</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-500">
                Generate content ideas based on top-performing competitor ads.
              </p>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Latest Recommendation Preview */}
      {latestRecommendation && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Lightbulb className="h-5 w-5 text-yellow-500" />
                  Latest Recommendations
                </CardTitle>
                <CardDescription>
                  Generated{' '}
                  {new Date(latestRecommendation.generated_date).toLocaleDateString()}
                </CardDescription>
              </div>
              <Button variant="outline" asChild>
                <Link href="/ideas">View All</Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {latestRecommendation.executive_summary && (
              <p className="text-sm text-gray-600 line-clamp-3">
                {latestRecommendation.executive_summary}
              </p>
            )}
            <div className="mt-4 flex gap-2">
              <Badge>{latestRecommendation.recommendations?.length ?? 0} recommendations</Badge>
              <Badge variant="outline">
                {latestRecommendation.ads_analyzed?.length ?? 0} ads analyzed
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
