import { get, post, put, del } from './client';
import type {
  BrandProfile,
  BrandProfileCreate,
  BrandProfileUpdate,
  OnboardingStatusResponse,
  IndustryOption,
  ToneOption,
} from '@/types/onboarding';

export const onboardingApi = {
  /**
   * Get onboarding status - check if user has completed onboarding
   */
  getStatus: async (): Promise<OnboardingStatusResponse> => {
    return get<OnboardingStatusResponse>('/api/onboarding/status');
  },

  /**
   * Complete onboarding and create a brand profile
   */
  completeOnboarding: async (data: BrandProfileCreate): Promise<BrandProfile> => {
    return post<BrandProfile>('/api/onboarding', data);
  },

  /**
   * Get the current brand profile
   */
  getBrandProfile: async (): Promise<BrandProfile> => {
    return get<BrandProfile>('/api/onboarding');
  },

  /**
   * Get a brand profile by ID
   */
  getBrandProfileById: async (id: string): Promise<BrandProfile> => {
    return get<BrandProfile>(`/api/onboarding/${id}`);
  },

  /**
   * Update a brand profile
   */
  updateBrandProfile: async (id: string, data: BrandProfileUpdate): Promise<BrandProfile> => {
    return put<BrandProfile>(`/api/onboarding/${id}`, data);
  },

  /**
   * Delete a brand profile
   */
  deleteBrandProfile: async (id: string): Promise<void> => {
    return del<void>(`/api/onboarding/${id}`);
  },

  /**
   * Get industry options
   */
  getIndustryOptions: async (): Promise<IndustryOption[]> => {
    return get<IndustryOption[]>('/api/onboarding/options/industries');
  },

  /**
   * Get tone options
   */
  getToneOptions: async (): Promise<ToneOption[]> => {
    return get<ToneOption[]>('/api/onboarding/options/tones');
  },
};
