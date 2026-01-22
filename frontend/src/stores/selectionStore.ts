'use client';

import { create } from 'zustand';

interface SelectionState {
  // Competitor selection for bulk operations
  selectedCompetitorIds: string[];

  // Ad selection for bulk operations
  selectedAdIds: string[];

  // Actions
  toggleCompetitorSelection: (id: string) => void;
  selectAllCompetitors: (ids: string[]) => void;
  clearCompetitorSelection: () => void;

  toggleAdSelection: (id: string) => void;
  selectAllAds: (ids: string[]) => void;
  clearAdSelection: () => void;

  clearAll: () => void;
}

export const useSelectionStore = create<SelectionState>((set) => ({
  selectedCompetitorIds: [],
  selectedAdIds: [],

  toggleCompetitorSelection: (id) =>
    set((state) => ({
      selectedCompetitorIds: state.selectedCompetitorIds.includes(id)
        ? state.selectedCompetitorIds.filter((cid) => cid !== id)
        : [...state.selectedCompetitorIds, id],
    })),
  selectAllCompetitors: (ids) => set({ selectedCompetitorIds: ids }),
  clearCompetitorSelection: () => set({ selectedCompetitorIds: [] }),

  toggleAdSelection: (id) =>
    set((state) => ({
      selectedAdIds: state.selectedAdIds.includes(id)
        ? state.selectedAdIds.filter((aid) => aid !== id)
        : [...state.selectedAdIds, id],
    })),
  selectAllAds: (ids) => set({ selectedAdIds: ids }),
  clearAdSelection: () => set({ selectedAdIds: [] }),

  clearAll: () => set({ selectedCompetitorIds: [], selectedAdIds: [] }),
}));
