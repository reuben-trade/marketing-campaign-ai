'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { recipesApi } from '@/lib/api/recipes';
import type { RecipeFilters, RecipeExtractRequest } from '@/types/recipe';

export function useRecipes(filters?: RecipeFilters) {
  return useQuery({
    queryKey: ['recipes', filters],
    queryFn: () => recipesApi.list(filters),
    staleTime: 60000, // 1 minute
  });
}

export function useRecipe(id: string) {
  return useQuery({
    queryKey: ['recipe', id],
    queryFn: () => recipesApi.get(id),
    enabled: !!id,
  });
}

export function useExtractRecipe() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: RecipeExtractRequest) => recipesApi.extract(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
    },
  });
}

export function useDeleteRecipe() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => recipesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
    },
  });
}
