// ABOUTME: Zustand store for managing the code bundle state.
// ABOUTME: Persists bundle to localStorage for cross-session persistence.

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { BundleItem } from '../types';

interface BundleState {
  items: BundleItem[];
  isOpen: boolean;
  addItem: (item: BundleItem) => void;
  removeItem: (code: string, system: string) => void;
  clear: () => void;
  hasItem: (code: string, system: string) => boolean;
  toggleOpen: () => void;
  setOpen: (open: boolean) => void;
}

export const useBundleStore = create<BundleState>()(
  persist(
    (set, get) => ({
      items: [],
      isOpen: false,

      addItem: (item) => {
        const { items } = get();
        // Prevent duplicates
        if (items.some(i => i.code === item.code && i.system === item.system)) {
          return;
        }
        // Auto-open sidebar when first item is added
        set({ items: [...items, item], isOpen: true });
      },

      removeItem: (code, system) => {
        set((state) => ({
          items: state.items.filter(i => !(i.code === code && i.system === system))
        }));
      },

      clear: () => set({ items: [], isOpen: false }),

      hasItem: (code, system) => {
        return get().items.some(i => i.code === code && i.system === system);
      },

      toggleOpen: () => set((state) => ({ isOpen: !state.isOpen })),

      setOpen: (open) => set({ isOpen: open }),
    }),
    {
      name: 'clinical-codes-bundle',
    }
  )
);

export function exportBundleToCSV(items: BundleItem[]): void {
  if (items.length === 0) return;

  const headers = ['System', 'Code', 'Display'];
  const rows = items.map(item => [
    item.system,
    item.code,
    `"${item.display.replace(/"/g, '""')}"`,
  ]);

  const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);

  // Format: clinical-codes-bundle-2025-12-18-1430.csv
  const now = new Date();
  const date = now.toISOString().slice(0, 10);
  const time = now.toTimeString().slice(0, 5).replace(':', '');
  const filename = `clinical-codes-bundle-${date}-${time}.csv`;

  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();

  URL.revokeObjectURL(url);
}
