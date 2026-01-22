export interface Notification {
  id: string;
  type: 'new_ads' | 'analysis_complete' | 'recommendation_ready';
  message: string;
  competitor_id?: string;
  competitor_name?: string;
  ad_count?: number;
  created_at: string;
  read_at?: string;
}

export interface NotificationListResponse {
  items: Notification[];
  total: number;
  unread_count: number;
}
