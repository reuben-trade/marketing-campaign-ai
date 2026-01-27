'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  useCompetitors,
  useAddCompetitor,
  useDeleteCompetitor,
  useDiscoverCompetitors,
} from '@/hooks/useCompetitors';
import { useRetrieveAds } from '@/hooks/useAds';
import { useSelectionStore } from '@/stores/selectionStore';
import {
  Plus,
  Search,
  Download,
  Trash2,
  Loader2,
  Building2,
  ExternalLink,
} from 'lucide-react';
import type { Competitor } from '@/types/competitor';
import { formatDistanceToNow } from 'date-fns';

const addCompetitorSchema = z.object({
  company_name: z.string().min(1, 'Company name is required'),
  facebook_url: z.string().optional(),
  industry: z.string().optional(),
  market_position: z.enum(['leader', 'challenger', 'niche']).optional(),
});

type AddCompetitorFormData = z.infer<typeof addCompetitorSchema>;

export default function CompetitorsPage() {
  const [discoverCount, setDiscoverCount] = useState(5);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [downloadingFor, setDownloadingFor] = useState<string | null>(null);

  const { data: competitorsData, isLoading } = useCompetitors({ page_size: 100 });
  const addCompetitor = useAddCompetitor();
  const deleteCompetitor = useDeleteCompetitor();
  const discoverCompetitors = useDiscoverCompetitors();
  const retrieveAds = useRetrieveAds();

  const { selectedCompetitorIds, toggleCompetitorSelection, selectAllCompetitors, clearCompetitorSelection } =
    useSelectionStore();

  const competitors = competitorsData?.items ?? [];

  const form = useForm<AddCompetitorFormData>({
    resolver: zodResolver(addCompetitorSchema),
    defaultValues: {
      company_name: '',
      facebook_url: '',
      industry: '',
    },
  });

  const onAddCompetitor = async (data: AddCompetitorFormData) => {
    try {
      await addCompetitor.mutateAsync({
        company_name: data.company_name,
        facebook_url: data.facebook_url || undefined,
        industry: data.industry || undefined,
        market_position: data.market_position,
      });
      toast.success(`Added ${data.company_name}`);
      form.reset();
      setIsAddDialogOpen(false);
    } catch {
      toast.error('Failed to add competitor. Make sure the Facebook URL is valid.');
    }
  };

  const onDiscover = async () => {
    try {
      const result = await discoverCompetitors.mutateAsync({
        max_competitors: discoverCount,
      });
      toast.success(
        `Discovered ${result.discovered.length} competitors. ${result.already_tracked} already tracked.`
      );
      if (result.pending_manual_review.length > 0) {
        toast.info(`${result.pending_manual_review.length} need manual review`);
      }
    } catch {
      toast.error('Failed to discover competitors');
    }
  };

  const onDownloadAds = async (competitorId: string) => {
    setDownloadingFor(competitorId);
    try {
      const result = await retrieveAds.mutateAsync({
        competitor_id: competitorId,
        max_ads: 50,
      });
      toast.success(`Retrieved ${result.retrieved} new ads`);
    } catch {
      toast.error('Failed to download ads');
    } finally {
      setDownloadingFor(null);
    }
  };

  const onDownloadSelectedAds = async () => {
    for (const id of selectedCompetitorIds) {
      await onDownloadAds(id);
    }
    clearCompetitorSelection();
  };

  const onDelete = async (competitor: Competitor) => {
    try {
      await deleteCompetitor.mutateAsync(competitor.id);
      toast.success(`Removed ${competitor.company_name}`);
    } catch {
      toast.error('Failed to remove competitor');
    }
  };

  const toggleSelectAll = () => {
    if (selectedCompetitorIds.length === competitors.length) {
      clearCompetitorSelection();
    } else {
      selectAllCompetitors(competitors.map((c) => c.id));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Competitors</h1>
          <p className="text-gray-500 mt-1">Discover and manage competitors to track</p>
        </div>
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Competitor
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Competitor</DialogTitle>
              <DialogDescription>
                Add a competitor manually. We&apos;ll automatically find their Facebook Page ID.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={form.handleSubmit(onAddCompetitor)}>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="company_name">Company Name *</Label>
                  <Input
                    id="company_name"
                    {...form.register('company_name')}
                    placeholder="e.g., Nike"
                  />
                  {form.formState.errors.company_name && (
                    <p className="text-sm text-red-500">
                      {form.formState.errors.company_name.message}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="facebook_url">Facebook URL (optional)</Label>
                  <Input
                    id="facebook_url"
                    {...form.register('facebook_url')}
                    placeholder="https://facebook.com/nike"
                  />
                  <p className="text-xs text-gray-500">
                    We&apos;ll auto-detect the Page ID from the URL
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="industry">Industry</Label>
                  <Input
                    id="industry"
                    {...form.register('industry')}
                    placeholder="e.g., Sportswear"
                  />
                </div>

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
              </div>
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsAddDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={addCompetitor.isPending}>
                  {addCompetitor.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Adding...
                    </>
                  ) : (
                    'Add Competitor'
                  )}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Auto-Discover Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Auto-Discover Competitors
          </CardTitle>
          <CardDescription>
            Use AI to find competitors based on your business strategy
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-6">
            <div className="flex-1">
              <Label className="mb-2 block">Number to discover: {discoverCount}</Label>
              <Slider
                value={[discoverCount]}
                onValueChange={([value]) => setDiscoverCount(value)}
                min={1}
                max={10}
                step={1}
                className="w-full max-w-xs"
              />
            </div>
            <Button onClick={onDiscover} disabled={discoverCompetitors.isPending}>
              {discoverCompetitors.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Discovering...
                </>
              ) : (
                <>
                  <Search className="mr-2 h-4 w-4" />
                  Discover Competitors
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Competitors List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Your Competitors ({competitorsData?.total ?? 0})</CardTitle>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={toggleSelectAll}>
                {selectedCompetitorIds.length === competitors.length ? 'Deselect All' : 'Select All'}
              </Button>
              {selectedCompetitorIds.length > 0 && (
                <Button size="sm" onClick={onDownloadSelectedAds} disabled={retrieveAds.isPending}>
                  <Download className="h-4 w-4 mr-2" />
                  Download Ads ({selectedCompetitorIds.length})
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
            </div>
          ) : competitors.length === 0 ? (
            <div className="text-center py-12">
              <Building2 className="h-12 w-12 mx-auto text-gray-300 mb-4" />
              <p className="text-gray-500">No competitors added yet</p>
              <p className="text-sm text-gray-400 mt-1">
                Add competitors manually or use auto-discover
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {competitors.map((competitor) => (
                <CompetitorCard
                  key={competitor.id}
                  competitor={competitor}
                  isSelected={selectedCompetitorIds.includes(competitor.id)}
                  onToggleSelect={() => toggleCompetitorSelection(competitor.id)}
                  onDownload={() => onDownloadAds(competitor.id)}
                  onDelete={() => onDelete(competitor)}
                  isDownloading={downloadingFor === competitor.id}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function CompetitorCard({
  competitor,
  isSelected,
  onToggleSelect,
  onDownload,
  onDelete,
  isDownloading,
}: {
  competitor: Competitor;
  isSelected: boolean;
  onToggleSelect: () => void;
  onDownload: () => void;
  onDelete: () => void;
  isDownloading: boolean;
}) {
  return (
    <div
      className={`flex items-center gap-4 p-4 rounded-lg border transition-colors ${
        isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
      }`}
    >
      <Checkbox checked={isSelected} onCheckedChange={onToggleSelect} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="font-medium truncate">{competitor.company_name}</h3>
          {competitor.is_market_leader && <Badge variant="secondary">Leader</Badge>}
          {competitor.facebook_page && (
            <a
              href={competitor.facebook_page}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-400 hover:text-gray-600"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          )}
        </div>
        <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
          {competitor.industry && <span>{competitor.industry}</span>}
          <span>{competitor.ad_count ?? 0} ads</span>
          {competitor.last_retrieved && (
            <span>
              Last retrieved{' '}
              {formatDistanceToNow(new Date(competitor.last_retrieved), { addSuffix: true })}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" onClick={onDownload} disabled={isDownloading}>
          {isDownloading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
        </Button>
        <Button variant="ghost" size="sm" onClick={onDelete} className="text-red-500 hover:text-red-700">
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
