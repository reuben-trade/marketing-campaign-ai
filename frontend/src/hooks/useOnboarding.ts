import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { onboardingApi } from '@/lib/api/onboarding';
import type { BrandProfileCreate, BrandProfileUpdate } from '@/types/onboarding';

// Query keys
export const onboardingKeys = {
  all: ['onboarding'] as const,
  status: () => [...onboardingKeys.all, 'status'] as const,
  profile: () => [...onboardingKeys.all, 'profile'] as const,
  profileById: (id: string) => [...onboardingKeys.all, 'profile', id] as const,
  industries: () => [...onboardingKeys.all, 'industries'] as const,
  tones: () => [...onboardingKeys.all, 'tones'] as const,
};

/**
 * Hook to get onboarding status
 */
export function useOnboardingStatus() {
  return useQuery({
    queryKey: onboardingKeys.status(),
    queryFn: () => onboardingApi.getStatus(),
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Hook to get current brand profile
 */
export function useBrandProfile() {
  return useQuery({
    queryKey: onboardingKeys.profile(),
    queryFn: () => onboardingApi.getBrandProfile(),
    retry: false, // Don't retry if profile doesn't exist
  });
}

/**
 * Hook to get brand profile by ID
 */
export function useBrandProfileById(id: string) {
  return useQuery({
    queryKey: onboardingKeys.profileById(id),
    queryFn: () => onboardingApi.getBrandProfileById(id),
    enabled: !!id,
  });
}

/**
 * Hook to complete onboarding
 */
export function useCompleteOnboarding() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: BrandProfileCreate) => onboardingApi.completeOnboarding(data),
    onSuccess: () => {
      // Invalidate onboarding queries to refetch status
      queryClient.invalidateQueries({ queryKey: onboardingKeys.all });
    },
  });
}

/**
 * Hook to update brand profile
 */
export function useUpdateBrandProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: BrandProfileUpdate }) =>
      onboardingApi.updateBrandProfile(id, data),
    onSuccess: (_, variables) => {
      // Invalidate specific profile and general profile queries
      queryClient.invalidateQueries({ queryKey: onboardingKeys.profileById(variables.id) });
      queryClient.invalidateQueries({ queryKey: onboardingKeys.profile() });
      queryClient.invalidateQueries({ queryKey: onboardingKeys.status() });
    },
  });
}

/**
 * Hook to delete brand profile
 */
export function useDeleteBrandProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => onboardingApi.deleteBrandProfile(id),
    onSuccess: () => {
      // Invalidate all onboarding queries
      queryClient.invalidateQueries({ queryKey: onboardingKeys.all });
    },
  });
}

/**
 * Hook to get industry options
 */
export function useIndustryOptions() {
  return useQuery({
    queryKey: onboardingKeys.industries(),
    queryFn: () => onboardingApi.getIndustryOptions(),
    staleTime: Infinity, // Options don't change
  });
}

/**
 * Hook to get tone options
 */
export function useToneOptions() {
  return useQuery({
    queryKey: onboardingKeys.tones(),
    queryFn: () => onboardingApi.getToneOptions(),
    staleTime: Infinity, // Options don't change
  });
}
