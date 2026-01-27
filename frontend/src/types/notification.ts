export type NotificationType =
  | 'new_ads'
  | 'analysis_complete'
  | 'recommendation_ready'
  | 'competitor_discovered'
  | 'system';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  competitor_id?: string;
  competitor_name?: string;
  ad_id?: string;
  ad_count?: number;
  created_at: string;
  read_at?: string;
  is_read: boolean;
}

export interface NotificationListResponse {
  items: Notification[];
  total: number;
  unread_count: number;
}

export interface NotificationMarkReadRequest {
  notification_ids?: string[];
}
