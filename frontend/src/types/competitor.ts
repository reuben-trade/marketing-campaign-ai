export interface Competitor {
  id: string;
  company_name: string;
  page_id: string;
  facebook_page?: string;
  industry?: string;
  follower_count?: number;
  is_market_leader: boolean;
  market_position?: 'leader' | 'challenger' | 'niche';
  discovery_method?: 'automated' | 'manual_add';
  discovered_date: string;
  last_retrieved?: string;
  active: boolean;
  metadata?: Record<string, unknown>;
  ad_count?: number;
}

export interface CompetitorCreate {
  company_name: string;
  facebook_url?: string;
  industry?: string;
  follower_count?: number;
  is_market_leader?: boolean;
  market_position?: 'leader' | 'challenger' | 'niche';
  discovery_method?: string;
}

export interface CompetitorUpdate {
  company_name?: string;
  page_id?: string;
  industry?: string;
  follower_count?: number;
  is_market_leader?: boolean;
  market_position?: string;
  active?: boolean;
}

export interface CompetitorListResponse {
  items: Competitor[];
  total: number;
  page: number;
  page_size: number;
}

export interface CompetitorDiscoverRequest {
  industry?: string;
  max_competitors: number;
  include_market_leaders?: boolean;
}

export interface PendingCompetitor {
  company_name: string;
  facebook_page_url?: string;
  relevance_reason?: string;
  description?: string;
}

export interface CompetitorDiscoverResponse {
  discovered: Competitor[];
  total_found: number;
  already_tracked: number;
  pending_manual_review: PendingCompetitor[];
}
