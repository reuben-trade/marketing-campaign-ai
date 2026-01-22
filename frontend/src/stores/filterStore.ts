'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface FilterState {
  // Ads filters
  selectedCompetitorIds: string[];
  creativeType: 'all' | 'image' | 'video';
  analyzedOnly: boolean | null;
  minEngagement: number;

  // Actions
  setSelectedCompetitors: (ids: string[]) => void;
  toggleCompetitor: (id: string) => void;
  setCreativeType: (type: 'all' | 'image' | 'video') => void;
  setAnalyzedOnly: (value: boolean | null) => void;
  setMinEngagement: (value: number) => void;
  clearFilters: () => void;
}

export const useFilterStore = create<FilterState>()(
  persist(
    (set) => ({
      selectedCompetitorIds: [],
      creativeType: 'all',
      analyzedOnly: null,
      minEngagement: 0,

      setSelectedCompetitors: (ids) => set({ selectedCompetitorIds: ids }),
      toggleCompetitor: (id) =>
        set((state) => ({
          selectedCompetitorIds: state.selectedCompetitorIds.includes(id)
            ? state.selectedCompetitorIds.filter((cid) => cid !== id)
            : [...state.selectedCompetitorIds, id],
        })),
      setCreativeType: (type) => set({ creativeType: type }),
      setAnalyzedOnly: (value) => set({ analyzedOnly: value }),
      setMinEngagement: (value) => set({ minEngagement: value }),
      clearFilters: () =>
        set({
          selectedCompetitorIds: [],
          creativeType: 'all',
          analyzedOnly: null,
          minEngagement: 0,
        }),
    }),
    {
      name: 'ads-filter-storage',
    }
  )
);
