import { get, post, del } from './client';
import type { Notification, NotificationListResponse } from '@/types/notification';

export interface UnreadCountResponse {
  unread_count: number;
}

export const notificationsApi = {
  list: async (params?: {
    unread_only?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<NotificationListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.unread_only) searchParams.append('unread_only', 'true');
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString());

    const queryString = searchParams.toString();
    return get<NotificationListResponse>(
      `/api/notifications${queryString ? `?${queryString}` : ''}`
    );
  },

  getUnreadCount: async (): Promise<UnreadCountResponse> => {
    return get<UnreadCountResponse>('/api/notifications/unread-count');
  },

  markAsRead: async (id: string): Promise<Notification> => {
    return post<Notification>(`/api/notifications/${id}/read`);
  },

  markAllAsRead: async (): Promise<void> => {
    return post<void>('/api/notifications/read-all');
  },

  delete: async (id: string): Promise<void> => {
    return del<void>(`/api/notifications/${id}`);
  },
};
